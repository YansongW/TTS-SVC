#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# 检查Python版本
check_python() {
    log "检查Python版本..."
    if command -v python3 >/dev/null 2>&1; then
        python3 --version
    else
        error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
}

# 检查CUDA
check_cuda() {
    log "检查CUDA环境..."
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=name --format=csv,noheader
    else
        warn "未检测到CUDA环境，这可能会影响SVC模型的性能"
    fi
}

# 检查Redis
check_redis() {
    log "检查Redis服务..."
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli ping >/dev/null 2>&1; then
            log "Redis服务正常运行"
        else
            warn "Redis服务未运行，尝试启动..."
            ./start_redis.sh
        fi
    else
        error "未找到Redis，请先安装Redis服务器"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    log "创建虚拟环境..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
}

# 安装依赖
install_dependencies() {
    log "安装项目依赖..."
    pip install -r requirements.txt

    log "安装so-vits-svc..."
    if [ ! -d "so-vits-svc" ]; then
        git clone https://github.com/svc-develop-team/so-vits-svc.git
        cd so-vits-svc
        pip install -r requirements.txt
        cd ..
    fi
}

# 初始化数据库
init_database() {
    log "初始化数据库..."
    export FLASK_APP=run.py
    flask db upgrade
    python scripts/init_db.py
}

# 启动服务
start_services() {
    log "启动服务..."
    
    # 启动Redis（如果未运行）
    ./scripts/start_redis.sh
    
    # 启动Celery worker
    ./scripts/start_celery.sh &
    
    # 启动Flask应用
    ./scripts/start_app.sh &
    
    log "所有服务已启动"
    log "访问 http://localhost:5000 使用系统"
}

# 主函数
main() {
    log "开始部署TTS+SVC系统..."
    
    # 切换到项目根目录
    cd "$(dirname "$0")/.."
    
    # 检查环境
    check_python
    check_cuda
    check_redis
    
    # 设置环境
    create_venv
    install_dependencies
    
    # 初始化
    init_database
    
    # 启动服务
    start_services
    
    log "部署完成!"
}

# 执行主函数
main
