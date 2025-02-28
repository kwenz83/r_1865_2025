from flask import Flask, render_template, request, g, jsonify, send_from_directory
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['DATABASE'] = 'running_data.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx'}


# 初始化数据库
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                date TEXT NOT NULL,  -- 使用 TEXT 类型存储日期
                distance REAL NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id),
                UNIQUE(member_id, date)
            )
        ''')
        db.commit()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(error):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def update_member_data(member_name, date, distance):
    """更新或插入成员活动数据"""
    db = get_db()
    cursor = db.cursor()
    try:
        # 确保数据类型正确
        member_name = str(member_name)
        date = str(date)  # 日期必须是字符串
        distance = float(distance)  # 距离必须是数值类型

        # 查找或创建成员
        member = cursor.execute('SELECT id FROM members WHERE name = ?',
                                (member_name,)).fetchone()
        if not member:
            cursor.execute('INSERT INTO members (name) VALUES (?)', (member_name,))
            member_id = cursor.lastrowid
        else:
            member_id = member['id']

        # 更新活动数据
        cursor.execute('''
        INSERT INTO activities (member_id, date, distance)
        VALUES (?, ?, ?)
        ON CONFLICT(member_id, date) DO UPDATE SET
            distance=excluded.distance
        ''', (member_id, date, distance))

        db.commit()
        return True
    except Exception as e:
        print(f"Error updating data: {e}")
        return False
    finally:
        cursor.close()


@app.route('/')
def index():
    db = get_db()

    # 获取所有日期（去除时间部分）
    dates = db.execute('''
        SELECT DISTINCT substr(date, 1, 10) as clean_date 
        FROM activities 
        ORDER BY clean_date
    ''').fetchall()
    dates = [d['clean_date'] for d in dates]

    # 修改数据查询逻辑
    members = db.execute('''
        SELECT m.id, m.name, 
               SUM(a.distance) as total,
               GROUP_CONCAT(substr(a.date, 1, 10) || ':' || a.distance) as details
        FROM members m
        LEFT JOIN activities a ON m.id = a.member_id
        GROUP BY m.id
    ''').fetchall()

    # 构建数据字典
    member_data = []
    for m in members:
        data = {
            'id': m['id'],
            'name': m['name'],
            'total': m['total'] or 0,
            'details': {}
        }
        if m['details']:
            for d in m['details'].split(','):
                try:
                    # 只取前两个值，忽略多余的部分
                    parts = d.split(':')
                    if len(parts) >= 2:
                        date, dist = parts[0], parts[1]
                        data['details'][date] = float(dist)
                except ValueError as e:
                    print(f"Error parsing details: {e}")
        member_data.append(data)

    return render_template('index.html',
                           dates=dates,
                           members=member_data,
                           is_admin=request.args.get('admin'))


@app.route('/update', methods=['POST'])
def update_data():
    """处理前端数据更新请求"""
    data = request.json
    if update_member_data(data['member'], data['date'], data['distance']):
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update data'})


@app.route('/import', methods=['POST'])
def import_data():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'})

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            # 转换日期列为标准日期格式（YYYY-MM-DD）
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            # 检查Excel文件是否包含必要的列
            if not all(col in df.columns for col in ['姓名', '日期', '距离']):
                return jsonify({'status': 'error', 'message': 'Excel文件格式不正确，必须包含“姓名”、“日期”、“距离”三列'})

            # 逐行处理数据
            for _, row in df.iterrows():
                try:
                    # 确保数据类型正确
                    name = str(row['姓名'])
                    date = str(row['日期'])  # 确保日期是字符串
                    distance = float(row['距离'])  # 确保距离是数值类型

                    if not update_member_data(name, date, distance):
                        return jsonify({'status': 'error', 'message': f'导入失败：{name}的数据无法更新'})
                except ValueError as e:
                    return jsonify({'status': 'error', 'message': f'数据格式错误：{e}'})

            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': '文件类型不支持，仅支持.xls和.xlsx文件'})


@app.route('/static/<path:filename>')
def static_files(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    app.run(debug=True)