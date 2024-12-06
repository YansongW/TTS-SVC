#!/bin/bash

# 确保在项目根目录
cd "$(dirname "$0")/.."

# 激活虚拟环境（如果使用）
source venv/bin/activate

# 启动Celery worker
celery -A app.celery worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=prefork \
    --logfile=logs/celery.log 