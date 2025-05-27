import pymysql

import click
from flask import current_app,g

#创建db连接
#g 是一个特殊对象，独立于每一个请求。在处理请求过程中，它可以 用于储存可能多个函数都会用到的数据。
# 把连接储存于其中，可以多次使用，而不用在同一个请求中每次调用 get_db 时都创建一个新的连接。
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['DB_HOST'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASS'],
            db=current_app.config['DB_NAME'],
            #使查询以字典形式返回
            cursorclass=pymysql.cursors.DictCursor
        )
        return g.db

#关闭连接
def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

#运行schema.sql脚本创建数据库
def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.cursor().executescript(f.read())

#定义一个cli——“init-db”，调用init-db函数
@click.command('init-db')
def init_db_command():
    """创建新的数据表"""
    init_db()
    click.echo('Initialized the database.')


