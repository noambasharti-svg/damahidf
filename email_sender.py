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

# Resend API Key (Can be set via env var RESEND_API_KEY)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# Fallback SMTP settings
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "idf.damah.system@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

def send_via_resend_api(excel_io, report_date, recipient, total_units, total_quota, api_key):
    """
    Sends email with Excel attachment using Resend HTTP API (No SMTP needed!)
    """
    try:
        dt = datetime.datetime.strptime(report_date, '%Y-%m-%d')
        formatted_date = dt.strftime('%d/%m/%Y')
        filename = f"damah_aka_{dt.strftime('%d_%m_%Y')}.xlsx"
    except Exception:
        formatted_date = report_date
        filename = f"damah_aka_{report_date}.xlsx"
        
    excel_io.seek(0)
    file_bytes = excel_io.read()
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    
    html_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; color: #0f172a; padding: 20px; background-color: #f8fafc; border-radius: 12px;">
        <h2 style="color: #0284c7;">📊 דו"ח דמ"ח אכ"א יומי מלא (100% דיווח)</h2>
        <p style="font-size: 16px;">שלום נעם,</p>
        <p style="font-size: 15px;">כל <strong>{total_units}</strong> יחידות אכ"א סיימו למלא את הדיווח היומי עבור תאריך <strong>{formatted_date}</strong> (100% התייצבות).</p>
        <div style="background: #e0f2fe; padding: 15px; border-radius: 8px; border-right: 4px solid #0284c7; margin: 15px 0;">
            <p style="margin: 0; font-weight: bold; color: #0369a1;">סה"כ מצבת אע"צים מדווחת: {total_quota} עובדים</p>
        </div>
        <p style="font-size: 15px;">מצורף קובץ האקסל הרשמי (XLSX) מעובד ומעוצב לפי פורמט דמ"ח תע"צ.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="font-size: 13px; color: #64748b;">מערכת ניהול ובקרת אע"צים - אכ"א צה"ל 🛡️</p>
    </div>
    """
    
    payload = {
        "from": "Damah IDF System <onboarding@resend.dev>",
        "to": [recipient],
        "subject": f"📊 דו\"ח דמ\"ח אכ\"א יומי מלא (100% דיווח) - {formatted_date}",
        "html": html_content,
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
            print(f"[RESEND SUCCESS] Email sent successfully to {recipient}! Resend ID: {res_data.get('id')}")
            return True, "קובץ האקסל נשלח בהצלחה למייל שלך!"
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
    msg['From'] = f"מערכת דמ\"ח אכ\"א <{SMTP_USER}>"
    msg['To'] = recipient
    msg['Subject'] = f"📊 דו\"ח דמ\"ח אכ\"א יומי מלא (100% דיווח) - {formatted_date}"
    
    body_text = f"""שלום נעם,

כל {total_units} יחידות אכ"א סיימו למלא את הדיווח היומי עבור תאריך {formatted_date} (100% התייצבות).
סה"כ מצבת אע"צים מדווחת: {total_quota} עובדים.

מצורף קובץ האקסל הרשמי (XLSX) מעובד ומעוצב לפי פורמט דמ"ח תע"צ.

בברכה,
מערכת ניהול ובקרת אע"צים - אכ"א צה"ל 🛡️
"""
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    
    excel_io.seek(0)
    part = MIMEApplication(excel_io.read(), Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    
    if not SMTP_PASS:
        print(f"[EMAIL NOTIFICATION TRIGGERED] 100% reporting reached for {report_date}! Target: {recipient}.")
        return False, "התראת 100% הופעלה במערכת. יש להגדיר RESEND_API_KEY או SMTP_PASS בשרת לשליחה פעילה."
        
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"[SMTP SUCCESS] Excel report successfully emailed to {recipient} for date {report_date}!")
        return True, f"קובץ האקסל נשלח בהצלחה למייל {recipient}!"
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {recipient}: {e}")
        return False, str(e)

def send_damah_excel_email(excel_io, report_date, total_units, total_quota):
    """
    Main entry point: Tries Resend HTTP API first, falls back to SMTP.
    """
    recipient = os.environ.get("NOTIFICATION_EMAIL", TARGET_EMAIL)
    api_key = os.environ.get("RESEND_API_KEY", RESEND_API_KEY)
    
    if api_key:
        return send_via_resend_api(excel_io, report_date, recipient, total_units, total_quota, api_key)
    
    return send_via_smtp(excel_io, report_date, recipient, total_units, total_quota)
