# Notification System Documentation

## Overview

The AI Home Security Notifications system provides multi-channel alerting for security events. When motion is detected and objects are classified, the system can notify you through:

- 📧 **Email** - Detailed HTML emails with images
- 📱 **SMS** - Text messages via Twilio
- 🔔 **Push Notifications** - Mobile notifications via Firebase
- 🔊 **Voice Alerts** - Spoken alerts using text-to-speech

## Architecture

```
┌─────────────────────┐
│  Motion Detection   │
│  + Object           │
│    Classification   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Notification        │
│ Manager             │
│ - Throttling        │
│ - Queue Management  │
│ - Priority Routing  │
└──────────┬──────────┘
           │
     ┌─────┴─────┬─────────┬─────────┐
     ▼           ▼         ▼         ▼
┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐
│ Email  │  │  SMS   │ │  Push  │ │ Voice  │
│Service │  │Service │ │Service │ │Service │
└────────┘  └────────┘ └────────┘ └────────┘
```

## Configuration

### Email Configuration

Edit `config/system_config.yaml`:

```yaml
notifications:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "your_email@gmail.com"
    smtp_password: "your_app_password"  # Use app-specific password
    from_address: "security@yourdomain.com"
    to_addresses:
      - "user1@example.com"
      - "user2@example.com"
    subject_template: "Security Alert: {event_type} detected"
```

#### Gmail Setup

1. Enable 2-factor authentication on your Google account
2. Generate an app-specific password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the generated password
3. Use this app password in the configuration

### SMS Configuration (Twilio)

```yaml
notifications:
  sms:
    enabled: true
    provider: "twilio"
    twilio:
      account_sid: "your_account_sid"
      auth_token: "your_auth_token"
      from_number: "+1234567890"
      to_numbers:
        - "+1234567890"
        - "+0987654321"
```

#### Twilio Setup

1. Create a Twilio account at https://www.twilio.com
2. Get a phone number (Trial accounts get one free number)
3. Find your Account SID and Auth Token in the console
4. Add recipient phone numbers (trial accounts can only send to verified numbers)

### Push Notification Configuration (Firebase)

```yaml
notifications:
  push:
    enabled: true
    provider: "firebase"
    firebase:
      credentials_path: "/path/to/firebase-credentials.json"
      device_tokens:
        - "device_token_1"
        - "device_token_2"
```

#### Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Cloud Messaging (FCM)
3. Download the service account credentials:
   - Project Settings → Service Accounts
   - Generate new private key
   - Save as `firebase-credentials.json`
4. Get device tokens from your mobile app

### Voice Notification Configuration

```yaml
notifications:
  voice:
    enabled: true
    text_to_speech: true
    voice_settings:
      rate: 150        # Words per minute
      volume: 0.8      # 0.0 to 1.0
      voice: "en-US-Standard-C"
```

#### Voice Setup

The system supports multiple TTS engines:

1. **pyttsx3** (Recommended, cross-platform)
   ```bash
   pip install pyttsx3
   ```

2. **espeak** (Linux)
   ```bash
   sudo apt-get install espeak
   ```

3. **festival** (Linux)
   ```bash
   sudo apt-get install festival
   ```

### Throttling Configuration

```yaml
notifications:
  enabled: true
  cooldown_period: 300           # 5 minutes between notifications
  max_notifications_per_hour: 10 # Maximum 10 per hour
```

## Usage

### Basic Usage

```python
from src.services.notification_manager import NotificationManager
from src.services.base_notification_service import NotificationContext, NotificationPriority
from src.utils.config import Config

# Initialize
config = Config()
manager = NotificationManager(config)
manager.start()

# Create notification context
context = NotificationContext(
    event_type='motion_detected',
    timestamp=time.time(),
    priority=NotificationPriority.HIGH,
    detected_objects=['person', 'car'],
    motion_percentage=15.5,
    threat_level='high',
    zone_name='Front Door',
    image_path='/path/to/snapshot.jpg'
)

# Send notification (async)
results = manager.send_notification(context)

# Or send synchronously
results = manager.send_notification(context, async_mode=False)

# Send to specific services only
results = manager.send_notification(context, services=['email', 'sms'])
```

### Integration with Motion Detection

