"""
Flask web application for AI Home Security System dashboard.
Provides live video streaming, event history, and system configuration.
"""

import logging
from pathlib import Path
from flask import Flask, render_template
from datetime import timedelta

# Import blueprints
from src.web.api.events import events_bp
from src.web.api.stream import stream_bp
from src.web.api.metrics import metrics_bp
from src.web.api.config_api import config_bp
from src.web.api.notifications import notifications_bp
from src.web.api.auth import auth_bp
from src.web.api.audit import audit_bp
from src.web.api.privacy import privacy_bp

# Import services
from src.services.database_service import DatabaseService
from src.services.camera_service import CameraService
from src.services.auth_service import AuthService
from src.services.encryption_service import EncryptionService
from src.services.privacy_service import PrivacyService
from src.utils.config import load_config


logger = logging.getLogger(__name__)


def create_app(config_path: str = None):
    """
    Flask application factory.
    
    Args:
        config_path: Path to system configuration file
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load system configuration
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "system_config.yaml"
    
    system_config = load_config(str(config_path))
    web_config = system_config.get('web', {})
    db_config = system_config.get('database', {})
    
    # Flask configuration
    app.config['SECRET_KEY'] = web_config.get('secret_key', 'dev-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = web_config.get('max_content_length', 16 * 1024 * 1024)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=web_config.get('session_timeout', 3600))
    
    # Store system config in app context
    app.config['SYSTEM_CONFIG'] = system_config
    app.config['WEB_CONFIG'] = web_config
    app.config['DB_CONFIG'] = db_config
    
    # Initialize services
    logger.info("Initializing database service...")
    db_service = DatabaseService(
        db_path=db_config.get('path'),
        fallback_path=db_config.get('fallback_path')
    )
    app.config['DB_SERVICE'] = db_service
    
    logger.info("Initializing authentication service...")
    auth_service = AuthService(
        database_service=db_service,
        jwt_secret=app.config['SECRET_KEY'],
        jwt_expiry_hours=web_config.get('jwt_expiry_hours', 24)
    )
    app.config['AUTH_SERVICE'] = auth_service
    
    logger.info("Initializing encryption service...")
    encryption_service = EncryptionService()
    app.config['ENCRYPTION_SERVICE'] = encryption_service
    
    logger.info("Initializing privacy service...")
    privacy_service = PrivacyService(
        database_service=db_service,
        media_base_path=system_config.get('storage', {}).get('media_path', '/tmp/ai_security_media')
    )
    app.config['PRIVACY_SERVICE'] = privacy_service
    
    logger.info("Camera service will be initialized on first stream request")
    app.config['CAMERA_SERVICE'] = None  # Lazy load when needed
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(privacy_bp, url_prefix='/api/privacy')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(stream_bp, url_prefix='/api/stream')
    app.register_blueprint(metrics_bp, url_prefix='/api/metrics')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    
    # Main routes
    @app.route('/')
    def index():
        """Dashboard home page."""
        return render_template('dashboard.html')
    
    @app.route('/login')
    def login_page():
        """Login page."""
        return render_template('login.html')
    
    @app.route('/events')
    def events_page():
        """Event history page."""
        return render_template('events.html')
    
    @app.route('/settings')
    def settings_page():
        """System settings page."""
        return render_template('settings.html')
    
    @app.route('/monitoring')
    def monitoring_page():
        """System monitoring page."""
        return render_template('monitoring.html')
    
    @app.route('/users')
    def users_page():
        """User management page (admin only)."""
        return render_template('users.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy', 'service': 'ai-security-dashboard'}, 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return {'error': 'Internal server error'}, 500
    
    logger.info("Flask application created successfully")
    return app


def run_server(config_path: str = None):
    """
    Run the Flask development server.
    
    Args:
        config_path: Path to system configuration file
    """
    app = create_app(config_path)
    web_config = app.config['WEB_CONFIG']
    
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 5000)
    debug = web_config.get('debug', False)
    threaded = web_config.get('threaded', True)
    
    logger.info(f"Starting web server on {host}:{port}")
    logger.info(f"Dashboard will be available at http://{host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=threaded,
        use_reloader=False  # Disable reloader to prevent camera conflicts
    )


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_server()



