from flask import Flask, request, jsonify
import os
import requests
import html as html_lib
import json
import logging
import time
from typing import List, Dict, Any, Optional

app = Flask(__name__)

# Basic logging configuration
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))


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


def _send_via_brevo(api_key: str, payload: Dict[str, Any], timeout: int = 10) -> requests.Response:
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    session = requests.Session()
    return session.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=timeout)


def _send_via_resend(api_key: str, sender: str, to: List[str], subject: str, html: str, text: Optional[str] = None, timeout: int = 10) -> requests.Response:
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
    timeout = 10

    sender_email = sender_email or os.environ.get("SENDER_EMAIL")
    if not sender_email:
        raise RuntimeError("SENDER_EMAIL environment variable is required")

    brevo_keys = [os.environ.get("BREVO_API_KEY_1"), os.environ.get("BREVO_API_KEY_2")]
    resend_key = os.environ.get("RESEND_API_KEY")

    # Normalize list: only keep non-empty keys
    brevo_keys = [k for k in brevo_keys if k]

    last_error: Optional[str] = None

    # Try Brevo keys in order
    for idx, key in enumerate(brevo_keys, start=1):
        try:
            logger.debug("Attempting Brevo key %d", idx)
            payload = _format_brevo_payload(sender_email, sender_name, subject, html, text, to_email, to_name, cc, bcc, reply_to)
            resp = _send_via_brevo(key, payload, timeout=timeout)
            if 200 <= resp.status_code < 300:
                return {"provider": f"brevo_{idx}", "status": "sent", "response": resp.text}
            # Treat 4xx/5xx/429 as failures to move to next provider
            last_error = f"brevo_{idx} HTTP {resp.status_code}: {resp.text}"
            logger.warning("Brevo key %d returned status %s", idx, resp.status_code)
        except requests.RequestException as exc:
            last_error = f"brevo_{idx} exception: {str(exc)}"
            logger.exception("Brevo key %d request failed", idx)
        # brief backoff before trying next provider
        time.sleep(0.5)

    # If Brevo keys exhausted, try Resend
    if resend_key:
        try:
            logger.debug("Attempting Resend as final fallback")
            sender_formatted = f"{sender_name} <{sender_email}>"
            resp = _send_via_resend(resend_key, sender_formatted, [to_email], subject, html, text, timeout=timeout)
            if 200 <= resp.status_code < 300:
                return {"provider": "resend", "status": "sent", "response": resp.text}
            last_error = f"resend HTTP {resp.status_code}: {resp.text}"
            logger.warning("Resend returned status %s", resp.status_code)
        except requests.RequestException as exc:
            last_error = f"resend exception: {str(exc)}"
            logger.exception("Resend request failed")

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


@app.route('/send-mail', methods=['POST', 'OPTIONS'])
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

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        phone = (data.get('phone') or '').strip()
        message = (data.get('message') or '').strip()
        source = (data.get('source') or 'Website Enquiry').strip()

        # Validate required fields
        if not name or not email or not message:
            return jsonify(success=False, error='Missing required fields: name, email, message'), 400
        if not _is_valid_email(email):
            return jsonify(success=False, error='Invalid email address'), 400
        if len(name) > 200 or len(message) > 5000:
            return jsonify(success=False, error='Payload too large'), 413

        phone_display = phone if phone else 'Not provided'
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
        admin_subject = '📁 New Portfolio Submission – Vartistic Studio' if source.strip().lower() == 'portfolio submission' else '🌐 New Website Enquiry – Vartistic Studio'
        admin_html = render_email_template(name, email, phone_display, message, subject=admin_subject, company='Vartistic Studio', subtitle=body_intro + ' (Admin)')

        client_subject = 'Vartistic Studio – We received your enquiry'
        client_html = render_email_template(name, email, phone_display, message, subject=client_subject, company='Vartistic Studio', subtitle=body_intro + ' (Confirmation)')

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
