from flask import Blueprint, request, jsonify
import json
import os
import hashlib

admin_bp = Blueprint('admin', __name__)

USERS_DIR = 'users'

def get_user(username):
    filename = f"{username}.json"
    filepath = os.path.join(USERS_DIR, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def update_user(username, data):
    user_data = get_user(username)
    if not user_data:
        return False
    
    user_data.update(data)
    
    filename = f"{username}.json"
    filepath = os.path.join(USERS_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return True

@admin_bp.route('/admin/update_user', methods=['POST'])
def admin_update_user():
    admin_key = request.headers.get('X-Admin-Key')
    username = request.json.get('username')
    updates = request.json.get('updates', {})
    
    if not admin_key:
        return jsonify({'error': 'Admin key required'}), 401
    
    user_data = get_user(username)
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    expected_key = hashlib.sha256(f"admin_key_{username}".encode()).hexdigest()
    
    if admin_key != expected_key:
        return jsonify({'error': 'Invalid admin key'}), 403
    
    if update_user(username, updates):
        return jsonify({'message': 'User updated successfully'})
    else:
        return jsonify({'error': 'Failed to update user'}), 500

@admin_bp.route('/admin/activate_account', methods=['POST'])
def admin_activate_account():
    admin_key = request.headers.get('X-Admin-Key')
    username = request.json.get('username')
    
    if not admin_key:
        return jsonify({'error': 'Admin key required'}), 401
    
    user_data = get_user(username)
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    expected_key = hashlib.sha256(f"admin_key_{username}".encode()).hexdigest()
    
    if admin_key != expected_key:
        return jsonify({'error': 'Invalid admin key'}), 403
    
    updates = {
        'is_active': True,
        'features': {
            'change_email': True,
            'display_email': True,
            'custom_otp': True,
            'delete_email': True,
            'fake_otp': True,
            'fake_email': True,
            'token_user': True
        }
    }
    
    if update_user(username, updates):
        return jsonify({'message': 'Account activated successfully'})
    else:
        return jsonify({'error': 'Failed to activate account'}), 500
