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

# 检查进程
check_process() {
    local name=$1
    pgrep -f "$name" > /dev/null
    return $?
}

# 停止进程
stop_process() {
    local name=$1
    local pid_file=$2
    
    if check_process "$name"; then
        log "Stopping $name..."
        pkill -f "$name"
        sleep 2
        
        if check_process "$name"; then
            warn "$name is still running, trying SIGKILL..."
            pkill -9 -f "$name"
            sleep 1
        fi
        
        if check_process "$name"; then
            error "Failed to stop $name"
            return 1
        fi
    else
        log "$name is not running"
    fi
    
    # 清理PID文件
    if [ -n "$pid_file" ] && [ -f "$pid_file" ]; then
        rm -f "$pid_file"
    fi
    
    return 0
}

# 停止所有服务
stop_all() {
    log "Stopping all services..."
    local success=true
    
    # 停止Flask
    if ! stop_process "python run.py" "data/flask.pid"; then
        success=false
    fi
    
    # 停止Celery
    if ! stop_process "celery worker" "data/celery.pid"; then
        success=false
    fi
    
    # 停止Redis
    if redis-cli ping &>/dev/null; then
        log "Stopping Redis..."
        if ! redis-cli shutdown; then
            warn "Failed to stop Redis gracefully, trying kill..."
            stop_process "redis-server" "data/redis.pid"
        fi
    else
        log "Redis is not running"
    fi
    
    # 检查结果
    if [ "$success" = true ]; then
        log "All services stopped successfully"
    else
        error "Some services failed to stop"
    fi
}

# 主函数
main() {
    # 确保在项目根目录
    cd "$(dirname "$0")/.."
    
    # 检查是否有权限
    if [ ! -w "data" ]; then
        error "No write permission for data directory"
    fi
    
    # 停止服务
    stop_all
}

main
