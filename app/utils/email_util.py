import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)


def send_email(to: str, subject: str, body: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Email is not configured. Set SMTP_USERNAME and SMTP_PASSWORD.",
        )

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [to], msg.as_string())
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
