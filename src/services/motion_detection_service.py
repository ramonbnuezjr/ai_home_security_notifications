"""Motion detection service using background subtraction."""

import cv2
import numpy as np
import time
from typing import Optional, List, Tuple, Dict, Any
from threading import Thread, Lock, Event
from dataclasses import dataclass
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.config import Config


@dataclass
class MotionEvent:
    """Represents a detected motion event."""
    timestamp: float
    frame_id: int
    contours: List[np.ndarray]
    bounding_boxes: List[Tuple[int, int, int, int]]  # (x, y, w, h)
    areas: List[float]
    motion_percentage: float
    frame_shape: Tuple[int, int]
    detected_objects: Optional[Any] = None  # DetectionResult from object detection
    
    def __str__(self):
        obj_info = ""
        if self.detected_objects and hasattr(self.detected_objects, 'objects'):
            obj_summary = ", ".join([str(obj) for obj in self.detected_objects.objects[:2]])
            if len(self.detected_objects.objects) > 2:
                obj_summary += f", +{len(self.detected_objects.objects) - 2} more"
            obj_info = f", detected=[{obj_summary}]"
        
        return (f"MotionEvent(time={datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')}, "
                f"motion_objects={len(self.bounding_boxes)}, motion={self.motion_percentage:.1f}%{obj_info})")


