import base64
import json
import os
import re
import sqlite3
import smtplib
import tempfile
from datetime import date, datetime, timezone
from email.message import EmailMessage
from threading import RLock
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request
from flask_cors import CORS

# Load environment variables from .env file (if present)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv()
except ImportError:
    # Lightweight fallback parser if python-dotenv is not installed
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


SERVICES = [
    {"id": 1, "name": "Full Home Deep Cleaning", "icon": "🏠", "price": 1499, "unit": "starting", "category": "cleaning", "description": "Complete deep cleaning of bedrooms, hall, kitchen & bathrooms with professional equipment."},
    {"id": 2, "name": "Bathroom Cleaning", "icon": "🚿", "price": 199, "unit": "starting", "category": "cleaning", "description": "Tile scrubbing, stain removal, sanitisation of toilets, sinks and fittings."},
    {"id": 3, "name": "Kitchen Cleaning", "icon": "🍳", "price": 399, "unit": "starting", "category": "cleaning", "description": "Make your counters, cabinets and cooking space shine again."},
    {"id": 4, "name": "Sofa & Carpet Cleaning", "icon": "🛋️", "price": 299, "unit": "starting", "category": "cleaning", "description": "Lift dust and stains from your favorite soft furnishings."},
    # {"id": 5, "name": "House Shifting (Local)", "icon": "📦", "price": 1999, "unit": "starting", "category": "shifting", "description": "A smooth, careful move to your new home in Shimoga."},
    # {"id": 6, "name": "Packing Services Only", "icon": "🎁", "price": 799, "unit": "starting", "category": "shifting", "description": "Professionally packed belongings, ready for your move."},
    # {"id": 7, "name": "Plumbing Repairs", "icon": "🚰", "price": 149, "unit": "starting", "category": "repairs", "description": "Leaky taps, clogged drains and plumbing fixes handled."},
    # {"id": 8, "name": "Electrician Services", "icon": "💡", "price": 149, "unit": "starting", "category": "repairs", "description": "Safe help with switches, fans, wiring and electrical faults."},
    # {"id": 9, "name": "Carpenter Services", "icon": "🪚", "price": 199, "unit": "starting", "category": "repairs", "description": "Furniture fixes and fittings from a skilled local carpenter."},
    # {"id": 10, "name": "Appliance Repair", "icon": "🔧", "price": 249, "unit": "starting", "category": "repairs", "description": "Get everyday home appliances checked and working again."},
    # {"id": 11, "name": "Home Painting", "icon": "🎨", "price": 999, "unit": "starting", "category": "other", "description": "Freshen up your walls with tidy, professional painting."},
    # {"id": 12, "name": "Pest Control", "icon": "🐜", "price": 799, "unit": "starting", "category": "other", "description": "Targeted treatments to help keep unwanted pests away."},
    # {"id": 13, "name": "Cook & Maid Services", "icon": "👩‍🍳", "price": 299, "unit": "day", "category": "other", "description": "Find dependable daily help for cooking and household tasks."},
    # {"id": 14, "name": "Gardening & Plants", "icon": "🪴", "price": 299, "unit": "starting", "category": "other", "description": "Give your garden and indoor plants the care they deserve."},
]

REQUIRED_BOOKING_FIELDS = (
    "name",
    "phone",
    "address",
    "preferred_date",
    "time_slot",
)
VALID_STATUSES = {"pending", "confirmed", "completed", "cancelled"}
BOOKING_ALERT_EMAIL = os.environ.get(
    "BOOKING_ALERT_EMAIL",
    os.environ.get("ADMIN_EMAIL", "anoopbr2002@gmail.com"),
)
BOOKING_ALERT_PHONE = os.environ.get(
    "BOOKING_ALERT_PHONE",
    os.environ.get("ADMIN_PHONE", "+918867572830"),
)
STORE_LOCK = RLock()


app = Flask(__name__)
app.config["JSON_STORE"] = os.environ.get(
    "HOUSEKEEP_JSON",
    os.path.join(os.path.dirname(__file__), "housekeep.json"),
)
app.config["LEGACY_DATABASE"] = os.environ.get(
    "HOUSEKEEP_DATABASE",
    os.path.join(os.path.dirname(__file__), "housekeep.sqlite3"),
)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001"]
        }
    },
)


