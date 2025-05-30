#配置文件
import os
import secrets
from urllib.parse import quote_plus

# 生成随机密钥
SECRET_KEY = secrets.token_hex(16)

# 数据库配置
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = quote_plus('Cpy041024@')  # URL编码密码
DB_NAME = 'SchoolSports_Management'

# 上传文件配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class Config:
    SECRET_KEY = SECRET_KEY
    # 设置SQLAlchemy数据库URI
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        '?charset=utf8mb4&connect_timeout=10'
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    DEBUG = True

class DevelopmentConfig(Config):
    pass

class ProductionConfig(Config):
    DEBUG = False

# 默认使用开发配置
config = DevelopmentConfig

#JWT配置
JWT_SECRET_KEY = 'nddfEEBB]mV7MeY'
