"""Camera service for video capture and streaming."""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, Any
from threading import Thread, Lock, Event
from queue import Queue, Full
import os

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config import Config


class CameraService:
    """
    Camera service for capturing video frames from Pi Camera.
    
    Uses picamera2 for Raspberry Pi Camera Module (preferred).
    Falls back to OpenCV for USB webcams if picamera2 is not available.
    Runs in a separate thread for non-blocking frame capture.
    """
    
    def __init__(self, config: Config):
        """
        Initialize camera service.
        
        Args:
            config: System configuration object
        """
        self.config = config
        self.logger = get_logger('camera_service')
        
        # Camera configuration
        camera_config = config.get_camera_config()
        self.camera_index = camera_config.get('index', 0)
        self.resolution = (
            camera_config.get('resolution', {}).get('width', 1920),
            camera_config.get('resolution', {}).get('height', 1080)
        )
        self.fps = camera_config.get('fps', 15)
        self.rotation = camera_config.get('rotation', 0)
        self.buffer_size = camera_config.get('buffer_size', 5)
        
        # Determine camera backend
        self.use_picamera2 = PICAMERA2_AVAILABLE and self.camera_index == 0
        
        # Camera state
        self.camera: Optional[Any] = None  # Picamera2 or cv2.VideoCapture
        self.is_running = False
        self.capture_thread: Optional[Thread] = None
        self.frame_queue: Queue = Queue(maxsize=self.buffer_size)
        self.lock = Lock()
        self.stop_event = Event()
        
        # Performance metrics
        self.frame_count = 0
        self.dropped_frames = 0
        self.last_frame_time = 0.0
        self.fps_actual = 0.0
        
        backend = "picamera2" if self.use_picamera2 else "opencv"
        self.logger.info(
            'Camera service initialized',
            backend=backend,
            resolution=f'{self.resolution[0]}x{self.resolution[1]}',
            fps=self.fps,
            camera_index=self.camera_index
        )
    
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if camera started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning('Camera service already running')
            return True
        
        self.logger.info('Starting camera service...')
        
        try:
            if self.use_picamera2:
                # Initialize picamera2
                self.camera = Picamera2()
                
                # Create configuration for video capture
                camera_config = self.camera.create_preview_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.camera.configure(camera_config)
                
                # Get camera properties
                camera_props = self.camera.camera_properties
                sensor_model = camera_props.get('Model', 'Unknown')
                
                self.logger.info(
                    'Camera opened successfully (picamera2)',
                    sensor=sensor_model,
                    resolution=f'{self.resolution[0]}x{self.resolution[1]}',
                    format='RGB888'
                )
                
                # Start camera
                self.camera.start()
                
                # Give camera time to initialize
                time.sleep(1.0)
                
            else:
                # Initialize OpenCV VideoCapture
                self.camera = cv2.VideoCapture(self.camera_index)
                
                if not self.camera.isOpened():
                    raise RuntimeError(f'Failed to open camera at index {self.camera_index}')
                
                # Set camera properties
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                
                # Verify settings
                actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
                
                self.logger.info(
                    'Camera opened successfully (opencv)',
                    requested_resolution=f'{self.resolution[0]}x{self.resolution[1]}',
                    actual_resolution=f'{actual_width}x{actual_height}',
                    requested_fps=self.fps,
                    actual_fps=actual_fps
                )
            
            # Start capture thread
            self.is_running = True
            self.stop_event.clear()
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            self.logger.info('Camera capture thread started')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start camera: {e}', exc_info=True)
            self.stop()
            return False
    
    def stop(self) -> None:
        """Stop camera capture and release resources."""
        if not self.is_running:
            return
        
        self.logger.info('Stopping camera service...')
        
        self.is_running = False
        self.stop_event.set()
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        # Release camera
        if self.camera:
            try:
                if self.use_picamera2:
                    self.camera.stop()
                    self.camera.close()
                else:
                    self.camera.release()
            except Exception as e:
                self.logger.warning(f'Error releasing camera: {e}')
            self.camera = None
        
        # Clear frame queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                pass
        
        self.logger.info(
            'Camera service stopped',
            total_frames=self.frame_count,
            dropped_frames=self.dropped_frames
        )
    
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        self.logger.debug('Capture loop started')
        
        frame_time = 1.0 / self.fps
        
        while self.is_running and not self.stop_event.is_set():
            loop_start = time.time()
            
            try:
                # Capture frame
                if self.use_picamera2:
                    frame = self.camera.capture_array()
                    
                    if frame is None:
                        self.logger.warning('Failed to capture frame')
                        continue
                    
                    # picamera2 returns RGB, convert to BGR for OpenCV compatibility
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                else:
                    ret, frame = self.camera.read()
                    
                    if not ret or frame is None:
                        self.logger.warning('Failed to capture frame')
                        continue
                
                # Apply rotation if needed
                if self.rotation != 0:
                    frame = self._rotate_frame(frame, self.rotation)
                
                # Update metrics
                self.frame_count += 1
                current_time = time.time()
                if self.last_frame_time > 0:
                    self.fps_actual = 1.0 / (current_time - self.last_frame_time)
                self.last_frame_time = current_time
                
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait((current_time, frame))
                except Full:
                    # Queue full, drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait((current_time, frame))
                        self.dropped_frames += 1
                    except:
                        pass
                
                # Maintain target FPS
                elapsed = time.time() - loop_start
                sleep_time = max(0, frame_time - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.error(f'Error in capture loop: {e}', exc_info=True)
                time.sleep(0.1)  # Prevent tight loop on errors
        
        self.logger.debug('Capture loop ended')
    
    def _rotate_frame(self, frame: np.ndarray, rotation: int) -> np.ndarray:
        """
        Rotate frame by specified degrees.
        
        Args:
            frame: Input frame
            rotation: Rotation angle (0, 90, 180, 270)
            
        Returns:
            Rotated frame
        """
        if rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
    
    def get_frame(self, timeout: float = 1.0) -> Optional[Tuple[float, np.ndarray]]:
        """
        Get latest frame from camera.
        
        Args:
            timeout: Timeout in seconds to wait for frame
            
        Returns:
            Tuple of (timestamp, frame) or None if no frame available
        """
        if not self.is_running:
            return None
        
        try:
            return self.frame_queue.get(timeout=timeout)
        except:
            return None
    
    def get_latest_frame(self) -> Optional[Tuple[float, np.ndarray]]:
        """
        Get the most recent frame, discarding older frames.
        
        Returns:
            Tuple of (timestamp, frame) or None if no frame available
        """
        frame_data = None
        
        # Get all frames from queue, keeping only the latest
        while not self.frame_queue.empty():
            try:
                frame_data = self.frame_queue.get_nowait()
            except:
                break
        
        return frame_data
    
    def capture_image(self, filepath: str) -> bool:
        """
        Capture and save a single image.
        
        Args:
            filepath: Path to save image
            
        Returns:
            True if image saved successfully, False otherwise
        """
        frame_data = self.get_latest_frame()
        
        if frame_data is None:
            self.logger.error('No frame available for image capture')
            return False
        
        _, frame = frame_data
        
        try:
            cv2.imwrite(filepath, frame)
            self.logger.info(f'Image saved to {filepath}')
            return True
        except Exception as e:
            self.logger.error(f'Failed to save image: {e}', exc_info=True)
            return False
    
    def get_camera_info(self) -> dict:
        """
        Get camera information and statistics.
        
        Returns:
            Dictionary with camera info
        """
        info = {
            'is_running': self.is_running,
            'backend': 'picamera2' if self.use_picamera2 else 'opencv',
            'camera_index': self.camera_index,
            'resolution': f'{self.resolution[0]}x{self.resolution[1]}',
            'target_fps': self.fps,
            'actual_fps': round(self.fps_actual, 2),
            'frame_count': self.frame_count,
            'dropped_frames': self.dropped_frames,
            'queue_size': self.frame_queue.qsize(),
            'queue_capacity': self.buffer_size,
        }
        
        if self.camera:
            if self.use_picamera2:
                try:
                    camera_props = self.camera.camera_properties
                    info['sensor_model'] = camera_props.get('Model', 'Unknown')
                    info['actual_width'] = self.resolution[0]
                    info['actual_height'] = self.resolution[1]
                except:
                    pass
            elif self.camera.isOpened():
                info['actual_width'] = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                info['actual_height'] = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        return info
    
    def test_camera(self) -> bool:
        """
        Test camera functionality.
        
        Returns:
            True if camera test passed, False otherwise
        """
        self.logger.info('Testing camera...')
        
        if not self.start():
            return False
        
        try:
            # Try to capture a few frames
            for i in range(5):
                frame_data = self.get_frame(timeout=2.0)
                if frame_data is None:
                    self.logger.error(f'Failed to capture test frame {i+1}')
                    return False
                
                timestamp, frame = frame_data
                self.logger.info(
                    f'Test frame {i+1} captured',
                    shape=frame.shape,
                    dtype=frame.dtype
                )
            
            self.logger.info('Camera test passed')
            return True
            
        except Exception as e:
            self.logger.error(f'Camera test failed: {e}', exc_info=True)
            return False
        finally:
            self.stop()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

