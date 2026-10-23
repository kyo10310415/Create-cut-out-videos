"""Authentication shared by the dashboard and the separate worker API."""
import hashlib
import hmac
import json
import re
from urllib.parse import urlsplit
from flask import g, jsonify, request


def _equal(actual, expected):
    return hmac.compare_digest(hashlib.sha256(actual.encode()).digest(),
                               hashlib.sha256(expected.encode()).digest())


def install_task_access(app, env):
    username = env.get('CLIPPER_ADMIN_USERNAME', '')
    password = env.get('CLIPPER_ADMIN_PASSWORD', '')
    origin = env.get('CLIPPER_PUBLIC_ORIGIN', '')
    if not re.fullmatch(r'[A-Za-z0-9_.@-]{1,100}', username):
        raise ValueError('CLIPPER_ADMIN_USERNAME is required')
    if not 32 <= len(password) <= 512 or re.search(r'\s', password):
        raise ValueError('CLIPPER_ADMIN_PASSWORD must be a random secret of at least 32 characters')
    parsed = urlsplit(origin)
    local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if (not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment
            or (parsed.scheme != 'https' and not (local and parsed.scheme == 'http'))):
        raise ValueError('CLIPPER_PUBLIC_ORIGIN must be an HTTPS origin')
    origin = origin.rstrip('/')
    try:
        workers = json.loads(env.get('CLIPPER_WORKER_TOKENS', ''))
    except (ValueError, TypeError):
        raise ValueError('CLIPPER_WORKER_TOKENS must be a JSON object') from None
    if not isinstance(workers, dict) or not workers:
        raise ValueError('CLIPPER_WORKER_TOKENS must contain at least one worker')
    for worker, token in workers.items():
        if (not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', worker)
                or not isinstance(token, str) or not 32 <= len(token) <= 512
                or re.search(r'\s', token) or token == password):
            raise ValueError('Worker IDs and distinct random tokens must be configured')
    if len(set(workers.values())) != len(workers):
        raise ValueError('Each worker needs a different token')

    @app.before_request
    def authenticate():
        if request.path == '/health' and request.method in ('GET', 'HEAD'):
            return None
        auth = request.authorization
        if auth and auth.type.lower() == 'bearer':
            worker = next((name for name, token in workers.items()
                           if _equal(auth.token or '', token)), None)
            if worker is None:
                return jsonify(success=False, error='Unauthorized'), 401
            if request.method != 'POST' or request.path not in (
                    '/api/tasks/pending', '/api/tasks/complete', '/api/tasks/error'):
                return jsonify(success=False, error='Forbidden'), 403
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify(success=False, error='JSON object required'), 400
            if data.get('worker_id', worker) != worker:
                return jsonify(success=False, error='Forbidden'), 403
            g.worker_id = worker
            return None
        if (not auth or auth.type.lower() != 'basic'
                or not _equal(auth.username or '', username)
                or not _equal(auth.password or '', password)):
            return jsonify(success=False, error='Unauthorized'), 401, {
                'WWW-Authenticate': 'Basic realm="Clipper administration", charset="UTF-8"'}
        # Dashboard credentials do not claim or finish worker tasks.
        if request.path in ('/api/tasks/pending', '/api/tasks/complete', '/api/tasks/error'):
            return jsonify(success=False, error='Worker credential required'), 403
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if request.headers.get('Origin') != origin:
                return jsonify(success=False, error='Forbidden'), 403

    @app.after_request
    def no_store(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/health')
    def health():
        return jsonify(status='ok')
