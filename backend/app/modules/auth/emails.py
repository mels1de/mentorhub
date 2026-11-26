from html import escape

from app.core.config import Settings
from app.integrations.ports import EmailMessage


def _link(settings: Settings, path: str, token: str) -> str:
    # Token in the fragment: browsers never send it to a server or leak it in the Referer header.
    return f"{settings.frontend_url.rstrip('/')}/{path}#token={token}"


def _html(paragraph: str, link: str, action: str, footer: str) -> str:
    return (
        f"<p>{escape(paragraph)}</p>"
        f'<p><a href="{escape(link)}">{escape(action)}</a></p>'
        f"<p>{escape(footer)}</p>"
    )


def verification_email(to: str, token: str, settings: Settings) -> EmailMessage:
    link = _link(settings, "verify-email", token)
    hours = settings.email_verification_ttl_hours
    paragraph = "Welcome to MentorHub! Please confirm your email address."
    footer = f"The link is valid for {hours} hours. If you didn't sign up, ignore this email."
    return EmailMessage(
        to=to,
        subject="Confirm your email",
        text=f"{paragraph}\n\n{link}\n\n{footer}\n",
        html=_html(paragraph, link, "Confirm email", footer),
    )


def password_reset_email(to: str, token: str, settings: Settings) -> EmailMessage:
    link = _link(settings, "reset-password", token)
    minutes = settings.password_reset_ttl_minutes
    paragraph = "Someone asked to reset the password of your MentorHub account."
    footer = (
        f"The link is valid for {minutes} minutes and works once. "
        "If it wasn't you, ignore this email — your password stays the same."
    )
    return EmailMessage(
        to=to,
        subject="Reset your password",
        text=f"{paragraph}\n\n{link}\n\n{footer}\n",
        html=_html(paragraph, link, "Choose a new password", footer),
    )
