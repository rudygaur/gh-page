from flask import jsonify, make_response


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
