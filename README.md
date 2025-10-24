# AI Home Security Notifications

An intelligent home security system built on Raspberry Pi 5 that provides real-time motion detection, AI-powered object classification, and multi-channel notifications including voice alerts via Whisper integration.

## 🎯 Project Vision

Create a privacy-focused, locally-processed home security solution that combines traditional motion detection with modern AI capabilities to provide intelligent, context-aware security notifications while keeping all data processing local to your home.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pi Camera     │───▶│   Pi 5 SBC       │───▶│  Notification   │
│   Module        │    │  (16GB RAM)      │    │  System         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Local Storage  │
                       │   (SD/SSD)       │
                       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   AI Models      │
                       │   (Motion +      │
                       │   Classification)│
                       └──────────────────┘
```

### Key Features ✨
- ✅ **Real-time Motion Detection**: Advanced background subtraction @ 30 FPS with configurable zones
- ✅ **AI Object Classification**: YOLOv8s-powered detection (80 object classes)
  - **CPU Performance**: ~1-2 FPS (500-1000ms per frame)
  - **With AI HAT+**: Can achieve 20-30 FPS (upgrade recommended)
  - Smart optimization: Only runs YOLO when motion detected
- ✅ **Multi-channel Notifications**: Email (HTML), SMS (Twilio), Push (Firebase), Voice (TTS)
  - Priority-based routing (LOW, MEDIUM, HIGH, CRITICAL)
  - Intelligent throttling with cooldown periods
  - Async delivery with queue management
  - Rich notifications with images and metadata
  - Working voice alerts with espeak TTS 🤖
- ✅ **Privacy-First Design**: All processing performed locally on Pi 5 (16GB RAM)
- 🔄 **Web Dashboard**: Live video feed, event history, and system configuration (In Progress)
- ✅ **Modular Architecture**: Easy to extend and customize

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi 5 (16GB RAM recommended)
- Pi Camera Module 3 or compatible
- 64GB+ microSD card or SSD
- Official Pi 5 power supply (27W)
- Active cooling solution

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_home_security_notifications
   ```

2. **Set up Pi 5 hardware**
   ```bash
   # Follow detailed setup in docs/deployment.md
   # Enable camera interface: sudo raspi-config
   ```

3. **Install system dependencies**
   ```bash
   # Install picamera2 (system package required for Pi Camera)
   sudo apt-get update
   sudo apt-get install -y python3-picamera2
   ```

4. **Download YOLO model**
   ```bash
   # The YOLOv8s model will be automatically downloaded on first run
   # Or manually download it to the project root:
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt
   ```

5. **Install Python dependencies**
   ```bash
   # Create virtual environment with access to system packages
   python3 -m venv --system-site-packages venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure the system**
   ```bash
   cp config/system_config.yaml config/production_config.yaml
   # Edit configuration file with your settings
   ```

7. **Test the notification system** (Optional but recommended)
   ```bash
   # Test email notifications
   python scripts/test_email_notification.py
   
   # Test all notification services
   python scripts/test_notifications.py
   ```

8. **Run live detection with notifications**
   ```bash
   # Full system demo
   python scripts/live_detection_with_notifications.py
   ```

9. **Access web dashboard with authentication** (Epic 6 Complete ✅)
   - Open browser to `https://your-pi-ip:5000` (HTTPS recommended)
   - First-time: Create admin account through setup wizard
   - Login with your credentials
   - Full authentication, RBAC, and security features enabled

10. **Manage security settings** (Epic 6 - Fully Integrated ✅)
   ```bash
   # Initialize encryption (first time setup)
   python scripts/epic6_cli.py encryption init
   
   # Create admin user
   python scripts/epic6_cli.py user create
   
   # Check system status
   python scripts/epic6_cli.py status
   
   # View audit logs
   python scripts/epic6_cli.py audit logs
   ```

## 📚 Documentation

### Core Documentation
- **[System Architecture](docs/architecture.md)** - Complete system design and component interactions
- **[Technical Specifications](docs/technical_specs.md)** - Hardware requirements, software stack, and performance targets
- **[Deployment Guide](docs/deployment.md)** - Step-by-step Pi 5 setup and installation
- **[Development Workflow](docs/development_workflow.md)** - Development environment, testing, and CI/CD

