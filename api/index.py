import os
import jwt
import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-me')

def get_database_url():
    """Neon via Vercel uses POSTGRES_URL; local/manual setup uses DATABASE_URL."""
    url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('POSTGRES_PRISMA_URL', '')
    # Vercel Neon sets postgres:// but psycopg2 needs postgresql://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


# ─── Database helpers ─────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(get_database_url(), sslmode='require')


def query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            if cur.description:
                return dict(cur.fetchone()) if fetchone else [dict(r) for r in cur.fetchall()]
            return cur.rowcount
        if fetchone:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetchall:
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ─── Auth helpers ─────────────────────────────────────────────────────
def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_auth():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    return verify_token(auth_header[7:])


# ─── Response helpers ─────────────────────────────────────────────────
def json_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers['Content-Type'] = 'application/json'
    return resp


def error_response(message, status=400):
    return json_response({'error': message}, status)


def handle_cors():
    resp = make_response('', 204)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return resp


# ─── CORS for all routes ─────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response


# ═══════════════════════════════════════════════════════════════════════
#  SETUP ENDPOINT — creates tables (run once, then remove)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/debug-env', methods=['GET'])
def debug_env():
    """Temporary: show which DB env vars are set (remove after debugging)."""
    db_vars = {}
    for key in sorted(os.environ.keys()):
        lower = key.lower()
        if 'postgres' in lower or 'database' in lower or 'neon' in lower or 'db' in lower or 'pg' in lower:
            val = os.environ[key]
            # Mask the password portion
            if '://' in val:
                db_vars[key] = val[:30] + '...[masked]'
            else:
                db_vars[key] = val[:20] + '...' if len(val) > 20 else val
    return json_response({'found_vars': db_vars, 'resolved_url': get_database_url()[:30] + '...' if get_database_url() else 'EMPTY'})

