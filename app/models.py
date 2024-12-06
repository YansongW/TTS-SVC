from . import db
from datetime import datetime

class BatchTask(db.Model):
    """批量任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    progress = db.Column(db.Integer, default=0)  # 进度百分比
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='batch', lazy=True)
    
    def update_progress(self):
        """更新进度"""
        if self.total_tasks > 0:
            self.progress = int((self.completed_tasks / self.total_tasks) * 100)
        else:
            self.progress = 0
        db.session.commit()

class Task(db.Model):
    """单个任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    pitch = db.Column(db.Float, default=1.0)
    speed = db.Column(db.Float, default=1.0) 
    melody = db.Column(db.String(50), default='default')
    status = db.Column(db.String(20), default='Pending')
    error_message = db.Column(db.Text)  # 错误信息
    tts_output = db.Column(db.String(200))
    svc_output = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch_task.id'), nullable=True)
    
    def __repr__(self):
        return f'<Task {self.id}>'