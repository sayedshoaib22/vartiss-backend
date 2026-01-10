from flask import Flask, request, jsonify
import os
import requests
import html as html_lib
import json

app = Flask(__name__)


# Optional: load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def render_email_template(name, email, phone, message, subject="Website Enquiry", company="Vartistic Studio", subtitle=None):
        """
        Returns an HTML email (string) for both admin and client with inline CSS only.
        All user inputs are escaped. The same template can be reused for admin or client
        by altering `subject` and `subtitle`.
        """
        import html
        esc = html.escape

        esc_name = esc(name or "")
        esc_email = esc(email or "")
        esc_phone = esc(phone or "Not provided")
        esc_message = esc(message or "").replace('\n', '<br>')
        esc_subject = esc(subject or "")
        esc_company = esc(company or "Vartistic Studio")
        esc_subtitle = esc(subtitle or esc_subject)

        return f"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
    </head>
    <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Inter, Helvetica, Arial, sans-serif;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;-webkit-font-smoothing:antialiased;font-size:15px;color:#0f172a;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
            <tr>
                <td align="center">
                    <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:10px;box-shadow:0 8px 24px rgba(16,24,40,0.08);overflow:hidden;border-collapse:collapse;">
                        <tr>
                            <td style="padding:22px 24px;background:linear-gradient(90deg,#b8860b 0%,#ffd700 100%);color:#ffffff;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                                    <tr>
                                        <td style="vertical-align:middle;">
                                            <h1 style="margin:0;font-size:22px;line-height:1.05;font-weight:700;color:#ffffff;font-family:Inter, Helvetica, Arial, sans-serif;">{esc_company}</h1>
                                            <p style="margin:6px 0 0;font-size:13px;opacity:0.95;color:#fff;font-weight:600;font-family:Inter, Helvetica, Arial, sans-serif;">{esc_subtitle}</p>
                                        </td>
                                        <td style="width:72px;text-align:right;vertical-align:middle;">
                                            <div style="width:48px;height:48px;border-radius:8px;background:rgba(255,255,255,0.15);display:inline-block;"></div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <tr>
                            <td style="padding:24px 24px 20px;color:#0f172a;font-size:15px;line-height:1.45;">
                                <p style="margin:0 0 14px;font-size:15px;">Hello{', ' + esc_name if esc_name else ''},</p>

                                <p style="margin:0 0 18px;font-size:15px;">We received the following submission. Below are the details:</p>

                                <table role="presentation" width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse;margin-bottom:18px;">
                                    <tr>
                                        <td style="width:130px;font-weight:600;padding:8px 8px 8px 0;color:#0f172a;font-size:14px;vertical-align:top;">Name</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;">{esc_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="width:130px;font-weight:600;padding:8px 8px 8px 0;color:#0f172a;font-size:14px;vertical-align:top;">Email</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;">{esc_email}</td>
                                    </tr>
                                    <tr>
                                        <td style="width:130px;font-weight:600;padding:8px 8px 8px 0;color:#0f172a;font-size:14px;vertical-align:top;">Phone</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;">{esc_phone}</td>
                                    </tr>
                                </table>

                                <div style="background:#f8fafc;border:1px solid #eef2f7;padding:16px;border-radius:8px;color:#0f172a;">
                                    <div style="font-weight:600;margin-bottom:8px;color:#0f172a;font-size:14px;">Message</div>
                                    <div style="color:#334155;font-size:14px;">{esc_message}</div>
                                </div>
                            </td>
                        </tr>

                        <tr>
                            <td style="padding:18px 24px 24px;background:#ffffff;color:#6b7280;font-size:13px;border-top:1px solid #f1f5f9;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                                    <tr>
                                        <td style="vertical-align:middle;color:#6b7280;">
                                            <div style="font-size:13px;">Best regards,<br><strong style="color:#0f172a;">{esc_company} Team</strong></div>
                                        </td>
                                        <td style="text-align:right;vertical-align:middle;color:#6b7280;font-size:12px;">
                                            <div>Subject: {esc_subject}</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
            <tr>
                <td align="center" style="padding-top:12px;font-size:12px;color:#9aa4b2;">
                    <div style="max-width:680px;width:100%;text-align:center;">© {esc_company}. All rights reserved.</div>
                </td>
            </tr>
        </table>
    </body>
