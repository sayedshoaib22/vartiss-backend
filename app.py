from flask import Flask, request, jsonify, send_file, abort
import os
import requests
import sqlite3
from datetime import datetime
from io import BytesIO

try:
    from openpyxl import Workbook
except Exception:
    Workbook = None

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'submissions.db')
EXCEL_PATH = os.path.join(BASE_DIR, 'clients.xlsx')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.commit()
    finally:
        conn.close()


def sync_excel_from_db():
    if Workbook is None:
        raise RuntimeError('openpyxl is required to write Excel files')

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, created_at, name, email, phone, message, source FROM clients ORDER BY created_at ASC')
        rows = cur.fetchall()
    finally:
        conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = 'Clients'
    ws.append(['id', 'created_at', 'name', 'email', 'phone', 'message', 'source'])
    for r in rows:
        ws.append(list(r))

    wb.save(EXCEL_PATH)


init_db()


@app.route('/send-mail', methods=['POST', 'OPTIONS'])
def send_mail():
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
    source = (data.get('source') or 'Website Enquiry').strip()

    if not name or not email or not message:
        return jsonify(success=False, error='Missing required fields'), 400

    created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Save to SQLite DB
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO clients (name, email, phone, message, source, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (name, email, phone, message, source, created_at)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return jsonify(success=False, error='Failed to save submission'), 500

    # Sync Excel from DB (truncate + rewrite)
    try:
        sync_excel_from_db()
    except Exception:
        return jsonify(success=False, error='Failed to update Excel from database'), 500

    # Prepare and attempt to send client confirmation email (non-fatal)
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

    user_subject = 'Vartistic Studio - We\'ve received your enquiry'
    user_html = f"""
    <html>
      <body style="margin:0;padding:20px;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
        <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;">
          <div style="background:#0f172a;padding:20px 24px;color:#fff;">
            <h1 style="margin:0;font-size:20px">We\'ve received your enquiry</h1>
          </div>
          <div style="padding:24px;font-size:14px;line-height:1.6;">
            <p style="margin:0 0 12px;">Hi {name},</p>
            <p style="margin:0 0 12px;">Thank you for contacting <strong>Vartistic Studio</strong>. We\'ve received your enquiry and a member of our team will be in touch soon.</p>

            <h2 style="font-size:15px;margin:18px 0 8px;">Your submission</h2>
            <table width="100%" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
              <tr><td style="width:120px;font-weight:600;">Name</td><td>{name}</td></tr>
              <tr><td style="font-weight:600;">Email</td><td>{email}</td></tr>
              <tr><td style="font-weight:600;">Phone</td><td>{phone}</td></tr>
              <tr><td style="font-weight:600;vertical-align:top;">Message</td><td>{message}</td></tr>
              <tr><td style="font-weight:600;">Source</td><td>{source}</td></tr>
              <tr><td style="font-weight:600;">Submitted at (UTC)</td><td>{created_at}</td></tr>
            </table>

            <p style="margin:18px 0 0;">Kind regards,<br><strong>Vartistic Studio Team</strong></p>
          </div>
        </div>
      </body>
    </html>
    """

    user_payload = {
        'sender': {'email': SENDER_EMAIL or '', 'name': 'Vartistic Studio'},
        'to': [{'email': email}],
        'subject': user_subject,
        'htmlContent': user_html,
    }

    try:
        if BREVO_API_KEY and SENDER_EMAIL:
            headers = {'api-key': BREVO_API_KEY, 'Content-Type': 'application/json'}
            requests.post(
                'https://api.brevo.com/v3/smtp/email',
                json=user_payload,
                headers=headers,
                timeout=15
            )
    except Exception:
        pass

    return jsonify(success=True), 200


@app.route('/export-excel', methods=['GET'])
def export_excel():
    token_required = os.environ.get('EXPORT_TOKEN')
    if token_required:
        token = request.headers.get('X-Export-Token') or request.args.get('token')
        if not token or token != token_required:
            abort(401)

    if Workbook is None:
        return jsonify(success=False, error='openpyxl not installed'), 500

    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute('SELECT id, created_at, name, email, phone, message, source FROM clients ORDER BY created_at ASC')
            rows = cur.fetchall()
        finally:
            conn.close()
    except Exception:
        return jsonify(success=False, error='Failed to read database'), 500

    wb = Workbook()
    ws = wb.active
    ws.title = 'Clients'
    ws.append(['id', 'created_at', 'name', 'email', 'phone', 'message', 'source'])
    for r in rows:
        ws.append(list(r))

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = f"clients_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        bio,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
