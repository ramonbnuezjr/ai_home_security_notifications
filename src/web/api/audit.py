"""
Audit log API endpoints.
Provides access to system audit logs with filtering and search capabilities.
"""

import logging
from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timedelta
from typing import Optional
from src.web.api.auth import require_auth, require_role

logger = logging.getLogger(__name__)

audit_bp = Blueprint('audit', __name__)


def get_db_service():
    """Get database service from app config"""
    return current_app.config.get('DB_SERVICE')


def get_auth_service():
    """Get auth service from app config"""
    return current_app.config.get('AUTH_SERVICE')


@audit_bp.route('/logs', methods=['GET'])
@require_role('moderator')
def get_audit_logs():
    """
    Get audit logs with filtering.
    
    Query params:
        page: int (default: 1)
        limit: int (default: 50, max: 500)
        user_id: int (optional filter)
        action: string (optional filter)
        status: string (optional filter)
        start_date: ISO datetime (optional filter)
        end_date: ISO datetime (optional filter)
        search: string (optional search in details)
    
    Response:
        {logs: [object], total: int, page: int, limit: int}
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 500)
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        db_service = get_db_service()
        
        # Build query
        where_clauses = []
        params = []
        
        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)
        
        if action:
            where_clauses.append("action = ?")
            params.append(action)
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if start_dt:
            where_clauses.append("timestamp >= ?")
            params.append(start_dt)
        
        if end_dt:
            where_clauses.append("timestamp <= ?")
            params.append(end_dt)
        
        if search:
            where_clauses.append("(details LIKE ? OR resource LIKE ? OR username LIKE ?)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM audit_log WHERE {where_sql}", params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * limit
            cursor.execute(f"""
                SELECT 
                    id, timestamp, user_id, username, action, 
                    resource, ip_address, user_agent, status, details
                FROM audit_log 
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            logs = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'logs': logs,
            'total': total_count,
            'page': page,
            'limit': limit
        }), 200
    
    except Exception as e:
        logger.error(f"Get audit logs error: {e}")
        return jsonify({'error': 'Failed to get audit logs'}), 500


@audit_bp.route('/logs/<int:log_id>', methods=['GET'])
@require_role('moderator')
def get_audit_log_detail(log_id):
    """
    Get detailed audit log entry.
    
    Response:
        {log: object}
    """
    try:
        db_service = get_db_service()
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_log WHERE id = ?
            """, (log_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'error': 'Audit log not found'}), 404
            
            log = dict(row)
        
        return jsonify({'log': log}), 200
    
    except Exception as e:
        logger.error(f"Get audit log detail error: {e}")
        return jsonify({'error': 'Failed to get audit log'}), 500


@audit_bp.route('/logs/user/<int:user_id>', methods=['GET'])
@require_auth
def get_user_audit_logs(user_id):
    """
    Get audit logs for specific user.
    Users can only view their own logs unless they're admin/moderator.
    
    Query params:
        page: int (default: 1)
        limit: int (default: 50)
        action: string (optional filter)
        days: int (default: 30)
    
    Response:
        {logs: [object], total: int}
    """
    try:
        current_user = g.current_user
        auth_service = get_auth_service()
        
        # Check permissions
        if current_user['id'] != user_id and not auth_service.check_permission(current_user, 'moderator'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 200)
        action = request.args.get('action')
        days = int(request.args.get('days', 30))
        
        start_date = datetime.now() - timedelta(days=days)
        
        db_service = get_db_service()
        
        # Build query
        where_clauses = ["user_id = ?", "timestamp >= ?"]
        params = [user_id, start_date]
        
        if action:
            where_clauses.append("action = ?")
            params.append(action)
        
        where_sql = " AND ".join(where_clauses)
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM audit_log WHERE {where_sql}", params)
            total_count = cursor.fetchone()[0]
            
            offset = (page - 1) * limit
            cursor.execute(f"""
                SELECT 
                    id, timestamp, action, resource, ip_address, 
                    user_agent, status, details
                FROM audit_log 
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            logs = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'logs': logs,
            'total': total_count,
            'page': page,
            'limit': limit
        }), 200
    
    except Exception as e:
        logger.error(f"Get user audit logs error: {e}")
        return jsonify({'error': 'Failed to get user audit logs'}), 500


