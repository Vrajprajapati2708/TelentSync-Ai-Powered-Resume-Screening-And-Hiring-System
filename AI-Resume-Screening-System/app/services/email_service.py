# ============================================================
#  TalentSync — Production Email Subsystem (GAP-12)
#  Multi-provider architecture with secure SMTP delivery,
#  in-memory test isolation, and professional HTML/Text templates.
# ============================================================

import os
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List
from flask import current_app
from app.config.settings import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    text_body: str
    html_body: str
    from_email: str = "noreply@talentsync.ai"
    sent_at: datetime = field(default_factory=datetime.now)


class BaseEmailProvider:
    """Abstract interface for email delivery providers."""
    def send(self, message: EmailMessage) -> bool:
        raise NotImplementedError


class SMTPEmailProvider(BaseEmailProvider):
    """Production-grade SMTP provider supporting TLS and authenticated delivery."""
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        timeout: int = 10
    ):
        self.host = host or os.getenv("MAIL_HOST", Config.MAIL_HOST)
        self.port = port or int(os.getenv("MAIL_PORT", Config.MAIL_PORT))
        self.username = username or os.getenv("MAIL_USERNAME", Config.MAIL_USERNAME)
        self.password = password or os.getenv("MAIL_PASSWORD", Config.MAIL_PASSWORD)
        self.use_tls = use_tls if use_tls is not None else Config.MAIL_USE_TLS
        self.from_email = from_email or os.getenv("MAIL_FROM", Config.MAIL_FROM)
        self.timeout = timeout

    def send(self, message: EmailMessage) -> bool:
        """Send an email over SMTP without exposing credentials on failure."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = message.from_email or self.from_email
        msg["To"] = message.to_email

        # Attach text alternative first, then HTML (RFC 2046)
        msg.attach(MIMEText(message.text_body, "plain", "utf-8"))
        msg.attach(MIMEText(message.html_body, "html", "utf-8"))

        server = None
        try:
            logger.info(f"Connecting to SMTP server at {self.host}:{self.port} (TLS={self.use_tls})")
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(msg["From"], [message.to_email], msg.as_string())
            logger.info(f"Email successfully delivered to {message.to_email} (Subject: '{message.subject}')")
            return True
        except (smtplib.SMTPException, socket.error, TimeoutError, OSError) as e:
            # Safe diagnostic logging: Do NOT log passwords or secrets
            logger.error(f"SMTP delivery failure for recipient {message.to_email}: {type(e).__name__} - {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass


class TestEmailProvider(BaseEmailProvider):
    """In-memory email provider for isolated unit and integration tests."""
    _outbox: List[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        TestEmailProvider._outbox.append(message)
        logger.info(f"[TestEmailProvider] Captured email for {message.to_email}: '{message.subject}'")
        return True

    @classmethod
    def get_outbox(cls) -> List[EmailMessage]:
        return cls._outbox

    @classmethod
    def clear_outbox(cls) -> None:
        cls._outbox.clear()

    @classmethod
    def get_last_email(cls) -> Optional[EmailMessage]:
        return cls._outbox[-1] if cls._outbox else None


# ── Global Provider Factory ──────────────────────────────────
_test_provider = TestEmailProvider()
_smtp_provider = SMTPEmailProvider()


def get_email_provider() -> BaseEmailProvider:
    """Return the active email provider based on application configuration."""
    provider_type = "test"
    try:
        if current_app:
            if current_app.config.get("TESTING"):
                return _test_provider
            provider_type = current_app.config.get("MAIL_PROVIDER", "test").lower()
    except RuntimeError:
        # Outside Flask application context
        provider_type = os.getenv("MAIL_PROVIDER", "test").lower()

    if provider_type == "smtp":
        return _smtp_provider
    return _test_provider


# ── Professional Email Templates & Dispatchers ───────────────

def send_verification_email(to_email: str, raw_token: str, user_name: str = "") -> bool:
    """
    Construct and dispatch a secure account verification email.
    """
    try:
        base_url = current_app.config.get("APP_BASE_URL", "http://localhost:5000").rstrip("/")
    except RuntimeError:
        base_url = os.getenv("APP_BASE_URL", "http://localhost:5000").rstrip("/")

    verification_link = f"{base_url}/#page-verify?token={raw_token}"
    greeting = f"Hi {user_name}," if user_name else "Hello,"

    text_body = f"""{greeting}

