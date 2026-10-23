import base64
import ast
from concurrent.futures import ThreadPoolExecutor
import json
import unittest
from unittest.mock import Mock
from pathlib import Path
from types import SimpleNamespace
from flask import Flask
from task_access import install_task_access
from task_api import create_task_api
from task_manager import TaskQueue


class TaskAccessTests(unittest.TestCase):
    def setUp(self):
        self.queue = TaskQueue()
        self.config = {'CLIPPER_ADMIN_USERNAME': 'test-admin',
                       'CLIPPER_ADMIN_PASSWORD': 'a' * 48,
                       'CLIPPER_PUBLIC_ORIGIN': 'https://clipper.example',
                       'CLIPPER_WORKER_TOKENS': json.dumps({'one': 'b' * 48, 'two': 'c' * 48})}
        self.app = Flask(__name__)
        install_task_access(self.app, self.config)
        self.app.register_blueprint(create_task_api(self.queue))
        self.client = self.app.test_client()
        self.admin = {'Authorization': 'Basic ' + base64.b64encode(b'test-admin:' + b'a'*48).decode(),
                      'Origin': 'https://clipper.example'}
        self.one = {'Authorization': 'Bearer ' + 'b'*48}
        self.two = {'Authorization': 'Bearer ' + 'c'*48}
        self.task = self.queue.add_task('video', 'title', [{'start': 1, 'end': 2}])

    def claim(self, headers=None):
        return self.client.post('/api/tasks/pending', json={'worker_id': 'one'}, headers=headers or self.one)

    def test_anonymous_all_routes_rejected(self):
        for method, path in [('get', '/'), ('get', '/api/tasks/list'),
                             ('get', '/api/tasks/pending'), ('get', '/api/tasks/' + self.task.task_id),
                             ('post', '/api/tasks/create'), ('post', '/api/tasks/complete'),
                             ('post', '/api/tasks/error')]:
            self.assertEqual(getattr(self.client, method)(path).status_code, 401)
        self.assertEqual(self.task.status, 'pending')

    def test_get_cannot_claim(self):
        self.assertEqual(self.client.get('/api/tasks/pending', headers=self.one).status_code, 403)
        self.assertEqual(self.client.get('/api/tasks/pending', headers=self.admin).status_code, 403)
        self.assertEqual(self.task.status, 'pending')

    def test_worker_identity_is_credential_bound(self):
        self.assertEqual(self.claim(self.two).status_code, 403)
        self.assertEqual(self.task.status, 'pending')
        self.assertEqual(self.claim().status_code, 200)
        self.assertEqual(self.task.worker_id, 'one')

    def test_other_worker_cannot_finish(self):
        self.claim()
        for path, value in [('complete', {'output_file': 'output.mp4'}), ('error', {'error': 'failure'})]:
            response = self.client.post('/api/tasks/' + path, headers=self.two,
                                        json={'task_id': self.task.task_id, 'worker_id': 'two', **value})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task.status, 'processing')

    def test_state_transition_and_replay(self):
        self.claim()
        body = {'task_id': self.task.task_id, 'output_file': 'output.mp4'}
        self.assertEqual(self.client.post('/api/tasks/complete', headers=self.one, json=body).status_code, 200)
        self.assertEqual(self.client.post('/api/tasks/complete', headers=self.one, json=body).status_code, 409)
        self.assertEqual(self.task.status, 'completed')

    def test_pending_task_cannot_be_finished(self):
        self.assertEqual(self.client.post('/api/tasks/complete', headers=self.one,
                         json={'task_id': self.task.task_id, 'output_file': 'output.mp4'}).status_code, 403)

    def test_worker_cannot_read_admin_data_or_create(self):
        for method, path in [('get', '/api/tasks/list'), ('post', '/api/tasks/create'),
                             ('get', '/api/tasks/' + self.task.task_id), ('get', '/')]:
            self.assertEqual(getattr(self.client, method)(path, headers=self.one).status_code, 403)

    def test_admin_normal_create_read_and_worker_separation(self):
        self.assertEqual(self.client.get('/api/tasks/list', headers=self.admin).status_code, 200)
        self.assertEqual(self.client.post('/api/tasks/create', headers=self.admin,
                         json={'video_id': 'v', 'highlights': [1]}).status_code, 200)
        self.assertEqual(self.claim(self.admin).status_code, 403)

    def test_foreign_origin_refused(self):
        headers = {**self.admin, 'Origin': 'https://attacker.example'}
        self.assertEqual(self.client.post('/api/tasks/create', headers=headers,
                         json={'video_id': 'v', 'highlights': [1]}).status_code, 403)

    def test_health_and_no_store(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_claim_is_atomic(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            tasks = list(pool.map(lambda n: self.queue.claim_pending_task(str(n)), range(20)))
        self.assertEqual(sum(task is not None for task in tasks), 1)

    def test_bad_or_missing_configuration_rejected(self):
        for key in self.config:
            with self.subTest(key=key), self.assertRaises(ValueError):
                install_task_access(Flask(__name__), {**self.config, key: ''})
        with self.assertRaises(ValueError):
            install_task_access(Flask(__name__), {**self.config, 'CLIPPER_WORKER_TOKENS':
                                json.dumps({'one': 'b'*48, 'two': 'b'*48})})

    def test_error_completion_and_invalid_payload(self):
        self.assertEqual(self.client.post('/api/tasks/pending', headers=self.one, json=[]).status_code, 400)
        self.claim()
        self.assertEqual(self.client.post('/api/tasks/error', headers=self.one,
                         json={'task_id': self.task.task_id, 'error': 'failed'}).status_code, 200)
        self.assertEqual(self.task.status, 'failed')

    def test_worker_http_contract_without_loading_video_dependencies(self):
        source = ast.parse(Path('local_worker.py').read_text(encoding='utf-8'))
        functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('get_pending_task', 'notify_completion', 'notify_error')]
        requests = SimpleNamespace(post=Mock(return_value=SimpleNamespace(status_code=200,
                                   json=lambda: {'success': True, 'task': {'task_id': 'example'}})),
                                   exceptions=SimpleNamespace(Timeout=TimeoutError))
        context = {'requests': requests, 'logger': Mock(), 'RENDER_API_URL': 'https://clipper.example',
                   'WORKER_ID': 'one', 'WORKER_HEADERS': self.one}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'worker-contract', 'exec'), context)
        self.assertEqual(context['get_pending_task'](), {'task_id': 'example'})
        context['notify_completion']('example', 'output.mp4')
        context['notify_error']('example', 'failed')
        self.assertEqual(requests.post.call_count, 3)
        for call, suffix in zip(requests.post.call_args_list, ('pending', 'complete', 'error')):
            self.assertEqual(call.args[0], 'https://clipper.example/api/tasks/' + suffix)
            self.assertEqual(call.kwargs['headers'], self.one)
            self.assertFalse(call.kwargs['allow_redirects'])
            self.assertEqual(call.kwargs['json']['worker_id'], 'one')


if __name__ == '__main__':
    unittest.main()
