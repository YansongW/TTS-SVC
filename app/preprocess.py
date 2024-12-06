import os
import librosa
import numpy as np
import soundfile as sf
from tqdm import tqdm
from config import AUDIO_SAMPLE_RATE
from .audio_processor import AudioProcessor
import pyworld
import random
import logging

logger = logging.getLogger(__name__)

def prepare_dataset(audio_path: str, output_dir: str):
    """准备训练数据集"""
    try:
        # 1. 创建必要的目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. 加载和预处理音频
        audio_processor = AudioProcessor()
        audio, sr = librosa.load(audio_path, sr=AUDIO_SAMPLE_RATE)
        
        # 3. 分割音频
        segments = split_audio(audio)
        logger.info(f"Split audio into {len(segments)} segments")
        
        # 4. 处理每个片段
        for i, segment in tqdm(enumerate(segments), desc="Processing segments"):
            # 标准化和去除静音
            segment = audio_processor.process_audio(
                segment,
                normalize=True,
                trim_silence=True
            )
            
            # 提取特征
            mel = extract_mel_spectrogram(segment)
            f0 = extract_f0(segment)
            
            # 保存文件
            segment_dir = os.path.join(output_dir, f"segment_{i:04d}")
            os.makedirs(segment_dir, exist_ok=True)
            
            # 保存音频
            sf.write(
                os.path.join(segment_dir, "audio.wav"),
                segment,
                AUDIO_SAMPLE_RATE
            )
            
            # 保存特征
            np.save(os.path.join(segment_dir, "mel.npy"), mel)
            np.save(os.path.join(segment_dir, "f0.npy"), f0)
            
        # 5. 生成文件列表
        create_filelist(output_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to prepare dataset: {str(e)}")
        return False

def extract_mel_spectrogram(audio: np.ndarray) -> np.ndarray:
    """提取mel频谱图"""
    # 使用so-vits-svc的mel参数
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=AUDIO_SAMPLE_RATE,
        n_fft=2048,
        hop_length=512,
        win_length=2048,
        n_mels=80,
        fmin=0,
        fmax=None,
        center=False
    )
    mel = librosa.power_to_db(mel, ref=1.0, top_db=80.0)
    return mel

def extract_f0(audio: np.ndarray) -> np.ndarray:
    """提取基频"""
    # 使用WORLD的dio算法
    f0, t = pyworld.dio(
        audio.astype(np.double),
        fs=AUDIO_SAMPLE_RATE,
        f0_floor=50.0,
        f0_ceil=1100.0,
        frame_period=5.0
    )
    f0 = pyworld.stonemask(audio.astype(np.double), f0, t, AUDIO_SAMPLE_RATE)
    return f0

def split_audio(audio: np.ndarray, 
                min_length: float = 2.0,
                max_length: float = 8.0) -> List[np.ndarray]:
    """切分音频"""
    # 参考so-vits-svc的切分参数
    segments = []
    
    # 使用能量检测分割
    intervals = librosa.effects.split(
        audio,
        top_db=30,
        frame_length=2048,
        hop_length=512
    )
    
    for start, end in intervals:
        segment = audio[start:end]
        segment_length = len(segment) / AUDIO_SAMPLE_RATE
        
        # 过滤过短的片段
        if segment_length < min_length:
            continue
            
        # 切分过长的片段
        if segment_length > max_length:
            n_chunks = int(np.ceil(segment_length / max_length))
            chunk_size = len(segment) // n_chunks
            
            for i in range(n_chunks):
                chunk = segment[i*chunk_size:(i+1)*chunk_size]
                if len(chunk) / AUDIO_SAMPLE_RATE >= min_length:
                    segments.append(chunk)
        else:
            segments.append(segment)
            
    return segments

def create_filelist(dataset_dir: str):
    """生成训练集文件列表"""
    # 获取所有音频文件
    audio_files = []
    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith('.wav'):
                rel_path = os.path.relpath(
                    os.path.join(root, file),
                    dataset_dir
                )
                audio_files.append(rel_path)
                
    # 随机划分训练集和验证集
    random.shuffle(audio_files)
    split = int(len(audio_files) * 0.95)  # 95%用于训练
    train_files = audio_files[:split]
    val_files = audio_files[split:]
    
    # 写入文件列表
    with open(os.path.join(dataset_dir, 'train.txt'), 'w') as f:
        f.write('\n'.join(train_files))
        
    with open(os.path.join(dataset_dir, 'val.txt'), 'w') as f:
        f.write('\n'.join(val_files))