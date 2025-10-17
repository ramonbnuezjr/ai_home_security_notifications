#!/usr/bin/env python3
"""Simple email notification test."""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.email_notification_service import EmailNotificationService
from src.services.base_notification_service import NotificationContext, NotificationPriority
from src.utils.config import Config


def main():
    """Test email notification service."""
    print("\n" + "=" * 70)
    print("  📧 Email Notification Test")
    print("=" * 70 + "\n")
    
    # Load config
    print("Loading configuration...")
    config = Config()
    
    # Initialize service
    print("Initializing email service...")
    service = EmailNotificationService(config)
    
    if not service.enabled:
        print("❌ Email service is disabled in configuration")
        print("\nTo enable email notifications:")
        print("1. Edit config/system_config.yaml")
        print("2. Set notifications.email.enabled to true")
        print("3. Configure SMTP settings (server, username, password)")
        print("4. Add recipient email addresses")
        return 1
    
    if not service.initialize():
        print("❌ Failed to initialize email service")
        print("\nPlease check:")
        print("- SMTP credentials are correct")
        print("- SMTP server is reachable")
        print("- Recipient addresses are configured")
        return 1
    
    print("✅ Email service initialized\n")
    
    # Test connection
    print("Testing SMTP connection...")
    if service.test_connection():
        print("✅ Connection successful\n")
    else:
        print("❌ Connection failed\n")
        return 1
    
    # Send test email
    print("Sending test email...")
    context = NotificationContext(
        event_type='system_test',
        timestamp=time.time(),
        priority=NotificationPriority.LOW,
        subject='Security System Test Email',
        message='This is a test email from your AI Home Security System.\n\nIf you received this, email notifications are working correctly!',
        detected_objects=['Test Object'],
        zone_name='Test Zone'
    )
    
    result = service.send_notification(context)
    
    if result.success:
        print(f"✅ Email sent successfully!")
        print(f"   {result.message}")
    else:
        print(f"❌ Failed to send email")
        print(f"   Error: {result.error}")
        return 1
    
    # Show statistics
    print("\n📊 Statistics:")
    stats = service.get_statistics()
    print(f"   Sent: {stats['sent_count']}")
    print(f"   Failed: {stats['failed_count']}")
    print(f"   Success Rate: {stats['success_rate']:.1%}")
    
    print("\n✅ Email test complete!\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())

