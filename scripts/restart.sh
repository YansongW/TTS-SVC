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

# 重启服务
restart_services() {
    log "Restarting services..."
    
    # 停止服务
    ./scripts/stop_all.sh
    if [ $? -ne 0 ]; then
        error "Failed to stop services"
    fi
    
    # 等待服务完全停止
    sleep 5
    
    # 启动服务
    ./scripts/start_all.sh
    if [ $? -ne 0 ]; then
        error "Failed to start services"
    fi
    
    log "Services restarted successfully"
}

# 主函数
main() {
    # 确保在项目根目录
    cd "$(dirname "$0")/.."
    
    # 检查脚本是否存在
    if [ ! -f "scripts/stop_all.sh" ] || [ ! -f "scripts/start_all.sh" ]; then
        error "Required scripts not found"
    fi
    
    # 重启服务
    restart_services
}

main 