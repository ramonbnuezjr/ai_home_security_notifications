"""
Database service for storing events, detections, and system metrics.
Uses SQLite with WAL mode for better concurrent access.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading


logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event record"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    event_type: str = ""  # 'motion', 'object_detected', 'alert'
    severity: str = "low"  # 'low', 'medium', 'high', 'critical'
    zone_name: Optional[str] = None
    motion_percentage: Optional[float] = None
    threat_level: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


@dataclass
class DetectedObject:
    """Detected object record"""
    id: Optional[int] = None
    event_id: int = 0
    class_name: str = ""
    confidence: float = 0.0
    bbox_x1: Optional[int] = None
    bbox_y1: Optional[int] = None
    bbox_x2: Optional[int] = None
    bbox_y2: Optional[int] = None
    threat_level: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class NotificationRecord:
    """Notification record"""
    id: Optional[int] = None
    event_id: int = 0
    channel: str = ""  # 'email', 'sms', 'push', 'voice'
    priority: str = "low"
    status: str = "pending"  # 'pending', 'sent', 'failed'
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


@dataclass
class SystemMetric:
    """System metric record"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    temperature: Optional[float] = None
    fps: Optional[float] = None
    yolo_inference_time: Optional[float] = None
    active_services: Optional[List[str]] = None
    created_at: Optional[datetime] = None


