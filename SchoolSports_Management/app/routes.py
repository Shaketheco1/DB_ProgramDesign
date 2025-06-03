#由于项目不是特别复杂，决定使用一个蓝图完成
#该文件包含了程序需要的所有路由
from sched import scheduler

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
    #如果当前用户已登录
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
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取搜索参数
    student_search = request.form.get('student_search')
    registration_search = request.form.get('registration_search')
    competition_search = request.form.get('competition_search')
    result_search = request.form.get('result_search')

    conn = db.get_db()
    with conn.cursor() as cursor:
        # 获取系统统计数据 (不受搜索影响)
        cursor.execute('SELECT COUNT(*) as count FROM Student')
        student_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM Referee')
        referee_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM Administrator')
        admin_count = cursor.fetchone()['count']
        total_users = student_count + referee_count + admin_count

        cursor.execute('SELECT COUNT(*) as count FROM Competition WHERE Status = "进行中"')
        active_events = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM Registration WHERE DATE(RegistrationTime) = CURDATE()')
        today_registrations = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM Registration WHERE Status = "待审核"')
        pending_approvals = cursor.fetchone()['count']

        stats = {
            'total_users': total_users,
            'active_events': active_events,
            'today_registrations': today_registrations,
            'pending_approvals': pending_approvals
        }

        # 获取最近的待审核报名记录 (如果未进行报名搜索)
        recent_registrations = []
        if not registration_search:
            cursor.execute('''
                SELECT r.*, s.Name AS StudentName, e.EventName, e.EventType,
                       c.ClassName, c.Department
                FROM Registration r
                JOIN Student s ON r.StudentID = s.StudentID
                JOIN Event e ON r.EventID = e.EventID
                JOIN Class c ON s.ClassID = c.ClassID
                WHERE r.Status = '待审核'
                ORDER BY r.RegistrationTime DESC
                LIMIT 5
            ''')
            recent_registrations = cursor.fetchall()

        # 获取今日比赛安排 (如果未进行比赛搜索)
        today_competitions = []
        if not competition_search:
            cursor.execute('''
                SELECT c.*, e.EventName, v.VenueName, r.Name AS RefereeName
                FROM Competition c
                JOIN Event e ON c.EventID = e.EventID
                JOIN Venue v ON c.VenueID = v.VenueID
                LEFT JOIN Referee r ON c.RefereeID = r.RefereeID
                WHERE DATE(c.ScheduledStartTime) = CURDATE()
            ''')
            today_competitions = cursor.fetchall()

        # 获取最近的成绩记录 (如果未进行成绩搜索)
        recent_results = []
        if not result_search:
            cursor.execute('''
                SELECT r.*, s.Name AS StudentName, e.EventName, c.GroupName,
                       v.VenueName, ref.Name AS RefereeName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                JOIN Venue v ON c.VenueID = v.VenueID
                JOIN Referee ref ON r.RefereeID = ref.RefereeID
                ORDER BY r.RecordTime DESC
                LIMIT 5
            ''')
            recent_results = cursor.fetchall()

        # 获取班级报名统计 (不受搜索影响)
        cursor.execute('''
            SELECT c.ClassName, c.Department, COUNT(r.RegistrationID) as registration_count
            FROM Class c
            LEFT JOIN Student s ON c.ClassID = s.ClassID
            LEFT JOIN Registration r ON s.StudentID = r.StudentID AND r.Status = '已通过'
            GROUP BY c.ClassID
            ORDER BY registration_count DESC
            LIMIT 5
        ''')
        class_stats = cursor.fetchall()

        # 根据搜索条件进行查询
        searched_students = []
        if student_search:
            # 简单示例：按学生姓名或学号搜索
            search_pattern = f'%%{student_search}%%'
            cursor.execute('''
                SELECT s.*, c.ClassName, c.Department
                FROM Student s
                JOIN Class c ON s.ClassID = c.ClassID
                WHERE s.Name LIKE %s OR s.StudentID LIKE %s
                ORDER BY s.StudentID
            ''', (search_pattern, search_pattern))
            searched_students = cursor.fetchall()

        searched_registrations = []
        if registration_search:
            # 简单示例：按学生姓名或项目名称搜索待审核报名
            search_pattern = f'%%{registration_search}%%'
            cursor.execute('''
                SELECT r.*, s.Name AS StudentName, e.EventName, e.EventType,
                       c.ClassName, c.Department
                FROM Registration r
                JOIN Student s ON r.StudentID = s.StudentID
                JOIN Event e ON r.EventID = e.EventID
                JOIN Class c ON s.ClassID = c.ClassID
                WHERE r.Status = '待审核' AND (s.Name LIKE %s OR e.EventName LIKE %s)
                ORDER BY r.RegistrationTime DESC
            ''', (search_pattern, search_pattern))
            searched_registrations = cursor.fetchall()
            # 如果进行了报名搜索，则不显示最近的待审核报名
            recent_registrations = []

        searched_competitions = []
        if competition_search:
            # 简单示例：按项目名称或场地名称搜索比赛安排
            search_pattern = f'%%{competition_search}%%'
            cursor.execute('''
                SELECT c.*, e.EventName, v.VenueName, r.Name AS RefereeName
                FROM Competition c
                JOIN Event e ON c.EventID = e.EventID
                JOIN Venue v ON c.VenueID = v.VenueID
                LEFT JOIN Referee r ON c.RefereeID = r.RefereeID
                WHERE e.EventName LIKE %s OR v.VenueName LIKE %s
                ORDER BY c.ScheduledStartTime DESC
            ''', (search_pattern, search_pattern))
            searched_competitions = cursor.fetchall()
            # 如果进行了比赛搜索，则不显示今日比赛安排
            today_competitions = []

        searched_results = []
        if result_search:
            # 简单示例：按学生姓名或项目名称搜索成绩记录
            search_pattern = f'%%{result_search}%%'
            cursor.execute('''
                SELECT r.*, s.Name AS StudentName, e.EventName, c.GroupName,
                       v.VenueName, ref.Name AS RefereeName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                JOIN Venue v ON c.VenueID = v.VenueID
                JOIN Referee ref ON r.RefereeID = ref.RefereeID
                WHERE s.Name LIKE %s OR e.EventName LIKE %s
                ORDER BY r.RecordTime DESC
            ''', (search_pattern, search_pattern))
            searched_results = cursor.fetchall()
            # 如果进行了成绩搜索，则不显示最近成绩记录
            recent_results = []


    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_registrations=recent_registrations,
                         today_competitions=today_competitions,
                         recent_results=recent_results,
                         class_stats=class_stats,
                         searched_students=searched_students,
                         searched_registrations=searched_registrations,
                         searched_competitions=searched_competitions,
                         searched_results=searched_results,
                         student_search=student_search,
                         registration_search=registration_search,
                         competition_search=competition_search,
                         result_search=result_search)

