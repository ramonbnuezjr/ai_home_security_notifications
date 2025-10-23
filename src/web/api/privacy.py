"""
Privacy API endpoints.
Handles privacy settings, data export, data deletion, and consent management.
"""

import logging
from flask import Blueprint, request, jsonify, current_app, g, send_file
from pathlib import Path
from src.web.api.auth import require_auth, require_role

logger = logging.getLogger(__name__)

privacy_bp = Blueprint('privacy', __name__)


def get_privacy_service():
    """Get privacy service from app config"""
    return current_app.config.get('PRIVACY_SERVICE')


def get_auth_service():
    """Get auth service from app config"""
    return current_app.config.get('AUTH_SERVICE')


# ==================== Privacy Settings ====================

@privacy_bp.route('/settings', methods=['GET'])
@require_auth
def get_privacy_settings():
    """
    Get privacy settings for current user.
    
    Response:
        {settings: object}
    """
    try:
        current_user = g.current_user
        privacy_service = get_privacy_service()
        
        settings = privacy_service.get_privacy_settings(current_user['id'])
        
        if not settings:
            return jsonify({'error': 'Failed to get privacy settings'}), 500
        
        return jsonify({'settings': settings}), 200
    
    except Exception as e:
        logger.error(f"Get privacy settings error: {e}")
        return jsonify({'error': 'Failed to get privacy settings'}), 500


@privacy_bp.route('/settings', methods=['PUT'])
@require_auth
def update_privacy_settings():
    """
    Update privacy settings for current user.
    
    Request JSON:
        collect_video: bool (optional)
        collect_images: bool (optional)
        collect_audio: bool (optional)
        retention_days_events: int (optional)
        retention_days_media: int (optional)
        ... (other privacy settings)
    
    Response:
        {success: bool, errors: [string]}
    """
    try:
        current_user = g.current_user
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'errors': ['No settings provided']
            }), 400
        
        privacy_service = get_privacy_service()
        success, errors = privacy_service.update_privacy_settings(
            user_id=current_user['id'],
            settings=data
        )
        
        if success:
            return jsonify({'success': True}), 200
        
        return jsonify({'success': False, 'errors': errors}), 400
    
    except Exception as e:
        logger.error(f"Update privacy settings error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to update privacy settings']
        }), 500


# ==================== Data Export ====================

@privacy_bp.route('/export/request', methods=['POST'])
@require_auth
def request_data_export():
    """
    Request data export for current user.
    
    Response:
        {success: bool, request_id: int, errors: [string]}
    """
    try:
        current_user = g.current_user
        privacy_service = get_privacy_service()
        
        success, request_id, errors = privacy_service.create_data_export_request(
            user_id=current_user['id']
        )
        
        if success:
            # Process the export asynchronously (or immediately for small datasets)
            # For now, process immediately
            export_success, export_file, export_errors = privacy_service.process_data_export(request_id)
            
            if export_success:
                return jsonify({
                    'success': True,
                    'request_id': request_id,
                    'message': 'Data export completed',
                    'export_file': export_file
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'errors': export_errors
                }), 500
        
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    except Exception as e:
        logger.error(f"Request data export error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to request data export']
        }), 500


@privacy_bp.route('/export/requests', methods=['GET'])
@require_auth
def get_export_requests():
    """
    Get data export requests for current user.
    
    Response:
        {requests: [object]}
    """
    try:
        current_user = g.current_user
        db_service = current_app.config.get('DB_SERVICE')
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, request_date, status, export_file, completed_at
                FROM data_export_requests
                WHERE user_id = ?
                ORDER BY request_date DESC
                LIMIT 10
            """, (current_user['id'],))
            
            requests = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'requests': requests}), 200
    
    except Exception as e:
        logger.error(f"Get export requests error: {e}")
        return jsonify({'error': 'Failed to get export requests'}), 500


@privacy_bp.route('/export/download/<int:request_id>', methods=['GET'])
@require_auth
def download_export(request_id):
    """
    Download exported data file.
    
    Response:
        File download
    """
    try:
        current_user = g.current_user
        db_service = current_app.config.get('DB_SERVICE')
        
        # Get export request
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, export_file, status
                FROM data_export_requests
                WHERE id = ?
            """, (request_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'error': 'Export request not found'}), 404
            
            export = dict(row)
            
            # Check ownership
            if export['user_id'] != current_user['id']:
                auth_service = get_auth_service()
                if not auth_service.check_permission(current_user, 'admin'):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Check status
            if export['status'] != 'completed':
                return jsonify({'error': 'Export not completed'}), 400
            
            export_file = export['export_file']
            if not export_file or not Path(export_file).exists():
                return jsonify({'error': 'Export file not found'}), 404
            
            return send_file(
                export_file,
                as_attachment=True,
                download_name=Path(export_file).name
            )
    
    except Exception as e:
        logger.error(f"Download export error: {e}")
        return jsonify({'error': 'Failed to download export'}), 500


# ==================== Data Deletion ====================

