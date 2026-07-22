from flask import Flask, render_template, request, jsonify, send_file, session
import db
import excel_exporter
import datetime
import os
from functools import wraps
from waitress import serve

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on start
db.init_db()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            return jsonify({'success': False, 'error': 'נדרשת התחברות מנהלים לביצוע פעולה זו', 'auth_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        username = data.get('username', '').strip()
        password = str(data.get('password', '')).strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'נא להזין שם משתמש וסיסמה'}), 400
            
        user = db.authenticate_user(username, password)
        if user:
            session['user'] = user
            return jsonify({
                'success': True,
                'message': f'ברוך/ה הבא/ה {user["full_name"]}',
                'user': user
            })
        else:
            return jsonify({'success': False, 'error': 'שם משתמש או סיסמה שגויים'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True, 'message': 'התנתקת בהצלחה'})

@app.route('/api/auth-check', methods=['GET'])
def auth_check():
    user = session.get('user')
    if user:
        return jsonify({'is_authenticated': True, 'user': user})
    return jsonify({'is_authenticated': False})

@app.route('/api/units', methods=['GET'])
def get_units():
    try:
        units = db.get_all_units()
        return jsonify({'success': True, 'units': units})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/units', methods=['POST'])
@admin_required
def create_unit():
    try:
        data = request.json or {}
        sid = int(data.get('sid', 99))
        authority = data.get('authority', 'אכ"א').strip()
        unit_name = data.get('unit_name', '').strip()
        quota = int(data.get('quota', 0))
        
        if not unit_name:
            return jsonify({'success': False, 'error': 'שם יחידה אינו יכול להיות ריק'}), 400
        if quota < 0:
            return jsonify({'success': False, 'error': 'מצבת כ"א חייבת להיות חיובית'}), 400
            
        unit_id = db.add_unit(sid, authority, unit_name, quota)
        return jsonify({'success': True, 'unit_id': unit_id, 'message': 'היחידה נוספה בהצלחה'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/units/<int:unit_id>', methods=['PUT'])
@admin_required
def update_unit_quota(unit_id):
    try:
        data = request.json or {}
        authority = data.get('authority', 'אכ"א').strip()
        unit_name = data.get('unit_name', '').strip()
        quota = int(data.get('quota', 0))
        
        if not unit_name:
            return jsonify({'success': False, 'error': 'שם יחידה אינו יכול להיות ריק'}), 400
        if quota < 0:
            return jsonify({'success': False, 'error': 'מצבת כ"א חייבת להיות חיובית'}), 400
            
        db.update_unit(unit_id, authority, unit_name, quota)
        return jsonify({'success': True, 'message': 'התקן עודכן בהצלחה'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/units/<int:unit_id>', methods=['DELETE'])
@admin_required
def remove_unit(unit_id):
    try:
        db.delete_unit(unit_id)
        return jsonify({'success': True, 'message': 'היחידה הוסרה בהצלחה'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        date_str = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
        reports = db.get_reports_for_date(date_str)
        
        total_units = len(reports)
        submitted_units = sum(1 for r in reports if r['is_submitted'])
        
        total_quota = sum(r['quota'] for r in reports)
        total_present = sum(r['present_base'] or 0 for r in reports if r['is_submitted'])
        total_reserve = sum(r['reserve'] or 0 for r in reports if r['is_submitted'])
        total_wfh = sum(r['work_from_home'] or 0 for r in reports if r['is_submitted'])
        total_standby = sum(r['standby_reduction'] or 0 for r in reports if r['is_submitted'])
        total_other = sum(r['other_absent'] or 0 for r in reports if r['is_submitted'])
        
        stats = {
            'date': date_str,
            'total_units': total_units,
            'submitted_units': submitted_units,
            'pending_units': total_units - submitted_units,
            'completion_percent': round((submitted_units / total_units * 100), 1) if total_units > 0 else 0,
            'total_quota': total_quota,
            'total_present': total_present,
            'total_reserve': total_reserve,
            'total_wfh': total_wfh,
            'total_standby': total_standby,
            'total_other': total_other
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'reports': reports,
            'is_admin': bool(session.get('user'))
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports', methods=['POST'])
def save_daily_report():
    try:
        data = request.json or {}
        unit_id = int(data.get('unit_id'))
        report_date = data.get('report_date', datetime.date.today().strftime('%Y-%m-%d')).strip()
        
        present_base = int(data.get('present_base', 0))
        reserve = int(data.get('reserve', 0))
        work_from_home = int(data.get('work_from_home', 0))
        standby_reduction = int(data.get('standby_reduction', 0))
        other_absent = int(data.get('other_absent', 0))
        submitted_by = data.get('submitted_by', 'נציג יחידה').strip()
        
        for val_name, val in [
            ('התייצבו', present_base),
            ('מילואים', reserve),
            ('עבודה מהבית', work_from_home),
            ('רידוד סד"כ', standby_reduction),
            ('לא נוכח מסיבות אחרות', other_absent)
        ]:
            if val < 0:
                return jsonify({'success': False, 'error': f'ערך {val_name} אינו יכול להיות שלילי'}), 400
                
        db.save_report(unit_id, report_date, present_base, reserve, work_from_home, standby_reduction, other_absent, submitted_by)
        return jsonify({'success': True, 'message': 'הדיווח נשמר בהצלחה!'})
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-excel', methods=['GET'])
@admin_required
def export_excel():
    try:
        date_str = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
        reports = db.get_reports_for_date(date_str)
        
        excel_io = excel_exporter.generate_damah_excel(reports, date_str)
        
        try:
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            filename = f"damah_aka_{dt.strftime('%d_%m_%Y')}.xlsx"
        except Exception:
            filename = "damah_aka_report.xlsx"
            
        return send_file(
            excel_io,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Serving Production Waitress WSGI server on port {port}...")
    serve(app, host='0.0.0.0', port=port, threads=16)