class MotionDetectionService:
    """
    Motion detection service using background subtraction.
    
    Supports multiple algorithms (MOG2, KNN, frame differencing) and provides
    configurable sensitivity, area filtering, and motion zone support.
    """
    
    def __init__(self, config: Config):
        """
        Initialize motion detection service.
        
        Args:
            config: System configuration object
        """
        self.config = config
        self.logger = get_logger('motion_detection')
        
        # Load detection configuration
        detection_config = config.get_detection_config()
        
        # Algorithm selection
        self.algorithm = detection_config.get('algorithm', 'mog2')
        
        # Sensitivity settings
        self.sensitivity = detection_config.get('sensitivity', 0.7)
        self.min_area = detection_config.get('min_area', 500)
        self.max_area = detection_config.get('max_area', 50000)
        
        # Background subtraction parameters
        self.learning_rate = detection_config.get('learning_rate', 0.001)
        self.history = detection_config.get('history', 500)
        self.var_threshold = detection_config.get('var_threshold', 16)
        
        # Motion detection state
        self.background_subtractor: Optional[Any] = None
        self.previous_frame: Optional[np.ndarray] = None
        self.is_initialized = False
        
        # Statistics
        self.frame_count = 0
        self.motion_count = 0
        self.last_motion_time = 0.0
        
        # Threading
        self.lock = Lock()
        
        self.logger.info(
            'Motion detection service initialized',
            algorithm=self.algorithm,
            sensitivity=self.sensitivity,
            min_area=self.min_area,
            max_area=self.max_area
        )
    
    def initialize(self) -> bool:
        """
        Initialize the motion detection algorithm.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self.algorithm == 'mog2':
                # MOG2 Background Subtractor
                self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                    history=self.history,
                    varThreshold=self.var_threshold,
                    detectShadows=True
                )
                self.logger.info('MOG2 background subtractor initialized')
                
            elif self.algorithm == 'knn':
                # KNN Background Subtractor
                self.background_subtractor = cv2.createBackgroundSubtractorKNN(
                    history=self.history,
                    dist2Threshold=400.0,
                    detectShadows=True
                )
                self.logger.info('KNN background subtractor initialized')
                
            elif self.algorithm == 'frame_diff':
                # Simple frame differencing (no initialization needed)
                self.background_subtractor = None
                self.logger.info('Frame differencing algorithm selected')
                
            else:
                raise ValueError(f'Unknown algorithm: {self.algorithm}')
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to initialize motion detection: {e}', exc_info=True)
            return False
    
    def detect_motion(self, frame: np.ndarray) -> Optional[MotionEvent]:
        """
        Detect motion in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            MotionEvent if motion detected, None otherwise
        """
        if not self.is_initialized:
            if not self.initialize():
                return None
        
        with self.lock:
            self.frame_count += 1
            current_time = time.time()
            
            try:
                # Apply the selected algorithm
                if self.algorithm in ['mog2', 'knn']:
                    motion_mask = self._detect_background_subtraction(frame)
                elif self.algorithm == 'frame_diff':
                    motion_mask = self._detect_frame_difference(frame)
                else:
                    return None
                
                if motion_mask is None:
                    return None
                
                # Post-process the motion mask
                motion_mask = self._post_process_mask(motion_mask)
                
                # Find contours
                contours, _ = cv2.findContours(
                    motion_mask,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                
                # Filter contours by area
                valid_contours = []
                bounding_boxes = []
                areas = []
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if self.min_area <= area <= self.max_area:
                        valid_contours.append(contour)
                        x, y, w, h = cv2.boundingRect(contour)
                        bounding_boxes.append((x, y, w, h))
                        areas.append(area)
                
                # Check if motion is significant
                if len(valid_contours) == 0:
                    return None
                
                # Calculate motion percentage
                total_motion_area = sum(areas)
                frame_area = frame.shape[0] * frame.shape[1]
                motion_percentage = (total_motion_area / frame_area) * 100
                
                # Create motion event
                motion_event = MotionEvent(
                    timestamp=current_time,
                    frame_id=self.frame_count,
                    contours=valid_contours,
                    bounding_boxes=bounding_boxes,
                    areas=areas,
                    motion_percentage=motion_percentage,
                    frame_shape=(frame.shape[0], frame.shape[1])
                )
                
                self.motion_count += 1
                self.last_motion_time = current_time
                
                self.logger.debug(
                    'Motion detected',
                    objects=len(bounding_boxes),
                    motion_pct=f'{motion_percentage:.2f}%',
                    frame_id=self.frame_count
                )
                
                return motion_event
                
            except Exception as e:
                self.logger.error(f'Error detecting motion: {e}', exc_info=True)
                return None
    
    def _detect_background_subtraction(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect motion using background subtraction.
        
        Args:
            frame: Input frame
            
        Returns:
            Motion mask or None
        """
        if self.background_subtractor is None:
            return None
        
        # Apply background subtractor
        motion_mask = self.background_subtractor.apply(frame, learningRate=self.learning_rate)
        
        # Remove shadow pixels (value 127 in MOG2)
        motion_mask[motion_mask == 127] = 0
        
        return motion_mask
    
    def _detect_frame_difference(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect motion using frame differencing.
        
        Args:
            frame: Input frame
            
        Returns:
            Motion mask or None
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # First frame - just store it
        if self.previous_frame is None:
            self.previous_frame = gray
            return None
        
        # Compute absolute difference
        frame_delta = cv2.absdiff(self.previous_frame, gray)
        
        # Apply threshold based on sensitivity
        threshold_value = int(25 * (1.0 - self.sensitivity))
        _, motion_mask = cv2.threshold(frame_delta, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Update previous frame
        self.previous_frame = gray
        
        return motion_mask
    
    def _post_process_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Post-process motion mask to reduce noise.
        
        Args:
            mask: Raw motion mask
            
        Returns:
            Cleaned motion mask
        """
        # Apply morphological operations to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # Erosion to remove small noise
        mask = cv2.erode(mask, kernel, iterations=1)
        
        # Dilation to fill gaps
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        return mask
    
    def draw_motion(self, frame: np.ndarray, motion_event: MotionEvent) -> np.ndarray:
        """
        Draw motion detection results on frame.
        
        Args:
            frame: Input frame
            motion_event: Detected motion event
            
        Returns:
            Frame with motion visualization
        """
        output_frame = frame.copy()
        
        # Draw bounding boxes
        for (x, y, w, h) in motion_event.bounding_boxes:
            cv2.rectangle(output_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Draw motion info
        info_text = f'Motion: {motion_event.motion_percentage:.1f}% | Objects: {len(motion_event.bounding_boxes)}'
        cv2.putText(
            output_frame,
            info_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        # Draw timestamp
        timestamp_text = datetime.fromtimestamp(motion_event.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(
            output_frame,
            timestamp_text,
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        return output_frame
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get motion detection statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'algorithm': self.algorithm,
            'sensitivity': self.sensitivity,
            'frame_count': self.frame_count,
            'motion_count': self.motion_count,
            'motion_rate': self.motion_count / max(1, self.frame_count),
            'last_motion_time': self.last_motion_time,
            'min_area': self.min_area,
            'max_area': self.max_area,
            'is_initialized': self.is_initialized
        }
    
    def reset(self) -> None:
        """Reset motion detection state."""
        with self.lock:
            if self.background_subtractor is not None:
                # Reinitialize background subtractor
                self.initialize()
            self.previous_frame = None
            self.logger.info('Motion detection state reset')
    
    def update_sensitivity(self, sensitivity: float) -> None:
        """
        Update detection sensitivity.
        
        Args:
            sensitivity: New sensitivity value (0.0-1.0)
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError('Sensitivity must be between 0.0 and 1.0')
        
        with self.lock:
            self.sensitivity = sensitivity
            self.logger.info(f'Sensitivity updated to {sensitivity}')
    
    def update_area_limits(self, min_area: int, max_area: int) -> None:
        """
        Update area filter limits.
        
        Args:
            min_area: Minimum contour area
            max_area: Maximum contour area
        """
        with self.lock:
            self.min_area = min_area
            self.max_area = max_area
            self.logger.info(f'Area limits updated: {min_area}-{max_area}')

