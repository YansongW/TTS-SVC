import os
import json
import shutil
from typing import Dict, List, Optional
from config import SVC_DIR
from scripts.path_utils import normalize_path, ensure_directory
import logging

# 添加日志配置
logger = logging.getLogger(__name__)

class SVCModelLibrary:
    """SVC模型库管理器"""
    def __init__(self):
        self.model_dir = 'logs/44k'
        self.config_dir = 'configs'
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
    def get_available_models(self) -> List[Dict]:
        """获取可用的模型列表"""
        models = []
        for model_name in os.listdir(self.model_dir):
            if model_name.endswith('.pth'):
                config_path = os.path.join(
                    'configs',
                    model_name.replace('.pth', '.json')
                )
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = json.load(f)
                    models.append({
                        'name': model_name.replace('.pth', ''),
                        'path': os.path.join(self.model_dir, model_name),
                        'config_path': config_path,
                        'speaker_name': config.get('speaker_name', 'Unknown'),
                        'description': config.get('description', '')
                    })
        return models
        
    def add_model(self, model_path: str, config_path: str,
                 speaker_name: str, description: str = '') -> bool:
        """添加新模型到库中"""
        try:
            # 生成模型名称
            model_name = f"svc_{speaker_name}_{len(self.get_available_models())}"
            
            # 复制文件
            new_model_path = os.path.join(self.model_dir, f"{model_name}.pth")
            new_config_path = os.path.join('configs', f"{model_name}.json")
            
            shutil.copy2(model_path, new_model_path)
            
            # 更新配置
            with open(config_path) as f:
                config = json.load(f)
            config['speaker_name'] = speaker_name
            config['description'] = description
            
            with open(new_config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            return True
        except Exception as e:
            logger.error(f"Failed to add model: {str(e)}")
            return False
            
    def remove_model(self, model_name: str) -> bool:
        """从库中移除模型"""
        try:
            model_path = os.path.join(self.model_dir, f"{model_name}.pth")
            config_path = os.path.join('configs', f"{model_name}.json")
            
            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(config_path):
                os.remove(config_path)
                
            return True
        except Exception as e:
            logger.error(f"Failed to remove model: {str(e)}")
            return False 