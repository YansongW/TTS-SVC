from . import celery, db
from .models import Task, BatchTask
from .utils import generate_tts, apply_svc, cleanup_files
import logging
import traceback
from celery.exceptions import SoftTimeLimitExceeded
import os
from .inference import SVCInference
from config import SVC_OUTPUT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
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
            update_batch_progress.delay(batch_id)
        
    except (SoftTimeLimitExceeded, Exception) as e:
        error_msg = str(e)
        if isinstance(e, SoftTimeLimitExceeded):
            error_msg = "Task exceeded time limit"
        
        task.status = 'Error'
        task.error_message = f"Error: {error_msg}\n{traceback.format_exc()}"
        db.session.commit()
        
        logger.error(f"Task {task_id} failed: {error_msg}")
        cleanup_files(task.tts_output, task.svc_output)
        
        # 重试任务
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            if batch_id:
                update_batch_status.delay(batch_id, 'Error')

@celery.task
def update_batch_progress(batch_id):
    """更新批量任务进度"""
    try:
        batch = BatchTask.query.get(batch_id)
        if batch:
            completed_count = Task.query.filter_by(
                batch_id=batch_id,
                status='Completed'
            ).count()
            
            batch.completed_tasks = completed_count
            batch.update_progress()
            
            if batch.completed_tasks == batch.total_tasks:
                batch.status = 'Completed'
            
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to update batch progress: {str(e)}")

@celery.task
def update_batch_status(batch_id, status):
    """更新批量任务状态"""
    try:
        batch = BatchTask.query.get(batch_id)
        if batch:
            batch.status = status
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to update batch status: {str(e)}")

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
        
        # 初始化推理器
        inferencer = SVCInference()
        if not inferencer.load_models():
            raise RuntimeError("Failed to load models")
        
        # 处理每个子任务
        for task in batch.tasks:
            try:
                # 生成输出路径
                output_path = os.path.join(
                    SVC_OUTPUT_DIR,
                    f"svc_{task.id}.wav"
                )
                
                # 执行推理
                if inferencer.infer(
                    task.tts_output,
                    output_path,
                    pitch_shift=task.pitch,
                    speaker_id=0  # TODO: 支持多说话人
                ):
                    task.svc_output = output_path
                    task.status = 'Completed'
                else:
                    task.status = 'Error'
                    task.error_message = "Inference failed"
                    
                db.session.commit()
                
            except Exception as e:
                task.status = 'Error'
                task.error_message = str(e)
                db.session.commit()
                logger.error(f"Task {task.id} failed: {str(e)}")
                
        batch.status = 'Completed'
        db.session.commit()
        
    except Exception as e:
        batch.status = 'Error'
        db.session.commit()
        logger.error(f"Batch {batch_id} failed: {str(e)}")