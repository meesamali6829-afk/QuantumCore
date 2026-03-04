import os, uuid, datetime, smtplib, threading, json, re
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# 1. INITIALIZATION & SECURITY HEADERS
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "QUANTUM_CORE_SUPREME_99_VERIFIED")
app.permanent_session_lifetime = datetime.timedelta(days=7) # Strong Session
CORS(app, resources={r"/*": {"origins": "*"}}) # Global Access Control

# 2. DATABASE CONFIGURATION (Strong Integrity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantum_pro_v8.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True} # Connection auto-refresh
db = SQLAlchemy(app)

# 3. MODELS (Titan Grade Models)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True, cascade="all, delete-orphan")

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(100), unique=True, default=lambda: f"QC-{uuid.uuid4().hex[:12].upper()}", index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_count = db.Column(db.Integer, default=0)
    max_limit = db.Column(db.Integer, default=50)
    status = db.Column(db.String(20), default="active") # Project On/Off toggle

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(100), index=True)
    payload = db.Column(db.JSON)
    visitor_ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(200)) # Device info capture
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 4. UTILITY: LOGIN REQUIRED DECORATOR (Security Layer)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Auth Token Missing"}), 401
        return f(*args, **kwargs)
    return decorated_function

# 5. TEMPLATE ROUTES (Index and Dashboard)
@app.route('/')
def home():
    # Ye line templates folder ke andar index.html ko dhoondti hai
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html')

# 6. FAST ALERT SYSTEM (Threaded & Bulletproof)
def send_fast_alert(to_email, data, p_name, ip):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = os.getenv("EMAIL_PASS", "hbrw 2p4m 3c6k lhyc")
    try:
        subject = f"⚡ NEW LEAD: {p_name}"
        body = f"Project: {p_name}\nIP: {ip}\nTime: {datetime.datetime.now()}\n\nData:\n{json.dumps(data, indent=2)}"
        msg = f"Subject: {subject}\n\n{body}"
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, to_email, msg)
    except: pass

# 7. API ROUTES (Strong & Optimized)
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Invalid Data"}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email globally registered. Try logging in."}), 409
    
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256') # Stronger Hash
    new_user = User(username=data.get('username', data['email'].split('@')[0]), 
                    email=data['email'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "msg": "Quantum Account Verified"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session.permanent = True
        session['user_id'] = user.id
        return jsonify({"success": True, "user": user.username}), 200
    return jsonify({"error": "Security Mismatch"}), 401

@app.route('/api/project/new', methods=['POST'])
@login_required
def create_project():
    data = request.json
    new_p = Project(project_name=data['name'], user_id=session['user_id'])
    db.session.add(new_p)
    db.session.commit()
    return jsonify({"key": new_p.api_key, "name": new_p.project_name})

@app.route('/api/vault/fetch')
@login_required
def get_vault():
    user = User.query.get(session['user_id'])
    response_data = []
    for proj in user.projects:
        data_points = DataVault.query.filter_by(api_key=proj.api_key).order_by(DataVault.timestamp.desc()).all()
        response_data.append({
            "name": proj.project_name,
            "key": proj.api_key,
            "leads": proj.submission_count,
            "history": [{"id": d.id, "data": d.payload, "ip": d.visitor_ip, "time": d.timestamp} for d in data_points]
        })
    return jsonify(response_data)

# 8. CAPTURE ENGINE (The Core Mechanism)
@app.route('/v1/receive/<api_key>', methods=['POST'])
def capture(api_key):
    # Security: Proxy-safe IP capture
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    project = Project.query.filter_by(api_key=api_key, status='active').first()
    
    if not project or project.submission_count >= project.max_limit:
        return jsonify({"status": "blocked", "reason": "quota_exceeded"}), 403

    payload = request.json
    new_entry = DataVault(api_key=api_key, payload=payload, visitor_ip=ip, 
                          user_agent=request.headers.get('User-Agent'))
    
    project.submission_count += 1
    db.session.add(new_entry)
    db.session.commit()
    
    # Fast Background Alert
    threading.Thread(target=send_fast_alert, args=(project.owner.email, payload, project.project_name, ip)).start()
    return jsonify({"status": "success", "vault_id": uuid.uuid4().hex[:8]}), 200

# 9. GLOBAL ERROR HANDLING & OPTIMIZATION
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Schema auto-check
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
