# TTS + SVC 音频生成系统

## 项目介绍
这是一个基于Flask的Web应用系统，集成了TTS(文本转语音)和so-vits-svc(语音转换)功能，可以批量将文本转换为具有特定音色的语音。系统采用异步任务处理架构，支持批量处理和实时进度显示。

### 主要特点
- 支持单条和批量文本转换
- 可调节音高(pitch)和语速(speed)
- 支持多种音色选择和自定义模型
- Web界面操作简单直观
- 实时显示处理进度
- 完整的错误处理和日志记录
- 支持异步任务处理和队列管理

## 系统要求

### 基础环境
- Python 3.8+
- Redis 服务器
- CUDA支持(用于so-vits-svc模型)
- 足够的磁盘空间用于存储音频文件

### Python依赖
- Flask 2.2.2
- Flask-SQLAlchemy 3.0.2
- Flask-Migrate 4.0.4
- Celery 5.2.7
- Redis 4.5.1
- TTS 0.10.3
- PyTorch (CUDA版本)
- 其他依赖见requirements.txt

## 详细安装步骤

### 1. 安装基础环境

#### Linux/Mac

```bash
# 安装Python 3.8+
sudo apt update
sudo apt install python3.8 python3.8-venv python3-pip

# 安装Redis
sudo apt install redis-server

# 安装CUDA (如果需要)
# 请参考NVIDIA官方文档
```

#### Windows
1. 从Python官网下载并安装Python 3.8+
2. 从Github下载Redis Windows版本
3. 安装CUDA (如果需要)

### 2. 克隆项目

```bash
git clone [项目地址]
cd tts-svc-system
```

### 3. 配置环境变量
1. 复制环境变量模板

```bash
cp .env.example .env
```

2. 编辑.env文件，配置必要的环境变量：

```env
# TTS配置
TTS_MODEL_NAME=tts_models/en/ljspeech/tacotron2-DDC

# SVC配置
SVC_MODEL_PATH=/path/to/your/model.pth
SVC_CONFIG_PATH=/path/to/your/config.json

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# Flask配置
FLASK_SECRET_KEY=your-secret-key-here
```

### 4. 下载模型

#### TTS模型
系统会自动下载TTS模型，如果需要手动下载：

```bash
# 进入虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 下载模型
python -c "from TTS.api import TTS; TTS.download_model('tts_models/en/ljspeech/tacotron2-DDC')"
```

#### SVC模型
1. 创建模型目录：

```bash
mkdir -p so-vits-svc/models
mkdir -p so-vits-svc/configs
```

2. 下载预训练模型：
- 访问[so-vits-svc releases](https://github.com/svc-develop-team/so-vits-svc/releases)
- 下载模型文件(.pth)和配置文件(config.json)
- 将文件放入对应目录

### 5. 初始化项目

#### Linux/Mac

```bash
# 设置脚本权限
chmod +x scripts/*.sh

# 运行部署脚本
./scripts/deploy.sh
```

#### Windows

```batch
# 运行部署脚本
scripts\deploy.bat
```

部署脚本会自动完成：
- 创建虚拟环境
- 安装依赖
- 初始化数据库
- 启动服务

### 6. 验证安装
访问 http://localhost:5000 验证系统是否正常运行

## 使用说明

### 单条文本转换
1. 访问系统主页
2. 点击"Upload Single Task"
3. 输入文本内容
4. 设置转换参数：
   - Pitch (音高): 0.5-2.0
   - Speed (语速): 0.5-2.0
   - Melody (音色): 根据模型支持的音色选择
5. 提交任务
6. 等待处理完成后下载音频文件

### 批量转换
1. 准备文本文件：
   - 文件格式：txt
   - 每行一个文本
   - UTF-8编码
2. 准备参数配置：

```json
[
    {
        "pitch": 1.0,
        "speed": 1.0,
        "melody": "default"
    },
    {
        "pitch": 1.2,
        "speed": 0.8,
        "melody": "happy"
    }
]
```
3. 上传文件和配置
4. 等待处理完成
5. 下载生成的音频文件

## 故障排除

### 1. 安装问题
#### 依赖安装失败

```bash
# 更新pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### CUDA问题
1. 检查CUDA版本：

```bash
nvidia-smi
```
2. 确保PyTorch版本与CUDA版本匹配
3. 必要时重新安装对应版本的PyTorch

### 2. 运行问题
#### Redis连接失败
1. 检查Redis服务状态：

```bash
# Linux/Mac
sudo systemctl status redis

# Windows
net start redis
```

2. 检查Redis配置：

```bash
redis-cli ping
```

#### 数据库错误
1. 重置数据库：

```bash
flask db reset
flask db upgrade
```

2. 检查日志：

```bash
tail -f logs/app.log
```

#### 任务处理失败
1. 检查Celery状态：

```bash
# 查看Celery日志
tail -f logs/celery.log
```

2. 重启Celery：

```bash
# Linux/Mac
./scripts/start_celery.sh

# Windows
scripts\start_celery.bat
```

## 维护指南

### 定期维护
1. 清理临时文件：

```bash
python scripts/cleanup.py
```

2. 备份数据库：

```bash
python scripts/backup_db.py
```

3. 更新依赖：

```bash
pip install -r requirements.txt --upgrade
```

### 监控
1. 检查系统状态：

```bash
python scripts/check_status.py
```

2. 查看资源使用：

```bash
python scripts/monitor.py
```

## 安全建议
1. 修改默认密钥
2. 限制上传文件大小
3. 配置防火墙
4. 定期更新依赖
5. 备份重要数据

## 常见问题解答

Q: 如何更换TTS模型？
A: 修改.env文件中的TTS_MODEL_NAME，选择其他支持的模型。

Q: 如何训练自己的SVC模型？
A: 参考so-vits-svc项目的训练文档，将训练好的模型放入models目录。

Q: 批量任务处理很慢怎么办？
A: 调整config.py中的并发设置，增加worker数量。

Q: 如何扩展音色选项？
A: 训练新的SVC模型，并更新配置文件。

## 贡献指南
1. Fork项目
2. 创建特性分支
3. 提交更改
4. 发起Pull Request

## 许可证
[添加许可证信息]

## 联系方式
[添加联系方式]
