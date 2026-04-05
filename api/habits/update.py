from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/habits/update', methods=['PUT', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    habit_id = request.args.get('id')
    if not habit_id:
        return error_response('Habit id is required')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    sets = []
    params = []
    if 'name' in data:
        sets.append("name = %s")
        params.append(data['name'])
    if 'emoji' in data:
        sets.append("emoji = %s")
        params.append(data['emoji'])

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