@app.route('/api/setup', methods=['GET'])
def setup_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                emoji VARCHAR(10) DEFAULT '✅',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
                is_done BOOLEAN DEFAULT FALSE,
                due_date DATE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS habit_logs (
                id SERIAL PRIMARY KEY,
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                log_date DATE NOT NULL DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(habit_id, log_date)
            );
            CREATE INDEX IF NOT EXISTS idx_habit_logs_user_date ON habit_logs(user_id, log_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
        """)
        conn.commit()
        conn.close()
        return json_response({'message': 'Database tables created successfully'})
    except Exception as e:
        return error_response(f'Setup failed: {str(e)}', 500)


# ═══════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def auth_register():
    if request.method == 'OPTIONS':
        return handle_cors()

    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return error_response('Username and password are required')

    username = data['username'].strip().lower()
    password = data['password']

    if len(username) < 3:
        return error_response('Username must be at least 3 characters')
    if len(password) < 4:
        return error_response('Password must be at least 4 characters')

    existing = query("SELECT id FROM users WHERE username = %s", (username,), fetchone=True)
    if existing:
        return error_response('Username already taken')

    password_hash = generate_password_hash(password)
    user = query(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id, username",
        (username, password_hash), fetchone=True, commit=True
    )

    token = create_token(user['id'])
    return json_response({'token': token, 'user': {'id': user['id'], 'username': user['username']}}, 201)


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def auth_login():
    if request.method == 'OPTIONS':
        return handle_cors()

    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return error_response('Username and password are required')

    username = data['username'].strip().lower()
    password = data['password']

    user = query(
        "SELECT id, username, password_hash FROM users WHERE username = %s",
        (username,), fetchone=True
    )

    if not user or not check_password_hash(user['password_hash'], password):
        return error_response('Invalid username or password', 401)

    token = create_token(user['id'])
    return json_response({'token': token, 'user': {'id': user['id'], 'username': user['username']}})


@app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
def auth_me():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    user = query("SELECT id, username, created_at FROM users WHERE id = %s", (user_id,), fetchone=True)
    if not user:
        return error_response('User not found', 404)

    user['created_at'] = user['created_at'].isoformat()
    return json_response(user)


# ═══════════════════════════════════════════════════════════════════════
#  HABITS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

def _calc_streak(habit_id):
    from datetime import date, timedelta
    logs = query("""
        SELECT log_date FROM habit_logs
        WHERE habit_id = %s AND log_date <= CURRENT_DATE
        ORDER BY log_date DESC LIMIT 365
    """, (habit_id,), fetchall=True)

    if not logs:
        return 0

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


@app.route('/api/habits', methods=['GET', 'POST', 'OPTIONS'])
def habits_index():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
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

    # POST
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


@app.route('/api/habits/update', methods=['PUT', 'OPTIONS'])
def habits_update():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    habit_id = request.args.get('id')
    if not habit_id:
        return error_response('Habit id is required')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    sets, params = [], []
    if 'name' in data:
        sets.append("name = %s"); params.append(data['name'])
    if 'emoji' in data:
        sets.append("emoji = %s"); params.append(data['emoji'])

    if not sets:
        return error_response('Nothing to update')

    params.extend([habit_id, user_id])
    habit = query(
        f"UPDATE habits SET {', '.join(sets)} WHERE id = %s AND user_id = %s RETURNING id, name, emoji, is_active",
        params, fetchone=True, commit=True
    )

    if not habit:
        return error_response('Habit not found', 404)
    return json_response(habit)


@app.route('/api/habits/delete', methods=['DELETE', 'OPTIONS'])
def habits_delete():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    habit_id = request.args.get('id')
    if not habit_id:
        return error_response('Habit id is required')

    result = query(
        "UPDATE habits SET is_active = FALSE WHERE id = %s AND user_id = %s RETURNING id",
        (habit_id, user_id), fetchone=True, commit=True
    )

    if not result:
        return error_response('Habit not found', 404)
    return json_response({'message': 'Habit deleted'})


@app.route('/api/habits/log', methods=['POST', 'OPTIONS'])
def habits_log():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    data = request.get_json()
    if not data or not data.get('habit_id'):
        return error_response('habit_id is required')

    habit_id = data['habit_id']

    habit = query(
        "SELECT id FROM habits WHERE id = %s AND user_id = %s AND is_active = TRUE",
        (habit_id, user_id), fetchone=True
    )
    if not habit:
        return error_response('Habit not found', 404)

    existing = query(
        "DELETE FROM habit_logs WHERE habit_id = %s AND user_id = %s AND log_date = CURRENT_DATE RETURNING id",
        (habit_id, user_id), fetchone=True, commit=True
    )

    if existing:
        return json_response({'logged': False, 'message': 'Habit un-logged for today'})

    query(
        "INSERT INTO habit_logs (habit_id, user_id, log_date) VALUES (%s, %s, CURRENT_DATE)",
        (habit_id, user_id), commit=True
    )
    return json_response({'logged': True, 'message': 'Habit logged for today'})


@app.route('/api/habits/stats', methods=['GET', 'OPTIONS'])
def habits_stats():
    if request.method == 'OPTIONS':
        return handle_cors()

    from datetime import date, timedelta

    user_id = require_auth()
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
            'weekly_data': [], 'weekly_avg': 0, 'best_day': None,
            'top_habit': None, 'day_streak': 0, 'today_done': 0,
            'today_total': 0, 'tasks_done': 0, 'tasks_total': 0
        })

    daily_logs = query("""
        SELECT log_date, COUNT(DISTINCT habit_id) as done
        FROM habit_logs
        WHERE user_id = %s AND log_date >= %s AND log_date <= %s
        GROUP BY log_date ORDER BY log_date
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

    top = query("""
        SELECT h.name, COUNT(hl.id) as cnt
        FROM habit_logs hl JOIN habits h ON h.id = hl.habit_id
        WHERE hl.user_id = %s AND hl.log_date >= %s
        GROUP BY h.name ORDER BY cnt DESC LIMIT 1
    """, (user_id, today - timedelta(days=30)), fetchone=True)

    top_habit = top['name'] if top else None

    all_logs = query("""
        SELECT DISTINCT log_date FROM habit_logs
        WHERE user_id = %s AND log_date <= %s
        ORDER BY log_date DESC LIMIT 365
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

    today_done = daily_map.get(today, 0)

    task_stats = query("""
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE is_done = TRUE) as done
        FROM tasks WHERE user_id = %s
    """, (user_id,), fetchone=True)

    return json_response({
        'weekly_data': weekly_data, 'weekly_avg': weekly_avg,
        'best_day': best_day_name, 'top_habit': top_habit,
        'day_streak': day_streak, 'today_done': today_done,
        'today_total': total_habits, 'tasks_done': task_stats['done'],
        'tasks_total': task_stats['total']
    })


# ═══════════════════════════════════════════════════════════════════════
#  TASKS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/tasks', methods=['GET', 'POST', 'OPTIONS'])
def tasks_index():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    if request.method == 'GET':
        tasks = query("""
            SELECT id, title, priority, is_done, due_date, created_at
            FROM tasks WHERE user_id = %s
            ORDER BY is_done ASC, created_at DESC
        """, (user_id,), fetchall=True)

        for t in tasks:
            if t.get('due_date'):
                t['due_date'] = t['due_date'].isoformat()
            if t.get('created_at'):
                t['created_at'] = t['created_at'].isoformat()

        return json_response(tasks)

    # POST
    data = request.get_json()
    if not data or not data.get('title'):
        return error_response('Task title is required')

    priority = data.get('priority', 'medium')
    if priority not in ('high', 'medium', 'low'):
        return error_response('Priority must be high, medium, or low')

    task = query(
        "INSERT INTO tasks (user_id, title, priority, due_date) VALUES (%s, %s, %s, %s) RETURNING id, title, priority, is_done, due_date, created_at",
        (user_id, data['title'], priority, data.get('due_date')),
        fetchone=True, commit=True
    )

    if task.get('due_date'):
        task['due_date'] = task['due_date'].isoformat()
    if task.get('created_at'):
        task['created_at'] = task['created_at'].isoformat()

    return json_response(task, 201)


@app.route('/api/tasks/update', methods=['PUT', 'OPTIONS'])
def tasks_update():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    task_id = request.args.get('id')
    if not task_id:
        return error_response('Task id is required')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    sets, params = [], []
    if 'title' in data:
        sets.append("title = %s"); params.append(data['title'])
    if 'priority' in data:
        if data['priority'] not in ('high', 'medium', 'low'):
            return error_response('Priority must be high, medium, or low')
        sets.append("priority = %s"); params.append(data['priority'])
    if 'is_done' in data:
        sets.append("is_done = %s"); params.append(bool(data['is_done']))
    if 'due_date' in data:
        sets.append("due_date = %s"); params.append(data['due_date'])

    if not sets:
        return error_response('Nothing to update')

    params.extend([task_id, user_id])
    task = query(
        f"UPDATE tasks SET {', '.join(sets)} WHERE id = %s AND user_id = %s RETURNING id, title, priority, is_done, due_date, created_at",
        params, fetchone=True, commit=True
    )

    if not task:
        return error_response('Task not found', 404)

    if task.get('due_date'):
        task['due_date'] = task['due_date'].isoformat()
    if task.get('created_at'):
        task['created_at'] = task['created_at'].isoformat()

    return json_response(task)


@app.route('/api/tasks/delete', methods=['DELETE', 'OPTIONS'])
def tasks_delete():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth()
    if not user_id:
        return error_response('Unauthorized', 401)

    task_id = request.args.get('id')
    if not task_id:
        return error_response('Task id is required')

    result = query(
        "DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id",
        (task_id, user_id), fetchone=True, commit=True
    )

    if not result:
        return error_response('Task not found', 404)
    return json_response({'message': 'Task deleted'})
