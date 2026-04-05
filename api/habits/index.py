from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/habits', methods=['GET', 'POST', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    if request.method == 'GET':
        habits = query("""
            SELECT h.id, h.name, h.emoji, h.is_active,
                   EXISTS(
                       SELECT 1 FROM habit_logs hl
                       WHERE hl.habit_id = h.id AND hl.log_date = CURRENT_DATE
                   ) AS done_today
            FROM habits h
            WHERE h.user_id = %s AND h.is_active = TRUE
            ORDER BY h.created_at
        """, (user_id,), fetchall=True)

        for habit in habits:
            habit['streak'] = _calc_streak(habit['id'])

        return json_response(habits)

    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'):
            return error_response('Habit name is required')

        habit = query(
            "INSERT INTO habits (user_id, name, emoji) VALUES (%s, %s, %s) RETURNING id, name, emoji, is_active",
            (user_id, data['name'], data.get('emoji', '✅')),
            fetchone=True, commit=True
        )
        habit['done_today'] = False
        habit['streak'] = 0
        return json_response(habit, 201)


def _calc_streak(habit_id):
    logs = query("""
        SELECT log_date FROM habit_logs
        WHERE habit_id = %s AND log_date <= CURRENT_DATE
        ORDER BY log_date DESC
        LIMIT 365
    """, (habit_id,), fetchall=True)

    if not logs:
        return 0

    from datetime import date, timedelta
    streak = 0
    expected = date.today()

    for log in logs:
        log_date = log['log_date']
        if isinstance(log_date, str):
            log_date = date.fromisoformat(log_date)
        if log_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif log_date == expected - timedelta(days=1) and streak == 0:
            expected = log_date
            streak = 1
            expected -= timedelta(days=1)
        else:
            break

    return streak
