"""
Event logger service for integrating database logging into detection system.
"""

import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from src.services.database_service import (
    DatabaseService, Event, DetectedObject, NotificationRecord, SystemMetric
)

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Service for logging events to the database.
    Integrates with existing motion detection and notification services.
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize event logger.
        
        Args:
            db_service: Database service instance
        """
        self.db = db_service
        logger.info("Event logger initialized")
    
    def log_motion_event(
        self,
        motion_percentage: float,
        zone_name: Optional[str] = None,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Log a motion detection event.
        
        Args:
            motion_percentage: Percentage of frame with motion
            zone_name: Name of detection zone
            image_path: Path to captured image
            video_path: Path to video clip
            metadata: Additional metadata
            
        Returns:
            event_id: ID of created event
        """
        severity = self._calculate_motion_severity(motion_percentage)
        
        event = Event(
            timestamp=datetime.now(),
            event_type='motion',
            severity=severity,
            zone_name=zone_name,
            motion_percentage=motion_percentage,
            image_path=image_path,
            video_path=video_path,
            metadata=metadata
        )
        
        event_id = self.db.create_event(event)
        logger.debug(f"Motion event logged: {event_id}")
        return event_id
    
    def log_object_detection_event(
        self,
        detected_objects: List[dict],
        motion_percentage: Optional[float] = None,
        zone_name: Optional[str] = None,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Log an object detection event.
        
        Args:
            detected_objects: List of detected objects with class_name, confidence, bbox, threat_level
            motion_percentage: Motion percentage if available
            zone_name: Name of detection zone
            image_path: Path to captured image
            video_path: Path to video clip
            metadata: Additional metadata
            
        Returns:
            event_id: ID of created event
        """
        # Calculate overall threat level
        threat_level = self._calculate_threat_level(detected_objects)
        severity = self._threat_to_severity(threat_level)
        
        # Create event
        event = Event(
            timestamp=datetime.now(),
            event_type='object_detected',
            severity=severity,
            zone_name=zone_name,
            motion_percentage=motion_percentage,
            threat_level=threat_level,
            image_path=image_path,
            video_path=video_path,
            metadata=metadata
        )
        
        # Create detected object records
        objects = [
            DetectedObject(
                class_name=obj.get('class_name', obj.get('label', 'unknown')),
                confidence=obj.get('confidence', 0.0),
                bbox_x1=obj.get('bbox', [0,0,0,0])[0] if obj.get('bbox') else None,
                bbox_y1=obj.get('bbox', [0,0,0,0])[1] if obj.get('bbox') else None,
                bbox_x2=obj.get('bbox', [0,0,0,0])[2] if obj.get('bbox') else None,
                bbox_y2=obj.get('bbox', [0,0,0,0])[3] if obj.get('bbox') else None,
                threat_level=obj.get('threat_level', 'low')
            )
            for obj in detected_objects
        ]
        
        event_id = self.db.create_event(event, objects)
        logger.debug(f"Object detection event logged: {event_id} with {len(objects)} objects")
        return event_id
    
    def log_notification(
        self,
        event_id: int,
        channel: str,
        priority: str,
        status: str = 'sent',
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Log a notification delivery.
        
        Args:
            event_id: Associated event ID
            channel: Notification channel (email, sms, push, voice)
            priority: Notification priority
            status: Delivery status (sent, failed, pending)
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            notification_id: ID of created notification record
        """
        notification = NotificationRecord(
            event_id=event_id,
            channel=channel,
            priority=priority,
            status=status,
            sent_at=datetime.now() if status == 'sent' else None,
            error_message=error_message,
            metadata=metadata
        )
        
        notification_id = self.db.create_notification(notification)
        logger.debug(f"Notification logged: {notification_id} for event {event_id}")
        return notification_id
    
    def log_system_metrics(
        self,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        disk_usage: Optional[float] = None,
        temperature: Optional[float] = None,
        fps: Optional[float] = None,
        yolo_inference_time: Optional[float] = None,
        active_services: Optional[List[str]] = None
    ) -> int:
        """
        Log system metrics.
        
        Args:
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
            temperature: System temperature in Celsius
            fps: Current FPS
            yolo_inference_time: YOLO inference time in ms
            active_services: List of active service names
            
        Returns:
            metric_id: ID of created metric record
        """
        metric = SystemMetric(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            temperature=temperature,
            fps=fps,
            yolo_inference_time=yolo_inference_time,
            active_services=active_services
        )
        
        metric_id = self.db.create_metric(metric)
        logger.debug(f"System metric logged: {metric_id}")
        return metric_id
    
    def _calculate_motion_severity(self, motion_percentage: float) -> str:
        """Calculate severity based on motion percentage."""
        if motion_percentage > 50:
            return 'high'
        elif motion_percentage > 20:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_threat_level(self, detected_objects: List[dict]) -> str:
        """Calculate overall threat level from detected objects."""
        threat_levels = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        max_threat = 'low'
        max_value = 1
        
        for obj in detected_objects:
            threat = obj.get('threat_level', 'low')
            value = threat_levels.get(threat, 1)
            if value > max_value:
                max_value = value
                max_threat = threat
        
        return max_threat
    
    def _threat_to_severity(self, threat_level: str) -> str:
        """Convert threat level to severity."""
        mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(threat_level, 'low')


