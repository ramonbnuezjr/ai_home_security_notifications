# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- **HAL 9000 Voice Layer**: Premium voice notification system using Google Cloud TTS
  - HAL-style voice characteristics (deep pitch, slow cadence)
  - 80+ pre-synthesized security phrases in `src/voice/hal_phrases.yaml`
  - Standalone voice library generator script
  - Local caching of audio files for instant playback
  - Graceful fallback to espeak when Google TTS unavailable
  - Comprehensive setup guide in `README_HAL_SETUP.md`
- **HAL Voice Integration**: Fully integrated HAL voice into notification system
  - Created `HALNotificationService` wrapper for notification manager
  - Automatic USB audio device detection
  - Context-aware phrase selection (person detected, motion, vehicles, etc.)
  - Test script: `scripts/test_yolo_and_hal.py`
  - Uses `mpg123` for superior MP3 playback (no more audio static)
- **Netdata System Monitoring**: Real-time performance monitoring dashboard
  - Install and configure Netdata for system monitoring
  - Access at `http://192.168.7.210:19999`
  - Monitor CPU, RAM, temperature, network, disk I/O
  - Track YOLO process performance
  - Temperature alert configuration
- **Future Vision Documentation**: Long-term roadmap for personal AI assistant
  - Created `docs/planning/PROPOSED_EPICS.md` with 14 new epics
  - Created `docs/planning/FUTURE_VISION.md` for personal AI transformation
  - Epic 7 (USB Audio): USB speaker/mic integration
  - Epic 8 (Face Recognition): Family member detection
  - Epic 10 (Hardware): Pironman 5-MAX case, NVMe storage
  - Epic 11 (AI HAT): Hailo-8L acceleration for 20-30 FPS YOLO
  - Vision for local LLM integration (Mistral 7B)
  - Robotics roadmap (SunFounder Picar-X)
- Created CHANGELOG.md to track project changes

### Changed
- **Notification Manager**: Updated to prioritize HAL voice over espeak
  - Auto-detects HAL audio files vs espeak fallback
  - Improved phrase mapping for security events
  - Better audio playback using mpg123

### Fixed
- **Audio Playback**: Fixed audio static issue by using `mpg123` instead of `aplay`
- **HAL Service**: Fixed missing abstract method implementation (`test_connection`)
- **Notification Result**: Fixed incorrect parameter names (service → provider)

### Documentation
- **Main README**: Added step 11 for Netdata monitoring setup
- **QUICK_REFERENCE.md**: Added monitoring URL and USB audio section
- **HARDWARE_UPGRADES.md**: Added Netdata monitoring section with installation
- **PROPOSED_EPICS.md**: Complete epic breakdown for Phase 2+ development
- **FUTURE_VISION.md**: Personal AI assistant roadmap
- **NEW_FEATURES_QUICK_START.md**: Quick reference for starting new features

## [1.0.1] - 2025-10-16

### Changed
- **Model Distribution**: YOLO model files now excluded from git repository
  - Added `*.pt` and `yolov8s.pt` to `.gitignore`
  - Model must be downloaded separately via wget
  - Documented download instructions in all guides
  - Keeps repository lightweight (~1MB vs ~21MB)

### Documentation Updates
- **README.md**: Added step 4 for model download in installation process
- **QUICKSTART.md**: Added Prerequisites section with model download instructions
- **YOLO_INTEGRATION_GUIDE.md**: Restructured Quick Start with model download as step 1
- **docs/deployment.md**: Updated model URLs from v0.0.0 to v8.3.0, changed path from `/models/` to project root
- **DOCUMENTATION_SUMMARY.md**: Added Recent Updates section documenting model distribution changes
- **.gitignore**: Added comprehensive Python, OS, and project-specific exclusions

### Improved
- Faster repository cloning (reduced size by ~20MB)
- Better separation of code and binary assets
- Aligned with Git best practices for ML projects
- More flexible model versioning

## [1.0.0] - 2025-10-12

### Added
- YOLOv8 object detection integration
- Motion detection with MOG2 algorithm
- Pi Camera Module 3 support via picamera2
- Live motion + object detection visualization
- 80 object class detection capability
- Command-line options for customization
  - `--confidence`: Adjust detection threshold
  - `--yolo-skip`: Frame skipping for performance
  - `--all-classes`: Detect all 80 classes
  - `--no-yolo`: Motion-only mode
  - `--fps`: Display frame rate limiting

### Features
- Efficient pipeline: YOLO only runs when motion detected
- Real-time classification with bounding boxes
- Interactive controls (toggle YOLO, save screenshots, adjust sensitivity)
- Multiple run modes (full system, frame skip, motion-only, headless)
- Comprehensive test scripts:
  - `test_camera.py`: Camera hardware verification
  - `test_yolo.py`: YOLO installation test
  - `test_motion_detection.py`: Headless motion testing
  - `test_object_detection.py`: Headless object detection
  - `test_small_objects.py`: Small object detection testing

### Documentation
- Comprehensive README with full setup instructions
- QUICKSTART.md for rapid testing
- YOLO_INTEGRATION_GUIDE.md for detailed integration info
- docs/deployment.md for production setup
- docs/architecture.md for system design
- docs/technical_specs.md for specifications
- DOCUMENTATION_SUMMARY.md for doc overview

### Performance
- Motion detection: ~30 FPS (real-time)
- YOLO inference: ~500-1000ms per detection (CPU)
- Live view with YOLO: ~1-2 FPS during detection
- Frame skipping mode: ~15-20 FPS

### Hardware Support
- Raspberry Pi 5 (16GB RAM)
- Pi Camera Module 3 (IMX708 sensor)
- 1920x1080 @ 15 FPS capture
- Active cooling recommended

---

## Version Naming

- **Major version** (X.0.0): Significant architectural changes or major features
- **Minor version** (0.X.0): New features, enhancements, or notable changes
- **Patch version** (0.0.X): Bug fixes, documentation updates, minor improvements


