@echo off
setlocal enabledelayedexpansion

:: 设置颜色代码
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set NC=[0m

:: 日志函数
:log
echo %GREEN%[%date% %time%] %*%NC%
exit /b

:error
echo %RED%[%date% %time%] ERROR: %*%NC%
exit /b

:warn
echo %YELLOW%[%date% %time%] WARNING: %*%NC%
exit /b

:: 主程序
call :log "开始部署TTS+SVC系统..."

:: 检查Python
call :log "检查Python版本..."
python --version 2>nul
if %errorlevel% neq 0 (
    call :error "未找到Python，请先安装Python 3.8+"
    exit /b 1
)

:: 检查CUDA
call :log "检查CUDA环境..."
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    call :warn "未检测到CUDA环境，这可能会影响SVC模型的性能"
)

:: 检查Redis
call :log "检查Redis服务..."
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    call :warn "Redis服务未运行，请确保Redis已安装并运行"
)

:: 创建虚拟环境
call :log "创建虚拟环境..."
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat

:: 安装依赖
call :log "安装项目依赖..."
pip install -r requirements.txt

:: ���装so-vits-svc
if not exist so-vits-svc (
    call :log "安装so-vits-svc..."
    git clone https://github.com/svc-develop-team/so-vits-svc.git
    cd so-vits-svc
    pip install -r requirements.txt
    cd ..
)

:: 初始化数据库
call :log "初始化数据库..."
set FLASK_APP=run.py
flask db upgrade
python scripts/init_db.py

:: 启动服务
call :log "启动服务..."

:: 启动Redis（如果已安装为Windows服务）
net start redis

:: 启动Celery worker
start cmd /k "venv\Scripts\celery -A app.celery worker --loglevel=info --pool=solo"

:: 启动Flask应用
start cmd /k "python run.py"

call :log "所有服务已启动"
call :log "访问 http://localhost:5000 使用系统"
call :log "部署完成!"

endlocal 