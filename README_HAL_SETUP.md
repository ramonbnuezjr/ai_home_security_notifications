# HAL 9000 Voice Layer Setup Guide

## Overview

The HAL 9000 Voice Layer provides synthesized speech for the AI Home Security System using Google Cloud Text-to-Speech with specific voice characteristics to emulate HAL 9000 from *2001: A Space Odyssey*. This system replaces espeak with high-quality, locally-cached voice phrases while maintaining graceful fallback capabilities.

### Key Features

- **Premium Voice Quality**: Google Cloud Neural2 voices with custom prosody
- **HAL 9000 Characteristics**: Deep pitch (-10dB), slow cadence (0.90 rate), measured tone
- **Local Caching**: ~50 common security phrases pre-synthesized and stored locally
- **Fast Playback**: Cached phrases play instantly without API latency
- **Graceful Fallback**: Automatic fallback to espeak if Google TTS unavailable
- **Custom Synthesis**: Dynamic synthesis for arbitrary text (TinyLama responses)
- **Privacy-Focused**: Audio files stored locally on Pi's SSD

## Prerequisites

### 1. Google Cloud Project Setup

You'll need a Google Cloud project with Text-to-Speech API enabled:

1. **Create Google Cloud Project** (if you don't have one):
   ```bash
   # Visit: https://console.cloud.google.com/
   # Click "Create Project"
   # Note your project ID
   ```

2. **Enable Text-to-Speech API**:
   ```bash
   # Visit: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com
   # Click "Enable"
   ```

3. **Create Service Account and Download Credentials**:
   ```bash
   # Visit: https://console.cloud.google.com/iam-admin/serviceaccounts
   # Click "Create Service Account"
   # Name: "hal-tts-service"
   # Grant role: "Cloud Text-to-Speech User"
   # Click "Create Key" -> JSON
   # Download the JSON file to your Pi
   ```

4. **Set Environment Variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"

   # Add to ~/.bashrc for persistence:
   echo 'export GOOGLE_APPLICATION_CREDENTIALS="/home/ramon/security_config/google-tts-key.json"' >> ~/.bashrc
   source ~/.bashrc
   ```

### 2. System Dependencies

Install required system packages on Raspberry Pi:

```bash
# Audio playback utilities
sudo apt-get update
sudo apt-get install -y alsa-utils

# Espeak fallback (if not already installed)
sudo apt-get install -y espeak

# Test audio output
aplay /usr/share/sounds/alsa/Front_Center.wav
```

### 3. Python Dependencies

Install Python packages for Google Cloud TTS:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install TTS dependencies
pip install -r requirements_tts.txt
```

## Installation

### Step 1: Verify Google Cloud Credentials

```bash
# Test that credentials are working
python -c "from google.cloud import texttospeech; print('✓ Google TTS available')"

# If you see errors, check:
# - GOOGLE_APPLICATION_CREDENTIALS environment variable is set
# - JSON key file exists and has correct permissions
# - Text-to-Speech API is enabled in your project
```

### Step 2: Generate Voice Library

Generate the complete library of cached HAL phrases:

```bash
# Generate all phrases (first time setup)
python scripts/generate_hal_voice_library.py --project-id=YOUR_PROJECT_ID

# Or with environment variable:
export GOOGLE_CLOUD_PROJECT=your-project-id
python scripts/generate_hal_voice_library.py
```

**Expected Output**:
```
INFO: Loading phrases from: src/voice/hal_phrases.yaml
INFO: Loaded 52 phrases from 7 categories
INFO: Starting synthesis of 52 phrases...
...
INFO: ✓ Voice library ready: 52/52 phrases available
INFO: Total size: 4.8 MB
```

**Options**:
```bash
# Force re-synthesis of all phrases (e.g., to change voice settings)
python scripts/generate_hal_voice_library.py --force

# Synthesize only detection phrases
python scripts/generate_hal_voice_library.py --phrases="detection:*"

# Synthesize a specific phrase
python scripts/generate_hal_voice_library.py --phrases="system:startup"

# Use a different voice
python scripts/generate_hal_voice_library.py --voice="en-US-Neural2-C"
```

### Step 3: Verify Installation

Test HAL voice playback:

```python
# Create a test script: test_hal_voice.py
from src.services.google_tts_hal_service import GoogleHALVoiceService

# Initialize HAL service
hal = GoogleHALVoiceService(project_id="your-project-id")

# Test cached phrase
hal.speak("system_startup")

# Test custom synthesis
hal.speak_custom("I'm sorry Dave, I'm afraid I can't do that")

# List available phrases
phrases = hal.list_available_phrases()
print(f"Available phrases: {len(phrases)}")
```

Run the test:
```bash
python test_hal_voice.py
```

## Integration with Notification System

### Current Integration Point

The HAL voice service integrates with your existing notification system:

**File**: `src/services/notification_manager.py` (or wherever voice notifications are triggered)

### Example Integration

Replace espeak calls with HAL service:

```python
from src.services.google_tts_hal_service import GoogleHALVoiceService

class NotificationManager:
    def __init__(self):
        # Initialize HAL voice service
        self.hal = GoogleHALVoiceService(
            project_id=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            cache_dir="src/voice/hal_audio"
        )

    def send_voice_alert(self, event_type: str, details: str = None):
        """Send voice notification with HAL voice."""

        # Map event types to HAL phrase IDs
        phrase_map = {
            'motion_detected': 'detection_motion_detected',
            'person_detected': 'detection_person_identified',
            'threat_high': 'detection_threat_level_high',
            'all_clear': 'clearance_all_clear',
        }

        phrase_id = phrase_map.get(event_type)

        if phrase_id:
            # Use cached phrase (fast)
            self.hal.speak(phrase_id, blocking=False)
        elif details:
            # Use custom synthesis (for TinyLama responses)
            self.hal.speak_custom(details, blocking=False)
        else:
            # Fallback to espeak
            subprocess.run(['espeak', event_type])
```

### Integration Best Practices

1. **Use Cached Phrases for Common Events**:
   - Motion detected, person identified, system status
   - Instant playback, no API latency

2. **Use Custom Synthesis for Dynamic Content**:
   - TinyLama-generated descriptions
   - User-specific messages
   - Novel event descriptions

3. **Non-blocking Playback**:
   - Use `blocking=False` for notifications to avoid delays
   - System continues processing while HAL speaks

4. **Error Handling**:
   - Service automatically falls back to espeak on failures
   - Log errors for debugging but don't crash

## Usage Examples

### Example 1: Security Event Notifications

```python
hal = GoogleHALVoiceService(project_id="your-project-id")

# Motion detected
hal.speak("detection_motion_detected")

# Person identified
hal.speak("detection_person_identified")

# System armed
hal.speak("system_armed")
```

### Example 2: Dynamic Status Updates

```python
# Get description from TinyLama
llm_description = "A delivery person approached the front door and left a package"

# Speak the custom description
hal.speak_custom(llm_description, blocking=False)
```

### Example 3: System Startup Sequence

```python
# System initialization
hal.speak("system_startup")  # "I'm fully operational..."

# Camera check
hal.speak("inquiries_camera_check")

# Ready
hal.speak("clearance_all_clear")
```

### Example 4: Batch Operations

```python
# List all available phrases
phrases = hal.list_available_phrases()
print(f"Available: {phrases}")

# Verify cache integrity
verification = hal.verify_cache()
print(f"Valid files: {verification['valid']}/{verification['total']}")

# Re-synthesize missing files
if verification['missing']:
    # Run generation script for missing phrases
    subprocess.run([
        'python', 'scripts/generate_hal_voice_library.py',
        '--phrases=' + ','.join(verification['missing'])
    ])
```

## Testing

### Test Scripts

**Test 1: Basic Functionality**
```bash
python -c "
from src.services.google_tts_hal_service import GoogleHALVoiceService
hal = GoogleHALVoiceService(project_id='your-project-id')
hal.speak('system_startup')
"
```

**Test 2: Custom Synthesis**
```bash
python -c "
from src.services.google_tts_hal_service import GoogleHALVoiceService
hal = GoogleHALVoiceService(project_id='your-project-id')
hal.speak_custom('All systems nominal')
"
```

**Test 3: Fallback Behavior**
```bash
# Test espeak fallback (disable Google credentials temporarily)
unset GOOGLE_APPLICATION_CREDENTIALS
python -c "
from src.services.google_tts_hal_service import GoogleHALVoiceService
hal = GoogleHALVoiceService(project_id='dummy')
hal.speak('system_online')  # Should fall back to espeak
"
```

### Manual Testing Commands

```bash
# Play a specific cached phrase directly
aplay src/voice/hal_audio/system_startup.mp3

# Check synthesis log
tail -f src/voice/hal_audio/synthesis.log

# Verify all cached files exist
python -c "
from src.services.google_tts_hal_service import GoogleHALVoiceService
hal = GoogleHALVoiceService(project_id='your-project-id')
result = hal.verify_cache()
print(result)
"
```

## Troubleshooting

### Issue: "google.cloud.texttospeech not found"

**Solution**:
```bash
pip install google-cloud-texttospeech
# Or reinstall requirements
pip install -r requirements_tts.txt
```

### Issue: "Authentication error" or "Permission denied"

**Causes**:
- GOOGLE_APPLICATION_CREDENTIALS not set
- JSON key file doesn't exist or has wrong permissions
- Service account lacks Text-to-Speech API permissions

**Solutions**:
```bash
# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verify file exists
ls -la /path/to/your-service-account-key.json

# Set permissions
chmod 600 /path/to/your-service-account-key.json

# Verify API is enabled
gcloud services list --enabled | grep texttospeech
```

### Issue: "Audio device not found"

**Solution**:
```bash
# List available audio devices
aplay -L

# Test default device
aplay /usr/share/sounds/alsa/Front_Center.wav

# Configure specific device in HAL service
hal = GoogleHALVoiceService(audio_device="plughw:CARD=Device,DEV=0")
```

### Issue: "espeak fallback not working"

**Solution**:
```bash
# Install espeak
sudo apt-get install espeak

# Test espeak
espeak "Testing espeak"
```

### Issue: "Synthesis succeeds but no audio plays"

**Causes**:
- SSH session (audio won't play over SSH)
- Audio device muted or disconnected
- aplay not installed

**Solutions**:
```bash
# Check if running over SSH
who am i

# Connect to Pi directly (HDMI + keyboard, or VNC)
# Ensure speakers/headphones connected to Pi

# Unmute audio
amixer set Master unmute
amixer set Master 100%

# Install aplay if missing
sudo apt-get install alsa-utils
```

### Issue: "Cached phrases missing after git clone"

**Cause**: Audio files are not committed to git (only .gitkeep is)

**Solution**:
```bash
# Re-generate voice library after cloning
python scripts/generate_hal_voice_library.py
```

### Issue: "High API costs"

**Optimization**:
- Use cached phrases for 95%+ of notifications
- Only use custom synthesis for truly dynamic content
- Set reasonable limits on custom synthesis in production
- Monitor usage in Google Cloud Console

**Cost Estimate**:
- Initial library generation: ~52 phrases × $0.000016/char ≈ $0.05
- Custom synthesis (occasional): $0.000016 per character
- Monthly cost (moderate use): < $1.00

## File Structure

```
ai_home_security_notifications/
├── src/
│   ├── services/
│   │   └── google_tts_hal_service.py    # HAL voice service class
│   └── voice/
│       ├── hal_phrases.yaml             # Phrase definitions
│       └── hal_audio/                   # Cached audio files
│           ├── .gitkeep                 # Git placeholder
│           ├── index.json               # Phrase index (auto-generated)
│           ├── synthesis.log            # Synthesis log
│           ├── system_startup.mp3       # Cached phrases...
│           ├── detection_motion_detected.mp3
│           └── ...
├── scripts/
│   └── generate_hal_voice_library.py    # Library generation script
├── requirements_tts.txt                 # TTS dependencies
└── README_HAL_SETUP.md                  # This file
```

## Voice Customization

### Changing Voice Characteristics

Edit `src/services/google_tts_hal_service.py`:

```python
# Default HAL settings
self.hal_pitch = "-10.0dB"  # Range: -20.0dB to +20.0dB
self.hal_rate = "0.90"       # Range: 0.25 to 4.0

# For deeper voice:
self.hal_pitch = "-15.0dB"

# For slower cadence:
self.hal_rate = "0.80"
```

After changing settings, re-generate library:
```bash
python scripts/generate_hal_voice_library.py --force
```

### Trying Different Voices

Available Neural2 voices (high quality):
- `en-US-Neural2-A`: Male, young
- `en-US-Neural2-C`: Female, young
- **`en-US-Neural2-D`: Male, deep (default)** ← Recommended for HAL
- `en-US-Neural2-F`: Female, older
- `en-US-Neural2-I`: Male, older

Test a different voice:
```bash
python scripts/generate_hal_voice_library.py --voice="en-US-Neural2-I" --phrases="system:startup"
```

[View all available voices](https://cloud.google.com/text-to-speech/docs/voices)

### Adding Custom Phrases

Edit `src/voice/hal_phrases.yaml`:

```yaml
hal_phrases:
  custom:
    welcome_home: "Welcome home. All systems secured during your absence"
    goodnight: "Goodnight. I'll maintain vigilance through the night"
    test_phrase: "This is a test of the HAL voice system"
```

Generate the new phrases:
```bash
python scripts/generate_hal_voice_library.py --phrases="custom:*"
```

## Performance Notes

### Latency

- **Cached phrases**: < 100ms (instant playback)
- **Custom synthesis**: 500-2000ms (Google API call + synthesis)
- **espeak fallback**: < 200ms

### Storage

- Each phrase: ~80-120 KB (MP3, ~3-5 seconds)
- Full library (52 phrases): ~4-5 MB
- Custom synthesis cache: Grows over time, monitor disk usage

### Network

- Library generation: ~1-2 MB download (one-time)
- Custom synthesis: ~50-100 KB per request
- No network needed for cached phrase playback

## Security Considerations

1. **Protect Service Account Key**:
   ```bash
   chmod 600 /path/to/service-account-key.json
   # Never commit this file to git!
   ```

2. **Add to .gitignore**:
   ```
   # Google Cloud credentials
   *-service-account-key.json
   google-credentials.json
   ```

3. **Limit API Access**:
   - Use service account with minimal permissions
   - Enable only Text-to-Speech API
   - Monitor usage in Google Cloud Console

4. **Local Storage**:
   - Audio files stored on SSD (not in git)
   - No sensitive data in voice phrases
   - Clear cache if needed: `rm -rf src/voice/hal_audio/*.mp3`

## Next Steps

After completing setup:

1. **Integrate with notification system** - Replace espeak calls
2. **Test end-to-end** - Trigger real security events
3. **Monitor API usage** - Check Google Cloud Console
4. **Customize phrases** - Add project-specific messages
5. **Consider voice customization** - Try different voices or prosody settings

## Support

- **Google Cloud TTS Docs**: https://cloud.google.com/text-to-speech/docs
- **Voice samples**: https://cloud.google.com/text-to-speech/docs/voices
- **Pricing**: https://cloud.google.com/text-to-speech/pricing
- **SSML Guide**: https://cloud.google.com/text-to-speech/docs/ssml

---

**"I'm sorry Dave, I'm afraid I can't do that."** — HAL 9000
