"""
Authentication API endpoints.
Handles login, logout, registration, MFA, and session management.
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, g
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def get_client_info() -> Tuple[Optional[str], Optional[str]]:
    """Get client IP address and user agent"""
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    return ip_address, user_agent


def get_auth_service():
    """Get auth service from app config"""
    return current_app.config.get('AUTH_SERVICE')


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        auth_service = get_auth_service()
        
        is_valid, user, errors = auth_service.verify_token(token)
        
        if not is_valid:
            return jsonify({'error': 'Invalid or expired token', 'details': errors}), 401
        
        # Store user in request context
        g.current_user = user
        g.current_token = token
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(required_role: str):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            auth_service = get_auth_service()
            user = g.current_user
            
            if not auth_service.check_permission(user, required_role):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'required_role': required_role,
                    'your_role': user.get('role', 'unknown')
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


# ==================== Public Endpoints ====================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint.
    
    Request JSON:
        username: string (required)
        password: string (required)
        mfa_code: string (optional, required if MFA enabled)
    
    Response:
        Success: {success: true, token: string, user: object}
        MFA Required: {success: false, requires_mfa: true, user_id: int}
        Error: {success: false, errors: [string]}
    """
    try:
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        mfa_code = data.get('mfa_code')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'errors': ['Username and password are required']
            }), 400
        
        ip_address, user_agent = get_client_info()
        auth_service = get_auth_service()
        
        success, token, user_data, errors = auth_service.authenticate(
            username=username,
            password=password,
            mfa_code=mfa_code,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if success:
            return jsonify({
                'success': True,
                'token': token,
                'user': user_data
            }), 200
        
        # Check if MFA is required
        if user_data and user_data.get('requires_mfa'):
            return jsonify({
                'success': False,
                'requires_mfa': True,
                'user_id': user_data.get('user_id')
            }), 200
        
        return jsonify({
            'success': False,
            'errors': errors
        }), 401
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'errors': ['An error occurred during login']
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register new user (admin only in production, open during setup).
    
    Request JSON:
        username: string (required)
        password: string (required)
        email: string (optional)
        role: string (optional, default: 'user')
    
    Response:
        {success: bool, user_id: int, errors: [string]}
    """
    try:
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'user')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'errors': ['Username and password are required']
            }), 400
        
        # Check if this is first user (no auth required)
        auth_service = get_auth_service()
        users, total = auth_service.list_users(limit=1)
        
        is_first_user = total == 0
        
        # If not first user, require admin auth
        if not is_first_user:
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    'success': False,
                    'errors': ['Admin authentication required']
                }), 401
            
            token = auth_header.split(' ')[1]
            is_valid, user, errors = auth_service.verify_token(token)
            
            if not is_valid or not auth_service.check_permission(user, 'admin'):
                return jsonify({
                    'success': False,
                    'errors': ['Admin privileges required']
                }), 403
        else:
            # First user gets admin role automatically
            role = 'admin'
            logger.info("Creating first user with admin role")
        
        success, user_id, errors = auth_service.create_user(
            username=username,
            password=password,
            email=email,
            role=role
        )
        
        if success:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'is_first_user': is_first_user
            }), 201
        
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'errors': ['An error occurred during registration']
        }), 500


@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify():
    """
    Verify JWT token and return user info.
    
    Response:
        {success: true, user: object}
    """
    return jsonify({
        'success': True,
        'user': g.current_user
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout current session.
    
    Response:
        {success: bool}
    """
    try:
        auth_service = get_auth_service()
        success = auth_service.logout(g.current_token)
        
        return jsonify({'success': success}), 200
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during logout'
        }), 500


# ==================== User Management ====================

