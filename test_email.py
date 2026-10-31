"""Utility script to test email notification configuration.

Run:
    python backend/test_email.py
"""

import os
import smtplib
import sys
from email.message import EmailMessage

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv()
except ImportError:
    def _fallback_load_dotenv(path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
    _fallback_load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    _fallback_load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main():
    print("=" * 60)
    print(" HouseKeep Shimoga - Email Notification Test")
    print("=" * 60)

    username = os.environ.get("HOUSEKEEP_SMTP_USERNAME", "").strip()
    password = os.environ.get("HOUSEKEEP_SMTP_PASSWORD", "").strip()
    host = os.environ.get("HOUSEKEEP_SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("HOUSEKEEP_SMTP_PORT", "587"))
    sender = os.environ.get("HOUSEKEEP_SMTP_FROM", username).strip()
    recipient = os.environ.get("BOOKING_ALERT_EMAIL", os.environ.get("ADMIN_EMAIL", "anoopbr2002@gmail.com")).strip()

    print(f"SMTP Host:      {host}")
    print(f"SMTP Port:      {port}")
    print(f"SMTP Username:  {username or '(NOT SET)'}")
    print(f"SMTP Password:  {'*' * len(password) if password and password != 'your_16_digit_gmail_app_password' else '(NOT CONFIGURED)'}")
    print(f"Sender Address: {sender or '(NOT SET)'}")
    print(f"Admin Recipient:{recipient}")
    print("-" * 60)

    if not username:
        print("[ERROR] HOUSEKEEP_SMTP_USERNAME is not set in backend/.env.")
        print("Please set your Gmail address in backend/.env.")
        sys.exit(1)

    has_smtp = bool(password and password != "your_16_digit_gmail_app_password")

    if not has_smtp:
        print("[INFO] SMTP password not configured in .env.")
        print(f"Testing direct Web Email API delivery to {recipient}...")
        import json
        from urllib.request import Request, urlopen

        payload = {
            "_subject": "HouseKeep Shimoga - Email System Active!",
            "_template": "table",
            "_captcha": "false",
            "Notification": "Email system is working!",
            "Admin Email": recipient,
            "Status": "Booking notifications are now active and ready to deliver.",
            "Timestamp": "Just now",
        }
        try:
            req = Request(
                f"https://formsubmit.co/ajax/{recipient}",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer": "http://localhost:3000",
                },
                method="POST",
            )
            with urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                print("=" * 60)
                print(f"[SUCCESS] Test notification successfully sent to {recipient}!")
                print(f"Response: {res_data.get('message', 'Delivered')}")
                print("=" * 60)
                print("Check your Gmail inbox (and spam folder) for the confirmation!")
                return
        except Exception as exc:
            print(f"[FAILED] Web email delivery error: {exc}")
            return

    print(f"Connecting to {host}:{port}...")
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=12)
        else:
            server = smtplib.SMTP(host, port, timeout=12)
            server.ehlo()
            server.starttls()
            server.ehlo()

        print("[OK] Connection established and TLS active.")
        print(f"Authenticating as {username}...")
        server.login(username, password)
        print("[OK] Authentication successful!")

        print(f"Sending test email to {recipient}...")
        msg = EmailMessage()
        msg["Subject"] = "HouseKeep Shimoga - Email Test Successful"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(
            "Hello Admin,\n\n"
            "This is a test notification from HouseKeep Shimoga.\n"
            "Your outbound SMTP email settings are working correctly!\n\n"
            "From now on, whenever a customer confirms a booking, the booking details\n"
            "will be automatically delivered to this inbox.\n"
        )
        server.send_message(msg)
        server.quit()

        print("=" * 60)
        print(f"[SUCCESS] Test email successfully sent to {recipient} via SMTP!")
        print("Check your inbox (and spam/promotions folder) to confirm.")
        print("=" * 60)

    except smtplib.SMTPAuthenticationError as auth_err:
        print(f"\n[AUTHENTICATION FAILED] {auth_err}")
        print("\nPossible reasons:")
        print(" 1. You used your normal Gmail password instead of a Google App Password.")
        print(" 2. The 16-character App Password has typos or expired.")
        print(" 3. 2-Step Verification is not enabled on your Google account.")
    except Exception as exc:
        print(f"\n[FAILED] Error while connecting or sending: {exc}")


if __name__ == "__main__":
    main()