# 比赛项目管理
@app.route('/admin/events')
@login_required
def manage_events():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Event ORDER BY EventID')
        events = cursor.fetchall()
    
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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO Event (EventID, EventName, EventType, GenderRestriction,
                                     MaxParticipants, Rules, IsFinal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (event_id, event_name, event_type, gender_restriction,
                      max_participants, rules, is_final))
                conn.commit()
            flash('比赛项目添加成功！', 'success')
            return redirect(url_for('main.manage_events'))
            
        except Exception as e:
            conn.rollback()
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
        
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            ORDER BY c.ScheduledStartTime DESC
        ''')
        competitions = cursor.fetchall()
    
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
            referee_id = request.form.get('referee_id')
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO Competition (CompetitionID, EventID, GroupName,
                                          ScheduledStartTime, ScheduledEndTime,
                                          VenueID, RefereeID, Status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, '未开始')
                ''', (competition_id, event_id, group_name,
                      scheduled_start_time, scheduled_end_time,
                      venue_id, referee_id))
                conn.commit()
            flash('赛程添加成功！', 'success')
            return redirect(url_for('main.manage_competitions'))
            
        except Exception as e:
            conn.rollback()
            flash('添加失败，请重试！', 'error')
            return redirect(url_for('main.add_competition'))
            
    # 获取所有比赛项目和场地
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Event')
        events = cursor.fetchall()
        cursor.execute('SELECT * FROM Venue')
        venues = cursor.fetchall()
        cursor.execute('SELECT * FROM Referee')
        referees = cursor.fetchall()
    
    return render_template('admin/add_competition.html', 
                         events=events, 
                         venues=venues,
                         referees=referees)

