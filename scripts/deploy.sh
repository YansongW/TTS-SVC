#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
PYTHON_VERSION="3.8"
REQUIRED_SPACE=5120  # 5GB in MB
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

# 检查系统要求
check_system_requirements() {
    log "检查系统要求..."
    
    # 检查磁盘空间
    local available_space=$(df -m . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt "$REQUIRED_SPACE" ]; then
        error "磁盘空间不足，需要至少 ${REQUIRED_SPACE}MB"
    fi
    
    # 检查必要命令
    for cmd in python3 pip3 git redis-cli; do
        if ! command -v $cmd &> /dev/null; then
            error "未找到命令: $cmd"
        fi
    done
}

# 检查Python版本
check_python() {
    log "检查Python版本..."
    local python_ver=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if (( $(echo "$python_ver < $PYTHON_VERSION" | bc -l) )); then
        error "需要Python $PYTHON_VERSION或更高版本"
    fi
}

# 检查CUDA
check_cuda() {
    log "检查CUDA环境..."
    if command -v nvidia-smi &> /dev/null; then
        local cuda_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader)
        log "检测到CUDA驱动版本: $cuda_version"
    else
        warn "未检测到CUDA环境，这可能会影响性能"
    fi
}

# 检查Redis
check_redis() {
    log "检查Redis服务..."
    if ! redis-cli ping &> /dev/null; then
        error "Redis服务未运行"
    fi
}

# 创建虚拟环境
setup_virtualenv() {
    log "创建虚拟环境..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv || error "创建虚拟环境失败"
    fi
    source venv/bin/activate || error "激活虚拟环境失败"
    pip install --upgrade pip
}

# 安装依赖
install_dependencies() {
    log "安装项目依赖..."
    pip install -r requirements.txt || error "安装依赖失败"
    
    log "安装so-vits-svc..."
    if [ ! -d "so-vits-svc" ]; then
        git clone https://github.com/svc-develop-team/so-vits-svc.git || error "克隆so-vits-svc失败"
        cd so-vits-svc
        pip install -r requirements.txt || error "安装so-vits-svc依赖失败"
        cd ..
    fi
}

# 检查和下载模型
setup_models() {
    log "检查模型文件..."
    
    # 创建必要的目录
    mkdir -p so-vits-svc/models
    mkdir -p so-vits-svc/configs
    mkdir -p so-vits-svc/pretrain
    
    # 下载hubert模型
    local HUBERT_URL="https://github.com/bshall/hubert/releases/download/v0.1/hubert-soft-0d54a1f4.pt"
    local HUBERT_PATH="so-vits-svc/pretrain/hubert-soft-0d54a1f4.pt"
    
    if [ ! -f "$HUBERT_PATH" ]; then
        log "下载hubert模型..."
        curl -L "$HUBERT_URL" -o "$HUBERT_PATH" || error "下载hubert模型失败"
    fi
    
    # 检查SVC模型文件
    if [ ! -f "so-vits-svc/models/model.pth" ]; then
        warn "未找到SVC模型文件"
        warn "请从以下地址下载模型文件："
        warn "1. 官方模型: https://github.com/svc-develop-team/so-vits-svc/releases"
        warn "2. 社区模型: https://huggingface.co/models?search=so-vits-svc"
        warn "下载后请将模型文件放置到 so-vits-svc/models/ 目录"
    fi
    
    # 检查配置文件
    if [ ! -f "so-vits-svc/configs/config.json" ]; then
        warn "未找到配置文件，创建默认配置..."
        cat > so-vits-svc/configs/config.json << EOF
{
    "model": {
        "device": "cuda:0",
        "sampling_rate": 44100,
        "hop_length": 512
    },
    "audio": {
        "sample_rate": 44100,
        "channels": 1
    },
    "inference": {
        "auto_predict_f0": false,
        "cluster_model_path": "",
        "speaker_id": 0,
        "noise_scale": 0.4,
        "f0_method": "dio"
    }
}
EOF
    fi
}

# 初始化数据库
init_database() {
    log "初始化数据库..."
    export FLASK_APP=run.py
    flask db upgrade || error "数据库初始化失败"
}

# 启动服务
start_services() {
    log "启动服务..."
    
    # 启动Redis（如果未运行）
    if ! redis-cli ping &> /dev/null; then
        ./scripts/start_redis.sh
    fi
    
    # 启动Celery worker
    ./scripts/start_celery.sh &
    
    # 启动Flask应用
    ./scripts/start_app.sh &
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态
    if ! curl -s http://localhost:5000 &> /dev/null; then
        error "Web服务启动失败"
    fi
    
    if ! celery -A app.celery status &> /dev/null; then
        error "Celery服务启动失败"
    fi
    
    log "所有服务已启动"
    log "访问 http://localhost:5000 使用系统"
}

# 清理函数
cleanup() {
    if [ $? -ne 0 ]; then
        error "部署失败，请检查日志文件"
    fi
}

# 主函数
main() {
    trap cleanup EXIT
    
    log "开始部署TTS+SVC系统..."
    
    # 切换到项目根目录
    cd "$PROJECT_ROOT"
    
    # 系统检查
    check_system_requirements
    check_python
    check_cuda
    check_redis
    
    # 环境设置
    setup_virtualenv
    install_dependencies
    setup_models
    
    # 初始化
    init_database
    
    # 启动服务
    start_services
    
    log "部署完成!"
}

# 执行主函数
main
