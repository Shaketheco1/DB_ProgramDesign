#利用应用程序Factory函数创建flask应用实例

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from instance.config import DevelopmentConfig
import logging

# 创建数据库实例
db = SQLAlchemy()

#工厂函数
def create_app():
    """工厂函数：创建并配置Flask实例"""
    app = Flask(__name__, instance_relative_config=True)
    
    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # 加载配置
    app.config.from_object(DevelopmentConfig)
    
    try:
        # 初始化数据库
        db.init_app(app)

        # 初始化Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'main.user_login'
        login_manager.login_message = '请先登录'
        login_manager.login_message_category = 'info'

        # 注册用户加载函数
        from .auth import User
        @login_manager.user_loader
        def load_user(user_id):
            return User.get_user(user_id)

        #注册路由
        from . import routes
        app.register_blueprint(routes.app)

        # 创建数据库表
        with app.app_context():
            db.create_all()
            logger.info("数据库表创建成功")

    except Exception as e:
        logger.error(f"应用初始化失败: {str(e)}")
        raise

    return app