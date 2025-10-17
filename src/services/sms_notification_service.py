"""SMS notification service using Twilio."""

import time
from typing import List, Optional

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationStatus
)
from ..utils.config import Config


class SMSNotificationService(BaseNotificationService):
    """
    SMS notification service using Twilio.
    
    Supports:
    - SMS messages to multiple recipients
    - MMS with image attachments
    - Delivery status tracking
    """
    
    def __init__(self, config: Config):
        """
        Initialize SMS notification service.
        
        Args:
            config: System configuration object
        """
        super().__init__(config, 'sms')
        
        # Check if Twilio is available
        if not TWILIO_AVAILABLE:
            self.logger.warning('Twilio library not installed. SMS notifications unavailable.')
            self.enabled = False
            return
        
        # Load SMS configuration
        notification_config = config.get('notifications', {})
        sms_config = notification_config.get('sms', {})
        
        self.enabled = sms_config.get('enabled', False)
        self.provider = sms_config.get('provider', 'twilio')
        
        # Twilio configuration
        twilio_config = sms_config.get('twilio', {})
        self.account_sid = twilio_config.get('account_sid', '')
        self.auth_token = twilio_config.get('auth_token', '')
        self.from_number = twilio_config.get('from_number', '')
        self.to_numbers = twilio_config.get('to_numbers', [])
        
        self.client: Optional[Client] = None
        
        self.logger.info(
            'SMS notification service created',
            enabled=self.enabled,
            provider=self.provider,
            recipients=len(self.to_numbers)
        )
    
    def initialize(self) -> bool:
        """
        Initialize the SMS service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.enabled:
            self.logger.info('SMS notifications disabled in configuration')
            return False
        
        if not TWILIO_AVAILABLE:
            self.logger.error('Twilio library not installed. Install with: pip install twilio')
            return False
        
        if not self.account_sid or not self.auth_token:
            self.logger.error('Twilio credentials not configured')
            return False
        
        if not self.from_number:
            self.logger.error('Twilio from_number not configured')
            return False
        
        if not self.to_numbers or len(self.to_numbers) == 0:
            self.logger.error('No recipient phone numbers configured')
            return False
        
        try:
            # Initialize Twilio client
            self.client = Client(self.account_sid, self.auth_token)
            
            # Test connection
            if not self.test_connection():
                self.logger.error('Failed to connect to Twilio API')
                return False
            
            self.is_initialized = True
            self.logger.info('SMS notification service initialized successfully')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to initialize Twilio client: {e}')
            return False
    
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send an SMS notification.
        
        Args:
            context: Notification context
            
        Returns:
            NotificationResult with delivery status
        """
        if not self.is_initialized:
            if not self.initialize():
                return NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider='sms',
                    timestamp=time.time(),
                    error='Service not initialized'
                )
        
        if not self.client:
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='sms',
                timestamp=time.time(),
                error='Twilio client not available'
            )
        
        try:
            # Create SMS message
            message_body = self._create_sms_message(context)
            
            # Send to all recipients
            successful_sends = 0
            failed_sends = 0
            errors = []
            
            for to_number in self.to_numbers:
                try:
                    # Send SMS (or MMS if image is provided)
                    if context.image_path:
                        # Send MMS with image
                        message = self.client.messages.create(
                            body=message_body,
                            from_=self.from_number,
                            to=to_number,
                            media_url=[context.image_path] if context.image_path.startswith('http') else []
                        )
                    else:
                        # Send plain SMS
                        message = self.client.messages.create(
                            body=message_body,
                            from_=self.from_number,
                            to=to_number
                        )
                    
                    if message.sid:
                        successful_sends += 1
                        self.logger.debug(f'SMS sent to {to_number}, SID: {message.sid}')
                    else:
                        failed_sends += 1
                        errors.append(f'Failed to send to {to_number}')
                        
                except TwilioRestException as e:
                    failed_sends += 1
                    error_msg = f'Twilio error for {to_number}: {e.msg}'
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    
                except Exception as e:
                    failed_sends += 1
                    error_msg = f'Error sending to {to_number}: {e}'
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Determine overall success
            if successful_sends > 0:
                self._record_success()
                self.logger.info(
                    'SMS sent',
                    successful=successful_sends,
                    failed=failed_sends
                )
                
                return NotificationResult(
                    success=True,
                    status=NotificationStatus.SENT,
                    provider='sms',
                    timestamp=time.time(),
                    message=f'SMS sent to {successful_sends}/{len(self.to_numbers)} recipient(s)',
                    metadata={'successful': successful_sends, 'failed': failed_sends}
                )
            else:
                self._record_failure()
                error_msg = f'Failed to send SMS to any recipients: {"; ".join(errors)}'
                self.logger.error(error_msg)
                
                return NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    provider='sms',
                    timestamp=time.time(),
                    error=error_msg
                )
            
        except Exception as e:
            self._record_failure()
            error_msg = f'Failed to send SMS: {e}'
            self.logger.error(error_msg, exc_info=True)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='sms',
                timestamp=time.time(),
                error=error_msg
            )
    
    def test_connection(self) -> bool:
        """
        Test Twilio API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Try to fetch account info to verify credentials
            account = self.client.api.accounts(self.account_sid).fetch()
            if account.sid == self.account_sid:
                self.logger.info('Twilio API connection test successful')
                return True
            return False
            
        except TwilioRestException as e:
            self.logger.error(f'Twilio API connection test failed: {e.msg}')
            return False
            
        except Exception as e:
            self.logger.error(f'Twilio API connection test failed: {e}')
            return False
    
    def _create_sms_message(self, context: NotificationContext) -> str:
        """
        Create SMS message text.
        
        Args:
            context: Notification context
            
        Returns:
            SMS message string (max 160 chars for best compatibility)
        """
        # SMS is limited, so we keep it concise
        parts = []
        
        # Add emoji based on priority
        emoji_map = {
            'low': '⚠️',
            'medium': '🚨',
            'high': '🚨',
            'critical': '🚨🚨'
        }
        emoji = emoji_map.get(context.priority.value, '🚨')
        
        parts.append(f"{emoji} Security Alert")
        
        # Add detected objects (most important info)
        if context.detected_objects and len(context.detected_objects) > 0:
            objects_str = ", ".join(context.detected_objects[:2])
            if len(context.detected_objects) > 2:
                objects_str += f" +{len(context.detected_objects) - 2}"
            parts.append(f"Detected: {objects_str}")
        else:
            parts.append(f"{context.event_type.replace('_', ' ').title()}")
        
        # Add zone if available
        if context.zone_name:
            parts.append(f"Zone: {context.zone_name}")
        
        # Add time
        time_str = time.strftime('%H:%M', time.localtime(context.timestamp))
        parts.append(f"Time: {time_str}")
        
        return "\n".join(parts)