class DatabaseService:
    """
    Database service for managing security system data.
    Thread-safe with connection pooling.
    """
    
    def __init__(self, db_path: str, fallback_path: Optional[str] = None):
        """
        Initialize database service.
        
        Args:
            db_path: Primary database path (preferably on SSD)
            fallback_path: Fallback path if primary is unavailable
        """
        self.db_path = self._ensure_db_path(db_path, fallback_path)
        self._lock = threading.Lock()
        self._initialize_database()
        logger.info(f"Database initialized at: {self.db_path}")
    
    def _ensure_db_path(self, primary_path: str, fallback_path: Optional[str]) -> str:
        """Ensure database path exists, use fallback if needed."""
        try:
            # Try primary path
            db_path = Path(primary_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = db_path.parent / ".write_test"
            test_file.touch()
            test_file.unlink()
            logger.info(f"Using primary database path: {primary_path}")
            return primary_path
        except Exception as e:
            logger.warning(f"Cannot use primary path {primary_path}: {e}")
            if fallback_path:
                try:
                    fb_path = Path(fallback_path)
                    fb_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Using fallback database path: {fallback_path}")
                    return fallback_path
                except Exception as e2:
                    logger.error(f"Cannot use fallback path {fallback_path}: {e2}")
            raise RuntimeError(f"No writable database path available")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper configuration."""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            # Set synchronous mode
            conn.execute("PRAGMA synchronous = NORMAL")
            # Return results as Row objects (dict-like)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    zone_name VARCHAR(100),
                    motion_percentage FLOAT,
                    threat_level VARCHAR(20),
                    image_path VARCHAR(500),
                    video_path VARCHAR(500),
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events(event_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_severity 
                ON events(severity)
            """)
            
            # Detected objects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detected_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    class_name VARCHAR(100) NOT NULL,
                    confidence FLOAT NOT NULL,
                    bbox_x1 INTEGER,
                    bbox_y1 INTEGER,
                    bbox_x2 INTEGER,
                    bbox_y2 INTEGER,
                    threat_level VARCHAR(20),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_objects_event_id 
                ON detected_objects(event_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_objects_class 
                ON detected_objects(class_name)
            """)
            
            # Notifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    sent_at DATETIME,
                    error_message TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_event_id 
                ON notifications(event_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_status 
                ON notifications(status)
            """)
            
            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cpu_usage FLOAT,
                    memory_usage FLOAT,
                    disk_usage FLOAT,
                    temperature FLOAT,
                    fps FLOAT,
                    yolo_inference_time FLOAT,
                    active_services TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON system_metrics(timestamp)
            """)
            
            # Configuration history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    config_section VARCHAR(100),
                    changes TEXT NOT NULL,
                    changed_by VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_timestamp 
                ON config_history(timestamp)
            """)
            
            # Users table (for Epic 6)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    role VARCHAR(50) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    last_login DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            conn.commit()
            logger.info("Database schema initialized successfully")
    
    # ==================== Event Operations ====================
    
    def create_event(self, event: Event, detected_objects: Optional[List[DetectedObject]] = None) -> int:
        """
        Create a new event record with optional detected objects.
        
        Args:
            event: Event data
            detected_objects: List of detected objects
            
        Returns:
            event_id: ID of created event
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Set timestamp if not provided
                if not event.timestamp:
                    event.timestamp = datetime.now()
                
                # Insert event
                cursor.execute("""
                    INSERT INTO events (
                        timestamp, event_type, severity, zone_name,
                        motion_percentage, threat_level, image_path,
                        video_path, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp,
                    event.event_type,
                    event.severity,
                    event.zone_name,
                    event.motion_percentage,
                    event.threat_level,
                    event.image_path,
                    event.video_path,
                    json.dumps(event.metadata) if event.metadata else None
                ))
                
                event_id = cursor.lastrowid
                
                # Insert detected objects if provided
                if detected_objects:
                    for obj in detected_objects:
                        cursor.execute("""
                            INSERT INTO detected_objects (
                                event_id, class_name, confidence,
                                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                                threat_level
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            event_id,
                            obj.class_name,
                            obj.confidence,
                            obj.bbox_x1,
                            obj.bbox_y1,
                            obj.bbox_x2,
                            obj.bbox_y2,
                            obj.threat_level
                        ))
                
                conn.commit()
                logger.debug(f"Created event {event_id} with {len(detected_objects or [])} objects")
                return event_id
    
    def get_event(self, event_id: int) -> Optional[Dict]:
        """Get event by ID with detected objects."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get event
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            event_row = cursor.fetchone()
            
            if not event_row:
                return None
            
            event = dict(event_row)
            if event.get('metadata'):
                event['metadata'] = json.loads(event['metadata'])
            
            # Get detected objects
            cursor.execute("""
                SELECT * FROM detected_objects WHERE event_id = ?
            """, (event_id,))
            
            event['detected_objects'] = [dict(row) for row in cursor.fetchall()]
            
            return event
    
    def get_events(
        self,
        page: int = 1,
        limit: int = 50,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Dict], int]:
        """
        Get events with pagination and filtering.
        
        Returns:
            (events, total_count)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            where_clauses = []
            params = []
            
            if event_type:
                where_clauses.append("event_type = ?")
                params.append(event_type)
            
            if severity:
                where_clauses.append("severity = ?")
                params.append(severity)
            
            if start_date:
                where_clauses.append("timestamp >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("timestamp <= ?")
                params.append(end_date)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM events WHERE {where_sql}", params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * limit
            cursor.execute(f"""
                SELECT * FROM events WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event.get('metadata'):
                    event['metadata'] = json.loads(event['metadata'])
                events.append(event)
            
            return events, total_count
    
    def delete_event(self, event_id: int) -> bool:
        """Delete event and associated objects (cascading)."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    def get_event_stats(self, days: int = 7) -> Dict:
        """Get event statistics for the last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            start_date = datetime.now() - timedelta(days=days)
            
            stats = {}
            
            # Total events
            cursor.execute("""
                SELECT COUNT(*) FROM events WHERE timestamp >= ?
            """, (start_date,))
            stats['total_events'] = cursor.fetchone()[0]
            
            # Events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM events WHERE timestamp >= ?
                GROUP BY event_type
            """, (start_date,))
            stats['by_type'] = {row['event_type']: row['count'] for row in cursor.fetchall()}
            
            # Events by severity
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM events WHERE timestamp >= ?
                GROUP BY severity
            """, (start_date,))
            stats['by_severity'] = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Most detected objects
            cursor.execute("""
                SELECT do.class_name, COUNT(*) as count
                FROM detected_objects do
                JOIN events e ON do.event_id = e.id
                WHERE e.timestamp >= ?
                GROUP BY do.class_name
                ORDER BY count DESC
                LIMIT 10
            """, (start_date,))
            stats['top_objects'] = [
                {'class_name': row['class_name'], 'count': row['count']}
                for row in cursor.fetchall()
            ]
            
            return stats
    
    # ==================== Notification Operations ====================
    
    def create_notification(self, notification: NotificationRecord) -> int:
        """Create notification record."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO notifications (
                        event_id, channel, priority, status,
                        sent_at, error_message, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    notification.event_id,
                    notification.channel,
                    notification.priority,
                    notification.status,
                    notification.sent_at,
                    notification.error_message,
                    json.dumps(notification.metadata) if notification.metadata else None
                ))
                
                return cursor.lastrowid
    
    def update_notification_status(
        self,
        notification_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update notification status."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE notifications
                    SET status = ?, sent_at = ?, error_message = ?
                    WHERE id = ?
                """, (status, datetime.now(), error_message, notification_id))
                
                conn.commit()
    
    def get_notification_stats(self, days: int = 7) -> Dict:
        """Get notification statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            start_date = datetime.now() - timedelta(days=days)
            
            stats = {}
            
            # Total notifications
            cursor.execute("""
                SELECT COUNT(*) FROM notifications WHERE created_at >= ?
            """, (start_date,))
            stats['total'] = cursor.fetchone()[0]
            
            # By channel
            cursor.execute("""
                SELECT channel, COUNT(*) as count
                FROM notifications WHERE created_at >= ?
                GROUP BY channel
            """, (start_date,))
            stats['by_channel'] = {row['channel']: row['count'] for row in cursor.fetchall()}
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM notifications WHERE created_at >= ?
                GROUP BY status
            """, (start_date,))
            stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            return stats
    
    # ==================== System Metrics Operations ====================
    
    def create_metric(self, metric: SystemMetric) -> int:
        """Create system metric record."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if not metric.timestamp:
                    metric.timestamp = datetime.now()
                
                cursor.execute("""
                    INSERT INTO system_metrics (
                        timestamp, cpu_usage, memory_usage, disk_usage,
                        temperature, fps, yolo_inference_time, active_services
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.timestamp,
                    metric.cpu_usage,
                    metric.memory_usage,
                    metric.disk_usage,
                    metric.temperature,
                    metric.fps,
                    metric.yolo_inference_time,
                    json.dumps(metric.active_services) if metric.active_services else None
                ))
                
                return cursor.lastrowid
    
    def get_latest_metrics(self, count: int = 1) -> List[Dict]:
        """Get the most recent system metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM system_metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """, (count,))
            
            metrics = []
            for row in cursor.fetchall():
                metric = dict(row)
                if metric.get('active_services'):
                    metric['active_services'] = json.loads(metric['active_services'])
                metrics.append(metric)
            
            return metrics
    
    def get_metrics_history(
        self,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5
    ) -> List[Dict]:
        """Get aggregated metrics history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    datetime((strftime('%s', timestamp) / (? * 60)) * (? * 60), 'unixepoch') as time_bucket,
                    AVG(cpu_usage) as avg_cpu,
                    AVG(memory_usage) as avg_memory,
                    AVG(disk_usage) as avg_disk,
                    AVG(temperature) as avg_temperature,
                    AVG(fps) as avg_fps,
                    AVG(yolo_inference_time) as avg_inference_time
                FROM system_metrics
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY time_bucket
                ORDER BY time_bucket
            """, (interval_minutes, interval_minutes, start_time, end_time))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Maintenance Operations ====================
    
    def cleanup_old_data(
        self,
        events_days: int = 30,
        metrics_days: int = 7,
        notifications_days: int = 30
    ):
        """Remove old data based on retention policies."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old events (cascades to objects and notifications)
                events_cutoff = datetime.now() - timedelta(days=events_days)
                cursor.execute("DELETE FROM events WHERE timestamp < ?", (events_cutoff,))
                events_deleted = cursor.rowcount
                
                # Delete old metrics
                metrics_cutoff = datetime.now() - timedelta(days=metrics_days)
                cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", (metrics_cutoff,))
                metrics_deleted = cursor.rowcount
                
                # Delete old notifications (orphaned ones)
                notif_cutoff = datetime.now() - timedelta(days=notifications_days)
                cursor.execute("DELETE FROM notifications WHERE created_at < ?", (notif_cutoff,))
                notif_deleted = cursor.rowcount
                
                conn.commit()
                
                logger.info(
                    f"Cleanup completed: {events_deleted} events, "
                    f"{metrics_deleted} metrics, {notif_deleted} notifications deleted"
                )
                
                return {
                    'events_deleted': events_deleted,
                    'metrics_deleted': metrics_deleted,
                    'notifications_deleted': notif_deleted
                }
    
    def vacuum_database(self):
        """Optimize database (VACUUM)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("VACUUM")
                conn.commit()
                logger.info("Database vacuum completed")
            finally:
                conn.close()
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Table counts
            cursor.execute("SELECT COUNT(*) FROM events")
            stats['total_events'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM detected_objects")
            stats['total_objects'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM notifications")
            stats['total_notifications'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM system_metrics")
            stats['total_metrics'] = cursor.fetchone()[0]
            
            # Database size
            db_file = Path(self.db_path)
            if db_file.exists():
                stats['database_size_mb'] = db_file.stat().st_size / (1024 * 1024)
            
            return stats
    
    def close(self):
        """Close database connections."""
        logger.info("Database service closed")


