from . import db
from datetime import datetime
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import Conv1d
from torch.nn.utils import weight_norm, remove_weight_norm
from app.modules import commons, modules, attentions

class BatchTask(db.Model):
    """批量任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    progress = db.Column(db.Integer, default=0)  # 进度百分比
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='batch', lazy=True)
    
    def update_progress(self):
        """更新进度"""
        if self.total_tasks > 0:
            self.progress = int((self.completed_tasks / self.total_tasks) * 100)
        else:
            self.progress = 0
        db.session.commit()

class Task(db.Model):
    """单个任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    pitch = db.Column(db.Float, default=1.0)
    speed = db.Column(db.Float, default=1.0) 
    melody = db.Column(db.String(50), default='default')
    status = db.Column(db.String(20), default='Pending')
    error_message = db.Column(db.Text)  # 错误信息
    tts_output = db.Column(db.String(200))
    svc_output = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch_task.id'), nullable=True)
    
    def __repr__(self):
        return f'<Task {self.id}>'

class SynthesizerTrn(nn.Module):
    """
    Synthesizer for Training
    """
    def __init__(self, 
                 spec_channels,
                 segment_size,
                 inter_channels,
                 hidden_channels,
                 filter_channels,
                 n_heads,
                 n_layers,
                 kernel_size,
                 p_dropout,
                 resblock, 
                 resblock_kernel_sizes,
                 resblock_dilation_sizes,
                 upsample_rates,
                 upsample_initial_channel,
                 upsample_kernel_sizes,
                 gin_channels,
                 ssl_dim,
                 n_speakers,
                 **kwargs):
        super().__init__()
        
        self.spec_channels = spec_channels
        self.inter_channels = inter_channels
        self.hidden_channels = hidden_channels
        self.filter_channels = filter_channels
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.kernel_size = kernel_size
        self.p_dropout = p_dropout
        self.resblock = resblock
        self.resblock_kernel_sizes = resblock_kernel_sizes
        self.resblock_dilation_sizes = resblock_dilation_sizes
        self.upsample_rates = upsample_rates
        self.upsample_initial_channel = upsample_initial_channel
        self.upsample_kernel_sizes = upsample_kernel_sizes
        self.segment_size = segment_size
        self.gin_channels = gin_channels
        self.ssl_dim = ssl_dim
        
        self.enc_p = modules.ContentEncoder(
            hidden_channels,
            filter_channels,
            n_heads,
            n_layers,
            kernel_size,
            p_dropout,
            ssl_dim=ssl_dim
        )
        
        self.dec = modules.Generator(
            inter_channels,
            resblock,
            resblock_kernel_sizes,
            resblock_dilation_sizes,
            upsample_rates,
            upsample_initial_channel,
            upsample_kernel_sizes,
            gin_channels=gin_channels
        )
        
        self.enc_q = modules.PosteriorEncoder(
            spec_channels,
            inter_channels,
            hidden_channels,
            5,
            1,
            16,
            gin_channels=gin_channels
        )
        
        self.flow = modules.ResidualCouplingBlock(
            inter_channels, hidden_channels, 5, 1, 3, gin_channels=gin_channels
        )
        
        self.emb_g = nn.Embedding(n_speakers, gin_channels)
        
    def forward(self, c, f0, spec, g=None, mel=None, c_lengths=None, spec_lengths=None):
        # Content encoder
        c_mask = torch.unsqueeze(commons.sequence_mask(c_lengths, c.size(2)), 1).to(c.dtype)
        z_p, m_p, logs_p, _ = self.enc_p(c, c_mask, f0=f0)
        
        # Posterior encoder
        z_q, m_q, logs_q = self.enc_q(spec, g=g)
        
        # Flow
        z_f = self.flow(z_q, g=g)
        
        # Generator
        z_p = self.flow(z_p, g=g, reverse=True)
        o = self.dec(z_p * c_mask, g=g)
        
        return o, z_f, m_p, logs_p, m_q, logs_q
        
    def infer(self, c, f0, g=None, mel=None, c_lengths=None):
        c_mask = torch.unsqueeze(commons.sequence_mask(c_lengths, c.size(2)), 1).to(c.dtype)
        z_p, m_p, logs_p, c_mask = self.enc_p(c, c_mask, f0=f0)
        
        # Generator
        z_p = self.flow(z_p, g=g, reverse=True)
        o = self.dec(z_p * c_mask, g=g)
        
        return o