# 编辑赛程
@app.route('/admin/competitions/<competition_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_competition(competition_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))

    # 获取赛程信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT c.*, e.EventName, v.VenueName, r.Name AS RefereeName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            LEFT JOIN Referee r ON c.RefereeID = r.RefereeID
            WHERE c.CompetitionID = %s
        ''', (competition_id,))
        competition = cursor.fetchone()

    if not competition:
        flash('未找到该赛程信息！', 'error')
        return redirect(url_for('main.manage_competitions'))

    if request.method == 'POST':
        try:
            group_name = request.form.get('group_name')
            venue_id = request.form.get('venue_id')
            scheduled_start_time = request.form.get('scheduled_start_time')
            scheduled_end_time = request.form.get('scheduled_end_time')
            status = request.form.get('status')
            referee_id = request.form.get('referee_id')
            
            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 根据状态设置实际开始和结束时间
            actual_start_time = competition['ActualStartTime']
            actual_end_time = competition['ActualEndTime']
            
            if status == '进行中' and competition['Status'] != '进行中':
                actual_start_time = current_time
            elif status == '已结束' and competition['Status'] != '已结束':
                actual_end_time = current_time
                if not actual_start_time:
                    actual_start_time = current_time

            # 更新比赛信息
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE Competition
                    SET GroupName = %s,
                        VenueID = %s,
                        ScheduledStartTime = %s,
                        ScheduledEndTime = %s,
                        Status = %s,
                        ActualStartTime = %s,
                        ActualEndTime = %s,
                        RefereeID = %s
                    WHERE CompetitionID = %s
                ''', (group_name, venue_id, scheduled_start_time,
                      scheduled_end_time, status, actual_start_time,
                      actual_end_time, referee_id, competition_id))
                conn.commit()
            flash('赛程更新成功！', 'success')
            return redirect(url_for('main.manage_competitions'))

        except Exception as e:
            conn.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_competition', competition_id=competition_id))

    # 获取可用场地
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Venue WHERE Status = "可用"')
        venues = cursor.fetchall()
        
        # 获取所有裁判
        cursor.execute('SELECT * FROM Referee')
        referees = cursor.fetchall()

    return render_template('admin/edit_competition.html',
                         competition=competition,
                         venues=venues,
                         referees=referees)

