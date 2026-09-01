import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    all_recipients = list(dict.fromkeys(to_list + cc_list))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, all_recipients, msg.as_string())
