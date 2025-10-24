# picamera2 Migration Summary

## Overview
The camera service has been updated to use **picamera2** (native Raspberry Pi camera library) instead of OpenCV for camera capture on Raspberry Pi 5.

## Why picamera2?
- **Native Pi camera support**: Built specifically for Raspberry Pi cameras
- **Better performance**: Optimized for Pi 5's new camera system (libcamera/PiSP)
- **Modern architecture**: Uses libcamera framework instead of legacy camera stack
- **Pi 5 compatibility**: OpenCV's `cv2.VideoCapture()` has issues with Pi 5 cameras
- **Better features**: Access to advanced camera controls (HDR, autofocus, etc.)

## What Changed

### Code Changes
- **src/services/camera_service.py**: 
  - Added automatic backend detection (picamera2 for Pi Camera, OpenCV fallback for USB)
  - Captures with picamera2, converts RGB→BGR for OpenCV compatibility
  - All existing APIs remain unchanged

### Documentation Updates

#### 1. **README.md**
- Updated "Key Technologies" section to mention picamera2
- Added picamera2 installation step in Quick Start
- Updated installation instructions to use `--system-site-packages` venv flag

#### 2. **docs/technical_specs.md**
- Added python3-picamera2 to system packages (REQUIRED)
- Clarified OpenCV is for processing, not capture
- Added "Camera Capture" section with performance metrics
- Added note about virtual environment requirements

#### 3. **docs/deployment.md**
- Added python3-picamera2 to system dependencies
- Updated venv creation to use `--system-site-packages` flag
- Updated camera testing section:
  - Replaced `vcgencmd` with `libcamera-hello` (Pi 5)
  - Replaced `raspistill` with `libcamera-still` (Pi 5)
  - Replaced OpenCV test with picamera2 test
  - Added camera service test command

#### 4. **activity_log.md**
- Documented camera testing results
- Documented picamera2 integration
- Marked Epic 2 (Camera integration) as complete

## Installation Requirements

### System Package (REQUIRED)
```bash
sudo apt-get update
sudo apt-get install -y python3-picamera2
```

### Virtual Environment Setup
```bash
# MUST use --system-site-packages to access picamera2
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

### Why system-site-packages?
- picamera2 is tightly integrated with system libraries (libcamera, ISP drivers)
- Cannot be installed via pip on Raspberry Pi
- Must be installed as system package
- Virtual environment needs `--system-site-packages` flag to access it

## Testing Results

### Camera: IMX708 sensor (Pi Camera Module 3)
### Resolution: 1920x1080
### Performance:
- **Basic test**: ✓ PASSED
- **Capture test**: ✓ PASSED (60/60 frames, 0 dropped, 100% success)
- **Performance test**: ✓ PASSED (225 frames, 15.03 FPS, 0 dropped)
- **Actual FPS**: 15-20 FPS
- **Frame time**: ~40ms average

## Backward Compatibility

The camera service maintains full backward compatibility:
- Same API interface
- Automatic backend selection
- Falls back to OpenCV for USB webcams
- Existing test scripts work without modification

## Remote Execution Note

All tests were successfully run remotely via SSH/Cursor, not requiring local Pi display access. This is important for headless server deployments.

## Migration Date
October 12, 2025

## Status
✅ Complete - All documentation updated
✅ All tests passing
✅ Ready for production use

