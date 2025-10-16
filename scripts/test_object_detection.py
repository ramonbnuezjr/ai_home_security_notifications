#!/usr/bin/env python3
"""
Test object detection with adjustable confidence threshold.
Helps identify why certain objects aren't being detected.
"""

import sys
import os
from pathlib import Path
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import get_logger, setup_logging
from src.services.camera_service import CameraService
from src.services.object_detection_service import ObjectDetectionService


def test_detection_with_confidence(confidence_threshold=0.3, config_path='config/system_config.yaml', disable_filters=False):
    """Test object detection with adjustable confidence."""
    setup_logging(log_level='INFO', log_dir='logs')
    logger = get_logger('object_test')
    
    logger.info('='*60)
    logger.info('OBJECT DETECTION TEST')
    logger.info('='*60)
    logger.info(f'Confidence threshold: {confidence_threshold}')
    logger.info(f'Config file: {config_path}')
    if disable_filters:
        logger.info('Class filtering: DISABLED (detecting all 80 classes)')
    logger.info('')
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Disable class filtering if requested
        if disable_filters:
            if 'ai' in config and 'classification' in config['ai']:
                config['ai']['classification']['target_classes'] = []
                config['ai']['classification']['ignore_classes'] = []
                logger.info('✓ Removed class filters - will detect ALL objects')
        
        # Initialize services
        camera = CameraService(config)
        detector = ObjectDetectionService(config)
        
        # Override confidence threshold
        detector.confidence_threshold = confidence_threshold
        logger.info(f'Using confidence threshold: {confidence_threshold}')
        
        # Initialize
        if not detector.initialize():
            logger.error('Failed to initialize detector')
            return False
        
        # Start camera
        if not camera.start():
            logger.error('Failed to start camera')
            return False
        
        logger.info('')
        logger.info('Camera started. Taking 5 test shots...')
        logger.info('Hold objects clearly in view of camera!')
        logger.info('')
        
        import time
        time.sleep(2)  # Let camera adjust
        
        for i in range(5):
            logger.info(f'Shot {i+1}/5 in 2 seconds...')
            time.sleep(2)
            
            # Get frame
            frame_data = camera.get_latest_frame()
            if frame_data is None:
                logger.warning(f'No frame available for shot {i+1}')
                continue
            
            timestamp, frame = frame_data
            
            # Detect objects
            result = detector.detect_objects(frame)
            
            if result and len(result.objects) > 0:
                logger.info(f'✓ DETECTED {len(result.objects)} OBJECTS:')
                for obj in result.objects:
                    logger.info(f'  - {obj.class_name}: {obj.confidence:.3f}')
                
                # Save annotated frame
                annotated = detector.draw_detections(frame, result)
                filename = f'detection_test_{i+1}.jpg'
                cv2.imwrite(filename, annotated)
                logger.info(f'  Saved: {filename}')
            else:
                logger.warning(f'✗ No objects detected in shot {i+1}')
                # Save frame anyway for debugging
                filename = f'detection_test_{i+1}_empty.jpg'
                cv2.imwrite(filename, frame)
                logger.info(f'  Saved frame: {filename}')
            
            logger.info('')
        
        camera.stop()
        
        logger.info('='*60)
        logger.info('TEST COMPLETE')
        logger.info('='*60)
        logger.info('Check the saved images: detection_test_*.jpg')
        logger.info('')
        
        return True
        
    except Exception as e:
        logger.error(f'Test failed: {e}', exc_info=True)
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Test object detection')
    parser.add_argument('--confidence', type=float, default=0.3,
                        help='Confidence threshold (0.0-1.0, default: 0.3)')
    parser.add_argument('--config', default='config/system_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--all-classes', action='store_true',
                        help='Detect ALL 80 classes (ignore target_classes filter)')
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("OBJECT DETECTION TROUBLESHOOTING")
    print(f"{'='*60}")
    print("\nTIPS FOR GETTING OBJECTS DETECTED:")
    print("1. Hold objects 1-2 feet from camera")
    print("2. Ensure good lighting")
    print("3. Hold objects against contrasting background")
    print("4. Objects should fill ~10-30% of frame")
    print("5. Keep objects in focus")
    print("\nEASY OBJECTS TO TEST:")
    print("- Cell phone (hold it up)")
    print("- Laptop (on desk)")
    print("- Bottle (hold in hand)")
    print("- Cup (on table)")
    print("- Book (hold up cover)")
    print("- Keyboard, mouse (on desk)")
    
    if args.all_classes:
        print("\n⚠️  --all-classes enabled: Will detect ALL 80 object types")
        print("   (ignoring target_classes filter from config)")
    
    print(f"\n{'='*60}\n")
    
    success = test_detection_with_confidence(
        confidence_threshold=args.confidence,
        config_path=args.config,
        disable_filters=args.all_classes
    )
    sys.exit(0 if success else 1)

