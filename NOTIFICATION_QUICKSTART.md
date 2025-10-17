# Notification System - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Install Dependencies

```bash
cd /home/ramon/ai_projects/ai_home_security_notifications
source venv/bin/activate
pip install firebase-admin pyttsx3
```

### Step 2: Configure Email (Easiest to start)

Edit `config/system_config.yaml`:

```yaml
notifications:
  enabled: true
  cooldown_period: 300  # 5 minutes between notifications
  max_notifications_per_hour: 10
  
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "your_email@gmail.com"
    smtp_password: "your_app_password"  # Get from Google
    from_address: "your_email@gmail.com"
    to_addresses:
      - "your_email@gmail.com"  # Send to yourself for testing
```

**Gmail App Password:** https://myaccount.google.com/apppasswords

### Step 3: Test Email

```bash
python scripts/test_email_notification.py
```

You should receive a test email! ✅

### Step 4: Enable Other Services (Optional)

#### SMS (Twilio)

```yaml
  sms:
    enabled: true
    provider: "twilio"
    twilio:
      account_sid: "your_account_sid"
      auth_token: "your_auth_token"
      from_number: "+1234567890"
      to_numbers:
        - "+1234567890"
```

Get credentials from: https://www.twilio.com

#### Push Notifications (Firebase)

```yaml
  push:
    enabled: true
    provider: "firebase"
    firebase:
      credentials_path: "/path/to/firebase-credentials.json"
      device_tokens:
        - "your_device_token"
```

Setup: https://console.firebase.google.com

#### Voice Alerts

```yaml
  voice:
    enabled: true
    text_to_speech: true
    voice_settings:
      rate: 150
      volume: 0.8
```

Already works! No external credentials needed.

### Step 5: Test All Services

```bash
python scripts/test_notifications.py
```

## 📱 Usage Examples

### Basic Notification

```python
from src.services.notification_manager import NotificationManager
from src.services.base_notification_service import (
    NotificationContext, 
    NotificationPriority
)
from src.utils.config import Config
import time

# Initialize
config = Config()
manager = NotificationManager(config)
manager.start()

# Send notification
context = NotificationContext(
    event_type='motion_detected',
    timestamp=time.time(),
    priority=NotificationPriority.HIGH,
    detected_objects=['person'],
    zone_name='Front Door'
)

manager.send_notification(context)

# Cleanup
manager.stop()
```

### With Motion Detection

```python
# ... initialize camera and motion detector ...

# Detect motion
motion_event = motion_detector.detect_motion(frame)

if motion_event:
    # Send notification
    context = NotificationContext(
        event_type='motion_detected',
        timestamp=motion_event.timestamp,
        priority=NotificationPriority.MEDIUM,
        motion_percentage=motion_event.motion_percentage,
        zone_name='Camera 1'
    )
    
    notifier.send_notification(context)
```

### Live Demo

```bash
python scripts/live_detection_with_notifications.py
```

Press 'N' to send test notification
Press 'S' to toggle notifications on/off

## 🎯 Priority Levels

- **LOW** - Regular events, subject to throttling
- **MEDIUM** - Important events
- **HIGH** - Security concerns, reduced throttling
- **CRITICAL** - Emergency, overrides all throttling

```python
NotificationPriority.LOW       # Motion detected
NotificationPriority.MEDIUM    # Object detected
NotificationPriority.HIGH      # Person detected
NotificationPriority.CRITICAL  # Break-in detected
```

## 🔧 Common Configurations

### Quiet Hours (Reduce Notifications at Night)

Use motion detection scheduling in config:

```yaml
detection:
  schedule:
    enabled: true
    active_hours:
      - start: "22:00"  # 10 PM to 6 AM
        end: "06:00"
```

### High Security Mode

```yaml
notifications:
  cooldown_period: 60    # Notify every minute
  max_notifications_per_hour: 30
```

### Low Noise Mode

```yaml
notifications:
  cooldown_period: 600   # Only every 10 minutes
  max_notifications_per_hour: 5
```

### Emergency Mode (No Throttling)

Send with `force=True`:

```python
manager.send_notification(context, force=True)
```

## 📊 Check Statistics

```python
stats = manager.get_statistics()
print(f"Email sent: {stats['services']['email']['sent_count']}")
print(f"Success rate: {stats['services']['email']['success_rate']:.1%}")
```

## 🔍 Troubleshooting

### Email not sending?

```bash
# Test SMTP connection
python -c "
from src.services.email_notification_service import EmailNotificationService
from src.utils.config import Config
service = EmailNotificationService(Config())
print('Test:', service.test_connection())
"
```

### Check logs

```bash
tail -f logs/security_system.log
```

### Reset throttling

```python
manager.reset_throttling()
```

## 📚 Full Documentation

See `docs/NOTIFICATION_SYSTEM.md` for:
- Detailed configuration for all services
- Advanced features
- API reference
- Performance tuning
- Security best practices

## 💡 Tips

1. **Start with email only** - Easiest to configure
2. **Test each service individually** before enabling all
3. **Monitor success rates** - Adjust configs as needed
4. **Use appropriate priorities** - Don't overuse HIGH/CRITICAL
5. **Configure throttling** - Prevent notification spam
6. **Check spam folders** - For email notifications
7. **Verify phone numbers** - For Twilio trial accounts
8. **Keep credentials secure** - Never commit to git

## 🎉 You're Done!

Your notification system is ready. When motion + objects are detected, you'll receive alerts through your configured channels.

Next steps:
- Fine-tune motion detection sensitivity
- Configure motion zones
- Adjust throttling for your needs
- Set up the web dashboard (Epic 5)