@auth_bp.route('/users', methods=['GET'])
@require_role('admin')
def list_users():
    """
    List all users (admin only).
    
    Query params:
        page: int (default: 1)
        limit: int (default: 50)
        role: string (optional filter)
        is_active: bool (optional filter)
    
    Response:
        {users: [object], total: int, page: int, limit: int}
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        role = request.args.get('role')
        is_active = request.args.get('is_active')
        
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
        auth_service = get_auth_service()
        users, total = auth_service.list_users(
            page=page,
            limit=limit,
            role=role,
            is_active=is_active
        )
        
        return jsonify({
            'users': users,
            'total': total,
            'page': page,
            'limit': limit
        }), 200
    
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({'error': 'Failed to list users'}), 500


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """
    Get user by ID.
    Users can only view their own profile unless they're admin.
    
    Response:
        {user: object}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        # Check permissions
        if current_user['id'] != user_id and not auth_service.check_permission(current_user, 'admin'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        user = auth_service.get_user(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user}), 200
    
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': 'Failed to get user'}), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """
    Update user.
    Users can only update their own profile (email only).
    Admins can update any user (email, role, is_active).
    
    Request JSON:
        email: string (optional)
        role: string (optional, admin only)
        is_active: bool (optional, admin only)
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        # Check permissions
        is_admin = auth_service.check_permission(current_user, 'admin')
        
        if current_user['id'] != user_id and not is_admin:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')
        is_active = data.get('is_active')
        
        # Non-admins can only update email
        if not is_admin:
            role = None
            is_active = None
        
        success, errors = auth_service.update_user(
            user_id=user_id,
            email=email,
            role=role,
            is_active=is_active
        )
        
        if success:
            return jsonify({'success': True}), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to update user']
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id):
    """
    Delete user (admin only).
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        
        # Prevent self-deletion
        if current_user['id'] == user_id:
            return jsonify({
                'success': False,
                'errors': ['Cannot delete your own account']
            }), 400
        
        auth_service = get_auth_service()
        success, errors = auth_service.delete_user(user_id)
        
        if success:
            return jsonify({'success': True}), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to delete user']
        }), 500


@auth_bp.route('/users/<int:user_id>/password', methods=['POST'])
@require_auth
def change_password(user_id):
    """
    Change user password.
    Users can only change their own password.
    
    Request JSON:
        old_password: string (required)
        new_password: string (required)
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        
        # Users can only change their own password
        if current_user['id'] != user_id:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({
                'success': False,
                'errors': ['Old and new password are required']
            }), 400
        
        auth_service = get_auth_service()
        success, errors = auth_service.change_password(
            user_id=user_id,
            old_password=old_password,
            new_password=new_password
        )
        
        if success:
            return jsonify({'success': True}), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to change password']
        }), 500


# ==================== Multi-Factor Authentication ====================

@auth_bp.route('/mfa/enable', methods=['POST'])
@require_auth
def enable_mfa():
    """
    Enable MFA for current user.
    
    Response:
        {success: bool, secret: string, qr_code: string, errors: [string]}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        success, secret, qr_code, errors = auth_service.enable_mfa(current_user['id'])
        
        if success:
            return jsonify({
                'success': True,
                'secret': secret,
                'qr_code': qr_code,
                'message': 'Scan QR code with authenticator app and verify with code'
            }), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Enable MFA error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to enable MFA']
        }), 500


@auth_bp.route('/mfa/verify', methods=['POST'])
@require_auth
def verify_mfa():
    """
    Verify MFA code and complete MFA setup.
    
    Request JSON:
        mfa_code: string (required)
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        data = request.get_json()
        
        mfa_code = data.get('mfa_code')
        
        if not mfa_code:
            return jsonify({
                'success': False,
                'errors': ['MFA code is required']
            }), 400
        
        auth_service = get_auth_service()
        success, errors = auth_service.verify_and_enable_mfa(
            user_id=current_user['id'],
            mfa_code=mfa_code
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'MFA enabled successfully'
            }), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Verify MFA error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to verify MFA']
        }), 500


@auth_bp.route('/mfa/disable', methods=['POST'])
@require_auth
def disable_mfa():
    """
    Disable MFA for current user.
    
    Request JSON:
        password: string (required for confirmation)
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        data = request.get_json()
        
        password = data.get('password')
        
        if not password:
            return jsonify({
                'success': False,
                'errors': ['Password is required']
            }), 400
        
        auth_service = get_auth_service()
        success, errors = auth_service.disable_mfa(
            user_id=current_user['id'],
            password=password
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'MFA disabled successfully'
            }), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Disable MFA error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to disable MFA']
        }), 500


# ==================== Session Management ====================

@auth_bp.route('/sessions', methods=['GET'])
@require_auth
def get_sessions():
    """
    Get all active sessions for current user.
    
    Response:
        {sessions: [object]}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        sessions = auth_service.get_active_sessions(current_user['id'])
        
        return jsonify({'sessions': sessions}), 200
    
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return jsonify({'error': 'Failed to get sessions'}), 500


@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@require_auth
def revoke_session(session_id):
    """
    Revoke a specific session.
    
    Response:
        {success: bool}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        success = auth_service.revoke_session(session_id, current_user['id'])
        
        if success:
            return jsonify({'success': True}), 200
        
        return jsonify({
            'success': False,
            'error': 'Session not found or already revoked'
        }), 404
    
    except Exception as e:
        logger.error(f"Revoke session error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to revoke session'
        }), 500


@auth_bp.route('/sessions/logout-all', methods=['POST'])
@require_auth
def logout_all():
    """
    Logout from all sessions.
    
    Response:
        {success: bool}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        success = auth_service.logout_all_sessions(current_user['id'])
        
        return jsonify({'success': success}), 200
    
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to logout from all sessions'
        }), 500


# ==================== Utility ====================

@auth_bp.route('/check-first-user', methods=['GET'])
def check_first_user():
    """
    Check if this is the first user (for initial setup).
    
    Response:
        {is_first_user: bool}
    """
    try:
        auth_service = get_auth_service()
        users, total = auth_service.list_users(limit=1)
        
        return jsonify({'is_first_user': total == 0}), 200
    
    except Exception as e:
        logger.error(f"Check first user error: {e}")
        return jsonify({'error': 'Failed to check first user'}), 500




