from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, jsonify
from .models import Task, BatchTask, db
from .tasks import process_task, process_batch_task
import os
import json
from werkzeug.utils import secure_filename
import logging
from config import ALLOWED_EXTENSIONS
from .model_library import SVCModelLibrary
from .trainer import SVCTrainer

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

@main.route('/')
def index():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    batches = BatchTask.query.order_by(BatchTask.created_at.desc()).all()
    return render_template('index.html', tasks=tasks, batches=batches)

@main.route('/upload_batch', methods=['GET', 'POST'])
def upload_batch():
    if request.method == 'POST':
        try:
            batch_name = request.form['batch_name']
            texts = request.files['texts_file'].read().decode('utf-8').splitlines()
            params_json = request.form['params']
            params = json.loads(params_json)
            
            # 创建批量任务
            batch = BatchTask(
                name=batch_name,
                total_tasks=len(texts) * len(params)
            )
            db.session.add(batch)
            db.session.commit()
            
            # 创建子任务
            for text in texts:
                for param in params:
                    task = Task(
                        text=text.strip(),
                        pitch=float(param.get('pitch', 1.0)),
                        speed=float(param.get('speed', 1.0)),
                        melody=param.get('melody', 'default'),
                        batch_id=batch.id
                    )
                    db.session.add(task)
            
            db.session.commit()
            
            # 启动批量处理
            process_batch_task.delay(batch.id)
            
            return redirect(url_for('main.index'))
            
        except Exception as e:
            return f"Error: {str(e)}", 400
            
    return render_template('upload_batch.html')

@main.route('/status/<int:task_id>')
def task_status(task_id):
    """获取单个任务状态"""
    task = Task.query.get_or_404(task_id)
    return jsonify({
        'status': task.status,
        'error': task.error_message
    })

@main.route('/batch_status/<int:batch_id>')
def batch_status(batch_id):
    """获取批量任务状态"""
    batch = BatchTask.query.get_or_404(batch_id)
    return jsonify({
        'status': batch.status,
        'progress': batch.progress,
        'completed': batch.completed_tasks,
        'total': batch.total_tasks
    })

@main.route('/download/<int:task_id>/<file_type>')
def download(task_id, file_type):
    task = Task.query.get_or_404(task_id)
    
    if file_type == 'tts':
        if not task.tts_output:
            return "TTS file not ready", 404
        filename = os.path.basename(task.tts_output)
        directory = os.path.dirname(task.tts_output)
    elif file_type == 'svc':
        if not task.svc_output:
            return "SVC file not ready", 404
        filename = os.path.basename(task.svc_output)
        directory = os.path.dirname(task.svc_output)
    else:
        return "Invalid file type", 400
        
    return send_from_directory(directory, filename, as_attachment=True) 

def validate_text_input(text):
    """验证文本输入"""
    if not text or len(text.strip()) == 0:
        raise ValueError("Text cannot be empty")
    if len(text) > 1000:  # 设置合理的长度限制
        raise ValueError("Text too long")
    return text.strip()

def validate_params(pitch, speed):
    """验证参数"""
    try:
        pitch = float(pitch)
        speed = float(speed)
        if not (0.5 <= pitch <= 2.0 and 0.5 <= speed <= 2.0):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Invalid pitch or speed value")
    return pitch, speed

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
        
    try:
        # 验证文本
        text = validate_text_input(request.form.get('text', ''))
        
        # 验证参数
        pitch = request.form.get('pitch', 1.0)
        speed = request.form.get('speed', 1.0)
        pitch, speed = validate_params(pitch, speed)
        
        # 创建任务
        task = Task(
            text=text,
            pitch=pitch,
            speed=speed,
            melody=request.form.get('melody', 'default')
        )
        db.session.add(task)
        db.session.commit()
        
        # 启动处理
        process_task.delay(task.id)
        
        return jsonify({'task_id': task.id}), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 

@main.route('/models')
def list_models():
    """列出可用模型"""
    model_library = SVCModelLibrary()
    models = model_library.get_available_models()
    return render_template('models.html', models=models)

@main.route('/train', methods=['GET', 'POST'])
def train_model():
    """训练新模型"""
    if request.method == 'POST':
        try:
            # 获取音频文件
            audio_file = request.files['audio']
            if not audio_file:
                return jsonify({'error': 'No audio file'}), 400
                
            # 获取配置
            speaker_name = request.form.get('speaker_name')
            if not speaker_name:
                return jsonify({'error': 'No speaker name'}), 400
                
            config = {
                'speaker_name': speaker_name,
                'description': request.form.get('description', ''),
                'epochs': int(request.form.get('epochs', 100)),
                'batch_size': int(request.form.get('batch_size', 16)),
                'learning_rate': float(request.form.get('learning_rate', 0.0001))
            }
            
            # 保存音频文件
            audio_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                secure_filename(audio_file.filename)
            )
            audio_file.save(audio_path)
            
            # 准备训练
            trainer = SVCTrainer()
            train_dir = trainer.prepare_training_data(audio_path, speaker_name)
            
            # 开始训练
            result = trainer.train_model(train_dir, config)
            if result:
                return jsonify({
                    'status': 'success',
                    'model_path': result['model_path']
                })
            else:
                return jsonify({'error': 'Training failed'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return render_template('train.html') 

@main.route('/train/progress/<train_id>')
def training_progress(train_id):
    """获取训练进度"""
    try:
        trainer = SVCTrainer()
        progress = trainer.get_training_progress(train_id)
        return jsonify(progress)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'progress': 0,
            'message': str(e)
        }), 500