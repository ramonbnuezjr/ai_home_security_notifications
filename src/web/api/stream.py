"""Video streaming API endpoints."""

from flask import Blueprint, Response, current_app, jsonify
import cv2
import logging
import time
from threading import Lock

logger = logging.getLogger(__name__)

stream_bp = Blueprint('stream', __name__)

# Global streaming state
streaming_clients = 0
streaming_lock = Lock()


def generate_frames():
    """Generate MJPEG frames for streaming."""
    global streaming_clients
    
    try:
        # Get camera service (lazy load)
        camera = current_app.config.get('CAMERA_SERVICE')
        if camera is None:
            from src.services.camera_service import CameraService
            camera_config = current_app.config['SYSTEM_CONFIG'].get('camera', {})
            camera = CameraService(camera_config)
            current_app.config['CAMERA_SERVICE'] = camera
            logger.info("Camera service initialized for streaming")
        
        web_config = current_app.config['WEB_CONFIG']
        stream_config = web_config.get('stream', {})
        target_fps = stream_config.get('fps', 15)
        quality = stream_config.get('quality', 85)
        
        frame_time = 1.0 / target_fps
        
        with streaming_lock:
            streaming_clients += 1
            logger.info(f"Stream client connected (total: {streaming_clients})")
        
        while True:
            start_time = time.time()
            
            # Get frame from camera
            timestamp, frame = camera.get_frame()
            
            if frame is None:
                logger.warning("No frame available from camera")
                time.sleep(0.1)
                continue
            
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = buffer.tobytes()
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except GeneratorExit:
        logger.info("Stream client disconnected")
    except Exception as e:
        logger.error(f"Error in stream generation: {e}")
    finally:
        with streaming_lock:
            streaming_clients -= 1
            logger.info(f"Stream client removed (remaining: {streaming_clients})")


@stream_bp.route('/live', methods=['GET'])
def live_stream():
    """
    Live MJPEG video stream endpoint.
    
    Returns multipart/x-mixed-replace stream of JPEG frames.
    """
    try:
        # Check client limit
        web_config = current_app.config['WEB_CONFIG']
        stream_config = web_config.get('stream', {})
        max_clients = stream_config.get('max_clients', 5)
        
        with streaming_lock:
            if streaming_clients >= max_clients:
                return jsonify({
                    'error': 'Maximum number of streaming clients reached',
                    'max_clients': max_clients
                }), 503
        
        return Response(
            generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
        
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        return jsonify({'error': str(e)}), 500


@stream_bp.route('/snapshot', methods=['GET'])
def snapshot():
    """
    Get current frame snapshot as JPEG.
    """
    try:
        # Get camera service
        camera = current_app.config.get('CAMERA_SERVICE')
        if camera is None:
            from src.services.camera_service import CameraService
            camera_config = current_app.config['SYSTEM_CONFIG'].get('camera', {})
            camera = CameraService(camera_config)
            current_app.config['CAMERA_SERVICE'] = camera
        
        web_config = current_app.config['WEB_CONFIG']
        stream_config = web_config.get('stream', {})
        quality = stream_config.get('quality', 85)
        
        # Get single frame
        timestamp, frame = camera.get_frame()
        
        if frame is None:
            return jsonify({'error': 'No frame available'}), 503
        
        # Encode as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        return Response(buffer.tobytes(), mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        return jsonify({'error': str(e)}), 500


@stream_bp.route('/status', methods=['GET'])
def stream_status():
    """Get streaming status information."""
    try:
        web_config = current_app.config['WEB_CONFIG']
        stream_config = web_config.get('stream', {})
        
        with streaming_lock:
            return jsonify({
                'active_clients': streaming_clients,
                'max_clients': stream_config.get('max_clients', 5),
                'stream_fps': stream_config.get('fps', 15),
                'quality': stream_config.get('quality', 85)
            })
            
    except Exception as e:
        logger.error(f"Error getting stream status: {e}")
        return jsonify({'error': str(e)}), 500


