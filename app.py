import os, uuid, datetime, smtplib, threading, json
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "QUANTUM_CORE_SUPREME_99_VERIFIED"
CORS(app)

# 1. DATABASE SETUP
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantum_pro_v8.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. MODELS (Linked Integrity)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # Only 1 account per email
    password_hash = db.Column(db.String(128))
    # Relationship: User delete nahi hoga toh projects bhi idher hi rahenge
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100)) 
    api_key = db.Column(db.String(100), unique=True, default=lambda: f"QCORE-{uuid.uuid4().hex[:10].upper()}")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_count = db.Column(db.Integer, default=0)
    max_limit = db.Column(db.Integer, default=50)

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(100)) 
    payload = db.Column(db.JSON) 
    visitor_ip = db.Column(db.String(50))
    country = db.Column(db.String(100), default="Unknown")
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. FAST EMAIL ALERT
def send_fast_alert(to_email, data, p_name):
    SENDER = "meesamali6829@gmail.com"
    PASSWORD = os.getenv("EMAIL_PASS", "hbrw 2p4m 3c6k lhyc")
    msg = f"Subject: ⚡ NEW DATA: {p_name}\n\nData Captured:\n{json.dumps(data, indent=2)}"
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, to_email, msg)
    except: pass

# 4. AUTHENTICATION (Signup with Email Check)
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    # Check if email already exists [cite: 2026-02-20]
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"error": "Email already exists. Please login."}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Quantum Account Created Successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id # Session starts
        return jsonify({"message": "Welcome Back!", "user": user.username}), 200
    return jsonify({"error": "Wrong Email or Password"}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

# 5. PROJECT MANAGEMENT (Create Keys)
@app.route('/api/create-project', methods=['POST'])
def create_project():
    if 'user_id' not in session: return jsonify({"error": "Please login first"}), 401
    data = request.json
    new_p = Project(project_name=data['project_name'], user_id=session['user_id'])
    db.session.add(new_p)
    db.session.commit()
    return jsonify({"message": "Project Created", "key": new_p.api_key})

# 6. DATA VAULT (Fetch all user projects/keys) [cite: 2026-02-20]
@app.route('/api/my-vault-data')
def get_user_data():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session['user_id'])
    
    all_projects = []
    for proj in user.projects:
        # Har project ka data usi ki key ke hisab se filter hoga
        submissions = DataVault.query.filter_by(api_key=proj.api_key).order_by(DataVault.timestamp.desc()).all()
        all_projects.append({
            "project_name": proj.project_name,
            "api_key": proj.api_key,
            "count": proj.submission_count,
            "limit": proj.max_limit,
            "data": [{"id": s.id, "content": s.payload, "ip": s.visitor_ip, "time": s.timestamp} for s in submissions]
        })
    return jsonify(all_projects)

# 7. CAPTURE ENGINE (External Visitor Data)
@app.route('/v1/receive/<api_key>', methods=['POST'])
def capture(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project or project.submission_count >= project.max_limit:
        return jsonify({"status": "error", "message": "Limit Exceeded"}), 403

    visitor_data = request.json
    new_entry = DataVault(api_key=api_key, payload=visitor_data, visitor_ip=request.remote_addr)
    project.submission_count += 1
    db.session.add(new_entry)
    db.session.commit()
    
    # Fast Email Alert
    threading.Thread(target=send_fast_alert, args=(project.owner.email, visitor_data, project.project_name)).start()
    return jsonify({"status": "success"}), 200

# 8. PAGE ROUTES
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template('dashboard.html')

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
