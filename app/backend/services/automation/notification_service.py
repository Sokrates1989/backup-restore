"""Notification service for backup automation.

This module provides notification capabilities for backup operations:
- Telegram notifications via bot API
- Email notifications via SMTP

Notifications are configured per-schedule in the ``retention.notifications`` field.
Both a legacy single-recipient format and a newer multi-recipient format are
supported.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.automation.notification_utils import (
    extract_email_recipients,
    extract_telegram_recipients,
    should_notify_for_min_severity,
)


logger = logging.getLogger(__name__)


def _build_smtp_ssl_context(*, allow_insecure: bool, ca_cert_file: str) -> ssl.SSLContext:
    """Build an SSL context for SMTP connections.

    Args:
        allow_insecure: When True, disable certificate verification.
        ca_cert_file: Optional CA bundle path used to validate the remote certificate.

    Returns:
        ssl.SSLContext: SSL context.
    """

    if allow_insecure:
        return ssl._create_unverified_context()

    cafile = str(ca_cert_file or "").strip()
    if cafile:
        try:
            context = ssl.create_default_context(cafile=cafile)
            logger.info("Using custom SMTP CA bundle cafile=%s", cafile)
            return context
        except Exception:
            logger.exception("Failed to load SMTP CA bundle cafile=%s; falling back to default trust store", cafile)

    return ssl.create_default_context()


def _coerce_size_bytes(value: Any) -> Optional[int]:
    """Coerce a size value into bytes.

    Args:
        value: Raw size value.

    Returns:
        Optional[int]: Size in bytes, or None when unavailable.
    """

    if value is None:
        return None

    try:
        size = float(value)
    except (TypeError, ValueError):
        return None

    if size < 0:
        return None
    return int(size)


def _format_size_mb(size_bytes: Optional[int]) -> Optional[str]:
    """Format a byte size as megabytes.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Optional[str]: Formatted size label or None when unavailable.
    """

    if size_bytes is None:
        return None

    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def _collect_upload_locations(uploads: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Collect destination lines for upload summaries.

    Args:
        uploads: Upload metadata list.

    Returns:
        List[str]: Destination summary lines.
    """

    lines: List[str] = []
    for upload in uploads or []:
        if not isinstance(upload, dict):
            continue
        destination_name = str(upload.get("destination_name") or "").strip() or "Unknown"
        backup_name = str(upload.get("backup_name") or upload.get("backup_id") or "").strip()
        size_label = _format_size_mb(_coerce_size_bytes(upload.get("size")))
        line = destination_name
        if backup_name:
            line = f"{destination_name}: {backup_name}"
        if size_label:
            line = f"{line} ({size_label})"
        lines.append(line)
    return lines


def _get_primary_upload_size(uploads: Optional[List[Dict[str, Any]]]) -> Optional[int]:
    """Return the first available upload size.

    Args:
        uploads: Upload metadata list.

    Returns:
        Optional[int]: Size in bytes, or None when unavailable.
    """

    for upload in uploads or []:
        if not isinstance(upload, dict):
            continue
        size = _coerce_size_bytes(upload.get("size"))
        if size is not None:
            return size
    return None


