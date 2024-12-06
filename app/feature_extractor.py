import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Dict
from config import HUBERT_CONFIG
import librosa

class HubertExtractor:
    """Hubert特征提取器"""
    def __init__(self, model: Dict, device: torch.device):
        self.model = model
        self.device = device
        self.sample_rate = HUBERT_CONFIG['sample_rate']
        self.hop_length = HUBERT_CONFIG['hop_length']
        
    def extract_features(self, audio: np.ndarray) -> torch.Tensor:
        """提取特征"""
        # 转换为tensor
        audio_tensor = torch.FloatTensor(audio).unsqueeze(0).to(self.device)
        
        # 提取特征
        with torch.no_grad():
            features = self.model.extract_features(audio_tensor)[0]
            features = features.transpose(1, 2)  # [B, T, D]
            
        return features
        
    def process_long_audio(self, audio: np.ndarray, chunk_size: int = 160000) -> torch.Tensor:
        """处理长音频"""
        # 分割音频
        chunks = []
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            if len(chunk) < chunk_size:
                # 填充最后一个块
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            chunks.append(chunk)
            
        # 提取特征
        features = []
        for chunk in chunks:
            feat = self.extract_features(chunk)
            features.append(feat)
            
        # 合并特征
        features = torch.cat(features, dim=1)
        return features

class ContentVecExtractor:
    """ContentVec特征提取器"""
    def __init__(self, model_path: str, device: torch.device):
        self.model = self._load_model(model_path).to(device)
        self.device = device
        self.model.eval()
        
    def _load_model(self, model_path: str):
        """加载模型"""
        from fairseq import checkpoint_utils
        models, cfg, task = checkpoint_utils.load_model_ensemble_and_task([model_path])
        model = models[0]
        model.remove_prenet()  # 移除预训练网络
        return model
        
    @torch.no_grad()
    def extract_features(self, audio: torch.Tensor) -> torch.Tensor:
        """提取特征"""
        # 添加填充
        padding_mask = torch.BoolTensor(audio.shape).fill_(False)
        inputs = {
            'source': audio.to(self.device),
            'padding_mask': padding_mask.to(self.device),
            'output_layer': 12,  # 使用第12层特征
        }
        
        # 提取特征
        features = self.model.extract_features(**inputs)
        return features[0]
        
    def process_audio(self, audio_path: str) -> torch.Tensor:
        """处理音频文件"""
        # 加载音频
        audio, sr = librosa.load(audio_path, sr=16000)  # ContentVec需要16kHz
        audio = torch.FloatTensor(audio).unsqueeze(0)
        
        # 提取特征
        features = self.extract_features(audio)
        return features

class HubertSoftExtractor:
    """HubertSoft特征提取器"""
    def __init__(self, model_path: str, device: torch.device):
        self.model = torch.jit.load(model_path).to(device)
        self.device = device
        self.model.eval()
        
    @torch.no_grad()
    def extract_features(self, audio: torch.Tensor) -> torch.Tensor:
        """提取特征"""
        # 添加批次维度
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
            
        # 提取特征
        features = self.model(audio)
        return features
        
    def process_audio(self, audio_path: str) -> torch.Tensor:
        """处理音频文件"""
        # 加载音频
        audio, sr = librosa.load(audio_path, sr=16000)  # HubertSoft需要16kHz
        audio = torch.FloatTensor(audio)
        
        # 提取特征
        features = self.extract_features(audio)
        return features

class WhisperPPGExtractor:
    """Whisper PPG特征提取器"""
    def __init__(self, model_path: str, device: torch.device):
        import whisper
        self.model = whisper.load_model(model_path).to(device)
        self.device = device
        self.model.eval()
        
    @torch.no_grad() 
    def extract_features(self, audio: torch.Tensor) -> torch.Tensor:
        """提取特征"""
        # Whisper的特征提取
        mel = self.model.mel_filters(audio)
        features = self.model.encoder(mel)
        return features
        
    def process_audio(self, audio_path: str) -> torch.Tensor:
        """处理音频文件"""
        # 加载音频
        audio = whisper.load_audio(audio_path)
        audio = torch.FloatTensor(audio)
        
        # 提取特征
        features = self.extract_features(audio)
        return features
