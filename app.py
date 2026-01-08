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

    # Detect source safely; default to 'Website Enquiry' when missing
    raw_source = data.get('source')
    source = (raw_source or 'Website Enquiry')
    source_norm = (source or '').strip().lower()

    phone_display = phone if phone else 'Not provided'

    # Plain-text body
    # Prepend Source line and use a human-friendly intro based on source
    body_intro = source if source else 'Website Enquiry'
    body = f"Source: {source}\n\n{body_intro}:\n\nName:\n{name}\n\nEmail:\n{email}\n\nPhone:\n{phone_display}\n\nMessage:\n{message}\n"

    # HTML body (ADMIN)
    html_body = f"""
    <html>
        <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
            <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(16,24,40,0.08);overflow:hidden;">
                  <div style="background:linear-gradient(90deg,#b8860b,#ffd700);padding:20px 24px;color:#fff;">
                    <h1 style="margin:0;font-size:18px">Vartistic Studio</h1>
                    <p style="margin:6px 0 0;font-size:13px;opacity:0.9">{body_intro}</p>
                    <p style="margin:6px 0 0;font-size:13px;opacity:0.9"><b>Source:</b> {source}</p>
                </div>
                <div style="padding:24px;color:#0f172a;font-size:14px;">
                    <table width="100%">
                        <tr><td><b>Name</b></td><td>{name}</td></tr>
                        <tr><td><b>Email</b></td><td>{email}</td></tr>
                        <tr><td><b>Phone</b></td><td>{phone_display}</td></tr>
                    </table>
                    <div style="margin-top:16px;padding:16px;background:#f8fafc;border-radius:6px;">
                        {message}
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    # Brevo configuration
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

    if not BREVO_API_KEY:
        return jsonify(success=False, error='BREVO_API_KEY not configured'), 500
    if not SENDER_EMAIL:
        return jsonify(success=False, error='SENDER_EMAIL not configured'), 500

    headers = {
        'api-key': BREVO_API_KEY,
        'Content-Type': 'application/json'
    }

    # ---------------- ADMIN EMAIL ----------------
    # Choose subject based on the provided source (defaults handled above)
    if source_norm == 'portfolio submission':
        admin_subject = '📁 New Portfolio Submission – Vartistic Studio'
    else:
        admin_subject = '🌐 New Website Enquiry – Vartistic Studio'

    admin_payload = {
        'sender': {'email': SENDER_EMAIL},
        'to': [{'email': 'vartisticstudio@gmail.com'}],
        'subject': admin_subject,
        'htmlContent': html_body,
        'textContent': body,
    }

    try:
        resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            json=admin_payload,
            headers=headers,
            timeout=15
        )
    except requests.RequestException as e:
        return jsonify(success=False, error=str(e)), 500

    if not (200 <= resp.status_code < 300):
        return jsonify(success=False, error=resp.text), 500

    # ---------------- USER CONFIRMATION EMAIL (ADDED ONLY) ----------------
    user_payload = {
        'sender': {'email': SENDER_EMAIL, 'name': 'Vartistic Studio'},
        'to': [{'email': email}],
        'subject': 'Vartistic Studio – We’ve received your enquiry',
        'htmlContent': f"""
        <html>
          <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
            <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;">
              <div style="background:#0f172a;padding:20px 24px;color:#fff;">
                <h1 style="margin:0;font-size:20px">We’ve received your enquiry</h1>
              </div>
              <div style="padding:24px;font-size:14px;line-height:1.6;">
                <p style="margin:0 0 12px;">Hi {name},</p>
                <p style="margin:0 0 12px;">Thank you for contacting <strong>Vartistic Studio</strong>. We’ve received your enquiry and a member of our team will be in touch soon.</p>

                <h2 style="font-size:15px;margin:18px 0 8px;">Your submission</h2>
                <table width="100%" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
                  <tr><td style="width:120px;font-weight:600;">Name</td><td>{name}</td></tr>
                  <tr><td style="font-weight:600;">Email</td><td>{email}</td></tr>
                  <tr><td style="font-weight:600;">Phone</td><td>{phone_display}</td></tr>
                  <tr><td style="font-weight:600;vertical-align:top;">Message</td><td>{message}</td></tr>
                </table>

                <p style="margin:18px 0 0;">Kind regards,<br><strong>Vartistic Studio Team</strong></p>
              </div>
            </div>
          </body>
        </html>
        """
    }

    try:
        requests.post(
            'https://api.brevo.com/v3/smtp/email',
            json=user_payload,
            headers=headers,
            timeout=15
        )
    except Exception:
        pass  # user mail failure should not break admin mail

    return jsonify(success=True), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
