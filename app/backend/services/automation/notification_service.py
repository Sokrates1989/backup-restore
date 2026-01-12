"""Notification service for backup automation.

This module provides notification capabilities for backup operations:
- Telegram notifications via bot API
- Email notifications via SMTP

Notifications are configured per-schedule in the retention.notifications field.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, Optional
from datetime import datetime


class NotificationService:
    """Service for sending backup notifications via Telegram and Email."""

    def __init__(self):
        """Initialize the notification service.
        
        Reads configuration from environment variables:
        - TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN_FILE
        - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
        """
        self.telegram_token = self._get_telegram_token()
        self.smtp_config = self._get_smtp_config()

    def _get_telegram_token(self) -> Optional[str]:
        """Get Telegram bot token from environment or file.
        
        Returns:
            Optional[str]: Telegram bot token or None if not configured.
        """
        token_file = os.getenv("TELEGRAM_BOT_TOKEN_FILE")
        if token_file:
            try:
                with open(token_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        
        return os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None

    def _get_smtp_config(self) -> Optional[Dict[str, Any]]:
        """Get SMTP configuration from environment.
        
        Returns:
            Optional[Dict[str, Any]]: SMTP config or None if not configured.
        """
        host = os.getenv("SMTP_HOST", "").strip()
        if not host:
            return None
        
        return {
            "host": host,
            "port": int(os.getenv("SMTP_PORT", "587")),
            "user": os.getenv("SMTP_USER", "").strip(),
            "password": os.getenv("SMTP_PASSWORD", "").strip(),
            "from_addr": os.getenv("SMTP_FROM", "").strip(),
            "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        }

    async def send_backup_notification(
        self,
        *,
        schedule_name: str,
        target_name: str,
        status: str,
        backup_filename: Optional[str] = None,
        error_message: Optional[str] = None,
        notifications_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send backup status notifications based on configuration.
        
        Args:
            schedule_name: Name of the backup schedule.
            target_name: Name of the database target.
            status: Backup status (success, failed, warning).
            backup_filename: Name of the backup file (for success).
            error_message: Error message (for failed).
            notifications_config: Notification configuration from schedule retention.
        
        Returns:
            Dict with notification results.
        """
        if not notifications_config:
            return {"sent": False, "reason": "No notifications configured"}
        
        results = {"telegram": None, "email": None}
        
        # Build message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if status == "success":
            emoji = "✅"
            title = "Backup Completed"
            details = f"File: {backup_filename}" if backup_filename else ""
        elif status == "failed":
            emoji = "❌"
            title = "Backup Failed"
            details = f"Error: {error_message}" if error_message else ""
        else:  # warning
            emoji = "⚠️"
            title = "Backup Warning"
            details = error_message or ""
        
        message = f"{emoji} <b>{title}</b>\n\n"
        message += f"<b>Schedule:</b> {schedule_name}\n"
        message += f"<b>Database:</b> {target_name}\n"
        message += f"<b>Time:</b> {timestamp}\n"
        if details:
            message += f"\n{details}"
        
        # Send Telegram notification
        telegram_config = notifications_config.get("telegram", {})
        if telegram_config.get("enabled") and self._should_notify(telegram_config, status):
            results["telegram"] = await self._send_telegram(
                chat_id=telegram_config.get("chat_id"),
                message=message,
            )
        
        # Send Email notification
        email_config = notifications_config.get("email", {})
        if email_config.get("enabled") and self._should_notify(email_config, status):
            plain_message = message.replace("<b>", "").replace("</b>", "")
            results["email"] = await self._send_email(
                to_addr=email_config.get("to"),
                subject=f"Backup {title}: {schedule_name}",
                body=plain_message,
            )
        
        return results

    def _should_notify(self, config: Dict[str, Any], status: str) -> bool:
        """Check if notification should be sent based on status and config.
        
        Args:
            config: Notification channel config (telegram or email).
            status: Current backup status.
        
        Returns:
            bool: True if notification should be sent.
        """
        if status == "success":
            return config.get("on_success", False)
        elif status == "failed":
            return config.get("on_failure", True)
        else:  # warning
            return config.get("on_warning", False)

    async def _send_telegram(
        self,
        *,
        chat_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send a Telegram message.
        
        Args:
            chat_id: Telegram chat ID.
            message: Message text (HTML supported).
        
        Returns:
            Dict with send result.
        """
        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}
        
        if not chat_id:
            return {"success": False, "error": "Chat ID not provided"}
        
        try:
            import httpx
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                data = response.json()
                
                if data.get("ok"):
                    return {"success": True, "message_id": data.get("result", {}).get("message_id")}
                else:
                    return {"success": False, "error": data.get("description", "Unknown error")}
        
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_email(
        self,
        *,
        to_addr: str,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """Send an email notification.
        
        Args:
            to_addr: Recipient email address.
            subject: Email subject.
            body: Email body text.
        
        Returns:
            Dict with send result.
        """
        if not self.smtp_config:
            return {"success": False, "error": "SMTP not configured"}
        
        if not to_addr:
            return {"success": False, "error": "Recipient email not provided"}
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["from_addr"] or self.smtp_config["user"]
            msg["To"] = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            if self.smtp_config["use_tls"]:
                server = smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"])
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"])
            
            if self.smtp_config["user"] and self.smtp_config["password"]:
                server.login(self.smtp_config["user"], self.smtp_config["password"])
            
            server.sendmail(msg["From"], to_addr, msg.as_string())
            server.quit()
            
            return {"success": True}
        
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the singleton notification service instance.
    
    Returns:
        NotificationService: The notification service.
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
