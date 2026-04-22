from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import sqlite3, os, hashlib, json
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'edutj_secret_2024_xK9mP'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
DB = 'lms.db'

# ── i18n ──────────────────────────────────────────────────
LANGS = {
    'tg': {
        'home':'Асосӣ','courses':'Курсҳо','login':'Дохил шудан','logout':'Баромад',
        'cabinet':'Кабинет','chat':'Чат','rating':'Рейтинг','schedule':'Ҷадвал',
        'welcome':'Хуш омадед','my_courses':'Курсҳои ман','all_courses':'Ҳамаи курсҳо',
        'progress':'Прогресс','enroll':'Қайд шудан','continue':'Идома додан',
        'lesson_done':'Дарс хонда шуд','take_test':'Тест гирифтан',
        'notifications':'Огоҳиномаҳо','homework':'Вазифаҳо','dark_mode':'Торик',
        'lang':'Забон','points':'XP','lessons':'дарс','tests':'тест',
        'certificate':'Сертификат','interpreter':'Интерпретатор','send':'Фиристодан',
        'submit':'Супоридан','back':'Баргаштан','delete':'Нест кардан',
        'add':'Илова кардан','save':'Сохтан','cancel':'Бекор',
    },
    'ru': {
        'home':'Главная','courses':'Курсы','login':'Войти','logout':'Выйти',
        'cabinet':'Кабинет','chat':'Чат','rating':'Рейтинг','schedule':'Расписание',
        'welcome':'Добро пожаловать','my_courses':'Мои курсы','all_courses':'Все курсы',
        'progress':'Прогресс','enroll':'Записаться','continue':'Продолжить',
        'lesson_done':'Урок пройден','take_test':'Пройти тест',
        'notifications':'Уведомления','homework':'Задания','dark_mode':'Тёмный',
        'lang':'Язык','points':'XP','lessons':'уроков','tests':'тестов',
        'certificate':'Сертификат','interpreter':'Интерпретатор','send':'Отправить',
        'submit':'Сдать','back':'Назад','delete':'Удалить',
        'add':'Добавить','save':'Сохранить','cancel':'Отмена',
    },
    'en': {
        'home':'Home','courses':'Courses','login':'Login','logout':'Logout',
        'cabinet':'Dashboard','chat':'Chat','rating':'Leaderboard','schedule':'Schedule',
        'welcome':'Welcome','my_courses':'My Courses','all_courses':'All Courses',
        'progress':'Progress','enroll':'Enroll','continue':'Continue',
        'lesson_done':'Lesson Done','take_test':'Take Test',
        'notifications':'Notifications','homework':'Homework','dark_mode':'Dark',
        'lang':'Language','points':'XP','lessons':'lessons','tests':'tests',
        'certificate':'Certificate','interpreter':'Interpreter','send':'Send',
        'submit':'Submit','back':'Back','delete':'Delete',
        'add':'Add','save':'Save','cancel':'Cancel',
    }
}

def t(key):
    lang = session.get('lang','tg')
    return LANGS.get(lang, LANGS['tg']).get(key, key)

app.jinja_env.globals['t'] = t
app.jinja_env.globals['enumerate'] = enumerate

