import urllib.request
import json
import base64
import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

TARGET_EMAIL = "noambasharti@gmail.com"

# API Keys from Environment Variables
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

# SMTP settings
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

def send_via_brevo_api(excel_io, report_date, recipient, total_units, total_quota, api_key):
    """
    Sends email with Excel attachment using Brevo HTTP API
    """
    try:
        dt = datetime.datetime.strptime(report_date, '%Y-%m-%d')
        formatted_date = dt.strftime('%d/%m/%Y')
        filename = f"damah_aka_{dt.strftime('%d_%m_%Y')}.xlsx"
    except Exception:
        formatted_date = report_date
        filename = f"damah_aka_{report_date}.xlsx"
        
    try:
        file_bytes = excel_io.getvalue()
    except Exception:
        excel_io.seek(0)
        file_bytes = excel_io.read()
        
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    
    html_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; color: #0f172a; padding: 25px; background-color: #f8fafc; border-radius: 16px; border: 1px solid #e2e8f0; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 18px; border-radius: 12px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 22px;">📊 דו"ח דמ"ח אכ"א יומי מלא (100% דיווח)</h2>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">מערכת ניהול ובקרת נוכחות אע"צים - צה"ל 🛡️</p>
        </div>
        
        <div style="padding: 20px 0;">
            <p style="font-size: 16px; font-weight: bold; color: #0f172a;">שלום נעם,</p>
            <p style="font-size: 15px; color: #334155; line-height: 1.6;">
                כל <strong>{total_units}</strong> יחידות אכ"א סיימו למלא את הדיווח היומי עבור תאריך <strong>{formatted_date}</strong> (100% התייצבות מלאה).
            </p>
            
            <div style="background: #e0f2fe; padding: 18px; border-radius: 12px; border-right: 5px solid #0284c7; margin: 20px 0;">
                <p style="margin: 0; font-weight: bold; font-size: 16px; color: #0369a1;">סה"כ מצבת אע"צים מדווחת: {total_quota} עובדים</p>
                <p style="margin: 5px 0 0 0; font-size: 13px; color: #0284c7;">100% מהיחידות מילאו בהצלחה ואימתו נתונים תואמים לתקן</p>
            </div>
            
            <p style="font-size: 15px; color: #334155;">
                מצורף למייל זה קובץ האקסל הרשמי (<strong>{filename}</strong>) מעובד, מחושב ומעוצב 100% לפי פורמט דמ"ח תע"צ.
            </p>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        
        <div style="text-align: center; color: #64748b; font-size: 13px;">
            <p style="margin: 0; font-weight: bold;">מערכת דמ"ח אכ"א האוטומטית 🛡️</p>
            <p style="margin: 4px 0 0 0;">הודעה זו נשלחה באופן אוטומטי בעת הגעה ל-100% דיווח יומי</p>
        </div>
    </div>
    """
    
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", recipient)
    
    payload = {
        "sender": {"name": "מערכת דמ\"ח אכ\"א צה\"ל", "email": sender_email},
        "to": [{"email": recipient, "name": "נעם בשרטי"}],
        "subject": f"📊 דו\"ח דמ\"ח אכ\"א יומי מלא (100% דיווח) - {formatted_date}",
        "htmlContent": html_content,
        "attachment": [
            {
                "name": filename,
                "content": b64_content
            }
        ]
    }
    
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"[BREVO SUCCESS] Email sent to {recipient}! Message ID: {res_data.get('messageId')}")
            return True, f"קובץ האקסל נשלח בהצלחה למייל {recipient}!"
    except Exception as e:
        print(f"[BREVO ERROR] Failed to send via Brevo API: {e}")
        return False, str(e)

def send_via_resend_api(excel_io, report_date, recipient, total_units, total_quota, api_key):
    """
    Sends email with Excel attachment using Resend HTTP API
    """
    try:
        dt = datetime.datetime.strptime(report_date, '%Y-%m-%d')
        formatted_date = dt.strftime('%d/%m/%Y')
        filename = f"damah_aka_{dt.strftime('%d_%m_%Y')}.xlsx"
    except Exception:
        formatted_date = report_date
        filename = f"damah_aka_{report_date}.xlsx"
        
    try:
        file_bytes = excel_io.getvalue()
    except Exception:
        excel_io.seek(0)
        file_bytes = excel_io.read()
        
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    
    payload = {
        "from": "Damah IDF System <onboarding@resend.dev>",
        "to": [recipient],
        "subject": f"📊 דו\"ח דמ\"ח אכ\"א יומי מלא (100% דיווח) - {formatted_date}",
        "html": f"<p>שלום נעם, מצורף דו\"ח דמ\"ח אכ\"א מלא (100% דיווח) לתאריך {formatted_date}.</p>",
        "attachments": [
            {
                "filename": filename,
                "content": b64_content
            }
        ]
    }
    
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"[RESEND SUCCESS] Email sent to {recipient}! Resend ID: {res_data.get('id')}")
            return True, f"קובץ האקסל נשלח בהצלחה למייל {recipient}!"
    except Exception as e:
        print(f"[RESEND ERROR] Failed to send via Resend API: {e}")
        return False, str(e)

def send_via_smtp(excel_io, report_date, recipient, total_units, total_quota):
    """
    Sends email via standard SMTP
    """
    try:
        dt = datetime.datetime.strptime(report_date, '%Y-%m-%d')
        formatted_date = dt.strftime('%d/%m/%Y')
        filename = f"damah_aka_{dt.strftime('%d_%m_%Y')}.xlsx"
    except Exception:
        formatted_date = report_date
        filename = f"damah_aka_{report_date}.xlsx"
        
    msg = MIMEMultipart()
    sender_email = SMTP_USER or recipient
    msg['From'] = f"מערכת דמ\"ח אכ\"א <{sender_email}>"
    msg['To'] = recipient
    msg['Subject'] = f"📊 דו\"ח דמ\"ח אכ\"א יומי מלא (100% דיווח) - {formatted_date}"
    
    body_text = f"שלום נעם,\n\nכל {total_units} יחידות אכ\"א סיימו למלא את הדיווח היומי עבור תאריך {formatted_date} (100% התייצבות).\nסה\"כ מצבת אע\"צים מדווחת: {total_quota} עובדים.\n\nמצורף קובץ האקסל הרשמי (XLSX) מעובד ומעוצב לפי פורמט דמ\"ח תע\"צ."
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    
    try:
        file_bytes = excel_io.getvalue()
    except Exception:
        excel_io.seek(0)
        file_bytes = excel_io.read()
        
    part = MIMEApplication(file_bytes, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    
    if not SMTP_PASS:
        print(f"[EMAIL NOTIFICATION TRIGGERED] 100% reporting reached for {report_date}! Target: {recipient}.")
        return False, "התראת 100% הופעלה במערכת."
        
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(sender_email, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"[SMTP SUCCESS] Excel report successfully emailed to {recipient} for date {report_date}!")
        return True, f"קובץ האקסל נשלח בהצלחה למייל {recipient}!"
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {recipient}: {e}")
        return False, str(e)

def send_damah_excel_email(excel_io, report_date, total_units, total_quota):
    """
    Main entry point: Tries Brevo -> Resend -> SMTP
    """
    recipient = os.environ.get("NOTIFICATION_EMAIL", TARGET_EMAIL)
    
    brevo_key = os.environ.get("BREVO_API_KEY", "")
    if brevo_key:
        ok, msg = send_via_brevo_api(excel_io, report_date, recipient, total_units, total_quota, brevo_key)
        if ok:
            return ok, msg
            
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if resend_key:
        ok, msg = send_via_resend_api(excel_io, report_date, recipient, total_units, total_quota, resend_key)
        if ok:
            return ok, msg
    
    return send_via_smtp(excel_io, report_date, recipient, total_units, total_quota)