@privacy_bp.route('/delete/request', methods=['POST'])
@require_auth
def request_data_deletion():
    """
    Request data deletion for current user.
    
    Request JSON:
        deletion_type: string ('partial' or 'full') - required
        data_types: [string] - required for partial deletion
        confirm: bool - required for full deletion
    
    Response:
        {success: bool, request_id: int, errors: [string]}
    """
    try:
        current_user = g.current_user
        data = request.get_json()
        
        deletion_type = data.get('deletion_type', 'partial')
        data_types = data.get('data_types', [])
        confirm = data.get('confirm', False)
        
        # Require confirmation for full deletion
        if deletion_type == 'full' and not confirm:
            return jsonify({
                'success': False,
                'errors': ['Full deletion requires confirmation']
            }), 400
        
        privacy_service = get_privacy_service()
        success, request_id, errors = privacy_service.create_data_deletion_request(
            user_id=current_user['id'],
            deletion_type=deletion_type,
            data_types=data_types if data_types else None
        )
        
        if success:
            # Process the deletion immediately (in production, might be async)
            delete_success, delete_errors = privacy_service.process_data_deletion(request_id)
            
            if delete_success:
                return jsonify({
                    'success': True,
                    'request_id': request_id,
                    'message': 'Data deletion completed'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'errors': delete_errors
                }), 500
        
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    except Exception as e:
        logger.error(f"Request data deletion error: {e}")
        return jsonify({
            'success': False,
            'errors': ['Failed to request data deletion']
        }), 500


@privacy_bp.route('/delete/requests', methods=['GET'])
@require_auth
def get_deletion_requests():
    """
    Get data deletion requests for current user.
    
    Response:
        {requests: [object]}
    """
    try:
        current_user = g.current_user
        db_service = current_app.config.get('DB_SERVICE')
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, request_date, deletion_type, data_types, status, completed_at
                FROM data_deletion_requests
                WHERE user_id = ?
                ORDER BY request_date DESC
                LIMIT 10
            """, (current_user['id'],))
            
            requests = [dict(row) for row in cursor.fetchall()]
            
            # Parse data_types JSON
            for req in requests:
                if req.get('data_types'):
                    import json
                    req['data_types'] = json.loads(req['data_types'])
        
        return jsonify({'requests': requests}), 200
    
    except Exception as e:
        logger.error(f"Get deletion requests error: {e}")
        return jsonify({'error': 'Failed to get deletion requests'}), 500


# ==================== Consent Management ====================

@privacy_bp.route('/consent/history', methods=['GET'])
@require_auth
def get_consent_history():
    """
    Get consent history for current user.
    
    Response:
        {consents: [object]}
    """
    try:
        current_user = g.current_user
        privacy_service = get_privacy_service()
        
        consents = privacy_service.get_consent_history(current_user['id'])
        
        return jsonify({'consents': consents}), 200
    
    except Exception as e:
        logger.error(f"Get consent history error: {e}")
        return jsonify({'error': 'Failed to get consent history'}), 500


# ==================== Data Retention ====================

@privacy_bp.route('/retention/enforce', methods=['POST'])
@require_role('admin')
def enforce_retention():
    """
    Manually enforce retention policies (admin only).
    
    Request JSON:
        user_id: int (optional) - Enforce for specific user
    
    Response:
        {success: bool, deleted: object}
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        privacy_service = get_privacy_service()
        results = privacy_service.enforce_retention_policies(user_id=user_id)
        
        return jsonify({
            'success': True,
            'deleted': results
        }), 200
    
    except Exception as e:
        logger.error(f"Enforce retention error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to enforce retention policies'
        }), 500


# ==================== Privacy Information ====================

@privacy_bp.route('/info', methods=['GET'])
def get_privacy_info():
    """
    Get privacy policy and data collection information (public).
    
    Response:
        {info: object}
    """
    privacy_info = {
        'version': '1.0',
        'last_updated': '2025-01-01',
        'data_types_collected': [
            {
                'type': 'video',
                'description': 'Security camera video footage',
                'retention': 'Configurable (default: 7 days)',
                'purpose': 'Security monitoring and threat detection'
            },
            {
                'type': 'images',
                'description': 'Security camera still images',
                'retention': 'Configurable (default: 7 days)',
                'purpose': 'Security monitoring and threat detection'
            },
            {
                'type': 'events',
                'description': 'Motion detection and object detection events',
                'retention': 'Configurable (default: 30 days)',
                'purpose': 'Security event history and analysis'
            },
            {
                'type': 'metrics',
                'description': 'System performance metrics',
                'retention': 'Configurable (default: 7 days)',
                'purpose': 'System monitoring and optimization'
            },
            {
                'type': 'audit_logs',
                'description': 'User actions and system access logs',
                'retention': 'Configurable (default: 90 days)',
                'purpose': 'Security auditing and compliance'
            }
        ],
        'user_rights': [
            'Right to access your personal data',
            'Right to export your personal data',
            'Right to delete your personal data',
            'Right to configure data retention policies',
            'Right to opt-out of specific data collection'
        ],
        'data_processing': 'All data is processed locally on your device',
        'data_sharing': 'No data is shared with third parties by default',
        'encryption': 'Data at rest can be encrypted',
        'contact': 'admin@localhost'
    }
    
    return jsonify({'info': privacy_info}), 200


@privacy_bp.route('/data-types', methods=['GET'])
@require_auth
def get_data_types():
    """
    Get available data types for deletion/export.
    
    Response:
        {data_types: [string]}
    """
    privacy_service = get_privacy_service()
    
    return jsonify({
        'data_types': privacy_service.DATA_TYPES
    }), 200




