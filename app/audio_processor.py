import os
import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Optional, Tuple
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频处理器"""
    def __init__(self):
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.channels = AUDIO_CHANNELS
        
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """加载音频"""
        try:
            # 加载音频
            audio, sr = librosa.load(file_path, sr=None, mono=False)
            
            # 转换声道
            if len(audio.shape) > 1 and audio.shape[0] > 1:
                audio = librosa.to_mono(audio)
            elif len(audio.shape) == 1:
                audio = audio[np.newaxis, :]
                
            # 重采样
            if sr != self.sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
                
            return audio, self.sample_rate
            
        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {str(e)}")
            raise
            
    def save_audio(self, audio: np.ndarray, file_path: str) -> bool:
        """保存音频"""
        try:
            sf.write(file_path, audio.T, self.sample_rate)
            return True
        except Exception as e:
            logger.error(f"Failed to save audio {file_path}: {str(e)}")
            return False
            
    def process_audio(self, audio: np.ndarray, 
                     normalize: bool = True,
                     trim_silence: bool = True) -> np.ndarray:
        """处理音频"""
        try:
            # 标准化音量
            if normalize:
                audio = librosa.util.normalize(audio)
                
            # 裁剪静音
            if trim_silence:
                audio, _ = librosa.effects.trim(audio, top_db=30)
                
            return audio
            
        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}")
            raise 