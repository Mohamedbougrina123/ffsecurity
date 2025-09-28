from admin import admin_bp
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import hashlib
import jwt
import datetime
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = 'mohamed'
app.config['JWT_SECRET'] = 'mohamed'

USERS_DIR = 'users'
TOKENS_DIR = 'tokens'
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 300

login_attempts = {}
app.register_blueprint(admin_bp)
def create_directories():
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user_file(username, password):
    user_data = {
        'username': username,
        'password_hash': hash_password(password),
        'is_active': False,
        'email': '',
        'custom_otp': '',
        'fake_email': '',
        'fake_otp': '',
        'user_token': '',
        'created_at': datetime.datetime.now().isoformat(),
        'last_login': None,
        'session_id': None,
        'features': {
            'change_email': False,
            'display_email': False,
            'custom_otp': False,
            'delete_email': False,
            'fake_otp': False,
            'fake_email': False,
            'token_user': False
        }
    }
    
    filename = f"{username}.json"
    filepath = os.path.join(USERS_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return user_data

def create_jwt_token(user_data):
    payload = {
        'username': user_data['username'],
        'is_active': user_data['is_active'],
        'features': user_data['features'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    
    token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
    return token

def save_token(username, token):
    filename = f"{username}_token.json"
    filepath = os.path.join(TOKENS_DIR, filename)
    
    token_data = {
        'token': token,
        'created_at': datetime.datetime.now().isoformat()
    }
    
    with open(filepath, 'w') as f:
        json.dump(token_data, f, indent=4)

def get_user(username):
    filename = f"{username}.json"
    filepath = os.path.join(USERS_DIR, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def update_user_session(username, session_id):
    user_data = get_user(username)
    if user_data:
        user_data['session_id'] = session_id
        user_data['last_login'] = datetime.datetime.now().isoformat()
        
        filename = f"{username}.json"
        filepath = os.path.join(USERS_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(user_data, f, indent=4)

def check_login_attempts(username, ip):
    key = f"{username}_{ip}"
    now = time.time()
    
    if key not in login_attempts:
        login_attempts[key] = {'count': 0, 'time': now}
        return True
    
    attempts = login_attempts[key]
    
    if now - attempts['time'] > LOGIN_TIMEOUT:
        login_attempts[key] = {'count': 1, 'time': now}
        return True
    
    if attempts['count'] >= MAX_LOGIN_ATTEMPTS:
        return False
    
    attempts['count'] += 1
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        
        user_data = get_user(session['username'])
        if not user_data or user_data['session_id'] != session['session_id']:
            session.clear()
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if get_user(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    user_data = create_user_file(username, password)
    token = create_jwt_token(user_data)
    save_token(username, token)
    
    return jsonify({
        'message': 'Account created successfully',
        'username': username,
        'is_active': False
    })

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    ip = request.remote_addr
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if not check_login_attempts(username, ip):
        return jsonify({'error': 'Too many login attempts. Try again later.'}), 429
    
    user_data = get_user(username)
    
    if not user_data or user_data['password_hash'] != hash_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session_id = hashlib.sha256(f"{username}{datetime.datetime.now()}".encode()).hexdigest()
    
    if user_data['session_id']:
        session.clear()
    
    update_user_session(username, session_id)
    
    session['username'] = username
    session['session_id'] = session_id
    
    token_data_file = os.path.join(TOKENS_DIR, f"{username}_token.json")
    with open(token_data_file, 'r') as f:
        token_data = json.load(f)
    
    return jsonify({
        'message': 'Login successful',
        'token': token_data['token'],
        'user_data': user_data
    })

@app.route('/dashboard')
@login_required
def dashboard():
    user_data = get_user(session['username'])
    return render_template('dashboard.html', user_data=user_data)

@app.route('/api/account_info', methods=['POST'])
def account_info():
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user_data = get_user(username)
    
    if not user_data or user_data['password_hash'] != hash_password(password):
        return jsonify({'error': 'No account found with these credentials'}), 404
    
    return jsonify({
        'account_info': user_data
    })

@app.route('/explain')
def explain():
    return render_template('explain.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        update_user_session(session['username'], None)
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    create_directories()
    app.run(debug=True)
