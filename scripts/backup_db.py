import os
import shutil
import logging
from datetime import datetime, timedelta
from app import create_app
from config import DB_BACKUP_DIR, SQLALCHEMY_DATABASE_URI, MAX_STORAGE_DAYS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_old_backups():
    """清理旧备份文件"""
    try:
        expiry_date = datetime.now() - timedelta(days=MAX_STORAGE_DAYS)
        for filename in os.listdir(DB_BACKUP_DIR):
            file_path = os.path.join(DB_BACKUP_DIR, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_time < expiry_date:
                os.remove(file_path)
                logger.info(f"已删除过期备份文件: {filename}")
    except Exception as e:
        logger.error(f"清理旧备份文件失败: {str(e)}")

def check_db_lock(db_path):
    """检查数据库是否被锁定"""
    try:
        # 尝试以独占模式打开数据库文件
        with open(db_path, 'r+b') as f:
            return False
    except IOError:
        return True

def backup_database():
    """备份数据库"""
    app = create_app()
    
    try:
        # 获取数据库文件路径
        db_path = SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
            
        # 检查数据库锁
        if check_db_lock(db_path):
            raise RuntimeError("数据库当前被锁定，无法备份")
            
        # 清理旧备份
        cleanup_old_backups()
        
        # 创建备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(DB_BACKUP_DIR, f'backup_{timestamp}.db')
        
        # 复制数据库文件
        shutil.copy2(db_path, backup_path)
        logger.info(f"数据库已备份到: {backup_path}")
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        backup_database()
    except Exception as e:
        logger.error(f"备份过程出错: {str(e)}")
        exit(1) 