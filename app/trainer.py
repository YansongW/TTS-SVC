import os
import json
import torch
import logging
import subprocess
from typing import Dict, Optional
from datetime import datetime
from .model_library import SVCModelLibrary
from .preprocess import prepare_dataset
from config import SVC_DIR
from .feature_extractor import ContentVecExtractor, HubertSoftExtractor
from torch.cuda.amp import autocast, GradScaler
from .losses import kl_loss
from torch.utils.data import DataLoader
from .models import SynthesizerTrn

logger = logging.getLogger(__name__)

class SVCTrainer:
    """SVC模型训练器"""
    def __init__(self):
        self.model_library = SVCModelLibrary()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def prepare_training_data(self, audio_path: str, speaker_name: str) -> str:
        """准备训练数据"""
        try:
            # 创建训练目录
            train_dir = os.path.join(
                self.model_library.training_dir,
                f"train_{speaker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(train_dir)
            
            # 创建数据集目录
            dataset_dir = os.path.join(train_dir, "dataset")
            raw_dir = os.path.join(dataset_dir, speaker_name)
            os.makedirs(raw_dir)
            
            # 处理音频文件
            prepare_dataset(audio_path, raw_dir)
            
            # 生成配置文件
            config = self._generate_config(train_dir, speaker_name)
            config_path = os.path.join(train_dir, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            return train_dir
            
        except Exception as e:
            logger.error(f"Failed to prepare training data: {str(e)}")
            raise
            
    def _generate_config(self, train_dir: str, speaker_name: str) -> Dict:
        """生成训练配置"""
        return {
            "train": {
                "log_interval": 200,
                "eval_interval": 1000,
                "seed": 1234,
                "epochs": 10000,
                "learning_rate": 0.0001,
                "betas": [0.8, 0.99],
                "eps": 1e-9,
                "batch_size": 16,
                "fp16_run": True,
                "lr_decay": 0.999875,
                "segment_size": 8192,
                "init_lr_ratio": 1,
                "warmup_epochs": 0,
                "c_mel": 45,
                "c_kl": 1.0
            },
            "data": {
                "training_files": f"filelists/{speaker_name}_train.txt",
                "validation_files": f"filelists/{speaker_name}_val.txt",
                "max_wav_value": 32768.0,
                "sampling_rate": 44100,
                "filter_length": 2048,
                "hop_length": 512,
                "win_length": 2048,
                "n_mel_channels": 80,
                "mel_fmin": 0.0,
                "mel_fmax": None
            },
            "model": {
                "inter_channels": 192,
                "hidden_channels": 192,
                "filter_channels": 768,
                "n_heads": 2,
                "n_layers": 6,
                "kernel_size": 3,
                "p_dropout": 0.1,
                "resblock": "1",
                "resblock_kernel_sizes": [3,7,11],
                "resblock_dilation_sizes": [[1,3,5], [1,3,5], [1,3,5]],
                "upsample_rates": [8,8,2,2],
                "upsample_initial_channel": 512,
                "upsample_kernel_sizes": [16,16,4,4],
                "n_layers_q": 3,
                "use_spectral_norm": False,
                "gin_channels": 256
            }
        }
        
    def _prepare_encoder(self, encoder_type: str):
        """准备特征提取器"""
        if encoder_type == 'vec768l12':
            model_path = os.path.join(SVC_DIR, 'pretrain/checkpoint_best_legacy_500.pt')
            return ContentVecExtractor(model_path, self.device)
        elif encoder_type == 'hubertsoft':
            model_path = os.path.join(SVC_DIR, 'pretrain/hubert-soft-0d54a1f4.pt')
            return HubertSoftExtractor(model_path, self.device)
        else:
            raise ValueError(f"Unsupported encoder type: {encoder_type}")
        
    def train_model(self, train_dir: str, config: Dict) -> Optional[Dict]:
        """训练模型"""
        try:
            # 准备环境
            os.chdir(SVC_DIR)
            
            # 准备特征提取器
            encoder_type = config.get('encoder_type', 'vec768l12')
            self.encoder = self._prepare_encoder(encoder_type)
            
            # 预处理数据
            subprocess.run([
                "python", "preprocess_flist_config.py",
                "--speech_encoder", encoder_type
            ], check=True)
            
            subprocess.run([
                "python", "preprocess_hubert_f0.py",
                "--f0_predictor", config.get('f0_predictor', 'dio'),
                "--num_processes", str(config.get('num_workers', 4))
            ], check=True)
            
            # 开始训练
            train_cmd = [
                "python", "train.py",
                "-c", os.path.join(train_dir, "config.json"),
                "-m", "44k"
            ]
            
            # 添加训练参数
            if config.get('use_fp16', True):
                train_cmd.append('--fp16')
                
            if config.get('cache_all_data', False):
                train_cmd.append('--cache_all_data')
                
            if 'batch_size' in config:
                train_cmd.extend(['--batch_size', str(config['batch_size'])])
                
            subprocess.run(train_cmd, check=True)
            
            # 获取训练好的模型
            model_path = os.path.join(train_dir, "logs/44k/G_latest.pth")
            config_path = os.path.join(train_dir, "config.json")
            
            # 添加到模型库
            if self.model_library.add_model(
                model_path,
                config_path,
                config['speaker_name'],
                config.get('description', '')
            ):
                return {
                    'model_path': model_path,
                    'config_path': config_path
                }
            return None
            
        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            return None
            
    def get_training_progress(self, train_dir: str) -> Dict:
        """获取训练进度"""
        try:
            # 读取日志获取进度
            log_file = os.path.join(train_dir, "logs/44k/train.log")
            if not os.path.exists(log_file):
                return {
                    'status': 'preparing',
                    'progress': 0,
                    'message': 'Preparing training data...'
                }
                
            with open(log_file) as f:
                lines = f.readlines()
                
            # 解析最后一行获取进度
            if lines:
                last_line = lines[-1]
                if 'Epoch' in last_line:
                    epoch = int(last_line.split('Epoch')[1].split()[0])
                    return {
                        'status': 'training',
                        'progress': min(epoch / 100, 100),  # 假设训练100个epoch
                        'message': f'Training epoch {epoch}...'
                    }
                    
            return {
                'status': 'unknown',
                'progress': 0,
                'message': 'Unknown status'
            }
            
        except Exception as e:
            logger.error(f"Failed to get progress: {str(e)}")
            return {
                'status': 'error',
                'progress': 0,
                'message': str(e)
            }
        
    def _train_svc_model(self, train_dir: str, config: Dict):
        """训练SVC模型"""
        try:
            # 1. 加载配置
            with open(os.path.join(SVC_DIR, "configs/config.json")) as f:
                model_config = json.load(f)
                
            # 2. 初始化模型
            model = SynthesizerTrn(
                spec_channels=model_config["data"]["spec_channels"],
                segment_size=model_config["train"]["segment_size"],
                inter_channels=model_config["model"]["inter_channels"],
                hidden_channels=model_config["model"]["hidden_channels"],
                filter_channels=model_config["model"]["filter_channels"],
                n_heads=model_config["model"]["n_heads"],
                n_layers=model_config["model"]["n_layers"],
                kernel_size=model_config["model"]["kernel_size"],
                p_dropout=model_config["model"]["p_dropout"],
                resblock=model_config["model"]["resblock"],
                resblock_kernel_sizes=model_config["model"]["resblock_kernel_sizes"],
                resblock_dilation_sizes=model_config["model"]["resblock_dilation_sizes"],
                upsample_rates=model_config["model"]["upsample_rates"],
                upsample_initial_channel=model_config["model"]["upsample_initial_channel"],
                upsample_kernel_sizes=model_config["model"]["upsample_kernel_sizes"],
                gin_channels=model_config["model"]["gin_channels"],
                ssl_dim=model_config["model"]["ssl_dim"],
                n_speakers=model_config["model"]["n_speakers"]
            ).to(self.device)

            # 3. 加载预训练模型
            if os.path.exists(os.path.join(SVC_DIR, "pretrain/G_0.pth")):
                model.load_state_dict(torch.load(
                    os.path.join(SVC_DIR, "pretrain/G_0.pth"),
                    map_location=self.device)["model"])
                
            # 4. 准备优化器
            optimizer = torch.optim.AdamW(
                model.parameters(),
                config["learning_rate"],
                betas=model_config["train"]["betas"],
                eps=model_config["train"]["eps"]
            )
            
            # 5. 准备数据集
            from data_utils import TextAudioSpeakerLoader, TextAudioSpeakerCollate
            train_dataset = TextAudioSpeakerLoader(
                model_config["data"]["training_files"],
                model_config["data"]
            )
            collate_fn = TextAudioSpeakerCollate()
            train_loader = DataLoader(
                train_dataset,
                batch_size=config["batch_size"],
                shuffle=True,
                collate_fn=collate_fn
            )
            
            # 6. 训练循环
            epochs = config["epochs"]
            for epoch in range(epochs):
                model.train()
                for batch_idx, batch in enumerate(train_loader):
                    # 获取数据
                    x, x_lengths, spec, spec_lengths, y, y_lengths, speakers = [
                        x.to(self.device) for x in batch
                    ]
                    
                    # 前向传播
                    with autocast(enabled=True):
                        (
                            y_hat,
                            l_length,
                            attn,
                            ids_slice,
                            x_mask,
                            z_mask,
                            (z, z_p, m_p, logs_p, m_q, logs_q),
                        ) = model(
                            x,
                            x_lengths,
                            spec,
                            spec_lengths,
                            speakers
                        )
                        
                        # 计算损失
                        loss_rec = F.l1_loss(y_hat, y)
                        loss_kl = kl_loss(z_p, logs_q, m_p, logs_p, z_mask)
                        loss_all = loss_rec + loss_kl
                        
                    # 反向传播
                    optimizer.zero_grad()
                    loss_all.backward()
                    optimizer.step()
                    
                    # 记录日志
                    if batch_idx % 100 == 0:
                        logger.info(
                            f"Epoch: {epoch}, Batch: {batch_idx}, "
                            f"Loss: {loss_all.item():.4f}, "
                            f"Loss rec: {loss_rec.item():.4f}, "
                            f"Loss kl: {loss_kl.item():.4f}"
                        )
                        
                # 保存检查点
                if (epoch + 1) % 10 == 0:
                    save_path = os.path.join(
                        train_dir,
                        f"G_{epoch+1}.pth"
                    )
                    torch.save({
                        "model": model.state_dict(),
                        "optimizer": optimizer.state_dict(),
                        "epoch": epoch,
                    }, save_path)
                    
            # 保存最终模型
            torch.save({
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "epoch": epochs,
            }, os.path.join(train_dir, "G_final.pth"))
            
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            return False
        
    def train_step(self, batch, model, optimizer):
        """单步训练"""
        # 准备数据
        x, x_lengths = batch['audio'], batch['audio_lengths'] 
        spec, spec_lengths = batch['spec'], batch['spec_lengths']
        y, y_lengths = batch['mel'], batch['mel_lengths']
        f0 = batch['f0']
        
        # 前向传播
        with autocast(enabled=True):
            (
                y_hat,
                l_length,
                attn,
                ids_slice,
                x_mask,
                z_mask,
                (z, z_p, m_p, logs_p, m_q, logs_q),
            ) = model(
                x,
                x_lengths,
                spec,
                spec_lengths,
                f0=f0
            )
            
            # 计算损失
            loss_rec = F.l1_loss(y_hat, y)
            loss_kl = kl_loss(z_p, logs_q, m_p, logs_p, z_mask)
            loss = loss_rec + self.config['train']['c_kl'] * loss_kl
            
        # 反向传播
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        return {
            'loss': loss.item(),
            'loss_rec': loss_rec.item(),
            'loss_kl': loss_kl.item()
        }