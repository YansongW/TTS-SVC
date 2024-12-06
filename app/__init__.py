from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery
import os
from config import (
    FLASK_SECRET_KEY, SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS, CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND, SQLALCHEMY_ENGINE_OPTIONS,
    CELERY_CONFIG
)

db = SQLAlchemy()
migrate = Migrate()
celery = Celery(__name__)

class FlaskApp(Flask):
    """扩展Flask应用类，添加上下文处理"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._activate_background_context()
        
    def _activate_background_context(self):
        """激活后台上下文"""
        if self.config.get('SQLALCHEMY_DATABASE_URI'):
            self.app_context().push()

def create_app():
    app = FlaskApp(__name__)
    
    # 基础配置
    app.config['SECRET_KEY'] = FLASK_SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS
    
    # Celery配置
    app.config['CELERY_BROKER_URL'] = CELERY_BROKER_URL
    app.config['CELERY_RESULT_BACKEND'] = CELERY_RESULT_BACKEND
    celery.conf.update(CELERY_CONFIG)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    from .routes import main
    app.register_blueprint(main)
    
    # 注册错误处理
    register_error_handlers(app)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return "Page not found", 404
        
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return "Internal server error", 500 