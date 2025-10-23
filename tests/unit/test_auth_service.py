"""
Unit tests for AuthService - Epic 6
Tests user management, authentication, MFA, sessions, and authorization.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
import tempfile
import os
from datetime import datetime, timedelta
import jwt

from src.services.database_service import DatabaseService
from src.services.auth_service import AuthService, PasswordPolicy, RateLimiter


class TestPasswordPolicy(unittest.TestCase):
    """Test password policy validation"""
    
    def test_valid_password(self):
        """Test valid password passes validation"""
        password = "SecurePass123!"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_short_password(self):
        """Test password too short fails"""
        password = "Short1!"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertFalse(is_valid)
        self.assertTrue(any("at least 8 characters" in e for e in errors))
    
    def test_no_uppercase(self):
        """Test password without uppercase fails"""
        password = "securepass123!"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertFalse(is_valid)
        self.assertTrue(any("uppercase" in e for e in errors))
    
    def test_no_lowercase(self):
        """Test password without lowercase fails"""
        password = "SECUREPASS123!"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertFalse(is_valid)
        self.assertTrue(any("lowercase" in e for e in errors))
    
    def test_no_digit(self):
        """Test password without digit fails"""
        password = "SecurePass!"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertFalse(is_valid)
        self.assertTrue(any("digit" in e for e in errors))
    
    def test_no_special_char(self):
        """Test password without special character fails"""
        password = "SecurePass123"
        is_valid, errors = PasswordPolicy.validate(password)
        self.assertFalse(is_valid)
        self.assertTrue(any("special character" in e for e in errors))


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter functionality"""
    
    def setUp(self):
        self.limiter = RateLimiter(max_attempts=3, window_seconds=60)
    
    def test_not_rate_limited_initially(self):
        """Test identifier is not rate limited initially"""
        is_limited, seconds = self.limiter.is_rate_limited("test_user")
        self.assertFalse(is_limited)
        self.assertIsNone(seconds)
    
    def test_rate_limiting_after_max_attempts(self):
        """Test rate limiting activates after max attempts"""
        identifier = "test_user"
        
        # Record max attempts
        for _ in range(3):
            self.limiter.record_attempt(identifier)
        
        # Should now be rate limited
        is_limited, seconds = self.limiter.is_rate_limited(identifier)
        self.assertTrue(is_limited)
        self.assertIsNotNone(seconds)
        self.assertGreater(seconds, 0)
    
    def test_reset_clears_attempts(self):
        """Test reset clears rate limit"""
        identifier = "test_user"
        
        # Record attempts
        for _ in range(3):
            self.limiter.record_attempt(identifier)
        
        # Reset
        self.limiter.reset(identifier)
        
        # Should no longer be rate limited
        is_limited, seconds = self.limiter.is_rate_limited(identifier)
        self.assertFalse(is_limited)