# 裁判成绩录入
@app.route('/referee/competitions/<competition_id>/results', methods=['GET', 'POST'])
@login_required
def manage_competition_results(competition_id):
    if current_user.role != 'Referee':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
    
    # 检查当前裁判是否是这场比赛的主持裁判
    competition = db.session.execute(
        text('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE c.CompetitionID = :competition_id
            AND c.RefereeID = :referee_id
        '''),
        {
            'competition_id': competition_id,
            'referee_id': current_user.id
        }
    ).first()
    
    if not competition:
        flash('您不是这场比赛的主持裁判！', 'error')
        return redirect(url_for('main.referee_dashboard'))
        
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            value = request.form.get('value')
            ranking = request.form.get('ranking')
            score = request.form.get('score')
            is_record_breaking = request.form.get('is_record_breaking') == 'true'
            record_type = request.form.get('record_type') if is_record_breaking else None
            
            # 检查是否已经录入过该学生的成绩
            existing_result = db.session.execute(
                text('''
                    SELECT * FROM Result 
                    WHERE CompetitionID = :competition_id 
                    AND StudentID = :student_id
                '''),
                {
                    'competition_id': competition_id,
                    'student_id': student_id
                }
            ).first()
            
            if existing_result:
                # 更新已有成绩
                db.session.execute(
                    text('''
                        UPDATE Result
                        SET Value = :value,
                            Ranking = :ranking,
                            Score = :score,
                            IsRecordBreaking = :is_record_breaking,
                            RecordType = :record_type,
                            RecordTime = CURRENT_TIMESTAMP
                        WHERE CompetitionID = :competition_id
                        AND StudentID = :student_id
                    '''),
                    {
                        'value': value,
                        'ranking': ranking,
                        'score': score,
                        'is_record_breaking': is_record_breaking,
                        'record_type': record_type,
                        'competition_id': competition_id,
                        'student_id': student_id
                    }
                )
            else:
                # 插入新成绩
                result_id = f"RES{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
            flash('成绩保存成功！', 'success')
            return redirect(url_for('main.manage_competition_results', competition_id=competition_id))
            
        except Exception as e:
            db.session.rollback()
            flash('保存失败，请重试！', 'error')
            return redirect(url_for('main.manage_competition_results', competition_id=competition_id))
    
    # 获取已录入的成绩
    results = db.session.execute(
        text('''
            SELECT r.*, s.Name AS StudentName
            FROM Result r
            JOIN Student s ON r.StudentID = s.StudentID
            WHERE r.CompetitionID = :competition_id
            ORDER BY r.Ranking ASC
        '''),
        {'competition_id': competition_id}
    ).fetchall()
    
    # 获取参赛学生列表
    participants = db.session.execute(
        text('''
            SELECT s.*, r.RegistrationID
            FROM Student s
            JOIN Registration r ON s.StudentID = r.StudentID
            WHERE r.EventID = :event_id AND r.Status = '已通过'
        '''),
        {'event_id': competition.EventID}
    ).fetchall()
    
    return render_template('referee/competition_results.html',
                         competition=competition,
                         results=results,
                         participants=participants)

# 学生管理
@app.route('/admin/students')
@login_required
def students():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    # 获取所有学生信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Student ORDER BY StudentID')
        students = cursor.fetchall()
    
    return render_template('admin/students.html', students=students)

# 裁判管理
@app.route('/admin/referees')
@login_required
def manage_referees():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Referee ORDER BY RefereeID')
        referees = cursor.fetchall()
    
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
@app.route('/student/dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取搜索参数
    registration_event_search = request.form.get('registration_event_search')
    registration_status_search = request.form.get('registration_status_search')
    result_event_search = request.form.get('result_event_search')
    result_group_search = request.form.get('result_group_search')

    conn = db.get_db()
    with conn.cursor() as cursor:
        # 获取学生的报名记录 (根据搜索条件过滤)
        registration_query = '''
            SELECT r.*, e.EventName, e.EventType
            FROM Registration r
            JOIN Event e ON r.EventID = e.EventID
            WHERE r.StudentID = %s
        '''
        registration_params = [current_user.id]

        if registration_event_search:
            registration_query += ' AND e.EventName LIKE %s'
            registration_params.append(f'%%{registration_event_search}%%')

        if registration_status_search:
            registration_query += ' AND r.Status = %s'
            registration_params.append(registration_status_search)

        registration_query += ' ORDER BY r.RegistrationTime DESC'

        cursor.execute(registration_query, registration_params)
        registrations = cursor.fetchall()
        
        # 获取比赛成绩 (根据搜索条件过滤)
        result_query = '''
            SELECT r.*, e.EventName, c.GroupName, c.ScheduledStartTime
            FROM Result r
            JOIN Competition c ON r.CompetitionID = c.CompetitionID
            JOIN Event e ON c.EventID = e.EventID
            WHERE r.StudentID = %s
        '''
        result_params = [current_user.id]

        if result_event_search:
            result_query += ' AND e.EventName LIKE %s'
            result_params.append(f'%%{result_event_search}%%')

        if result_group_search:
            result_query += ' AND c.GroupName LIKE %s'
            result_params.append(f'%%{result_group_search}%%')

        result_query += ' ORDER BY c.ScheduledStartTime DESC'

        cursor.execute(result_query, result_params)
        print("Executing SQL Query:", result_query)
        print("With parameters:", result_params)
        results = cursor.fetchall()
    
    return render_template('student/dashboard.html', 
                         registrations=registrations,
                         results=results,
                         registration_event_search=registration_event_search,
                         registration_status_search=registration_status_search,
                         result_event_search=result_event_search,
                         result_group_search=result_group_search)

# 裁判仪表板
@app.route('/referee/dashboard', methods=['GET', 'POST'])
@login_required
def referee_dashboard():
    if current_user.role != 'Referee':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取搜索参数
    result_search = request.form.get('result_search')

    conn = db.get_db()
    with conn.cursor() as cursor:
        # 获取今日比赛 (不受成绩搜索影响)
        today = datetime.now().date()
        cursor.execute('''
            SELECT c.*, e.EventName, v.VenueName
            FROM Competition c
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE DATE(c.ScheduledStartTime) = %s
            AND c.RefereeID = %s
            ORDER BY c.ScheduledStartTime ASC
        ''', (today, current_user.id))
        today_competitions = cursor.fetchall()
        
        # 获取最近录入的成绩 (如果未进行成绩搜索)
        recorded_results = []
        if not result_search:
            cursor.execute('''
                SELECT r.*, e.EventName, s.Name AS StudentName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                WHERE r.RefereeID = %s
                ORDER BY r.RecordTime DESC
                LIMIT 10
            ''', (current_user.id,))
            recorded_results = cursor.fetchall()

        # 根据搜索条件进行成绩查询
        searched_results = []
        if result_search:
            search_pattern = f'%%{result_search}%%'
            cursor.execute('''
                SELECT r.*, e.EventName, s.Name AS StudentName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                WHERE r.RefereeID = %s
                AND (e.EventName LIKE %s OR s.Name LIKE %s)
                ORDER BY r.RecordTime DESC
            ''', (current_user.id, search_pattern, search_pattern))
            searched_results = cursor.fetchall()

    return render_template('referee/dashboard.html',
                         today_competitions=today_competitions,
                         recorded_results=recorded_results,
                         searched_results=searched_results,
                         result_search=result_search)

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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 检查是否已经录入过该学生的成绩
                cursor.execute('''
                    SELECT * FROM Result 
                    WHERE CompetitionID = %s AND StudentID = %s
                ''', (competition_id, student_id))
                existing_result = cursor.fetchone()
                
                if existing_result:
                    flash('该学生的成绩已经录入！', 'error')
                    return redirect(url_for('main.record_result', competition_id=competition_id))
                
                # 生成成绩ID
                result_id = f"RES{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # 插入成绩记录
                cursor.execute('''
                    INSERT INTO Result (ResultID, CompetitionID, StudentID, Value, 
                                      Ranking, Score, IsRecordBreaking, RecordType, 
                                      RefereeID, RecordTime)
                    VALUES (:result_id, :competition_id, :student_id, :value,
                            :ranking, :score, :is_record_breaking, :record_type,
                            :referee_id, CURRENT_TIMESTAMP)
                ''', (result_id, competition_id, student_id, value,
                      ranking, score, is_record_breaking, record_type,
                      current_user.id))
                conn.commit()
            flash('成绩录入成功！', 'success')
            return redirect(url_for('main.referee_dashboard'))
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'成绩录入失败: {str(e)}')
            flash('成绩录入失败，请重试！', 'error')
            return redirect(url_for('main.record_result', competition_id=competition_id))
    
    try:
        # 获取比赛信息
        conn = db.get_db()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT c.*, e.EventName, v.VenueName
                FROM Competition c
                JOIN Event e ON c.EventID = e.EventID
                JOIN Venue v ON c.VenueID = v.VenueID
                WHERE c.CompetitionID = %s AND c.RefereeID = %s
            ''', (competition_id, current_user.id))
            competition = cursor.fetchone()
            
            if not competition:
                flash('未找到该比赛信息或您不是该比赛的主持裁判！', 'error')
                return redirect(url_for('main.referee_dashboard'))
            
            # 获取参赛学生列表（已通过报名审核且未录入成绩的学生）
            cursor.execute('''
                SELECT s.*
                FROM Student s
                JOIN Registration r ON s.StudentID = r.StudentID
                WHERE r.EventID = %s 
                AND r.Status = '已通过'
                AND s.StudentID NOT IN (
                    SELECT StudentID FROM Result WHERE CompetitionID = %s
                )
            ''', (competition['EventID'], competition_id))
            participants = cursor.fetchall()
        
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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 更新成绩记录
                cursor.execute('''
                    UPDATE Result
                    SET Value = %s,
                        Ranking = %s,
                        Score = %s,
                        IsRecordBreaking = %s,
                        RecordType = %s,
                        RecordTime = CURRENT_TIMESTAMP
                    WHERE ResultID = %s AND RefereeID = %s
                ''', (value, ranking, score, is_record_breaking,
                      record_type, result_id, current_user.id))
                
                if cursor.rowcount == 0:
                    flash('未找到该成绩记录或您没有权限修改！', 'error')
                    return redirect(url_for('main.referee_dashboard'))
                    
                conn.commit()
            flash('成绩修改成功！', 'success')
            return redirect(url_for('main.referee_dashboard'))
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'成绩修改失败: {str(e)}')
            flash('成绩修改失败，请重试！', 'error')
            return redirect(url_for('main.edit_result', result_id=result_id))
    
    try:
        # 获取成绩信息
        conn = db.get_db()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT r.*, e.EventName, s.Name AS StudentName
                FROM Result r
                JOIN Competition c ON r.CompetitionID = c.CompetitionID
                JOIN Event e ON c.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                WHERE r.ResultID = %s AND r.RefereeID = %s
            ''', (result_id, current_user.id))
            result = cursor.fetchone()
            
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
        
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否已经报名
            cursor.execute('SELECT * FROM Registration WHERE StudentID = %s AND EventID = %s',
                         (current_user.id, event_id))
            existing_registration = cursor.fetchone()
            
            if existing_registration:
                flash('您已经报名过该项目！', 'error')
                return redirect(url_for('main.register_event'))
                
            # 创建新的报名记录
            registration_id = f"REG{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute('''
                INSERT INTO Registration (RegistrationID, StudentID, EventID, Status) 
                VALUES (%s, %s, %s, %s)
            ''', (registration_id, current_user.id, event_id, '待审核'))
            conn.commit()
        
        flash('报名成功，等待审核！', 'success')
        return redirect(url_for('main.student_dashboard'))
        
    # 获取可报名的赛事列表
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT e.* 
            FROM Event e 
            WHERE e.EventID NOT IN (
                SELECT EventID 
                FROM Registration 
                WHERE StudentID = %s
            )
        ''', (current_user.id,))
        events = cursor.fetchall()
    
    return render_template('student/register_event.html', events=events)

