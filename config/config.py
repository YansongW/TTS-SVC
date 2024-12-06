import os

# SVC相关配置
SVC_CONFIG = {
    'data_path': 'dataset',
    'model_path': 'logs/44k',
    'config_path': 'configs',
    'pretrain_path': 'pretrain',
    'raw_path': 'raw',
    'results_path': 'results',
    
    # 音频参数
    'sample_rate': 44100,
    'hop_length': 512,
    'segment_size': 8192,
    
    # 训练参数
    'batch_size': 16,
    'learning_rate': 2e-4,
    'max_epochs': 10000,
    
    # 模型参数
    'model': {
        'hidden_channels': 192,
        'filter_channels': 768,
        'n_heads': 2,
        'n_layers': 6,
        'kernel_size': 3,
        'p_dropout': 0.1,
        'resblock': '1',
        'resblock_kernel_sizes': [3,7,11],
        'resblock_dilation_sizes': [[1,3,5], [1,3,5], [1,3,5]],
        'upsample_rates': [8,8,2,2],
        'upsample_initial_channel': 512,
        'upsample_kernel_sizes': [16,16,4,4],
        'ssl_dim': 768,
        'n_speakers': 100
    }
}

# 添加音频处理配置
AUDIO_CONFIG = {
    'sample_rate': 44100,
    'hop_length': 512,
    'win_length': 2048,
    'n_fft': 2048,
    'mel_channels': 80,
    'mel_fmin': 0,
    'mel_fmax': None
}

# 添加模型配置
MODEL_CONFIG = {
    'hidden_channels': 192,
    'filter_channels': 768,
    'n_heads': 2,
    'n_layers': 6,
    'kernel_size': 3,
    'p_dropout': 0.1,
    'resblock': '1',
    'resblock_kernel_sizes': [3,7,11],
    'resblock_dilation_sizes': [[1,3,5], [1,3,5], [1,3,5]],
    'upsample_rates': [8,8,2,2],
    'upsample_initial_channel': 512,
    'upsample_kernel_sizes': [16,16,4,4],
    'ssl_dim': 768,
    'n_speakers': 100
}

# 更新SVC配置
SVC_CONFIG.update({
    'audio': AUDIO_CONFIG,
    'model': MODEL_CONFIG
})

# 确保目录存在
for dir_path in [SVC_CONFIG['pretrain_path'], 
                 SVC_CONFIG['model_path'],
                 SVC_CONFIG['config_path']]:
    os.makedirs(dir_path, exist_ok=True) 