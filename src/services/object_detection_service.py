"""Object detection service using YOLOv8."""

import cv2
import numpy as np
import time
from typing import Optional, List, Tuple, Dict, Any
from threading import Lock
from dataclasses import dataclass
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import Config


@dataclass
class DetectedObject:
    """Represents a detected object."""
    class_name: str
    class_id: int
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    
    def __str__(self):
        return f"{self.class_name} ({self.confidence:.2f})"
    
    def get_center(self) -> Tuple[int, int]:
        """Get center point of bounding box."""
        x1, y1, x2, y2 = self.bounding_box
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    def get_area(self) -> int:
        """Get area of bounding box."""
        x1, y1, x2, y2 = self.bounding_box
        return (x2 - x1) * (y2 - y1)


@dataclass
class DetectionResult:
    """Result of object detection on a frame."""
    timestamp: float
    frame_id: int
    objects: List[DetectedObject]
    inference_time: float
    frame_shape: Tuple[int, int]
    
    def __str__(self):
        obj_summary = ", ".join([str(obj) for obj in self.objects[:3]])
        if len(self.objects) > 3:
            obj_summary += f", +{len(self.objects) - 3} more"
        return f"DetectionResult({len(self.objects)} objects: {obj_summary})"
    
    def get_objects_by_class(self, class_name: str) -> List[DetectedObject]:
        """Get all detected objects of a specific class."""
        return [obj for obj in self.objects if obj.class_name == class_name]
    
    def has_class(self, class_name: str) -> bool:
        """Check if a specific class was detected."""
        return any(obj.class_name == class_name for obj in self.objects)


