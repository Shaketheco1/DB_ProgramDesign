#由于项目不是特别复杂，决定使用一个蓝图完成
#该文件包含了程序需要的所有路由
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from . import db
from .auth import User
import pymysql.cursors
from datetime import datetime
from sqlalchemy import text

app = Blueprint('main', __name__)

#定义首页
@app.route('/',methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 处理首页的表单提交
        return redirect(url_for('main.index'))
    return render_template('index.html')

#用户登录
@app.route('/login',methods=['GET','POST'])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        if not user_id or not password:
            flash('请输入用户ID和密码', 'error')
            return redirect(url_for('main.user_login'))
        
        # 使用auth.py中的验证方法
        user = User.authenticate(user_id, password)
        
        if user:
            login_user(user)
            flash(f'欢迎回来，{user.username}！', 'success')
            # 根据用户角色重定向到不同页面
            if user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('main.student_dashboard'))
            elif user.role == 'Referee':
                return redirect(url_for('main.referee_dashboard'))
        else:
            flash('用户ID或密码错误！', 'error')
            return redirect(url_for('main.user_login'))
            
    return render_template('login.html')

# 用户登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出！', 'success')
    return redirect(url_for('main.index'))

# 管理员仪表板
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取系统统计数据
    stats = {
        'total_users': db.session.execute(
            text('SELECT COUNT(*) as count FROM Student')).scalar() +
            db.session.execute(text('SELECT COUNT(*) as count FROM Referee')).scalar() +
            db.session.execute(text('SELECT COUNT(*) as count FROM Administrator')).scalar(),
        'active_events': db.session.execute(
            text('SELECT COUNT(*) as count FROM Competition WHERE Status = "进行中"')).scalar(),
        'today_registrations': db.session.execute(
            text('SELECT COUNT(*) as count FROM Registration WHERE DATE(RegistrationTime) = CURDATE()')).scalar(),
        'pending_approvals': db.session.execute(
            text('SELECT COUNT(*) as count FROM Registration WHERE Status = "待审核"')).scalar()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

# 比赛项目管理
@app.route('/admin/events')
@login_required
def manage_events():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    events = db.session.execute(
        text('SELECT * FROM Event ORDER BY EventID')
    ).fetchall()
    
    return render_template('admin/events.html', events=events)

# 添加比赛项目
@app.route('/admin/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            event_id = request.form.get('event_id')
            event_name = request.form.get('event_name')
            event_type = request.form.get('event_type')
            gender_restriction = request.form.get('gender_restriction')
            max_participants = request.form.get('max_participants')
            rules = request.form.get('rules')
            is_final = request.form.get('is_final') == 'true'
            
            db.session.execute(
                text('''
                    INSERT INTO Event (EventID, EventName, EventType, GenderRestriction,
                                     MaxParticipants, Rules, IsFinal)
                    VALUES (:event_id, :event_name, :event_type, :gender_restriction,
                            :max_participants, :rules, :is_final)
                '''),
                {
                    'event_id': event_id,
                    'event_name': event_name,
                    'event_type': event_type,
                    'gender_restriction': gender_restriction,
                    'max_participants': max_participants,
                    'rules': rules,
                    'is_final': is_final
                }
            )
            db.session.commit()
            flash('比赛项目添加成功！', 'success')
            return redirect(url_for('main.manage_events'))
            
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请重试！', 'error')
            return redirect(url_for('main.add_event'))
            
    return render_template('admin/add_event.html')

# 场地管理
@app.route('/admin/venues')
@login_required
def manage_venues():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    venues = db.session.execute(
        text('SELECT * FROM Venue ORDER BY VenueID')
    ).fetchall()
    
    return render_template('admin/venues.html', venues=venues)

# 添加场地
@app.route('/admin/venues/add', methods=['GET', 'POST'])
@login_required
def add_venue():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            venue_id = request.form.get('venue_id')
            venue_name = request.form.get('venue_name')
            venue_type = request.form.get('venue_type')
            location = request.form.get('location')
            capacity = request.form.get('capacity')
            
            db.session.execute(
                text('''
                    INSERT INTO Venue (VenueID, VenueName, VenueType, Location, Capacity, Status)
                    VALUES (:venue_id, :venue_name, :venue_type, :location, :capacity, '可用')
                '''),
                {
                    'venue_id': venue_id,
                    'venue_name': venue_name,
                    'venue_type': venue_type,
                    'location': location,
                    'capacity': capacity
                }
            )
            db.session.commit()
            flash('场地添加成功！', 'success')
            return redirect(url_for('main.manage_venues'))
            
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请重试！', 'error')
            return redirect(url_for('main.add_venue'))
            
    return render_template('admin/add_venue.html')

# 赛程安排
@app.route('/admin/competitions')
@login_required
def manage_competitions():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    competitions = db.session.execute(
        text('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            ORDER BY c.ScheduledStartTime DESC
        ''')
    ).fetchall()
    
    return render_template('admin/competitions.html', competitions=competitions)

# 添加赛程
@app.route('/admin/competitions/add', methods=['GET', 'POST'])
@login_required
def add_competition():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            competition_id = request.form.get('competition_id')
            event_id = request.form.get('event_id')
            group_name = request.form.get('group_name')
            scheduled_start_time = request.form.get('scheduled_start_time')
            scheduled_end_time = request.form.get('scheduled_end_time')
            venue_id = request.form.get('venue_id')
            
            db.session.execute(
                text('''
                    INSERT INTO Competition (CompetitionID, EventID, GroupName,
                                          ScheduledStartTime, ScheduledEndTime,
                                          VenueID, Status)
                    VALUES (:competition_id, :event_id, :group_name,
                            :scheduled_start_time, :scheduled_end_time,
                            :venue_id, '未开始')
                '''),
                {
                    'competition_id': competition_id,
                    'event_id': event_id,
                    'group_name': group_name,
                    'scheduled_start_time': scheduled_start_time,
                    'scheduled_end_time': scheduled_end_time,
                    'venue_id': venue_id
                }
            )
            db.session.commit()
            flash('赛程添加成功！', 'success')
            return redirect(url_for('main.manage_competitions'))
            
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请重试！', 'error')
            return redirect(url_for('main.add_competition'))
            
    # 获取所有比赛项目和场地
    events = db.session.execute(text('SELECT * FROM Event')).fetchall()
    venues = db.session.execute(text('SELECT * FROM Venue')).fetchall()
    
    return render_template('admin/add_competition.html', events=events, venues=venues)

# 学生管理
@app.route('/admin/students')
@login_required
def students():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    # 获取所有学生信息
    students = db.session.execute(
        text('SELECT * FROM Student ORDER BY StudentID')
    ).fetchall()
    
    return render_template('admin/students.html', students=students)

# 裁判管理
@app.route('/admin/referees')
@login_required
def manage_referees():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    referees = db.session.execute(
        text('SELECT * FROM Referee ORDER BY RefereeID')
    ).fetchall()
    
    return render_template('admin/referees.html', referees=referees)

# 管理员管理
@app.route('/admin/admins')
@login_required
def manage_admins():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    admins = db.session.execute(
        text('SELECT * FROM Administrator ORDER BY AdminID')
    ).fetchall()
    
    return render_template('admin/admins.html', admins=admins)

# 系统设置
@app.route('/admin/settings')
@login_required
def system_settings():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    return render_template('admin/settings.html')

# 数据分析
@app.route('/admin/analysis')
@login_required
def data_analysis():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取统计数据
    stats = {
        'total_events': db.session.execute(text('SELECT COUNT(*) FROM Event')).scalar(),
        'total_competitions': db.session.execute(text('SELECT COUNT(*) FROM Competition')).scalar(),
        'total_registrations': db.session.execute(text('SELECT COUNT(*) FROM Registration')).scalar(),
        'total_results': db.session.execute(text('SELECT COUNT(*) FROM Result')).scalar()
    }
    
    return render_template('admin/analysis.html', stats=stats)

# 备份与恢复
@app.route('/admin/backup')
@login_required
def backup_restore():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    return render_template('admin/backup.html')

# 学生仪表板
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取学生的报名记录
    registrations = db.session.execute(
        text('''
            SELECT r.*, e.EventName, e.EventType
            FROM Registration r
            JOIN Event e ON r.EventID = e.EventID
            WHERE r.StudentID = :student_id
            ORDER BY r.RegistrationTime DESC
        '''),
        {'student_id': current_user.id}
    ).fetchall()
    
    return render_template('student/dashboard.html', registrations=registrations)

# 裁判仪表板
@app.route('/referee/dashboard')
@login_required
def referee_dashboard():
    if current_user.role != 'Referee':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取今日比赛
    today = datetime.now().date()
    today_competitions = db.session.execute(
        text('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE DATE(c.ScheduledStartTime) = :today
            ORDER BY c.ScheduledStartTime ASC
        '''),
        {'today': today}
    ).fetchall()
    
    # 获取已录入的成绩
    recorded_results = db.session.execute(
        text('''
            SELECT r.*, e.EventName, s.Name AS StudentName
            FROM Result r
            JOIN Competition c ON r.CompetitionID = c.CompetitionID
            JOIN Event e ON c.EventID = e.EventID
            JOIN Student s ON r.StudentID = s.StudentID
            WHERE r.RefereeID = :referee_id
            ORDER BY r.RecordTime DESC
        '''),
        {'referee_id': current_user.id}
    ).fetchall()
    
    return render_template('referee/dashboard.html', 
                         today_competitions=today_competitions,
                         recorded_results=recorded_results)

# 录入成绩
@app.route('/referee/record_result/<competition_id>', methods=['GET', 'POST'])
@login_required
def record_result(competition_id):
    if current_user.role != 'Referee':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            value = request.form.get('value')
            ranking = request.form.get('ranking')
            score = request.form.get('score')
            is_record_breaking = request.form.get('is_record_breaking') == 'true'
            record_type = request.form.get('record_type') if is_record_breaking else None
            
            # 验证输入
            if not all([student_id, value, ranking, score]):
                flash('请填写所有必填字段！', 'error')
                return redirect(url_for('main.record_result', competition_id=competition_id))
            
            # 检查是否已经录入过该学生的成绩
            existing_result = db.session.execute(
                text('SELECT * FROM Result WHERE CompetitionID = :competition_id AND StudentID = :student_id'),
                {'competition_id': competition_id, 'student_id': student_id}
            ).first()
            
            if existing_result:
                flash('该学生的成绩已经录入！', 'error')
                return redirect(url_for('main.record_result', competition_id=competition_id))
            
            # 生成成绩ID
            result_id = f"RES{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 插入成绩记录
            db.session.execute(
                text('''
                    INSERT INTO Result (ResultID, CompetitionID, StudentID, Value, 
                                      Ranking, Score, IsRecordBreaking, RecordType, 
                                      RefereeID, RecordTime)
                    VALUES (:result_id, :competition_id, :student_id, :value,
                            :ranking, :score, :is_record_breaking, :record_type,
                            :referee_id, CURRENT_TIMESTAMP)
                '''),
                {
                    'result_id': result_id,
                    'competition_id': competition_id,
                    'student_id': student_id,
                    'value': value,
                    'ranking': ranking,
                    'score': score,
                    'is_record_breaking': is_record_breaking,
                    'record_type': record_type,
                    'referee_id': current_user.id
                }
            )
            db.session.commit()
            flash('成绩录入成功！', 'success')
            return redirect(url_for('main.referee_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'成绩录入失败: {str(e)}')
            flash('成绩录入失败，请重试！', 'error')
            return redirect(url_for('main.record_result', competition_id=competition_id))
    
    try:
        # 获取比赛信息
        competition = db.session.execute(
            text('''
                SELECT c.*, e.EventName, v.VenueName
                FROM Competition c
                JOIN Event e ON c.EventID = e.EventID
                JOIN Venue v ON c.VenueID = v.VenueID
                WHERE c.CompetitionID = :competition_id
            '''),
            {'competition_id': competition_id}
        ).first()
        
        if not competition:
            flash('未找到该比赛信息！', 'error')
            return redirect(url_for('main.referee_dashboard'))
        
        # 获取参赛学生列表
        participants = db.session.execute(
            text('''
                SELECT s.*, r.RegistrationID
                FROM Student s
                JOIN Registration r ON s.StudentID = r.StudentID
                WHERE r.EventID = :event_id AND r.Status = '已通过'
                AND s.StudentID NOT IN (
                    SELECT StudentID FROM Result WHERE CompetitionID = :competition_id
                )
            '''),
            {
                'event_id': competition.EventID,
                'competition_id': competition_id
            }
        ).fetchall()
        
        return render_template('referee/record_result.html',
                             competition=competition,
                             participants=participants)
                             
    except Exception as e:
        current_app.logger.error(f'获取比赛信息失败: {str(e)}')
        flash('获取比赛信息失败，请重试！', 'error')
        return redirect(url_for('main.referee_dashboard'))

# 修改成绩
@app.route('/referee/edit_result/<result_id>', methods=['GET', 'POST'])
@login_required
def edit_result(result_id):
    if current_user.role != 'Referee':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            value = request.form.get('value')
            ranking = request.form.get('ranking')
            score = request.form.get('score')
            is_record_breaking = request.form.get('is_record_breaking') == 'true'
            record_type = request.form.get('record_type') if is_record_breaking else None
            
            # 验证输入
            if not all([value, ranking, score]):
                flash('请填写所有必填字段！', 'error')
                return redirect(url_for('main.edit_result', result_id=result_id))
            
            # 更新成绩记录
            result = db.session.execute(
                text('''
                    UPDATE Result
                    SET Value = :value,
                        Ranking = :ranking,
                        Score = :score,
                        IsRecordBreaking = :is_record_breaking,
                        RecordType = :record_type,
                        RecordTime = CURRENT_TIMESTAMP
                    WHERE ResultID = :result_id AND RefereeID = :referee_id
                '''),
                {
                    'value': value,
                    'ranking': ranking,
                    'score': score,
                    'is_record_breaking': is_record_breaking,
                    'record_type': record_type,
                    'result_id': result_id,
                    'referee_id': current_user.id
                }
            )
            
            if result.rowcount == 0:
                flash('未找到该成绩记录或您没有权限修改！', 'error')
                return redirect(url_for('main.referee_dashboard'))
                
            db.session.commit()
            flash('成绩修改成功！', 'success')
            return redirect(url_for('main.referee_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'成绩修改失败: {str(e)}')
            flash('成绩修改失败，请重试！', 'error')
            return redirect(url_for('main.edit_result', result_id=result_id))
    
    try:
        # 获取成绩信息
        result = db.session.execute(
            text('''
                SELECT r.*, e.EventName, s.Name AS StudentName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                WHERE r.ResultID = :result_id AND r.RefereeID = :referee_id
            '''),
            {
                'result_id': result_id,
                'referee_id': current_user.id
            }
        ).first()
        
        if not result:
            flash('未找到该成绩记录或您没有权限修改！', 'error')
            return redirect(url_for('main.referee_dashboard'))
        
        return render_template('referee/edit_result.html', result=result)
        
    except Exception as e:
        current_app.logger.error(f'获取成绩信息失败: {str(e)}')
        flash('获取成绩信息失败，请重试！', 'error')
        return redirect(url_for('main.referee_dashboard'))

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# 用户密码修改
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            flash('请填写所有密码字段', 'error')
            return redirect(url_for('main.change_password'))
            
        if new_password != confirm_password:
            flash('新密码和确认密码不匹配', 'error')
            return redirect(url_for('main.change_password'))
            
        if not current_user.check_password(old_password):
            flash('当前密码错误', 'error')
            return redirect(url_for('main.change_password'))
            
        # 更新密码
        current_user.set_password(new_password)
        flash('密码修改成功！', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('change_password.html')

# 个人信息编辑
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        try:
            if current_user.role == 'student':
                db.session.execute(
                    text('UPDATE Student SET Phone = :phone, Email = :email WHERE StudentID = :id'),
                    {'phone': phone, 'email': email, 'id': current_user.id}
                )
            elif current_user.role == 'Referee':
                db.session.execute(
                    text('UPDATE Referee SET Phone = :phone, Email = :email WHERE RefereeID = :id'),
                    {'phone': phone, 'email': email, 'id': current_user.id}
                )
            elif current_user.role == 'admin':
                db.session.execute(
                    text('UPDATE Administrator SET Phone = :phone, Email = :email WHERE AdminID = :id'),
                    {'phone': phone, 'email': email, 'id': current_user.id}
                )
                
            db.session.commit()
            flash('个人信息更新成功！', 'success')
            return redirect(url_for('main.profile'))
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请稍后重试！', 'error')
            return redirect(url_for('main.edit_profile'))
        
    # 获取当前用户信息
    try:
        if current_user.role == 'student':
            user_info = db.session.execute(
                text('SELECT * FROM Student WHERE StudentID = :id'),
                {'id': current_user.id}
            ).first()
        elif current_user.role == 'Referee':
            user_info = db.session.execute(
                text('SELECT * FROM Referee WHERE RefereeID = :id'),
                {'id': current_user.id}
            ).first()
        else:
            user_info = db.session.execute(
                text('SELECT * FROM Administrator WHERE AdminID = :id'),
                {'id': current_user.id}
            ).first()
            
        return render_template('profile/edit.html', user_info=user_info)
    except Exception as e:
        flash('获取用户信息失败，请稍后重试！', 'error')
        return redirect(url_for('main.profile'))

# 个人信息查看
@app.route('/profile')
@login_required
def profile():
    try:
        if current_user.role == 'student':
            user_info = db.session.execute(
                text('SELECT * FROM Student WHERE StudentID = :id'),
                {'id': current_user.id}
            ).first()
        elif current_user.role == 'Referee':
            user_info = db.session.execute(
                text('SELECT * FROM Referee WHERE RefereeID = :id'),
                {'id': current_user.id}
            ).first()
        else:
            user_info = db.session.execute(
                text('SELECT * FROM Administrator WHERE AdminID = :id'),
                {'id': current_user.id}
            ).first()
            
        return render_template('profile/view.html', user_info=user_info)
    except Exception as e:
        flash('获取用户信息失败，请稍后重试！', 'error')
    return render_template('profile.html')

# 赛事报名
@app.route('/student/register_event', methods=['GET', 'POST'])
@login_required
def register_event():
    if current_user.role != 'student':
        flash('只有学生可以报名赛事！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        event_id = request.form.get('event_id')
        
        # 检查是否已经报名
        existing_registration = db.session.execute(
            text('SELECT * FROM Registration WHERE StudentID = :student_id AND EventID = :event_id'),
            {'student_id': current_user.id, 'event_id': event_id}
        ).first()
        
        if existing_registration:
            flash('您已经报名过该项目！', 'error')
            return redirect(url_for('main.register_event'))
            
        # 创建新的报名记录
        registration_id = f"REG{datetime.now().strftime('%Y%m%d%H%M%S')}"
        db.session.execute(
            text('INSERT INTO Registration (RegistrationID, StudentID, EventID, Status) '
                'VALUES (:reg_id, :student_id, :event_id, :status)'),
            {
                'reg_id': registration_id,
                'student_id': current_user.id,
                'event_id': event_id,
                'status': '待审核'
            }
        )
        db.session.commit()
        
        flash('报名成功，等待审核！', 'success')
        return redirect(url_for('main.student_dashboard'))
        
    # 获取可报名的赛事列表
    events = db.session.execute(
        text('''
            SELECT e.* 
            FROM Event e 
            WHERE e.EventID NOT IN (
                SELECT EventID 
                FROM Registration 
                WHERE StudentID = :student_id
            )
        '''),
        {'student_id': current_user.id}
    ).fetchall()
    
    return render_template('student/register_event.html', events=events)

# 成绩查询
@app.route('/student/results')
@login_required
def view_results():
    if current_user.role != 'student':
        flash('只有学生可以查看成绩！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取学生的所有比赛成绩
    results = db.session.execute(
        text('''
            SELECT r.*, e.EventName, c.GroupName, v.VenueName, c.ScheduledStartTime
            FROM Result r
            JOIN Competition c ON r.CompetitionID = c.CompetitionID
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE r.StudentID = :student_id
            ORDER BY c.ScheduledStartTime DESC
        '''),
        {'student_id': current_user.id}
    ).fetchall()
    
    return render_template('student/results.html', results=results)

# 编辑比赛项目
@app.route('/admin/events/<event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            event_name = request.form.get('event_name')
            event_type = request.form.get('event_type')
            gender_restriction = request.form.get('gender_restriction')
            max_participants = request.form.get('max_participants')
            rules = request.form.get('rules')
            is_final = request.form.get('is_final') == 'true'
            
            db.session.execute(
                text('''
                    UPDATE Event
                    SET EventName = :event_name,
                        EventType = :event_type,
                        GenderRestriction = :gender_restriction,
                        MaxParticipants = :max_participants,
                        Rules = :rules,
                        IsFinal = :is_final
                    WHERE EventID = :event_id
                '''),
                {
                    'event_id': event_id,
                    'event_name': event_name,
                    'event_type': event_type,
                    'gender_restriction': gender_restriction,
                    'max_participants': max_participants,
                    'rules': rules,
                    'is_final': is_final
                }
            )
            db.session.commit()
            flash('比赛项目更新成功！', 'success')
            return redirect(url_for('main.manage_events'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_event', event_id=event_id))
            
    # 获取项目信息
    event = db.session.execute(
        text('SELECT * FROM Event WHERE EventID = :event_id'),
        {'event_id': event_id}
    ).first()
    
    if not event:
        flash('未找到该比赛项目！', 'error')
        return redirect(url_for('main.manage_events'))
        
    return render_template('admin/edit_event.html', event=event)

# 删除比赛项目
@app.route('/admin/events/<event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        # 检查是否有关联的报名记录
        registrations = db.session.execute(
            text('SELECT COUNT(*) as count FROM Registration WHERE EventID = :event_id'),
            {'event_id': event_id}
        ).scalar()
        
        if registrations > 0:
            flash('该比赛项目已有报名记录，无法删除！', 'error')
            return redirect(url_for('main.manage_events'))
            
        # 删除项目
        db.session.execute(
            text('DELETE FROM Event WHERE EventID = :event_id'),
            {'event_id': event_id}
        )
        db.session.commit()
        flash('比赛项目删除成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_events'))

# 编辑场地
@app.route('/admin/venues/<venue_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_venue(venue_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            venue_name = request.form.get('venue_name')
            venue_type = request.form.get('venue_type')
            location = request.form.get('location')
            capacity = request.form.get('capacity')
            status = request.form.get('status')
            
            db.session.execute(
                text('''
                    UPDATE Venue
                    SET VenueName = :venue_name,
                        VenueType = :venue_type,
                        Location = :location,
                        Capacity = :capacity,
                        Status = :status
                    WHERE VenueID = :venue_id
                '''),
                {
                    'venue_id': venue_id,
                    'venue_name': venue_name,
                    'venue_type': venue_type,
                    'location': location,
                    'capacity': capacity,
                    'status': status
                }
            )
            db.session.commit()
            flash('场地信息更新成功！', 'success')
            return redirect(url_for('main.manage_venues'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_venue', venue_id=venue_id))
            
    # 获取场地信息
    venue = db.session.execute(
        text('SELECT * FROM Venue WHERE VenueID = :venue_id'),
        {'venue_id': venue_id}
    ).first()
    
    if not venue:
        flash('未找到该场地信息！', 'error')
        return redirect(url_for('main.manage_venues'))
        
    return render_template('admin/edit_venue.html', venue=venue)

# 删除场地
@app.route('/admin/venues/<venue_id>/delete', methods=['POST'])
@login_required
def delete_venue(venue_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        # 检查是否有关联的比赛
        competitions = db.session.execute(
            text('SELECT COUNT(*) as count FROM Competition WHERE VenueID = :venue_id'),
            {'venue_id': venue_id}
        ).scalar()
        
        if competitions > 0:
            flash('该场地已有比赛安排，无法删除！', 'error')
            return redirect(url_for('main.manage_venues'))
            
        # 删除场地
        db.session.execute(
            text('DELETE FROM Venue WHERE VenueID = :venue_id'),
            {'venue_id': venue_id}
        )
        db.session.commit()
        flash('场地删除成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_venues'))

# 编辑赛程
@app.route('/admin/competitions/<competition_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_competition(competition_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            event_id = request.form.get('event_id')
            group_name = request.form.get('group_name')
            venue_id = request.form.get('venue_id')
            scheduled_start_time = request.form.get('scheduled_start_time')
            scheduled_end_time = request.form.get('scheduled_end_time')
            status = request.form.get('status')
            
            db.session.execute(
                text('''
                    UPDATE Competition
                    SET EventID = :event_id,
                        GroupName = :group_name,
                        VenueID = :venue_id,
                        ScheduledStartTime = :scheduled_start_time,
                        ScheduledEndTime = :scheduled_end_time,
                        Status = :status
                    WHERE CompetitionID = :competition_id
                '''),
                {
                    'competition_id': competition_id,
                    'event_id': event_id,
                    'group_name': group_name,
                    'venue_id': venue_id,
                    'scheduled_start_time': scheduled_start_time,
                    'scheduled_end_time': scheduled_end_time,
                    'status': status
                }
            )
            db.session.commit()
            flash('赛程更新成功！', 'success')
            return redirect(url_for('main.manage_competitions'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_competition', competition_id=competition_id))
            
    # 获取赛程信息
    competition = db.session.execute(
        text('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE c.CompetitionID = :competition_id
        '''),
        {'competition_id': competition_id}
    ).first()
    
    if not competition:
        flash('未找到该赛程信息！', 'error')
        return redirect(url_for('main.manage_competitions'))
        
    # 获取所有比赛项目和场地
    events = db.session.execute(text('SELECT * FROM Event')).fetchall()
    venues = db.session.execute(text('SELECT * FROM Venue')).fetchall()
    
    return render_template('admin/edit_competition.html', 
                         competition=competition,
                         events=events,
                         venues=venues)

# 删除赛程
@app.route('/admin/competitions/<competition_id>/delete', methods=['POST'])
@login_required
def delete_competition(competition_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        # 检查是否有关联的成绩记录
        results = db.session.execute(
            text('SELECT COUNT(*) as count FROM Result WHERE CompetitionID = :competition_id'),
            {'competition_id': competition_id}
        ).scalar()
        
        if results > 0:
            flash('该赛程已有成绩记录，无法删除！', 'error')
            return redirect(url_for('main.manage_competitions'))
            
        # 删除赛程
        db.session.execute(
            text('DELETE FROM Competition WHERE CompetitionID = :competition_id'),
            {'competition_id': competition_id}
        )
        db.session.commit()
        flash('赛程删除成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_competitions'))

@app.route('/admin/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if not current_user.is_admin:
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_name = request.form.get('class_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # 检查学号是否已存在
            existing_student = db.session.execute(
                'SELECT * FROM Student WHERE StudentID = :student_id',
                {'student_id': student_id}
            ).fetchone()
            
            if existing_student:
                flash('该学号已存在', 'danger')
                return redirect(url_for('main.add_student'))
            
            # 添加新学生
            db.session.execute(
                'INSERT INTO Student (StudentID, Name, Gender, ClassName, Phone, Email, Password) '
                'VALUES (:student_id, :name, :gender, :class_name, :phone, :email, :password)',
                {
                    'student_id': student_id,
                    'name': name,
                    'gender': gender,
                    'class_name': class_name,
                    'phone': phone,
                    'email': email,
                    'password': generate_password_hash(password)
                }
            )
            db.session.commit()
            flash('学生添加成功', 'success')
            return redirect(url_for('main.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加学生失败：{str(e)}', 'danger')
            return redirect(url_for('main.add_student'))
    
    return render_template('admin/add_student.html')

@app.route('/admin/students/<student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if not current_user.is_admin:
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_name = request.form.get('class_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # 更新学生信息
            update_query = '''
                UPDATE Student 
                SET Name = :name,
                    Gender = :gender,
                    ClassName = :class_name,
                    Phone = :phone,
                    Email = :email
            '''
            params = {
                'student_id': student_id,
                'name': name,
                'gender': gender,
                'class_name': class_name,
                'phone': phone,
                'email': email
            }
            
            # 如果提供了新密码，则更新密码
            if password:
                update_query += ', Password = :password'
                params['password'] = generate_password_hash(password)
            
            update_query += ' WHERE StudentID = :student_id'
            
            db.session.execute(update_query, params)
            db.session.commit()
            flash('学生信息更新成功', 'success')
            return redirect(url_for('main.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新学生信息失败：{str(e)}', 'danger')
            return redirect(url_for('main.edit_student', student_id=student_id))
    
    # 获取学生信息
    student = db.session.execute(
        'SELECT * FROM Student WHERE StudentID = :student_id',
        {'student_id': student_id}
    ).fetchone()
    
    if not student:
        flash('未找到该学生', 'danger')
        return redirect(url_for('main.students'))
    
    return render_template('admin/edit_student.html', student=student)

@app.route('/admin/students/<student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    if not current_user.is_admin:
        flash('您没有权限执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # 检查是否有相关的报名记录
        registrations = db.session.execute(
            'SELECT * FROM Registration WHERE StudentID = :student_id',
            {'student_id': student_id}
        ).fetchall()
        
        if registrations:
            flash('该学生有报名记录，无法删除', 'danger')
            return redirect(url_for('main.students'))
        
        # 删除学生
        db.session.execute(
            'DELETE FROM Student WHERE StudentID = :student_id',
            {'student_id': student_id}
        )
        db.session.commit()
        flash('学生删除成功', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除学生失败：{str(e)}', 'danger')
    
    return redirect(url_for('main.students'))

# 添加裁判
@app.route('/admin/referees/add', methods=['GET', 'POST'])
@login_required
def add_referee():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            referee_id = request.form.get('referee_id')
            name = request.form.get('name')
            gender = request.form.get('gender')
            affiliation = request.form.get('affiliation')
            title = request.form.get('title')
            phone = request.form.get('phone')
            email = request.form.get('email')
            username = request.form.get('username')
            password = request.form.get('password')
            
            # 检查裁判ID是否已存在
            existing_referee = db.session.execute(
                text('SELECT * FROM Referee WHERE RefereeID = :referee_id'),
                {'referee_id': referee_id}
            ).first()
            
            if existing_referee:
                flash('该裁判ID已存在！', 'error')
                return redirect(url_for('main.add_referee'))
            
            # 检查用户名是否已存在
            existing_username = db.session.execute(
                text('SELECT * FROM Referee WHERE Username = :username'),
                {'username': username}
            ).first()
            
            if existing_username:
                flash('该用户名已存在！', 'error')
                return redirect(url_for('main.add_referee'))
            
            # 添加新裁判
            db.session.execute(
                text('''
                    INSERT INTO Referee (RefereeID, Name, Gender, Affiliation, Title,
                                       Phone, Email, Username, Password)
                    VALUES (:referee_id, :name, :gender, :affiliation, :title,
                            :phone, :email, :username, :password)
                '''),
                {
                    'referee_id': referee_id,
                    'name': name,
                    'gender': gender,
                    'affiliation': affiliation,
                    'title': title,
                    'phone': phone,
                    'email': email,
                    'username': username,
                    'password': generate_password_hash(password)
                }
            )
            db.session.commit()
            flash('裁判添加成功！', 'success')
            return redirect(url_for('main.manage_referees'))
            
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请重试！', 'error')
            return redirect(url_for('main.add_referee'))
            
    return render_template('admin/add_referee.html')

# 编辑裁判
@app.route('/admin/referees/<referee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_referee(referee_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            gender = request.form.get('gender')
            affiliation = request.form.get('affiliation')
            title = request.form.get('title')
            phone = request.form.get('phone')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # 更新裁判信息
            update_query = '''
                UPDATE Referee 
                SET Name = :name,
                    Gender = :gender,
                    Affiliation = :affiliation,
                    Title = :title,
                    Phone = :phone,
                    Email = :email
            '''
            params = {
                'referee_id': referee_id,
                'name': name,
                'gender': gender,
                'affiliation': affiliation,
                'title': title,
                'phone': phone,
                'email': email
            }
            
            # 如果提供了新密码，则更新密码
            if password:
                update_query += ', Password = :password'
                params['password'] = generate_password_hash(password)
            
            update_query += ' WHERE RefereeID = :referee_id'
            
            db.session.execute(text(update_query), params)
            db.session.commit()
            flash('裁判信息更新成功！', 'success')
            return redirect(url_for('main.manage_referees'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_referee', referee_id=referee_id))
    
    # 获取裁判信息
    referee = db.session.execute(
        text('SELECT * FROM Referee WHERE RefereeID = :referee_id'),
        {'referee_id': referee_id}
    ).first()
    
    if not referee:
        flash('未找到该裁判！', 'error')
        return redirect(url_for('main.manage_referees'))
    
    return render_template('admin/edit_referee.html', referee=referee)

# 删除裁判
@app.route('/admin/referees/<referee_id>/delete', methods=['POST'])
@login_required
def delete_referee(referee_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        # 检查是否有关联的成绩记录
        results = db.session.execute(
            text('SELECT COUNT(*) as count FROM Result WHERE RefereeID = :referee_id'),
            {'referee_id': referee_id}
        ).scalar()
        
        if results > 0:
            flash('该裁判已有成绩记录，无法删除！', 'error')
            return redirect(url_for('main.manage_referees'))
            
        # 删除裁判
        db.session.execute(
            text('DELETE FROM Referee WHERE RefereeID = :referee_id'),
            {'referee_id': referee_id}
        )
        db.session.commit()
        flash('裁判删除成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_referees'))

# 更新系统设置
@app.route('/admin/settings/update', methods=['POST'])
@login_required
def update_system_settings():
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        system_name = request.form.get('system_name')
        contact_email = request.form.get('contact_email')
        contact_phone = request.form.get('contact_phone')
        
        # 更新系统设置
        db.session.execute(
            text('''
                UPDATE SystemSettings 
                SET SystemName = :system_name,
                    ContactEmail = :contact_email,
                    ContactPhone = :contact_phone
                WHERE ID = 1
            '''),
            {
                'system_name': system_name,
                'contact_email': contact_email,
                'contact_phone': contact_phone
            }
        )
        db.session.commit()
        flash('系统设置更新成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('更新失败，请重试！', 'error')
        
    return redirect(url_for('main.system_settings'))

# 更新安全设置
@app.route('/admin/settings/security/update', methods=['POST'])
@login_required
def update_security_settings():
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        password_policy = request.form.get('password_policy')
        session_timeout = request.form.get('session_timeout')
        enable_2fa = request.form.get('enable_2fa') == 'on'
        
        # 更新安全设置
        db.session.execute(
            text('''
                UPDATE SystemSettings 
                SET PasswordPolicy = :password_policy,
                    SessionTimeout = :session_timeout,
                    Enable2FA = :enable_2fa
                WHERE ID = 1
            '''),
            {
                'password_policy': password_policy,
                'session_timeout': session_timeout,
                'enable_2fa': enable_2fa
            }
        )
        db.session.commit()
        flash('安全设置更新成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('更新失败，请重试！', 'error')
        
    return redirect(url_for('main.system_settings'))

# 更新通知设置
@app.route('/admin/settings/notification/update', methods=['POST'])
@login_required
def update_notification_settings():
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        email_notifications = request.form.get('email_notifications') == 'on'
        sms_notifications = request.form.get('sms_notifications') == 'on'
        notification_events = request.form.getlist('notification_events')
        
        # 更新通知设置
        db.session.execute(
            text('''
                UPDATE SystemSettings 
                SET EmailNotifications = :email_notifications,
                    SMSNotifications = :sms_notifications,
                    NotificationEvents = :notification_events
                WHERE ID = 1
            '''),
            {
                'email_notifications': email_notifications,
                'sms_notifications': sms_notifications,
                'notification_events': ','.join(notification_events)
            }
        )
        db.session.commit()
        flash('通知设置更新成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('更新失败，请重试！', 'error')
        
    return redirect(url_for('main.system_settings'))

# 更新备份设置
@app.route('/admin/settings/backup/update', methods=['POST'])
@login_required
def update_backup_settings():
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        auto_backup = request.form.get('auto_backup') == 'on'
        backup_frequency = request.form.get('backup_frequency')
        backup_retention = request.form.get('backup_retention')
        
        # 更新备份设置
        db.session.execute(
            text('''
                UPDATE SystemSettings 
                SET AutoBackup = :auto_backup,
                    BackupFrequency = :backup_frequency,
                    BackupRetention = :backup_retention
                WHERE ID = 1
            '''),
            {
                'auto_backup': auto_backup,
                'backup_frequency': backup_frequency,
                'backup_retention': backup_retention
            }
        )
        db.session.commit()
        flash('备份设置更新成功！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('更新失败，请重试！', 'error')
        
    return redirect(url_for('main.system_settings'))

