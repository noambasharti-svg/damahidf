import sqlite3
import hashlib
import os
import datetime
from zoneinfo import ZoneInfo

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')

def get_israel_now():
    """Returns ISO format timestamp with explicit GMT+3 offset (+03:00)"""
    return datetime.datetime.now(ISRAEL_TZ).isoformat()

def get_israel_date():
    """Returns YYYY-MM-DD in Israel Timezone"""
    return datetime.datetime.now(ISRAEL_TZ).strftime('%Y-%m-%d')

DEFAULT_UNITS = [
    {'sid': 1, 'authority': 'אכ"א', 'unit_name': 'גלי צה״ל', 'quota': 85},
    {'sid': 2, 'authority': 'אכ"א', 'unit_name': 'ענף משא״ן', 'quota': 1},
    {'sid': 3, 'authority': 'אכ"א', 'unit_name': 'חשבות השכר', 'quota': 4},
    {'sid': 4, 'authority': 'אכ"א', 'unit_name': 'מרכז תע״ץ', 'quota': 60},
    {'sid': 5, 'authority': 'אכ"א', 'unit_name': 'מחלקת תוא״ר', 'quota': 10},
    {'sid': 6, 'authority': 'אכ"א', 'unit_name': 'מחנה רבין', 'quota': 17},
    {'sid': 7, 'authority': 'אכ"א', 'unit_name': 'מופת', 'quota': 31},
    {'sid': 8, 'authority': 'אכ"א', 'unit_name': 'מחלקת אמל״ח', 'quota': 35},
    {'sid': 9, 'authority': 'אכ"א', 'unit_name': 'מיטב', 'quota': 53},
    {'sid': 10, 'authority': 'אכ"א', 'unit_name': 'חתומכ״א', 'quota': 17},
    {'sid': 11, 'authority': 'אכ"א', 'unit_name': 'ממד״ה', 'quota': 24},
    {'sid': 12, 'authority': 'אכ"א', 'unit_name': 'ביסל״ם', 'quota': 37},
    {'sid': 13, 'authority': 'אכ"א', 'unit_name': 'מקח״ר', 'quota': 18},
    {'sid': 14, 'authority': 'אכ"א', 'unit_name': 'נפגעים', 'quota': 11},
    {'sid': 15, 'authority': 'אכ"א', 'unit_name': 'מקמש״ר', 'quota': 8},
    {'sid': 16, 'authority': 'אכ"א', 'unit_name': 'מקמצ״ר', 'quota': 24},
    {'sid': 17, 'authority': 'אכ"א', 'unit_name': 'שחר', 'quota': 18},
    {'sid': 18, 'authority': 'אכ"א', 'unit_name': 'בה״ד 11', 'quota': 4},
    {'sid': 19, 'authority': 'אכ"א', 'unit_name': 'יוהל״ם', 'quota': 11},
    {'sid': 20, 'authority': 'אכ"א', 'unit_name': 'מערך השירות', 'quota': 5},
    {'sid': 21, 'authority': 'אכ"א', 'unit_name': 'חטיבת הסגל', 'quota': 21},
    {'sid': 22, 'authority': 'אכ"א', 'unit_name': 'ענף סגל', 'quota': 5},
    {'sid': 23, 'authority': 'אכ"א', 'unit_name': 'מחלקת פרט ושכר', 'quota': 8}
]

ADMIN_USERS = [
    {'username': 'נעם בשרטי', 'password': '9811578', 'full_name': 'נעם בשרטי'},
    {'username': 'רינה נוגה בקר', 'password': '9812532', 'full_name': 'רינה נוגה בקר'},
    {'username': 'יהלי סבן', 'password': '9746440', 'full_name': 'יהלי סבן'}
]

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create units table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid INTEGER NOT NULL,
            authority TEXT NOT NULL,
            unit_name TEXT NOT NULL UNIQUE,
            quota INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    ''')
    
    # Create daily_reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            report_date TEXT NOT NULL,
            present_base INTEGER NOT NULL DEFAULT 0,
            reserve INTEGER NOT NULL DEFAULT 0,
            work_from_home INTEGER NOT NULL DEFAULT 0,
            standby_reduction INTEGER NOT NULL DEFAULT 0,
            other_absent INTEGER NOT NULL DEFAULT 0,
            revision_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            submitted_by TEXT DEFAULT '',
            FOREIGN KEY (unit_id) REFERENCES units (id),
            UNIQUE(unit_id, report_date)
        )
    ''')

    # Migration check for revision_count column
    try:
        cursor.execute('ALTER TABLE daily_reports ADD COLUMN revision_count INTEGER NOT NULL DEFAULT 1')
    except Exception:
        pass
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin'
        )
    ''')
    
    # Seed default units if empty
    cursor.execute('SELECT COUNT(*) FROM units')
    count = cursor.fetchone()[0]
    if count == 0:
        for u in DEFAULT_UNITS:
            cursor.execute('''
                INSERT INTO units (sid, authority, unit_name, quota)
                VALUES (?, ?, ?, ?)
            ''', (u['sid'], u['authority'], u['unit_name'], u['quota']))
            
    # Seed or update admin users
    for user in ADMIN_USERS:
        pwd_h = hash_password(user['password'])
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, 'admin')
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                full_name = excluded.full_name
        ''', (user['username'], pwd_h, user['full_name']))
        
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    pwd_h = hash_password(password)
    user = conn.execute('''
        SELECT id, username, full_name, role
        FROM users
        WHERE (username = ? OR full_name = ?) AND password_hash = ?
    ''', (username.strip(), username.strip(), pwd_h)).fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_all_units():
    conn = get_db_connection()
    units = conn.execute('SELECT * FROM units WHERE is_active = 1 ORDER BY sid ASC, id ASC').fetchall()
    conn.close()
    return [dict(u) for u in units]

