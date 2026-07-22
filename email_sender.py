import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import datetime

# Target recipient
TARGET_EMAIL = "noambasharti@gmail.com"

# SMTP Configuration from Environment Variables (with fallback defaults)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "idf.damah.system@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

def send_damah_excel_email(excel_io, report_date, total_units, total_quota):
    """
    Sends the generated Excel report (.xlsx) to target recipient when 100% reporting is reached.
    """
    recipient = os.environ.get("NOTIFICATION_EMAIL", TARGET_EMAIL)
    
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
    
    # Attach Excel File
    excel_io.seek(0)
    part = MIMEApplication(excel_io.read(), Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    
    if not SMTP_PASS:
        print(f"[EMAIL NOTIFICATION TRIGGERED] 100% reporting reached for {report_date}! Target: {recipient}.")
        print("[EMAIL NOTICE] SMTP_PASS environment variable is not configured. Email payload generated successfully.")
        return False, "התראת 100% הופעלה במערכת. יש להגדיר סיסמת אפליקציה ל-SMTP בשרת לשליחה פעילה."
        
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"[EMAIL SUCCESS] Excel report successfully emailed to {recipient} for date {report_date}!")
        return True, f"קובץ האקסל נשלח בהצלחה למייל {recipient}!"
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {recipient}: {e}")
        return False, str(e)
