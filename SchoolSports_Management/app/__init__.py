#利用应用程序Factory函数创建flask应用实例

from flask import Flask




#工厂函数
def create_app():
    """工厂函数：创建并配置Flask实例"""
    app = Flask(__name__, instance_relative_config=True)
    #从config文件中加载配置
    app.config.from_pyfile('config.py')
    from . import db
    #将db对象与FLASK应用实例关联起来
    db.init_app(app)
    return app