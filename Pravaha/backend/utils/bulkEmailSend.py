import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import uuid
from typing import List, Dict, Any

class BulkEmailSender:
    def __init__(self, smtp_server, smtp_port, smtp_user, smtp_password, from_email):
        """
        Initialize the BulkEmailSender with SMTP server details, login credentials, and the sender's email.
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.smtp = None
    
    def connect(self):
        """
        Connect to the SMTP server and authenticate.
        """
        self.smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
        self.smtp.starttls()  # Start TLS encryption
        self.smtp.login(self.smtp_user, self.smtp_password)
    
    def disconnect(self):
        """
        Close the SMTP connection.
        """
        if self.smtp:
            self.smtp.quit()
    
    def send_email(self, to_email, subject, body):
        """
        Send an email to a specified address.
        """
        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Attach the email body (plain text)
        msg.attach(MIMEText(body, "plain"))
        
        # Send the email
        self.smtp.sendmail(self.from_email, to_email, msg.as_string())
    
    def send_bulk_emails(self, email_list: List[str], subject: str, template: str, delay: int = 1) -> List[Dict[str, Any]]:
        """
        Send bulk emails with a given subject and template to a list of email addresses.
        """
        results: List[Dict[str, Any]] = []
        self.connect()

        try:
            for raw_email in email_list:
                email = raw_email.strip()
                personalized_body = template.format(name=email.split("@")[0], id=uuid.uuid4())

                try:
                    self.send_email(email, subject, personalized_body)
                    results.append({"recipient": email, "status": "sent"})
                except Exception as exc:
                    results.append({"recipient": email, "status": "failed", "error": str(exc)})

                time.sleep(delay)
        finally:
            self.disconnect()

        return results
