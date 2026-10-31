# HouseKeep Shimoga

A responsive home-services booking website for Shimoga, Karnataka. The frontend is a React/Vite single-page app and the REST API is a Flask service backed by a JSON file.

## Run locally

### API

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

The API listens on `http://localhost:5000` and stores bookings, reviews, and contact messages in `backend/housekeep.json`. Set `HOUSEKEEP_JSON` to use a different JSON file. If `backend/housekeep.json` does not exist but the old `backend/housekeep.sqlite3` does, the API imports its records into the JSON file on startup; the SQLite file is left unchanged.

Set `HOUSEKEEP_ADMIN_TOKEN` in the API environment before starting it. This token is required to mark a booking completed; keep it private and send it as the `X-Admin-Token` header from a trusted admin tool.

New bookings automatically send an alert email to the admin (`anoopbr2002@gmail.com`) when outbound SMTP is configured. 

#### Email Notification Setup (Gmail SMTP)
1. In `backend/`, copy `.env.example` to `.env` (or edit the existing `backend/.env`).
2. Generate a 16-character Google App Password:
   - Go to your Google Account -> **Security** -> turn ON **2-Step Verification**.
   - Go to **App Passwords** (`https://myaccount.google.com/apppasswords`).
   - Create an app password named **HouseKeep**.
3. In `backend/.env`, set:
   ```env
   HOUSEKEEP_SMTP_USERNAME=anoopbr2002@gmail.com
   HOUSEKEEP_SMTP_PASSWORD=your_16_digit_app_password
   BOOKING_ALERT_EMAIL=anoopbr2002@gmail.com
   ```
4. Test the email setup immediately from the terminal:
   ```powershell
   python backend/test_email.py
   ```
   If successful, you will receive a test email in your inbox right away!

### Frontend

From the project root:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend uses `http://localhost:5000` by default; set `VITE_API_BASE_URL` before starting Vite to point it at another API URL.

## API

- `GET /api/services` — list services as a JSON array with `id`, `name`, `icon`, `price`, `unit`, `category`, and `description`; optionally filter with `?category=cleaning`, `shifting`, `repairs`, or `other`.
- `POST /api/book` — validate and save a booking, then attempt configured email and SMS notifications.
- `GET /api/bookings` — list bookings.
- `PUT /api/bookings/<id>/status` — update to `pending`, `confirmed`, `completed`, or `cancelled`; completing a booking requires the admin token.
- `GET /api/reviews` — list customer feedback shared for completed bookings.
- `POST /api/reviews` — submit feedback using a completed booking reference and its booking phone number.
- `POST /api/contact` — save a contact message.

The API allows cross-origin requests from `http://localhost:3000` and `http://localhost:3001`.
