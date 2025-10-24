#!/usr/bin/env python3
"""
Setup HTTPS/TLS for Flask web dashboard.
Generates self-signed certificates or uses existing certificates.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.encryption_service import EncryptionService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_tls_certificates(config_dir: str, domain: str = "localhost"):
    """
    Setup TLS certificates for HTTPS.
    
    Args:
        config_dir: Directory to store certificates
        domain: Domain name for certificate (default: localhost)
    """
    logger.info("Setting up TLS certificates...")
    
    cert_dir = Path(config_dir) / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"
    
    # Check if certificates already exist
    if cert_path.exists() and key_path.exists():
        logger.info(f"Certificates already exist at {cert_dir}")
        response = input("Regenerate certificates? (y/N): ")
        if response.lower() != 'y':
            logger.info("Using existing certificates")
            return str(cert_path), str(key_path)
    
    # Generate self-signed certificate
    logger.info(f"Generating self-signed certificate for {domain}...")
    
    encryption_service = EncryptionService()
    cert_pem, key_pem = encryption_service.generate_tls_certificate(
        domain_name=domain,
        days_valid=365
    )
    
    # Save certificates
    with open(cert_path, 'wb') as f:
        f.write(cert_pem)
    
    with open(key_path, 'wb') as f:
        f.write(key_pem)
    
    # Set appropriate permissions (readable only by owner)
    os.chmod(cert_path, 0o600)
    os.chmod(key_path, 0o600)
    
    logger.info(f"✅ Certificate saved to: {cert_path}")
    logger.info(f"✅ Private key saved to: {key_path}")
    logger.info("")
    logger.info("⚠️  This is a self-signed certificate for development/testing.")
    logger.info("⚠️  Browsers will show a security warning.")
    logger.info("")
    logger.info("For production, consider using Let's Encrypt:")
    logger.info("  1. Install certbot: sudo apt-get install certbot")
    logger.info("  2. Get certificate: sudo certbot certonly --standalone -d yourdomain.com")
    logger.info("  3. Update paths in system_config.yaml")
    
    return str(cert_path), str(key_path)


def update_config_file(config_path: str, cert_path: str, key_path: str):
    """
    Update system configuration with certificate paths.
    
    Args:
        config_path: Path to system configuration file
        cert_path: Path to certificate file
        key_path: Path to private key file
    """
    import yaml
    
    logger.info(f"Updating configuration file: {config_path}")
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return False
    
    # Load existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update TLS settings
    if 'web' not in config:
        config['web'] = {}
    
    config['web']['use_https'] = True
    config['web']['cert_file'] = cert_path
    config['web']['key_file'] = key_path
    
    # Backup original config
    backup_path = config_path.with_suffix('.yaml.backup')
    if config_path.exists() and not backup_path.exists():
        import shutil
        shutil.copy(config_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
    
    # Write updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    logger.info("✅ Configuration updated successfully")
    return True


def test_https(cert_path: str, key_path: str, port: int = 5000):
    """
    Test HTTPS configuration with a minimal Flask server.
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        port: Port to test on (default: 5000)
    """
    try:
        from flask import Flask
        import ssl
        
        logger.info(f"Testing HTTPS configuration on port {port}...")
        
        app = Flask(__name__)
        
        @app.route('/health')
        def health():
            return {'status': 'healthy', 'https': True}
        
        # Create SSL context
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_path, key_path)
        
        logger.info(f"Starting test server on https://localhost:{port}")
        logger.info("Press Ctrl+C to stop the test server")
        logger.info("")
        logger.info(f"Test with: curl -k https://localhost:{port}/health")
        
        app.run(
            host='0.0.0.0',
            port=port,
            ssl_context=ssl_context
        )
        
    except Exception as e:
        logger.error(f"HTTPS test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Setup HTTPS/TLS for AI Security System web dashboard'
    )
    parser.add_argument(
        '--config-dir',
        default='config',
        help='Directory to store certificates (default: config)'
    )
    parser.add_argument(
        '--config-file',
        default='config/system_config.yaml',
        help='System configuration file to update (default: config/system_config.yaml)'
    )
    parser.add_argument(
        '--domain',
        default='localhost',
        help='Domain name for certificate (default: localhost)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test HTTPS configuration with a test server'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port for test server (default: 5000)'
    )
    
    args = parser.parse_args()
    
    try:
        # Setup certificates
        cert_path, key_path = setup_tls_certificates(args.config_dir, args.domain)
        
        # Update configuration
        if not args.test:
            config_file = Path(args.config_file)
            if config_file.exists():
                update_config_file(str(config_file), cert_path, key_path)
            else:
                logger.warning(f"Config file not found: {config_file}")
                logger.info("You can manually add these to your config:")
                logger.info(f"  cert_file: {cert_path}")
                logger.info(f"  key_file: {key_path}")
        
        # Test if requested
        if args.test:
            logger.info("")
            test_https(cert_path, key_path, args.port)
        else:
            logger.info("")
            logger.info("✅ HTTPS setup complete!")
            logger.info("")
            logger.info("To enable HTTPS in your Flask app:")
            logger.info("  1. Update run_dashboard.py to use ssl_context")
            logger.info("  2. Or run: python scripts/run_dashboard_https.py")
            logger.info("")
            logger.info("To test the configuration:")
            logger.info(f"  python {__file__} --test")
    
    except KeyboardInterrupt:
        logger.info("\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

