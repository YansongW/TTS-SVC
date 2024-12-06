import os
from TTS.api import TTS
import subprocess
import uuid
import logging
from config import (
    TTS_MODEL_NAME, TTS_OUTPUT_DIR, 
    SVC_MODEL_PATH, SVC_CONFIG_PATH, SVC_OUTPUT_DIR,
    SVC_DIR, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
)

# 配置日志
logger = logging.getLogger(__name__)

# 全局TTS实例
tts = None

# 在文件开头添加
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def init_tts():
    """初始化TTS实例"""
    global tts
    try:
        tts = TTS(TTS_MODEL_NAME)
        logger.info("TTS initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize TTS: {str(e)}")
        raise

def setup_svc():
    """检查并设置so-vits-svc环境"""
    if not os.path.exists(SVC_DIR):
        raise RuntimeError(f"SVC directory not found at {SVC_DIR}")
    if not os.path.exists(SVC_MODEL_PATH):
        raise RuntimeError(f"SVC model not found at {SVC_MODEL_PATH}")
    if not os.path.exists(SVC_CONFIG_PATH):
        raise RuntimeError(f"SVC config not found at {SVC_CONFIG_PATH}")
    
    # 检查CUDA可用性
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available")
        logger.info(f"CUDA is available: {torch.cuda.get_device_name(0)}")
    except ImportError:
        raise RuntimeError("PyTorch is not installed")

def check_file_size(file_path):
    """检查文件大小"""
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        os.remove(file_path)
        raise ValueError(f"Generated file exceeds maximum size limit of {MAX_FILE_SIZE/1024/1024}MB")

def validate_audio_file(file_path):
    """验证音频文件"""
    try:
        import soundfile as sf
        data, samplerate = sf.read(file_path)
        
        # 检查采样率
        if samplerate != AUDIO_SAMPLE_RATE:
            raise ValueError(f"Invalid sample rate: {samplerate}")
            
        # 检查声道数
        if len(data.shape) > 1 and data.shape[1] != AUDIO_CHANNELS:
            raise ValueError(f"Invalid number of channels: {data.shape[1]}")
            
        return True
    except Exception as e:
        logger.error(f"Audio file validation failed: {str(e)}")
        raise

def get_safe_filename(filename):
    """生成安全的文件名"""
    import re
    from werkzeug.utils import secure_filename
    
    # 移除非ASCII字符
    filename = secure_filename(filename)
    # 只保留字母、数字、下划线和点
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # 确保文件名不为空
    if not filename:
        filename = str(uuid.uuid4())
    return filename

def generate_tts(text, pitch, speed):
    """生成TTS音频"""
    global tts
    if tts is None:
        init_tts()
        
    try:
        unique_id = uuid.uuid4().hex
        filename = get_safe_filename(f"tts_{unique_id}.wav")
        file_path = os.path.join(TTS_OUTPUT_DIR, filename)
        
        # 生成音频
        tts.tts_to_file(
            text=text,
            file_path=file_path,
            speed=speed,
            pitch=pitch
        )
        
        check_file_size(file_path)
        validate_audio_file(file_path)
        
        return file_path
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        cleanup_files(file_path)
        raise

def apply_svc(tts_path, melody):
    """应用SVC转换"""
    try:
        if not os.path.exists(tts_path):
            raise FileNotFoundError(f"TTS file not found: {tts_path}")
            
        unique_id = uuid.uuid4().hex
        filename = f"svc_{unique_id}.wav"
        svc_path = os.path.join(SVC_OUTPUT_DIR, filename)
        
        # 构建SVC处理命令
        svc_command = [
            'python',
            os.path.join(SVC_DIR, 'inference.py'),
            '--model', SVC_MODEL_PATH,
            '--config', SVC_CONFIG_PATH,
            '--input', tts_path,
            '--output', svc_path,
            '--melody', melody,
            '--device', 'cuda:0'
        ]
        
        # 执行SVC处理
        result = subprocess.run(
            svc_command,
            check=True,
            capture_output=True,
            text=True,
            cwd=SVC_DIR
        )
        
        if result.returncode != 0:
            raise Exception(f"SVC processing failed: {result.stderr}")
            
        if not os.path.exists(svc_path):
            raise Exception("SVC failed to generate audio file")
            
        check_file_size(svc_path)  # 添加文件大小检查
        
        return svc_path
    except Exception as e:
        logger.error(f"SVC processing failed: {str(e)}")
        raise

def cleanup_files(*file_paths):
    """清理临时文件"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"Cleaned up file: {path}")
            except Exception as e:
                logger.error(f"Failed to clean up file {path}: {str(e)}")