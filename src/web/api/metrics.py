"""System metrics API endpoints."""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import psutil
import logging

logger = logging.getLogger(__name__)

metrics_bp = Blueprint('metrics', __name__)


def get_current_system_metrics():
    """Get current system metrics from the OS."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Temperature (Raspberry Pi specific)
        temperature = None
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temperature = float(f.read().strip()) / 1000.0
        except:
            pass
        
        return {
            'cpu_usage': cpu_percent,
            'memory_usage': memory_percent,
            'disk_usage': disk_percent,
            'temperature': temperature,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return None


@metrics_bp.route('/current', methods=['GET'])
def get_current_metrics():
    """Get current system status."""
    try:
        metrics = get_current_system_metrics()
        
        if metrics is None:
            return jsonify({'error': 'Unable to retrieve system metrics'}), 500
        
        # Get latest metrics from database if available
        db = current_app.config['DB_SERVICE']
        latest_db_metrics = db.get_latest_metrics(count=1)
        
        if latest_db_metrics:
            metrics['fps'] = latest_db_metrics[0].get('fps')
            metrics['yolo_inference_time'] = latest_db_metrics[0].get('yolo_inference_time')
            metrics['active_services'] = latest_db_metrics[0].get('active_services')
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error fetching current metrics: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/history', methods=['GET'])
def get_metrics_history():
    """
    Get historical system metrics.
    
    Query params:
        - start_time: Start time (ISO format, default: 1 hour ago)
        - end_time: End time (ISO format, default: now)
        - interval: Aggregation interval in minutes (default: 5)
    """
    try:
        db = current_app.config['DB_SERVICE']
        
        # Parse query parameters
        end_time = datetime.now()
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args.get('end_time'))
        
        start_time = end_time - timedelta(hours=1)
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args.get('start_time'))
        
        interval = request.args.get('interval', 5, type=int)
        
        # Get metrics history
        history = db.get_metrics_history(
            start_time=start_time,
            end_time=end_time,
            interval_minutes=interval
        )
        
        return jsonify({
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'interval_minutes': interval,
            'data': history
        })
        
    except Exception as e:
        logger.error(f"Error fetching metrics history: {e}")
        return jsonify({'error': str(e)}), 500


@metrics_bp.route('/health', methods=['GET'])
def health_check():
    """System health check."""
    try:
        # Get current metrics
        metrics = get_current_system_metrics()
        
        if metrics is None:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Unable to retrieve system metrics'
            }), 500
        
        # Check thresholds
        issues = []
        
        if metrics['cpu_usage'] > 90:
            issues.append('High CPU usage')
        
        if metrics['memory_usage'] > 95:
            issues.append('High memory usage')
        
        if metrics['disk_usage'] > 90:
            issues.append('High disk usage')
        
        if metrics['temperature'] and metrics['temperature'] > 80:
            issues.append('High temperature')
        
        status = 'healthy' if not issues else 'warning'
        
        return jsonify({
            'status': status,
            'metrics': metrics,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@metrics_bp.route('/database', methods=['GET'])
def database_stats():
    """Get database statistics."""
    try:
        db = current_app.config['DB_SERVICE']
        stats = db.get_database_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error fetching database stats: {e}")
        return jsonify({'error': str(e)}), 500


