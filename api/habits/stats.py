from flask import Flask, request
from datetime import date, timedelta
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/habits/stats', methods=['GET', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    today = date.today()
    week_ago = today - timedelta(days=6)

    total_habits = query(
        "SELECT COUNT(*) as cnt FROM habits WHERE user_id = %s AND is_active = TRUE",
        (user_id,), fetchone=True
    )['cnt']

    if total_habits == 0:
        return json_response({
            'weekly_data': [],
            'weekly_avg': 0,
            'best_day': None,
            'top_habit': None,
            'day_streak': 0,
            'today_done': 0,
            'today_total': 0,
            'tasks_done': 0,
            'tasks_total': 0
        })

    # Weekly data: completions per day for last 7 days
    daily_logs = query("""
        SELECT log_date, COUNT(DISTINCT habit_id) as done
        FROM habit_logs
        WHERE user_id = %s AND log_date >= %s AND log_date <= %s
        GROUP BY log_date
        ORDER BY log_date
    """, (user_id, week_ago, today), fetchall=True)

    daily_map = {}
    for row in daily_logs:
        d = row['log_date']
        if isinstance(d, str):
            d = date.fromisoformat(d)
        daily_map[d] = row['done']

    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekly_data = []
    total_pct = 0
    best_pct = -1
    best_day_name = None

    for i in range(7):
        d = week_ago + timedelta(days=i)
        done = daily_map.get(d, 0)
        pct = round((done / total_habits) * 100) if total_habits > 0 else 0
        day_name = day_names[d.weekday()]
        weekly_data.append({'day': day_name, 'date': d.isoformat(), 'percentage': pct})
        total_pct += pct
        if pct > best_pct:
            best_pct = pct
            best_day_name = day_name

    weekly_avg = round(total_pct / 7)

    # Top habit (most logs in last 30 days)
    top = query("""
        SELECT h.name, COUNT(hl.id) as cnt
        FROM habit_logs hl
        JOIN habits h ON h.id = hl.habit_id
        WHERE hl.user_id = %s AND hl.log_date >= %s
        GROUP BY h.name
        ORDER BY cnt DESC
        LIMIT 1
    """, (user_id, today - timedelta(days=30)), fetchone=True)

    top_habit = top['name'] if top else None

    # Day streak: consecutive days with at least one log
    all_logs = query("""
        SELECT DISTINCT log_date FROM habit_logs
        WHERE user_id = %s AND log_date <= %s
        ORDER BY log_date DESC
        LIMIT 365
    """, (user_id, today), fetchall=True)

    day_streak = 0
    expected = today
    for row in all_logs:
        d = row['log_date']
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if d == expected:
            day_streak += 1
            expected -= timedelta(days=1)
        elif d == expected - timedelta(days=1) and day_streak == 0:
            expected = d
            day_streak = 1
            expected -= timedelta(days=1)
        else:
            break

    # Today's stats
    today_done = daily_map.get(today, 0)

    # Task stats
    task_stats = query("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_done = TRUE) as done
        FROM tasks WHERE user_id = %s
    """, (user_id,), fetchone=True)

    return json_response({
        'weekly_data': weekly_data,
        'weekly_avg': weekly_avg,
        'best_day': best_day_name,
        'top_habit': top_habit,
        'day_streak': day_streak,
        'today_done': today_done,
        'today_total': total_habits,
        'tasks_done': task_stats['done'],
        'tasks_total': task_stats['total']
    })
