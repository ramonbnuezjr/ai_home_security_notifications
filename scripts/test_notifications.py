#!/usr/bin/env python3
"""Test script for notification system."""

import sys
import os
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.base_notification_service import NotificationContext, NotificationPriority
from src.services.notification_manager import NotificationManager
from src.utils.config import Config
from src.utils.logger import get_logger


def print_banner(text: str):
    """Print a formatted banner."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def test_individual_services(manager: NotificationManager):
    """Test each notification service individually."""
    print_banner("Testing Individual Services")
    
    # Create test context
    context = NotificationContext(
        event_type='motion_detected',
        timestamp=time.time(),
        priority=NotificationPriority.MEDIUM,
        subject='Test Alert',
        message='This is a test notification from your security system.',
        detected_objects=['person', 'car'],
        motion_percentage=15.5,
        threat_level='medium',
        zone_name='Front Door'
    )
    
    # Test each service
    for service_name, service in manager.services.items():
        print(f"\n📧 Testing {service_name.upper()} service...")
        print(f"   Enabled: {service.enabled}")
        print(f"   Initialized: {service.is_initialized}")
        
        if not service.is_initialized:
            print(f"   ⚠️  Service not initialized, skipping")
            continue
        
        try:
            result = service.send_notification(context)
            
            if result.success:
                print(f"   ✅ SUCCESS: {result.message}")
            else:
                print(f"   ❌ FAILED: {result.error}")
            
            # Show statistics
            stats = service.get_statistics()
            print(f"   Stats: {stats['sent_count']} sent, {stats['failed_count']} failed")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        time.sleep(1)  # Small delay between tests


def test_notification_manager(manager: NotificationManager):
    """Test the notification manager."""
    print_banner("Testing Notification Manager")
    
    # Test 1: Regular notification
    print("\n1️⃣  Testing regular notification (all services)...")
    context = NotificationContext(
        event_type='object_detected',
        timestamp=time.time(),
        priority=NotificationPriority.MEDIUM,
        detected_objects=['person', 'backpack'],
        motion_percentage=12.3,
        zone_name='Backyard'
    )
    
    results = manager.send_notification(context, async_mode=False)
    print(f"   Results: {len(results)} service(s)")
    for result in results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.provider}: {result.status.value}")
    
    time.sleep(2)
    
    # Test 2: High priority notification
    print("\n2️⃣  Testing high priority notification...")
    context = NotificationContext(
        event_type='security_breach',
        timestamp=time.time(),
        priority=NotificationPriority.HIGH,
        detected_objects=['person', 'crowbar'],
        threat_level='high',
        zone_name='Back Door'
    )
    
    results = manager.send_notification(context, async_mode=False)
    for result in results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.provider}: {result.status.value}")
    
    time.sleep(2)
    
    # Test 3: Test throttling
    print("\n3️⃣  Testing throttling mechanism...")
    print("   Sending 3 notifications rapidly...")
    
    for i in range(3):
        context = NotificationContext(
            event_type='motion_detected',
            timestamp=time.time(),
            priority=NotificationPriority.LOW,
            message=f'Test notification {i+1}'
        )
        
        results = manager.send_notification(context, async_mode=False)
        
        if any(r.status.value == 'throttled' for r in results):
            print(f"   {i+1}. ⏸️  THROTTLED (expected)")
        else:
            print(f"   {i+1}. ✅ Sent")
        
        time.sleep(0.5)
    
    # Test 4: Critical alert (should override throttling)
    print("\n4️⃣  Testing critical alert (should override throttling)...")
    context = NotificationContext(
        event_type='emergency',
        timestamp=time.time(),
        priority=NotificationPriority.CRITICAL,
        detected_objects=['fire', 'smoke'],
        threat_level='critical',
        message='CRITICAL: Emergency detected!'
    )
    
    results = manager.send_notification(context, async_mode=False, force=True)
    for result in results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.provider}: {result.status.value}")


def test_async_mode(manager: NotificationManager):
    """Test async notification delivery."""
    print_banner("Testing Async Mode")
    
    # Start the manager
    manager.start()
    
    print("Sending 3 async notifications...")
    
    for i in range(3):
        context = NotificationContext(
            event_type='motion_detected',
            timestamp=time.time(),
            priority=NotificationPriority.LOW,
            message=f'Async test notification {i+1}',
            zone_name=f'Zone {i+1}'
        )
        
        results = manager.send_notification(context, async_mode=True, force=True)
        print(f"   {i+1}. Queued: {results[0].message}")
    
    print("\nWaiting for async delivery...")
    time.sleep(5)
    
    print("✅ Async delivery complete")
    
    manager.stop()


def test_statistics(manager: NotificationManager):
    """Test statistics reporting."""
    print_banner("Notification Statistics")
    
    stats = manager.get_statistics()
    
    print(f"Manager Status:")
    print(f"  Enabled: {stats['enabled']}")
    print(f"  Queue Size: {stats['queue_size']}")
    
    print(f"\nThrottling:")
    throttle = stats['throttling']
    print(f"  Cooldown Period: {throttle['cooldown_period']}s")
    print(f"  Max Per Hour: {throttle['max_per_hour']}")
    print(f"  Current Hour Count: {throttle['current_hourly_count']}")
    
    print(f"\nServices:")
    for service_name, service_stats in stats['services'].items():
        print(f"\n  {service_name.upper()}:")
        print(f"    Enabled: {service_stats['enabled']}")
        print(f"    Initialized: {service_stats['initialized']}")
        print(f"    Sent: {service_stats['sent_count']}")
        print(f"    Failed: {service_stats['failed_count']}")
        print(f"    Success Rate: {service_stats['success_rate']:.1%}")
    
    print(f"\nHistory:")
    history = stats['history']
    print(f"  Total Notifications: {history['total']}")
    if history['total'] > 0:
        print(f"  Sent: {history['sent']}")
        print(f"  Failed: {history['failed']}")
        print(f"  Success Rate: {history['success_rate']:.1%}")
        print(f"  Last Notification: {history['last_notification']}")
        
        if 'priority_distribution' in history:
            print(f"  Priority Distribution:")
            for priority, count in history['priority_distribution'].items():
                print(f"    {priority}: {count}")


def main():
    """Main test function."""
    print_banner("🔔 Notification System Test Suite")
    
    # Initialize logger
    logger = get_logger('test_notifications')
    
    print("Loading configuration...")
    try:
        config = Config()
        print("✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    print("\nInitializing notification manager...")
    try:
        manager = NotificationManager(config)
        print(f"✅ Manager initialized with {len(manager.services)} service(s)")
        
        if len(manager.services) == 0:
            print("⚠️  Warning: No notification services are configured/available")
            print("   Please configure at least one notification service in config/system_config.yaml")
            return 1
        
    except Exception as e:
        print(f"❌ Failed to initialize manager: {e}")
        return 1
    
    # Run tests
    try:
        # Test 1: Individual services
        test_individual_services(manager)
        
        # Test 2: Notification manager
        test_notification_manager(manager)
        
        # Test 3: Async mode
        test_async_mode(manager)
        
        # Test 4: Statistics
        test_statistics(manager)
        
        print_banner("✅ All Tests Complete")
        
        # Reset throttling for next run
        manager.reset_throttling()
        print("\n💡 Tip: Throttling counters have been reset")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        manager.stop()
        return 130
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        manager.stop()


if __name__ == '__main__':
    sys.exit(main())

