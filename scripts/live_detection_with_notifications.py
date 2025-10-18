#!/usr/bin/env python3
"""
Live motion detection with object classification and notifications.

This script combines all the core features:
- Real-time video capture
- Motion detection
- Object classification (YOLOv8)
- Multi-channel notifications

Press 'Q' to quit
Press 'N' to send a test notification
Press 'S' to toggle notification sending
"""

import sys
import cv2
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.camera_service import CameraService
from src.services.motion_detection_service import MotionDetectionService
from src.services.object_detection_service import ObjectDetectionService
from src.services.notification_manager import NotificationManager
from src.services.database_service import DatabaseService, Event, DetectedObject, NotificationRecord
from src.services.base_notification_service import NotificationContext, NotificationPriority
from src.utils.config import Config
from src.utils.logger import get_logger
from datetime import datetime


def determine_priority(detected_objects, threat_level):
    """Determine notification priority based on detected objects."""
    if not detected_objects:
        return NotificationPriority.LOW
    
    # Check for high-priority objects
    high_priority_objects = ['person', 'car', 'truck', 'knife', 'scissors']
    
    if any(obj.lower() in high_priority_objects for obj in detected_objects):
        return NotificationPriority.HIGH
    
    if threat_level and threat_level.lower() in ['high', 'critical']:
        return NotificationPriority.HIGH
    
    return NotificationPriority.MEDIUM


