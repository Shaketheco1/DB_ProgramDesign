#用于完成用户验证
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from . import db

class User(UserMixin):
    def __init__(self, id, username, role, password_hash=None):
        self.id = id
        self.username = username
        self.role = role
        self.password_hash = password_hash

    @staticmethod
    def get_user(user_id):
        """根据用户ID获取用户信息"""
        # 尝试从学生表中查找
        conn = db.get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT StudentID as id, Name as username, "student" as role, Password FROM Student WHERE StudentID = %s',
                (user_id,)
            )
            student = cursor.fetchone()
            if student:
                return User(student['id'], student['username'], student['role'], student['Password'])

            # 尝试从裁判表中查找
            cursor.execute(
                'SELECT RefereeID as id, Username, "Referee" as role, Password FROM Referee WHERE RefereeID = %s',
                (user_id,)
            )
            referee = cursor.fetchone()
            if referee:
                return User(referee['id'], referee['Username'], referee['role'], referee['Password'])

            # 尝试从管理员表中查找
            cursor.execute(
                'SELECT AdminID as id, Username, "admin" as role, Password FROM Administrator WHERE AdminID = %s',
                (user_id,)
            )
            admin = cursor.fetchone()
            if admin:
                return User(admin['id'], admin['Username'], admin['role'], admin['Password'])

        return None

    @staticmethod
    def authenticate(user_id, password):
        """验证用户登录"""
        user = User.get_user(user_id)
        if user and user.check_password(password):
            return user
        return None

    def set_password(self, password):
        """设置新密码"""
        self.password_hash = generate_password_hash(password)
        conn = db.get_db()
        with conn.cursor() as cursor:
            if self.role == 'student':
                cursor.execute(
                    'UPDATE Student SET Password = %s WHERE StudentID = %s',
                    (self.password_hash, self.id)
                )
            elif self.role == 'Referee':
                cursor.execute(
                    'UPDATE Referee SET Password = %s WHERE RefereeID = %s',
                    (self.password_hash, self.id)
                )
            elif self.role == 'admin':
                cursor.execute(
                    'UPDATE Administrator SET Password = %s WHERE AdminID = %s',
                    (self.password_hash, self.id)
                )
            conn.commit()

    def check_password(self, password):
        """检查密码是否正确"""
        return self.password_hash and check_password_hash(self.password_hash, password)
