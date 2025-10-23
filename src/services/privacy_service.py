"""
Privacy service for data collection controls, retention policies, and GDPR compliance.
Provides data export, deletion, and privacy settings management.
"""

import logging
import json
import zipfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PrivacySettings:
    """Privacy settings configuration"""
    user_id: int
    collect_video: bool = True
    collect_images: bool = True
    collect_audio: bool = False
    collect_location: bool = False
    collect_biometric: bool = False
    retention_days_events: int = 30
    retention_days_media: int = 7
    retention_days_logs: int = 90
    retention_days_metrics: int = 7
    allow_analytics: bool = True
    allow_cloud_backup: bool = False
    anonymize_data: bool = True
    third_party_sharing: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DataExportRequest:
    """Data export request record"""
    id: Optional[int] = None
    user_id: int = 0
    request_date: Optional[datetime] = None
    status: str = "pending"  # 'pending', 'processing', 'completed', 'failed'
    export_file: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class DataDeletionRequest:
    """Data deletion request record"""
    id: Optional[int] = None
    user_id: int = 0
    request_date: Optional[datetime] = None
    deletion_type: str = "partial"  # 'partial', 'full'
    data_types: Optional[List[str]] = None
    status: str = "pending"  # 'pending', 'processing', 'completed', 'failed'
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class PrivacyService:
    """
    Service for managing privacy settings, data retention, export, and deletion.
    GDPR and privacy law compliant.
    """
    
    DATA_TYPES = [
        'events',
        'media_files',
        'notifications',
        'system_metrics',
        'audit_logs',
        'user_data'
    ]
    
    def __init__(self, database_service, media_base_path: Optional[str] = None):
        """
        Initialize privacy service.
        
        Args:
            database_service: DatabaseService instance
            media_base_path: Base path for media files storage
        """
        self.db = database_service
        self.media_base_path = media_base_path or "/tmp/ai_security_media"
        self._initialize_privacy_tables()
        logger.info("Privacy service initialized")
    
    def _initialize_privacy_tables(self):
        """Create privacy-related tables if they don't exist"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Privacy settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS privacy_settings (
                    user_id INTEGER PRIMARY KEY,
                    collect_video BOOLEAN DEFAULT 1,
                    collect_images BOOLEAN DEFAULT 1,
                    collect_audio BOOLEAN DEFAULT 0,
                    collect_location BOOLEAN DEFAULT 0,
                    collect_biometric BOOLEAN DEFAULT 0,
                    retention_days_events INTEGER DEFAULT 30,
                    retention_days_media INTEGER DEFAULT 7,
                    retention_days_logs INTEGER DEFAULT 90,
                    retention_days_metrics INTEGER DEFAULT 7,
                    allow_analytics BOOLEAN DEFAULT 1,
                    allow_cloud_backup BOOLEAN DEFAULT 0,
                    anonymize_data BOOLEAN DEFAULT 1,
                    third_party_sharing BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Data export requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_export_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    export_file VARCHAR(500),
                    error_message TEXT,
                    completed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_export_user_id 
                ON data_export_requests(user_id)
            """)
            
            # Data deletion requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_deletion_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deletion_type VARCHAR(20) DEFAULT 'partial',
                    data_types TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    completed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deletion_user_id 
                ON data_deletion_requests(user_id)
            """)
            
            # Consent log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consent_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    consent_type VARCHAR(100) NOT NULL,
                    consent_given BOOLEAN NOT NULL,
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_consent_user_id 
                ON consent_log(user_id)
            """)
            
            conn.commit()
            logger.info("Privacy tables initialized")
    
    # ==================== Privacy Settings ====================
    
    def get_privacy_settings(self, user_id: int) -> Optional[Dict]:
        """Get privacy settings for user"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM privacy_settings WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                # Return default settings if none exist
                return self._get_default_privacy_settings(user_id)
        
        except Exception as e:
            logger.error(f"Failed to get privacy settings: {e}")
            return None
    
    def _get_default_privacy_settings(self, user_id: int) -> Dict:
        """Get default privacy settings"""
        settings = PrivacySettings(user_id=user_id)
        return asdict(settings)
    
    def update_privacy_settings(
        self,
        user_id: int,
        settings: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Update privacy settings for user.
        
        Args:
            user_id: User ID
            settings: Dict of settings to update
            
        Returns:
            (success, errors)
        """
        errors = []
        
        try:
            # Get existing settings or create defaults
            existing = self.get_privacy_settings(user_id)
            
            # Validate settings
            valid_fields = [
                'collect_video', 'collect_images', 'collect_audio', 
                'collect_location', 'collect_biometric',
                'retention_days_events', 'retention_days_media',
                'retention_days_logs', 'retention_days_metrics',
                'allow_analytics', 'allow_cloud_backup',
                'anonymize_data', 'third_party_sharing'
            ]
            
            # Filter and validate settings
            updates = {}
            for key, value in settings.items():
                if key in valid_fields:
                    # Validate retention days
                    if key.startswith('retention_days_'):
                        if not isinstance(value, int) or value < 1:
                            errors.append(f"{key} must be a positive integer")
                            continue
                    updates[key] = value
            
            if errors:
                return False, errors
            
            # Update or insert settings
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                if existing and existing.get('user_id'):
                    # Update existing
                    if updates:
                        set_clauses = [f"{key} = ?" for key in updates.keys()]
                        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                        
                        query = f"""
                            UPDATE privacy_settings 
                            SET {', '.join(set_clauses)}
                            WHERE user_id = ?
                        """
                        
                        params = list(updates.values()) + [user_id]
                        cursor.execute(query, params)
                else:
                    # Insert new
                    columns = ['user_id'] + list(updates.keys())
                    placeholders = ['?'] * len(columns)
                    
                    query = f"""
                        INSERT INTO privacy_settings ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    params = [user_id] + list(updates.values())
                    cursor.execute(query, params)
                
                conn.commit()
                
                logger.info(f"Privacy settings updated for user {user_id}")
                self._log_consent(user_id, "privacy_settings_updated", True)
                
                return True, []
        
        except Exception as e:
            error_msg = f"Failed to update privacy settings: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors
    
    # ==================== Data Retention ====================
    
    def enforce_retention_policies(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        Enforce retention policies for all users or specific user.
        
        Args:
            user_id: Optional user ID to enforce policies for (None = all users)
            
        Returns:
            Dict with counts of deleted items per data type
        """
        results = {}
        
        try:
            # Get all users' privacy settings
            if user_id:
                settings_list = [self.get_privacy_settings(user_id)]
            else:
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT user_id FROM privacy_settings")
                    user_ids = [row[0] for row in cursor.fetchall()]
                    settings_list = [self.get_privacy_settings(uid) for uid in user_ids]
            
            total_deleted = {
                'events': 0,
                'media_files': 0,
                'notifications': 0,
                'metrics': 0,
                'audit_logs': 0
            }
            
            for settings in settings_list:
                if not settings:
                    continue
                
                user_id = settings['user_id']
                
                # Delete old events
                events_cutoff = datetime.now() - timedelta(days=settings['retention_days_events'])
                deleted = self._delete_old_events(user_id, events_cutoff)
                total_deleted['events'] += deleted
                
                # Delete old media files
                media_cutoff = datetime.now() - timedelta(days=settings['retention_days_media'])
                deleted = self._delete_old_media(user_id, media_cutoff)
                total_deleted['media_files'] += deleted
                
                # Delete old metrics
                metrics_cutoff = datetime.now() - timedelta(days=settings['retention_days_metrics'])
                deleted = self._delete_old_metrics(metrics_cutoff)
                total_deleted['metrics'] += deleted
                
                # Delete old audit logs (if user specifically requests)
                if settings.get('retention_days_logs', 90) < 90:
                    logs_cutoff = datetime.now() - timedelta(days=settings['retention_days_logs'])
                    deleted = self._delete_old_audit_logs(user_id, logs_cutoff)
                    total_deleted['audit_logs'] += deleted
            
            logger.info(f"Retention policies enforced: {total_deleted}")
            return total_deleted
        
        except Exception as e:
            logger.error(f"Failed to enforce retention policies: {e}")
            return {}
    
    def _delete_old_events(self, user_id: int, cutoff_date: datetime) -> int:
        """Delete events older than cutoff date"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM events 
                    WHERE timestamp < ? 
                """, (cutoff_date,))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete old events: {e}")
            return 0
    
    def _delete_old_media(self, user_id: int, cutoff_date: datetime) -> int:
        """Delete media files older than cutoff date"""
        try:
            # Get old media file paths from events
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT image_path, video_path FROM events
                    WHERE timestamp < ?
                """, (cutoff_date,))
                
                deleted = 0
                for row in cursor.fetchall():
                    for path in [row[0], row[1]]:
                        if path and Path(path).exists():
                            try:
                                Path(path).unlink()
                                deleted += 1
                            except Exception as e:
                                logger.error(f"Failed to delete media file {path}: {e}")
                
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete old media: {e}")
            return 0
    
    def _delete_old_metrics(self, cutoff_date: datetime) -> int:
        """Delete metrics older than cutoff date"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM system_metrics 
                    WHERE timestamp < ?
                """, (cutoff_date,))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete old metrics: {e}")
            return 0
    
    def _delete_old_audit_logs(self, user_id: int, cutoff_date: datetime) -> int:
        """Delete audit logs older than cutoff date"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM audit_log 
                    WHERE user_id = ? AND timestamp < ?
                """, (user_id, cutoff_date))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete old audit logs: {e}")
            return 0
    
    # ==================== Data Export ====================
    
    def create_data_export_request(self, user_id: int) -> Tuple[bool, Optional[int], List[str]]:
        """
        Create a data export request.
        
        Returns:
            (success, request_id, errors)
        """
        errors = []
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for existing pending requests
                cursor.execute("""
                    SELECT id FROM data_export_requests
                    WHERE user_id = ? AND status = 'pending'
                """, (user_id,))
                
                if cursor.fetchone():
                    errors.append("A data export request is already pending")
                    return False, None, errors
                
                # Create new request
                cursor.execute("""
                    INSERT INTO data_export_requests (user_id, status)
                    VALUES (?, 'pending')
                """, (user_id,))
                
                request_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Data export request created for user {user_id}: {request_id}")
                self._log_consent(user_id, "data_export_requested", True)
                
                return True, request_id, []
        
        except Exception as e:
            error_msg = f"Failed to create export request: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, None, errors
    
    def process_data_export(self, request_id: int) -> Tuple[bool, Optional[str], List[str]]:
        """
        Process a data export request and generate export file.
        
        Returns:
            (success, export_file_path, errors)
        """
        errors = []
        
        try:
            # Get request
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM data_export_requests WHERE id = ?
                """, (request_id,))
                
                request_row = cursor.fetchone()
                if not request_row:
                    errors.append("Export request not found")
                    return False, None, errors
                
                request = dict(request_row)
                user_id = request['user_id']
                
                # Update status to processing
                cursor.execute("""
                    UPDATE data_export_requests
                    SET status = 'processing'
                    WHERE id = ?
                """, (request_id,))
                conn.commit()
            
            # Create export directory
            export_dir = Path(self.media_base_path) / "exports" / f"user_{user_id}"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Export data
            export_data = self._gather_user_data(user_id)
            
            # Save to JSON
            json_file = export_dir / f"data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Create ZIP archive
            zip_file = export_dir / f"data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(json_file, json_file.name)
                
                # Add media files
                if export_data.get('media_files'):
                    for media_path in export_data['media_files']:
                        if Path(media_path).exists():
                            zipf.write(media_path, Path(media_path).name)
            
            # Clean up JSON file
            json_file.unlink()
            
            # Update request with export file
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE data_export_requests
                    SET status = 'completed', export_file = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (str(zip_file), request_id))
                conn.commit()
            
            logger.info(f"Data export completed for request {request_id}: {zip_file}")
            self._log_consent(user_id, "data_export_completed", True)
            
            return True, str(zip_file), []
        
        except Exception as e:
            error_msg = f"Failed to process export: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            
            # Update request status to failed
            try:
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE data_export_requests
                        SET status = 'failed', error_message = ?
                        WHERE id = ?
                    """, (error_msg, request_id))
                    conn.commit()
            except:
                pass
            
            return False, None, errors
    
    def _gather_user_data(self, user_id: int) -> Dict[str, Any]:
        """Gather all user data for export"""
        data = {
            'user_id': user_id,
            'export_date': datetime.now().isoformat(),
            'user_profile': {},
            'events': [],
            'notifications': [],
            'privacy_settings': {},
            'audit_logs': [],
            'media_files': []
        }
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # User profile
                cursor.execute("""
                    SELECT username, email, role, created_at, last_login
                    FROM users WHERE id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    data['user_profile'] = dict(row)
                
                # Events
                cursor.execute("""
                    SELECT * FROM events
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """)
                for row in cursor.fetchall():
                    event = dict(row)
                    if event.get('metadata'):
                        event['metadata'] = json.loads(event['metadata'])
                    data['events'].append(event)
                    
                    # Collect media file paths
                    if event.get('image_path'):
                        data['media_files'].append(event['image_path'])
                    if event.get('video_path'):
                        data['media_files'].append(event['video_path'])
                
                # Notifications
                cursor.execute("""
                    SELECT * FROM notifications
                    ORDER BY created_at DESC
                    LIMIT 500
                """)
                for row in cursor.fetchall():
                    notif = dict(row)
                    if notif.get('metadata'):
                        notif['metadata'] = json.loads(notif['metadata'])
                    data['notifications'].append(notif)
                
                # Privacy settings
                cursor.execute("""
                    SELECT * FROM privacy_settings WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    data['privacy_settings'] = dict(row)
                
                # Audit logs
                cursor.execute("""
                    SELECT * FROM audit_log WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, (user_id,))
                for row in cursor.fetchall():
                    data['audit_logs'].append(dict(row))
        
        except Exception as e:
            logger.error(f"Failed to gather user data: {e}")
        
        return data
    
    # ==================== Data Deletion ====================
    
    def create_data_deletion_request(
        self,
        user_id: int,
        deletion_type: str = "partial",
        data_types: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[int], List[str]]:
        """
        Create a data deletion request.
        
        Args:
            user_id: User ID
            deletion_type: 'partial' or 'full'
            data_types: List of data types to delete (for partial deletion)
            
        Returns:
            (success, request_id, errors)
        """
        errors = []
        
        if deletion_type not in ['partial', 'full']:
            errors.append("deletion_type must be 'partial' or 'full'")
            return False, None, errors
        
        if deletion_type == 'partial' and not data_types:
            errors.append("data_types required for partial deletion")
            return False, None, errors
        
        if data_types:
            invalid_types = [dt for dt in data_types if dt not in self.DATA_TYPES]
            if invalid_types:
                errors.append(f"Invalid data types: {invalid_types}")
                return False, None, errors
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create request
                cursor.execute("""
                    INSERT INTO data_deletion_requests 
                    (user_id, deletion_type, data_types, status)
                    VALUES (?, ?, ?, 'pending')
                """, (user_id, deletion_type, json.dumps(data_types) if data_types else None))
                
                request_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Data deletion request created for user {user_id}: {request_id}")
                self._log_consent(user_id, "data_deletion_requested", True)
                
                return True, request_id, []
        
        except Exception as e:
            error_msg = f"Failed to create deletion request: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, None, errors
    
    def process_data_deletion(self, request_id: int) -> Tuple[bool, List[str]]:
        """
        Process a data deletion request.
        
        Returns:
            (success, errors)
        """
        errors = []
        
        try:
            # Get request
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM data_deletion_requests WHERE id = ?
                """, (request_id,))
                
                request_row = cursor.fetchone()
                if not request_row:
                    errors.append("Deletion request not found")
                    return False, errors
                
                request = dict(request_row)
                user_id = request['user_id']
                deletion_type = request['deletion_type']
                data_types_json = request.get('data_types')
                data_types = json.loads(data_types_json) if data_types_json else []
                
                # Update status to processing
                cursor.execute("""
                    UPDATE data_deletion_requests
                    SET status = 'processing'
                    WHERE id = ?
                """, (request_id,))
                conn.commit()
            
            # Perform deletion
            if deletion_type == 'full':
                # Delete all user data
                self._delete_all_user_data(user_id)
            else:
                # Delete specific data types
                self._delete_user_data_types(user_id, data_types)
            
            # Update request status
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE data_deletion_requests
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (request_id,))
                conn.commit()
            
            logger.info(f"Data deletion completed for request {request_id}")
            self._log_consent(user_id, "data_deletion_completed", True)
            
            return True, []
        
        except Exception as e:
            error_msg = f"Failed to process deletion: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            
            # Update request status to failed
            try:
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE data_deletion_requests
                        SET status = 'failed', error_message = ?
                        WHERE id = ?
                    """, (error_msg, request_id))
                    conn.commit()
            except:
                pass
            
            return False, errors
    
    def _delete_all_user_data(self, user_id: int):
        """Delete all data for a user (except audit logs)"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete events (cascades to detected_objects and notifications)
            cursor.execute("DELETE FROM events")
            
            # Delete sessions
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            
            # Delete privacy settings
            cursor.execute("DELETE FROM privacy_settings WHERE user_id = ?", (user_id,))
            
            # Delete export/deletion requests
            cursor.execute("DELETE FROM data_export_requests WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM data_deletion_requests WHERE user_id = ?", (user_id,))
            
            conn.commit()
        
        # Delete media files
        media_dir = Path(self.media_base_path)
        if media_dir.exists():
            try:
                shutil.rmtree(media_dir)
            except Exception as e:
                logger.error(f"Failed to delete media directory: {e}")
    
    def _delete_user_data_types(self, user_id: int, data_types: List[str]):
        """Delete specific data types for a user"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            if 'events' in data_types:
                cursor.execute("DELETE FROM events")
            
            if 'notifications' in data_types:
                cursor.execute("DELETE FROM notifications")
            
            if 'system_metrics' in data_types:
                cursor.execute("DELETE FROM system_metrics")
            
            conn.commit()
        
        if 'media_files' in data_types:
            media_dir = Path(self.media_base_path)
            if media_dir.exists():
                try:
                    shutil.rmtree(media_dir)
                    media_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.error(f"Failed to delete media files: {e}")
    
    # ==================== Consent Management ====================
    
    def _log_consent(
        self,
        user_id: int,
        consent_type: str,
        consent_given: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log consent action"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO consent_log 
                    (user_id, consent_type, consent_given, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, consent_type, 1 if consent_given else 0, ip_address, user_agent))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log consent: {e}")
    
    def get_consent_history(self, user_id: int) -> List[Dict]:
        """Get consent history for user"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM consent_log 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get consent history: {e}")
            return []




