"""Voice notification service using text-to-speech."""

import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationStatus
)
from ..utils.config import Config


class VoiceNotificationService(BaseNotificationService):
    """
    Voice notification service using text-to-speech.
    
    Supports:
    - Text-to-speech announcements
    - Multiple TTS engines (pyttsx3, espeak, festival)
    - Configurable voice settings (rate, volume, voice)
    - Audio file generation for playback
    """
    
    def __init__(self, config: Config):
        """
        Initialize voice notification service.
        
        Args:
            config: System configuration object
        """
        super().__init__(config, 'voice')
        
        # Load voice configuration
        notification_config = config.get('notifications', {})
        voice_config = notification_config.get('voice', {})
        
        self.enabled = voice_config.get('enabled', False)
        self.tts_enabled = voice_config.get('text_to_speech', True)
        
        # Voice settings
        voice_settings = voice_config.get('voice_settings', {})
        self.rate = voice_settings.get('rate', 150)  # words per minute
        self.volume = voice_settings.get('volume', 0.8)  # 0.0 to 1.0
        self.voice_id = voice_settings.get('voice', None)
        
        # TTS engine
        self.engine: Optional[Any] = None
        self.tts_method = 'pyttsx3'  # default
        
        self.logger.info(
            'Voice notification service created',
            enabled=self.enabled,
            tts_enabled=self.tts_enabled
        )
    
    def initialize(self) -> bool:
        """
        Initialize the voice notification service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.enabled:
            self.logger.info('Voice notifications disabled in configuration')
            return False
        
        if not self.tts_enabled:
            self.logger.info('Text-to-speech disabled in configuration')
            return False
        
        # Try to initialize pyttsx3 first
        if PYTTSX3_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
                
                # Set voice if specified
                if self.voice_id:
                    voices = self.engine.getProperty('voices')
                    for voice in voices:
                        if self.voice_id in voice.id or self.voice_id in voice.name:
                            self.engine.setProperty('voice', voice.id)
                            break
                
                self.tts_method = 'pyttsx3'
                self.is_initialized = True
                self.logger.info('Voice service initialized with pyttsx3')
                return True
                
            except Exception as e:
                self.logger.warning(f'Failed to initialize pyttsx3: {e}')
        
        # Fallback to espeak if available
        if self._check_command_available('espeak'):
            self.tts_method = 'espeak'
            self.is_initialized = True
            self.logger.info('Voice service initialized with espeak')
            return True
        
        # Fallback to festival if available
        if self._check_command_available('festival'):
            self.tts_method = 'festival'
            self.is_initialized = True
            self.logger.info('Voice service initialized with festival')
            return True
        
        self.logger.error('No TTS engine available. Install pyttsx3, espeak, or festival')
        return False
    
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send a voice notification (speak the alert).
        
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
                    provider='voice',
                    timestamp=time.time(),
                    error='Service not initialized'
                )
        
        try:
            # Create spoken message
            message = self._create_voice_message(context)
            
            # Speak the message based on available TTS method
            if self.tts_method == 'pyttsx3' and self.engine:
                self.engine.say(message)
                self.engine.runAndWait()
                
            elif self.tts_method == 'espeak':
                subprocess.run(
                    ['espeak', '-s', str(self.rate), '-a', str(int(self.volume * 200)), message],
                    check=True,
                    capture_output=True
                )
                
            elif self.tts_method == 'festival':
                # Festival requires input from stdin
                subprocess.run(
                    ['festival', '--tts'],
                    input=message.encode(),
                    check=True,
                    capture_output=True
                )
            
            else:
                raise Exception('No TTS method available')
            
            self._record_success()
            self.logger.info('Voice notification spoken successfully')
            
            return NotificationResult(
                success=True,
                status=NotificationStatus.SENT,
                provider='voice',
                timestamp=time.time(),
                message=f'Voice notification spoken using {self.tts_method}',
                metadata={'tts_method': self.tts_method, 'message': message}
            )
            
        except subprocess.CalledProcessError as e:
            self._record_failure()
            error_msg = f'TTS command failed: {e.stderr.decode() if e.stderr else str(e)}'
            self.logger.error(error_msg)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='voice',
                timestamp=time.time(),
                error=error_msg
            )
            
        except Exception as e:
            self._record_failure()
            error_msg = f'Failed to send voice notification: {e}'
            self.logger.error(error_msg, exc_info=True)
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider='voice',
                timestamp=time.time(),
                error=error_msg
            )
    
    def test_connection(self) -> bool:
        """
        Test TTS engine.
        
        Returns:
            True if TTS is working, False otherwise
        """
        try:
            # Create test message
            test_message = "Security system test"
            
            if self.tts_method == 'pyttsx3' and self.engine:
                self.engine.say(test_message)
                self.engine.runAndWait()
                return True
                
            elif self.tts_method == 'espeak':
                result = subprocess.run(
                    ['espeak', '-s', str(self.rate), test_message],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            elif self.tts_method == 'festival':
                result = subprocess.run(
                    ['festival', '--tts'],
                    input=test_message.encode(),
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            
            return False
            
        except Exception as e:
            self.logger.error(f'TTS test failed: {e}')
            return False
    
    def _create_voice_message(self, context: NotificationContext) -> str:
        """
        Create a voice message from context.
        
        Args:
            context: Notification context
            
        Returns:
            Voice message string
        """
        parts = []
        
        # Priority-based intro
        if context.priority.value in ['high', 'critical']:
            parts.append("Alert! Security alert!")
        else:
            parts.append("Security notification.")
        
        # Event type
        event_type = context.event_type.replace('_', ' ')
        parts.append(f"{event_type} detected")
        
        # Detected objects
        if context.detected_objects and len(context.detected_objects) > 0:
            if len(context.detected_objects) == 1:
                parts.append(f"{context.detected_objects[0]} detected")
            elif len(context.detected_objects) == 2:
                parts.append(f"{context.detected_objects[0]} and {context.detected_objects[1]} detected")
            else:
                parts.append(f"{context.detected_objects[0]}, {context.detected_objects[1]}, and {len(context.detected_objects) - 2} other objects detected")
        
        # Zone
        if context.zone_name:
            parts.append(f"in {context.zone_name}")
        
        # Threat level
        if context.threat_level and context.threat_level in ['high', 'critical']:
            parts.append(f"Threat level: {context.threat_level}")
        
        # Time
        time_str = time.strftime('%I %M %p', time.localtime(context.timestamp))
        parts.append(f"at {time_str}")
        
        return ". ".join(parts) + "."
    
    def generate_audio_file(self, context: NotificationContext, output_path: str) -> bool:
        """
        Generate an audio file of the notification.
        
        Args:
            context: Notification context
            output_path: Path to save audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            return False
        
        try:
            message = self._create_voice_message(context)
            
            if self.tts_method == 'pyttsx3' and self.engine:
                self.engine.save_to_file(message, output_path)
                self.engine.runAndWait()
                return True
                
            elif self.tts_method == 'espeak':
                subprocess.run(
                    ['espeak', '-s', str(self.rate), '-w', output_path, message],
                    check=True,
                    capture_output=True
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f'Failed to generate audio file: {e}')
            return False
    
    def _check_command_available(self, command: str) -> bool:
        """
        Check if a command is available on the system.
        
        Args:
            command: Command name to check
            
        Returns:
            True if command is available, False otherwise
        """
        try:
            subprocess.run(
                ['which', command],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def list_available_voices(self) -> list:
        """
        List available voices for the TTS engine.
        
        Returns:
            List of voice names/IDs
        """
        if self.tts_method == 'pyttsx3' and self.engine:
            try:
                voices = self.engine.getProperty('voices')
                return [{'id': v.id, 'name': v.name, 'languages': v.languages} for v in voices]
            except Exception:
                return []
        
        return []
    
    def shutdown(self) -> None:
        """Shutdown the voice service."""
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        super().shutdown()

