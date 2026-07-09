"""Email client configured via an injected :class:`~solution.app.settings.Settings`."""

import smtplib
from email.mime.text import MIMEText

from solution.app.settings import Settings


class EmailClient:
    """Sends plain-text emails through SMTP using injected settings."""

    def __init__(self, settings: Settings) -> None:
        """Store the settings used to reach the SMTP server."""
        self._settings = settings

    def send(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text email to ``to``."""
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = self._settings.email_from
        msg["To"] = to

        with smtplib.SMTP(
            self._settings.email_smtp_host,
            self._settings.email_smtp_port,
        ) as smtp:
            smtp.sendmail(self._settings.email_from, [to], msg.as_string())
