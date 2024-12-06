from app import create_app, db
from app.models import Task, BatchTask

def init_db():
    app = create_app()
    with app.app_context():
        # 删除所有表
        db.drop_all()
        # 创建所有表
        db.create_all()
        print("Database initialized successfully")

if __name__ == '__main__':
    init_db() 