# 成绩查询
@app.route('/student/results')
@login_required
def view_results():
    if current_user.role != 'student':
        flash('只有学生可以查看成绩！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取学生的所有比赛成绩
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT r.*, e.EventName, c.GroupName, v.VenueName, c.ScheduledStartTime
            FROM Result r
            JOIN Competition c ON r.CompetitionID = c.CompetitionID
            JOIN Event e ON c.EventID = e.EventID
            JOIN Venue v ON c.VenueID = v.VenueID
            WHERE r.StudentID = %s
            ORDER BY c.ScheduledStartTime DESC
        ''', (current_user.id,))
        results = cursor.fetchall()
    
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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE Event
                    SET EventName = %s,
                        EventType = %s,
                        GenderRestriction = %s,
                        MaxParticipants = %s,
                        Rules = %s,
                        IsFinal = %s
                    WHERE EventID = %s
                ''', (event_name, event_type, gender_restriction,
                      max_participants, rules, is_final, event_id))
                conn.commit()
            flash('比赛项目更新成功！', 'success')
            return redirect(url_for('main.manage_events'))
            
        except Exception as e:
            conn.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_event', event_id=event_id))
            
    # 获取项目信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Event WHERE EventID = %s', (event_id,))
        event = cursor.fetchone()
    
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
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否有关联的报名记录
            cursor.execute('SELECT COUNT(*) as count FROM Registration WHERE EventID = %s', (event_id,))
            registrations = cursor.fetchone()['count']
            
            if registrations > 0:
                flash('该比赛项目已有报名记录，无法删除！', 'error')
                return redirect(url_for('main.manage_events'))
                
            # 删除项目
            cursor.execute('DELETE FROM Event WHERE EventID = %s', (event_id,))
            conn.commit()
            flash('比赛项目删除成功！', 'success')
        
    except Exception as e:
        conn.rollback()
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

