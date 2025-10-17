"""Email notification service using SMTP."""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import List, Optional
from pathlib import Path

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationStatus
)
from ..utils.config import Config


class EmailNotificationService(BaseNotificationService):
    """
    Email notification service using SMTP.
    
    Supports:
    - HTML and plain text emails
    - Image attachments
    - Multiple recipients
    - TLS encryption
    """
    
    def __init__(self, config: Config):
        """
        Initialize email notification service.
        
        Args:
            config: System configuration object
        """
        super().__init__(config, 'email')
        
        # Load email configuration
        notification_config = config.get('notifications', {})
        email_config = notification_config.get('email', {})
        
        self.enabled = email_config.get('enabled', False)
        self.smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = email_config.get('smtp_port', 587)
        self.smtp_username = email_config.get('smtp_username', '')
        self.smtp_password = email_config.get('smtp_password', '')
        self.from_address = email_config.get('from_address', self.smtp_username)
        self.to_addresses = email_config.get('to_addresses', [])
        self.subject_template = email_config.get('subject_template', 'Security Alert: {event_type}')
        
        self.logger.info(
            'Email notification service created',
            enabled=self.enabled,
            smtp_server=self.smtp_server,
            recipients=len(self.to_addresses)
        )
    
    def initialize(self) -> bool:
        """
        Initialize the email service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.enabled:
            self.logger.info('Email notifications disabled in configuration')
            return False
        
        if not self.smtp_username or not self.smtp_password:
            self.logger.error('SMTP credentials not configured')
            return False
        
        if not self.to_addresses or len(self.to_addresses) == 0:
            self.logger.error('No recipient email addresses configured')
            return False
        
        # Test connection
        if not self.test_connection():
            self.logger.error('Failed to connect to SMTP server')
            return False
        
        self.is_initialized = True
        self.logger.info('Email notification service initialized successfully')
        return True
    
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send an email notification.
        
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
                    provider='email',
                    timestamp=time.time(),
                    error='Service not initialized'
                )
        
        try:
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            msg['Subject'] = context.get_formatted_subject()
            
            # Create HTML body
            html_body = self._create_html_body(context)
            
            # Attach HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Attach image if provided
            if context.image_path and Path(context.image_path).exists():
                try:
                    with open(context.image_path, 'rb') as img_file:
                        img_data = img_file.read()
                        image = MIMEImage(img_data)
                        image.add_header('Content-ID', '<event_image>')
                        image.add_header('Content-Disposition', 'inline', filename='event.jpg')
                        msg.attach(image)
                except Exception as e:
                    self.logger.warning(f'Failed to attach image: {e}')
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            self._record_success()
            self.logger.info(
                'Email sent successfully',
                recipients=len(self.to_addresses),
                subject=msg['Subject']
            )
            
            return NotificationResult(
                success=True,
                status=NotificationStatus.SENT,
                provider='email',
                timestamp=time.time(),
                message=f'Email sent to {len(self.to_addresses)} recipient(s)'
            )
            
        except smtplib.SMTPAuthenticationError as e:
            self._record_failure()
            error_msg = f'SMTP authentication failed: {e}'
            self.logger.error(error_msg)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='email',
                timestamp=time.time(),
                error=error_msg
            )
            
        except smtplib.SMTPException as e:
            self._record_failure()
            error_msg = f'SMTP error: {e}'
            self.logger.error(error_msg)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='email',
                timestamp=time.time(),
                error=error_msg
            )
            
        except Exception as e:
            self._record_failure()
            error_msg = f'Failed to send email: {e}'
            self.logger.error(error_msg, exc_info=True)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='email',
                timestamp=time.time(),
                error=error_msg
            )
    
    def test_connection(self) -> bool:
        """
        Test SMTP server connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            self.logger.info('SMTP connection test successful')
            return True
            
        except Exception as e:
            self.logger.error(f'SMTP connection test failed: {e}')
            return False
    
    def _create_html_body(self, context: NotificationContext) -> str:
        """
        Create HTML email body.
        
        Args:
            context: Notification context
            
        Returns:
            HTML string
        """
        # Priority color
        priority_colors = {
            'low': '#4CAF50',
            'medium': '#FF9800',
            'high': '#FF5722',
            'critical': '#D32F2F'
        }
        priority_color = priority_colors.get(context.priority.value, '#FF9800')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: {priority_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .info-row {{ margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 4px; }}
                .label {{ font-weight: bold; color: #555; }}
                .value {{ color: #333; }}
                .image {{ margin: 20px 0; text-align: center; }}
                .image img {{ max-width: 100%; height: auto; border-radius: 4px; }}
                .footer {{ padding: 20px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Security Alert</h1>
                </div>
                <div class="content">
                    <div class="info-row">
                        <span class="label">Event Type:</span>
                        <span class="value">{context.event_type.replace('_', ' ').title()}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Time:</span>
                        <span class="value">{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(context.timestamp))}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Priority:</span>
                        <span class="value" style="color: {priority_color}; font-weight: bold;">{context.priority.value.upper()}</span>
                    </div>
        """
        
        # Add zone if available
        if context.zone_name:
            html += f"""
                    <div class="info-row">
                        <span class="label">Zone:</span>
                        <span class="value">{context.zone_name}</span>
                    </div>
            """
        
        # Add detected objects if available
        if context.detected_objects and len(context.detected_objects) > 0:
            objects_str = ", ".join(context.detected_objects)
            html += f"""
                    <div class="info-row">
                        <span class="label">Detected Objects:</span>
                        <span class="value">{objects_str}</span>
                    </div>
            """
        
        # Add motion percentage if available
        if context.motion_percentage is not None:
            html += f"""
                    <div class="info-row">
                        <span class="label">Motion Level:</span>
                        <span class="value">{context.motion_percentage:.1f}%</span>
                    </div>
            """
        
        # Add threat level if available
        if context.threat_level:
            html += f"""
                    <div class="info-row">
                        <span class="label">Threat Level:</span>
                        <span class="value">{context.threat_level.upper()}</span>
                    </div>
            """
        
        # Add image if available
        if context.image_path:
            html += """
                    <div class="image">
                        <img src="cid:event_image" alt="Event Image">
                    </div>
            """
        
        # Add custom message if provided
        if context.message:
            html += f"""
                    <div class="info-row">
                        <p>{context.message.replace(chr(10), '<br>')}</p>
                    </div>
            """
        
        html += """
                </div>
                <div class="footer">
                    <p>AI Home Security Notifications System</p>
                    <p>Powered by Raspberry Pi 5</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

