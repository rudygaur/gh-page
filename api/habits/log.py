from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/habits/log', methods=['POST', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
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
