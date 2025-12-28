from flask import Flask, request, jsonify
import os
import smtplib
import threading
from email.message import EmailMessage

app = Flask(__name__)


# Optional: load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@app.after_request
def add_cors_headers(response):
    # Allow simple cross-origin testing from different ports (localhost)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response


@app.route('/send-mail', methods=['POST', 'OPTIONS'])
def send_mail():
    # Respond to CORS preflight immediately
    if request.method == 'OPTIONS':
        return jsonify(success=True), 200

    try:
        data = request.get_json(force=True)
    except Exception:
        data = {}

    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    message = (data.get('message') or '').strip()

    # Basic validation
    if not name or not email or not message:
        return jsonify(success=False, error='Missing required fields'), 400

    GMAIL_USER = os.environ.get('GMAIL_USER')
    GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return jsonify(success=False, error='Mail credentials not configured'), 500

    source = (data.get('source') or 'index').strip().lower()

    # Prepare payload for background sending. We avoid creating EmailMessage
    # objects here to keep the request lightweight; the worker will construct
    # the messages and perform SMTP actions.
    bg_args = {
        'name': name,
        'email': email,
        'phone': phone,
        'message': message,
        'source': source,
        'gmail_user': GMAIL_USER,
        'gmail_pass': GMAIL_APP_PASSWORD
    }

    def send_emails_worker(args):
        """Background worker to send emails. Runs in a separate daemon thread.

        We use a background thread to ensure the HTTP response is returned
        immediately to the client (Vercel may close the connection if the
        function runs too long). The worker logs any exceptions but does
        not affect the client response.
        """
        try:
            n = args['name']
            em = args['email']
            ph = args['phone']
            msg_text = args['message']
            src = args['source']
            user = args['gmail_user']
            pwd = args['gmail_pass']

            phone_display = ph if ph else 'Not provided'

            # Build studio message
            studio_msg = EmailMessage()
            studio_msg['From'] = user
            studio_msg['To'] = 'vartisticstudio@gmail.com'
            if src == 'contact':
                studio_msg['Subject'] = '🚀 New Contact Enquiry – Vartistic Studio'
                body_intro = 'Contact Page Submission'
            else:
                studio_msg['Subject'] = '🚀 New Website Enquiry – Vartistic Studio'
                body_intro = 'Website Enquiry'

            body = f"{body_intro}:\n\nName:\n{n}\n\nEmail:\n{em}\n\nPhone:\n{phone_display}\n\nMessage:\n{msg_text}\n"

            html_body = f"""
            <html>
                <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
                    <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(16,24,40,0.08);overflow:hidden;">
                          <div style="background:linear-gradient(90deg,#b8860b,#ffd700);padding:20px 24px;color:#fff;">
                            <h1 style="margin:0;font-size:18px;letter-spacing:0.2px">Vartistic Studio</h1>
                            <p style="margin:6px 0 0;font-size:13px;opacity:0.9">{body_intro}</p>
                        </div>
                        <div style="padding:24px;color:#0f172a;font-size:14px;line-height:1.5">
                            <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;margin-bottom:16px;">
                                <tr><td style="padding:6px 0;font-weight:600;width:110px;color:#111827">Name</td><td style="padding:6px 0;color:#374151">{n}</td></tr>
                                <tr><td style="padding:6px 0;font-weight:600;color:#111827">Email</td><td style="padding:6px 0;color:#374151">{em}</td></tr>
                                <tr><td style="padding:6px 0;font-weight:600;color:#111827">Phone</td><td style="padding:6px 0;color:#374151">{phone_display}</td></tr>
                            </table>

                            <div style="margin-top:8px;padding:16px;background:#f8fafc;border-radius:6px;color:#111827;white-space:pre-wrap">{msg_text}</div>
                        </div>
                        <div style="padding:16px 24px;background:#fcfcfd;border-top:1px solid #eef2f7;font-size:12px;color:#6b7280">
                            <div>— Vartistic Studio</div>
                            <div style="margin-top:6px;color:#9ca3af">Visit <a href="https://www.vartisticstudio.com" style="color:#b8860b;text-decoration:none">vartisticstudio.com</a></div>
                        </div>
                    </div>
                </body>
            </html>
            """

            studio_msg.set_content(body)
            studio_msg.add_alternative(html_body, subtype='html')

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(user, pwd)
                smtp.send_message(studio_msg)

                # Try sending confirmation to user (best-effort)
                if em:
                    try:
                        confirm = EmailMessage()
                        confirm['From'] = user
                        confirm['To'] = em
                        if src == 'contact':
                            confirm['Subject'] = "Vartistic Studio — We received your contact enquiry"
                            note = 'Thank you for contacting us via the Contact page.'
                        else:
                            confirm['Subject'] = "Vartistic Studio — We've received your enquiry"
                            note = 'Thank you for your website enquiry.'

                        confirm_body = (
                            f"Hi {n or ''},\n\n{note} Our team will connect with you shortly.\n\n"
                            f"Here is a copy of your submission:\n\nName:\n{n}\n\nEmail:\n{em}\n\n"
                            f"Phone:\n{phone_display}\n\nMessage:\n{msg_text}\n\n— Vartistic Studio"
                        )

                        confirm_html = f"""
                        <html>
                            <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
                                <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(16,24,40,0.06);overflow:hidden;">
                                      <div style="background:linear-gradient(90deg,#b8860b,#ffd700);padding:18px 22px;color:#fff;">
                                        <h2 style="margin:0;font-size:16px">Vartistic Studio</h2>
                                    </div>
                                    <div style="padding:20px;color:#0f172a;font-size:14px;line-height:1.5">
                                        <p style="margin:0 0 12px">Hi {n or ''},</p>
                                        <p style="margin:0 0 16px">{note} Our team will connect with you shortly.</p>
                                        <div style="background:#f8fafc;padding:14px;border-radius:6px;margin-bottom:12px;">
                                            <p style="margin:0 0 8px;font-weight:600">Your submission</p>
                                            <p style="margin:0"><strong>Name:</strong> {n}</p>
                                            <p style="margin:6px 0 0"><strong>Email:</strong> {em}</p>
                                            <p style="margin:6px 0 0"><strong>Phone:</strong> {phone_display}</p>
                                        </div>
                                        <div style="white-space:pre-wrap;color:#111827">{msg_text}</div>
                                    </div>
                                    <div style="padding:14px 20px;background:#fcfcfd;border-top:1px solid #eef2f7;font-size:12px;color:#6b7280">
                                        <div>— Vartistic Studio</div>
                                        <div style="margin-top:6px;color:#9ca3af">We typically reply within 1 business day.</div>
                                    </div>
                                </div>
                            </body>
                        </html>
                        """

                        confirm.set_content(confirm_body)
                        confirm.add_alternative(confirm_html, subtype='html')
                        smtp.send_message(confirm)
                    except Exception:
                        app.logger.exception('Failed to send confirmation email to user')

        except Exception:
            app.logger.exception('Failed to send email in background')

    # Start background thread to send emails and return immediately.
    t = threading.Thread(target=send_emails_worker, args=(bg_args,))
    t.daemon = True
    t.start()

    # Respond immediately - the email sending happens asynchronously.
    return jsonify(success=True), 200


if __name__ == '__main__':
    # Run in production via a proper WSGI server. This is for local/dev usage.
    app.run(host='0.0.0.0', port=5000)
