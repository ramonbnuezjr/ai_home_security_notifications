#!/usr/bin/env python3
"""
Motion detection test script.

Tests motion detection with the camera service.
Saves frames with detected motion for verification.
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
import cv2


def test_motion_detection_basic(config, duration=30, save_frames=True):
    """
    Test basic motion detection.
    
    Args:
        config: System configuration
        duration: Test duration in seconds
        save_frames: Whether to save frames with motion
    """
    logger = get_logger('test_motion')
    logger.info('='*60)
    logger.info('MOTION DETECTION BASIC TEST')
    logger.info('='*60)
    
    # Create output directory for saved frames
    output_dir = Path('motion_test_output')
    if save_frames:
        output_dir.mkdir(exist_ok=True)
        logger.info(f'Saving motion frames to: {output_dir}')
    
    # Initialize services
    camera = CameraService(config)
    motion_detector = MotionDetectionService(config)
    
    # Start camera
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    try:
        logger.info(f'Running motion detection for {duration} seconds...')
        logger.info('Move in front of the camera to trigger detection!')
        logger.info('-'*60)
        
        start_time = time.time()
        frame_count = 0
        motion_event_count = 0
        last_motion_time = 0
        saved_frame_count = 0
        
        while time.time() - start_time < duration:
            # Get frame from camera
            frame_data = camera.get_latest_frame()
            
            if frame_data is None:
                time.sleep(0.01)
                continue
            
            timestamp, frame = frame_data
            frame_count += 1
            
            # Detect motion
            motion_event = motion_detector.detect_motion(frame)
            
            if motion_event is not None:
                motion_event_count += 1
                last_motion_time = timestamp
                
                # Log motion event
                logger.info(
                    f'🎯 MOTION DETECTED: {motion_event}',
                    total_objects=len(motion_event.bounding_boxes),
                    largest_area=max(motion_event.areas) if motion_event.areas else 0
                )
                
                # Save frame with motion visualization
                if save_frames and saved_frame_count < 50:  # Limit to 50 frames
                    annotated_frame = motion_detector.draw_motion(frame, motion_event)
                    output_path = output_dir / f'motion_{motion_event_count:04d}.jpg'
                    cv2.imwrite(str(output_path), annotated_frame)
                    saved_frame_count += 1
                    
                    if saved_frame_count == 1:
                        logger.info(f'💾 Saved first motion frame to: {output_path}')
            
            # Progress update every 5 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and frame_count % 10 == 0:
                logger.info(
                    f'Progress: {elapsed:.0f}s | Frames: {frame_count} | '
                    f'Motion events: {motion_event_count}'
                )
            
            # Small delay to prevent tight loop
            time.sleep(0.01)
        
        # Final statistics
        elapsed = time.time() - start_time
        stats = motion_detector.get_statistics()
        
        logger.info('')
        logger.info('='*60)
        logger.info('TEST RESULTS')
        logger.info('='*60)
        logger.info(f'Duration: {elapsed:.1f}s')
        logger.info(f'Frames processed: {frame_count}')
        logger.info(f'Motion events detected: {motion_event_count}')
        logger.info(f'Detection rate: {(motion_event_count/frame_count)*100:.1f}%')
        logger.info(f'Saved frames: {saved_frame_count}')
        
        logger.info('')
        logger.info('Motion Detector Statistics:')
        logger.info(f'  Algorithm: {stats["algorithm"]}')
        logger.info(f'  Sensitivity: {stats["sensitivity"]}')
        logger.info(f'  Area limits: {stats["min_area"]}-{stats["max_area"]} pixels')
        logger.info(f'  Total frames: {stats["frame_count"]}')
        logger.info(f'  Motion detected: {stats["motion_count"]} times')
        logger.info(f'  Motion rate: {stats["motion_rate"]*100:.2f}%')
        
        if motion_event_count > 0:
            logger.info('')
            logger.info('✓ Motion detection test PASSED')
            logger.info(f'📁 Check saved frames in: {output_dir}/')
            return True
        else:
            logger.warning('')
            logger.warning('⚠ No motion detected during test')
            logger.warning('Try moving in front of the camera')
            return False
            
    except KeyboardInterrupt:
        logger.info('\n\nTest interrupted by user')
        return False
        
    finally:
        camera.stop()
        logger.info('Camera stopped')


def test_motion_sensitivity(config, duration=60):
    """
    Test motion detection with different sensitivity levels.
    
    Args:
        config: System configuration
        duration: Duration per sensitivity test
    """
    logger = get_logger('test_motion')
    logger.info('='*60)
    logger.info('MOTION DETECTION SENSITIVITY TEST')
    logger.info('='*60)
    
    sensitivity_levels = [0.3, 0.5, 0.7, 0.9]
    
    camera = CameraService(config)
    motion_detector = MotionDetectionService(config)
    
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    try:
        for sensitivity in sensitivity_levels:
            logger.info('')
            logger.info(f'Testing with sensitivity: {sensitivity}')
            logger.info('-'*60)
            
            motion_detector.update_sensitivity(sensitivity)
            
            start_time = time.time()
            frame_count = 0
            motion_count = 0
            
            while time.time() - start_time < duration:
                frame_data = camera.get_latest_frame()
                
                if frame_data is not None:
                    _, frame = frame_data
                    frame_count += 1
                    
                    motion_event = motion_detector.detect_motion(frame)
                    if motion_event is not None:
                        motion_count += 1
                
                time.sleep(0.01)
            
            detection_rate = (motion_count / frame_count * 100) if frame_count > 0 else 0
            logger.info(
                f'Sensitivity {sensitivity}: {motion_count} detections in {frame_count} frames '
                f'({detection_rate:.1f}%)'
            )
        
        logger.info('')
        logger.info('✓ Sensitivity test completed')
        return True
        
    finally:
        camera.stop()


def test_motion_continuous(config, save_interval=5):
    """
    Run continuous motion detection (until interrupted).
    
    Args:
        config: System configuration
        save_interval: Save a frame every N seconds
    """
    logger = get_logger('test_motion')
    logger.info('='*60)
    logger.info('CONTINUOUS MOTION DETECTION')
    logger.info('='*60)
    logger.info('Press Ctrl+C to stop')
    logger.info('')
    
    output_dir = Path('motion_continuous_output')
    output_dir.mkdir(exist_ok=True)
    
    camera = CameraService(config)
    motion_detector = MotionDetectionService(config)
    
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    try:
        start_time = time.time()
        last_save_time = 0
        frame_count = 0
        motion_count = 0
        
        while True:
            frame_data = camera.get_latest_frame()
            
            if frame_data is not None:
                timestamp, frame = frame_data
                frame_count += 1
                
                motion_event = motion_detector.detect_motion(frame)
                
                if motion_event is not None:
                    motion_count += 1
                    logger.info(f'🎯 {motion_event}')
                    
                    # Save frame at intervals
                    if timestamp - last_save_time >= save_interval:
                        annotated_frame = motion_detector.draw_motion(frame, motion_event)
                        output_path = output_dir / f'motion_{int(timestamp)}.jpg'
                        cv2.imwrite(str(output_path), annotated_frame)
                        last_save_time = timestamp
                
                # Status update every 30 seconds
                elapsed = time.time() - start_time
                if int(elapsed) % 30 == 0 and frame_count % 10 == 0:
                    rate = (motion_count / frame_count * 100) if frame_count > 0 else 0
                    logger.info(f'Status: {int(elapsed)}s | Frames: {frame_count} | '
                               f'Motion: {motion_count} ({rate:.1f}%)')
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        logger.info('\n\nStopping...')
        
        elapsed = time.time() - start_time
        stats = motion_detector.get_statistics()
        
        logger.info('')
        logger.info('='*60)
        logger.info('FINAL STATISTICS')
        logger.info('='*60)
        logger.info(f'Runtime: {elapsed:.0f}s')
        logger.info(f'Frames: {frame_count}')
        logger.info(f'Motion events: {motion_count}')
        logger.info(f'Detection rate: {(motion_count/frame_count)*100:.1f}%')
        logger.info(f'Saved frames: {output_dir}/')
        
        return True
        
    finally:
        camera.stop()


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test motion detection')
    parser.add_argument('--config', default='config/system_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--test', choices=['basic', 'sensitivity', 'continuous'],
                        default='basic', help='Test to run')
    parser.add_argument('--duration', type=int, default=30,
                        help='Test duration in seconds')
    parser.add_argument('--no-save', action='store_true',
                        help='Do not save motion frames')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level, log_dir='logs')
    logger = get_logger('test_motion')
    
    # Load configuration
    try:
        config = get_config(args.config)
        logger.info(f'Configuration loaded from {args.config}')
    except Exception as e:
        logger.error(f'Failed to load configuration: {e}')
        return 1
    
    # Run selected test
    try:
        if args.test == 'basic':
            success = test_motion_detection_basic(
                config,
                duration=args.duration,
                save_frames=not args.no_save
            )
        elif args.test == 'sensitivity':
            success = test_motion_sensitivity(config, duration=args.duration)
        elif args.test == 'continuous':
            success = test_motion_continuous(config)
        else:
            logger.error(f'Unknown test: {args.test}')
            return 1
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f'Test failed with error: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

