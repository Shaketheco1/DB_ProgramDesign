#用于完成用户验证
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from sqlalchemy import text

class User(UserMixin):
    def __init__(self, id, username, role, password_hash=None):
        self.id = id
        self.username = username
        self.role = role
        self.password_hash = password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_user(user_id):
        """根据用户id获取用户对象"""
        # 尝试从学生表中查询
        student = db.session.execute(
            text('SELECT StudentID AS id, Name AS username, \'student\' AS role, Password AS password_hash '
                'FROM Student WHERE Student.StudentID = :user_id'),
            {'user_id': user_id}
        ).mappings().first()
        if student:
            return User(student.id, student.username, student.role, student.password_hash)

        # 尝试在裁判表中查询
        referee = db.session.execute(
            text('SELECT RefereeID AS id, Name AS username, \'Referee\' AS role, Password AS password_hash '
                'FROM Referee WHERE Referee.RefereeID = :user_id'),
            {'user_id': user_id}
        ).mappings().first()
        if referee:
            return User(referee.id, referee.username, referee.role, referee.password_hash)

        # 尝试在管理员表中查询
        admin = db.session.execute(
            text('SELECT AdminID AS id, Username AS username, \'admin\' AS role, Password AS password_hash '
                'FROM Administrator WHERE AdminID = :user_id'),
            {'user_id': user_id}
        ).mappings().first()
        if admin:
            return User(admin.id, admin.username, admin.role, admin.password_hash)

    @staticmethod
    def authenticate(user_id, password):
        """验证用户凭据"""
        user = User.get_user(user_id)
        if user and user.check_password(password):
            return user
        return None
