import os
import json
import logging
from typing import Dict, Any
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> bool:
    """验证配置文件"""
    required_fields = {
        'model': ['device', 'sampling_rate', 'hop_length'],
        'audio': ['sample_rate', 'channels'],
        'inference': ['speaker_id', 'noise_scale', 'f0_method']
    }
    
    # 检查必需字段
    for section, fields in required_fields.items():
        if section not in config:
            raise ValueError(f"Missing section: {section}")
        for field in fields:
            if field not in config[section]:
                raise ValueError(f"Missing field: {section}.{field}")
    
    # 验证值的合法性
    if not isinstance(config['model']['sampling_rate'], int):
        raise ValueError("sampling_rate must be an integer")
    if not isinstance(config['model']['hop_length'], int):
        raise ValueError("hop_length must be an integer")
    if not isinstance(config['audio']['channels'], int):
        raise ValueError("channels must be an integer")
    if not isinstance(config['inference']['noise_scale'], (int, float)):
        raise ValueError("noise_scale must be a number")
    
    return True

def validate_env_file(env_path: str) -> bool:
    """验证环境变量文件"""
    required_vars = [
        'TTS_MODEL_NAME',
        'REDIS_HOST',
        'REDIS_PORT',
        'FLASK_SECRET_KEY'
    ]
    
    with open(env_path) as f:
        env_content = f.read()
        
    # 检查必需变量
    for var in required_vars:
        if var not in env_content:
            raise ValueError(f"Missing environment variable: {var}")
    
    # 解析并验证值
    env_dict = {}
    for line in env_content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_dict[key.strip()] = value.strip()
    
    # 验证端口号
    try:
        port = int(env_dict.get('REDIS_PORT', ''))
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        raise ValueError("Invalid REDIS_PORT value")
    
    # 验证密钥长度
    if len(env_dict.get('FLASK_SECRET_KEY', '')) < 16:
        raise ValueError("FLASK_SECRET_KEY should be at least 16 characters long")
    
    return True

def validate_database_config(db_url: str) -> bool:
    """验证数据库配置"""
    try:
        parsed = urlparse(db_url)
        if parsed.scheme not in ['sqlite']:
            raise ValueError(f"Unsupported database type: {parsed.scheme}")
        
        if parsed.scheme == 'sqlite':
            db_path = parsed.path.lstrip('/')
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                raise ValueError(f"Database directory does not exist: {db_dir}")
            if os.path.exists(db_path) and not os.access(db_path, os.W_OK):
                raise ValueError(f"No write permission for database file: {db_path}")
    except Exception as e:
        raise ValueError(f"Invalid database URL: {str(e)}")
    
    return True

def check_file_permissions():
    """检查文件权限"""
    paths_to_check = [
        'data',
        'logs',
        'output',
        'so-vits-svc/models',
        'so-vits-svc/configs',
        'so-vits-svc/pretrain'
    ]
    
    for path in paths_to_check:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.access(path, os.W_OK):
            raise PermissionError(f"No write permission for: {path}")
            
    return True

def validate_all():
    """验证所有配置"""
    try:
        # 检查环境变量文件
        if os.path.exists('.env'):
            logger.info("验证环境变量文件...")
            validate_env_file('.env')
        else:
            raise FileNotFoundError(".env file not found")
            
        # 检查SVC配置文件
        logger.info("验证SVC配置文件...")
        svc_config_path = 'so-vits-svc/configs/config.json'
        if os.path.exists(svc_config_path):
            with open(svc_config_path) as f:
                config = json.load(f)
            validate_config(config)
            
        # 检查数据库配置
        logger.info("验证数据库配置...")
        from config import SQLALCHEMY_DATABASE_URI
        validate_database_config(SQLALCHEMY_DATABASE_URI)
            
        # 检查文件权限
        logger.info("检查文件权限...")
        check_file_permissions()
        
        logger.info("配置验证完成")
        return True
    except Exception as e:
        logger.error(f"配置验证失败: {str(e)}")
        return False

if __name__ == '__main__':
    if not validate_all():
        exit(1) 