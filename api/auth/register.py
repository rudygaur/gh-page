from flask import Flask, request
from werkzeug.security import generate_password_hash
from api._utils.db import query
from api._utils.auth import create_token
from api._utils.response import json_response, error_response, handle_cors

app = Flask(__name__)


@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def handler():
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
