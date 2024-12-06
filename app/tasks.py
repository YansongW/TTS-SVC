from . import celery, db
from .models import Task, BatchTask
from .utils import generate_tts, apply_svc, cleanup_files
import logging
import traceback
from celery.exceptions import SoftTimeLimitExceeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery.task(bind=True)
def process_task(self, task_id, batch_id=None):
    """处理单个任务"""
    task = Task.query.get(task_id)
    if not task:
        logger.error(f"Task ID {task_id} not found.")
        return
    
    try:
        # TTS处理
        task.status = 'Processing TTS'
        db.session.commit()
        
        tts_path = generate_tts(task.text, task.pitch, task.speed)
        task.tts_output = tts_path
        db.session.commit()
        
        # SVC处理
        task.status = 'Processing SVC'
        db.session.commit()
        
        svc_path = apply_svc(tts_path, task.melody)
        task.svc_output = svc_path
        
        task.status = 'Completed'
        db.session.commit()
        
        logger.info(f"Task ID {task_id} completed successfully.")
        
        # 更新批量任务进度
        if batch_id:
            batch = BatchTask.query.get(batch_id)
            if batch:
                batch.completed_tasks += 1
                batch.update_progress()
                if batch.completed_tasks == batch.total_tasks:
                    batch.status = 'Completed'
                db.session.commit()
        
    except SoftTimeLimitExceeded:
        error_msg = "Task exceeded time limit"
        task.status = 'Error'
        task.error_message = error_msg
        db.session.commit()
        logger.error(error_msg)
        cleanup_files(task.tts_output, task.svc_output)
        
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        task.status = 'Error'
        task.error_message = error_msg
        db.session.commit()
        logger.error(error_msg)
        cleanup_files(task.tts_output, task.svc_output)
        
        # 如果是批量任务的一部分，更新批量任务状态
        if batch_id:
            try:
                batch = BatchTask.query.get(batch_id)
                if batch:
                    batch.status = 'Error'
                    db.session.commit()
            except Exception as be:
                logger.error(f"Failed to update batch status: {str(be)}")

@celery.task(bind=True)
def process_batch_task(self, batch_id):
    """处理批量任务"""
    batch = BatchTask.query.get(batch_id)
    if not batch:
        logger.error(f"Batch ID {batch_id} not found.")
        return
    
    try:
        batch.status = 'Processing'
        db.session.commit()
        
        # 处理每个子任务
        for task in batch.tasks:
            process_task.delay(task.id, batch_id)
        
        logger.info(f"Batch ID {batch_id} started processing.")
        
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        batch.status = 'Error'
        db.session.commit()
        logger.error(error_msg)