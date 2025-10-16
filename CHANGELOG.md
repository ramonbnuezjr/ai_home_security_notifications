# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Created CHANGELOG.md to track project changes

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

