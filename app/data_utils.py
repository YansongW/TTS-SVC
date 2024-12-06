import os
import torch
import numpy as np
from torch.utils.data import Dataset
import random
from typing import Dict, List, Iterator
import librosa
from config import AUDIO_SAMPLE_RATE

class SVCDataset(Dataset):
    """SVC数据集"""
    def __init__(self, root_dir: str, segment_size: int = 8192):
        self.root_dir = root_dir
        self.segment_size = segment_size
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> List[Dict]:
        """加载元数据"""
        metadata = []
        with open(os.path.join(self.root_dir, 'train.txt')) as f:
            for line in f:
                # 解析文件路径
                path = line.strip()
                segment_dir = os.path.dirname(path)
                
                # 加载特征文件路径
                metadata.append({
                    'audio_path': os.path.join(self.root_dir, path),
                    'mel_path': os.path.join(self.root_dir, segment_dir, 'mel.npy'),
                    'f0_path': os.path.join(self.root_dir, segment_dir, 'f0.npy')
                })
        return metadata
        
    def __len__(self):
        return len(self.metadata)
        
    def __getitem__(self, idx) -> Dict:
        """获取数据项"""
        item = self.metadata[idx]
        
        # 加载音频和特征
        audio, _ = librosa.load(item['audio_path'], sr=AUDIO_SAMPLE_RATE)
        mel = np.load(item['mel_path'])
        f0 = np.load(item['f0_path'])
        
        # 随机裁剪
        if len(audio) > self.segment_size:
            start = random.randint(0, len(audio) - self.segment_size)
            end = start + self.segment_size
            
            audio = audio[start:end]
            mel = mel[:, start//512:end//512]
            f0 = f0[start//512:end//512]
            
        # 转换为tensor
        audio = torch.FloatTensor(audio)
        mel = torch.FloatTensor(mel)
        f0 = torch.FloatTensor(f0)
        
        return {
            'audio': audio,
            'mel': mel,
            'f0': f0,
            'path': item['audio_path']
        }
        
    def get_batch(self, batch_size: int) -> Iterator[Dict[str, torch.Tensor]]:
        """获取批次数据"""
        indices = list(range(len(self)))
        random.shuffle(indices)
        
        for i in range(0, len(self), batch_size):
            batch_indices = indices[i:i + batch_size]
            batch = [self[idx] for idx in batch_indices]
            
            # 合并批次
            audio = torch.stack([item['audio'] for item in batch])
            mel = torch.stack([item['mel'] for item in batch])
            f0 = torch.stack([item['f0'] for item in batch])
            
            yield {
                'audio': audio,
                'mel': mel,
                'f0': f0,
                'paths': [item['path'] for item in batch]
            } 