# ── DB ────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'student',
            xp INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'tg',
            dark_mode INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT,
            image TEXT, instructor TEXT, duration TEXT,
            level TEXT DEFAULT 'Асосӣ',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER, title TEXT NOT NULL,
            description TEXT, video_url TEXT, content TEXT,
            order_num INTEGER DEFAULT 0, scheduled_at TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER, course_id INTEGER, title TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER, question TEXT NOT NULL,
            options TEXT NOT NULL, correct INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, test_id INTEGER,
            score INTEGER, total INTEGER, passed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, lesson_id INTEGER, completed INTEGER DEFAULT 0,
            UNIQUE(user_id, lesson_id)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER, lesson_id INTEGER,
            title TEXT NOT NULL, description TEXT,
            test_code TEXT, deadline TEXT
        );
        CREATE TABLE IF NOT EXISTS homework_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, task_id INTEGER,
            filename TEXT, comment TEXT,
            grade INTEGER, feedback TEXT,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, course_id INTEGER,
            enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, course_id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, title TEXT NOT NULL,
            message TEXT NOT NULL, type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, badge_key TEXT,
            earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge_key)
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER, lesson_id INTEGER,
            title TEXT NOT NULL, scheduled_date TEXT NOT NULL,
            scheduled_time TEXT DEFAULT '09:00',
            duration_min INTEGER DEFAULT 60, description TEXT
        );
    ''')
    try: db.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                    ('admin', hash_pass('admin123'), 'Администратор', 'admin'))
    except: pass
    try: db.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                    ('student1', hash_pass('student123'), 'Алӣ Раҳимов', 'student'))
    except: pass
    try: db.execute("INSERT INTO courses (title,description,instructor,duration,level) VALUES (?,?,?,?,?)",
                    ('Python аз Сифр','Омӯзиши Python аз асос','Устод Карим','3 моҳ','Асосӣ'))
    except: pass
    db.commit(); db.close()

# ── HELPERS ───────────────────────────────────────────────
def add_notification(user_id, title, message, ntype='info'):
    db = get_db()
    db.execute("INSERT INTO notifications (user_id,title,message,type) VALUES (?,?,?,?)",
               (user_id, title, message, ntype))
    db.commit(); db.close()

def add_xp(user_id, amount):
    db = get_db()
    db.execute("UPDATE users SET xp = xp + ? WHERE id=?", (amount, user_id))
    db.commit()
    user = db.execute("SELECT xp FROM users WHERE id=?", (user_id,)).fetchone()
    xp = user['xp'] if user else 0
    for threshold, key, label in [(100,'xp_100','🥉 100 XP'),(500,'xp_500','🥈 500 XP'),(1000,'xp_1000','🥇 1000 XP')]:
        if xp >= threshold:
            try:
                db.execute("INSERT INTO badges (user_id,badge_key) VALUES (?,?)", (user_id, key))
                db.commit()
                add_notification(user_id, '🏅 Нишон гирифтед!', f'Нишони "{label}" гирифтед!', 'success')
            except: pass
    db.close()

def get_unread(user_id):
    db = get_db()
    n = db.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (user_id,)).fetchone()['c']
    db.close()
    return n

app.jinja_env.globals['get_unread'] = get_unread

def login_required(f):
    from functools import wraps
    @wraps(f)
    def d(*a, **k):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a, **k)
    return d

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def d(*a, **k):
        if 'user_id' not in session or session.get('role') != 'admin': return redirect(url_for('login'))
        return f(*a, **k)
    return d

# ── LANGUAGE & DARK MODE ──────────────────────────────────
@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['tg','ru','en']:
        session['lang'] = lang
        if 'user_id' in session:
            db = get_db()
            db.execute("UPDATE users SET lang=? WHERE id=?", (lang, session['user_id']))
            db.commit(); db.close()
    return redirect(request.referrer or '/')

@app.route('/toggle_dark')
@login_required
def toggle_dark():
    session['dark'] = not session.get('dark', False)
    db = get_db()
    db.execute("UPDATE users SET dark_mode=? WHERE id=?", (1 if session['dark'] else 0, session['user_id']))
    db.commit(); db.close()
    return redirect(request.referrer or '/')

# ── PUBLIC ────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template('index.html', courses=courses)

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        user = get_db().execute("SELECT * FROM users WHERE username=? AND password=?",
                                 (request.form['username'], hash_pass(request.form['password']))).fetchone()
        if user:
            session.update({'user_id':user['id'],'username':user['username'],
                            'full_name':user['full_name'],'role':user['role'],
                            'lang':user['lang'] or 'tg','dark':bool(user['dark_mode'])})
            return redirect(url_for('admin') if user['role']=='admin' else url_for('pupil'))
        error = 'Логин ё парол нодуруст аст!'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

# ── PUPIL ─────────────────────────────────────────────────
@app.route('/pupil')
@login_required
def pupil():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    enrolled = db.execute("""SELECT c.*, e.enrolled_at FROM courses c
        JOIN enrollments e ON c.id=e.course_id WHERE e.user_id=?""", (session['user_id'],)).fetchall()
    all_courses = db.execute("SELECT * FROM courses").fetchall()
    progress_data = {}
    for c in enrolled:
        total = db.execute("SELECT COUNT(*) as cnt FROM lessons WHERE course_id=?", (c['id'],)).fetchone()['cnt']
        done = db.execute("""SELECT COUNT(*) as cnt FROM progress p JOIN lessons l ON p.lesson_id=l.id
            WHERE l.course_id=? AND p.user_id=? AND p.completed=1""", (c['id'], session['user_id'])).fetchone()['cnt']
        progress_data[c['id']] = {'total':total,'done':done,'pct':int((done/total*100) if total else 0)}
    badges = [b['badge_key'] for b in db.execute("SELECT badge_key FROM badges WHERE user_id=?", (session['user_id'],)).fetchall()]
    activity = db.execute("""SELECT date(created_at) as day, COUNT(*) as cnt FROM test_results
        WHERE user_id=? GROUP BY day ORDER BY day DESC LIMIT 7""", (session['user_id'],)).fetchall()
    db.close()
    return render_template('pupil.html', user=user, enrolled=enrolled, all_courses=all_courses,
                           progress=progress_data, badge_keys=badges, activity=list(activity))

@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    db = get_db()
    try:
        db.execute("INSERT INTO enrollments (user_id,course_id) VALUES (?,?)", (session['user_id'], course_id))
        db.commit()
        course = db.execute("SELECT title FROM courses WHERE id=?", (course_id,)).fetchone()
        add_notification(session['user_id'],'📚 Курсга қайд шудед!',
                         f'Шумо ба курси "{course["title"]}" қайд шудед!','success')
        add_xp(session['user_id'], 10)
    except: pass
    db.close(); return redirect(url_for('pupil'))

@app.route('/course/<int:course_id>')
@login_required
def course_view(course_id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    lessons = db.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course_id,)).fetchall()
    progress_map = {}
    for l in lessons:
        p = db.execute("SELECT completed FROM progress WHERE user_id=? AND lesson_id=?", (session['user_id'], l['id'])).fetchone()
        progress_map[l['id']] = p['completed'] if p else 0
    db.close()
    return render_template('pupil.html', course=course, lessons=lessons, progress_map=progress_map, view='course')

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_view(lesson_id):
    db = get_db()
    lesson = db.execute("SELECT l.*, c.title as course_title FROM lessons l JOIN courses c ON l.course_id=c.id WHERE l.id=?", (lesson_id,)).fetchone()
    tests = db.execute("SELECT * FROM tests WHERE lesson_id=?", (lesson_id,)).fetchall()
    tasks = db.execute("SELECT * FROM tasks WHERE lesson_id=?", (lesson_id,)).fetchall()
    all_lessons = db.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (lesson['course_id'],)).fetchall()
    try:
        db.execute("INSERT OR IGNORE INTO progress (user_id,lesson_id,completed) VALUES (?,?,0)", (session['user_id'], lesson_id))
        db.commit()
    except: pass
    db.close()
    return render_template('pupil.html', lesson=lesson, tests=tests, tasks=tasks, all_lessons=all_lessons, view='lesson')

@app.route('/complete_lesson/<int:lesson_id>')
@login_required
def complete_lesson(lesson_id):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO progress (user_id,lesson_id,completed) VALUES (?,?,1)", (session['user_id'], lesson_id))
    db.commit()
    lesson = db.execute("SELECT title FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    db.close()
    add_xp(session['user_id'], 20)
    add_notification(session['user_id'],'✅ Дарс тамом!',f'"{lesson["title"]}" — +20 XP!','success')
    return jsonify({'ok': True})

# ── NOTIFICATIONS ─────────────────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    db = get_db()
    notifs = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (session['user_id'],)).fetchall()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session['user_id'],))
    db.commit(); db.close()
    return render_template('notifications.html', notifs=notifs)

@app.route('/api/notif_count')
@login_required
def notif_count():
    return jsonify({'count': get_unread(session['user_id'])})

# ── SCHEDULE ──────────────────────────────────────────────
@app.route('/schedule')
@login_required
def schedule():
    db = get_db()
    events = db.execute("""SELECT s.*, c.title as course_title, l.title as lesson_title
        FROM schedule s LEFT JOIN courses c ON s.course_id=c.id
        LEFT JOIN lessons l ON s.lesson_id=l.id
        ORDER BY s.scheduled_date, s.scheduled_time""").fetchall()
    db.close()
    return render_template('schedule.html', events=events)

@app.route('/admin/add_schedule', methods=['POST'])
@admin_required
def add_schedule():
    db = get_db()
    db.execute("INSERT INTO schedule (course_id,lesson_id,title,scheduled_date,scheduled_time,duration_min,description) VALUES (?,?,?,?,?,?,?)",
               (request.form.get('course_id'), request.form.get('lesson_id') or None,
                request.form['title'], request.form['scheduled_date'],
                request.form.get('scheduled_time','09:00'), int(request.form.get('duration_min',60)),
                request.form.get('description','')))
    users = db.execute("SELECT id FROM users WHERE role='student'").fetchall()
    for u in users:
        add_notification(u['id'],'📅 Дарси нав ҷадвал шуд!',
                         f'{request.form["title"]} — {request.form["scheduled_date"]}','info')
    db.commit(); db.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_schedule/<int:sid>')
@admin_required
def delete_schedule(sid):
    db = get_db()
    db.execute("DELETE FROM schedule WHERE id=?", (sid,))
    db.commit(); db.close()
    return redirect(url_for('admin'))

# ── HOMEWORK ──────────────────────────────────────────────
@app.route('/homework/<int:task_id>', methods=['GET','POST'])
@login_required
def homework(task_id):
    db = get_db()
    task = db.execute("""SELECT t.*, c.title as course_title FROM tasks t
                         LEFT JOIN courses c ON t.course_id=c.id WHERE t.id=?""", (task_id,)).fetchone()
    my_sub = db.execute("SELECT * FROM homework_submissions WHERE user_id=? AND task_id=?",
                        (session['user_id'], task_id)).fetchone()
    if request.method == 'POST':
        comment = request.form.get('comment','')
        filename = ''
        if 'file' in request.files:
            f = request.files['file']
            if f and f.filename:
                ext = f.filename.rsplit('.',1)[-1].lower()
                safe = f"hw_{session['user_id']}_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],'homework', safe))
                filename = safe
        db.execute("INSERT OR REPLACE INTO homework_submissions (user_id,task_id,filename,comment) VALUES (?,?,?,?)",
                   (session['user_id'], task_id, filename, comment))
        db.commit()
        add_xp(session['user_id'], 15)
        add_notification(session['user_id'],'📤 Вазифа фиристода шуд!',f'"{task["title"]}" — +15 XP!','success')
        for a in db.execute("SELECT id FROM users WHERE role='admin'").fetchall():
            add_notification(a['id'],'📥 Вазифаи нав!',f'{session["full_name"]}: "{task["title"]}"','info')
        db.close()
        return redirect(url_for('zadacha'))
    db.close()
    return render_template('homework.html', task=task, my_sub=my_sub)

@app.route('/admin/submissions')
@admin_required
def admin_submissions():
    db = get_db()
    subs = db.execute("""SELECT s.*, u.full_name, t.title as task_title
        FROM homework_submissions s JOIN users u ON s.user_id=u.id
        JOIN tasks t ON s.task_id=t.id ORDER BY s.submitted_at DESC""").fetchall()
    db.close()
    return render_template('admin.html', submissions=subs, view='submissions')

@app.route('/admin/grade/<int:sub_id>', methods=['POST'])
@admin_required
def grade_homework(sub_id):
    db = get_db()
    grade = int(request.form.get('grade',0))
    feedback = request.form.get('feedback','')
    sub = db.execute("SELECT * FROM homework_submissions WHERE id=?", (sub_id,)).fetchone()
    db.execute("UPDATE homework_submissions SET grade=?,feedback=? WHERE id=?", (grade, feedback, sub_id))
    db.commit()
    if sub:
        add_notification(sub['user_id'],'📊 Вазифа баҳогузорӣ шуд!',
                         f'Баҳо: {grade}/100. {feedback}','info')
    db.close(); return redirect(url_for('admin_submissions'))

@app.route('/static/uploads/homework/<path:filename>')
@login_required
def download_homework(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'],'homework'), filename)

# ── TEST ──────────────────────────────────────────────────
@app.route('/test/<int:test_id>')
@login_required
def test_view(test_id):
    db = get_db()
    test = db.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()
    questions = [{'id':q['id'],'question':q['question'],'options':json.loads(q['options']),'correct':q['correct']}
                 for q in db.execute("SELECT * FROM questions WHERE test_id=?", (test_id,)).fetchall()]
    db.close()
    return render_template('test.html', test=test, questions=questions)

@app.route('/submit_test/<int:test_id>', methods=['POST'])
@login_required
def submit_test(test_id):
    db = get_db()
    questions = db.execute("SELECT * FROM questions WHERE test_id=?", (test_id,)).fetchall()
    score = sum(1 for q in questions if request.form.get(f'q_{q["id"]}') and int(request.form.get(f'q_{q["id"]}')) == q['correct'])
    total = len(questions)
    passed = 1 if total > 0 and score/total >= 0.6 else 0
    db.execute("INSERT INTO test_results (user_id,test_id,score,total,passed) VALUES (?,?,?,?,?)",
               (session['user_id'], test_id, score, total, passed))
    db.commit()
    test = db.execute("SELECT title FROM tests WHERE id=?", (test_id,)).fetchone()
    db.close()
    xp = score * 5
    add_xp(session['user_id'], xp)
    msg = f'Тести "{test["title"]}": {score}/{total}. +{xp} XP!'
    add_notification(session['user_id'], '🏆 Тест тамом!' if passed else '📝 Натиҷа', msg, 'success' if passed else 'warning')
    return render_template('test.html', result={'score':score,'total':total,'passed':passed}, test_id=test_id)

# ── RATING ────────────────────────────────────────────────
@app.route('/reiting')
@login_required
def reiting():
    db = get_db()
    users = db.execute("""SELECT u.full_name, u.username, u.xp,
               COUNT(DISTINCT p.lesson_id) as lessons_done,
               COALESCE(SUM(tr.score),0) as total_score,
               COUNT(DISTINCT tr.test_id) as tests_done
        FROM users u LEFT JOIN progress p ON u.id=p.user_id AND p.completed=1
        LEFT JOIN test_results tr ON u.id=tr.user_id AND tr.passed=1
        WHERE u.role='student' GROUP BY u.id ORDER BY u.xp DESC""").fetchall()
    db.close()
    return render_template('reiting.html', users=users)

# ── CHAT ──────────────────────────────────────────────────
@app.route('/chat')
@login_required
def chat():
    db = get_db()
    msgs = db.execute("""SELECT m.*, u.full_name, u.role FROM chat_messages m
        JOIN users u ON m.user_id=u.id ORDER BY m.created_at DESC LIMIT 100""").fetchall()
    db.close()
    return render_template('chat.html', messages=list(reversed(msgs)))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    msg = request.form.get('message','').strip()
    if msg:
        db = get_db()
        db.execute("INSERT INTO chat_messages (user_id,message) VALUES (?,?)", (session['user_id'], msg))
        db.commit(); db.close()
    return redirect(url_for('chat'))

@app.route('/api/messages')
@login_required
def api_messages():
    db = get_db()
    msgs = db.execute("""SELECT m.*, u.full_name, u.role FROM chat_messages m
        JOIN users u ON m.user_id=u.id ORDER BY m.created_at DESC LIMIT 100""").fetchall()
    db.close()
    return jsonify([dict(m) for m in reversed(msgs)])

# ── INTERPRETER ───────────────────────────────────────────
@app.route('/interpretator')
@login_required
def interpretator():
    return render_template('interpretator.html')

@app.route('/run_code', methods=['POST'])
@login_required
def run_code():
    import subprocess, tempfile
    code = request.json.get('code','')
    try:
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(code); fname = f.name
        r = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
        os.unlink(fname)
        return jsonify({'output': r.stdout, 'error': r.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({'output':'','error':'Вақт тамом шуд (10 сония)'})
    except Exception as e:
        return jsonify({'output':'','error':str(e)})

# ── CERTIFICATE ───────────────────────────────────────────
@app.route('/sertifikat/<int:course_id>')
@login_required
def sertifikat(course_id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    total = db.execute("SELECT COUNT(*) as cnt FROM lessons WHERE course_id=?", (course_id,)).fetchone()['cnt']
    done = db.execute("""SELECT COUNT(*) as cnt FROM progress p JOIN lessons l ON p.lesson_id=l.id
        WHERE l.course_id=? AND p.user_id=? AND p.completed=1""", (course_id, session['user_id'])).fetchone()['cnt']
    db.close()
    return render_template('sertifikat.html', course=course, user=user,
                           eligible=total>0 and done==total, date=datetime.now().strftime('%d.%m.%Y'))

# ── ZADACHA ───────────────────────────────────────────────
@app.route('/zadacha')
@login_required
def zadacha():
    db = get_db()
    tasks = db.execute("""SELECT t.*, l.title as lesson_title, c.title as course_title
        FROM tasks t LEFT JOIN lessons l ON t.lesson_id=l.id
        LEFT JOIN courses c ON t.course_id=c.id""").fetchall()
    my_subs = {s['task_id']:s for s in db.execute(
        "SELECT * FROM homework_submissions WHERE user_id=?", (session['user_id'],)).fetchall()}
    db.close()
    return render_template('zadacha.html', tasks=tasks, my_subs=my_subs)

# ── ADMIN ─────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY created_at DESC").fetchall()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    lessons_count = db.execute("SELECT COUNT(*) as cnt FROM lessons").fetchone()['cnt']
    tests_count = db.execute("SELECT COUNT(*) as cnt FROM tests").fetchone()['cnt']
    hw_count = db.execute("SELECT COUNT(*) as cnt FROM homework_submissions").fetchone()['cnt']
    schedule_events = db.execute("""SELECT s.*, c.title as course_title FROM schedule s
        LEFT JOIN courses c ON s.course_id=c.id ORDER BY s.scheduled_date, s.scheduled_time""").fetchall()
    db.close()
    return render_template('admin.html', courses=courses, users=users,
                           lessons_count=lessons_count, tests_count=tests_count,
                           hw_count=hw_count, schedule_events=schedule_events)

@app.route('/admin/add_course', methods=['POST'])
@admin_required
def add_course():
    db = get_db()
    image = ''
    if 'image' in request.files:
        f = request.files['image']
        if f and f.filename:
            fname = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],'images', fname))
            image = fname
    db.execute("INSERT INTO courses (title,description,image,instructor,duration,level) VALUES (?,?,?,?,?,?)",
               (request.form['title'], request.form['description'], image,
                request.form['instructor'], request.form['duration'], request.form['level']))
    db.commit(); db.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_course/<int:cid>')
@admin_required
def delete_course(cid):
    db = get_db(); db.execute("DELETE FROM courses WHERE id=?", (cid,)); db.commit(); db.close()
    return redirect(url_for('admin'))

@app.route('/admin/lessons/<int:course_id>')
@admin_required
def admin_lessons(course_id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    lessons = db.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course_id,)).fetchall()
    db.close()
    return render_template('admin.html', course=course, lessons=lessons, view='lessons')

@app.route('/admin/add_lesson', methods=['POST'])
@admin_required
def add_lesson():
    db = get_db()
    video_url = ''
    if 'video' in request.files:
        f = request.files['video']
        if f and f.filename:
            fname = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],'videos', fname))
            video_url = f'/static/uploads/videos/{fname}'
    order = db.execute("SELECT COUNT(*) as cnt FROM lessons WHERE course_id=?", (request.form['course_id'],)).fetchone()['cnt']
    db.execute("INSERT INTO lessons (course_id,title,description,video_url,content,order_num,scheduled_at) VALUES (?,?,?,?,?,?,?)",
               (request.form['course_id'], request.form['title'], request.form.get('description',''),
                video_url or request.form.get('video_link',''), request.form.get('content',''),
                order+1, request.form.get('scheduled_at','')))
    db.commit()
    for s in db.execute("SELECT user_id FROM enrollments WHERE course_id=?", (request.form['course_id'],)).fetchall():
        add_notification(s['user_id'],'📖 Дарси нав!',f'"{request.form["title"]}" илова шуд!','info')
    db.close()
    return redirect(url_for('admin_lessons', course_id=request.form['course_id']))

@app.route('/admin/delete_lesson/<int:lid>')
@admin_required
def delete_lesson(lid):
    db = get_db()
    lesson = db.execute("SELECT course_id FROM lessons WHERE id=?", (lid,)).fetchone()
    cid = lesson['course_id'] if lesson else 0
    db.execute("DELETE FROM lessons WHERE id=?", (lid,)); db.commit(); db.close()
    return redirect(url_for('admin_lessons', course_id=cid))

@app.route('/admin/tests/<int:lesson_id>')
@admin_required
def admin_tests(lesson_id):
    db = get_db()
    lesson = db.execute("SELECT l.*, c.title as course_title FROM lessons l JOIN courses c ON l.course_id=c.id WHERE l.id=?", (lesson_id,)).fetchone()
    tests = db.execute("SELECT * FROM tests WHERE lesson_id=?", (lesson_id,)).fetchall()
    db.close()
    return render_template('admin.html', lesson=lesson, tests=tests, view='tests')

@app.route('/admin/add_test', methods=['POST'])
@admin_required
def add_test():
    db = get_db()
    lid = request.form['lesson_id']
    lesson = db.execute("SELECT course_id FROM lessons WHERE id=?", (lid,)).fetchone()
    tid = db.execute("INSERT INTO tests (lesson_id,course_id,title) VALUES (?,?,?)",
                     (lid, lesson['course_id'], request.form['title'])).lastrowid
    for i, q in enumerate(request.form.getlist('question[]')):
        if not q.strip(): continue
        opts = [request.form.getlist(k+'[]')[i] if i < len(request.form.getlist(k+'[]')) else ''
                for k in ['opt_a','opt_b','opt_c','opt_d']]
        correct = int(request.form.getlist('correct[]')[i]) if i < len(request.form.getlist('correct[]')) else 0
        db.execute("INSERT INTO questions (test_id,question,options,correct) VALUES (?,?,?,?)",
                   (tid, q, json.dumps(opts), correct))
    db.commit(); db.close()
    return redirect(url_for('admin_tests', lesson_id=lid))

@app.route('/admin/add_task', methods=['POST'])
@admin_required
def add_task():
    db = get_db()
    db.execute("INSERT INTO tasks (course_id,lesson_id,title,description,test_code,deadline) VALUES (?,?,?,?,?,?)",
               (request.form['course_id'], request.form.get('lesson_id') or None,
                request.form['title'], request.form.get('description',''),
                request.form.get('test_code',''), request.form.get('deadline','')))
    db.commit(); db.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    db = get_db()
    try:
        db.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                   (request.form['username'], hash_pass(request.form['password']),
                    request.form['full_name'], request.form.get('role','student')))
        db.commit()
    except: pass
    db.close(); return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:uid>')
@admin_required
def delete_user(uid):
    db = get_db(); db.execute("DELETE FROM users WHERE id=? AND role!='admin'", (uid,)); db.commit(); db.close()
    return redirect(url_for('admin'))

@app.route('/admin/notify_all', methods=['POST'])
@admin_required
def notify_all():
    db = get_db()
    for u in db.execute("SELECT id FROM users WHERE role='student'").fetchall():
        add_notification(u['id'], request.form['title'], request.form['message'], request.form.get('type','info'))
    db.close(); return redirect(url_for('admin'))

if __name__ == '__main__':
    for d in ['static/uploads/videos','static/uploads/images','static/uploads/homework']:
        os.makedirs(d, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
