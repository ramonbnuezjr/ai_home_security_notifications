"""Notification manager to coordinate all notification services."""

import time
from typing import List, Dict, Any, Optional
from threading import Lock, Thread
from queue import Queue, Empty
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationPriority,
    NotificationStatus
)
from .email_notification_service import EmailNotificationService
from .sms_notification_service import SMSNotificationService
from .push_notification_service import PushNotificationService
from .voice_notification_service import VoiceNotificationService
from ..utils.config import Config
from ..utils.logger import get_logger


@dataclass
class NotificationHistory:
    """Track notification history for throttling."""
    notifications: deque = field(default_factory=lambda: deque(maxlen=100))
    last_notification_time: float = 0.0
    hourly_count: int = 0
    hourly_reset_time: float = 0.0
    
    def add_notification(self, context: NotificationContext, results: List[NotificationResult]):
        """Add a notification to history."""
        self.notifications.append({
            'context': context,
            'results': results,
            'timestamp': time.time()
        })
        self.last_notification_time = time.time()
        self.hourly_count += 1
    
    def should_throttle(self, cooldown_period: int, max_per_hour: int) -> tuple[bool, str]:
        """
        Check if notification should be throttled.
        
        Returns:
            (should_throttle, reason)
        """
        current_time = time.time()
        
        # Check cooldown period
        if self.last_notification_time > 0:
            time_since_last = current_time - self.last_notification_time
            if time_since_last < cooldown_period:
                return True, f'Cooldown active ({cooldown_period - time_since_last:.1f}s remaining)'
        
        # Reset hourly counter if needed
        if current_time - self.hourly_reset_time > 3600:
            self.hourly_count = 0
            self.hourly_reset_time = current_time
        
        # Check hourly limit
        if self.hourly_count >= max_per_hour:
            return True, f'Hourly limit reached ({self.hourly_count}/{max_per_hour})'
        
        return False, ''
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification history statistics."""
        total = len(self.notifications)
        
        if total == 0:
            return {
                'total': 0,
                'last_notification': None,
                'hourly_count': self.hourly_count
            }
        
        # Count by status
        sent = sum(1 for n in self.notifications if any(r.success for r in n['results']))
        failed = sum(1 for n in self.notifications if all(not r.success for r in n['results']))
        
        # Count by priority
        priority_counts = {}
        for n in self.notifications:
            priority = n['context'].priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            'total': total,
            'sent': sent,
            'failed': failed,
            'success_rate': sent / total if total > 0 else 0,
            'last_notification': datetime.fromtimestamp(self.last_notification_time).isoformat(),
            'hourly_count': self.hourly_count,
            'priority_distribution': priority_counts
        }


class NotificationManager:
    """
    Central manager for all notification services.
    
    Features:
    - Coordinates multiple notification providers
    - Throttling and cooldown management
    - Priority-based notification routing
    - Async notification delivery
    - Statistics and monitoring
    """
    
    def __init__(self, config: Config):
        """
        Initialize notification manager.
        
        Args:
            config: System configuration object
        """
        self.config = config
        self.logger = get_logger('notification_manager')
        
        # Load notification configuration
        notification_config = config.get('notifications', {})
        
        self.enabled = notification_config.get('enabled', True)
        self.cooldown_period = notification_config.get('cooldown_period', 300)  # seconds
        self.max_per_hour = notification_config.get('max_notifications_per_hour', 10)
        
        # Initialize services
        self.services: Dict[str, BaseNotificationService] = {}
        self._initialize_services()
        
        # Notification queue for async processing
        self.notification_queue = Queue(maxsize=100)
        self.worker_thread: Optional[Thread] = None
        self.is_running = False
        
        # History and throttling
        self.history = NotificationHistory()
        self.lock = Lock()
        
        self.logger.info(
            'Notification manager initialized',
            enabled=self.enabled,
            services=list(self.services.keys()),
            cooldown=self.cooldown_period,
            max_per_hour=self.max_per_hour
        )
    
    def _initialize_services(self) -> None:
        """Initialize all notification services."""
        try:
            # Email service
            email_service = EmailNotificationService(self.config)
            if email_service.initialize():
                self.services['email'] = email_service
                self.logger.info('Email service registered')
            
        except Exception as e:
            self.logger.error(f'Failed to initialize email service: {e}')
        
        try:
            # SMS service
            sms_service = SMSNotificationService(self.config)
            if sms_service.initialize():
                self.services['sms'] = sms_service
                self.logger.info('SMS service registered')
            
        except Exception as e:
            self.logger.error(f'Failed to initialize SMS service: {e}')
        
        try:
            # Push notification service
            push_service = PushNotificationService(self.config)
            if push_service.initialize():
                self.services['push'] = push_service
                self.logger.info('Push notification service registered')
            
        except Exception as e:
            self.logger.error(f'Failed to initialize push service: {e}')
        
        try:
            # Voice notification service
            voice_service = VoiceNotificationService(self.config)
            if voice_service.initialize():
                self.services['voice'] = voice_service
                self.logger.info('Voice notification service registered')
            
        except Exception as e:
            self.logger.error(f'Failed to initialize voice service: {e}')
    
    def start(self) -> None:
        """Start the notification manager and worker thread."""
        if self.is_running:
            self.logger.warning('Notification manager already running')
            return
        
        self.is_running = True
        self.worker_thread = Thread(target=self._worker, daemon=True, name='NotificationWorker')
        self.worker_thread.start()
        
        self.logger.info('Notification manager started')
    
    def stop(self) -> None:
        """Stop the notification manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        # Shutdown all services
        for service in self.services.values():
            service.shutdown()
        
        self.logger.info('Notification manager stopped')
    
    def send_notification(
        self,
        context: NotificationContext,
        services: Optional[List[str]] = None,
        force: bool = False,
        async_mode: bool = True
    ) -> List[NotificationResult]:
        """
        Send a notification through specified services.
        
        Args:
            context: Notification context
            services: List of service names to use (None = all enabled)
            force: Skip throttling if True
            async_mode: Queue for async delivery if True
            
        Returns:
            List of NotificationResult from each service
        """
        if not self.enabled:
            self.logger.info('Notifications disabled')
            return [NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='manager',
                timestamp=time.time(),
                error='Notifications disabled'
            )]
        
        # Check throttling unless forced
        if not force:
            should_throttle, reason = self.history.should_throttle(
                self.cooldown_period,
                self.max_per_hour
            )
            
            if should_throttle:
                self.logger.info(f'Notification throttled: {reason}')
                
                # For critical alerts, override throttling
                if context.priority == NotificationPriority.CRITICAL:
                    self.logger.warning('Critical alert - overriding throttle')
                else:
                    return [NotificationResult(
                        success=False,
                        status=NotificationStatus.THROTTLED,
                        provider='manager',
                        timestamp=time.time(),
                        message=reason
                    )]
        
        # Queue for async processing
        if async_mode:
            try:
                self.notification_queue.put((context, services), block=False)
                self.logger.debug('Notification queued for async delivery')
                return [NotificationResult(
                    success=True,
                    status=NotificationStatus.PENDING,
                    provider='manager',
                    timestamp=time.time(),
                    message='Queued for delivery'
                )]
            except Exception as e:
                self.logger.error(f'Failed to queue notification: {e}')
        
        # Synchronous delivery
        return self._deliver_notification(context, services)
    
    def _deliver_notification(
        self,
        context: NotificationContext,
        services: Optional[List[str]] = None
    ) -> List[NotificationResult]:
        """
        Deliver notification to specified services.
        
        Args:
            context: Notification context
            services: List of service names (None = all)
            
        Returns:
            List of NotificationResult from each service
        """
        results = []
        
        # Determine which services to use
        target_services = services if services else list(self.services.keys())
        
        # Send through each service
        for service_name in target_services:
            service = self.services.get(service_name)
            
            if not service:
                self.logger.warning(f'Service not available: {service_name}')
                results.append(NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider=service_name,
                    timestamp=time.time(),
                    error='Service not available'
                ))
                continue
            
            try:
                # Send notification
                result = service.send_notification(context)
                results.append(result)
                
                self.logger.debug(
                    f'Notification sent via {service_name}',
                    success=result.success,
                    status=result.status.value
                )
                
            except Exception as e:
                self.logger.error(f'Error sending via {service_name}: {e}', exc_info=True)
                results.append(NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider=service_name,
                    timestamp=time.time(),
                    error=str(e)
                ))
        
        # Record in history
        with self.lock:
            self.history.add_notification(context, results)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        self.logger.info(
            f'Notification delivery complete',
            successful=successful,
            total=len(results),
            priority=context.priority.value
        )
        
        return results
    
    def _worker(self) -> None:
        """Worker thread for async notification delivery."""
        self.logger.info('Notification worker thread started')
        
        while self.is_running:
            try:
                # Get notification from queue (with timeout)
                context, services = self.notification_queue.get(timeout=1.0)
                
                # Deliver notification
                self._deliver_notification(context, services)
                
                self.notification_queue.task_done()
                
            except Empty:
                # No notifications in queue, continue waiting
                continue
                
            except Exception as e:
                self.logger.error(f'Error in notification worker: {e}', exc_info=True)
        
        self.logger.info('Notification worker thread stopped')
    
    def send_test_notification(self, service_name: Optional[str] = None) -> Dict[str, NotificationResult]:
        """
        Send a test notification.
        
        Args:
            service_name: Specific service to test (None = all)
            
        Returns:
            Dictionary mapping service names to results
        """
        context = NotificationContext(
            event_type='system_test',
            timestamp=time.time(),
            priority=NotificationPriority.LOW,
            subject='Security System Test',
            message='This is a test notification from your AI Home Security System.',
            detected_objects=['Test'],
            zone_name='System'
        )
        
        services = [service_name] if service_name else None
        results = self._deliver_notification(context, services)
        
        return {r.provider: r for r in results}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get notification manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            return {
                'enabled': self.enabled,
                'services': {
                    name: service.get_statistics()
                    for name, service in self.services.items()
                },
                'history': self.history.get_statistics(),
                'queue_size': self.notification_queue.qsize(),
                'throttling': {
                    'cooldown_period': self.cooldown_period,
                    'max_per_hour': self.max_per_hour,
                    'current_hourly_count': self.history.hourly_count
                }
            }
    
    def reset_throttling(self) -> None:
        """Reset throttling counters."""
        with self.lock:
            self.history.hourly_count = 0
            self.history.hourly_reset_time = time.time()
            self.history.last_notification_time = 0.0
            self.logger.info('Throttling counters reset')
    
    def update_settings(
        self,
        cooldown_period: Optional[int] = None,
        max_per_hour: Optional[int] = None
    ) -> None:
        """
        Update notification settings.
        
        Args:
            cooldown_period: New cooldown period in seconds
            max_per_hour: New max notifications per hour
        """
        with self.lock:
            if cooldown_period is not None:
                self.cooldown_period = cooldown_period
                self.logger.info(f'Cooldown period updated to {cooldown_period}s')
            
            if max_per_hour is not None:
                self.max_per_hour = max_per_hour
                self.logger.info(f'Max per hour updated to {max_per_hour}')

