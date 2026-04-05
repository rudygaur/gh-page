from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/habits/delete', methods=['DELETE', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
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
