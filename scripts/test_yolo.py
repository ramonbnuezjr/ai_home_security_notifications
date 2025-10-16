#!/usr/bin/env python3
"""
Test script to verify YOLOv8 installation and download model.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import get_logger, setup_logging
from src.services.object_detection_service import ObjectDetectionService
import cv2
import numpy as np


def test_yolo_installation():
    """Test YOLOv8 installation and model download."""
    setup_logging(log_level='INFO', log_dir='logs')
    logger = get_logger('yolo_test')
    
    logger.info('='*60)
    logger.info('YOLO INSTALLATION TEST')
    logger.info('='*60)
    logger.info('')
    
    try:
        # Load configuration
        config = get_config('config/system_config.yaml')
        logger.info('✓ Configuration loaded')
        
        # Initialize object detection service
        logger.info('Initializing ObjectDetectionService...')
        detector = ObjectDetectionService(config)
        
        # Initialize the model (will download if needed)
        logger.info('Loading YOLOv8 model (this may take a while on first run)...')
        if not detector.initialize():
            logger.error('❌ Failed to initialize YOLO')
            return False
        
        logger.info('✓ YOLOv8 model loaded successfully')
        
        # Test inference on a dummy image
        logger.info('Testing inference...')
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        result = detector.detect_objects(test_image)
        
        if result is not None:
            logger.info(f'✓ Inference successful!')
            logger.info(f'  - Inference time: {result.inference_time*1000:.1f}ms')
            logger.info(f'  - Objects detected: {len(result.objects)}')
        else:
            logger.warning('⚠ No detection result (this is OK for random image)')
        
        # Get statistics
        stats = detector.get_statistics()
        logger.info('')
        logger.info('MODEL INFORMATION:')
        logger.info(f'  Model: {stats["model"]}')
        logger.info(f'  Classes: {stats["num_classes"]}')
        logger.info(f'  Confidence threshold: {stats["confidence_threshold"]}')
        logger.info(f'  Target classes: {stats["target_classes"]}')
        
        # List available classes
        available_classes = detector.get_available_classes()
        logger.info('')
        logger.info(f'AVAILABLE DETECTION CLASSES ({len(available_classes)}):')
        logger.info(f'{", ".join(available_classes[:20])}...')
        
        logger.info('')
        logger.info('='*60)
        logger.info('✓ ALL TESTS PASSED')
        logger.info('='*60)
        logger.info('')
        logger.info('YOLOv8 is ready to use!')
        logger.info('Run: python scripts/live_motion_detection.py')
        logger.info('')
        
        return True
        
    except ImportError as e:
        logger.error(f'❌ Import error: {e}')
        logger.error('Make sure ultralytics is installed: pip install ultralytics')
        return False
        
    except Exception as e:
        logger.error(f'❌ Test failed: {e}', exc_info=True)
        return False


if __name__ == '__main__':
    success = test_yolo_installation()
    sys.exit(0 if success else 1)