```python
from src.services.camera_service import CameraService
from src.services.motion_detection_service import MotionDetectionService
from src.services.object_detection_service import ObjectDetectionService
from src.services.notification_manager import NotificationManager

# Initialize services
camera = CameraService(config)
motion_detector = MotionDetectionService(config)
object_detector = ObjectDetectionService(config)
notifier = NotificationManager(config)

camera.start()
notifier.start()

# Main loop
while True:
    # Capture frame
    frame = camera.get_frame()
    
    # Detect motion
    motion_event = motion_detector.detect_motion(frame)
    
    if motion_event:
        # Classify objects
        detection_result = object_detector.detect_objects(frame)
        motion_event.detected_objects = detection_result
        
        # Create notification
        context = NotificationContext(
            event_type='motion_and_objects',
            timestamp=motion_event.timestamp,
            priority=NotificationPriority.MEDIUM,
            detected_objects=[obj.label for obj in detection_result.objects],
            motion_percentage=motion_event.motion_percentage,
            zone_name='Front Door'
        )
        
        # Send notification
        notifier.send_notification(context)
```

### Priority Levels

```python
NotificationPriority.LOW       # Regular events, can be throttled
NotificationPriority.MEDIUM    # Important events
NotificationPriority.HIGH      # Security concerns
NotificationPriority.CRITICAL  # Emergency, overrides throttling
```

### Testing

#### Test All Services

```bash
cd /home/ramon/ai_projects/ai_home_security_notifications
source venv/bin/activate
python scripts/test_notifications.py
```

#### Test Email Only

```bash
python scripts/test_email_notification.py
```

#### Test Individual Service

```python
from src.services.email_notification_service import EmailNotificationService
from src.utils.config import Config

config = Config()
service = EmailNotificationService(config)
service.initialize()

# Test connection
if service.test_connection():
    print("Email service is working!")
```

## Notification Content

### Email Notifications

Emails include:
- HTML formatted message with colored priority indicators
- Event type, timestamp, zone
- Detected objects list
- Motion percentage
- Threat level
- Embedded image (if available)
- Responsive design for mobile viewing

### SMS Notifications

SMS messages are concise (160 char target):
```
🚨 Security Alert
Detected: person, car
Zone: Front Door
Time: 14:30
```

### Push Notifications

Push notifications include:
- Title with event summary
- Body with key details
- Custom data payload for app handling
- Image attachment (if URL provided)
- Priority-based delivery (high/normal)

### Voice Notifications

Voice alerts speak:
```
"Alert! Security alert! Motion detected. Person detected in front door at 2:30 PM."
```

## Advanced Features

### Custom Notification Templates

```python
context = NotificationContext(
    event_type='custom_alert',
    timestamp=time.time(),
    priority=NotificationPriority.HIGH,
    subject='🚨 Custom Alert Title',
    message='Custom message body with details...',
    metadata={'custom_field': 'value'}
)
```

### Notification Statistics

```python
# Get overall statistics
stats = manager.get_statistics()

print(f"Services: {stats['services']}")
print(f"History: {stats['history']}")
print(f"Queue size: {stats['queue_size']}")
print(f"Throttling: {stats['throttling']}")

# Get service-specific statistics
for service_name, service in manager.services.items():
    service_stats = service.get_statistics()
    print(f"{service_name}: {service_stats['sent_count']} sent, "
          f"{service_stats['success_rate']:.1%} success rate")
```

### Reset Throttling

```python
# Reset throttling counters
manager.reset_throttling()
```

### Update Settings Dynamically

```python
# Update throttling settings at runtime
manager.update_settings(
    cooldown_period=180,  # 3 minutes
    max_per_hour=20       # 20 per hour
)
```

### Force Send (Override Throttling)

```python
# Send notification even if throttled
results = manager.send_notification(context, force=True)
```

## Troubleshooting

### Email Issues

**Problem:** Authentication failed
- **Solution:** Use app-specific password for Gmail, not your regular password
- Enable "Less secure app access" if not using 2FA

**Problem:** Connection timeout
- **Solution:** Check firewall, ensure port 587 is open
- Try port 465 with SSL instead of 587 with TLS

