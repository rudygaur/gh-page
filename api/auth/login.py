from flask import Flask, request
from werkzeug.security import check_password_hash
from api._utils.db import query
from api._utils.auth import create_token
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def handler():
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
