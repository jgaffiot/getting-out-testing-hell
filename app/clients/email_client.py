import smtplib
from email.mime.text import MIMEText
from app.config import EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_FROM


class EmailClient:
    def send(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to

        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as smtp:
            smtp.sendmail(EMAIL_FROM, [to], msg.as_string())
