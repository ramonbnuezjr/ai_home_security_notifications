#!/usr/bin/env python3
"""
Camera hardware test script.

Tests camera connectivity, frame capture, and basic functionality.
Run this script after hardware setup to verify camera is working correctly.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.utils.logger import get_logger, setup_logging
from src.services.camera_service import CameraService
import argparse
import time


def test_camera_basic(config):
    """Test basic camera functionality."""
    logger = get_logger('test_camera')
    logger.info('='*60)
    logger.info('CAMERA BASIC TEST')
    logger.info('='*60)
    
    camera = CameraService(config)
    
    if not camera.test_camera():
        logger.error('❌ Camera basic test FAILED')
        return False
    
    logger.info('✓ Camera basic test PASSED')
    return True


def test_camera_capture(config, num_frames=30, save_sample=False):
    """Test camera capture over time."""
    logger = get_logger('test_camera')
    logger.info('='*60)
    logger.info('CAMERA CAPTURE TEST')
    logger.info('='*60)
    
    camera = CameraService(config)
    
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    try:
        logger.info(f'Capturing {num_frames} frames...')
        captured = 0
        failed = 0
        start_time = time.time()
        
        for i in range(num_frames):
            frame_data = camera.get_frame(timeout=2.0)
            
            if frame_data is None:
                failed += 1
                logger.warning(f'Frame {i+1}/{num_frames}: ❌ FAILED')
            else:
                captured += 1
                timestamp, frame = frame_data
                
                # Save first frame as sample
                if save_sample and i == 0:
                    sample_path = 'test_frame_sample.jpg'
                    camera.capture_image(sample_path)
                    logger.info(f'Sample frame saved to {sample_path}')
                
                if (i + 1) % 10 == 0:
                    logger.info(f'Frame {i+1}/{num_frames}: ✓ OK (shape={frame.shape})')
        
        elapsed = time.time() - start_time
        actual_fps = captured / elapsed if elapsed > 0 else 0
        
        logger.info(f'\nResults:')
        logger.info(f'  Captured: {captured}/{num_frames}')
        logger.info(f'  Failed: {failed}/{num_frames}')
        logger.info(f'  Success rate: {(captured/num_frames)*100:.1f}%')
        logger.info(f'  Actual FPS: {actual_fps:.2f}')
        
        # Get camera info
        info = camera.get_camera_info()
        logger.info(f'\nCamera Info:')
        for key, value in info.items():
            logger.info(f'  {key}: {value}')
        
        success = captured >= num_frames * 0.9  # 90% success rate
        
        if success:
            logger.info('\n✓ Camera capture test PASSED')
        else:
            logger.error('\n❌ Camera capture test FAILED')
        
        return success
        
    finally:
        camera.stop()


def test_camera_performance(config, duration=10):
    """Test camera performance over time."""
    logger = get_logger('test_camera')
    logger.info('='*60)
    logger.info('CAMERA PERFORMANCE TEST')
    logger.info('='*60)
    
    camera = CameraService(config)
    
    if not camera.start():
        logger.error('❌ Failed to start camera')
        return False
    
    try:
        logger.info(f'Running performance test for {duration} seconds...')
        start_time = time.time()
        frame_times = []
        
        while time.time() - start_time < duration:
            loop_start = time.time()
            frame_data = camera.get_latest_frame()
            
            if frame_data is not None:
                frame_times.append(time.time() - loop_start)
            
            time.sleep(0.01)  # Small delay
        
        # Calculate statistics
        if frame_times:
            avg_time = sum(frame_times) / len(frame_times)
            max_time = max(frame_times)
            min_time = min(frame_times)
            
            logger.info(f'\nPerformance Statistics:')
            logger.info(f'  Frames processed: {len(frame_times)}')
            logger.info(f'  Avg frame time: {avg_time*1000:.2f}ms')
            logger.info(f'  Min frame time: {min_time*1000:.2f}ms')
            logger.info(f'  Max frame time: {max_time*1000:.2f}ms')
            logger.info(f'  Theoretical max FPS: {1/avg_time:.2f}')
            
            # Get final camera info
            info = camera.get_camera_info()
            logger.info(f'\nCamera Statistics:')
            logger.info(f'  Total frames: {info["frame_count"]}')
            logger.info(f'  Dropped frames: {info["dropped_frames"]}')
            logger.info(f'  Actual FPS: {info["actual_fps"]}')
            
            success = info["dropped_frames"] < info["frame_count"] * 0.1  # <10% dropped
            
            if success:
                logger.info('\n✓ Camera performance test PASSED')
            else:
                logger.warning('\n⚠ Camera performance test WARNING: High frame drop rate')
            
            return success
        else:
            logger.error('❌ No frames captured during performance test')
            return False
            
    finally:
        camera.stop()


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test camera hardware')
    parser.add_argument('--config', default='config/system_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--test', choices=['basic', 'capture', 'performance', 'all'],
                        default='all', help='Test to run')
    parser.add_argument('--frames', type=int, default=30,
                        help='Number of frames to capture in capture test')
    parser.add_argument('--duration', type=int, default=10,
                        help='Duration in seconds for performance test')
    parser.add_argument('--save-sample', action='store_true',
                        help='Save sample frame during capture test')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level, log_dir='logs')
    logger = get_logger('test_camera')
    
    # Load configuration
    try:
        config = get_config(args.config)
        logger.info(f'Configuration loaded from {args.config}')
    except Exception as e:
        logger.error(f'Failed to load configuration: {e}')
        return 1
    
    # Run tests
    logger.info('\n' + '='*60)
    logger.info('CAMERA HARDWARE TEST SUITE')
    logger.info('='*60 + '\n')
    
    results = {}
    
    if args.test in ['basic', 'all']:
        results['basic'] = test_camera_basic(config)
        print()
    
    if args.test in ['capture', 'all']:
        results['capture'] = test_camera_capture(
            config,
            num_frames=args.frames,
            save_sample=args.save_sample
        )
        print()
    
    if args.test in ['performance', 'all']:
        results['performance'] = test_camera_performance(
            config,
            duration=args.duration
        )
        print()
    
    # Summary
    logger.info('='*60)
    logger.info('TEST SUMMARY')
    logger.info('='*60)
    
    for test_name, passed in results.items():
        status = '✓ PASSED' if passed else '❌ FAILED'
        logger.info(f'{test_name.upper()}: {status}')
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info('\n🎉 All tests PASSED! Camera is ready for use.')
        return 0
    else:
        logger.error('\n❌ Some tests FAILED. Please check camera setup.')
        return 1


if __name__ == '__main__':
    sys.exit(main())