def read_legacy_database(path):
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        bookings = [dict(row) for row in connection.execute("SELECT * FROM bookings")]
        messages = [
            dict(row) for row in connection.execute("SELECT * FROM contact_messages")
        ]
    finally:
        connection.close()

    return {
        "bookings": bookings,
        "contact_messages": messages,
        "next_ids": {
            "bookings": max((row["id"] for row in bookings), default=0) + 1,
            "contact_messages": max((row["id"] for row in messages), default=0) + 1,
        },
    }


def save_store(store):
    path = app.config["JSON_STORE"]
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(store, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def load_store():
    with open(app.config["JSON_STORE"], encoding="utf-8") as store_file:
        return json.load(store_file)


def init_store():
    path = app.config["JSON_STORE"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if os.path.exists(path):
        load_store()
        return

    legacy_path = app.config["LEGACY_DATABASE"]
    if os.path.exists(legacy_path):
        store = read_legacy_database(legacy_path)
    else:
        store = {
            "bookings": [],
            "contact_messages": [],
            "next_ids": {"bookings": 1, "contact_messages": 1},
        }
    save_store(store)


init_store()


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def clean_text(data, field):
    value = data.get(field, "")
    return value.strip() if isinstance(value, str) else ""


def valid_phone(phone):
    return bool(re.fullmatch(r"\d{10}", phone))


def send_email_via_formsubmit(booking, booking_id):
    """Deliver booking notification directly to admin email via FormSubmit Web API (no password needed)."""
    recipient = BOOKING_ALERT_EMAIL
    endpoint = f"https://formsubmit.co/ajax/{recipient}"
    payload = {
        "_subject": f"New HouseKeep Booking #{booking_id} - {booking.get('service_name', 'Service')}",
        "_template": "table",
        "_captcha": "false",
        "Booking ID": f"#{booking_id}",
        "Customer Name": booking.get("name"),
        "Phone Number": booking.get("phone"),
        "Customer Email": booking.get("email") or "Not provided",
        "Service": booking.get("service_name"),
        "Service Date": booking.get("preferred_date"),
        "Time Slot": booking.get("time_slot"),
        "Address in Shimoga": booking.get("address"),
        "Special Instructions": booking.get("instructions") or "None",
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            endpoint,
            data=data,
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
            app.logger.info(
                "[EMAIL ALERT] Direct web notification response for booking #%s: %s",
                booking_id,
                res_data.get("message", "Sent"),
            )
            return True
    except Exception as exc:
        app.logger.error("[EMAIL ALERT] Direct web email delivery failed: %s", exc)
        return False


def send_booking_email(booking, booking_id):
    username = os.environ.get("HOUSEKEEP_SMTP_USERNAME")
    password = os.environ.get("HOUSEKEEP_SMTP_PASSWORD")
    host = os.environ.get("HOUSEKEEP_SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("HOUSEKEEP_SMTP_PORT", "587"))

    has_valid_smtp = bool(
        username
        and password
        and password != "your_16_digit_gmail_app_password"
    )

    if has_valid_smtp:
        sender = os.environ.get("HOUSEKEEP_SMTP_FROM", username)
        recipient = BOOKING_ALERT_EMAIL

        try:
            message = EmailMessage()
            message["Subject"] = f"New HouseKeep Booking #{booking_id} - {booking.get('service_name', 'Service')}"
            message["From"] = sender
            message["To"] = recipient

            # Plain-text version
            plain_text = (
                f"=== NEW BOOKING RECEIVED ===\n\n"
                f"Booking Reference: #{booking_id}\n"
                f"Customer Name: {booking.get('name')}\n"
                f"Phone: {booking.get('phone')}\n"
                f"Email: {booking.get('email') or 'Not provided'}\n"
                f"Service: {booking.get('service_name')}\n"
                f"Address: {booking.get('address')}\n"
                f"Preferred Date: {booking.get('preferred_date')}\n"
                f"Time Slot: {booking.get('time_slot')}\n"
                f"Special Instructions: {booking.get('instructions') or 'None'}\n\n"
                f"Please call the customer to confirm the appointment."
            )
            message.set_content(plain_text)

            # HTML formatted version
            html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b; margin: 0; padding: 20px; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
    .header {{ background: #16a34a; color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0 0; opacity: 0.9; font-size: 14px; }}
    .body {{ padding: 24px; }}
    .section-title {{ font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
    td.label {{ font-weight: 600; color: #475569; width: 38%; }}
    td.value {{ color: #0f172a; }}
    .badge {{ display: inline-block; background: #dcfce7; color: #15803d; font-weight: 700; padding: 4px 10px; border-radius: 9999px; font-size: 13px; }}
    .action-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; font-size: 14px; color: #334155; }}
    .action-box a {{ color: #16a34a; font-weight: 700; text-decoration: none; }}
    .footer {{ background: #f8fafc; text-align: center; padding: 16px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>New Booking Received</h1>
      <p>Reference <span class="badge">#{booking_id}</span></p>
    </div>
    <div class="body">
      <div class="section-title">Customer & Service Details</div>
      <table>
        <tr><td class="label">Customer Name</td><td class="value"><strong>{booking.get('name')}</strong></td></tr>
        <tr><td class="label">Phone Number</td><td class="value"><a href="tel:{booking.get('phone')}" style="color: #16a34a; font-weight: 600;">{booking.get('phone')}</a></td></tr>
        <tr><td class="label">Customer Email</td><td class="value">{booking.get('email') or '<em>Not provided</em>'}</td></tr>
        <tr><td class="label">Service</td><td class="value"><strong>{booking.get('service_name')}</strong></td></tr>
        <tr><td class="label">Preferred Date</td><td class="value">{booking.get('preferred_date')}</td></tr>
        <tr><td class="label">Time Slot</td><td class="value">{booking.get('time_slot')}</td></tr>
        <tr><td class="label">Address in Shimoga</td><td class="value">{booking.get('address')}</td></tr>
        <tr><td class="label">Special Instructions</td><td class="value">{booking.get('instructions') or '<em>None</em>'}</td></tr>
      </table>
      <div class="action-box">
        📞 Call customer at <a href="tel:{booking.get('phone')}">{booking.get('phone')}</a> to confirm this appointment.
      </div>
    </div>
    <div class="footer">
      HouseKeep Shimoga Notification System · Admin Alert
    </div>
  </div>
</body>
</html>"""
            message.add_alternative(html_content, subtype="html")

            app.logger.info(
                "[EMAIL ALERT] Connecting to SMTP server %s:%d to send booking #%s alert...",
                host,
                port,
                booking_id,
            )

            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=12) as smtp:
                    smtp.login(username, password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(host, port, timeout=12) as smtp:
                    smtp.starttls()
                    smtp.login(username, password)
                    smtp.send_message(message)

            app.logger.info(
                "[EMAIL ALERT] Successfully sent booking #%s email alert to %s via SMTP",
                booking_id,
                recipient,
            )
            return True
        except Exception as exc:
            app.logger.error(
                "[EMAIL ALERT] SMTP delivery failed (%s), falling back to Web API...",
                exc,
            )

    # Automatic fallback: Deliver directly to admin email via Web Email API
    app.logger.info(
        "[EMAIL ALERT] Forwarding booking #%s notification directly to %s via Web Email Service...",
        booking_id,
        BOOKING_ALERT_EMAIL,
    )
    return send_email_via_formsubmit(booking, booking_id)


def send_booking_sms(booking, booking_id):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not account_sid or not auth_token or not from_number:
        return False

    body = (
        f"New HouseKeep booking #{booking_id}: {booking['name']}, "
        f"{booking['service_name']}, {booking['preferred_date']} "
        f"{booking['time_slot']}. Customer phone: {booking['phone']}."
    )
    try:
        request = Request(
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{account_sid}/Messages.json",
            data=urlencode(
                {"To": BOOKING_ALERT_PHONE, "From": from_number, "Body": body}
            ).encode(),
            headers={
                "Authorization": "Basic "
                + base64.b64encode(
                    f"{account_sid}:{auth_token}".encode()
                ).decode(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except Exception:
        app.logger.exception("Booking SMS notification failed")
        return False


def send_booking_notifications(booking, booking_id):
    return {
        "email": send_booking_email(booking, booking_id),
        "sms": send_booking_sms(booking, booking_id),
    }


@app.get("/api/services")
def list_services():
    category = request.args.get("category")
    if category:
        return jsonify([service for service in SERVICES if service["category"] == category])
    return jsonify(SERVICES)


@app.post("/api/book")
def create_booking():
    data = json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400

    missing = [field for field in REQUIRED_BOOKING_FIELDS if not clean_text(data, field)]
    if missing:
        return jsonify({"error": f"Please provide all required fields: {', '.join(missing)}."}), 400

    phone = clean_text(data, "phone")
    if not valid_phone(phone):
        return jsonify({"error": "Phone number must contain exactly 10 digits."}), 400

    email = clean_text(data, "email")
    if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
        return jsonify({"error": "Please provide a valid email address."}), 400

    try:
        service_id = int(data.get("service_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please select a valid service."}), 400
    service = next((item for item in SERVICES if item["id"] == service_id), None)
    if service is None:
        return jsonify({"error": "Please select a valid service."}), 400

    try:
        service_date = date.fromisoformat(clean_text(data, "preferred_date"))
    except ValueError:
        return jsonify({"error": "Please provide a valid service date."}), 400
    if service_date < date.today():
        return jsonify({"error": "Service date cannot be in the past."}), 400

    time_slot = clean_text(data, "time_slot")
    if time_slot not in {
        "8:00 AM – 10:00 AM",
        "10:00 AM – 12:00 PM",
        "12:00 PM – 2:00 PM",
        "2:00 PM – 4:00 PM",
        "4:00 PM – 6:00 PM",
        "6:00 PM – 8:00 PM",
    }:
        return jsonify({"error": "Please select a valid time slot."}), 400

    booking = {
        "name": clean_text(data, "name"),
        "phone": phone,
        "email": email or None,
        "service_id": service_id,
        "address": clean_text(data, "address"),
        "preferred_date": service_date.isoformat(),
        "time_slot": time_slot,
        "instructions": clean_text(data, "instructions"),
    }
    with STORE_LOCK:
        store = load_store()
        booking_id = store["next_ids"]["bookings"]
        store["bookings"].append(
            {
                **booking,
                "id": booking_id,
                "service_name": service["name"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
        store["next_ids"]["bookings"] += 1
        save_store(store)

    notifications = send_booking_notifications(
        {**booking, "service_name": service["name"]}, booking_id
    )
    return jsonify(
        {
            "message": "Booking received. Our HouseKeep team will call you shortly.",
            "booking_id": booking_id,
            "status": "pending",
            "notifications": notifications,
        }
    ), 201


@app.get("/api/bookings")
def list_bookings():
    with STORE_LOCK:
        bookings = load_store()["bookings"]
    return jsonify(
        sorted(
            bookings,
            key=lambda row: (row["created_at"], row["id"]),
            reverse=True,
        )
    )


@app.put("/api/bookings/<int:booking_id>/status")
def update_booking_status(booking_id):
    data = json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400
    status = clean_text(data, "status").lower()
    if status not in VALID_STATUSES:
        return jsonify({"error": "Status must be pending, confirmed, completed, or cancelled."}), 400
    if status == "completed":
        admin_token = os.environ.get("HOUSEKEEP_ADMIN_TOKEN")
        if not admin_token:
            return jsonify(
                {"error": "Completion updates are not configured."}
            ), 503
        if request.headers.get("X-Admin-Token") != admin_token:
            return jsonify(
                {
                    "error": "Only an authorized administrator "
                    "can complete bookings."
                }
            ), 403

    with STORE_LOCK:
        store = load_store()
        booking = next(
            (row for row in store["bookings"] if row["id"] == booking_id), None
        )
        if booking is None:
            return jsonify({"error": "Booking not found."}), 404
        booking["status"] = status
        save_store(store)
    return jsonify(
        {"message": "Booking status updated.", "booking_id": booking_id, "status": status}
    )


@app.get("/api/reviews")
def list_reviews():
    with STORE_LOCK:
        reviews = load_store().get("reviews", [])
    public_reviews = [
        {
            "id": review["id"],
            "name": review["name"],
            "service_name": review["service_name"],
            "comment": review["comment"],
            "created_at": review["created_at"],
        }
        for review in reviews
    ]
    return jsonify(
        sorted(
            public_reviews,
            key=lambda review: review["created_at"],
            reverse=True,
        )
    )


@app.post("/api/reviews")
def create_review():
    data = json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        booking_id = int(data.get("booking_id"))
    except (TypeError, ValueError):
        return jsonify(
            {"error": "Please provide a valid booking reference."}
        ), 400

    phone = clean_text(data, "phone")
    comment = clean_text(data, "comment")
    if not valid_phone(phone):
        return jsonify(
            {"error": "Phone number must contain exactly 10 digits."}
        ), 400
    if not comment or len(comment) > 1000:
        return jsonify(
            {"error": "Feedback must be between 1 and 1000 characters."}
        ), 400
    if data.get("consent") is not True:
        return jsonify(
            {"error": "Please agree before publishing your feedback."}
        ), 400

    with STORE_LOCK:
        store = load_store()
        booking = next(
            (row for row in store["bookings"] if row["id"] == booking_id), None
        )
        if booking is None or booking["phone"] != phone:
            return jsonify(
                {"error": "We couldn’t verify that booking and phone number."}
            ), 404
        if booking["status"] != "completed":
            return jsonify(
                {
                    "error": "You can leave feedback after the service is "
                    "marked complete."
                }
            ), 400

        store.setdefault("reviews", [])
        if any(
            review["booking_id"] == booking_id for review in store["reviews"]
        ):
            return jsonify(
                {
                    "error": "Feedback has already been submitted "
                    "for this booking."
                }
            ), 409

        next_ids = store.setdefault("next_ids", {})
        review_id = next_ids.setdefault("reviews", 1)
        review = {
            "id": review_id,
            "booking_id": booking_id,
            "name": booking["name"].split()[0],
            "service_name": booking["service_name"],
            "comment": comment,
            "created_at": (
                datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            ),
        }
        store["reviews"].append(review)
        next_ids["reviews"] += 1
        save_store(store)

    return jsonify({"message": "Feedback received.", "review": review}), 201


@app.post("/api/contact")
def create_contact_message():
    data = json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400
    name = clean_text(data, "name")
    phone = clean_text(data, "phone")
    email = clean_text(data, "email")
    message = clean_text(data, "message")
    if not name or not phone or not message:
        return jsonify({"error": "Name, phone, and message are required."}), 400
    if not valid_phone(phone):
        return jsonify({"error": "Phone number must contain exactly 10 digits."}), 400
    if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
        return jsonify({"error": "Please provide a valid email address."}), 400

    with STORE_LOCK:
        store = load_store()
        message_id = store["next_ids"]["contact_messages"]
        store["contact_messages"].append(
            {
                "id": message_id,
                "name": name,
                "phone": phone,
                "email": email or None,
                "message": message,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
        store["next_ids"]["contact_messages"] += 1
        save_store(store)
    return jsonify(
        {"message": "Your message has been received.", "message_id": message_id}
    ), 201


@app.get("/api/notification-status")
def notification_status():
    username = os.environ.get("HOUSEKEEP_SMTP_USERNAME")
    raw_password = os.environ.get("HOUSEKEEP_SMTP_PASSWORD", "").strip()
    is_password_valid = bool(raw_password and raw_password != "your_16_digit_gmail_app_password")
    host = os.environ.get("HOUSEKEEP_SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("HOUSEKEEP_SMTP_PORT", "587"))
    return jsonify(
        {
            "admin_email": BOOKING_ALERT_EMAIL,
            "admin_phone": BOOKING_ALERT_PHONE,
            "email_configured": True,
            "email_channel": "smtp" if (username and is_password_valid) else "web_api",
            "smtp_host": host,
            "smtp_port": port,
            "smtp_username": username or None,
            "sms_configured": bool(
                os.environ.get("TWILIO_ACCOUNT_SID")
                and os.environ.get("TWILIO_AUTH_TOKEN")
                and os.environ.get("TWILIO_FROM_NUMBER")
            ),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
