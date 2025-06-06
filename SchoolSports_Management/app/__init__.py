#利用应用程序Factory函数创建flask应用实例

from flask import Flask
from flask_login import LoginManager
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from instance import config
import logging

from . import db

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
    app.config.from_object(config.Config)
    
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

    return app