#!/usr/bin/python3

import pymysql

#打开数据库连接
db = pymysql.connect(host = 'localhost',
                     user = 'U1',
                     passwd = '1234',
                     database = 'scsc')
#使用cursor（）方法创建一个游标对象cursor
cursor = db.cursor()

#使用 execute（）方法执行SQL查询
cursor.execute('select sc.* from sc')

#使用fetchone()方法获取单条数据
for row in cursor:
    # 方法1：使用索引访问
    student_id = row[0]    # 学号
    course_id = row[1]     # 课程号
    score = row[2]         # 分数
    print(f"学号: {student_id}, 课程: {course_id}, 分数: {score}")

#关闭数据库连接
cursor.close()
db.close()



