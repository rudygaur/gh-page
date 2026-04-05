from flask import Flask, request
from api._utils.db import query
from api._utils.auth import require_auth
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        return handle_cors()

    user_id = require_auth(request)
    if not user_id:
        return error_response('Unauthorized', 401)

    user = query(
        "SELECT id, username, created_at FROM users WHERE id = %s",
        (user_id,), fetchone=True
    )

    if not user:
        return error_response('User not found', 404)

    user['created_at'] = user['created_at'].isoformat()
    return json_response(user)