def add_unit(sid, authority, unit_name, quota):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO units (sid, authority, unit_name, quota)
        VALUES (?, ?, ?, ?)
    ''', (sid, authority, unit_name, quota))
    unit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return unit_id

def update_unit(unit_id, authority, unit_name, quota):
    conn = get_db_connection()
    conn.execute('''
        UPDATE units
        SET authority = ?, unit_name = ?, quota = ?
        WHERE id = ?
    ''', (authority, unit_name, quota, unit_id))
    conn.commit()
    conn.close()

def delete_unit(unit_id):
    conn = get_db_connection()
    conn.execute('UPDATE units SET is_active = 0 WHERE id = ?', (unit_id,))
    conn.commit()
    conn.close()

def get_reports_for_date(report_date):
    conn = get_db_connection()
    query = '''
        SELECT 
            u.id as unit_id,
            u.sid,
            u.authority,
            u.unit_name,
            u.quota,
            r.id as report_id,
            r.report_date,
            r.present_base,
            r.reserve,
            r.work_from_home,
            r.standby_reduction,
            r.other_absent,
            COALESCE(r.revision_count, 1) as revision_count,
            r.submitted_by,
            r.created_at,
            r.updated_at,
            CASE WHEN r.id IS NOT NULL THEN 1 ELSE 0 END as is_submitted
        FROM units u
        LEFT JOIN daily_reports r ON u.id = r.unit_id AND r.report_date = ?
        WHERE u.is_active = 1
        ORDER BY u.sid ASC, u.id ASC
    '''
    rows = conn.execute(query, (report_date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_report(unit_id, report_date, present_base, reserve, work_from_home, standby_reduction, other_absent, submitted_by=''):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    unit = conn.execute('SELECT quota FROM units WHERE id = ?', (unit_id,)).fetchone()
    if not unit:
        conn.close()
        raise ValueError('היחידה אינה קיימת')
    
    total_reported = present_base + reserve + work_from_home + standby_reduction + other_absent
    if total_reported != unit['quota']:
        conn.close()
        raise ValueError(f'סך העובדים שדווחו ({total_reported}) אינו תואם למצבה הקבועה של היחידה ({unit["quota"]})')
    
    existing = conn.execute('SELECT id, revision_count FROM daily_reports WHERE unit_id = ? AND report_date = ?', (unit_id, report_date)).fetchone()
    
    now_israel_iso = get_israel_now()
    is_update = False
    new_rev = 1
    if existing:
        is_update = True
        new_rev = (existing['revision_count'] or 1) + 1
        
    cursor.execute('''
        INSERT INTO daily_reports (unit_id, report_date, present_base, reserve, work_from_home, standby_reduction, other_absent, revision_count, submitted_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        ON CONFLICT(unit_id, report_date) DO UPDATE SET
            present_base = excluded.present_base,
            reserve = excluded.reserve,
            work_from_home = excluded.work_from_home,
            standby_reduction = excluded.standby_reduction,
            other_absent = excluded.other_absent,
            revision_count = daily_reports.revision_count + 1,
            submitted_by = excluded.submitted_by,
            updated_at = ?
    ''', (unit_id, report_date, present_base, reserve, work_from_home, standby_reduction, other_absent, submitted_by, now_israel_iso, now_israel_iso, now_israel_iso))
    
    conn.commit()
    conn.close()
    return is_update, new_rev

if __name__ == '__main__':
    init_db()
    print("Database updated with ISO Israel Timezone timestamps (+03:00)!")