# 删除赛程
@app.route('/admin/competitions/<competition_id>/delete', methods=['POST'])
@login_required
def delete_competition(competition_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否有关联的成绩记录
            cursor.execute('SELECT COUNT(*) as count FROM Result WHERE CompetitionID = %s', (competition_id,))
            results = cursor.fetchone()['count']
            
            if results > 0:
                flash('该赛程已有成绩记录，无法删除！', 'error')
                return redirect(url_for('main.manage_competitions'))
                
            # 删除赛程
            cursor.execute('DELETE FROM Competition WHERE CompetitionID = %s', (competition_id,))
            conn.commit()
            flash('赛程删除成功！', 'success')
        
    except Exception as e:
        conn.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_competitions'))

@app.route('/admin/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_id = request.form.get('class_id')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 检查学号是否已存在
                cursor.execute('SELECT * FROM Student WHERE StudentID = %s', (student_id,))
                existing_student = cursor.fetchone()
                
                if existing_student:
                    flash('该学号已存在', 'danger')
                    return redirect(url_for('main.add_student'))
                
                # 添加新学生
                cursor.execute('''
                    INSERT INTO Student (StudentID, Name, Gender, ClassID, Phone, Email, Password)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (student_id, name, gender, class_id, phone, email, generate_password_hash(password)))
                conn.commit()
            flash('学生添加成功', 'success')
            return redirect(url_for('main.students'))
            
        except Exception as e:
            conn.rollback()
            flash(f'添加学生失败：{str(e)}', 'danger')
            return redirect(url_for('main.add_student'))
    
    # 获取所有班级信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Class ORDER BY ClassID')
        classes = cursor.fetchall()
    
    return render_template('admin/add_student.html', classes=classes)

@app.route('/admin/students/<student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_id = request.form.get('class_id')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 更新学生信息
                update_query = '''
                    UPDATE Student 
                    SET Name = %s,
                        Gender = %s,
                        ClassID = %s,
                        Phone = %s,
                        Email = %s
                '''
                params = [name, gender, class_id, phone, email]
                
                # 如果提供了新密码，则更新密码
                if password:
                    update_query += ', Password = %s'
                    params.append(generate_password_hash(password))
                
                update_query += ' WHERE StudentID = %s'
                params.append(student_id)
                
                cursor.execute(update_query, params)
                conn.commit()
            flash('学生信息更新成功', 'success')
            return redirect(url_for('main.students'))
            
        except Exception as e:
            conn.rollback()
            flash(f'更新学生信息失败：{str(e)}', 'danger')
            return redirect(url_for('main.edit_student', student_id=student_id))
    
    # 获取学生信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Student WHERE StudentID = %s', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('未找到该学生', 'danger')
            return redirect(url_for('main.students'))
        
        # 获取所有班级信息
        cursor.execute('SELECT * FROM Class ORDER BY ClassID')
        classes = cursor.fetchall()
    
    return render_template('admin/edit_student.html', student=student, classes=classes)

@app.route('/admin/students/<student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否有相关的报名记录
            cursor.execute('SELECT * FROM Registration WHERE StudentID = %s', (student_id,))
            registrations = cursor.fetchall()
            
            if registrations:
                flash('该学生有报名记录，无法删除', 'danger')
                return redirect(url_for('main.students'))
            
            # 删除学生
            cursor.execute('DELETE FROM Student WHERE StudentID = %s', (student_id,))
            conn.commit()
            flash('学生删除成功', 'success')
        
    except Exception as e:
        conn.rollback()
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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 检查裁判ID是否已存在
                cursor.execute('SELECT * FROM Referee WHERE RefereeID = %s', (referee_id,))
                existing_referee = cursor.fetchone()
                
                if existing_referee:
                    flash('该裁判ID已存在！', 'error')
                    return redirect(url_for('main.add_referee'))
                
                # 检查用户名是否已存在
                cursor.execute('SELECT * FROM Referee WHERE Username = %s', (username,))
                existing_username = cursor.fetchone()
                
                if existing_username:
                    flash('该用户名已存在！', 'error')
                    return redirect(url_for('main.add_referee'))
                
                # 添加新裁判
                cursor.execute('''
                    INSERT INTO Referee (RefereeID, Name, Gender, Affiliation, Title,
                                       Phone, Email, Username, Password)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (referee_id, name, gender, affiliation, title,
                      phone, email, username, generate_password_hash(password)))
                conn.commit()
            flash('裁判添加成功！', 'success')
            return redirect(url_for('main.manage_referees'))
            
        except Exception as e:
            conn.rollback()
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
            
            conn = db.get_db()
            with conn.cursor() as cursor:
                # 更新裁判信息
                update_query = '''
                    UPDATE Referee 
                    SET Name = %s,
                        Gender = %s,
                        Affiliation = %s,
                        Title = %s,
                        Phone = %s,
                        Email = %s
                '''
                params = [name, gender, affiliation, title, phone, email]
                
                # 如果提供了新密码，则更新密码
                if password:
                    update_query += ', Password = %s'
                    params.append(generate_password_hash(password))
                
                update_query += ' WHERE RefereeID = %s'
                params.append(referee_id)
                
                cursor.execute(update_query, params)
                conn.commit()
            flash('裁判信息更新成功！', 'success')
            return redirect(url_for('main.manage_referees'))
            
        except Exception as e:
            conn.rollback()
            flash('更新失败，请重试！', 'error')
            return redirect(url_for('main.edit_referee', referee_id=referee_id))
    
    # 获取裁判信息
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM Referee WHERE RefereeID = %s', (referee_id,))
        referee = cursor.fetchone()
        
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
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否有关联的成绩记录
            cursor.execute('SELECT COUNT(*) as count FROM Result WHERE RefereeID = %s', (referee_id,))
            results = cursor.fetchone()['count']
            
            if results > 0:
                flash('该裁判已有成绩记录，无法删除！', 'error')
                return redirect(url_for('main.manage_referees'))
                
            # 删除裁判
            cursor.execute('DELETE FROM Referee WHERE RefereeID = %s', (referee_id,))
            conn.commit()
            flash('裁判删除成功！', 'success')
        
    except Exception as e:
        conn.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.manage_referees'))

# 报名审核列表
@app.route('/admin/registrations')
@login_required
def manage_registrations():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    # 获取所有待审核的报名记录
    conn = db.get_db()
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT r.*, s.Name AS StudentName, e.EventName, e.EventType, e.GenderRestriction,
                   c.ClassName, c.Department
            FROM Registration r
            JOIN Student s ON r.StudentID = s.StudentID
            JOIN Event e ON r.EventID = e.EventID
            JOIN Class c ON s.ClassID = c.ClassID
            WHERE r.Status = '待审核'
            ORDER BY r.RegistrationTime DESC
        ''')
        registrations = cursor.fetchall()
    
    return render_template('admin/registrations.html', registrations=registrations)

# 审核报名
@app.route('/admin/registrations/<registration_id>/review', methods=['POST'])
@login_required
def review_registration(registration_id):
    if current_user.role != 'admin':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        action = request.form.get('action')
        approval_note = request.form.get('approval_note', '')
        
        if action not in ['approve', 'reject']:
            flash('无效的操作！', 'error')
            return redirect(url_for('main.manage_registrations'))
            
        # 更新报名状态
        status = '已通过' if action == 'approve' else '已拒绝'
        
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 获取报名信息
            cursor.execute('''
                SELECT r.*, e.EventName, e.MaxParticipants, e.GenderRestriction,
                       s.Gender, s.ClassID
                FROM Registration r
                JOIN Event e ON r.EventID = e.EventID
                JOIN Student s ON r.StudentID = s.StudentID
                WHERE r.RegistrationID = %s
            ''', (registration_id,))
            registration = cursor.fetchone()
            
            if not registration:
                flash('未找到该报名记录！', 'error')
                return redirect(url_for('main.manage_registrations'))
            
            # 如果是通过，需要检查一些条件
            if action == 'approve':
                # 检查性别限制
                if registration['GenderRestriction'] != '不限' and registration['GenderRestriction'] != registration['Gender']:
                    flash('该学生不符合项目的性别要求！', 'error')
                    return redirect(url_for('main.manage_registrations'))
                
                # 检查班级报名人数是否超过限制
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM Registration r
                    JOIN Student s ON r.StudentID = s.StudentID
                    WHERE r.EventID = %s AND s.ClassID = %s AND r.Status = '已通过'
                ''', (registration['EventID'], registration['ClassID']))
                class_count = cursor.fetchone()['count']
                
                if class_count >= registration['MaxParticipants']:
                    flash('该班级的报名人数已达到上限！', 'error')
                    return redirect(url_for('main.manage_registrations'))
            
            # 更新报名状态
            cursor.execute('''
                UPDATE Registration
                SET Status = %s,
                    ApprovalTime = CURRENT_TIMESTAMP,
                    ApproveID = %s,
                    ApprovalNote = %s
                WHERE RegistrationID = %s
            ''', (status, current_user.id, approval_note, registration_id))
            conn.commit()
            
            flash('审核完成！', 'success')
            return redirect(url_for('main.manage_registrations'))
            
    except Exception as e:
        conn.rollback()
        flash('审核失败，请重试！', 'error')
        return redirect(url_for('main.manage_registrations'))

# 查看学生报名记录
@app.route('/admin/students/<student_id>/registrations')
@login_required
def view_student_registrations(student_id):
    if current_user.role != 'admin':
        flash('您没有权限访问此页面！', 'error')
        return redirect(url_for('main.index'))
        
    conn = db.get_db()
    with conn.cursor() as cursor:
        # 获取学生的所有报名记录
        cursor.execute('''
            SELECT r.*, e.EventName, e.EventType, e.GenderRestriction,
                   c.ClassName, c.Department
            FROM Registration r
            JOIN Event e ON r.EventID = e.EventID
            JOIN Student s ON r.StudentID = s.StudentID
            JOIN Class c ON s.ClassID = c.ClassID
            WHERE r.StudentID = %s
            ORDER BY r.RegistrationTime DESC
        ''', (student_id,))
        registrations = cursor.fetchall()
        
        # 获取学生信息
        cursor.execute('''
            SELECT s.*, c.ClassName, c.Department
            FROM Student s
            JOIN Class c ON s.ClassID = c.ClassID
            WHERE s.StudentID = %s
        ''', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('未找到该学生！', 'error')
            return redirect(url_for('main.students'))
    
    return render_template('admin/student_registrations.html',
                         student=student,
                         registrations=registrations)

# 删除成绩
@app.route('/referee/results/<result_id>/delete', methods=['POST'])
@login_required
def delete_result(result_id):
    if current_user.role != 'Referee':
        flash('您没有权限执行此操作！', 'error')
        return redirect(url_for('main.index'))
        
    try:
        conn = db.get_db()
        with conn.cursor() as cursor:
            # 检查是否是当前裁判录入的成绩
            cursor.execute('SELECT * FROM Result WHERE ResultID = %s AND RefereeID = %s',
                         (result_id, current_user.id))
            result = cursor.fetchone()
            
            if not result:
                flash('未找到该成绩记录或您没有权限删除！', 'error')
                return redirect(url_for('main.referee_dashboard'))
            
            # 删除成绩
            cursor.execute('DELETE FROM Result WHERE ResultID = %s', (result_id,))
            conn.commit()
            flash('成绩删除成功！', 'success')
        
    except Exception as e:
        conn.rollback()
        flash('删除失败，请重试！', 'error')
        
    return redirect(url_for('main.referee_dashboard'))

