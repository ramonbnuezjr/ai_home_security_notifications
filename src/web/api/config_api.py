"""Configuration API endpoints."""

from flask import Blueprint, request, jsonify, current_app
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__)


@config_bp.route('/', methods=['GET'])
def get_config():
    """Get current system configuration."""
    try:
        config = current_app.config['SYSTEM_CONFIG']
        # Remove sensitive information
        safe_config = _sanitize_config(config)
        return jsonify(safe_config)
        
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        return jsonify({'error': str(e)}), 500


@config_bp.route('/<section>', methods=['GET'])
def get_config_section(section):
    """Get specific configuration section."""
    try:
        config = current_app.config['SYSTEM_CONFIG']
        
        if section not in config:
            return jsonify({'error': f'Section {section} not found'}), 404
        
        section_config = config[section]
        safe_config = _sanitize_config({section: section_config})
        
        return jsonify(safe_config[section])
        
    except Exception as e:
        logger.error(f"Error fetching config section {section}: {e}")
        return jsonify({'error': str(e)}), 500


@config_bp.route('/<section>', methods=['PUT'])
def update_config_section(section):
    """
    Update configuration section.
    TODO: Implement configuration validation and persistence.
    This endpoint is reserved for Epic 6 (admin authentication required).
    """
    return jsonify({'message': 'Configuration update - to be implemented in Epic 6'}), 501


@config_bp.route('/history', methods=['GET'])
def get_config_history():
    """Get configuration change history."""
    try:
        # TODO: Implement when config updates are enabled
        return jsonify({'message': 'Config history - to be implemented'}), 501
        
    except Exception as e:
        logger.error(f"Error fetching config history: {e}")
        return jsonify({'error': str(e)}), 500


def _sanitize_config(config):
    """Remove sensitive information from config."""
    safe_config = config.copy()
    
    # Remove sensitive keys
    sensitive_keys = [
        'password', 'secret', 'token', 'key', 'auth',
        'smtp_password', 'auth_token', 'server_key'
    ]
    
    def remove_sensitive(obj):
        if isinstance(obj, dict):
            return {
                k: '***REDACTED***' if any(sk in k.lower() for sk in sensitive_keys)
                else remove_sensitive(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [remove_sensitive(item) for item in obj]
        else:
            return obj
    
    return remove_sensitive(safe_config)


