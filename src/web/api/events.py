"""Events API endpoints."""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

events_bp = Blueprint('events', __name__)


@events_bp.route('/', methods=['GET'])
def get_events():
    """
    Get list of events with pagination and filtering.
    
    Query params:
        - page: Page number (default: 1)
        - limit: Items per page (default: 50, max: 100)
        - event_type: Filter by event type
        - severity: Filter by severity
        - start_date: Filter events after this date (ISO format)
        - end_date: Filter events before this date (ISO format)
    """
    try:
        db = current_app.config['DB_SERVICE']
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 50, type=int), 100)
        event_type = request.args.get('event_type')
        severity = request.args.get('severity')
        
        start_date = None
        if request.args.get('start_date'):
            start_date = datetime.fromisoformat(request.args.get('start_date'))
        
        end_date = None
        if request.args.get('end_date'):
            end_date = datetime.fromisoformat(request.args.get('end_date'))
        
        # Get events from database
        events, total_count = db.get_events(
            page=page,
            limit=limit,
            event_type=event_type,
            severity=severity,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return jsonify({
            'events': events,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_items': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get specific event by ID with detected objects."""
    try:
        db = current_app.config['DB_SERVICE']
        event = db.get_event(event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify(event)
        
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete event by ID (admin only)."""
    try:
        db = current_app.config['DB_SERVICE']
        success = db.delete_event(event_id)
        
        if not success:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify({'message': 'Event deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/stats', methods=['GET'])
def get_event_stats():
    """
    Get event statistics.
    
    Query params:
        - days: Number of days to analyze (default: 7)
    """
    try:
        db = current_app.config['DB_SERVICE']
        days = request.args.get('days', 7, type=int)
        
        stats = db.get_event_stats(days=days)
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error fetching event stats: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/stream', methods=['GET'])
def event_stream():
    """
    Server-Sent Events endpoint for real-time event updates.
    TODO: Implement SSE for live event notifications
    """
    # This will be implemented when we integrate with the detection system
    return jsonify({'message': 'SSE endpoint - to be implemented'}), 501


