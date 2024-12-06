import logging
import logging.handlers
from config import LOG_FORMAT, LOG_FILE, LOG_LEVEL

def setup_logging():
    """配置日志系统"""
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.WARNING) 