@audit_bp.route('/logs/actions', methods=['GET'])
@require_role('moderator')
def get_audit_actions():
    """
    Get list of all unique audit actions.
    
    Response:
        {actions: [string]}
    """
    try:
        db_service = get_db_service()
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT action FROM audit_log
                ORDER BY action
            """)
            
            actions = [row[0] for row in cursor.fetchall()]
        
        return jsonify({'actions': actions}), 200
    
    except Exception as e:
        logger.error(f"Get audit actions error: {e}")
        return jsonify({'error': 'Failed to get audit actions'}), 500


@audit_bp.route('/logs/stats', methods=['GET'])
@require_role('moderator')
def get_audit_stats():
    """
    Get audit log statistics.
    
    Query params:
        days: int (default: 7)
    
    Response:
        {stats: object}
    """
    try:
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        db_service = get_db_service()
        
        stats = {}
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total logs
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?
            """, (start_date,))
            stats['total_logs'] = cursor.fetchone()[0]
            
            # By action
            cursor.execute("""
                SELECT action, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """, (start_date,))
            stats['by_action'] = [
                {'action': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY status
            """, (start_date,))
            stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # By user
            cursor.execute("""
                SELECT username, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ? AND username IS NOT NULL
                GROUP BY username
                ORDER BY count DESC
                LIMIT 10
            """, (start_date,))
            stats['by_user'] = [
                {'username': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
            
            # Failed actions
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log 
                WHERE timestamp >= ? AND status != 'success'
            """, (start_date,))
            stats['failed_actions'] = cursor.fetchone()[0]
            
            # Activity timeline (by hour)
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY hour
                ORDER BY hour
            """, (start_date,))
            stats['timeline'] = [
                {'hour': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
        
        return jsonify({'stats': stats}), 200
    
    except Exception as e:
        logger.error(f"Get audit stats error: {e}")
        return jsonify({'error': 'Failed to get audit stats'}), 500


@audit_bp.route('/logs/export', methods=['POST'])
@require_role('admin')
def export_audit_logs():
    """
    Export audit logs to JSON file (admin only).
    
    Request JSON:
        start_date: ISO datetime (optional)
        end_date: ISO datetime (optional)
        user_id: int (optional)
        action: string (optional)
    
    Response:
        {logs: [object], count: int}
    """
    try:
        data = request.get_json() or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        user_id = data.get('user_id')
        action = data.get('action')
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        db_service = get_db_service()
        
        # Build query
        where_clauses = []
        params = []
        
        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)
        
        if action:
            where_clauses.append("action = ?")
            params.append(action)
        
        if start_dt:
            where_clauses.append("timestamp >= ?")
            params.append(start_dt)
        
        if end_dt:
            where_clauses.append("timestamp <= ?")
            params.append(end_dt)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM audit_log WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT 10000
            """, params)
            
            logs = [dict(row) for row in cursor.fetchall()]
        
        # Convert datetime objects to strings for JSON serialization
        for log in logs:
            if log.get('timestamp'):
                log['timestamp'] = str(log['timestamp'])
        
        return jsonify({
            'logs': logs,
            'count': len(logs),
            'export_date': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Export audit logs error: {e}")
        return jsonify({'error': 'Failed to export audit logs'}), 500


@audit_bp.route('/logs/security-events', methods=['GET'])
@require_role('moderator')
def get_security_events():
    """
    Get security-related audit events (failed logins, unauthorized access, etc.).
    
    Query params:
        days: int (default: 7)
        limit: int (default: 100)
    
    Response:
        {events: [object], count: int}
    """
    try:
        days = int(request.args.get('days', 7))
        limit = min(int(request.args.get('limit', 100)), 500)
        start_date = datetime.now() - timedelta(days=days)
        
        db_service = get_db_service()
        
        # Security-related actions
        security_actions = [
            'login_failed',
            'mfa_disable_failed',
            'password_change_failed',
            'unauthorized_access',
            'rate_limited'
        ]
        
        placeholders = ','.join('?' * len(security_actions))
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    id, timestamp, user_id, username, action, 
                    resource, ip_address, user_agent, status, details
                FROM audit_log 
                WHERE timestamp >= ? 
                AND (action IN ({placeholders}) OR status != 'success')
                ORDER BY timestamp DESC
                LIMIT ?
            """, [start_date] + security_actions + [limit])
            
            events = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'events': events,
            'count': len(events)
        }), 200
    
    except Exception as e:
        logger.error(f"Get security events error: {e}")
        return jsonify({'error': 'Failed to get security events'}), 500


@audit_bp.route('/logs/retention', methods=['POST'])
@require_role('admin')
def cleanup_old_logs():
    """
    Clean up old audit logs (admin only).
    
    Request JSON:
        days: int (required) - Delete logs older than this many days
        dry_run: bool (optional) - If true, just count without deleting
    
    Response:
        {deleted_count: int, dry_run: bool}
    """
    try:
        data = request.get_json()
        
        if not data or 'days' not in data:
            return jsonify({'error': 'days parameter required'}), 400
        
        days = int(data['days'])
        dry_run = data.get('dry_run', False)
        
        if days < 30:
            return jsonify({'error': 'Cannot delete logs newer than 30 days'}), 400
        
        cutoff_date = datetime.now() - timedelta(days=days)
        db_service = get_db_service()
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            if dry_run:
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_log WHERE timestamp < ?
                """, (cutoff_date,))
                count = cursor.fetchone()[0]
                deleted_count = count
            else:
                cursor.execute("""
                    DELETE FROM audit_log WHERE timestamp < ?
                """, (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} audit logs older than {days} days")
        
        return jsonify({
            'deleted_count': deleted_count,
            'dry_run': dry_run
        }), 200
    
    except Exception as e:
        logger.error(f"Cleanup audit logs error: {e}")
        return jsonify({'error': 'Failed to cleanup audit logs'}), 500




