import os
import logging
import hashlib
import requests
from tqdm import tqdm
from typing import Optional
from config import HUBERT_CONFIG, SVC_MODEL_PATH, SVC_CONFIG_PATH
from scripts.path_utils import normalize_path, ensure_directory

logger = logging.getLogger(__name__)

class ModelManager:
    """模型管理器"""
    def __init__(self):
        self.model_urls = {
            'hubert': HUBERT_CONFIG['download_url'],
            'contentvec': 'https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt'
        }
        
    def download_file(self, url: str, save_path: str) -> bool:
        """下载文件"""
        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            save_path = normalize_path(save_path)
            ensure_directory(os.path.dirname(save_path))
            
            with open(save_path, 'wb') as f, tqdm(
                desc=os.path.basename(save_path),
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {str(e)}")
            return False
            
    def verify_model(self, model_path: str, expected_hash: Optional[str] = None) -> bool:
        """验证模型文件"""
        try:
            if not os.path.exists(model_path):
                return False
                
            if expected_hash:
                # 计算文件哈希
                sha256_hash = hashlib.sha256()
                with open(model_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                actual_hash = sha256_hash.hexdigest()
                
                if actual_hash != expected_hash:
                    logger.error(f"Hash mismatch for {model_path}")
                    return False
                    
            # 尝试加载模型验证格式
            import torch
            model_data = torch.load(model_path, map_location='cpu')
            
            # 验证模型结构
            if 'model' not in model_data and 'state_dict' not in model_data:
                raise ValueError("Invalid model format")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify model {model_path}: {str(e)}")
            return False
            
    def prepare_models(self) -> bool:
        """准备所有必要的模型"""
        try:
            # 下载hubert模型
            hubert_path = HUBERT_CONFIG['model_path']
            if not os.path.exists(hubert_path):
                logger.info("Downloading hubert model...")
                if not self.download_file(self.model_urls['hubert'], hubert_path):
                    raise RuntimeError("Failed to download hubert model")
                    
            # 验证hubert模型
            if not self.verify_model(hubert_path):
                raise RuntimeError("Invalid hubert model")
                
            # 检查SVC模型
            if not os.path.exists(SVC_MODEL_PATH):
                raise RuntimeError(
                    "SVC model not found. Please download from: "
                    "https://github.com/svc-develop-team/so-vits-svc/releases"
                )
                
            # 验证SVC模型
            if not self.verify_model(SVC_MODEL_PATH):
                raise RuntimeError("Invalid SVC model")
                
            # 检查配置文件
            if not os.path.exists(SVC_CONFIG_PATH):
                raise RuntimeError("SVC config not found")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare models: {str(e)}")
            return False 