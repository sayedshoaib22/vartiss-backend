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


# -------------------- EMAIL SENDER (DUAL SMTP) --------------------
def send_email(name, email, phone, message, source):
    # ---------- SMTP 1 (PRIMARY - EXE / MAIN) ----------
    SMTP1_USER = os.environ.get("GMAIL_USER")
    SMTP1_PASS = os.environ.get("GMAIL_APP_PASSWORD")

    # ---------- SMTP 2 (BACKUP - SERVER / CODE) ----------
    SMTP2_USER = os.environ.get("vartisticstudio@gmail.com")
    SMTP2_PASS = os.environ.get("mdaa ypie qgrl bkhl")

    STUDIO_EMAIL = os.environ.get("STUDIO_EMAIL", "vartisticstudio@gmail.com")

    if not SMTP1_USER or not SMTP1_PASS:
        raise RuntimeError("Primary SMTP credentials missing")

    phone_display = phone if phone else "Not provided"

    def build_messages(sender_email):
        # Mail to Studio
        studio_msg = EmailMessage()
        studio_msg["From"] = sender_email
        studio_msg["To"] = STUDIO_EMAIL

        if source == "contact":
            studio_msg["Subject"] = "🚀 New Contact Enquiry – Vartistic Studio"
            title = "Contact Page Submission"
        else:
            studio_msg["Subject"] = "🚀 New Website Enquiry – Vartistic Studio"
            title = "Website Enquiry"

        studio_msg.set_content(
            f"{title}\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Phone: {phone_display}\n\n"
            f"Message:\n{message}"
        )

        # Confirmation mail to user
        user_msg = None
        if email:
            user_msg = EmailMessage()
            user_msg["From"] = sender_email
            user_msg["To"] = email
            user_msg["Subject"] = "Vartistic Studio — We received your enquiry"
            user_msg.set_content(
                f"Hi {name},\n\n"
                f"Thank you for contacting Vartistic Studio.\n"
                f"Our team will get back to you shortly.\n\n"
                f"— Vartistic Studio"
            )

        return studio_msg, user_msg

    # ---------- TRY PRIMARY SMTP ----------
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP1_USER, SMTP1_PASS)

            studio_msg, user_msg = build_messages(SMTP1_USER)
            smtp.send_message(studio_msg)
            if user_msg:
                smtp.send_message(user_msg)

            print("✅ Email sent using PRIMARY SMTP")
            return

    except Exception as e1:
        print("⚠️ Primary SMTP failed:", e1)

    # ---------- TRY BACKUP SMTP ----------
    if SMTP2_USER and SMTP2_PASS:
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(SMTP2_USER, SMTP2_PASS)

                studio_msg, user_msg = build_messages(SMTP2_USER)
                smtp.send_message(studio_msg)
                if user_msg:
                    smtp.send_message(user_msg)

                print("✅ Email sent using BACKUP SMTP")
                return

        except Exception as e2:
            print("❌ Backup SMTP failed:", e2)

    raise RuntimeError("Both SMTP providers failed")


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
