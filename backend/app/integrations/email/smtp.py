from email.message import EmailMessage as MimeMessage

import aiosmtplib

from app.core.config import Settings
from app.integrations.exceptions import IntegrationError, IntegrationUnavailableError
from app.integrations.ports import EmailMessage

TIMEOUT_SECONDS = 10.0


class SmtpEmailSender:
    """EmailSender over SMTP: Mailpit locally, any SMTP relay (SES, Postmark...) in production."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.settings.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        if message.html is not None:
            mime.add_alternative(message.html, subtype="html")

        password = self.settings.smtp_password
        try:
            await aiosmtplib.send(
                mime,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_username,
                password=password.get_secret_value() if password else None,
                start_tls=self.settings.smtp_start_tls,
                timeout=TIMEOUT_SECONDS,
            )
        except aiosmtplib.SMTPRecipientsRefused as exc:
            raise IntegrationError("The mail server refused the recipient.") from exc
        except (aiosmtplib.SMTPException, OSError) as exc:
            # Connection errors, timeouts and 4xx/5xx replies: let the task retry later.
            raise IntegrationUnavailableError("The mail server is unavailable.") from exc
