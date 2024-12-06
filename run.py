from app import create_app
from app.logger import setup_logging
from app.utils import setup_svc

# 设置日志
setup_logging()

# 检查SVC环境
setup_svc()

# 创建应用
app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 