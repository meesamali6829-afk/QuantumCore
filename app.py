From flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import uuid, datetime, smtplib, threading, time, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "QUANTUM_CORE_SUPER_SECRET_KEY_99" 
CORS(app)

# 1. DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quantumcore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. SECURE MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100))
    api_key = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_count = db.Column(db.Integer, default=0)

class DataVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    payload = db.Column(db.JSON) 
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 3. HIGH-SPEED EMAIL ENGINE (MEESAM ALI ENGINE)
def send_quantum_alert(receiver_email, p_name, data_payload):
    SENDER = "meesamali6829@gmail.com"
    # AAPKA NAYA APP PASSWORD YAHAN DAL DIYA HAI
    PASSWORD = "hbrw 2p4m 3c6k lhyc" 
    
    msg = MIMEMultipart()
    msg['From'] = f"QuantumCore <{SENDER}>"
    msg['To'] = receiver_email
    msg['Subject'] = f"🚀 New Submission: {p_name}"
    
    content = f"Bhai Meesam, Naya data aaya hai:\n\nProject: {p_name}\n"
    content += "="*30 + "\n"
    for key, value in data_payload.items():
        content += f"➤ {key.upper()}: {value}\n"
    content += "="*30 + "\n"
    content += "Powered by QuantumCore Vault Engine"
    
    msg.attach(MIMEText(content, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Email Error: {e}")

# 4. SECURITY RULES (Anti-Spam)
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# 5. ROUTES
@app.route('/')
def index():
    return render_template('index.html')

# NAYA ROUTE: User apni marzi ka project name banaye
@app.route('/api/create-project', methods=['POST'])
def create_project():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Pehle login karein"}), 401
    
    data = request.json
    p_name = data.get('project_name', 'Unnamed Project')
    
    # Unique API Key banana
    new_key = "QC-" + str(uuid.uuid4())[:8].upper()
    
    new_project = Project(
        project_name=p_name,
        api_key=new_key,
        user_id=session['user_id']
    )
    db.session.add(new_project)
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "message": f"Project '{p_name}' created!",
        "api_key": new_key
    })

@app.route('/auth/process', methods=['POST'])
def process_auth():
    data = request.json
    action = data.get('action')
    email = data.get('email').lower().strip()
    password = data.get('password')

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Bhai, sahi email dalo!"}), 400
    
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Security Rule: Password 6 chars se bada rakho"}), 400

    if action == 'register':
        if User.query.filter_by(email=email).first():
            return jsonify({"status": "error", "message": "Email pehle se register hai!"}), 400
        
        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Account Verified & Secured!"})

    elif action == 'login':
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return jsonify({"status": "success", "message": "Welcome back to QuantumCore!"})
        return jsonify({"status": "error", "message": "Invalid Login Details"}), 401

# GLOBAL DATA RECEIVER (User ki website ka sara data yahan aayega)
@app.route('/v1/receive/<api_key>', methods=['POST'])
def receive_data(api_key):
    project = Project.query.filter_by(api_key=api_key).first()
    if not project:
        return jsonify({"error": "Unauthorized API Key"}), 403

    data = request.json
    project.submission_count += 1
    
    # Quantum Vault mein save karna
    new_entry = DataVault(project_id=project.id, payload=data)
    db.session.add(new_entry)
    db.session.commit()

    # 1 Second Alert (Non-blocking)
    threading.Thread(target=send_quantum_alert, args=(project.owner.email, project.project_name, data)).start()

    return jsonify({"status": "Success", "vault": "Encrypted"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    