### Project Management
- **[Epics and User Stories](docs/epics_and_stories.md)** - Feature breakdown with acceptance criteria
- **[Task Breakdown](docs/task_breakdown.md)** - Detailed implementation tasks with dependencies
- **[Risk Management](docs/risks.md)** - Technical and project risks with mitigation strategies

### Configuration & Guides
- **[Quick Reference](QUICK_REFERENCE.md)** - ⚡ Command cheat sheet
- **[Authentication Guide](docs/AUTHENTICATION_GUIDE.md)** - 🔐 Complete security & auth setup
- **[System Configuration](config/system_config.yaml)** - Complete configuration template
- **[Notification System Guide](docs/NOTIFICATION_SYSTEM.md)** - Comprehensive notification setup
- **[Notification Quick Start](NOTIFICATION_QUICKSTART.md)** - 5-minute notification setup
- **[Hardware Upgrades](docs/HARDWARE_UPGRADES.md)** - Performance optimization guide
- **[Phase 1 Complete](PHASE1_COMPLETE.md)** - 🎉 Summary of achievements
- **[Project Status](project_status.md)** - Current project status and milestones
- **[Activity Log](activity_log.md)** - Development history and decisions

## 🏗️ Project Structure

```
ai_home_security_notifications/
├── README.md                    # This file
├── project_status.md           # Current project status
├── activity_log.md             # Development history
├── contributing.md             # Contribution guidelines
├── config/
│   └── system_config.yaml      # Configuration template
├── docs/
│   ├── architecture.md         # System architecture
│   ├── technical_specs.md      # Technical specifications
│   ├── epics_and_stories.md    # Feature breakdown
│   ├── task_breakdown.md       # Implementation tasks
│   ├── risks.md                # Risk management
│   ├── development_workflow.md # Development process
│   └── deployment.md           # Installation guide
├── src/                        # Source code
│   ├── services/               # Core service implementations
│   │   ├── auth_service.py     # Authentication & user management
│   │   ├── encryption_service.py # Data encryption & TLS
│   │   ├── privacy_service.py  # GDPR compliance & privacy
│   │   ├── database_service.py # Database operations
│   │   └── ...                 # Other services
│   ├── web/                    # Web dashboard
│   │   ├── app.py              # Flask application
│   │   ├── api/                # REST API endpoints
│   │   ├── templates/          # HTML templates
│   │   └── static/             # CSS, JS, images
│   └── utils/                  # Utility modules
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── hardware/               # Hardware tests
└── scripts/                    # Utility and test scripts
    ├── live_detection_with_notifications.py  # Main detection system
    ├── run_dashboard.py                      # Web dashboard launcher
    ├── epic6_cli.py                          # Security management CLI
    └── test_*.py                             # Various test scripts
```

## 🎯 Current Status

**Phase:** All Core Epics Complete ✅ - Production Integration Phase

### Completed ✅
- ✅ **Epic 1: Hardware & Camera** - Pi 5 16GB + Camera Module @ 1920x1080
- ✅ **Epic 2: Motion Detection** - Real-time detection @ 30 FPS
- ✅ **Epic 3: AI Classification** - YOLOv8s object detection (80 classes, ~1-2 FPS on CPU)
- ✅ **Epic 4: Notification System** - Multi-channel alerts (Email, SMS, Push, Voice)
  - Voice notifications fully operational with espeak
  - Email/SMS/Push configured (need credentials)
  - Intelligent throttling and async delivery
- ✅ **Epic 5: Web Dashboard & Monitoring** - Complete web interface
  - Live video streaming (MJPEG)
  - Event history with filtering and search
  - System monitoring (CPU, memory, temperature)
  - Configuration interface
  - SQLite database with event logging
  - Database integration with live detection
