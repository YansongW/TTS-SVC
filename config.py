import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础路径配置
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 创建必要的目录
for dir_path in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# TTS配置
TTS_MODEL_NAME = os.getenv('TTS_MODEL_NAME', 'tts_models/en/ljspeech/tacotron2-DDC')
TTS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'tts')
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

# SVC配置
SVC_DIR = os.path.join(BASE_DIR, 'so-vits-svc')
SVC_MODEL_PATH = os.getenv('SVC_MODEL_PATH', os.path.join(SVC_DIR, 'models', 'model.pth'))
SVC_CONFIG_PATH = os.getenv('SVC_CONFIG_PATH', os.path.join(SVC_DIR, 'configs', 'config.json'))
SVC_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'svc')
os.makedirs(SVC_OUTPUT_DIR, exist_ok=True)

# Redis配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Celery配置
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1小时超时
CELERY_TASK_SOFT_TIME_LIMIT = 3540  # 59分钟软超时

# Flask配置
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(DATA_DIR, "app.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# 清理配置
MAX_STORAGE_DAYS = int(os.getenv('MAX_STORAGE_DAYS', 7))  # 文件保存最大天数 

# SQLAlchemy配置
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}

# Celery详细配置
CELERY_CONFIG = {
    'broker_url': CELERY_BROKER_URL,
    'result_backend': CELERY_RESULT_BACKEND,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'Asia/Shanghai',
    'task_track_started': True,
    'task_time_limit': 3600,
    'task_soft_time_limit': 3540,
    'worker_max_tasks_per_child': 200,
    'worker_prefetch_multiplier': 4,
    'task_queue_max_priority': 10,
    'task_default_priority': 5,
    'task_acks_late': True,
    'task_reject_on_worker_lost': True,
    'task_annotations': {
        'app.tasks.process_task': {
            'rate_limit': '10/m',
            'max_retries': 3,
            'default_retry_delay': 60
        }
    }
}

# 文件上传配置
ALLOWED_EXTENSIONS = {'txt', 'json'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 音频文件配置
ALLOWED_AUDIO_FORMATS = {'wav', 'mp3'}
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1 

# 音频转换配置
AUDIO_FORMATS = {
    'input': ['wav', 'mp3', 'flac'],
    'output': 'wav'
}

# Hubert模型配置
HUBERT_MODEL_PATH = os.path.join(SVC_DIR, 'pretrain', 'hubert-soft-0d54a1f4.pt')

# SVC推理配置
SVC_INFERENCE_CONFIG = {
    'auto_predict_f0': False,
    'cluster_model_path': '',
    'speaker_id': int(os.getenv('SVC_SPEAKER_ID', 0)),
    'noise_scale': float(os.getenv('SVC_NOISE_SCALE', 0.4)),
    'f0_method': os.getenv('SVC_F0_METHOD', 'dio'),
    'device': os.getenv('SVC_DEVICE', 'cuda:0')
}

# 数据库备份配置
DB_BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
os.makedirs(DB_BACKUP_DIR, exist_ok=True)