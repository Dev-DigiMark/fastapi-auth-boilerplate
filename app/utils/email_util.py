import os
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

import aiosmtplib
from dotenv import load_dotenv
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company Name")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_email_template(template_name: str, **context) -> str:
    """Render an HTML email template from app/templates/."""
    template = _jinja_env.get_template(template_name)
    return template.render(
        company_name=COMPANY_NAME,
        year=datetime.utcnow().year,
        **context,
    )


async def send_email(to: str, subject: str, body: str):
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
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
    except aiosmtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
