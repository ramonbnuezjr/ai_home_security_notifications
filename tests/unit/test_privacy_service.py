"""
Unit tests for PrivacyService - Epic 6
Tests privacy settings, data retention, export, and deletion (GDPR compliance).
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
import tempfile
import os
import json
import zipfile
from datetime import datetime, timedelta

from src.services.database_service import DatabaseService
from src.services.privacy_service import PrivacyService, PrivacySettings
from src.services.auth_service import AuthService


class TestPrivacyService(unittest.TestCase):
    """Test PrivacyService functionality"""
    
    def setUp(self):
        """Set up test database and services"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Create temporary media directory
        self.media_dir = tempfile.mkdtemp()
        
        # Initialize services
        self.db_service = DatabaseService(db_path=self.db_path)
        self.privacy_service = PrivacyService(
            database_service=self.db_service,
            media_base_path=self.media_dir
        )
        
        # Create auth service for creating test users
        self.auth_service = AuthService(
            database_service=self.db_service,
            jwt_secret="test-secret",
            jwt_expiry_hours=24
        )
        
        # Create test user
        _, self.user_id, _ = self.auth_service.create_user(
            username="testuser",
            password="SecurePass123!",
            email="test@example.com",
            role="user"
        )
    
    def tearDown(self):
        """Clean up test files"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
        # Clean up media directory
        import shutil
        if os.path.exists(self.media_dir):
            shutil.rmtree(self.media_dir)
    
    # ==================== Privacy Settings Tests ====================
    
    def test_get_default_privacy_settings(self):
        """Test getting default privacy settings for new user"""
        settings = self.privacy_service.get_privacy_settings(self.user_id)
        
        self.assertIsNotNone(settings)
        self.assertEqual(settings['user_id'], self.user_id)
        self.assertTrue(settings['collect_video'])
        self.assertTrue(settings['collect_images'])
        self.assertFalse(settings['collect_audio'])
        self.assertEqual(settings['retention_days_events'], 30)
    
    def test_update_privacy_settings(self):
        """Test updating privacy settings"""
        new_settings = {
            'collect_video': False,
            'collect_audio': True,
            'retention_days_events': 14,
            'retention_days_media': 3
        }
        
        success, errors = self.privacy_service.update_privacy_settings(
            self.user_id,
            new_settings
        )
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify settings were updated
        settings = self.privacy_service.get_privacy_settings(self.user_id)
        self.assertFalse(settings['collect_video'])
        self.assertTrue(settings['collect_audio'])
        self.assertEqual(settings['retention_days_events'], 14)
        self.assertEqual(settings['retention_days_media'], 3)
    
    def test_update_privacy_settings_invalid_retention(self):
        """Test updating with invalid retention days fails"""
        new_settings = {
            'retention_days_events': -5  # Invalid: negative
        }
        
        success, errors = self.privacy_service.update_privacy_settings(
            self.user_id,
            new_settings
        )
        
        self.assertFalse(success)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('positive integer' in e for e in errors))
    
    def test_update_privacy_settings_ignores_invalid_fields(self):
        """Test that invalid fields are ignored"""
        new_settings = {
            'collect_video': False,
            'invalid_field': 'some_value',  # Should be ignored
            'another_invalid': 123
        }
        
        success, errors = self.privacy_service.update_privacy_settings(
            self.user_id,
            new_settings
        )
        
        self.assertTrue(success)  # Should succeed, just ignore invalid fields
    
    # ==================== Data Retention Tests ====================
    
    def test_enforce_retention_policies_empty(self):
        """Test retention enforcement with no data"""
        results = self.privacy_service.enforce_retention_policies(self.user_id)
        
        self.assertIsInstance(results, dict)
        # Should return counts (all should be 0 with no data)
        self.assertIn('events', results)
    
    def test_delete_old_events(self):
        """Test deletion of old events"""
        # Create some test events
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Old event (should be deleted)
            old_date = datetime.now() - timedelta(days=60)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{}')
            """, (old_date,))
            
            # Recent event (should be kept)
            recent_date = datetime.now() - timedelta(days=5)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{}')
            """, (recent_date,))
            
            conn.commit()
        
        # Set retention to 30 days
        self.privacy_service.update_privacy_settings(
            self.user_id,
            {'retention_days_events': 30}
        )
        
        # Enforce retention
        results = self.privacy_service.enforce_retention_policies(self.user_id)
        
        # Verify old event was deleted
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
        
        self.assertEqual(count, 1)  # Only recent event should remain
    
    # ==================== Data Export Tests ====================
    
    def test_create_data_export_request(self):
        """Test creating data export request"""
        success, request_id, errors = self.privacy_service.create_data_export_request(self.user_id)
        
        self.assertTrue(success)
        self.assertIsNotNone(request_id)
        self.assertEqual(len(errors), 0)
    
    def test_create_duplicate_export_request_fails(self):
        """Test creating duplicate export request fails"""
        # Create first request
        self.privacy_service.create_data_export_request(self.user_id)
        
        # Try to create duplicate
        success, request_id, errors = self.privacy_service.create_data_export_request(self.user_id)
        
        self.assertFalse(success)
        self.assertIsNone(request_id)
        self.assertTrue(any('already pending' in e for e in errors))
    
    def test_process_data_export(self):
        """Test processing data export request"""
        # Create some test data
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{"test": "data"}')
            """, (datetime.now(),))
            conn.commit()
        
        # Create export request
        success, request_id, _ = self.privacy_service.create_data_export_request(self.user_id)
        
        # Process export
        success, export_file, errors = self.privacy_service.process_data_export(request_id)
        
        self.assertTrue(success)
        self.assertIsNotNone(export_file)
        self.assertEqual(len(errors), 0)
        self.assertTrue(os.path.exists(export_file))
        self.assertTrue(export_file.endswith('.zip'))
        
        # Verify ZIP contains data
        with zipfile.ZipFile(export_file, 'r') as zipf:
            files = zipf.namelist()
            self.assertGreater(len(files), 0)
        
        # Cleanup
        if os.path.exists(export_file):
            os.unlink(export_file)
    
    def test_gather_user_data(self):
        """Test gathering user data for export"""
        # Create some test data
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{"test": "data"}')
            """, (datetime.now(),))
            conn.commit()
        
        # Gather data
        data = self.privacy_service._gather_user_data(self.user_id)
        
        self.assertIsInstance(data, dict)
        self.assertIn('user_id', data)
        self.assertIn('export_date', data)
        self.assertIn('user_profile', data)
        self.assertIn('events', data)
        self.assertIn('privacy_settings', data)
        
        self.assertEqual(data['user_id'], self.user_id)
        self.assertGreater(len(data['events']), 0)
    
    # ==================== Data Deletion Tests ====================
    
    def test_create_data_deletion_request_partial(self):
        """Test creating partial data deletion request"""
        success, request_id, errors = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='partial',
            data_types=['events', 'media_files']
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(request_id)
        self.assertEqual(len(errors), 0)
    
    def test_create_data_deletion_request_full(self):
        """Test creating full data deletion request"""
        success, request_id, errors = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='full'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(request_id)
        self.assertEqual(len(errors), 0)
    
    def test_create_deletion_request_invalid_type(self):
        """Test creating deletion request with invalid type fails"""
        success, request_id, errors = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='invalid_type'
        )
        
        self.assertFalse(success)
        self.assertIsNone(request_id)
        self.assertGreater(len(errors), 0)
    
    def test_create_deletion_request_invalid_data_types(self):
        """Test creating deletion request with invalid data types fails"""
        success, request_id, errors = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='partial',
            data_types=['invalid_type', 'another_invalid']
        )
        
        self.assertFalse(success)
        self.assertIsNone(request_id)
        self.assertTrue(any('Invalid data types' in e for e in errors))
    
    def test_process_data_deletion_partial(self):
        """Test processing partial data deletion"""
        # Create some test data
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{}')
            """, (datetime.now(),))
            conn.commit()
        
        # Create deletion request
        success, request_id, _ = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='partial',
            data_types=['events']
        )
        
        # Process deletion
        success, errors = self.privacy_service.process_data_deletion(request_id)
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify events were deleted
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
        
        self.assertEqual(count, 0)
    
    def test_process_data_deletion_full(self):
        """Test processing full data deletion"""
        # Create some test data
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{}')
            """, (datetime.now(),))
            conn.commit()
        
        # Create deletion request
        success, request_id, _ = self.privacy_service.create_data_deletion_request(
            user_id=self.user_id,
            deletion_type='full'
        )
        
        # Process deletion
        success, errors = self.privacy_service.process_data_deletion(request_id)
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        
        # Verify all user data was deleted
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            events_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (self.user_id,))
            sessions_count = cursor.fetchone()[0]
        
        self.assertEqual(events_count, 0)
        self.assertEqual(sessions_count, 0)
    
    # ==================== Consent Management Tests ====================
    
    def test_log_consent(self):
        """Test logging consent action"""
        # Log consent
        self.privacy_service._log_consent(
            user_id=self.user_id,
            consent_type="privacy_policy_accepted",
            consent_given=True,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        # Verify logged
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM consent_log WHERE user_id = ?
            """, (self.user_id,))
            
            log = cursor.fetchone()
        
        self.assertIsNotNone(log)
        self.assertEqual(log['consent_type'], "privacy_policy_accepted")
        self.assertEqual(log['consent_given'], 1)
    
    def test_get_consent_history(self):
        """Test getting consent history"""
        # Log some consents
        for i in range(3):
            self.privacy_service._log_consent(
                user_id=self.user_id,
                consent_type=f"consent_type_{i}",
                consent_given=True
            )
        
        # Get history
        history = self.privacy_service.get_consent_history(self.user_id)
        
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 3)
        
        # Should be in reverse chronological order
        self.assertEqual(history[0]['consent_type'], "consent_type_2")
    
    # ==================== Integration with Privacy Settings ====================
    
    def test_privacy_settings_affect_retention(self):
        """Test that privacy settings properly affect retention policies"""
        # Set short retention period
        self.privacy_service.update_privacy_settings(
            self.user_id,
            {'retention_days_events': 1}
        )
        
        # Create old event
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            old_date = datetime.now() - timedelta(days=3)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, confidence, metadata)
                VALUES (?, 'motion_detected', 0.9, '{}')
            """, (old_date,))
            conn.commit()
        
        # Enforce retention
        results = self.privacy_service.enforce_retention_policies(self.user_id)
        
        # Verify event was deleted
        with self.db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
        
        self.assertEqual(count, 0)


class TestPrivacySettings(unittest.TestCase):
    """Test PrivacySettings dataclass"""
    
    def test_default_privacy_settings(self):
        """Test default privacy settings values"""
        settings = PrivacySettings(user_id=1)
        
        self.assertEqual(settings.user_id, 1)
        self.assertTrue(settings.collect_video)
        self.assertTrue(settings.collect_images)
        self.assertFalse(settings.collect_audio)
        self.assertFalse(settings.collect_location)
        self.assertFalse(settings.collect_biometric)
        self.assertEqual(settings.retention_days_events, 30)
        self.assertEqual(settings.retention_days_media, 7)
        self.assertEqual(settings.retention_days_logs, 90)
        self.assertTrue(settings.allow_analytics)
        self.assertFalse(settings.allow_cloud_backup)
        self.assertTrue(settings.anonymize_data)
        self.assertFalse(settings.third_party_sharing)


if __name__ == '__main__':
    unittest.main()

