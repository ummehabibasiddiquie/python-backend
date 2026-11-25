import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

TEST_MAIL_SUBJECT_PREFIX = "[VERCEL TEST]"
_TEST_MAIL_BANNER_HTML = (
    '<div style="background:#fff3cd;border:2px solid #f0ad4e;color:#7a4e00;'
    'padding:12px 16px;margin:0 0 16px 0;font-family:Arial,sans-serif;font-size:14px;line-height:1.4;">'
    "<strong>VERCEL / TEST ENVIRONMENT</strong><br>"
    "This message was sent while testing HRMS on Vercel against the test database "
    "(mytfs_test). It is for testing only. Please ignore it for live work."
    "</div>"
)
_TEST_MAIL_BANNER_TEXT = (
    "VERCEL / TEST ENVIRONMENT: This email is from HRMS testing on Vercel "
    "(database mytfs_test). For testing only. Ignore for live work.\n\n"
)


def is_test_mail_env() -> bool:
    flag = (os.getenv("MAIL_TEST_BANNER") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return (os.getenv("DB_DATABASE") or "").strip().lower() == "mytfs_test"


def apply_test_mail_notice(subject, html_body, text_body=None):
    """Prefix subject + banner when APIs use mytfs_test / MAIL_TEST_BANNER. Live mytfs is unchanged."""
    if not is_test_mail_env():
        return subject, html_body, text_body
    subj = subject or ""
    if not subj.upper().startswith(TEST_MAIL_SUBJECT_PREFIX):
        subj = f"{TEST_MAIL_SUBJECT_PREFIX} {subj}".strip()
    html = html_body or ""
    lower = html.lower()
    body_at = lower.find("<body")
    if body_at >= 0:
        gt = html.find(">", body_at)
        if gt >= 0:
            html = html[: gt + 1] + _TEST_MAIL_BANNER_HTML + html[gt + 1 :]
        else:
            html = _TEST_MAIL_BANNER_HTML + html
    else:
        html = _TEST_MAIL_BANNER_HTML + html
    text = None if text_body is None else (_TEST_MAIL_BANNER_TEXT + text_body)
    return subj, html, text


def send_email(to_email, subject: str, html_body: str, cc=None):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_name = os.getenv("SMTP_FROM_NAME", "No-Reply")

    if not all([host, user, password]):
        raise RuntimeError("SMTP configuration missing")

    if isinstance(to_email, str):
        to_list = [e.strip() for e in to_email.replace(";", ",").split(",") if e.strip()]
    else:
        to_list = [str(e).strip() for e in (to_email or []) if str(e).strip()]
    if not to_list:
        raise ValueError("No recipient email address")

    cc_list = []
    if cc:
        if isinstance(cc, str):
            cc_list = [e.strip() for e in cc.replace(";", ",").split(",") if e.strip()]
        else:
            cc_list = [str(e).strip() for e in cc if str(e).strip()]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    subject, html_body, _ = apply_test_mail_notice(subject, html_body)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    all_recipients = list(dict.fromkeys(to_list + cc_list))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, all_recipients, msg.as_string())