class TestAuthService(unittest.TestCase):
    """Test AuthService functionality"""
    
    def setUp(self):
        """Set up test database and auth service"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Initialize services
        self.db_service = DatabaseService(db_path=self.db_path)
        self.jwt_secret = "test-secret-key-12345"
        self.auth_service = AuthService(
            database_service=self.db_service,
            jwt_secret=self.jwt_secret,
            jwt_expiry_hours=24
        )
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    # ==================== User Management Tests ====================
    
    def test_create_user_success(self):
        """Test successful user creation"""
        success, user_id, errors = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user_id)
        self.assertEqual(len(errors), 0)
    
    def test_create_user_invalid_password(self):
        """Test user creation with invalid password fails"""
        success, user_id, errors = self.auth_service.create_user(
            username="testuser",
            password="weak",
            email="test@example.com",
            role="user"
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_id)
        self.assertGreater(len(errors), 0)
    
    def test_create_user_duplicate_username(self):
        """Test creating user with duplicate username fails"""
        # Create first user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test1@example.com",
            role="user"
        )
        
        # Try to create duplicate
        success, user_id, errors = self.auth_service.create_user(
            username="testuser",
            password="SecurePass456!",
            email="test2@example.com",
            role="user"
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_id)
        self.assertTrue(any("already exists" in e.lower() for e in errors))
    
    def test_create_user_invalid_role(self):
        """Test creating user with invalid role fails"""
        success, user_id, errors = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="superadmin"
        )
        
        self.assertFalse(success)
        self.assertTrue(any("Invalid role" in e for e in errors))
    
    def test_get_user(self):
        """Test getting user by ID"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Get user
        user = self.auth_service.get_user(user_id)
        
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        self.assertEqual(user['email'], "test@example.com")
        self.assertNotIn('password_hash', user)  # Should not return password
    
    def test_get_user_by_username(self):
        """Test getting user by username"""
        # Create user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Get user
        user = self.auth_service.get_user_by_username("testuser")
        
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        self.assertIn('password_hash', user)  # Internal method returns hash
    
    def test_update_user(self):
        """Test updating user details"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Update user
        success, errors = self.auth_service.update_user(
            user_id=user_id,
            email="newemail@example.com",
            role="moderator"
        )
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify update
        user = self.auth_service.get_user(user_id)
        self.assertEqual(user['email'], "newemail@example.com")
        self.assertEqual(user['role'], "moderator")
    
    def test_delete_user(self):
        """Test deleting user"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Delete user
        success, errors = self.auth_service.delete_user(user_id)
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify deletion
        user = self.auth_service.get_user(user_id)
        self.assertIsNone(user)
    
    def test_list_users(self):
        """Test listing users"""
        # Create multiple users
        for i in range(5):
            self.auth_service.create_user(
                username=f"user{i}",
                password="SecurePass123!",
                email=f"user{i}@example.com",
                role="user"
            )
        
        # List users
        users, total = self.auth_service.list_users(limit=10)
        
        self.assertEqual(total, 5)
        self.assertEqual(len(users), 5)
    
    def test_change_password_success(self):
        """Test successful password change"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="OldPass123!",
            email="test@example.com",
            role="user"
        )
        
        # Change password
        success, errors = self.auth_service.change_password(
            user_id=user_id,
            old_password="OldPass123!",
            new_password="NewPass456!"
        )
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
    
    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password fails"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="OldPass123!",
            email="test@example.com",
            role="user"
        )
        
        # Try to change with wrong old password
        success, errors = self.auth_service.change_password(
            user_id=user_id,
            old_password="WrongPass123!",
            new_password="NewPass456!"
        )
        
        self.assertFalse(success)
        self.assertTrue(any("incorrect" in e.lower() for e in errors))
    
    # ==================== Authentication Tests ====================
    
    def test_authenticate_success(self):
        """Test successful authentication"""
        # Create user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Authenticate
        success, token, user_data, errors = self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(token)
        self.assertIsNotNone(user_data)
        self.assertEqual(len(errors), 0)
        self.assertEqual(user_data['username'], "testuser")
    
    def test_authenticate_invalid_username(self):
        """Test authentication with invalid username fails"""
        success, token, user_data, errors = self.auth_service.authenticate(
            username="nonexistent",
            password="SecurePass123!"
        )
        
        self.assertFalse(success)
        self.assertIsNone(token)
        self.assertIsNone(user_data)
        self.assertGreater(len(errors), 0)
    
    def test_authenticate_invalid_password(self):
        """Test authentication with invalid password fails"""
        # Create user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Try wrong password
        success, token, user_data, errors = self.auth_service.authenticate(
            username="testuser",
            password="WrongPass123!"
        )
        
        self.assertFalse(success)
        self.assertIsNone(token)
        self.assertIsNone(user_data)
        self.assertGreater(len(errors), 0)
    
    def test_authenticate_inactive_user(self):
        """Test authentication with inactive user fails"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Deactivate user
        self.auth_service.update_user(user_id, is_active=False)
        
        # Try to authenticate
        success, token, user_data, errors = self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        self.assertFalse(success)
        self.assertTrue(any("disabled" in e.lower() for e in errors))
    
    def test_verify_token_success(self):
        """Test successful token verification"""
        # Create and authenticate user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        _, token, _, _ = self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        # Verify token
        is_valid, user_data, errors = self.auth_service.verify_token(token)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(user_data)
        self.assertEqual(len(errors), 0)
    
    def test_verify_token_invalid(self):
        """Test verification of invalid token fails"""
        invalid_token = "invalid.token.here"
        
        is_valid, user_data, errors = self.auth_service.verify_token(invalid_token)
        
        self.assertFalse(is_valid)
        self.assertIsNone(user_data)
        self.assertGreater(len(errors), 0)
    
    def test_logout(self):
        """Test logout invalidates session"""
        # Create and authenticate user
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        _, token, _, _ = self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        # Logout
        success = self.auth_service.logout(token)
        self.assertTrue(success)
        
        # Token should no longer be valid
        is_valid, _, _ = self.auth_service.verify_token(token)
        self.assertFalse(is_valid)
    
    # ==================== MFA Tests ====================
    
    def test_enable_mfa(self):
        """Test enabling MFA"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        # Enable MFA
        success, secret, qr_code, errors = self.auth_service.enable_mfa(user_id)
        
        self.assertTrue(success)
        self.assertIsNotNone(secret)
        self.assertIsNotNone(qr_code)
        self.assertEqual(len(errors), 0)
        self.assertIn("data:image/png;base64,", qr_code)
    
    def test_disable_mfa(self):
        """Test disabling MFA"""
        # Create user and enable MFA
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        success, secret, _, _ = self.auth_service.enable_mfa(user_id)
        
        # Generate valid MFA code and enable it
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()
        self.auth_service.verify_and_enable_mfa(user_id, code)
        
        # Disable MFA
        success, errors = self.auth_service.disable_mfa(user_id, "SecurePass123!")
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
    
    # ==================== Authorization Tests ====================
    
    def test_check_permission_admin(self):
        """Test admin has all permissions"""
        user = {'role': 'admin'}
        
        self.assertTrue(self.auth_service.check_permission(user, 'viewer'))
        self.assertTrue(self.auth_service.check_permission(user, 'user'))
        self.assertTrue(self.auth_service.check_permission(user, 'moderator'))
        self.assertTrue(self.auth_service.check_permission(user, 'admin'))
    
    def test_check_permission_user(self):
        """Test user has limited permissions"""
        user = {'role': 'user'}
        
        self.assertTrue(self.auth_service.check_permission(user, 'viewer'))
        self.assertTrue(self.auth_service.check_permission(user, 'user'))
        self.assertFalse(self.auth_service.check_permission(user, 'moderator'))
        self.assertFalse(self.auth_service.check_permission(user, 'admin'))
    
    def test_check_permission_viewer(self):
        """Test viewer has minimal permissions"""
        user = {'role': 'viewer'}
        
        self.assertTrue(self.auth_service.check_permission(user, 'viewer'))
        self.assertFalse(self.auth_service.check_permission(user, 'user'))
        self.assertFalse(self.auth_service.check_permission(user, 'moderator'))
        self.assertFalse(self.auth_service.check_permission(user, 'admin'))
    
    # ==================== Session Management Tests ====================
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        # Create user and authenticate
        self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        # Run cleanup (nothing should be deleted yet)
        deleted = self.auth_service.cleanup_expired_sessions()
        self.assertEqual(deleted, 0)
    
    def test_get_active_sessions(self):
        """Test getting active sessions for user"""
        # Create user and authenticate
        _, user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
        
        self.auth_service.authenticate(
            username="testuser",
            password="SecurePass123!"
        )
        
        # Get active sessions
        sessions = self.auth_service.get_active_sessions(user_id)
        
        self.assertGreater(len(sessions), 0)


if __name__ == '__main__':
    unittest.main()

