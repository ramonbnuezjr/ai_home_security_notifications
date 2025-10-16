#!/usr/bin/env python3
"""
Live motion detection visualization.

Displays real-time video feed with motion detection overlays.
Requires display/X server (run on Pi with display connected).
"""

import sys
import os
from pathlib import Path
import time
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import get_logger, setup_logging
from src.services.camera_service import CameraService
from src.services.motion_detection_service import MotionDetectionService
from src.services.object_detection_service import ObjectDetectionService
import cv2
import numpy as np


def draw_info_panel(frame, stats, motion_event=None, detection_stats=None):
    """
    Draw information panel on frame.
    
    Args:
        frame: Input frame
        stats: Motion detector statistics
        motion_event: Current motion event (if any)
        detection_stats: Object detection statistics (if any)
    """
    # Create semi-transparent overlay
    overlay = frame.copy()
    
    # Adjust panel size if we have detection stats
    panel_height = 250 if detection_stats else 200
    cv2.rectangle(overlay, (10, 10), (450, panel_height), (0, 0, 0), -1)
    frame_with_overlay = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
    
    # Draw info text
    y_offset = 40
    line_height = 30
    
    info_lines = [
        f"Algorithm: {stats['algorithm'].upper()}",
        f"Sensitivity: {stats['sensitivity']:.2f}",
        f"Area: {stats['min_area']}-{stats['max_area']}px",
        f"Frames: {stats['frame_count']}",
        f"Motion: {stats['motion_count']} ({stats['motion_rate']*100:.1f}%)",
    ]
    
    if motion_event:
        info_lines.append(f"Motion Regions: {len(motion_event.bounding_boxes)}")
        info_lines.append(f"Motion %: {motion_event.motion_percentage:.1f}%")
        
        # Add detected objects info
        if motion_event.detected_objects and hasattr(motion_event.detected_objects, 'objects'):
            detected = motion_event.detected_objects.objects
            if len(detected) > 0:
                obj_summary = ", ".join([obj.class_name for obj in detected[:3]])
                if len(detected) > 3:
                    obj_summary += f" +{len(detected)-3}"
                info_lines.append(f"Detected: {obj_summary}")
    
    for i, line in enumerate(info_lines):
        cv2.putText(
            frame_with_overlay,
            line,
            (20, y_offset + i * line_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    # Draw controls help
    help_text = [
        "Q: Quit | R: Reset | S: Screenshot",
        "1-9: Sensitivity | O: Toggle YOLO"
    ]
    
    help_y = frame.shape[0] - 50
    for i, line in enumerate(help_text):
        cv2.putText(
            frame_with_overlay,
            line,
            (10, help_y + i * 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1
        )
    
    return frame_with_overlay


def live_motion_detection(config, show_mask=True, fps_limit=30, enable_yolo=True, confidence_threshold=None, all_classes=False, yolo_skip_frames=0):
    """
    Run live motion detection with visualization.
    
    Args:
        config: System configuration
        show_mask: Whether to show motion mask window
        fps_limit: Maximum FPS for display
        enable_yolo: Whether to enable YOLOv8 object detection
        confidence_threshold: Override YOLO confidence threshold (optional)
        all_classes: Detect all 80 classes (ignore target_classes filter)
        yolo_skip_frames: Run YOLO every N motion frames (0=every frame)
    """
    logger = get_logger('live_motion')
    logger.info('='*60)
    logger.info('LIVE MOTION DETECTION + OBJECT DETECTION')
    logger.info('='*60)
    logger.info('Starting live visualization...')
    logger.info('Controls: Q=Quit, R=Reset, S=Screenshot, 1-9=Sensitivity, O=Toggle YOLO')
    logger.info('')
    
    # Initialize services
    camera = CameraService(config)
    motion_detector = MotionDetectionService(config)
    
    # Disable class filtering if requested
    if all_classes:
        if 'ai' in config and 'classification' in config['ai']:
            config['ai']['classification']['target_classes'] = []
            config['ai']['classification']['ignore_classes'] = []
            logger.info('Class filtering disabled - will detect ALL 80 object types')
    
    # Initialize object detection if enabled
    object_detector = None
    if enable_yolo:
        try:
            logger.info('Initializing YOLOv8 object detection...')
            object_detector = ObjectDetectionService(config)
            if object_detector.initialize():
                # Override confidence threshold if specified
                if confidence_threshold is not None:
                    object_detector.update_confidence_threshold(confidence_threshold)
                    logger.info(f'✓ YOLOv8 initialized with confidence {confidence_threshold}')
                else:
                    logger.info('✓ YOLOv8 initialized successfully')
            else:
                logger.warning('⚠ YOLOv8 initialization failed, continuing without object detection')
                object_detector = None
        except Exception as e:
            logger.warning(f'⚠ Could not initialize YOLO: {e}')
            object_detector = None
    
    # Start camera
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    # Create windows
    cv2.namedWindow('Motion Detection', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Motion Detection', 1280, 720)
    
    if show_mask:
        cv2.namedWindow('Motion Mask', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Motion Mask', 640, 480)
    
    try:
        logger.info('✓ Live view started')
        logger.info('Move in front of the camera to trigger motion detection!')
        logger.info('')
        
        screenshot_count = 0
        show_mask_window = show_mask
        frame_time = 1.0 / fps_limit
        last_frame_time = 0
        yolo_enabled = (object_detector is not None)
        yolo_frame_skip = yolo_skip_frames  # Run YOLO every N motion frames (0 = every frame)
        motion_frame_count = 0
        
        if yolo_frame_skip > 0:
            logger.info(f'YOLO frame skipping enabled: running every {yolo_frame_skip + 1} motion frames')
        
        while True:
            loop_start = time.time()
            
            # Get frame from camera
            frame_data = camera.get_latest_frame()
            
            if frame_data is None:
                time.sleep(0.01)
                continue
            
            timestamp, frame = frame_data
            
            # Detect motion
            motion_event = motion_detector.detect_motion(frame)
            
            # Detect objects if motion detected and YOLO enabled
            if motion_event is not None and yolo_enabled and object_detector is not None:
                # Frame skipping: only run YOLO every N motion frames for better performance
                motion_frame_count += 1
                if yolo_frame_skip == 0 or (motion_frame_count % (yolo_frame_skip + 1)) == 0:
                    detection_result = object_detector.detect_objects(frame, motion_event.frame_id)
                    motion_event.detected_objects = detection_result
            
            # Create display frame
            display_frame = frame.copy()
            motion_mask = None
            
            if motion_event is not None:
                # Draw motion boxes (semi-transparent)
                for (x, y, w, h) in motion_event.bounding_boxes:
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (128, 128, 128), 1)
                
                # Draw contours
                cv2.drawContours(display_frame, motion_event.contours, -1, (0, 255, 255), 1)
                
                # Draw detected objects (if any)
                if motion_event.detected_objects and hasattr(motion_event.detected_objects, 'objects'):
                    if len(motion_event.detected_objects.objects) > 0:
                        display_frame = object_detector.draw_detections(
                            display_frame,
                            motion_event.detected_objects,
                            show_confidence=True,
                            color_by_class=True
                        )
                
                # Status indicator
                cv2.circle(display_frame, (frame.shape[1] - 30, 30), 15, (0, 255, 0), -1)
                cv2.putText(
                    display_frame,
                    'MOTION',
                    (frame.shape[1] - 130, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
                # Get motion mask for display
                if show_mask_window:
                    # Recreate motion mask from contours for visualization
                    motion_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                    cv2.drawContours(motion_mask, motion_event.contours, -1, 255, -1)
            else:
                # No motion indicator
                cv2.circle(display_frame, (frame.shape[1] - 30, 30), 15, (128, 128, 128), -1)
            
            # Draw info panel
            stats = motion_detector.get_statistics()
            detection_stats = object_detector.get_statistics() if object_detector else None
            display_frame = draw_info_panel(display_frame, stats, motion_event, detection_stats)
            
            # Add YOLO status indicator
            if yolo_enabled:
                cv2.putText(
                    display_frame,
                    'YOLO: ON',
                    (frame.shape[1] - 130, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
            else:
                cv2.putText(
                    display_frame,
                    'YOLO: OFF',
                    (frame.shape[1] - 130, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (128, 128, 128),
                    2
                )
            
            # Add timestamp
            timestamp_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            cv2.putText(
                display_frame,
                timestamp_text,
                (frame.shape[1] - 250, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1
            )
            
            # Show frames
            cv2.imshow('Motion Detection', display_frame)
            
            if show_mask_window and motion_mask is not None:
                # Create colored version of mask for better visualization
                motion_mask_colored = cv2.applyColorMap(motion_mask, cv2.COLORMAP_HOT)
                cv2.imshow('Motion Mask', motion_mask_colored)
            elif show_mask_window:
                # Show blank mask
                blank_mask = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
                cv2.imshow('Motion Mask', blank_mask)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                logger.info('Quit requested')
                break
            elif key == ord('r'):  # Reset
                logger.info('Resetting motion detector...')
                motion_detector.reset()
            elif key == ord('s'):  # Screenshot
                screenshot_count += 1
                filename = f'screenshot_{screenshot_count:04d}.jpg'
                cv2.imwrite(filename, display_frame)
                logger.info(f'💾 Screenshot saved: {filename}')
            elif key == ord('o'):  # Toggle YOLO
                if object_detector is not None:
                    yolo_enabled = not yolo_enabled
                    logger.info(f'YOLO detection: {"ON" if yolo_enabled else "OFF"}')
                else:
                    logger.warning('YOLO not available')
            elif key == ord('m'):  # Toggle mask
                show_mask_window = not show_mask_window
                if not show_mask_window:
                    cv2.destroyWindow('Motion Mask')
                else:
                    cv2.namedWindow('Motion Mask', cv2.WINDOW_NORMAL)
                    cv2.resizeWindow('Motion Mask', 640, 480)
                logger.info(f'Mask display: {"ON" if show_mask_window else "OFF"}')
            elif ord('1') <= key <= ord('9'):  # Sensitivity 0.1 - 0.9
                sensitivity = (key - ord('0')) / 10.0
                motion_detector.update_sensitivity(sensitivity)
                logger.info(f'Sensitivity updated to: {sensitivity}')
            
            # Maintain FPS limit
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            last_frame_time = time.time()
        
        # Final statistics
        stats = motion_detector.get_statistics()
        logger.info('')
        logger.info('='*60)
        logger.info('SESSION STATISTICS')
        logger.info('='*60)
        logger.info(f'Total frames: {stats["frame_count"]}')
        logger.info(f'Motion detected: {stats["motion_count"]} times')
        logger.info(f'Detection rate: {stats["motion_rate"]*100:.1f}%')
        logger.info(f'Screenshots saved: {screenshot_count}')
        
        if object_detector is not None:
            obj_stats = object_detector.get_statistics()
            logger.info('')
            logger.info('OBJECT DETECTION STATISTICS')
            logger.info(f'Objects detected: {obj_stats["detection_count"]} times')
            logger.info(f'Avg inference time: {obj_stats["avg_inference_time"]*1000:.1f}ms')
        
        logger.info('')
        
        return True
        
    except KeyboardInterrupt:
        logger.info('\n\nInterrupted by user')
        return True
        
    except Exception as e:
        logger.error(f'Error during live detection: {e}', exc_info=True)
        return False
        
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        logger.info('Live view stopped')


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Live motion detection visualization')
    parser.add_argument('--config', default='config/system_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--no-mask', action='store_true',
                        help='Do not show motion mask window')
    parser.add_argument('--fps', type=int, default=30,
                        help='Display FPS limit')
    parser.add_argument('--no-yolo', action='store_true',
                        help='Disable YOLOv8 object detection')
    parser.add_argument('--confidence', type=float, default=None,
                        help='YOLO confidence threshold (0.0-1.0, default: from config)')
    parser.add_argument('--all-classes', action='store_true',
                        help='Detect ALL 80 classes (ignore target_classes filter)')
    parser.add_argument('--yolo-skip', type=int, default=0,
                        help='Run YOLO every N motion frames (0=every frame, 2=every 2nd frame, etc.)')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level, log_dir='logs')
    logger = get_logger('live_motion')
    
    # Load configuration
    try:
        config = get_config(args.config)
        logger.info(f'Configuration loaded from {args.config}')
    except Exception as e:
        logger.error(f'Failed to load configuration: {e}')
        return 1
    
    # Run live detection
    try:
        success = live_motion_detection(
            config,
            show_mask=not args.no_mask,
            fps_limit=args.fps,
            enable_yolo=not args.no_yolo,
            confidence_threshold=args.confidence,
            all_classes=args.all_classes,
            yolo_skip_frames=args.yolo_skip
        )
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f'Failed to run live detection: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

