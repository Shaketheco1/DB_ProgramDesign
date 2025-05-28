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
            password=current_app.config['DB_PASSWORD'],
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
    try:
        # 使用上下文管理器确保文件和数据库资源正确关闭
        with current_app.open_instance_resource('schema.sql') as f, db.cursor() as cursor:
            sql_buffer = ""  # 用于缓存多行 SQL 语句
            for line in f:  # 逐行读取文件
                decoded_line = line.decode('utf-8').strip()  # 将字节解码为字符串并去除多余空格
                if not decoded_line or decoded_line.startswith('--'):  # 跳过空行和注释
                    continue
                sql_buffer += decoded_line + " "  # 缓存有效 SQL 语句
                if decoded_line.endswith(';'):  # 如果语句以分号结束，则执行
                    cursor.execute(sql_buffer.strip())
                    sql_buffer = ""  # 清空缓冲区
    except Exception as e:
        # 提供更有意义的错误信息
        raise RuntimeError(f"Failed to execute SQL script '{'schema.sql'}': {e}")


#定义一个cli——“init-db”，调用init-db函数
@click.command('init-db')
def init_db_command():
    """创建新的数据表"""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    #添加一个新的命令可以与flask一起使用
    app.cli.add_command(init_db_command)
