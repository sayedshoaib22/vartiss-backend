from flask import Flask, request, jsonify
import os
import requests

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

    source = (data.get('source') or 'index').strip().lower()

    # Use the same body content as before for Brevo payload
    phone_display = phone if phone else 'Not provided'

    # Plain-text body
    body_intro = 'Website Enquiry'
    body = f"{body_intro}:\n\nName:\n{name}\n\nEmail:\n{email}\n\nPhone:\n{phone_display}\n\nMessage:\n{message}\n"

    # HTML body for better email UI (kept from previous template)
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
                        <tr><td style="padding:6px 0;font-weight:600;width:110px;color:#111827">Name</td><td style="padding:6px 0;color:#374151">{name}</td></tr>
                        <tr><td style="padding:6px 0;font-weight:600;color:#111827">Email</td><td style="padding:6px 0;color:#374151">{email}</td></tr>
                        <tr><td style="padding:6px 0;font-weight:600;color:#111827">Phone</td><td style="padding:6px 0;color:#374151">{phone_display}</td></tr>
                    </table>

                    <div style="margin-top:8px;padding:16px;background:#f8fafc;border-radius:6px;color:#111827;white-space:pre-wrap">{message}</div>
                </div>
                <div style="padding:16px 24px;background:#fcfcfd;border-top:1px solid #eef2f7;font-size:12px;color:#6b7280">
                    <div>— Vartistic Studio</div>
                    <div style="margin-top:6px;color:#9ca3af">Visit <a href="https://www.vartisticstudio.com" style="color:#b8860b;text-decoration:none">vartisticstudio.com</a></div>
                </div>
            </div>
        </body>
    </html>
    """

    # Brevo configuration from environment
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

    if not BREVO_API_KEY:
        return jsonify(success=False, error='BREVO_API_KEY not configured'), 500
    if not SENDER_EMAIL:
        return jsonify(success=False, error='SENDER_EMAIL not configured'), 500

    # Brevo expects JSON payload to /v3/smtp/email
    payload = {
        'sender': {'email': SENDER_EMAIL},
        'to': [{'email': 'vartisticstudio@gmail.com'}],
        'subject': '🚀 New Website Enquiry – Vartistic Studio',
        'htmlContent': html_body,
        'textContent': body,
    }

    headers = {
        'api-key': BREVO_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        resp = requests.post('https://api.brevo.com/v3/smtp/email', json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        app.logger.exception('Failed to reach Brevo API')
        return jsonify(success=False, error=str(e)), 500

    if 200 <= resp.status_code < 300:
        return jsonify(success=True), 200
    else:
        # Return Brevo response body to help debug failures (not exposing secrets)
        err_text = resp.text or f'Status {resp.status_code}'
        app.logger.error('Brevo API error: %s', err_text)
        return jsonify(success=False, error=err_text), 500


if __name__ == '__main__':
    # Run in production via a proper WSGI server. This is for local/dev usage.
    app.run(host='0.0.0.0', port=5000)