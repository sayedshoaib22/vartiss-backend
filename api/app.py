from flask import Flask, request, jsonify, make_response
import os
import smtplib
import threading
from email.message import EmailMessage

app = Flask(__name__)

# Load .env locally if available (Vercel ignores .env and uses dashboard vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# -------------------- CORS (Vercel-safe) --------------------
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        origin = request.headers.get("Origin")
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"] = "3600"
        resp.headers["Vary"] = "Origin"
        return resp


def attach_cors(resp):
    origin = request.headers.get("Origin")
    resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    resp.headers["Vary"] = "Origin"
    return resp


# -------------------- ASYNC EMAIL WORKER --------------------
def send_email_async(
    name,
    email,
    phone,
    message,
    source
):
    try:
        GMAIL_USER = os.environ.get("GMAIL_USER")
        GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            print("❌ Gmail credentials missing")
            return

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)

            # -------- Email to Studio --------
            msg = EmailMessage()
            msg["From"] = GMAIL_USER
            msg["To"] = "vartisticstudio@gmail.com"

            if source == "contact":
                msg["Subject"] = "🚀 New Contact Enquiry – Vartistic Studio"
                title = "Contact Page Submission"
            else:
                msg["Subject"] = "🚀 New Website Enquiry – Vartistic Studio"
                title = "Website Enquiry"

            phone_display = phone if phone else "Not provided"

            msg.set_content(
                f"{title}\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Phone: {phone_display}\n\n"
                f"Message:\n{message}"
            )

            smtp.send_message(msg)

            # -------- Confirmation to User --------
            if email:
                confirm = EmailMessage()
                confirm["From"] = GMAIL_USER
                confirm["To"] = email
                confirm["Subject"] = "Vartistic Studio — We received your enquiry"
                confirm.set_content(
                    f"Hi {name},\n\n"
                    f"Thank you for contacting Vartistic Studio.\n"
                    f"Our team will reach out to you shortly.\n\n"
                    f"— Vartistic Studio"
                )
                smtp.send_message(confirm)

        print("✅ Email sent successfully (async)")

    except Exception as e:
        print("❌ Async email error:", e)


# -------------------- API ROUTE --------------------
@app.route("/send-mail", methods=["POST", "OPTIONS"])
def send_mail():
    try:
        data = request.get_json(force=True)
    except Exception:
        data = {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()
    source = (data.get("source") or "index").strip().lower()

    # Basic validation
    if not name or not email or not message:
        resp = jsonify(success=False, error="Missing required fields")
        resp.status_code = 400
        return attach_cors(resp)

    # 🔥 START BACKGROUND EMAIL (NON-BLOCKING)
    threading.Thread(
        target=send_email_async,
        args=(name, email, phone, message, source),
        daemon=True
    ).start()

    # ✅ IMMEDIATE RESPONSE (THIS FIXES NETWORK ERROR)
    resp = jsonify(success=True)
    resp.status_code = 200
    return attach_cors(resp)


# -------------------- LOCAL DEV ONLY --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
