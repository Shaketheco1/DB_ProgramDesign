#配置文件
import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1234'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql://U1:1234@localhost:3306/SchoolSports_Management'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProdConfig(Config):
    DEBUG = False