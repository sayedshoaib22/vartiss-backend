from flask import Flask, request, jsonify
import os
import requests
import json
import logging
import time
from typing import List, Dict, Any, Optional

app = Flask(__name__)

# Basic logging configuration
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=log_level)


# Optional: load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def format_phone(phone):
    if not phone:
        return 'Not provided'
    phone = phone.strip()
    if phone.startswith('+'):
        return phone
    # Assume Indian if 10 digits starting with 6-9
    if len(phone) == 10 and phone.isdigit() and phone[0] in '6789':
        return '+91' + phone
    return phone


def render_email_template(name, email, phone, message, subject="Website Enquiry", company="Vartistic Studio", subtitle=None, body_text=None):
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
        if not body_text:
            body_text = "We received the following submission. Below are the details:"
        esc_body_text = esc(body_text).replace('\n', '<br>')

        return f"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
    </head>
    <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Poppins, 'Segoe UI', Arial, sans-serif;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;-webkit-font-smoothing:antialiased;font-size:15px;color:#0f172a;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
            <tr>
                <td align="center">
                    <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:10px;box-shadow:0 10px 30px rgba(16,24,40,0.08);overflow:hidden;border-collapse:collapse;">
                        <!-- Header -->
                        <tr>
                            <td align="center" style="padding:20px 24px;background:linear-gradient(90deg,#b8860b 0%,#ffd700 100%);color:#ffffff;text-align:center;vertical-align:middle;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                                    <tr>
                                        <td align="center" valign="middle" height="76" style="padding:0;">
                                            <span style="display:inline-block;font-family:Poppins, 'Segoe UI', Arial, sans-serif;font-size:28px;font-weight:700;color:#ffffff;margin:0;">{esc_company}</span>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding:28px 28px 20px;background:#ffffff;color:#0f172a;font-size:15px;line-height:1.45;">
                                <p style="margin:0 0 14px;font-size:15px;">Hello{', ' + esc_name if esc_name else ''},</p>
                                <p style="margin:0 0 18px;font-size:15px;color:#374151;">{esc_body_text}</p>

                                <table role="presentation" width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse;margin-bottom:18px;">
                                    <tr>
                                        <td style="width:140px;padding:8px 8px 8px 0;color:#6b7280;font-size:14px;font-weight:600;vertical-align:top;">Name</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;font-weight:600;">{esc_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="width:140px;padding:8px 8px 8px 0;color:#6b7280;font-size:14px;font-weight:600;vertical-align:top;">Email</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;font-weight:600;">{esc_email}</td>
                                    </tr>
                                    <tr>
                                        <td style="width:140px;padding:8px 8px 8px 0;color:#6b7280;font-size:14px;font-weight:600;vertical-align:top;">Phone</td>
                                        <td style="padding:8px;background:transparent;border-radius:4px;color:#0f172a;font-size:14px;font-weight:600;">{esc_phone}</td>
                                    </tr>
                                </table>

                                <div style="background:#f7f8fa;border-radius:8px;border-left:4px solid #b8860b;padding:16px;color:#334155;font-size:14px;">
                                    <div style="font-weight:600;margin-bottom:8px;color:#0f172a;font-size:14px;">Message</div>
                                    <div style="white-space:pre-wrap;">{esc_message}</div>
                                </div>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding:18px 24px 24px;background:#ffffff;color:#6b7280;font-size:13px;border-top:1px solid #f1f5f9;">
                                <div style="font-size:13px;color:#6b7280;">Best regards,<br><strong style="color:#0f172a;">{esc_company} Team</strong></div>
                                <div style="margin-top:10px;font-size:12px;color:#9ca3af;text-align:center;">🌐 Vartistic Studio | Creative Digital Solutions</div>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>"""


def _format_brevo_payload(sender_email: str, sender_name: str, subject: str, html: str, text: str, to_email: str, to_name: Optional[str] = None, cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None, reply_to: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email, "name": (to_name or "")}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    if cc:
        payload["cc"] = [{"email": e} for e in cc]
    if bcc:
        payload["bcc"] = [{"email": e} for e in bcc]
    if reply_to:
        payload["replyTo"] = reply_to
    return payload


def _send_via_brevo(api_key: str, payload: Dict[str, Any], timeout: int = 20) -> requests.Response:
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    session = requests.Session()
    return session.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=timeout)


def _send_via_resend(api_key: str, sender: str, to: List[str], subject: str, html: str, text: Optional[str] = None, timeout: int = 20) -> requests.Response:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "from": sender,
        "to": to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    session = requests.Session()
    return session.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=timeout)


def send_email_with_fallback(subject: str, html: str, text: str, to_email: str, to_name: Optional[str] = None, *, sender_email: Optional[str] = None, sender_name: str = "Vartistic Studio", cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None, reply_to: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
    """
    Attempts to send email using BREVO_API_KEY_1, then BREVO_API_KEY_2, then RESEND_API_KEY.
    Returns a dict: {'provider': str, 'status': 'sent'|'failed', 'response': ...}
    """
    logger = logging.getLogger("email_fallback")
    # Increase timeout to accommodate slow networks / cold starts on hosted platforms
    timeout = 20

    sender_email = sender_email or os.environ.get("SENDER_EMAIL")
    if not sender_email:
        raise RuntimeError("SENDER_EMAIL environment variable is required")

    brevo_keys = [os.environ.get("BREVO_API_KEY_1"), os.environ.get("BREVO_API_KEY_2")]
    resend_key = os.environ.get("RESEND_API_KEY")

    # Normalize list: only keep non-empty keys
    brevo_keys = [k for k in brevo_keys if k]

    last_error: Optional[str] = None

    # Try Brevo keys in order, with a small retry for transient network issues
    for idx, key in enumerate(brevo_keys, start=1):
        provider_name = f"brevo_{idx}"
        if not key:
            continue
        for attempt in (1, 2):
            try:
                logger.info("Attempting provider %s (attempt %d)", provider_name, attempt)
                payload = _format_brevo_payload(sender_email, sender_name, subject, html, text, to_email, to_name, cc, bcc, reply_to)
                resp = _send_via_brevo(key, payload, timeout=timeout)
                status = resp.status_code
                body = (resp.text or '')[:2000]
                if 200 <= status < 300:
                    logger.info("Provider %s succeeded (status=%s)", provider_name, status)
                    return {"provider": provider_name, "status": "sent", "response": body}
                last_error = f"{provider_name} HTTP {status}: {body}"
                logger.warning("Provider %s returned HTTP %s; body: %s", provider_name, status, body)
            except requests.RequestException as exc:
                err_str = f"{type(exc).__name__}: {str(exc)}"
                last_error = f"{provider_name} exception: {err_str}"
                logger.warning("Provider %s request exception: %s", provider_name, err_str)
            # backoff before retrying or moving to next provider
            time.sleep(0.8 * attempt)

    # If Brevo keys exhausted, try Resend
    if resend_key:
        provider_name = "resend"
        for attempt in (1, 2):
            try:
                logger.info("Attempting provider %s (attempt %d)", provider_name, attempt)
                sender_formatted = f"{sender_name} <{sender_email}>"
                resp = _send_via_resend(resend_key, sender_formatted, [to_email], subject, html, text, timeout=timeout)
                status = resp.status_code
                body = (resp.text or '')[:2000]
                if 200 <= status < 300:
                    logger.info("Provider %s succeeded (status=%s)", provider_name, status)
                    return {"provider": provider_name, "status": "sent", "response": body}
                last_error = f"{provider_name} HTTP {status}: {body}"
                logger.warning("Provider %s returned HTTP %s; body: %s", provider_name, status, body)
            except requests.RequestException as exc:
                err_str = f"{type(exc).__name__}: {str(exc)}"
                last_error = f"{provider_name} exception: {err_str}"
                logger.warning("Provider %s request exception: %s", provider_name, err_str)
            time.sleep(0.8 * attempt)

    # Nothing succeeded
    logger.error("All providers failed: %s", last_error)
    return {"provider": "none", "status": "failed", "error": last_error}


@app.after_request
def add_cors_headers(response):
    # Allow simple cross-origin testing from different ports (localhost)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response


def _get_env(key: str, required: bool = False) -> Optional[str]:
    val = os.environ.get(key)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def _is_valid_email(email: str) -> bool:
    import re
    if not email:
        return False
    if len(email) > 254:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


def _parse_json_request() -> Dict[str, Any]:
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


@app.route('/send-mail', methods=['POST', 'OPTIONS'])
def send_mail():
    logger = logging.getLogger('send_mail')
    # Quick CORS preflight handling
    if request.method == 'OPTIONS':
        return jsonify(success=True), 200

    try:
        data = _parse_json_request()

        name = (data.get('name') or request.form.get('name') or '').strip()
        email = (data.get('email') or request.form.get('email') or '').strip()
        phone = (data.get('phone') or request.form.get('phone') or '').strip()
        message = (data.get('message') or request.form.get('message') or '').strip()
        source = (data.get('source') or request.form.get('source') or 'Website Enquiry').strip()

        # Validate required fields
        if not name or not email or not message:
            return jsonify(success=False, error='Missing required fields: name, email, message'), 400
        if not _is_valid_email(email):
            return jsonify(success=False, error='Invalid email address'), 400
        if len(name) > 200 or len(message) > 5000:
            return jsonify(success=False, error='Payload too large'), 413

        phone_display = format_phone(phone)
        body_intro = source or 'Website Enquiry'
        body = (
            f"Source: {source}\n\n"
            f"{body_intro}:\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Phone: {phone_display}\n\n"
            f"Message:\n{message}\n"
        )

        # Prepare HTML bodies using existing template helper which escapes inputs
        admin_subject = 'New Website Enquiry Received – Vartistic Studio'
        admin_html = render_email_template(name, email, phone_display, message, subject=admin_subject, company='Vartistic Studio', subtitle=body_intro + ' (Admin)')

        client_subject = "Thanks for contacting Vartistic Studio – We'll get back within 24 hours"
        client_body_text = "Thank you for contacting Vartistic Studio. Our team has received your request and will contact you within 24 hours.\n\nFor your records, here are the details you submitted:"
        client_html = render_email_template(name, email, phone_display, message, subject=client_subject, company='Vartistic Studio', subtitle=body_intro + ' (Confirmation)', body_text=client_body_text)

        # Ensure sender email configured
        try:
            sender_email = _get_env('SENDER_EMAIL', required=True)
        except Exception:
            logger.exception('SENDER_EMAIL not configured')
            return jsonify(success=False, error='Server email configuration error'), 500

        # Send admin email (must succeed for form to be considered delivered)
        try:
            admin_result = send_email_with_fallback(admin_subject, admin_html, body, 'vartisticstudio@gmail.com', 'Vartistic Studio', sender_email=sender_email)
        except Exception:
            logger.exception('Admin email send exception')
            return jsonify(success=False, error='Failed to send email'), 502

        if admin_result.get('status') != 'sent':
            logger.error('Admin email failed: %s', admin_result)
            return jsonify(success=False, error='Failed to send email'), 502

        # Send client confirmation (best-effort; don't fail the whole request)
        client_email_sent = False
        try:
            client_result = send_email_with_fallback(client_subject, client_html, body, email, name, sender_email=sender_email)
            client_email_sent = client_result.get('status') == 'sent'
            if not client_email_sent:
                logger.warning('Client confirmation not sent: %s', client_result)
        except Exception:
            logger.exception('Client confirmation send exception')

        payload = {
            'success': True,
            'admin_email_sent': True,
            'client_email_sent': client_email_sent,
        }
        return jsonify(payload), 200

    except Exception:
        logging.getLogger('send_mail').exception('Unexpected error in send_mail')
        return jsonify(success=False, error='Internal server error'), 500


def _check_required_envs() -> None:
    logger = logging.getLogger('startup')
    required = ['SENDER_EMAIL']
    provider_vars = ['BREVO_API_KEY_1', 'BREVO_API_KEY_2', 'RESEND_API_KEY']

    missing_required = [k for k in required if not os.environ.get(k)]
    if missing_required:
        logger.error('Missing required environment variables: %s', missing_required)
    else:
        sender = os.environ.get('SENDER_EMAIL')
        if sender and not _is_valid_email(sender):
            logger.error('SENDER_EMAIL is present but invalid: %s', sender)
        else:
            logger.info('SENDER_EMAIL configured')

    present_providers = [k for k in provider_vars if os.environ.get(k)]
    if not present_providers:
        logger.warning('No mail provider API keys found in environment (BREVO_API_KEY_1, BREVO_API_KEY_2, RESEND_API_KEY)')
    else:
        logger.info('Mail provider env vars present: %s', present_providers)


_check_required_envs()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