Welcome to HireAI / TalentSync!

Please verify your email address to activate your account and access all recruitment features.
Click or copy this link into your browser:
{verification_link}

This verification link will expire in 24 hours.

If you did not create a TalentSync account, you can safely ignore this email.

Best regards,
The TalentSync Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Verify Your Email</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 10px;">
  <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <div style="background: linear-gradient(135deg, #1260cc, #00c9a7); padding: 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">TalentSync</h1>
      <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">AI-Powered Recruitment & Resume Intelligence</p>
    </div>
    <div style="padding: 30px 24px;">
      <h2 style="color: #0f172a; font-size: 18px; margin-top: 0;">Verify Your Email Address</h2>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">{greeting}</p>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">Thank you for registering with TalentSync. Please click the button below to verify your email address and unlock full platform capabilities:</p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{verification_link}" style="background-color: #1260cc; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block;">Verify Email Address</a>
      </div>
      <p style="color: #64748b; font-size: 12px; line-height: 1.5;">Or copy and paste this secure URL into your browser:<br><a href="{verification_link}" style="color: #1260cc; word-break: break-all;">{verification_link}</a></p>
      <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;">
      <p style="color: #94a3b8; font-size: 12px; margin: 0;">This link is valid for <strong>24 hours</strong>. If you did not create an account with TalentSync, please disregard this message.</p>
    </div>
  </div>
</body>
</html>"""

    msg = EmailMessage(
        to_email=to_email,
        subject="Verify your TalentSync account",
        text_body=text_body,
        html_body=html_body,
        from_email=os.getenv("MAIL_FROM", Config.MAIL_FROM)
    )
    provider = get_email_provider()
    return provider.send(msg)


def send_password_reset_email(to_email: str, raw_token: str, user_name: str = "") -> bool:
    """
    Construct and dispatch a secure password reset email.
    """
    try:
        base_url = current_app.config.get("APP_BASE_URL", "http://localhost:5000").rstrip("/")
    except RuntimeError:
        base_url = os.getenv("APP_BASE_URL", "http://localhost:5000").rstrip("/")

    reset_link = f"{base_url}/#page-reset?token={raw_token}"
    greeting = f"Hi {user_name}," if user_name else "Hello,"

    text_body = f"""{greeting}

We received a request to reset your password for your TalentSync account.

To reset your password, visit this link:
{reset_link}

This link is single-use and will expire in 15 minutes.

Security Notice: If you did not request this password reset, your account is safe and you can safely ignore this email. Your password will remain unchanged.

Best regards,
The TalentSync Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 10px;">
  <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">TalentSync</h1>
      <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Account Security</p>
    </div>
    <div style="padding: 30px 24px;">
      <h2 style="color: #0f172a; font-size: 18px; margin-top: 0;">Password Reset Request</h2>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">{greeting}</p>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">We received a request to reset the password for your TalentSync account. Click the button below to choose a new password:</p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{reset_link}" style="background-color: #1260cc; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block;">Reset Password</a>
      </div>
      <p style="color: #64748b; font-size: 12px; line-height: 1.5;">Or copy and paste this secure URL into your browser:<br><a href="{reset_link}" style="color: #1260cc; word-break: break-all;">{reset_link}</a></p>
      <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;">
      <p style="color: #94a3b8; font-size: 12px; margin: 0;">This link is single-use and will expire in <strong>15 minutes</strong>.<br><strong>Security Notice:</strong> If you did not request a password reset, you can safely discard this email.</p>
    </div>
  </div>
</body>
</html>"""

    msg = EmailMessage(
        to_email=to_email,
        subject="Reset your TalentSync password",
        text_body=text_body,
        html_body=html_body,
        from_email=os.getenv("MAIL_FROM", Config.MAIL_FROM)
    )
    provider = get_email_provider()
    return provider.send(msg)