**Problem:** Emails go to spam
- **Solution:** 
  - Configure SPF/DKIM records for your domain
  - Use a verified from_address
  - Avoid spam trigger words in subject

### SMS Issues

**Problem:** Invalid phone number
- **Solution:** Use E.164 format: +[country code][number]
- Example: +14155552671

**Problem:** Twilio authentication error
- **Solution:** 
  - Verify Account SID and Auth Token are correct
  - Check they're not expired or revoked

**Problem:** Message not delivered
- **Solution:**
  - For trial accounts, verify recipient numbers in Twilio console
  - Check account balance
  - Verify from_number is a valid Twilio number

### Push Notification Issues

**Problem:** Firebase initialization failed
- **Solution:**
  - Verify credentials JSON file path is correct
  - Check file permissions
  - Ensure service account has correct roles

**Problem:** Device not receiving notifications
- **Solution:**
  - Verify device token is current (they can expire)
  - Check device has internet connection
  - Ensure app has notification permissions

### Voice Notification Issues

**Problem:** No TTS engine available
- **Solution:** Install at least one TTS engine:
  ```bash
  pip install pyttsx3
  # or
  sudo apt-get install espeak
  ```

**Problem:** Voice sounds robotic
- **Solution:** 
  - Try different voices (list with `service.list_available_voices()`)
  - Adjust rate and volume in config

**Problem:** No audio output
- **Solution:**
  - Check audio is not muted
  - Verify audio device is configured correctly
  - For headless systems, may need virtual audio device

### General Issues

**Problem:** Notifications not sending
- **Solution:**
  1. Check service is enabled in config
  2. Verify credentials are correct
  3. Test individual service with test scripts
  4. Check logs for errors

**Problem:** Notifications throttled too aggressively
- **Solution:** Adjust throttling settings:
  ```yaml
  notifications:
    cooldown_period: 60      # Reduce cooldown
    max_notifications_per_hour: 20  # Increase limit
  ```

**Problem:** Too many notifications
- **Solution:**
  - Increase motion detection thresholds
  - Adjust sensitivity settings
  - Configure motion zones to ignore less important areas
  - Increase cooldown_period

## Performance Considerations

### Email
- **Latency:** 1-5 seconds per email
- **Bandwidth:** ~50-500 KB per email (with image)
- **Rate limits:** Most SMTP servers limit to 100-500 emails/day

### SMS
- **Latency:** 1-3 seconds
- **Cost:** ~$0.0075 per SMS (Twilio pricing)
- **Rate limits:** Twilio has messaging limits based on account type

### Push
- **Latency:** < 1 second
- **Bandwidth:** Minimal (~1-2 KB per notification)
- **Rate limits:** FCM supports millions of messages

### Voice
- **Latency:** 2-5 seconds (depends on message length)
- **Bandwidth:** None (local TTS)
- **CPU:** Low (~5-10% during speech)

## Best Practices

1. **Use appropriate priority levels**
   - Don't mark everything as CRITICAL
   - Reserve HIGH/CRITICAL for actual security threats

2. **Configure throttling appropriately**
   - Balance between responsiveness and notification fatigue
   - Consider time of day (more restrictive at night?)

3. **Test regularly**
   - Send test notifications weekly to verify configuration
   - Monitor success rates and adjust as needed

4. **Secure credentials**
   - Never commit credentials to version control
   - Use environment variables or secure secrets management
   - Rotate credentials periodically

5. **Monitor notification stats**
   - Check success rates regularly
   - Investigate failures promptly
   - Adjust based on usage patterns

6. **Customize for your needs**
   - Not all services may be needed
   - Disable unused services to save resources
   - Configure different services for different priorities

## API Reference

See source files for detailed API documentation:
- `src/services/base_notification_service.py` - Base interfaces
- `src/services/notification_manager.py` - Manager API
- Individual service files for service-specific APIs

## Examples

See the `scripts/` directory for working examples:
- `test_notifications.py` - Comprehensive test suite
- `test_email_notification.py` - Email-specific testing

## Support

For issues or questions:
1. Check logs in `/home/ramon/security_data/logs/`
2. Run test scripts to diagnose issues
3. Review this documentation
4. Check service provider documentation (Twilio, Firebase, etc.)

