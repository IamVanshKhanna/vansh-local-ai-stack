"""
Notification utilities for local AI stack scripts.

Provides desktop notifications and email notifications for script alerts.

Usage:
    from examples.notify import notify, notify_if_alert

    notify("Script Complete", "Files organized successfully")
"""

import logging
import os
import platform
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def notify(
    title: str,
    message: str,
    urgency: str = "normal",
    timeout: int = 5000
) -> bool:
    """
    Send a desktop notification.

    Args:
        title: Notification title
        message: Notification body
        urgency: Urgency level (low, normal, critical)
        timeout: Timeout in milliseconds

    Returns:
        True if notification was sent successfully
    """
    system = platform.system()

    try:
        if system == "Windows":
            # Windows toast notification via PowerShell
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show(
                "{message}",
                "{title}",
                "OK",
                "Information"
            )
            '''
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=10
            )
            # Alternative: win10toast library
            return True

        elif system == "Darwin":  # macOS
            subprocess.run(
                [
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}"'
                ],
                check=True
            )
            return True

        elif system == "Linux":
            # Try notify-send (libnotify)
            subprocess.run(
                ["notify-send", "-u", urgency, "-t", str(timeout), title, message],
                check=True
            )
            return True

        else:
            logger.warning(f"Notifications not supported on {system}")
            return False

    except FileNotFoundError:
        logger.warning("Notification tool not found")
        return False
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
        return False


def notify_email(
    subject: str,
    body: str,
    to: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: int = 587,
    from_addr: Optional[str] = None,
    password: Optional[str] = None
) -> bool:
    """
    Send an email notification.

    Requires SMTP configuration in environment:
        EMAIL_SMTP_SERVER
        EMAIL_SMTP_PORT
        EMAIL_USER
        EMAIL_PASSWORD

    Args:
        subject: Email subject
        body: Email body text
        to: Recipient address
        smtp_server: SMTP server host
        smtp_port: SMTP server port
        from_addr: Sender address
        password: SMTP password

    Returns:
        True if email was sent successfully
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Get configuration from environment
    smtp_server = smtp_server or os.getenv("EMAIL_SMTP_SERVER")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", smtp_port))
    from_addr = from_addr or os.getenv("EMAIL_USER")
    password = password or os.getenv("EMAIL_PASSWORD")
    to = to or os.getenv("EMAIL_TO", from_addr)

    if not all([smtp_server, from_addr, password]):
        logger.warning("Email not configured. Set EMAIL_* environment variables.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_addr, password)
            server.send_message(msg)

        logger.info(f"Email sent to {to}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def notify_webhook(url: str, payload: dict) -> bool:
    """
    Send a notification to a webhook URL.

    Args:
        url: Webhook URL
        payload: JSON payload to send

    Returns:
        True if webhook was called successfully
    """
    try:
        import requests

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True

    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        return False


def notify_if_alert(level: str, title: str, message: str, threshold: str = "warning"):
    """
    Send notification only if level meets threshold.

    Args:
        level: Current level (pass, warning, fail)
        title: Notification title
        message: Notification message
        threshold: Minimum level to notify (warning or fail)
    """
    levels = {"pass": 0, "warning": 1, "fail": 2}
    threshold_level = levels.get(threshold, 1)
    current_level = levels.get(level, 0)

    if current_level >= threshold_level:
        notify(title, message)


if __name__ == "__main__":
    # Test notification
    print("Testing desktop notification...")
    success = notify(
        "Local AI Stack",
        "This is a test notification from health_check.py"
    )
    print(f"Notification sent: {success}")
