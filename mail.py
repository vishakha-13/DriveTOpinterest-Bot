import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))  # ← DEFAULT FIX
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_test_email():
    """Send a test email via Mailjet to verify credentials."""
    try:
        # Create MIME message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = "Mailjet Test Email from DrivePinterestUploader"
        
        body = (
            "This is a test email sent via Mailjet SMTP integration.\n\n"
            "If you're seeing this, your Mailjet credentials are working correctly!"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Connect to Mailjet SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())

        print("✅ Test email sent successfully via Mailjet!")

    except Exception as e:
        print("❌ Email test failed:", e)


def send_email_notification(subject, body):
    """Send a notification email via Mailjet with proper UTF-8 encoding."""
    try:
        # Create MIME message with UTF-8 encoding
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = subject
        
        # Attach body with UTF-8 encoding to support emojis
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # Connect to Mailjet SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())
        
        print("📧 Notification email sent successfully!")
        
    except Exception as e:
        print("❌ Failed to send notification email:", e)


if __name__ == "__main__":
    send_test_email()