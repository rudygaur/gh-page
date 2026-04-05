from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/tasks/update', methods=['PUT', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    task_id = request.args.get('id')
    if not task_id:
        return error_response('Task id is required')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    sets = []
    params = []
    if 'title' in data:
        sets.append("title = %s")
        params.append(data['title'])
    if 'priority' in data:
        if data['priority'] not in ('high', 'medium', 'low'):
            return error_response('Priority must be high, medium, or low')
        sets.append("priority = %s")
        params.append(data['priority'])
    if 'is_done' in data:
        sets.append("is_done = %s")
        params.append(bool(data['is_done']))
    if 'due_date' in data:
        sets.append("due_date = %s")
        params.append(data['due_date'])

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
