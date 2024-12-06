import numpy as np
import torch
import pyworld
import parselmouth
import librosa
from typing import Optional, List, Union, Tuple
from config import SVC_INFERENCE_CONFIG

class F0Predictor:
    """F0预测器"""
    def __init__(self, method: str = 'dio'):
        self.method = method
        self.sample_rate = 44100  # 采样率
        self.hop_length = 512     # 帧移
        
    def compute_f0(self, audio: np.ndarray) -> np.ndarray:
        """计算F0"""
        if not isinstance(audio, np.ndarray):
            raise TypeError("Audio must be numpy array")
            
        if self.method == 'dio':
            return self._dio(audio)
        elif self.method == 'harvest':
            return self._harvest(audio)
        elif self.method == 'parselmouth':
            return self._parselmouth(audio)
        else:
            raise ValueError(f"Unsupported F0 method: {self.method}")
            
    def _dio(self, audio: np.ndarray) -> np.ndarray:
        """DIO算法"""
        f0, t = pyworld.dio(
            audio.astype(np.double),
            fs=self.sample_rate,
            f0_floor=50.0,
            f0_ceil=1100.0,
            frame_period=1000 * self.hop_length / self.sample_rate
        )
        f0 = pyworld.stonemask(audio.astype(np.double), f0, t, self.sample_rate)
        return f0
        
    def _harvest(self, audio: np.ndarray) -> np.ndarray:
        """Harvest算法"""
        f0, t = pyworld.harvest(
            audio.astype(np.double),
            fs=self.sample_rate,
            f0_floor=50.0,
            f0_ceil=1100.0,
            frame_period=1000 * self.hop_length / self.sample_rate
        )
        return f0
        
    def _parselmouth(self, audio: np.ndarray) -> np.ndarray:
        """Parselmouth算法"""
        sound = parselmouth.Sound(audio, self.sample_rate)
        pitch = sound.to_pitch_ac(
            time_step=self.hop_length / self.sample_rate,
            voicing_threshold=0.6,
            pitch_floor=50.0,
            pitch_ceiling=1100.0
        )
        pitch_values = np.array([
            pitch.get_value_at_time(t) if pitch.get_value_at_time(t) is not None
            else 0.0 for t in pitch.xs()
        ])
        return pitch_values
                        
    def compute_f0_with_pitch_shift(self, audio: np.ndarray, pitch_shift: float = 0) -> np.ndarray:
        """计算带音高偏移的F0"""
        f0 = self.compute_f0(audio)
        if pitch_shift != 0:
            f0 = f0 * 2 ** (pitch_shift / 12)  # 半音转换
        return f0 