import pymysql
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['DB_HOST'],
            port=current_app.config['DB_PORT'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD'],
            db=current_app.config['DB_NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库"""
    db = get_db()
    try:
        with current_app.open_instance_resource('schema.sql') as f:
            sql_commands = f.read().decode('utf8')
            with db.cursor() as cursor:
                for command in sql_commands.split(';'):
                    if command.strip():
                        cursor.execute(command)
        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"数据库初始化失败: {str(e)}")
    finally:
        close_db()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """创建新的数据表"""
    init_db()
    click.echo('数据库初始化完成。')

@click.command('init-test-data')
@with_appcontext
def init_test_data_command():
    """初始化测试数据"""
    db = get_db()
    try:
        with current_app.open_instance_resource('test_data.sql') as f:
            sql_commands = f.read().decode('utf8')
            with db.cursor() as cursor:
                for command in sql_commands.split(';'):
                    if command.strip():
                        cursor.execute(command)
        db.commit()
        click.echo('测试数据初始化完成。')
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"测试数据初始化失败: {str(e)}")
    finally:
        close_db()

def init_app(app):
    """注册数据库命令"""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(init_test_data_command)
