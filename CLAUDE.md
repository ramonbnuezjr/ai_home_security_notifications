# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Home Security Notifications is a privacy-focused home security system built on Raspberry Pi 5 (16GB RAM) that provides real-time motion detection, AI-powered object classification (YOLOv8), and multi-channel notifications including voice alerts. All processing is performed locally on the Pi 5, ensuring complete privacy and data ownership.

**Current Status**: All core epics complete - Production ready with enterprise-grade security features.

## Essential Commands

### Environment Setup
```bash
# Create virtual environment with system packages (required for picamera2)
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt

# Install system dependencies (on Raspberry Pi)
sudo apt-get install -y python3-picamera2 espeak
```

### Running the System
```bash
# Main detection system with notifications
python scripts/live_detection_with_notifications.py

# Web dashboard (HTTP)
python scripts/run_dashboard.py

# Web dashboard (HTTPS with authentication)
python scripts/run_dashboard_https.py
```

### Testing
```bash
# Run all unit tests
pytest tests/unit/

# Run specific test module
pytest tests/unit/test_auth_service.py

# Run with coverage
pytest --cov=src tests/unit/

# Run integration tests
pytest tests/integration/

# Test notifications
python scripts/test_notifications.py
python scripts/test_email_notification.py
```

### Development Tools
```bash
# Code formatting and linting
black src/ tests/
flake8 src/ tests/
mypy src/

# Security audit
python scripts/security_audit.py

# User management (Epic 6)
python scripts/epic6_cli.py user create
python scripts/epic6_cli.py user list
python scripts/epic6_cli.py status

# Setup HTTPS certificates
python scripts/setup_https.py
```

## System Architecture

### Core Service Architecture

The system follows a modular service-oriented architecture:

1. **Camera Service** (`src/services/camera_service.py`)
   - Uses picamera2 (system package required)
   - Provides frame capture and streaming at 1920x1080
   - Lazy-loaded in web dashboard to prevent camera conflicts

2. **Motion Detection Service** (`src/services/motion_detection_service.py`)
   - Background subtraction using MOG2 algorithm
   - Runs at 30 FPS when YOLO is disabled
   - Configurable zones, sensitivity, and scheduling

3. **Object Detection Service** (`src/services/object_detection_service.py`)
   - YOLOv8s model for 80 object classes
   - CPU performance: 1-2 FPS (expected, consider AI HAT+ upgrade)
   - Only triggered when motion is detected (optimization)

4. **Notification Manager** (`src/services/notification_manager.py`)
   - Multi-channel: Email, SMS (Twilio), Push (Firebase), Voice (espeak TTS)
   - Priority-based routing (LOW, MEDIUM, HIGH, CRITICAL)
   - Intelligent throttling with cooldown periods
   - Async delivery with queue management

5. **Authentication Service** (`src/services/auth_service.py`)
   - JWT-based authentication with refresh tokens
   - Multi-factor authentication (TOTP)
   - Role-based access control (RBAC)
   - 26/26 tests passing

6. **Encryption Service** (`src/services/encryption_service.py`)
   - Fernet encryption for sensitive data at rest
   - TLS certificate generation and management
   - 16/16 tests passing

7. **Privacy Service** (`src/services/privacy_service.py`)
   - GDPR compliance features
   - Data export and deletion capabilities
   - Audit logging
   - 29/32 tests passing

8. **Database Service** (`src/services/database_service.py`)
   - SQLite with WAL mode for concurrency
   - Automatic fallback from SSD to SD card
   - Event logging, user management, audit logs
   - Automatic directory creation

### Web Dashboard Architecture

The Flask-based web dashboard (`src/web/app.py`) uses a blueprint pattern:

- **auth_bp**: Authentication endpoints (login, register, MFA)
- **audit_bp**: Audit log access and monitoring
- **privacy_bp**: GDPR features (data export, deletion)
- **events_bp**: Event history and search
- **stream_bp**: Live MJPEG video streaming
- **metrics_bp**: System monitoring (CPU, memory, temperature)
- **config_bp**: Configuration management
- **notifications_bp**: Notification management

**Important**: Camera service is lazy-loaded on first stream request to prevent conflicts with the main detection script.

### Data Flow

1. **Detection Pipeline**: Camera → Motion Detection → (if motion) → YOLO → Notification Manager
2. **Web Dashboard**: Camera → Stream Generator → MJPEG Stream → Browser
3. **Event Logging**: Detection → Database Service → SQLite
4. **Authentication**: Login → JWT Generation → Middleware Validation

## Configuration

### Primary Configuration File
`config/system_config.yaml` contains all system settings:
- Camera settings (resolution, FPS, format)
- Motion detection parameters (sensitivity, zones, scheduling)
- AI model paths and thresholds
- Notification service credentials
- Database paths and retention policies
- Web dashboard settings (security, streaming, rate limiting)
- Security settings (encryption, HTTPS, audit logging)

