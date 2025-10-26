"""
USB Audio Configuration for HAL Voice System
Configures ALSA to use USB audio devices for playback and recording.
"""
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class USBAudioConfig:
    """Configuration manager for USB audio devices."""
    
    def __init__(self):
        self.usb_speaker_card = None
        self.usb_mic_card = None
        self.usb_speaker_device = None
        self.usb_mic_device = None
        
    def detect_usb_audio_devices(self):
        """
        Detect USB audio devices and return card numbers.
        
        Returns:
            tuple: (speaker_card, mic_card) or (None, None) if not found
        """
        try:
            # Get speaker playback devices
            result = subprocess.run(
                ['aplay', '-l'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get mic recording devices
            mic_result = subprocess.run(
                ['arecord', '-l'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse for USB devices
            for line in result.stdout.split('\n'):
                if 'USB' in line or 'Audio' in line:
                    # Extract card number
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'card' and i + 1 < len(parts):
                            card_num = parts[i + 1].strip(':')
                            device_parts = parts[i + 3].split(',')
                            device_num = device_parts[0]
                            self.usb_speaker_card = card_num
                            self.usb_speaker_device = device_num
                            logger.info(f"Found USB speaker: card {card_num}, device {device_num}")
                            break
            
            for line in mic_result.stdout.split('\n'):
                if 'USB' in line or 'Audio' in line:
                    # Extract card number
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'card' and i + 1 < len(parts):
                            card_num = parts[i + 1].strip(':')
                            device_parts = parts[i + 3].split(',')
                            device_num = device_parts[0]
                            self.usb_mic_card = card_num
                            self.usb_mic_device = device_num
                            logger.info(f"Found USB mic: card {card_num}, device {device_num}")
                            break
            
            return (self.usb_speaker_card, self.usb_mic_card)
            
        except Exception as e:
            logger.error(f"Failed to detect USB audio devices: {e}")
            return (None, None)
    
    def test_usb_speaker(self, card, device):
        """
        Test USB speaker playback.
        
        Args:
            card: Audio card number
            device: Device number
            
        Returns:
            bool: True if test successful
        """
        try:
            # Use default ALSA device
            logger.info(f"Testing USB speaker: card {card}, device {device}")
            
            # Try to play a test tone
            result = subprocess.run(
                ['speaker-test', '-t', 'wav', '-c', '2', '-l', '1'],
                timeout=5,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("USB speaker test successful")
                return True
            else:
                logger.warning(f"USB speaker test failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"USB speaker test error: {e}")
            return False
    
    def configure_alsa_for_usb(self, speaker_card, mic_card):
        """
        Configure ALSA to prefer USB devices.
        
        This creates an .asoundrc configuration file.
        
        Args:
            speaker_card: USB speaker card number
            mic_card: USB mic card number
        """
        asoundrc_path = Path.home() / ".asoundrc"
        
        config = f"""pcm.!default {{
    type hw
    card {speaker_card}
    device 0
}}

ctl.!default {{
    type hw
    card {speaker_card}
}}

# USB microphone configuration
pcm.usbmic {{
    type hw
    card {mic_card}
    device 0
}}

ctl.usbmic {{
    type hw
    card {mic_card}
}}
"""
        
        try:
            with open(asoundrc_path, 'w') as f:
                f.write(config)
            
            logger.info(f"Created ALSA config at {asoundrc_path}")
            logger.info(f"USB speaker configured on card {speaker_card}")
            logger.info(f"USB mic configured on card {mic_card}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ALSA config: {e}")
            return False
    
    def play_test_audio(self, audio_file):
        """
        Play an audio file using USB speaker.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            bool: True if playback successful
        """
        try:
            # Use mpg123 for MP3 files (best compatibility)
            result = subprocess.run(
                ['mpg123', '-q', str(audio_file)],
                timeout=10,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully played audio: {audio_file}")
                return True
            else:
                logger.warning(f"Failed to play audio: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False


def main():
    """CLI interface for USB audio configuration."""
    logging.basicConfig(level=logging.INFO)
    
    config = USBAudioConfig()
    
    print("🔊 USB Audio Configuration")
    print("=" * 60)
    
    # Detect devices
    print("\n1. Detecting USB audio devices...")
    speaker_card, mic_card = config.detect_usb_audio_devices()
    
    if speaker_card is None and mic_card is None:
        print("❌ No USB audio devices detected")
        return False
    
    if speaker_card:
        print(f"✅ Found USB speaker: card {speaker_card}")
    
    if mic_card:
        print(f"✅ Found USB mic: card {mic_card}")
    
    # Configure ALSA
    if speaker_card:
        print(f"\n2. Configuring ALSA for USB speaker (card {speaker_card})...")
        config.configure_alsa_for_usb(speaker_card or 0, mic_card or 0)
        print("✅ ALSA configuration created at ~/.asoundrc")
    
    # Test playback
    if speaker_card:
        print("\n3. Testing USB speaker...")
        print("   Playing test audio...")
        # Test with HAL voice
        hal_audio = Path(__file__).parent.parent / "voice" / "hal_audio" / "system_startup.mp3"
        if hal_audio.exists():
            success = config.play_test_audio(hal_audio)
            if success:
                print("✅ USB speaker working!")
            else:
                print("⚠️  USB speaker test failed")
        else:
            print("⚠️  No HAL audio file found for testing")
    
    print("\n" + "=" * 60)
    print("✅ Configuration complete!")
    print("\nTo use USB audio, HAL voice will automatically detect it.")
    print("Restart your YOLO detection system to use USB audio.")
    
    return True


if __name__ == "__main__":
    main()



