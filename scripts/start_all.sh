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
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# 检查服务状态
check_service() {
    local service=$1
    local port=$2
    if lsof -i :$port > /dev/null; then
        log "$service is running on port $port"
        return 0
    else
        warn "$service is not running on port $port"
        return 1
    fi
}

# 检查进程
check_process() {
    local name=$1
    if pgrep -f "$name" > /dev/null; then
        log "$name process is running"
        return 0
    else
        warn "$name process is not running"
        return 1
    fi
}

# 启动所有服务
start_all() {
    log "Starting all services..."
    
    # 启动Redis
    if ! check_process "redis-server"; then
        log "Starting Redis..."
        redis-server /etc/redis/redis.conf &
        sleep 2
    fi
    
    # 启动Celery
    if ! check_process "celery"; then
        log "Starting Celery..."
        celery -A app.celery worker --loglevel=info --detach
        sleep 2
    fi
    
    # 启动Flask
    if ! check_service "Flask" 5000; then
        log "Starting Flask..."
        nohup python run.py > logs/flask.log 2>&1 &
        sleep 2
    fi
    
    # 验证服务状态
    local all_running=true
    
    if ! check_service "Redis" 6379; then
        error "Redis failed to start"
        all_running=false
    fi
    
    if ! check_process "celery"; then
        error "Celery failed to start"
        all_running=false
    fi
    
    if ! check_service "Flask" 5000; then
        error "Flask failed to start"
        all_running=false
    fi
    
    if [ "$all_running" = true ]; then
        log "All services started successfully"
    else
        error "Some services failed to start"
    fi
}

# 主函数
main() {
    # 确保在项目根目录
    cd "$(dirname "$0")/.."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        error "Virtual environment not found. Please run deploy.sh first."
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 启动服务
    start_all
}

main