</html>"""


def send_email_with_fallback(subject, html, text, to_email, to_name):
    try:
        # -------- TRY BREVO FIRST --------
        brevo_payload = {
            "sender": {"email": os.environ.get("SENDER_EMAIL", "vartisticstudio@gmail.com"), "name": "Vartistic Studio"},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
        }

        brevo_headers = {
            "api-key": os.environ.get("BREVO_API_KEY"),
            "Content-Type": "application/json",
        }

        brevo_resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=brevo_payload,
            headers=brevo_headers,
            timeout=10
        )

        if 200 <= brevo_resp.status_code < 300:
            return {"provider": "brevo", "status": "sent", "response": brevo_resp.text}

        raise Exception(f"Brevo failed: {brevo_resp.status_code} {brevo_resp.text}")

    except Exception:
        # -------- FALLBACK TO RESEND --------
        resend_api_key = os.environ.get('RESEND_API_KEY')
        if not resend_api_key:
            raise Exception('Both Brevo failed and RESEND_API_KEY not configured')

        resend_headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        }

        resend_payload = {
            "from": "Vartistic Studio <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        }

        resend_resp = requests.post(
            "https://api.resend.com/emails",
            json=resend_payload,
            headers=resend_headers,
            timeout=10
        )

        if 200 <= resend_resp.status_code < 300:
            return {"provider": "resend", "status": "sent", "response": resend_resp.text}

        raise Exception(f"Both Brevo and Resend failed: {resend_resp.status_code} {resend_resp.text}")


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

        # We'll use the reusable HTML template when composing emails below.

    # Brevo configuration - must be provided via environment variables
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

    # Render the same HTML for admin and client with minor subtitle differences
    admin_html = render_email_template(name, email, phone_display, message, subject=admin_subject, company='Vartistic Studio', subtitle=body_intro + ' (Admin)')

    admin_payload = {
        'sender': {'email': SENDER_EMAIL, 'name': 'Vartistic Studio'},
        'to': [{'email': 'vartisticstudio@gmail.com'}],
        'subject': admin_subject,
        'htmlContent': admin_html,
        'textContent': body,
    }

    try:
        admin_result = send_email_with_fallback(admin_subject, admin_html, body, 'vartisticstudio@gmail.com', 'Vartistic Studio')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    if admin_result.get('status') != 'sent':
        return jsonify(success=False, error='Admin email failed', details=admin_result), 500

    # ---------------- USER CONFIRMATION EMAIL ----------------
    client_subject = 'Vartistic Studio – We received your enquiry'
    client_html = render_email_template(name, email, phone_display, message, subject=client_subject, company='Vartistic Studio', subtitle=body_intro + ' (Confirmation)')

    user_payload = {
            'sender': {'email': SENDER_EMAIL, 'name': 'Vartistic Studio'},
            'to': [{'email': email, 'name': name}],
            'subject': client_subject,
            'htmlContent': client_html,
            'textContent': body,
    }

    client_email_sent = False
    client_error = None
    try:
        client_result = send_email_with_fallback(client_subject, client_html, body, email, name)
        if client_result.get('status') == 'sent':
            client_email_sent = True
        else:
            client_error = json.dumps(client_result)
    except Exception as e:
        client_error = str(e)

    # Admin email succeeded; client email may or may not have succeeded.
    response_payload = {'success': True, 'admin_email_sent': True, 'client_email_sent': client_email_sent}
    if client_error:
        response_payload['client_error'] = client_error

    return jsonify(response_payload), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
