import os
import stat
import logging
from typing import List, Dict
from cryptography.fernet import Fernet
from config import SECURITY_CONFIG, DATA_DIR
from scripts.path_utils import normalize_path, ensure_directory
import hashlib
import yaml

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        self.key_file = normalize_path(SECURITY_CONFIG['key_file'])
        self.min_key_length = SECURITY_CONFIG['min_key_length']
        
    def check_file_permissions(self, path: str) -> bool:
        """检查文件权限"""
        try:
            path = normalize_path(path)
            stat_info = os.stat(path)
            if stat_info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                logger.error(f"Unsafe permissions on {path}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check permissions: {str(e)}")
            return False
            
    def generate_key(self) -> bytes:
        """生成新的加密密钥"""
        return Fernet.generate_key()
        
    def save_key(self, key: bytes) -> bool:
        """安全保存密钥"""
        try:
            # 确保目录存在
            ensure_directory(os.path.dirname(self.key_file))
            # 设置安全的文件权限
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, SECURITY_CONFIG['file_permissions'])
            return True
        except Exception as e:
            logger.error(f"Failed to save key: {str(e)}")
            return False
            
    def load_key(self) -> bytes:
        """加载密钥"""
        try:
            if not os.path.exists(self.key_file):
                key = self.generate_key()
                self.save_key(key)
                return key
                
            with open(self.key_file, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load key: {str(e)}")
            raise
            
    def encrypt_value(self, value: str) -> str:
        """加密值"""
        try:
            f = Fernet(self.load_key())
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
            
    def decrypt_value(self, encrypted: str) -> str:
        """解密值"""
        try:
            f = Fernet(self.load_key())
            return f.decrypt(encrypted.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

def calculate_file_hash(file_path: str) -> str:
    """计算文件哈希值"""
    sha256_hash = hashlib.sha256()
    try:
        with open(normalize_path(file_path), "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {str(e)}")
        raise

def verify_file_integrity(file_path: str, expected_hash: str) -> bool:
    """验证文件完整性"""
    try:
        current_hash = calculate_file_hash(file_path)
        return current_hash == expected_hash
    except Exception:
        return False

class ConfigValidator:
    """配置验证器"""
    def __init__(self, config_file: str):
        self.config_file = normalize_path(config_file)
        
    def validate_yaml(self) -> bool:
        """验证YAML文件格式"""
        try:
            with open(self.config_file) as f:
                yaml.safe_load(f)
            return True
        except Exception as e:
            logger.error(f"Invalid YAML format in {self.config_file}: {str(e)}")
            return False
            
    def validate_required_fields(self, required_fields: Dict) -> bool:
        """验证必需字段"""
        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                
            for section, fields in required_fields.items():
                if section not in config:
                    logger.error(f"Missing section: {section}")
                    return False
                for field in fields:
                    if field not in config[section]:
                        logger.error(f"Missing field: {section}.{field}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Failed to validate config: {str(e)}")
            return False

def check_security():
    """执行安全检查"""
    security = SecurityManager()
    
    # 检查关键目录权限
    critical_dirs = [
        DATA_DIR,
        os.path.dirname(SECURITY_CONFIG['key_file']),
        'so-vits-svc/models',
        'so-vits-svc/configs'
    ]
    
    for dir_path in critical_dirs:
        dir_path = normalize_path(dir_path)
        if not security.check_file_permissions(dir_path):
            raise RuntimeError(f"Insecure directory permissions: {dir_path}")
            
    # 检查配置文件
    config_validator = ConfigValidator('config/monitor.yml')
    if not config_validator.validate_yaml():
        raise RuntimeError("Invalid monitor.yml format")
        
    required_fields = {
        'intervals': ['check', 'cleanup'],
        'thresholds': ['cpu', 'memory', 'disk'],
        'process_priority': [],
        'process_limits': []
    }
    
    if not config_validator.validate_required_fields(required_fields):
        raise RuntimeError("Missing required fields in monitor.yml")
        
    # 检查密钥文件
    if not os.path.exists(security.key_file):
        logger.warning("Key file not found, generating new key")
        security.generate_key()
    elif not security.check_file_permissions(security.key_file):
        raise RuntimeError("Insecure key file permissions")
        
    return True

if __name__ == '__main__':
    try:
        check_security()
        logger.info("Security check passed")
    except Exception as e:
        logger.error(f"Security check failed: {str(e)}")
        exit(1) 