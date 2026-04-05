from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/tasks', methods=['GET', 'POST', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    if request.method == 'GET':
        tasks = query("""
            SELECT id, title, priority, is_done, due_date, created_at
            FROM tasks
            WHERE user_id = %s
            ORDER BY is_done ASC, created_at DESC
        """, (user_id,), fetchall=True)

        for t in tasks:
            if t.get('due_date'):
                t['due_date'] = t['due_date'].isoformat()
            if t.get('created_at'):
                t['created_at'] = t['created_at'].isoformat()

        return json_response(tasks)

    if request.method == 'POST':
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
