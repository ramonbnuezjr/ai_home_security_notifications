"""
Integration tests for Epic 6 - Security & Privacy
Tests complete workflows with all services working together.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta

from src.services.database_service import DatabaseService
from src.services.auth_service import AuthService
from src.services.encryption_service import EncryptionService, ConfigEncryption
from src.services.privacy_service import PrivacyService


class TestEpic6Integration(unittest.TestCase):
    """Integration tests for Epic 6 services"""
    
    def setUp(self):
        """Set up all Epic 6 services"""
        # Create temporary files
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.key_fd, self.key_file = tempfile.mkstemp(suffix='.key')
        os.close(self.key_fd)
        os.unlink(self.key_file)  # Let encryption service create it
        self.media_dir = tempfile.mkdtemp()
        
        # Initialize all services
        self.db_service = DatabaseService(db_path=self.db_path)
        
        self.auth_service = AuthService(
            database_service=self.db_service,
            jwt_secret="integration-test-secret-key",
            jwt_expiry_hours=24
        )
        
        self.enc_service = EncryptionService(key_file=self.key_file)
        
        self.privacy_service = PrivacyService(
            database_service=self.db_service,
            media_base_path=self.media_dir
        )
    
    def tearDown(self):
        """Clean up test files"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
        if os.path.exists(self.key_file):
            os.unlink(self.key_file)
        
        import shutil
        if os.path.exists(self.media_dir):
            shutil.rmtree(self.media_dir)
    
    # ==================== Complete User Workflow Tests ====================
    
    def test_complete_user_lifecycle(self):
        """Test complete user lifecycle: create, authenticate, use system, delete"""
        # 1. Create user
        success, user_id, errors = self.auth_service.create_user(
            username="integrationuser",
            password="SecurePass123!",
            email="integration@example.com",
            role="admin"
        )
        self.assertTrue(success)
        self.assertIsNotNone(user_id)
        
        # 2. Authenticate user
        success, token, user_data, errors = self.auth_service.authenticate(
            username="integrationuser",
            password="SecurePass123!",
            ip_address="127.0.0.1",
            user_agent="Integration Test"
        )
        self.assertTrue(success)
        self.assertIsNotNone(token)
        
        # 3. Verify token
        is_valid, user_data, errors = self.auth_service.verify_token(token)
        self.assertTrue(is_valid)
        
        # 4. Update privacy settings
        success, errors = self.privacy_service.update_privacy_settings(
            user_id,
            {
                'collect_video': True,
                'retention_days_events': 14,
                'anonymize_data': True
            }
        )
        self.assertTrue(success)
        
        # 5. Create some events
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.95, '{"location": "front_door"}')
            """, (datetime.now(),))
            conn.commit()
        
        # 6. Export user data
        success, request_id, errors = self.privacy_service.create_data_export_request(user_id)
        self.assertTrue(success)
        
        success, export_file, errors = self.privacy_service.process_data_export(request_id)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_file))
        
        # 7. Delete user data
        success, request_id, errors = self.privacy_service.create_data_deletion_request(
            user_id,
            deletion_type='full'
        )
        self.assertTrue(success)
        
        # 8. Logout
        success = self.auth_service.logout(token)
        self.assertTrue(success)
        
        # Cleanup export file
        if os.path.exists(export_file):
            os.unlink(export_file)
    
    def test_multi_user_with_different_privacy_settings(self):
        """Test multiple users with different privacy settings"""
        # Create two users with different privacy preferences
        _, user1_id, _ = self.auth_service.create_user(
            username="privacyuser1",
            password="SecurePass123!",
            email="user1@example.com",
            role="user"
        )
        
        _, user2_id, _ = self.auth_service.create_user(
            username="privacyuser2",
            password="SecurePass456!",
            email="user2@example.com",
            role="user"
        )
        
        # User 1: Conservative privacy settings (short retention)
        self.privacy_service.update_privacy_settings(
            user1_id,
            {
                'collect_video': False,
                'collect_audio': False,
                'retention_days_events': 7,
                'allow_analytics': False
            }
        )
        
        # User 2: Standard privacy settings
        self.privacy_service.update_privacy_settings(
            user2_id,
            {
                'collect_video': True,
                'collect_audio': True,
                'retention_days_events': 30,
                'allow_analytics': True
            }
        )
        
        # Verify settings
        user1_settings = self.privacy_service.get_privacy_settings(user1_id)
        user2_settings = self.privacy_service.get_privacy_settings(user2_id)
        
        self.assertFalse(user1_settings['collect_video'])
        self.assertTrue(user2_settings['collect_video'])
        self.assertEqual(user1_settings['retention_days_events'], 7)
        self.assertEqual(user2_settings['retention_days_events'], 30)
    
    def test_encrypted_sensitive_config_workflow(self):
        """Test encrypting and storing sensitive configuration"""
        # Create config encryption helper
        config_enc = ConfigEncryption(self.enc_service)
        
        # Simulate sensitive configuration
        sensitive_config = {
            'smtp_password': 'email_password_123',
            'twilio_auth_token': 'twilio_token_456',
            'firebase_api_key': 'firebase_key_789',
            'public_setting': 'not_encrypted'
        }
        
        sensitive_keys = ['smtp_password', 'twilio_auth_token', 'firebase_api_key']
        
        # Encrypt sensitive values
        encrypted_config = config_enc.encrypt_sensitive_config(
            sensitive_config,
            sensitive_keys
        )
        
        # Store encrypted config (simulate)
        config_json = json.dumps(encrypted_config)
        
        # Later, load and decrypt
        loaded_config = json.loads(config_json)
        decrypted_config = config_enc.decrypt_sensitive_config(loaded_config)
        
        # Verify decryption successful
        self.assertEqual(decrypted_config['smtp_password'], 'email_password_123')
        self.assertEqual(decrypted_config['twilio_auth_token'], 'twilio_token_456')
        self.assertEqual(decrypted_config['firebase_api_key'], 'firebase_key_789')
        self.assertEqual(decrypted_config['public_setting'], 'not_encrypted')
    
    def test_mfa_enrollment_and_login(self):
        """Test complete MFA enrollment and authentication workflow"""
        # 1. Create user
        _, user_id, _ = self.auth_service.create_user(
            username="mfauser",
            password="SecurePass123!",
            email="mfa@example.com",
            role="admin"
        )
        
        # 2. Enable MFA
        success, secret, qr_code, errors = self.auth_service.enable_mfa(user_id)
        self.assertTrue(success)
        self.assertIsNotNone(secret)
        self.assertIsNotNone(qr_code)
        
        # 3. Verify and activate MFA
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        success, errors = self.auth_service.verify_and_enable_mfa(user_id, code)
        self.assertTrue(success)
        
        # 4. Try to login without MFA code (should require MFA)
        success, token, user_data, errors = self.auth_service.authenticate(
            username="mfauser",
            password="SecurePass123!"
        )
        self.assertFalse(success)
        self.assertIsNotNone(user_data)  # Should return partial data with MFA requirement
        self.assertTrue(user_data.get('requires_mfa'))
        
        # 5. Login with MFA code
        code = totp.now()
        success, token, user_data, errors = self.auth_service.authenticate(
            username="mfauser",
            password="SecurePass123!",
            mfa_code=code
        )
        self.assertTrue(success)
        self.assertIsNotNone(token)
    
    def test_rate_limiting_and_audit_trail(self):
        """Test rate limiting during failed logins and verify audit trail"""
        # Create user
        self.auth_service.create_user(
            username="audituser",
            password="SecurePass123!",
            email="audit@example.com",
            role="user"
        )
        
        # Attempt multiple failed logins (should trigger rate limiting)
        for i in range(6):
            success, token, user_data, errors = self.auth_service.authenticate(
                username="audituser",
                password="WrongPassword123!",
                ip_address="192.168.1.100",
                user_agent="Test Browser"
            )
            
            if i < 5:
                # First 5 attempts should fail normally
                self.assertFalse(success)
            else:
                # 6th attempt should be rate limited
                self.assertFalse(success)
                self.assertTrue(any('too many' in e.lower() for e in errors))
        
        # Verify audit trail
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log 
                WHERE username = 'audituser' AND action = 'login_failed'
            """)
            failed_attempts = cursor.fetchone()[0]
        
        self.assertGreater(failed_attempts, 0)
    
    def test_gdpr_data_export_completeness(self):
        """Test GDPR-compliant data export includes all user data"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="gdpruser",
            password="SecurePass123!",
            email="gdpr@example.com",
            role="user"
        )
        
        # Set privacy settings
        self.privacy_service.update_privacy_settings(
            user_id,
            {'collect_video': True, 'retention_days_events': 30}
        )
        
        # Create various types of data
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create events
            for i in range(3):
                cursor.execute("""
                    INSERT INTO events (timestamp, event_type, confidence, metadata)
                    VALUES (?, 'motion_detected', 0.9, ?)
                """, (datetime.now() - timedelta(hours=i), json.dumps({'test': f'event_{i}'})))
            
            conn.commit()
        
        # Authenticate to create session
        self.auth_service.authenticate(
            username="gdpruser",
            password="SecurePass123!"
        )
        
        # Request data export
        success, request_id, _ = self.privacy_service.create_data_export_request(user_id)
        self.assertTrue(success)
        
        # Process export
        success, export_file, _ = self.privacy_service.process_data_export(request_id)
        self.assertTrue(success)
        
        # Verify export contains all data types
        import zipfile
        with zipfile.ZipFile(export_file, 'r') as zipf:
            # Should contain at least the JSON file
            files = zipf.namelist()
            self.assertGreater(len(files), 0)
            
            # Read and verify JSON content
            json_files = [f for f in files if f.endswith('.json')]
            self.assertGreater(len(json_files), 0)
            
            with zipf.open(json_files[0]) as f:
                data = json.load(f)
            
            # Verify all required data is present
            self.assertIn('user_id', data)
            self.assertIn('export_date', data)
            self.assertIn('user_profile', data)
            self.assertIn('events', data)
            self.assertIn('privacy_settings', data)
            
            # Verify event data
            self.assertEqual(len(data['events']), 3)
        
        # Cleanup
        if os.path.exists(export_file):
            os.unlink(export_file)
    
    def test_data_retention_enforcement(self):
        """Test automatic data retention policy enforcement"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="retentionuser",
            password="SecurePass123!",
            email="retention@example.com",
            role="user"
        )
        
        # Set aggressive retention policy
        self.privacy_service.update_privacy_settings(
            user_id,
            {'retention_days_events': 7}
        )
        
        # Create events with different ages
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Old event (should be deleted)
            old_date = datetime.now() - timedelta(days=10)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'old_event', 0.9, '{}')
            """, (old_date,))
            
            # Recent event (should be kept)
            recent_date = datetime.now() - timedelta(days=3)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'recent_event', 0.9, '{}')
            """, (recent_date,))
            
            conn.commit()
        
        # Enforce retention policies
        results = self.privacy_service.enforce_retention_policies(user_id)
        
        # Verify old events deleted
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'old_event'")
            old_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'recent_event'")
            recent_count = cursor.fetchone()[0]
        
        self.assertEqual(old_count, 0)  # Old event should be deleted
        self.assertEqual(recent_count, 1)  # Recent event should remain
    
    def test_session_management_lifecycle(self):
        """Test complete session management lifecycle"""
        # Create user
        _, user_id, _ = self.auth_service.create_user(
            username="sessionuser",
            password="SecurePass123!",
            email="session@example.com",
            role="user"
        )
        
        # Create multiple sessions
        tokens = []
        for i in range(3):
            success, token, _, _ = self.auth_service.authenticate(
                username="sessionuser",
                password="SecurePass123!",
                ip_address=f"192.168.1.{i}",
                user_agent=f"Browser {i}"
            )
            tokens.append(token)
        
        # Verify all sessions are active
        active_sessions = self.auth_service.get_active_sessions(user_id)
        self.assertEqual(len(active_sessions), 3)
        
        # Logout one session
        self.auth_service.logout(tokens[0])
        active_sessions = self.auth_service.get_active_sessions(user_id)
        self.assertEqual(len(active_sessions), 2)
        
        # Logout all sessions
        self.auth_service.logout_all_sessions(user_id)
        active_sessions = self.auth_service.get_active_sessions(user_id)
        self.assertEqual(len(active_sessions), 0)
    
    def test_role_based_access_control(self):
        """Test role-based access control across services"""
        # Create users with different roles
        roles = ['viewer', 'user', 'moderator', 'admin']
        user_ids = {}
        
        for role in roles:
            _, user_id, _ = self.auth_service.create_user(
                username=f"{role}_user",
                password="SecurePass123!",
                email=f"{role}@example.com",
                role=role
            )
            user_ids[role] = user_id
        
        # Test permission hierarchy
        admin_user = self.auth_service.get_user(user_ids['admin'])
        viewer_user = self.auth_service.get_user(user_ids['viewer'])
        
        # Admin should have all permissions
        self.assertTrue(self.auth_service.check_permission(admin_user, 'viewer'))
        self.assertTrue(self.auth_service.check_permission(admin_user, 'user'))
        self.assertTrue(self.auth_service.check_permission(admin_user, 'moderator'))
        self.assertTrue(self.auth_service.check_permission(admin_user, 'admin'))
        
        # Viewer should only have viewer permission
        self.assertTrue(self.auth_service.check_permission(viewer_user, 'viewer'))
        self.assertFalse(self.auth_service.check_permission(viewer_user, 'user'))
        self.assertFalse(self.auth_service.check_permission(viewer_user, 'moderator'))
        self.assertFalse(self.auth_service.check_permission(viewer_user, 'admin'))


if __name__ == '__main__':
    unittest.main()

