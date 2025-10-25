"""HAL 9000 voice notification service wrapper."""

import subprocess
from pathlib import Path
from typing import Optional

from .base_notification_service import (
    BaseNotificationService,
    NotificationContext,
    NotificationResult,
    NotificationStatus
)
from ..utils.config import Config


class HALNotificationService(BaseNotificationService):
    """
    HAL 9000 voice notification service.
    
    Uses pre-generated HAL voice audio files for security notifications.
    Plays MP3 files using mpg123 for clear audio playback.
    """
    
    SERVICE_NAME = 'hal_voice'
    
    def __init__(self, config: Config):
        """Initialize HAL voice notification service."""
        super().__init__(config, self.SERVICE_NAME)
        
        # HAL audio directory
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.hal_audio_dir = self.project_root / "src/voice/hal_audio"
        
        # Audio player (mpg123 works best for MP3)
        self.audio_player = 'mpg123'
        
        # Phrase mapping (event types to HAL phrase files)
        self.phrase_map = {
            'motion_detected': 'detection_motion_detected',
            'person_detected': 'detection_person_identified',
            'multiple_persons': 'detection_multiple_persons',
            'object_detected': 'detection_object_detected',
            'vehicle_detected': 'detection_vehicle_detected',
            'animal_detected': 'detection_animal_detected',
            'package_detected': 'detection_package_detected',
            'loitering_detected': 'detection_loitering_detected',
            'threat_high': 'detection_threat_level_high',
            'threat_medium': 'detection_threat_level_medium',
            'threat_low': 'detection_threat_level_low',
            'all_clear': 'clearance_all_clear',
            'motion_cleared': 'clearance_motion_cleared',
            'threat_cleared': 'clearance_threat_cleared',
            'zone_clear': 'clearance_zone_clear',
            'false_alarm': 'clearance_false_alarm',
            'system_startup': 'system_startup',
            'system_armed': 'system_armed',
            'system_disarmed': 'system_disarmed',
            'immediate_attention': 'alerts_immediate_attention',
        }
    
    def _check_audio_player(self) -> bool:
        """Check if mpg123 is available."""
        try:
            subprocess.run(['which', self.audio_player], 
                         capture_output=True, 
                         check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning(f"{self.audio_player} not found")
            return False
    
    def _check_hal_audio_files(self) -> bool:
        """Check if HAL audio files exist."""
        if not self.hal_audio_dir.exists():
            self.logger.warning(f"HAL audio directory not found: {self.hal_audio_dir}")
            return False
        
        audio_files = list(self.hal_audio_dir.glob("*.mp3"))
        if len(audio_files) == 0:
            self.logger.warning("No HAL audio files found")
            return False
        
        self.logger.info(f"Found {len(audio_files)} HAL voice phrases")
        return True
    
    def initialize(self) -> bool:
        """Initialize the HAL voice service."""
        # Check if voice notifications are enabled
        voice_config = self.config.get('notifications', {}).get('voice', {})
        if not voice_config.get('enabled', False):
            self.logger.info('Voice notifications disabled in config')
            return False
        
        # Check audio player
        if not self._check_audio_player():
            self.logger.error(f"{self.audio_player} not found. Install with: sudo apt-get install mpg123")
            return False
        
        # Check HAL audio files
        if not self._check_hal_audio_files():
            self.logger.warning("HAL audio files not found. Generate with: python scripts/generate_hal_voice_library_standalone.py")
            # Don't fail initialization - we can still work
        
        self.logger.info("HAL voice notification service initialized")
        return True
    
    def _select_phrase(self, context: NotificationContext) -> Optional[Path]:
        """
        Select appropriate HAL phrase based on notification context.
        
        Args:
            context: Notification context
            
        Returns:
            Path to audio file, or None if not found
        """
        # Try to map event type to phrase
        phrase_id = self.phrase_map.get(context.event_type)
        
        # If no direct mapping, try based on detected objects
        if not phrase_id and context.detected_objects:
            if 'person' in context.detected_objects:
                phrase_id = 'detection_person_identified'
            elif 'car' in context.detected_objects or 'truck' in context.detected_objects:
                phrase_id = 'detection_vehicle_detected'
            elif 'dog' in context.detected_objects or 'cat' in context.detected_objects:
                phrase_id = 'detection_animal_detected'
            else:
                phrase_id = 'detection_object_detected'
        
        # Default to motion detected
        if not phrase_id:
            phrase_id = 'detection_motion_detected'
        
        # Find audio file
        audio_file = self.hal_audio_dir / f"{phrase_id}.mp3"
        if audio_file.exists():
            return audio_file
        else:
            self.logger.warning(f"HAL audio file not found: {audio_file}")
            return None
    
    def _play_audio(self, audio_file: Path) -> bool:
        """
        Play audio file using mpg123.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            True if playback succeeded, False otherwise
        """
        try:
            result = subprocess.run(
                [self.audio_player, '-q', str(audio_file)],
                capture_output=True,
                timeout=15
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.logger.error("Audio playback timed out")
            return False
        except Exception as e:
            self.logger.error(f"Audio playback failed: {e}")
            return False
    
    def send_notification(self, context: NotificationContext) -> NotificationResult:
        """
        Send HAL voice notification.
        
        Args:
            context: Notification context
            
        Returns:
            NotificationResult with success/failure status
        """
        self.logger.info(f"Sending HAL voice notification for: {context.event_type}")
        
        # Select appropriate phrase
        audio_file = self._select_phrase(context)
        
        if not audio_file:
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider=self.SERVICE_NAME,
                message="No matching HAL phrase found",
                timestamp=context.timestamp
            )
        
        self.logger.info(f"Playing HAL phrase: {audio_file.stem}")
        
        # Play audio
        success = self._play_audio(audio_file)
        
        if success:
            return NotificationResult(
                success=True,
                status=NotificationStatus.SENT,
                provider=self.SERVICE_NAME,
                message=f"HAL voice notification played: {audio_file.stem}",
                timestamp=context.timestamp
            )
        else:
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider=self.SERVICE_NAME,
                message="Audio playback failed",
                timestamp=context.timestamp
            )
    
    def test_connection(self) -> bool:
        """
        Test if HAL voice system is working.
        
        Returns:
            True if audio files exist and player is available
        """
        return self._check_audio_player() and self._check_hal_audio_files()
    
    def test_notification(self) -> NotificationResult:
        """Test HAL voice notification."""
        # Play system startup phrase
        audio_file = self.hal_audio_dir / "system_startup.mp3"
        
        if not audio_file.exists():
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider=self.SERVICE_NAME,
                message="HAL audio file not found",
                timestamp=0
            )
        
        self.logger.info("Testing HAL voice: system_startup")
        success = self._play_audio(audio_file)
        
        if success:
            return NotificationResult(
                success=True,
                status=NotificationStatus.SENT,
                provider=self.SERVICE_NAME,
                message="HAL test notification: System online. I'm fully operational",
                timestamp=0
            )
        else:
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                provider=self.SERVICE_NAME,
                message="HAL test notification failed",
                timestamp=0
            )

