import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

# Load settings from .env
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.school.dev")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "user")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password")
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@school.edu")

def send_substitution_notification(
    substitute_email: str, 
    details: Dict[str, Any]
) -> bool:
    """
    Sends an email notification to the assigned substitute teacher.
    Uses standard SMTP settings defined in the .env file.
    """
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"URGENT: Substitution Duty Assigned - {details['date']} {details['period']}"
    msg['From'] = EMAIL_FROM
    msg['To'] = substitute_email

    body_html = f"""
    <html>
    <body style="font-family: sans-serif; padding: 20px; border: 1px solid #ddd; max-width: 600px; margin: auto;">
        <h3 style="color: #4f46e5;">Substitution Alert: Immediate Action Required</h3>
        <p>Dear {details['substitute_name']},</p>
        <p>You have been assigned to cover a class due to an absence.</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Date:</td><td style="padding: 8px; border: 1px solid #ddd;">{details['date']} ({details['day']})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Time:</td><td style="padding: 8px; border: 1px solid #ddd;">{details['period']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Subject/Class:</td><td style="padding: 8px; border: 1px solid #ddd;">{details['class_name']} ({details['subject']})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Absent Teacher:</td><td style="padding: 8px; border: 1px solid #ddd;">{details['absent_name']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Reason:</td><td style="padding: 8px; border: 1px solid #ddd;">{details['reason'] or 'Absent'}</td></tr>
        </table>
        <p style="margin-top: 20px;">Please check the updated schedule immediately. Thank you for covering this period.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body_html, 'html'))

    try:
        # Connect to the SMTP server (e.g., SendGrid, Gmail SMTP)
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()  # Secure the connection
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, substitute_email, msg.as_string())
        server.quit()
        print(f"INFO: Email notification successfully sent to {substitute_email}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send email to {substitute_email}. Exception: {e}")
        return False