class ObjectDetectionService:
    """
    Object detection service using YOLOv8.
    
    Provides real-time object detection with configurable confidence thresholds,
    class filtering, and performance optimizations.
    """
    
    def __init__(self, config: Config):
        """
        Initialize object detection service.
        
        Args:
            config: System configuration object
        """
        self.config = config
        self.logger = get_logger('object_detection')
        
        # Load AI configuration
        ai_config = config.get('ai', {})
        yolo_config = ai_config.get('yolo', {})
        classification_config = ai_config.get('classification', {})
        
        # Model settings
        self.model_variant = yolo_config.get('model_variant', 'yolov8s')
        self.model_path = yolo_config.get('model_path', None)
        self.confidence_threshold = yolo_config.get('confidence_threshold', 0.5)
        self.iou_threshold = yolo_config.get('iou_threshold', 0.45)
        self.max_detections = yolo_config.get('max_detections', 10)
        
        # Classification filters
        self.classification_enabled = classification_config.get('enabled', True)
        self.target_classes = classification_config.get('target_classes', [])
        self.ignore_classes = classification_config.get('ignore_classes', [])
        self.min_object_size = classification_config.get('min_object_size', 0.01)
        self.max_object_size = classification_config.get('max_object_size', 0.8)
        
        # Model state
        self.model = None
        self.is_initialized = False
        self.class_names = []
        
        # Statistics
        self.frame_count = 0
        self.detection_count = 0
        self.total_inference_time = 0.0
        
        # Threading
        self.lock = Lock()
        
        self.logger.info(
            'Object detection service created',
            model=self.model_variant,
            confidence=self.confidence_threshold,
            target_classes=self.target_classes
        )
    
    def initialize(self) -> bool:
        """
        Initialize the YOLOv8 model.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            from ultralytics import YOLO
            
            self.logger.info(f'Loading YOLOv8 model: {self.model_variant}')
            
            # Load model
            if self.model_path and Path(self.model_path).exists():
                self.logger.info(f'Loading model from: {self.model_path}')
                self.model = YOLO(self.model_path)
            else:
                # Download pretrained model
                self.logger.info(f'Downloading pretrained {self.model_variant} model...')
                self.model = YOLO(f'{self.model_variant}.pt')
            
            # Get class names
            self.class_names = self.model.names
            
            self.logger.info(
                'YOLOv8 model loaded successfully',
                num_classes=len(self.class_names),
                model_type=self.model_variant
            )
            
            # Run a warmup inference
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy_frame, verbose=False)
            self.logger.info('Model warmup completed')
            
            self.is_initialized = True
            return True
            
        except ImportError:
            self.logger.error(
                'ultralytics package not installed. '
                'Install with: pip install ultralytics'
            )
            return False
            
        except Exception as e:
            self.logger.error(f'Failed to initialize object detection: {e}', exc_info=True)
            return False
    
    def detect_objects(
        self,
        frame: np.ndarray,
        frame_id: Optional[int] = None
    ) -> Optional[DetectionResult]:
        """
        Detect objects in a frame.
        
        Args:
            frame: Input frame (BGR format)
            frame_id: Optional frame identifier
            
        Returns:
            DetectionResult if objects detected, None otherwise
        """
        if not self.is_initialized:
            if not self.initialize():
                return None
        
        with self.lock:
            self.frame_count += 1
            if frame_id is None:
                frame_id = self.frame_count
            
            try:
                # Run inference
                start_time = time.time()
                
                results = self.model(
                    frame,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    max_det=self.max_detections,
                    verbose=False
                )
                
                inference_time = time.time() - start_time
                self.total_inference_time += inference_time
                
                # Parse results
                detected_objects = []
                
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    
                    for i in range(len(boxes)):
                        # Get box data
                        box = boxes.xyxy[i].cpu().numpy()
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        cls_name = self.class_names[cls_id]
                        
                        # Apply filters
                        if not self._should_include_detection(cls_name, box, frame.shape):
                            continue
                        
                        # Create detected object
                        detected_obj = DetectedObject(
                            class_name=cls_name,
                            class_id=cls_id,
                            confidence=conf,
                            bounding_box=(int(box[0]), int(box[1]), int(box[2]), int(box[3]))
                        )
                        
                        detected_objects.append(detected_obj)
                
                # Create detection result
                if len(detected_objects) > 0:
                    self.detection_count += 1
                
                detection_result = DetectionResult(
                    timestamp=time.time(),
                    frame_id=frame_id,
                    objects=detected_objects,
                    inference_time=inference_time,
                    frame_shape=(frame.shape[0], frame.shape[1])
                )
                
                if len(detected_objects) > 0:
                    self.logger.debug(
                        'Objects detected',
                        count=len(detected_objects),
                        objects=[str(obj) for obj in detected_objects],
                        inference_ms=f'{inference_time*1000:.1f}'
                    )
                
                return detection_result
                
            except Exception as e:
                self.logger.error(f'Error detecting objects: {e}', exc_info=True)
                return None
    
    def _should_include_detection(
        self,
        class_name: str,
        box: np.ndarray,
        frame_shape: Tuple[int, int, int]
    ) -> bool:
        """
        Check if detection should be included based on filters.
        
        Args:
            class_name: Detected class name
            box: Bounding box coordinates
            frame_shape: Frame dimensions
            
        Returns:
            True if detection should be included, False otherwise
        """
        # Check ignore list
        if class_name in self.ignore_classes:
            return False
        
        # Check target classes (if specified)
        if self.target_classes and class_name not in self.target_classes:
            return False
        
        # Check object size
        frame_area = frame_shape[0] * frame_shape[1]
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        size_ratio = box_area / frame_area
        
        if size_ratio < self.min_object_size or size_ratio > self.max_object_size:
            return False
        
        return True
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detection_result: DetectionResult,
        show_confidence: bool = True,
        color_by_class: bool = True
    ) -> np.ndarray:
        """
        Draw detection results on frame.
        
        Args:
            frame: Input frame
            detection_result: Detection result to draw
            show_confidence: Whether to show confidence scores
            color_by_class: Whether to use different colors for different classes
            
        Returns:
            Frame with detections drawn
        """
        output_frame = frame.copy()
        
        # Define colors for different classes
        class_colors = {
            'person': (0, 255, 0),      # Green
            'car': (255, 0, 0),          # Blue
            'truck': (255, 100, 0),      # Blue-ish
            'bicycle': (0, 255, 255),    # Yellow
            'motorcycle': (0, 165, 255), # Orange
            'cat': (255, 255, 0),        # Cyan
            'dog': (255, 255, 0),        # Cyan
        }
        default_color = (0, 255, 0)  # Green
        
        for obj in detection_result.objects:
            x1, y1, x2, y2 = obj.bounding_box
            
            # Get color
            if color_by_class:
                color = class_colors.get(obj.class_name, default_color)
            else:
                color = default_color
            
            # Draw bounding box
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), color, 2)
            
            # Prepare label
            if show_confidence:
                label = f'{obj.class_name} {obj.confidence:.2f}'
            else:
                label = obj.class_name
            
            # Draw label background
            (label_width, label_height), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                2
            )
            
            cv2.rectangle(
                output_frame,
                (x1, y1 - label_height - 10),
                (x1 + label_width + 10, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                output_frame,
                label,
                (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )
        
        return output_frame
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get object detection statistics.
        
        Returns:
            Dictionary with statistics
        """
        avg_inference_time = 0.0
        if self.frame_count > 0:
            avg_inference_time = self.total_inference_time / self.frame_count
        
        return {
            'model': self.model_variant,
            'is_initialized': self.is_initialized,
            'frame_count': self.frame_count,
            'detection_count': self.detection_count,
            'detection_rate': self.detection_count / max(1, self.frame_count),
            'avg_inference_time': avg_inference_time,
            'confidence_threshold': self.confidence_threshold,
            'target_classes': self.target_classes,
            'num_classes': len(self.class_names) if self.class_names else 0
        }
    
    def update_confidence_threshold(self, threshold: float) -> None:
        """
        Update confidence threshold.
        
        Args:
            threshold: New threshold value (0.0-1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        
        with self.lock:
            self.confidence_threshold = threshold
            self.logger.info(f'Confidence threshold updated to {threshold}')
    
    def get_available_classes(self) -> List[str]:
        """
        Get list of all available detection classes.
        
        Returns:
            List of class names
        """
        if not self.is_initialized:
            return []
        return list(self.class_names.values())

