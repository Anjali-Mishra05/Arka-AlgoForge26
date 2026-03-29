import os
from typing import List

from utils.bulkEmailSend import BulkEmailSender
from utils.database import APP_DB_NAME, Database
from utils.hubspot import sync_bulk_email_to_crm


DEFAULT_EMAIL_TEMPLATE = """Hi {name},

We hope this message finds you well.

You can continue the conversation here:
{app_url}/chat

Best regards,
Pravaha Team
"""


def _build_email_sender() -> BulkEmailSender:
    return BulkEmailSender(
        smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS"),
        from_email=os.getenv("SMTP_FROM_EMAIL") or os.getenv("FROM_EMAIL") or os.getenv("SMTP_USERNAME"),
    )


def send_mails(subject: str, body: str | None, mail_list: List[str], sent_by: str | None = None):
    app_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    template = (body or DEFAULT_EMAIL_TEMPLATE).replace("{app_url}", app_url)

    sender = _build_email_sender()
    results = sender.send_bulk_emails(mail_list, subject, template, delay=0)

    successful = sum(1 for result in results if result["status"] == "sent")
    failed = len(results) - successful

    campaign_id = None
    crm_sync = {"status": "skipped", "reason": "CRM sync not attempted"}

    # Log campaign to MongoDB for cross-channel intelligence
    try:
        db = Database(APP_DB_NAME)
        campaign_id = db.save_email_campaign(
            subject=subject,
            body=template,
            recipients=mail_list,
            sent_count=successful,
            failed_count=failed,
            results=results,
            sent_by=sent_by,
        )
        try:
            crm_sync = sync_bulk_email_to_crm(sent_by, subject, template, mail_list, results)
        except Exception:
            crm_sync = {"status": "error", "reason": "CRM sync failed"}
    except Exception:
        pass  # Don't fail the send if logging fails

    return {
        "total_sent": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
        "campaign_id": campaign_id,
        "crm_sync": crm_sync,
    }
