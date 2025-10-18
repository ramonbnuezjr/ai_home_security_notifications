#!/usr/bin/env python3
"""
Launch script for AI Security System Web Dashboard.
Starts the Flask web server with proper configuration.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web.app import run_server

def main():
    """Main entry point for web dashboard."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(project_root / 'logs' / 'web_dashboard.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("AI Home Security System - Web Dashboard")
    logger.info("=" * 60)
    
    # Get config path
    config_path = project_root / "config" / "system_config.yaml"
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please create config/system_config.yaml from the template")
        sys.exit(1)
    
    logger.info(f"Using configuration: {config_path}")
    
    try:
        # Run the server
        run_server(str(config_path))
    except KeyboardInterrupt:
        logger.info("\nShutting down web dashboard...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()


