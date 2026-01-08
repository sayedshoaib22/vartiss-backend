from flask import Flask, request, jsonify
import os
import requests
import html as html_lib

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
    body_intro = source if source else 'Website Enquiry'
    body = (
        f"Source: {source}\n\n"
        f"{body_intro}:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone_display}\n\n"
        f"Message:\n{message}\n"
    )

    # HTML body (ADMIN) - escape to avoid injection and preserve line breaks
    esc_name = html_lib.escape(name)
    esc_email = html_lib.escape(email)
    esc_phone = html_lib.escape(phone_display)
    esc_source = html_lib.escape(source)
    esc_message = html_lib.escape(message).replace('\n', '<br>')

    html_body = f"""
    <html>
      <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
        <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(16,24,40,0.08);overflow:hidden;">
          <div style="background:linear-gradient(90deg,#b8860b,#ffd700);padding:20px 24px;color:#fff;">
            <h1 style="margin:0;font-size:18px">Vartistic Studio</h1>
            <p style="margin:6px 0 0;font-size:13px;opacity:0.9">{html_lib.escape(body_intro)}</p>
            <p style="margin:6px 0 0;font-size:13px;opacity:0.9"><b>Source:</b> {esc_source}</p>
          </div>
          <div style="padding:24px;color:#0f172a;font-size:14px;">
            <table width="100%" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
              <tr><td style="width:120px;font-weight:600">Name</td><td>{esc_name}</td></tr>
              <tr><td style="width:120px;font-weight:600">Email</td><td>{esc_email}</td></tr>
              <tr><td style="width:120px;font-weight:600">Phone</td><td>{esc_phone}</td></tr>
            </table>
            <div style="margin-top:16px;padding:16px;background:#f8fafc;border-radius:6px;">
              {esc_message}
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
        'sender': {'email': SENDER_EMAIL, 'name': 'Vartistic Studio'},
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
        # return Brevo error body as JSON
        return jsonify(success=False, error=resp.text, status_code=resp.status_code), 500

    # ---------------- USER CONFIRMATION EMAIL ----------------
    esc_user_message = html_lib.escape(message).replace('\n', '<br>')
    client_html = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;color:#0f172a;line-height:1.4;margin:0;padding:20px;background:#f4f6f8;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;padding:24px;border-radius:8px;">
          <p style="margin:0 0 12px;">Hi {esc_name},</p>
          <p style="margin:0 0 12px;">Thank you for contacting <strong>Vartistic Studio</strong>. We have received your enquiry and will contact you shortly.</p>
          <hr style="border:none;border-top:1px solid #eef2f7;margin:16px 0;">
          <h3 style="margin:0 0 8px;font-size:16px">Your submission</h3>
          <p style="margin:6px 0"><strong>Name:</strong> {esc_name}</p>
          <p style="margin:6px 0"><strong>Email:</strong> {esc_email}</p>
          <p style="margin:6px 0"><strong>Phone:</strong> {esc_phone}</p>
          <p style="margin:6px 0"><strong>Message:</strong><br>{esc_user_message}</p>
          <p style="margin-top:18px;">Best regards,<br><strong>Vartistic Studio Team</strong></p>
        </div>
      </body>
    </html>
    """

    user_payload = {
        'sender': {'email': SENDER_EMAIL, 'name': 'Vartistic Studio'},
        'to': [{'email': email, 'name': name}],
        'subject': 'Vartistic Studio – We received your enquiry',
        'htmlContent': client_html,
        'textContent': body,
    }

    client_email_sent = False
    client_error = None
    try:
        user_resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            json=user_payload,
            headers=headers,
            timeout=15
        )
        if 200 <= user_resp.status_code < 300:
            client_email_sent = True
        else:
            client_error = f"Status {user_resp.status_code}: {user_resp.text}"
    except requests.RequestException as e:
        client_error = str(e)

    # Admin email succeeded; client email may or may not have succeeded.
    response_payload = {'success': True, 'admin_email_sent': True, 'client_email_sent': client_email_sent}
    if client_error:
        response_payload['client_error'] = client_error

    return jsonify(response_payload), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
