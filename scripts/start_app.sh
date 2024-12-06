#!/bin/bash

# 确保在项目根目录
cd "$(dirname "$0")/.."

# 激活虚拟环境（如果使用）
source venv/bin/activate

# 设置环境变量
export FLASK_APP=run.py
export FLASK_ENV=development

# 初始化数据库（如果需要）
flask db upgrade

# 启动应用
python run.py