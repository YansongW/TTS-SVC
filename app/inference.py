import os
import torch
import numpy as np
import librosa
import soundfile as sf
import json
from typing import Optional, Dict, Any, List
from .model_manager import ModelManager
from .audio_processor import AudioProcessor
from config import (
    HUBERT_CONFIG, SVC_MODEL_PATH, SVC_CONFIG_PATH,
    SVC_INFERENCE_CONFIG
)
from .f0_predictor import F0Predictor
from .feature_extractor import HubertExtractor
import logging

logger = logging.getLogger(__name__)

class SVCInference:
    """SVC推理接口"""
    def __init__(self, model_path: str, config_path: str):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.load_model(model_path, config_path)
        self.config = self.load_config(config_path)
        self.hubert = self.load_hubert()
        self.f0_predictor = F0Predictor()
        
    def load_model(self, model_path: str, config_path: str):
        """加载模型"""
        # 加载配置
        with open(config_path) as f:
            config = json.load(f)
            
        # 初始化模型
        model = SynthesizerTrn(
            **config['model']
        ).to(self.device)
        
        # 加载权重
        model.load_state_dict(
            torch.load(model_path, map_location=self.device)['model']
        )
        model.eval()
        return model
        
    def infer(self, audio_path: str, 
              output_path: str,
              speaker_id: int = 0,
              pitch_adjust: float = 0) -> bool:
        """执行推理"""
        try:
            # 加载音频
            audio, sr = librosa.load(audio_path, sr=self.config['audio']['sample_rate'])
            
            # 提取特征
            with torch.no_grad():
                # 提取内容特征
                c = self.extract_features(audio)
                # 提取F0
                f0 = self.extract_f0(audio, pitch_adjust)
                
                # 生成
                audio = self.model.infer(
                    c, f0,
                    g=torch.LongTensor([speaker_id]).to(self.device)
                )[0,0].data.cpu().float().numpy()
                
            # 保存结果
            sf.write(output_path, audio, self.config['audio']['sample_rate'])
            return True
            
        except Exception as e:
            logger.error(f"Inference failed: {str(e)}")
            return False
        
    def load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path) as f:
            return json.load(f)
            
    def load_hubert(self):
        """加载HuBERT模型"""
        from fairseq import checkpoint_utils
        hubert_path = os.path.join('pretrain', 'hubert-soft-0d54a1f4.pt')
        models, cfg, task = checkpoint_utils.load_model_ensemble_and_task([hubert_path])
        return models[0].to(self.device)
        
    def extract_features(self, audio: np.ndarray) -> torch.Tensor:
        """提取特征"""
        with torch.no_grad():
            audio = torch.FloatTensor(audio).unsqueeze(0).to(self.device)
            feats = self.hubert.extract_features(audio, padding_mask=None, mask=False)[0]
            return feats.transpose(1, 2)
            
    def extract_f0(self, audio: np.ndarray, pitch_adjust: float = 0) -> torch.Tensor:
        """提取F0"""
        f0 = self.f0_predictor.compute_f0_with_pitch_shift(audio, pitch_adjust)
        return torch.FloatTensor(f0).unsqueeze(0).to(self.device)