class NotificationService:
    """Service for sending backup notifications via Telegram and Email."""

    def _should_notify_legacy(self, config: Dict[str, Any], status: str) -> bool:
        """Return True when a legacy config should notify for the given status.

        Args:
            config: Legacy channel config.
            status: Backup status.

        Returns:
            bool: True if the legacy configuration enables this event.
        """

        if status == "success":
            return bool(config.get("on_success", False))
        if status == "failed":
            return bool(config.get("on_failure", True))
        return bool(config.get("on_warning", False))

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
        
        port = int(os.getenv("SMTP_PORT", "587"))
        use_ssl_raw = os.getenv("SMTP_USE_SSL", "").strip().lower()
        use_ssl = (use_ssl_raw in ("true", "1", "yes")) if use_ssl_raw else (port == 465)

        allow_insecure_certs = os.getenv("SMTP_ALLOW_INSECURE_CERTS", "false").lower() in ("true", "1", "yes")
        ca_cert_file = os.getenv("SMTP_CA_CERT_FILE", "").strip()

        return {
            "host": host,
            "port": port,
            "user": os.getenv("SMTP_USER", "").strip(),
            "password": os.getenv("SMTP_PASSWORD", "").strip(),
            "from_addr": os.getenv("SMTP_FROM", "").strip(),
            "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
            "use_ssl": use_ssl,
            "allow_insecure_certs": allow_insecure_certs,
            "ca_cert_file": ca_cert_file,
        }

    async def send_backup_notification(
        self,
        *,
        schedule_name: str,
        target_name: str,
        status: str,
        backup_filename: Optional[str] = None,
        error_message: Optional[str] = None,
        uploads: Optional[List[Dict[str, Any]]] = None,
        backup_file_path: Optional[Path | str] = None,
        backup_size_bytes: Optional[int] = None,
        notifications_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send backup status notifications based on configuration.
        
        Args:
            schedule_name: Name of the backup schedule.
            target_name: Name of the database target.
            status: Backup status (success, failed, warning).
            backup_filename: Name of the backup file (for success).
            error_message: Error message (for failed).
            uploads: Upload metadata list.
            backup_file_path: Optional local path to the backup artifact.
            backup_size_bytes: Optional backup size in bytes.
            notifications_config: Notification configuration from schedule retention.
        
        Returns:
            Dict[str, Any]: Notification results.
        """
        if not notifications_config:
            logger.debug(
                "Notifications skipped for schedule=%s status=%s (no notifications configured)",
                schedule_name,
                status,
            )
            return {"sent": False, "reason": "No notifications configured"}

        results: Dict[str, Any] = {"telegram": [], "email": []}
        
        # Build message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        upload_locations = _collect_upload_locations(uploads)
        size_bytes = backup_size_bytes or _get_primary_upload_size(uploads)
        attachment_path = None
        attachment_name = None

        if backup_file_path:
            backup_path = Path(backup_file_path)
            if backup_path.exists():
                attachment_path = backup_path
                attachment_name = backup_filename or backup_path.name
                if size_bytes is None:
                    try:
                        size_bytes = backup_path.stat().st_size
                    except OSError:
                        size_bytes = None

        if status == "success":
            emoji = "✅"
            title = "Backup Completed"
            details = ""
        elif status == "failed":
            emoji = "❌"
            title = "Backup Failed"
            details = f"Error: {error_message}" if error_message else ""
        else:  # warning
            emoji = "⚠️"
            title = "Backup Warning"
            details = error_message or ""

        size_label = _format_size_mb(size_bytes)

        message = f"{emoji} <b>{title}</b>\n\n"
        message += f"<b>Status:</b> {status}\n"
        message += f"<b>Schedule:</b> {schedule_name}\n"
        message += f"<b>Database:</b> {target_name}\n"
        message += f"<b>Time:</b> {timestamp}\n"
        if backup_filename:
            message += f"<b>Backup file:</b> {backup_filename}\n"
        if size_label:
            message += f"<b>Size:</b> {size_label}\n"
        if upload_locations:
            message += "<b>Stored at:</b>\n"
            message += "\n".join(f"- {line}" for line in upload_locations)
            message += "\n"
        if details:
            message += f"\n{details}"

        logger.info(
            "Preparing notifications for schedule=%s target=%s status=%s",
            schedule_name,
            target_name,
            status,
        )

        # Send Telegram notifications
        telegram_config = notifications_config.get("telegram", {})
        if isinstance(telegram_config, dict) and telegram_config.get("enabled"):
            attach_backup = bool(telegram_config.get("attach_backup"))
            if isinstance(telegram_config.get("recipients"), list):
                telegram_recipients = extract_telegram_recipients(telegram_config)
                for recipient in telegram_recipients:
                    if not should_notify_for_min_severity(status=status, min_severity=recipient.get("min_severity")):
                        continue
                    should_attach = bool(attach_backup and status == "success" and attachment_path)
                    logger.info(
                        "Sending Telegram notification schedule=%s status=%s chat_id=%s",
                        schedule_name,
                        status,
                        recipient.get("chat_id"),
                    )
                    if should_attach:
                        response = await self._send_telegram_document(
                            chat_id=recipient.get("chat_id"),
                            file_path=attachment_path,
                            filename=attachment_name,
                            caption=message,
                        )
                    else:
                        response = await self._send_telegram(chat_id=recipient.get("chat_id"), message=message)
                    if not response.get("success"):
                        logger.warning(
                            "Telegram notification failed schedule=%s chat_id=%s error=%s",
                            schedule_name,
                            recipient.get("chat_id"),
                            response.get("error"),
                        )
                    results["telegram"].append({"chat_id": recipient.get("chat_id"), **response})
            else:
                if self._should_notify_legacy(telegram_config, status):
                    chat_id = str(telegram_config.get("chat_id") or "").strip()
                    should_attach = bool(attach_backup and status == "success" and attachment_path)
                    logger.info(
                        "Sending Telegram notification schedule=%s status=%s chat_id=%s",
                        schedule_name,
                        status,
                        chat_id,
                    )
                    if should_attach:
                        response = await self._send_telegram_document(
                            chat_id=chat_id,
                            file_path=attachment_path,
                            filename=attachment_name,
                            caption=message,
                        )
                    else:
                        response = await self._send_telegram(chat_id=chat_id, message=message)
                    if not response.get("success"):
                        logger.warning(
                            "Telegram notification failed schedule=%s chat_id=%s error=%s",
                            schedule_name,
                            chat_id,
                            response.get("error"),
                        )
                    results["telegram"].append({"chat_id": chat_id, **response})

        # Send email notifications
        email_config = notifications_config.get("email", {})
        if isinstance(email_config, dict) and email_config.get("enabled"):
            plain_message = message.replace("<b>", "").replace("</b>", "")
            attach_backup = bool(email_config.get("attach_backup"))
            if isinstance(email_config.get("recipients"), list):
                email_recipients = extract_email_recipients(email_config)
                for recipient in email_recipients:
                    if not should_notify_for_min_severity(status=status, min_severity=recipient.get("min_severity")):
                        continue
                    should_attach = bool(attach_backup and status == "success" and attachment_path)
                    logger.info(
                        "Sending email notification schedule=%s status=%s to=%s",
                        schedule_name,
                        status,
                        recipient.get("to"),
                    )
                    response = await self._send_email(
                        to_addr=recipient.get("to"),
                        subject=f"Backup {title}: {schedule_name}",
                        body=plain_message,
                        attachment_path=attachment_path if should_attach else None,
                        attachment_filename=attachment_name,
                    )
                    if not response.get("success"):
                        logger.warning(
                            "Email notification failed schedule=%s to=%s error=%s",
                            schedule_name,
                            recipient.get("to"),
                            response.get("error"),
                        )
                    results["email"].append({"to": recipient.get("to"), **response})
            else:
                if self._should_notify_legacy(email_config, status):
                    to_addr = str(email_config.get("to") or "").strip()
                    should_attach = bool(attach_backup and status == "success" and attachment_path)
                    logger.info(
                        "Sending email notification schedule=%s status=%s to=%s",
                        schedule_name,
                        status,
                        to_addr,
                    )
                    response = await self._send_email(
                        to_addr=to_addr,
                        subject=f"Backup {title}: {schedule_name}",
                        body=plain_message,
                        attachment_path=attachment_path if should_attach else None,
                        attachment_filename=attachment_name,
                    )
                    if not response.get("success"):
                        logger.warning(
                            "Email notification failed schedule=%s to=%s error=%s",
                            schedule_name,
                            to_addr,
                            response.get("error"),
                        )
                    results["email"].append({"to": to_addr, **response})

        results["sent"] = any(
            item.get("success")
            for channel in ("telegram", "email")
            for item in results.get(channel, [])
            if isinstance(item, dict)
        )
        logger.info(
            "Notification results schedule=%s status=%s sent=%s telegram=%s email=%s",
            schedule_name,
            status,
            results.get("sent"),
            len(results.get("telegram") or []),
            len(results.get("email") or []),
        )
        return results

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
            logger.exception("Telegram send failed chat_id=%s", chat_id)
            return {"success": False, "error": str(e)}

    async def _send_telegram_document(
        self,
        *,
        chat_id: str,
        file_path: Path,
        filename: Optional[str],
        caption: Optional[str],
    ) -> Dict[str, Any]:
        """Send a Telegram document with an optional caption.

        Args:
            chat_id: Telegram chat ID.
            file_path: Path to the attachment.
            filename: Optional filename override.
            caption: Optional caption text (HTML supported).

        Returns:
            Dict[str, Any]: Send result.
        """

        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}

        if not chat_id:
            return {"success": False, "error": "Chat ID not provided"}

        if not file_path.exists():
            return {"success": False, "error": "Attachment not found"}

        try:
            import httpx

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendDocument"
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"

            with file_path.open("rb") as handle:
                files = {"document": (filename or file_path.name, handle)}
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=data, files=files, timeout=30.0)
                    payload = response.json()

            if payload.get("ok"):
                return {"success": True, "message_id": payload.get("result", {}).get("message_id")}
            return {"success": False, "error": payload.get("description", "Unknown error")}

        except Exception as exc:
            logger.exception("Telegram document send failed chat_id=%s", chat_id)
            return {"success": False, "error": str(exc)}

    async def _send_email(
        self,
        *,
        to_addr: str,
        subject: str,
        body: str,
        attachment_path: Optional[Path] = None,
        attachment_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email notification.
        
        Args:
            to_addr: Recipient email address.
            subject: Email subject.
            body: Email body text.
            attachment_path: Optional path to attach.
            attachment_filename: Optional attachment filename override.
        
        Returns:
            Dict with send result.
        """
        if not self.smtp_config:
            logger.warning("SMTP not configured; skipping email to=%s", to_addr)
            return {"success": False, "error": "SMTP not configured"}
        
        if not to_addr:
            logger.warning("Email recipient not provided; skipping send")
            return {"success": False, "error": "Recipient email not provided"}
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["from_addr"] or self.smtp_config["user"]
            msg["To"] = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            if attachment_path:
                try:
                    if attachment_path.exists():
                        filename = attachment_filename or attachment_path.name
                        with attachment_path.open("rb") as handle:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(handle.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
                        msg.attach(part)
                except Exception:
                    logger.exception("Failed to attach backup file to email")

            allow_insecure = bool(self.smtp_config.get("allow_insecure_certs"))
            ca_cert_file = str(self.smtp_config.get("ca_cert_file") or "").strip()
            if allow_insecure:
                logger.warning(
                    "SMTP_ALLOW_INSECURE_CERTS is enabled; TLS certificate verification is disabled for SMTP"
                )

            server = None
            try:
                if self.smtp_config.get("use_ssl"):
                    context = _build_smtp_ssl_context(allow_insecure=allow_insecure, ca_cert_file=ca_cert_file)
                    server = smtplib.SMTP_SSL(self.smtp_config["host"], self.smtp_config["port"], context=context)
                else:
                    server = smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"])
                    if self.smtp_config.get("use_tls"):
                        context = _build_smtp_ssl_context(allow_insecure=allow_insecure, ca_cert_file=ca_cert_file)
                        server.starttls(context=context)

                if self.smtp_config["user"] and self.smtp_config["password"]:
                    server.login(self.smtp_config["user"], self.smtp_config["password"])

                server.sendmail(msg["From"], to_addr, msg.as_string())
            finally:
                if server is not None:
                    try:
                        server.quit()
                    except Exception:
                        pass
            
            logger.info("Email sent successfully to=%s", to_addr)
            return {"success": True}
        
        except Exception as e:
            logger.exception(
                "SMTP send failed to=%s host=%s port=%s use_ssl=%s",
                to_addr,
                (self.smtp_config or {}).get("host"),
                (self.smtp_config or {}).get("port"),
                (self.smtp_config or {}).get("use_ssl"),
            )
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
