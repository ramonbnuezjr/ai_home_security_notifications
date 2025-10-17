# Quick Reference Card

## 🚀 Start the System

```bash
cd /home/ramon/ai_projects/ai_home_security_notifications
source venv/bin/activate
python scripts/live_detection_with_notifications.py
```

## 🎮 Controls (in video window)

| Key | Action |
|-----|--------|
| **Q** | Quit |
| **N** | Send test notification |
| **S** | Toggle notifications ON/OFF |
| **O** | Toggle YOLO ON/OFF |
| **3** | Low sensitivity (0.3) |
| **5** | Medium sensitivity (0.5) |
| **7** | High sensitivity (0.7) |
| **9** | Max sensitivity (0.9) |

## 📊 Performance

| Feature | FPS | Notes |
|---------|-----|-------|
| Motion Only | 30 | YOLO off |
| Motion + YOLO | 1-2 | CPU limitation |
| With AI HAT+ | 20-30 | Future upgrade |

## 🔊 Notifications

| Service | Status | Setup |
|---------|--------|-------|
| Voice | ✅ Working | espeak installed |
| Email | ⚙️ Needs config | Edit config YAML |
| SMS | ⚙️ Needs config | Twilio account |
| Push | ⚙️ Needs config | Firebase setup |

## 📁 Key Files

```
Main script:       scripts/live_detection_with_notifications.py
Config:            config/system_config.yaml
Test email:        scripts/test_email_notification.py
Test all notifs:   scripts/test_notifications.py
Documentation:     docs/NOTIFICATION_SYSTEM.md
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| No voice | Install espeak: `sudo apt install espeak` |
| Can't hear | Connect to Pi directly (not SSH) |
| Camera busy | Quit other scripts using camera |
| Slow FPS | Normal on CPU, see HARDWARE_UPGRADES.md |
| Keys don't work | Click video window first |

## ⚙️ Configuration

Edit `config/system_config.yaml`:

```yaml
# Motion sensitivity
detection:
  sensitivity: 0.7  # 0.0-1.0

# Notification cooldown
notifications:
  cooldown_period: 30  # seconds

# Camera resolution
camera:
  resolution:
    width: 1920
    height: 1080
```

## 📚 Documentation

- **Quick Start**: `NOTIFICATION_QUICKSTART.md`
- **Full Guide**: `docs/NOTIFICATION_SYSTEM.md`
- **Upgrades**: `docs/HARDWARE_UPGRADES.md`
- **Phase 1 Summary**: `PHASE1_COMPLETE.md`

## 🆘 Help

1. Check logs: `tail -f logs/security_system.log`
2. Run tests: `python scripts/test_notifications.py`
3. See docs: `docs/` directory
4. Activity log: `activity_log.md`

---

**Quick tip**: Press 'N' in the video window to test voice notifications! 🤖