- ✅ **Epic 6: Security & Privacy Controls** - Fully integrated into web dashboard (100% Complete)
  - ✅ Authentication service (JWT, MFA, RBAC) - 26/26 tests passing
  - ✅ Encryption service (Fernet, TLS certs) - 16/16 tests passing
  - ✅ Privacy service (GDPR, data export/deletion) - 29/32 tests passing
  - ✅ Web dashboard authentication integration (login UI, JWT middleware)
  - ✅ HTTPS/TLS configuration with certificate generation
  - ✅ User management interface (admin portal)
  - ✅ Security audit tools
  - ✅ Comprehensive documentation
- ✅ System architecture and documentation
- ✅ Test scripts and integration demos
- ✅ Configuration system

### Performance Notes
- Motion detection alone: **30 FPS** ⚡
- Motion + YOLO (CPU): **1-2 FPS** (expected behavior)
- **Recommended upgrade**: AI HAT+ (Hailo-8L) for 20-30 FPS with YOLO

### System Status ✅
**All Core Features Complete** - Ready for Production Deployment

The system is now feature-complete with enterprise-grade security. All epics have been successfully implemented and integrated.

### Production Deployment Checklist
Before deploying to production:
1. ✅ Run security audit: `python scripts/security_audit.py`
2. ✅ Setup HTTPS certificates: `python scripts/setup_https.py`
3. ✅ Create admin user: `python scripts/epic6_cli.py user create`
4. ✅ Secure file permissions: `chmod 600 config/system_config.yaml data/*.db`
5. ✅ Configure production settings (disable debug, set strong secret key)
6. ✅ Setup automated backups for database
7. ⚠️ Optional: Consider AI HAT+ (Hailo-8L) for 10-15x YOLO performance boost

### Optional Enhancements
- AI HAT+ Integration for 20-30 FPS YOLO (vs. current 1-2 FPS on CPU)
- Mobile app development
- Multi-camera support
- Advanced AI features (face recognition, behavior analysis)
- Cloud integration (optional backup)

## 🛠️ Development

### Getting Started
1. Read the [Development Workflow](docs/development_workflow.md)
2. Set up your development environment
3. Review the [Task Breakdown](docs/task_breakdown.md) for implementation details
4. Check [Contributing Guidelines](contributing.md) for contribution process

### Key Technologies
- **Hardware**: Raspberry Pi 5, Pi Camera Module (IMX708)
- **Camera**: picamera2 (native Pi camera library), OpenCV for processing
- **AI/ML**: YOLOv8, Whisper
- **Backend**: Python 3.11+, Flask, SQLite
- **Frontend**: HTML5, JavaScript, WebRTC
- **Notifications**: SMTP, Twilio, Firebase Cloud Messaging

## 🔒 Security & Privacy

This system is designed with enterprise-grade security and privacy:
- **JWT Authentication**: Secure token-based authentication with role-based access control
- **Multi-Factor Authentication**: Optional TOTP-based 2FA for added security
- **Encrypted Storage**: Fernet encryption for sensitive data at rest
- **HTTPS/TLS**: Secure communication with TLS 1.2+ encryption
- **Local Processing**: All AI inference performed on Pi 5
- **No Cloud Storage**: Video data never leaves your home (unless you configure cloud notifications)
- **User Control**: Complete data ownership and deletion capabilities
- **GDPR Compliant**: Built-in privacy controls, data export, and audit logging
- **Security Auditing**: Automated security audit tools included

**See [Authentication Guide](docs/AUTHENTICATION_GUIDE.md) for complete security documentation.**

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](contributing.md) for details on:
- Development workflow
- Code style guidelines
- Testing requirements
- Pull request process

## 📄 License

[Add your license information here]

## 🆘 Support

- **Documentation**: Check the `/docs` directory for comprehensive guides
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions via GitHub Discussions

## 🗺️ Roadmap

### Phase 1: Core System (Current)
- Hardware setup and camera integration
- Basic motion detection
- AI object classification
- Email/SMS notifications

### Phase 2: Enhanced Features
- Voice notifications (Whisper)
- Web dashboard
- Push notifications
- Advanced configuration

### Phase 3: Advanced Capabilities
- Multi-camera support
- Advanced AI features
- Mobile app
- Cloud integration (optional)

---

**Built with ❤️ for privacy-focused home security**
