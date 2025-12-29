from flask import Flask, request, jsonify, make_response
import os
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# -------------------- CORS --------------------
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


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    response.headers.setdefault("Access-Control-Allow-Methods", "POST, OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    response.headers["Vary"] = "Origin"
    return response


# -------------------- EMAIL SENDER --------------------
def send_email(
    name: str,
    email: str,
    phone: str,
    message: str,
    source: str
):
    # Environment variables (Render Dashboard)
    GMAIL_USER = os.environ.get("GMAIL_USER")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
    STUDIO_EMAIL = os.environ.get("STUDIO_EMAIL", "vartisticstudio@gmail.com")

    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("Gmail credentials missing in environment variables")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)

        # -------- Mail to Studio --------
        studio_msg = EmailMessage()
        studio_msg["From"] = GMAIL_USER
        studio_msg["To"] = STUDIO_EMAIL

        if source == "contact":
            studio_msg["Subject"] = "🚀 New Contact Enquiry – Vartistic Studio"
            title = "Contact Page Submission"
        else:
            studio_msg["Subject"] = "🚀 New Website Enquiry – Vartistic Studio"
            title = "Website Enquiry"

        phone_display = phone if phone else "Not provided"

        studio_msg.set_content(
            f"{title}\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Phone: {phone_display}\n\n"
            f"Message:\n{message}"
        )

        smtp.send_message(studio_msg)

        # -------- Confirmation Mail to User --------
        if email:
            user_msg = EmailMessage()
            user_msg["From"] = GMAIL_USER
            user_msg["To"] = email
            user_msg["Subject"] = "Vartistic Studio — We received your enquiry"
            user_msg.set_content(
                f"Hi {name},\n\n"
                f"Thank you for contacting Vartistic Studio.\n"
                f"Our team will get back to you shortly.\n\n"
                f"— Vartistic Studio"
            )
            smtp.send_message(user_msg)


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

    # Validation
    if not name or not email or not message:
        resp = jsonify(success=False, error="Missing required fields")
        resp.status_code = 400
        return attach_cors(resp)

    try:
        # ✅ SEND EMAIL DIRECTLY (NO THREADING)
        send_email(name, email, phone, message, source)
    except Exception as e:
        print("❌ Email send error:", e)
        resp = jsonify(success=False, error="Email failed to send")
        resp.status_code = 500
        return attach_cors(resp)

    resp = jsonify(success=True)
    resp.status_code = 200
    return attach_cors(resp)


# -------------------- LOCAL / RENDER --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