def main():
    """Main function."""
    logger = get_logger('live_detection_notifications')
    
    print("\n" + "=" * 70)
    print("  🎥 Live Detection with Notifications")
    print("=" * 70)
    print("\nControls:")
    print("  Q - Quit")
    print("  N - Send test notification")
    print("  S - Toggle notification sending")
    print("  O - Toggle YOLO detection")
    print("  3/5/7/9 - Adjust sensitivity")
    print("=" * 70 + "\n")
    
    # Load configuration
    print("Loading configuration...")
    config = Config()
    
    # Initialize services
    print("Initializing services...")
    camera = CameraService(config)
    motion_detector = MotionDetectionService(config)
    object_detector = ObjectDetectionService(config)
    notifier = NotificationManager(config)
    
    # Initialize database
    db_config = config.get('database', {})
    db_path = db_config.get('path', '/home/ramon/security_data/database/security.db')
    fallback_path = db_config.get('fallback_path', '/home/ramon/security_data/database/security.db')
    print(f"Initializing database at {db_path}...")
    db = DatabaseService(db_path, fallback_path)
    
    # Start services
    print("Starting camera...")
    if not camera.start():
        print("❌ Failed to start camera")
        return 1
    
    print("Starting notification manager...")
    notifier.start()
    
    # State
    notifications_enabled = True
    yolo_enabled = True
    last_notification_time = 0
    notification_cooldown = 30  # seconds between notifications
    frame_count = 0
    
    print(f"\n✅ System ready!")
    print(f"   Camera: {camera.resolution}")
    print(f"   Notification services: {len(notifier.services)}")
    print(f"   Database: Connected")
    print(f"   YOLO: {'Enabled' if yolo_enabled else 'Disabled'}")
    print(f"   Notifications: {'Enabled' if notifications_enabled else 'Disabled'}")
    print()
    
    try:
        while True:
            frame_count += 1
            
            # Capture frame
            frame_data = camera.get_frame()
            if frame_data is None:
                print("Failed to get frame")
                break
            
            timestamp, frame = frame_data
            
            # Detect motion
            motion_event = motion_detector.detect_motion(frame)
            
            # Display frame with motion detection
            display_frame = frame.copy()
            
            if motion_event:
                # Draw motion detection
                display_frame = motion_detector.draw_motion(display_frame, motion_event)
                
                # Run object detection if enabled
                if yolo_enabled:
                    detection_result = object_detector.detect_objects(frame)
                    motion_event.detected_objects = detection_result
                    
                    # Draw object detections
                    if detection_result and detection_result.objects:
                        display_frame = object_detector.draw_detections(
                            display_frame,
                            detection_result
                        )
                    
                    # Send notification if enabled and not on cooldown
                    current_time = time.time()
                    if (notifications_enabled and 
                        detection_result and 
                        detection_result.objects and
                        current_time - last_notification_time > notification_cooldown):
                        
                        # Get detected object labels
                        detected_labels = [obj.class_name for obj in detection_result.objects]
                        
                        # Determine priority and threat level
                        threat_level = 'medium'  # Default threat level
                        priority = determine_priority(detected_labels, threat_level)
                        
                        # Save event to database
                        severity_map = {
                            NotificationPriority.LOW: 'low',
                            NotificationPriority.MEDIUM: 'medium',
                            NotificationPriority.HIGH: 'high',
                            NotificationPriority.CRITICAL: 'critical'
                        }
                        
                        event = Event(
                            timestamp=datetime.now(),
                            event_type='object_detected',
                            severity=severity_map.get(priority, 'medium'),
                            zone_name='Camera 1',
                            motion_percentage=motion_event.motion_percentage,
                            threat_level=threat_level,
                            metadata={
                                'detected_objects': detected_labels,
                                'frame_count': frame_count
                            }
                        )
                        
                        # Save detected objects
                        db_objects = [
                            DetectedObject(
                                event_id=0,  # Will be set after event insert
                                class_name=obj.class_name,
                                confidence=obj.confidence,
                                bbox_x1=int(obj.bounding_box[0]),
                                bbox_y1=int(obj.bounding_box[1]),
                                bbox_x2=int(obj.bounding_box[2]),
                                bbox_y2=int(obj.bounding_box[3]),
                                threat_level=threat_level
                            )
                            for obj in detection_result.objects
                        ]
                        
                        # Save to database
                        event_id = db.create_event(event, db_objects)
                        
                        # Create notification context
                        context = NotificationContext(
                            event_type='security_alert',
                            timestamp=current_time,
                            priority=priority,
                            detected_objects=detected_labels,
                            motion_percentage=motion_event.motion_percentage,
                            threat_level=threat_level,
                            zone_name='Camera 1'
                        )
                        
                        # Send notification (async)
                        notifier.send_notification(context, async_mode=True)
                        
                        last_notification_time = current_time
                        
                        print(f"\n📧 Event {event_id} logged and notification sent: {detected_labels} detected!")
                        print(f"   Priority: {priority.value}")
                        print(f"   Motion: {motion_event.motion_percentage:.1f}%")
                        print()
            
            # Add status overlay
            status_y = 60
            cv2.putText(
                display_frame,
                f"Notifications: {'ON' if notifications_enabled else 'OFF'}",
                (10, status_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0) if notifications_enabled else (0, 0, 255),
                2
            )
            
            cv2.putText(
                display_frame,
                f"YOLO: {'ON' if yolo_enabled else 'OFF'}",
                (10, status_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0) if yolo_enabled else (0, 0, 255),
                2
            )
            
            # Show frame
            cv2.imshow('Security Camera - Live Detection', display_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("\nQuitting...")
                break
            
            elif key == ord('n') or key == ord('N'):
                # Send test notification
                print("\n📧 Sending test notification...")
                context = NotificationContext(
                    event_type='system_test',
                    timestamp=time.time(),
                    priority=NotificationPriority.LOW,
                    message='This is a test notification from your security system.',
                    zone_name='Camera 1'
                )
                results = notifier.send_notification(context, async_mode=False, force=True)
                successful = sum(1 for r in results if r.success)
                print(f"   Sent to {successful}/{len(results)} service(s)")
            
            elif key == ord('s') or key == ord('S'):
                # Toggle notifications
                notifications_enabled = not notifications_enabled
                print(f"\n🔔 Notifications {'ENABLED' if notifications_enabled else 'DISABLED'}")
            
            elif key == ord('o') or key == ord('O'):
                # Toggle YOLO
                yolo_enabled = not yolo_enabled
                print(f"\n🎯 YOLO detection {'ENABLED' if yolo_enabled else 'DISABLED'}")
            
            elif key in [ord('3'), ord('5'), ord('7'), ord('9')]:
                # Adjust sensitivity
                sensitivity_map = {ord('3'): 0.3, ord('5'): 0.5, ord('7'): 0.7, ord('9'): 0.9}
                new_sensitivity = sensitivity_map[key]
                motion_detector.update_sensitivity(new_sensitivity)
                print(f"\n🎚️  Sensitivity set to {new_sensitivity}")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        camera.stop()
        notifier.stop()
        cv2.destroyAllWindows()
        
        # Show final statistics
        print("\n" + "=" * 70)
        print("  📊 Session Statistics")
        print("=" * 70)
        
        print(f"\nMotion Detection:")
        motion_stats = motion_detector.get_statistics()
        print(f"  Frames processed: {motion_stats['frame_count']}")
        print(f"  Motion events: {motion_stats['motion_count']}")
        print(f"  Motion rate: {motion_stats['motion_rate']:.1%}")
        
        print(f"\nObject Detection:")
        obj_stats = object_detector.get_statistics()
        print(f"  Detections run: {obj_stats['detection_count']}")
        print(f"  Frames processed: {obj_stats['frame_count']}")
        
        print(f"\nNotifications:")
        notif_stats = notifier.get_statistics()
        for service_name, service_stats in notif_stats['services'].items():
            print(f"  {service_name.upper()}:")
            print(f"    Sent: {service_stats['sent_count']}")
            print(f"    Failed: {service_stats['failed_count']}")
            print(f"    Success rate: {service_stats['success_rate']:.1%}")
        
        print(f"\nDatabase:")
        db_stats = db.get_database_stats()
        print(f"  Total events: {db_stats['total_events']}")
        print(f"  Total objects detected: {db_stats['total_objects']}")
        print(f"  Database size: {db_stats.get('database_size_mb', 0):.2f} MB")
        
        db.close()
        print("\n✅ System stopped cleanly\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

