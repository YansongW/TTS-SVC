import os
from TTS.api import TTS
import subprocess
import uuid
import logging
from config import (
    TTS_MODEL_NAME, TTS_OUTPUT_DIR, 
    SVC_MODEL_PATH, SVC_CONFIG_PATH, SVC_OUTPUT_DIR,
    SVC_DIR, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    HUBERT_MODEL_PATH, SVC_INFERENCE_CONFIG
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
    
    # 检查必要的模型文件
    required_files = {
        'SVC model': SVC_MODEL_PATH,
        'SVC config': SVC_CONFIG_PATH,
        'Hubert model': HUBERT_MODEL_PATH
    }
    
    for name, path in required_files.items():
        if not os.path.exists(path):
            raise RuntimeError(f"{name} not found at {path}")
    
    # 验证模型文件
    try:
        import torch
        # 检查hubert模型
        hubert = torch.load(HUBERT_MODEL_PATH, map_location='cpu')
        if not isinstance(hubert, dict) or 'model' not in hubert:
            raise RuntimeError("Invalid hubert model file")
            
        # 检查SVC模型
        svc_model = torch.load(SVC_MODEL_PATH, map_location='cpu')
        if not isinstance(svc_model, dict):
            raise RuntimeError("Invalid SVC model file")
            
        # 检查CUDA
        if SVC_INFERENCE_CONFIG['device'].startswith('cuda'):
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available")
            logger.info(f"CUDA is available: {torch.cuda.get_device_name(0)}")
    except Exception as e:
        logger.error(f"Model validation failed: {str(e)}")
        raise

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

def convert_audio_format(input_path, output_format='wav'):
    """转换音频格式"""
    try:
        import soundfile as sf
        import librosa
        
        # 读取音频
        y, sr = librosa.load(input_path, sr=AUDIO_SAMPLE_RATE, mono=True)
        
        # 生成输出路径
        output_path = os.path.splitext(input_path)[0] + f'.{output_format}'
        
        # 保存为新格式
        sf.write(output_path, y, sr, format=output_format)
        
        return output_path
    except Exception as e:
        logger.error(f"Audio format conversion failed: {str(e)}")
        raise

def generate_tts(text, pitch, speed):
    """生成TTS音频"""
    global tts
    if tts is None:
        init_tts()
        
    try:
        unique_id = uuid.uuid4().hex
        temp_path = os.path.join(TTS_OUTPUT_DIR, f"temp_{unique_id}.wav")
        final_path = os.path.join(TTS_OUTPUT_DIR, f"tts_{unique_id}.wav")
        
        # 生成音频
        tts.tts_to_file(
            text=text,
            file_path=temp_path,
            speed=speed,
            pitch=pitch
        )
        
        # 验证临时文件
        if not os.path.exists(temp_path):
            raise Exception("TTS failed to generate audio file")
            
        # 转换格式并验证
        final_path = convert_audio_format(temp_path)
        check_file_size(final_path)
        validate_audio_file(final_path)
        
        # 清理临时文件
        cleanup_files(temp_path)
        
        return final_path
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        cleanup_files(temp_path, final_path)
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
            '--device', SVC_INFERENCE_CONFIG['device'],
            '--speaker_id', str(SVC_INFERENCE_CONFIG['speaker_id']),
            '--noise_scale', str(SVC_INFERENCE_CONFIG['noise_scale']),
            '--f0_method', SVC_INFERENCE_CONFIG['f0_method']
        ]
        
        if SVC_INFERENCE_CONFIG['auto_predict_f0']:
            svc_command.append('--auto_predict_f0')
            
        if SVC_INFERENCE_CONFIG['cluster_model_path']:
            svc_command.extend(['--cluster_model_path', 
                              SVC_INFERENCE_CONFIG['cluster_model_path']])
        
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
            
        check_file_size(svc_path)
        validate_audio_file(svc_path)
        
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