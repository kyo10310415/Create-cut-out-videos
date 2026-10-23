"""Task endpoints without heavyweight video-processing imports."""
from flask import Blueprint, g, jsonify, request


def create_task_api(task_queue):
    api = Blueprint('tasks', __name__)

    @api.post('/api/tasks/create')
    def create():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data.get('video_id') or not data.get('highlights'):
            return jsonify(success=False, error='Required parameters missing'), 400
        task = task_queue.add_task(data['video_id'], data.get('video_title', ''),
                                   data['highlights'], data.get('channel_id'))
        return jsonify(success=True, task=task.to_dict())

    @api.post('/api/tasks/pending')
    def claim():
        task = task_queue.claim_pending_task(g.worker_id)
        return jsonify(success=True, task=task.to_dict() if task else None)

    @api.post('/api/tasks/complete')
    def complete():
        return finish('output_file', 'completed')

    @api.post('/api/tasks/error')
    def error():
        return finish('error', 'failed')

    def finish(value_key, status):
        data = request.get_json(silent=True)
        value = data.get(value_key)
        if not isinstance(data.get('task_id'), str) or not isinstance(value, str) or not value:
            return jsonify(success=False, error='Required parameters missing'), 400
        task, failure = task_queue.finish_task(data['task_id'], g.worker_id, status, value)
        if failure:
            return jsonify(success=False, error='Task update rejected'), failure
        return jsonify(success=True, task=task.to_dict())

    @api.get('/api/tasks/list')
    def list_tasks():
        try:
            limit = int(request.args.get('limit', 50))
            if not 1 <= limit <= 500:
                raise ValueError()
        except ValueError:
            return jsonify(success=False, error='Invalid limit'), 400
        status = request.args.get('status')
        tasks = task_queue.get_tasks_by_status(status) if status else task_queue.get_all_tasks()
        tasks = sorted(tasks, key=lambda task: task.created_at, reverse=True)[:limit]
        return jsonify(success=True, tasks=[task.to_dict() for task in tasks], stats=task_queue.get_stats())

    @api.get('/api/tasks/<task_id>')
    def get(task_id):
        task = task_queue.get_task(task_id)
        if not task:
            return jsonify(success=False, error='Task not found'), 404
        return jsonify(success=True, task=task.to_dict())

    return api
