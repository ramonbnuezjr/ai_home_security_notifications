#!/usr/bin/env python3
"""
Test detection of small objects like books and toothbrushes.
Uses lower confidence threshold and provides specific guidance.
"""

import sys
import os
from pathlib import Path
import cv2
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import get_logger, setup_logging
from src.services.camera_service import CameraService
from src.services.object_detection_service import ObjectDetectionService


def test_small_objects():
    """Test detection of small household objects."""
    setup_logging(log_level='INFO', log_dir='logs')
    logger = get_logger('small_objects')
    
    print("\n" + "="*60)
    print("SMALL OBJECT DETECTION TEST")
    print("="*60)
    print("\nThis test uses confidence=0.15 (very low) to detect small objects")
    print("\nOBJECT PRESENTATION TIPS:")
    print("\n📚 BOOK:")
    print("  - Show the COVER (not spine)")
    print("  - Hold 12-18 inches from camera")
    print("  - Fill about 20% of frame")
    print("  - Keep cover flat and visible")
    print("\n🪥 TOOTHBRUSH:")
    print("  - Hold HORIZONTALLY (sideways)")
    print("  - Get closer: 8-12 inches")
    print("  - Against contrasting background")
    print("  - Make sure it's well-lit")
    print("\n📱 OTHER OBJECTS TO TRY:")
    print("  - Scissors (hold open, sideways)")
    print("  - Fork/Knife/Spoon (hold close)")
    print("  - Clock (show face clearly)")
    print("  - Vase (on table, well-lit)")
    print("="*60)
    
    try:
        # Load configuration
        config = get_config('config/system_config.yaml')
        
        # Initialize services
        camera = CameraService(config)
        detector = ObjectDetectionService(config)
        
        # Use very low confidence for small objects
        detector.confidence_threshold = 0.15
        logger.info('Using confidence threshold: 0.15 (very sensitive)')
        
        # Initialize
        if not detector.initialize():
            logger.error('Failed to initialize detector')
            return False
        
        # Start camera
        if not camera.start():
            logger.error('Failed to start camera')
            return False
        
        logger.info('Camera started. Get ready...')
        time.sleep(2)
        
        test_objects = [
            "📚 BOOK - Show cover clearly",
            "🪥 TOOTHBRUSH - Hold horizontally",
            "✂️ SCISSORS - Hold open, sideways",
            "🍴 FORK/SPOON - Hold close-up",
            "⏰ CLOCK or other object"
        ]
        
        for i, obj_name in enumerate(test_objects, 1):
            print(f"\n{'='*60}")
            print(f"Shot {i}/5: {obj_name}")
            print(f"{'='*60}")
            print(f"Get ready in 3 seconds...")
            time.sleep(3)
            print("📸 CAPTURING...")
            
            # Get frame
            frame_data = camera.get_latest_frame()
            if frame_data is None:
                logger.warning(f'No frame available for shot {i}')
                continue
            
            timestamp, frame = frame_data
            
            # Detect objects
            result = detector.detect_objects(frame)
            
            detected_anything = False
            if result and len(result.objects) > 0:
                print(f"✅ DETECTED {len(result.objects)} OBJECT(S):")
                for obj in result.objects:
                    print(f"   • {obj.class_name}: {obj.confidence:.1%} confident")
                detected_anything = True
                
                # Save annotated frame
                annotated = detector.draw_detections(frame, result)
                filename = f'small_object_{i}_{obj_name[:20]}.jpg'
                filename = filename.replace(' ', '_').replace('/', '_')
                cv2.imwrite(filename, annotated)
                print(f"   💾 Saved: {filename}")
            else:
                print(f"❌ No objects detected")
                # Save frame anyway
                filename = f'small_object_{i}_empty.jpg'
                cv2.imwrite(filename, frame)
                print(f"   💾 Saved frame: {filename}")
            
            if not detected_anything:
                print("\n💡 TIPS:")
                print("   - Move object closer to camera")
                print("   - Ensure good lighting")
                print("   - Make object larger in frame (15-30%)")
                print("   - Check focus (not blurry)")
        
        camera.stop()
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)
        print("\nCheck the saved images: small_object_*.jpg")
        print("\nIf objects weren't detected:")
        print("  1. Try holding them CLOSER (fill more of frame)")
        print("  2. Improve lighting")
        print("  3. Show characteristic features (book cover, not spine)")
        print("  4. Keep objects still and in focus")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f'Test failed: {e}', exc_info=True)
        return False


if __name__ == '__main__':
    success = test_small_objects()
    sys.exit(0 if success else 1)

