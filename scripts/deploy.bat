@echo off
chcp 65001
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

:: 检查服务状态
:check_service
set service_name=%~1
sc query %service_name% | find "RUNNING" >nul
if %errorlevel% equ 0 (
    call :log "%service_name% 服务正在运行"
    exit /b 0
) else (
    call :warn "%service_name% 服务未运行"
    exit /b 1
)

:: 主程序开始
call :log "开始部署TTS+SVC系统..."

:: 检查和设置环境变量
if not exist .env (
    call :error "未找到.env文件，请先复制.env.example为.env并配置"
    exit /b 1
)

:: 从.env加载环境变量
for /f "tokens=*" %%a in (.env) do (
    set %%a
)

:: 验证配置
call :log "验证配置..."
python config_validator.py
if %errorlevel% neq 0 (
    call :error "配置验证失败"
    exit /b 1
)

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

:: 检查Redis服务
call :log "检查Redis服务..."
call :check_service Redis
if %errorlevel% neq 0 (
    call :log "尝试启动Redis服务..."
    net start Redis
    if %errorlevel% neq 0 (
        call :error "无法启动Redis服务"
        exit /b 1
    )
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

:: 安装so-vits-svc
if not exist so-vits-svc (
    call :log "安装so-vits-svc..."
    git clone https://github.com/svc-develop-team/so-vits-svc.git
    cd so-vits-svc
    pip install -r requirements.txt
    cd ..
)

:: 检查模型文件
call :log "检查模型文件..."

:: 创建必要的目录
mkdir so-vits-svc\models 2>nul
mkdir so-vits-svc\configs 2>nul
mkdir so-vits-svc\pretrain 2>nul

:: 下载hubert模型
set HUBERT_URL=https://github.com/bshall/hubert/releases/download/v0.1/hubert-soft-0d54a1f4.pt
set HUBERT_PATH=so-vits-svc\pretrain\hubert-soft-0d54a1f4.pt

if not exist "%HUBERT_PATH%" (
    call :log "下载hubert模型..."
    curl -L "%HUBERT_URL%" -o "%HUBERT_PATH%"
    if %errorlevel% neq 0 (
        call :error "下载hubert模型失败"
        exit /b 1
    )
)

:: 检查SVC模型
if not exist "so-vits-svc\models\model.pth" (
    call :warn "未找到SVC模型文件"
    call :warn "请从以下地址下载模型文件："
    call :warn "1. 官方模型: https://github.com/svc-develop-team/so-vits-svc/releases"
    call :warn "2. 社区模型: https://huggingface.co/models?search=so-vits-svc"
    call :warn "下载后请���模型文件放置到 so-vits-svc\models\ 目录"
    exit /b 1
)

:: 检查配置文件
if not exist "so-vits-svc\configs\config.json" (
    call :warn "未找到配置文件，创建默认配置..."
    echo {> so-vits-svc\configs\config.json
    echo     "model": {>> so-vits-svc\configs\config.json
    echo         "device": "cuda:0",>> so-vits-svc\configs\config.json
    echo         "sampling_rate": 44100,>> so-vits-svc\configs\config.json
    echo         "hop_length": 512>> so-vits-svc\configs\config.json
    echo     },>> so-vits-svc\configs\config.json
    echo     "audio": {>> so-vits-svc\configs\config.json
    echo         "sample_rate": 44100,>> so-vits-svc\configs\config.json
    echo         "channels": 1>> so-vits-svc\configs\config.json
    echo     },>> so-vits-svc\configs\config.json
    echo     "inference": {>> so-vits-svc\configs\config.json
    echo         "auto_predict_f0": false,>> so-vits-svc\configs\config.json
    echo         "cluster_model_path": "",>> so-vits-svc\configs\config.json
    echo         "speaker_id": 0,>> so-vits-svc\configs\config.json
    echo         "noise_scale": 0.4,>> so-vits-svc\configs\config.json
    echo         "f0_method": "dio">> so-vits-svc\configs\config.json
    echo     }>> so-vits-svc\configs\config.json
    echo }>> so-vits-svc\configs\config.json
)

:: 初始化数据库
call :log "初始化数据库..."
set FLASK_APP=run.py
flask db upgrade
python scripts/init_db.py

:: 检查进程
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Flask*" >nul 2>&1
if %errorlevel% equ 0 (
    call :warn "检测到Flask应用正在运行，尝试关闭..."
    taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Flask*" >nul 2>&1
)

tasklist /FI "IMAGENAME eq celery.exe" >nul 2>&1
if %errorlevel% equ 0 (
    call :warn "检测到Celery进程正在运行，尝试关闭..."
    taskkill /F /FI "IMAGENAME eq celery.exe" >nul 2>&1
)

:: 启动服务
call :log "启动服务..."

:: 启动Redis（如果未运行）
call :check_service Redis
if %errorlevel% neq 0 (
    net start Redis
)

:: 创建新的命令窗口启动Celery
start "Celery Worker" cmd /k "title Celery Worker && venv\Scripts\activate && celery -A app.celery worker --loglevel=info --pool=solo"

:: 等待Celery启动
timeout /t 5 /nobreak >nul

:: 创建新的命令窗口启动Flask
start "Flask App" cmd /k "title Flask App && venv\Scripts\activate && python run.py"

:: 等待服务启动
timeout /t 5 /nobreak >nul

:: 检查服务是否成功启动
curl -s http://localhost:5000 >nul
if %errorlevel% neq 0 (
    call :error "Flask应用启动失败"
    goto :cleanup
)

call :log "所有服务已启动"
call :log "访问 http://localhost:5000 使用系统"
call :log "部署完成!"
exit /b 0

:cleanup
:: 清理进程
taskkill /F /FI "WINDOWTITLE eq Celery Worker*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Flask App*" >nul 2>&1
exit /b 1

endlocal