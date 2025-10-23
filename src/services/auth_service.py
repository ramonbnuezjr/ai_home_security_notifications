"""
Authentication service for user management, JWT tokens, and MFA.
Implements secure authentication with rate limiting and audit logging.
"""

import jwt
import bcrypt
import pyotp
import qrcode
import io
import base64
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, asdict
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User record"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    email: Optional[str] = None
    role: str = "user"  # 'admin', 'moderator', 'user', 'viewer'
    is_active: bool = True
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    failed_login_attempts: int = 0
    last_failed_login: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Session:
    """Session record"""
    id: Optional[int] = None
    user_id: int = 0
    token: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class PasswordPolicy:
    """Password policy validator"""
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against policy.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if cls.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(f"Password must contain at least one special character: {cls.SPECIAL_CHARS}")
        
        return len(errors) == 0, errors


class RateLimiter:
    """Rate limiter for login attempts"""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        """
        Args:
            max_attempts: Maximum login attempts allowed
            window_seconds: Time window in seconds (default: 15 minutes)
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)
        self._lock = Lock()
    
    def is_rate_limited(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier is rate limited.
        
        Returns:
            (is_limited, seconds_until_reset)
        """
        with self._lock:
            now = datetime.now()
            
            # Clean old attempts
            cutoff = now - timedelta(seconds=self.window_seconds)
            self.attempts[identifier] = [
                attempt for attempt in self.attempts[identifier]
                if attempt > cutoff
            ]
            
            # Check if rate limited
            if len(self.attempts[identifier]) >= self.max_attempts:
                oldest_attempt = min(self.attempts[identifier])
                reset_time = oldest_attempt + timedelta(seconds=self.window_seconds)
                seconds_until_reset = int((reset_time - now).total_seconds())
                return True, seconds_until_reset
            
            return False, None
    
    def record_attempt(self, identifier: str):
        """Record a failed login attempt"""
        with self._lock:
            self.attempts[identifier].append(datetime.now())
    
    def reset(self, identifier: str):
        """Reset attempts for an identifier"""
        with self._lock:
            self.attempts[identifier] = []


