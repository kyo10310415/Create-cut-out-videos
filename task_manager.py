"""
タスク管理モジュール
Renderでのタスクキュー管理とローカルワーカーとの連携
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
import json


class Task:
    """処理タスク"""
    
    def __init__(self, video_id: str, video_title: str, highlights: List[Dict], channel_id: str = None):
        self.task_id = str(uuid.uuid4())
        self.video_id = video_id
        self.video_title = video_title
        self.highlights = highlights
        self.channel_id = channel_id
        self.status = 'pending'  # pending, processing, completed, failed
        self.worker_id = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.output_file = None
        self.error_message = None
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'task_id': self.task_id,
            'video_id': self.video_id,
            'video_title': self.video_title,
            'highlights': self.highlights,
            'channel_id': self.channel_id,
            'status': self.status,
            'worker_id': self.worker_id,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'output_file': self.output_file,
            'error_message': self.error_message
        }
    
    def start_processing(self, worker_id: str):
        """処理開始"""
        self.status = 'processing'
        self.worker_id = worker_id
        self.started_at = datetime.now().isoformat()
    
    def complete(self, output_file: str):
        """処理完了"""
        self.status = 'completed'
        self.output_file = output_file
        self.completed_at = datetime.now().isoformat()
    
    def fail(self, error_message: str):
        """処理失敗"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.now().isoformat()


class TaskQueue:
    """タスクキュー管理"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.pending_tasks: List[str] = []  # task_id のリスト
    
    def add_task(self, video_id: str, video_title: str, highlights: List[Dict], channel_id: str = None) -> Task:
        """タスクを追加"""
        task = Task(video_id, video_title, highlights, channel_id)
        self.tasks[task.task_id] = task
        self.pending_tasks.append(task.task_id)
        return task
    
    def get_pending_task(self) -> Optional[Task]:
        """処理待ちタスクを1つ取得"""
        if not self.pending_tasks:
            return None
        
        task_id = self.pending_tasks.pop(0)
        task = self.tasks.get(task_id)
        
        if task and task.status == 'pending':
            return task
        
        # タスクが見つからない、または既に処理済みの場合は次を試す
        return self.get_pending_task()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """タスクIDでタスクを取得"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """すべてのタスクを取得"""
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """ステータスでタスクをフィルタ"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return {
            'total': len(self.tasks),
            'pending': len([t for t in self.tasks.values() if t.status == 'pending']),
            'processing': len([t for t in self.tasks.values() if t.status == 'processing']),
            'completed': len([t for t in self.tasks.values() if t.status == 'completed']),
            'failed': len([t for t in self.tasks.values() if t.status == 'failed'])
        }


# グローバルタスクキュー
task_queue = TaskQueue()