### Database Locations
- **Primary**: `/mnt/ssd/security_data/database/security.db` (SSD for performance)
- **Fallback**: `/home/ramon/security_data/database/security.db` (SD card)
- Auto-creates parent directories if missing

### Important Paths
- YOLO Model: `/home/ramon/security_models/yolov8s.pt` (auto-downloaded if missing)
- Media Storage: `/home/ramon/security_data/` (videos, images, logs)
- TLS Certificates: `config/certs/` (generated by setup_https.py)

## Development Workflow

### Virtual Environment Notes
- **Critical**: Must use `--system-site-packages` flag for picamera2 access
- picamera2 is installed system-wide via apt (cannot be pip installed)
- All other dependencies installed via pip in venv

### Testing Strategy
- Unit tests: `tests/unit/` - Isolated service testing
- Integration tests: `tests/integration/` - Service interaction testing
- Hardware tests: Require actual Pi 5 hardware with camera

### Camera Conflict Prevention
The Pi Camera can only be accessed by one process at a time:
- If running detection script, don't start web dashboard stream
- If web dashboard has active stream, don't start detection script
- Camera service in web app is lazy-loaded to avoid preemptive locks

### Code Style
- PEP 8 compliance enforced by flake8
- Black for formatting
- Type hints for all functions (mypy)
- Google-style docstrings

## Performance Characteristics

### CPU Performance (No AI HAT)
- **Motion Detection Only**: 30 FPS
- **Motion + YOLO**: 1-2 FPS (500-1000ms per frame)
- This is expected behavior on Pi 5 CPU

### Optimization Strategy
- YOLO only runs when motion is detected (major optimization)
- Frame skipping can be configured via `performance.frame_skip`
- Consider AI HAT+ (Hailo-8L) for 20-30 FPS with YOLO (10-15x speedup)

### Memory Usage
- System designed for 16GB RAM Pi 5
- Can run multiple AI models simultaneously
- Memory limit configured at 14GB (leaving 2GB for system)

## Security & Authentication

### Production Deployment Requirements
1. Change `web.secret_key` in config to secure random key
2. Setup HTTPS: `python scripts/setup_https.py`
3. Create admin user: `python scripts/epic6_cli.py user create`
4. Secure file permissions: `chmod 600 config/system_config.yaml data/*.db`
5. Run security audit: `python scripts/security_audit.py`
6. Disable debug mode: Set `web.debug: false` in config

### Authentication Flow
- JWT tokens with refresh mechanism
- Optional MFA (TOTP) for enhanced security
- Role-based access control (admin, user, viewer roles)
- Session timeout configurable via `web.session_timeout`

### Privacy Features
- All processing is local (no cloud storage)
- GDPR compliance built-in (data export, deletion, audit logs)
- Configurable data retention policies
- Encryption for sensitive data at rest

## Common Pitfalls

1. **picamera2 Import Errors**: Must use `--system-site-packages` when creating venv
2. **Camera Busy Error**: Only one process can access camera - check for running scripts
3. **Slow YOLO Performance**: This is normal on CPU - not a bug, consider AI HAT+ upgrade
4. **Voice Notifications Not Working**: Need physical audio connection to Pi (not SSH)
5. **Database Connection Errors**: Check parent directories exist or enable `auto_create_dirs`
6. **HTTPS Certificate Issues**: Run `python scripts/setup_https.py` to generate certs
7. **NumPy Version Conflicts**: Must use numpy<2.0 for picamera2 compatibility

## Key Documentation Files

- **Architecture**: `docs/architecture.md` - Complete system design
- **Quick Start**: `docs/guides/QUICKSTART.md` - Get started in minutes
- **Authentication**: `docs/guides/AUTHENTICATION_GUIDE.md` - Security setup
- **Notifications**: `docs/guides/NOTIFICATION_SYSTEM.md` - Notification configuration
- **Hardware Upgrades**: `docs/guides/HARDWARE_UPGRADES.md` - Performance optimization
- **Development**: `docs/development/development_workflow.md` - Development process
- **Quick Reference**: `QUICK_REFERENCE.md` - Command cheat sheet

## Recent Major Milestones

- ✅ Epic 1-3: Hardware, motion detection, AI classification
- ✅ Epic 4: Multi-channel notification system (Email, SMS, Push, Voice)
- ✅ Epic 5: Web dashboard with live streaming and database integration
- ✅ Epic 6: Enterprise security features (JWT, MFA, RBAC, encryption, GDPR)
- ✅ Full system integration complete

## Git Workflow

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch (if used)
- `feature/*`: Feature development branches

### Commit Message Format
```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore
Examples:
  feat(motion): add zone-based detection
  fix(camera): resolve initialization timeout
  docs(api): update authentication guide
```
