import os
import time
from datetime import datetime, timedelta
from app import create_app
from app.models import Task, BatchTask, db
from config import TTS_OUTPUT_DIR, SVC_OUTPUT_DIR, MAX_STORAGE_DAYS

def cleanup_old_files():
    """清理旧文件"""
    app = create_app()
    with app.app_context():
        # 获取过期时间
        expiry_date = datetime.now() - timedelta(days=MAX_STORAGE_DAYS)
        
        # 清理过期任务
        old_tasks = Task.query.filter(Task.created_at < expiry_date).all()
        for task in old_tasks:
            # 清理文件
            if task.tts_output and os.path.exists(task.tts_output):
                os.remove(task.tts_output)
            if task.svc_output and os.path.exists(task.svc_output):
                os.remove(task.svc_output)
            
            # 删除数据库记录
            db.session.delete(task)
        
        # 清理空的批量任务
        BatchTask.query.filter(
            BatchTask.created_at < expiry_date,
            ~BatchTask.tasks.any()
        ).delete()
        
        db.session.commit()

if __name__ == '__main__':
    cleanup_old_files() 