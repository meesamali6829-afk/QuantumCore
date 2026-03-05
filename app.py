import os, uuid, datetime, requests, re, smtplib, random, logging
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# --- ENGINE CONFIG ---
app = Flask(__name__, template_folder='templates')
app.secret_key = "QUANTUM_FINAL_BOSS_999"
app.permanent_session_lifetime = datetime.timedelta(days=36500) 
CORS(app)

# --- DATABASE (Render Permanent Path) ---
# SQLite file ko absolute path dena zaroori hai Render par
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'quantum_core_master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
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
    payload = db.Column(db.JSON) 
    visitor_ip = db.Column(db.String(50))
    visitor_loc = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# --- ROUTES ---
@app.route('/')
def home():
    """Templates folder se index.html uthayega [cite: 2026-03-05]"""
    try:
        return render_template('index.html')
    except:
        return jsonify({"status": "QuantumCore Engine Live", "msg": "index.html missing in templates/"})

@app.route('/api/vault/live')
def get_vault():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    entries = DataEntry.query.join(Project).filter(Project.user_id == user_id).order_by(DataEntry.timestamp.desc()).all()
    return jsonify([{"project": d.project.name, "content": d.payload, "ip": d.visitor_ip, "location": d.visitor_loc, "time": d.timestamp.strftime("%b %d, %H:%M")} for d in entries])

@app.route('/v1/receive/<api_key>', methods=['POST'])
def capture(api_key):
    project = Project.query.filter_by(api_key=api_key).first_or_404()
    entry = DataEntry(project_id=project.id, payload=request.json, visitor_ip=request.remote_addr, visitor_loc="Remote-Visitor")
    project.total_hits += 1
    db.session.add(entry)
    db.session.commit()
    return jsonify({"status": "Captured", "total": project.total_hits}), 200

# --- ENGINE START ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Local run ke liye [cite: 2026-03-05]
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
