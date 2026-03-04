import os, uuid, datetime, smtplib, threading, json
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Pydroid safety check
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    Limiter = None

app = Flask(__name__)
app.secret_key = "QUANTUM_CORE_SUPREME_99_VERIFIED"
CORS(app)

# 1. DATABASE (SQLite for Life-time Storage) [cite: 2026-02-20]
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantum_master_v6.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. MODELS (Users, Projects & Vault)
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100)) # e.g. "Order Page"
    # Auto-generate Verified Key [cite: 2026-02-20]
    api_key = db.Column(db.String(100), unique=True, default=lambda: f"QCORE-{uuid.uuid4().hex[:10].upper()}")
    user_email = db.Column(db.String(100)) 
    submission_count = db.Column(db.Integer, default=0)
    max_limit = db.Column(db.Integer, default=50) # Free Plan [cite: 2026-02-20]

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(100))
    payload = db.Column(db.JSON) # Saara login/signup data yahan save hoga [cite: 2026-02-20]
    visitor_ip = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. EMAIL ALERT FUNCTION [cite: 2026-02-20]
def send_submission_alert(to_email, p_name, data, v_ip):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = os.getenv("EMAIL_PASS", "hbrw 2p4m 3c6k lhyc") #
    
    subject = f"⚡ New Lead Captured: {p_name}"
    body = f"Project: {p_name}\nVisitor IP: {v_ip}\nData: {json.dumps(data, indent=2)}"
    msg = f"Subject: {subject}\n\n{body}"
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, to_email, msg)
    except: pass

# 4. ROUTES
@app.route('/')
def home():
    return render_template('index.html') # Templates folder check [cite: 2026-02-20]

# Route to create new projects and get Unique Keys [cite: 2026-02-20]
@app.route('/api/create', methods=['POST'])
def create_project():
    data = request.json
    new_p = Project(project_name=data['name'], user_email=data['email'])
    db.session.add(new_p)
    db.session.commit()
    return jsonify({"key": new_p.api_key, "project": new_p.project_name})

# DATA RECEIVE (Visitor data yahan aayega) [cite: 2026-02-20]
@app.route('/v1/receive/<api_key>', methods=['POST'])
def receive_data(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project: return jsonify({"error": "Key Invalid"}), 403
    
    if project.submission_count >= project.max_limit:
        return jsonify({"error": "Limit Reached (50/50)"}), 402

    visitor_data = request.json
    v_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # 1. Save in Data Vault [cite: 2026-02-20]
    new_entry = DataVault(api_key=api_key, payload=visitor_data, visitor_ip=v_ip)
    project.submission_count += 1
    db.session.add(new_entry)
    db.session.commit()
    
    # 2. Fast Email Alert [cite: 2026-02-20]
    threading.Thread(target=send_submission_alert, args=(project.user_email, project.project_name, visitor_data, v_ip)).start()
    
    return jsonify({"status": "captured", "count": project.submission_count}), 200

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
