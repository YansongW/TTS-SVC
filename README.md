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

## 安装步骤

### 1. 克隆项目

```bash
git clone [项目地址]
cd tts-svc-system
```

### 2. 创建并激活虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装so-vits-svc

```bash
git clone https://github.com/svc-develop-team/so-vits-svc.git
cd so-vits-svc
pip install -r requirements.txt
```

### 5. 下载模型
1. 下载TTS模型(会自动下载)
2. 下载或训练so-vits-svc模型，放置到 `so-vits-svc/models/` 目录

### 6. 配置系统
1. 修改 `config.py` 中的相关配置：

```python
# 更新SVC模型路径
SVC_MODEL_PATH = os.path.join(SVC_DIR, 'models', '你的模型文件名.pth')
SVC_CONFIG_PATH = os.path.join(SVC_DIR, 'configs', '你的配置文件名.json')
```

2. 确保所有目录权限正确：

```bash
chmod +x scripts/*.sh  # Linux/Mac
```

### 7. 初始化数据库

```bash
flask db upgrade
```

## 启动系统

### 1. 启动Redis服务器

```bash
./scripts/start_redis.sh
# 或手动启动Redis服务器
```

### 2. 启动Celery Worker

```bash
./scripts/start_celery.sh
# 或
celery -A app.celery worker --loglevel=info
```

### 3. 启动Web应用

```bash
./scripts/start_app.sh
# 或
python run.py
```

## 使用说明

### 单条文本转换
1. 访问系统主页 http://localhost:5000
2. 点击 "Upload Single Task"
3. 输入要转换的文本
4. 设置音高(pitch)和语速(speed)参数
5. 选择音色(melody)
6. 提交任务并等待处理完成
7. 下载生成的音频文件

### 批量转换
1. 准备文本文件(每行一个文本)
2. 点击 "Upload Batch Task"
3. 输入批次名称
4. 上传文本文件
5. 设置参数JSON(可以设置多组参数)
6. 提交批量任务
7. 在主页查看处理进度
8. 下载完成的音频文件

### 参数说明
- pitch: 音高调节，范围0.5-2.0
- speed: 语速调节，范围0.5-2.0
- melody: 音色选择，取决于使用的模型

## 常见问题

### 1. 系统启动失败
- 检查Redis服务是否正常运行
- 确认所有Python依赖是否正确安装
- 检查日志文件获取详细错误信息

### 2. 音频生成失败
- 确认CUDA环境配置正确
- 检查模型文件是否存在且路径正确
- 查看日志文件了解具体错误原因

### 3. 批量处理停止
- 检查Redis连接是否正常
- 确认Celery worker是否在运行
- 查看celery.log获取详细信息

## 注意事项
1. 定期清理output目录下的临时文件
2. 监控磁盘空间使用情况
3. 建议定期备份数据库
4. 在生产环境中建议使用gunicorn等WSGI服务器
5. 注意保护好模型文件和配置文件

## 日志说明
- 应用日志: logs/app.log
- Celery日志: logs/celery.log
- 日志级别可在config.py中配置

## 目录结构
```
project/
├── app/                # 应用主目录
├── data/              # 数据文件
├── logs/              # 日志文件
├── output/            # 输出文件
│   ├── tts/          # TTS音频文件
│   └── svc/          # SVC音频文件
├── scripts/           # 启动脚本
├── so-vits-svc/      # SVC模型
├── static/           # 静态文件
├── templates/        # 模板文件
├── config.py         # 配置文件
├── requirements.txt  # 依赖文件
└── run.py           # 启动文件
```

## 开发说明
如需进行二次开发，请参考以下文件：
- models.py: 数据模型定义
- routes.py: 路由和视图函数
- tasks.py: 异步任务处理
- utils.py: 工具函数
# TTS-SVC