class AuthService:
    """
    Authentication service with JWT, MFA, and role-based access control.
    """
    
    # Role hierarchy (higher value = more permissions)
    ROLES = {
        'viewer': 1,
        'user': 2,
        'moderator': 3,
        'admin': 4
    }
    
    def __init__(self, database_service, jwt_secret: str, jwt_expiry_hours: int = 24):
        """
        Initialize authentication service.
        
        Args:
            database_service: DatabaseService instance
            jwt_secret: Secret key for JWT signing
            jwt_expiry_hours: JWT token expiry time in hours
        """
        self.db = database_service
        self.jwt_secret = jwt_secret
        self.jwt_expiry_hours = jwt_expiry_hours
        self.rate_limiter = RateLimiter()
        
        # Ensure required tables exist
        self._initialize_auth_tables()
        logger.info("Authentication service initialized")
    
    def _initialize_auth_tables(self):
        """Create authentication tables if they don't exist"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enhance users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    role VARCHAR(50) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    mfa_enabled BOOLEAN DEFAULT 0,
                    mfa_secret VARCHAR(255),
                    failed_login_attempts INTEGER DEFAULT 0,
                    last_failed_login DATETIME,
                    last_login DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token VARCHAR(500) UNIQUE NOT NULL,
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)
            """)
            
            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    username VARCHAR(100),
                    action VARCHAR(100) NOT NULL,
                    resource VARCHAR(255),
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    status VARCHAR(50),
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)
            """)
            
            conn.commit()
            logger.info("Authentication tables initialized")
    
    # ==================== User Management ====================
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        role: str = "user"
    ) -> Tuple[bool, Optional[int], List[str]]:
        """
        Create a new user.
        
        Returns:
            (success, user_id, errors)
        """
        errors = []
        
        # Validate username
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters")
        
        # Validate password
        is_valid, password_errors = PasswordPolicy.validate(password)
        if not is_valid:
            errors.extend(password_errors)
        
        # Validate role
        if role not in self.ROLES:
            errors.append(f"Invalid role. Must be one of: {', '.join(self.ROLES.keys())}")
        
        if errors:
            return False, None, errors
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO users (username, password_hash, email, role, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (username, password_hash, email, role))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"User created: {username} (ID: {user_id}, Role: {role})")
                self._log_audit(user_id, username, "user_created", f"user:{user_id}", None, None, "success")
                
                return True, user_id, []
        
        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg:
                if "username" in error_msg:
                    errors.append("Username already exists")
                elif "email" in error_msg:
                    errors.append("Email already exists")
            else:
                errors.append(f"Failed to create user: {error_msg}")
            
            logger.error(f"Failed to create user {username}: {e}")
            return False, None, errors
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    user = dict(row)
                    # Don't return password hash
                    user.pop('password_hash', None)
                    return user
                
                return None
        
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
        
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[bool, List[str]]:
        """Update user details"""
        errors = []
        
        if role and role not in self.ROLES:
            errors.append(f"Invalid role. Must be one of: {', '.join(self.ROLES.keys())}")
            return False, errors
        
        try:
            updates = []
            params = []
            
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            
            if role is not None:
                updates.append("role = ?")
                params.append(role)
            
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(1 if is_active else 0)
            
            if not updates:
                return True, []
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()
                
                logger.info(f"User {user_id} updated")
                self._log_audit(user_id, None, "user_updated", f"user:{user_id}", None, None, "success")
                
                return True, []
        
        except Exception as e:
            error_msg = f"Failed to update user: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, List[str]]:
        """Change user password"""
        errors = []
        
        # Get user
        user = self.get_user_by_id_with_hash(user_id)
        if not user:
            errors.append("User not found")
            return False, errors
        
        # Verify old password
        if not bcrypt.checkpw(old_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            errors.append("Current password is incorrect")
            self._log_audit(user_id, user['username'], "password_change_failed", f"user:{user_id}", None, None, "failed")
            return False, errors
        
        # Validate new password
        is_valid, password_errors = PasswordPolicy.validate(new_password)
        if not is_valid:
            errors.extend(password_errors)
            return False, errors
        
        # Hash new password
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_hash, user_id))
                conn.commit()
                
                logger.info(f"Password changed for user {user_id}")
                self._log_audit(user_id, user['username'], "password_changed", f"user:{user_id}", None, None, "success")
                
                return True, []
        
        except Exception as e:
            error_msg = f"Failed to change password: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    def get_user_by_id_with_hash(self, user_id: int) -> Optional[Dict]:
        """Get user by ID including password hash (internal use only)"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def delete_user(self, user_id: int) -> Tuple[bool, List[str]]:
        """Delete user (cascades to sessions)"""
        errors = []
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                
                if cursor.rowcount == 0:
                    errors.append("User not found")
                    return False, errors
                
                conn.commit()
                
                logger.info(f"User {user_id} deleted")
                self._log_audit(user_id, None, "user_deleted", f"user:{user_id}", None, None, "success")
                
                return True, []
        
        except Exception as e:
            error_msg = f"Failed to delete user: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    def list_users(
        self,
        page: int = 1,
        limit: int = 50,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Dict], int]:
        """
        List users with pagination and filtering.
        
        Returns:
            (users, total_count)
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                where_clauses = []
                params = []
                
                if role:
                    where_clauses.append("role = ?")
                    params.append(role)
                
                if is_active is not None:
                    where_clauses.append("is_active = ?")
                    params.append(1 if is_active else 0)
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM users WHERE {where_sql}", params)
                total_count = cursor.fetchone()[0]
                
                # Get paginated results
                offset = (page - 1) * limit
                cursor.execute(f"""
                    SELECT id, username, email, role, is_active, mfa_enabled,
                           last_login, created_at, updated_at
                    FROM users WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, params + [limit, offset])
                
                users = [dict(row) for row in cursor.fetchall()]
                
                return users, total_count
        
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return [], 0
    
    # ==================== Authentication ====================
    
    def authenticate(
        self,
        username: str,
        password: str,
        mfa_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict], List[str]]:
        """
        Authenticate user and generate JWT token.
        
        Returns:
            (success, token, user_data, errors)
        """
        errors = []
        
        # Check rate limiting
        is_limited, seconds_until_reset = self.rate_limiter.is_rate_limited(username)
        if is_limited:
            errors.append(f"Too many login attempts. Try again in {seconds_until_reset} seconds")
            self._log_audit(None, username, "login_failed", None, ip_address, user_agent, "rate_limited")
            return False, None, None, errors
        
        # Get user
        user = self.get_user_by_username(username)
        if not user:
            errors.append("Invalid username or password")
            self.rate_limiter.record_attempt(username)
            self._log_audit(None, username, "login_failed", None, ip_address, user_agent, "invalid_credentials")
            return False, None, None, errors
        
        # Check if user is active
        if not user['is_active']:
            errors.append("Account is disabled")
            self._log_audit(user['id'], username, "login_failed", None, ip_address, user_agent, "account_disabled")
            return False, None, None, errors
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            errors.append("Invalid username or password")
            self.rate_limiter.record_attempt(username)
            self._record_failed_login(user['id'])
            self._log_audit(user['id'], username, "login_failed", None, ip_address, user_agent, "invalid_password")
            return False, None, None, errors
        
        # Check MFA if enabled
        if user['mfa_enabled']:
            if not mfa_code:
                # MFA required but not provided - partial success
                return False, None, {'requires_mfa': True, 'user_id': user['id']}, ["MFA code required"]
            
            if not self._verify_mfa_code(user['mfa_secret'], mfa_code):
                errors.append("Invalid MFA code")
                self.rate_limiter.record_attempt(username)
                self._log_audit(user['id'], username, "login_failed", None, ip_address, user_agent, "invalid_mfa")
                return False, None, None, errors
        
        # Authentication successful
        self.rate_limiter.reset(username)
        self._reset_failed_logins(user['id'])
        self._update_last_login(user['id'])
        
        # Generate JWT token
        token = self._generate_jwt(user['id'], user['username'], user['role'])
        
        # Create session
        self._create_session(user['id'], token, ip_address, user_agent)
        
        # Prepare user data (without sensitive info)
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'mfa_enabled': user['mfa_enabled']
        }
        
        logger.info(f"User authenticated: {username} (ID: {user['id']})")
        self._log_audit(user['id'], username, "login_success", None, ip_address, user_agent, "success")
        
        return True, token, user_data, []
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict], List[str]]:
        """
        Verify JWT token and return user data.
        
        Returns:
            (is_valid, user_data, errors)
        """
        errors = []
        
        try:
            # Decode JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if session exists and is valid
            session = self._get_session_by_token(token)
            if not session:
                errors.append("Invalid or expired session")
                return False, None, errors
            
            # Update session activity
            self._update_session_activity(session['id'])
            
            # Get user
            user = self.get_user(payload['user_id'])
            if not user or not user['is_active']:
                errors.append("User not found or inactive")
                return False, None, errors
            
            return True, user, []
        
        except jwt.ExpiredSignatureError:
            errors.append("Token has expired")
            return False, None, errors
        
        except jwt.InvalidTokenError:
            errors.append("Invalid token")
            return False, None, errors
        
        except Exception as e:
            errors.append(f"Token verification failed: {str(e)}")
            logger.error(f"Token verification error: {e}")
            return False, None, errors
    
    def logout(self, token: str) -> bool:
        """Logout user by invalidating session"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                
                logger.info("User logged out")
                return True
        
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            return False
    
    def logout_all_sessions(self, user_id: int) -> bool:
        """Logout user from all sessions"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
                conn.commit()
                
                logger.info(f"All sessions terminated for user {user_id}")
                self._log_audit(user_id, None, "logout_all_sessions", f"user:{user_id}", None, None, "success")
                
                return True
        
        except Exception as e:
            logger.error(f"Failed to logout all sessions: {e}")
            return False
    
    # ==================== Multi-Factor Authentication ====================
    
    def enable_mfa(self, user_id: int) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
        """
        Enable MFA for user.
        
        Returns:
            (success, secret, qr_code_data_url, errors)
        """
        errors = []
        
        try:
            # Generate MFA secret
            secret = pyotp.random_base32()
            
            # Get user
            user = self.get_user(user_id)
            if not user:
                errors.append("User not found")
                return False, None, None, errors
            
            # Generate provisioning URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user['username'],
                issuer_name="AI Home Security"
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to data URL
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data_url = f"data:image/png;base64,{qr_code_data}"
            
            # Save secret (but don't enable MFA yet - user must verify)
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET mfa_secret = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (secret, user_id))
                conn.commit()
            
            logger.info(f"MFA secret generated for user {user_id}")
            
            return True, secret, qr_code_data_url, []
        
        except Exception as e:
            error_msg = f"Failed to enable MFA: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, None, None, errors
    
    def verify_and_enable_mfa(self, user_id: int, mfa_code: str) -> Tuple[bool, List[str]]:
        """Verify MFA code and enable MFA for user"""
        errors = []
        
        try:
            # Get user with secret
            user = self.get_user_by_id_with_hash(user_id)
            if not user or not user.get('mfa_secret'):
                errors.append("MFA not initialized")
                return False, errors
            
            # Verify code
            if not self._verify_mfa_code(user['mfa_secret'], mfa_code):
                errors.append("Invalid MFA code")
                return False, errors
            
            # Enable MFA
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET mfa_enabled = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
            
            logger.info(f"MFA enabled for user {user_id}")
            self._log_audit(user_id, user['username'], "mfa_enabled", f"user:{user_id}", None, None, "success")
            
            return True, []
        
        except Exception as e:
            error_msg = f"Failed to verify MFA: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    def disable_mfa(self, user_id: int, password: str) -> Tuple[bool, List[str]]:
        """Disable MFA for user (requires password confirmation)"""
        errors = []
        
        try:
            # Get user
            user = self.get_user_by_id_with_hash(user_id)
            if not user:
                errors.append("User not found")
                return False, errors
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                errors.append("Invalid password")
                self._log_audit(user_id, user['username'], "mfa_disable_failed", f"user:{user_id}", None, None, "invalid_password")
                return False, errors
            
            # Disable MFA
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET mfa_enabled = 0, mfa_secret = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
            
            logger.info(f"MFA disabled for user {user_id}")
            self._log_audit(user_id, user['username'], "mfa_disabled", f"user:{user_id}", None, None, "success")
            
            return True, []
        
        except Exception as e:
            error_msg = f"Failed to disable MFA: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    def _verify_mfa_code(self, secret: str, code: str) -> bool:
        """Verify TOTP MFA code"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)  # Allow 1 time step tolerance
        except Exception as e:
            logger.error(f"MFA verification error: {e}")
            return False
    
    # ==================== Authorization ====================
    
    def check_permission(self, user: Dict, required_role: str) -> bool:
        """
        Check if user has required role or higher.
        
        Args:
            user: User dict with 'role' field
            required_role: Required role level
            
        Returns:
            True if user has permission
        """
        user_role = user.get('role', 'viewer')
        user_level = self.ROLES.get(user_role, 0)
        required_level = self.ROLES.get(required_role, 0)
        
        return user_level >= required_level
    
    # ==================== Helper Methods ====================
    
    def _generate_jwt(self, user_id: int, username: str, role: str) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiry_hours),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def _create_session(
        self,
        user_id: int,
        token: str,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Create session record"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                expires_at = datetime.now() + timedelta(hours=self.jwt_expiry_hours)
                
                cursor.execute("""
                    INSERT INTO sessions (user_id, token, ip_address, user_agent, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, token, ip_address, user_agent, expires_at))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
    
    def _get_session_by_token(self, token: str) -> Optional[Dict]:
        """Get session by token"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE token = ? AND expires_at > datetime('now')
                """, (token,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def _update_session_activity(self, session_id: int):
        """Update session last activity timestamp"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (session_id,))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    def _record_failed_login(self, user_id: int):
        """Record failed login attempt"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = failed_login_attempts + 1,
                        last_failed_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to record failed login: {e}")
    
    def _reset_failed_logins(self, user_id: int):
        """Reset failed login attempts"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = 0, last_failed_login = NULL
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to reset failed logins: {e}")
    
    def _update_last_login(self, user_id: int):
        """Update last login timestamp"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
    
    def _log_audit(
        self,
        user_id: Optional[int],
        username: Optional[str],
        action: str,
        resource: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        status: str,
        details: Optional[str] = None
    ):
        """Log audit event"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_log (
                        user_id, username, action, resource, ip_address,
                        user_agent, status, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, action, resource, ip_address, user_agent, status, details))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    # ==================== Session Management ====================
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired sessions")
                
                return deleted_count
        
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0
    
    def get_active_sessions(self, user_id: int) -> List[Dict]:
        """Get all active sessions for a user"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, ip_address, user_agent, created_at, last_activity, expires_at
                    FROM sessions 
                    WHERE user_id = ? AND expires_at > datetime('now')
                    ORDER BY last_activity DESC
                """, (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def revoke_session(self, session_id: int, user_id: int) -> bool:
        """Revoke a specific session"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sessions 
                    WHERE id = ? AND user_id = ?
                """, (session_id, user_id))
                conn.commit()
                
                return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")
            return False




