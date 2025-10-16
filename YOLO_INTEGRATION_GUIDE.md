# YOLOv8 Object Detection Integration Guide

## Overview

YOLOv8 object detection has been successfully integrated with the motion detection system! The system now intelligently detects motion first, then classifies what's moving (person, car, animal, etc.).

## What's New

### Architecture
- **Efficient Pipeline**: Object detection only runs when motion is detected (saves processing power)
- **YOLOv8s Model**: Using the "small" variant optimized for your Pi 5 16GB RAM
- **80 Object Classes**: Can detect people, vehicles, animals, and many more objects
- **Real-time Classification**: Live object detection with bounding boxes and confidence scores

### Files Created/Modified
1. **`src/services/object_detection_service.py`** - New YOLOv8 service
2. **`scripts/live_motion_detection.py`** - Updated with YOLO integration
3. **`src/services/motion_detection_service.py`** - Enhanced MotionEvent with object detection
4. **`scripts/test_yolo.py`** - YOLO installation test script

## Quick Start

### 1. Test YOLO Installation
```bash
cd /home/ramon/ai_projects/ai_home_security_notifications
source venv/bin/activate
python scripts/test_yolo.py
```

**Expected output:**
- ✓ Model downloads (21.5MB, one-time only)
- ✓ Model loads successfully
- ✓ Inference test passes
- ✓ Shows 80 available detection classes

### 2. Test Object Detection (No Display Needed)
```bash
python scripts/test_object_detection.py --confidence 0.25
```

Takes 5 photos and saves annotated images showing detections.

### 3. Run Live Detection with YOLO
```bash
python scripts/live_motion_detection.py
```

**Requires display (HDMI/VNC). For smoother performance:**
```bash
python scripts/live_motion_detection.py --yolo-skip 2
```

## Testing Instructions

### Basic Motion + Object Detection Test

1. **Start the system:**
   ```bash
   cd /home/ramon/ai_projects/ai_home_security_notifications
   source venv/bin/activate
   python scripts/live_motion_detection.py
   ```

2. **Initial calibration:**
   - Stay still for 2-3 seconds (lets algorithm learn background)
   - Status display will show "YOLO: ON" in bottom right

3. **Trigger motion detection:**
   - Wave your hand in front of camera
   - Motion boxes appear (gray/yellow)
   - **NEW**: Colored bounding boxes with labels appear around detected objects
   - Green box = person, Blue box = car, etc.

4. **Watch the info panel (top left):**
   - Motion statistics
   - **NEW**: "Detected: [object names]" when objects are classified
   - Example: "Detected: person, cell phone"

5. **Performance check:**
   - First detection may be slow (~3-4 seconds)
   - Subsequent detections should be faster (~500-1000ms on Pi 5)
   - Object detection only runs when motion is detected

### Interactive Controls

| Key | Action |
|-----|--------|
| `Q` | Quit the application |
| `R` | Reset motion detector |
| `S` | Save screenshot |
| `O` | Toggle YOLO on/off (for speed testing) |
| `1-9` | Change motion sensitivity |
| `M` | Toggle motion mask window |

### Command Line Options

| Flag | Description |
|------|-------------|
| `--confidence 0.25` | Lower detection threshold (detects more objects) |
| `--yolo-skip 2` | Run YOLO every 3rd frame (smoother live view) |
| `--all-classes` | Detect all 80 classes (ignore config filter) |
| `--no-yolo` | Disable YOLO (30 FPS motion only) |
| `--fps 15` | Limit display frame rate |

### Advanced Testing

#### Test Different Object Types

1. **Person Detection:**
   - Walk in front of camera
   - Expected: Green box with "person 0.85" label

2. **Multiple Objects:**
   - Hold your phone while walking
   - Expected: "person" + "cell phone" detected

3. **Vehicle Detection** (if applicable):
   - Point camera at street/driveway
   - Expected: "car", "truck", "bicycle", etc.

#### Performance Modes

1. **With YOLO (default):**
   ```bash
   python scripts/live_motion_detection.py
   ```
   - Full object classification
   - ~500-1000ms inference time per motion event

2. **Motion Only (faster):**
   ```bash
   python scripts/live_motion_detection.py --no-yolo
   ```
   - Just motion detection, no object classification
   - Useful for performance comparison

3. **Adjust sensitivity:**
   - Press `3` for 30% sensitivity (less sensitive)
   - Press `7` for 70% sensitivity (more sensitive)
   - Press `9` for 90% sensitivity (very sensitive)

#### Toggle YOLO During Runtime

- Press `O` to toggle YOLO on/off without restarting
- Useful for comparing performance impact
- Status indicator shows "YOLO: ON" or "YOLO: OFF"

## Configuration

Edit `config/system_config.yaml` to customize object detection:

```yaml
ai:
  yolo:
    model_variant: "yolov8s"  # Options: yolov8n (faster), yolov8s (balanced), yolov8m (accurate)
    confidence_threshold: 0.5  # 0.0-1.0, higher = fewer false positives
    max_detections: 10         # Maximum objects per frame
    
  classification:
    enabled: true
    target_classes: []         # CURRENT: Empty = detects all 80 classes
    ignore_classes: []         # CURRENT: No filtering
    min_object_size: 0.01      # Minimum object size (1% of frame)
    max_object_size: 0.8       # Maximum object size (80% of frame)

# Example filters for specific use cases:
# Security camera: target_classes: ["person", "car", "truck", "backpack"]
# Package detection: target_classes: ["person", "backpack", "handbag", "suitcase"]
# Pet monitoring: target_classes: ["cat", "dog", "bird"]
```

## Detection Classes

YOLOv8 can detect 80 object classes including:

**People & Animals:**
person, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, bird

**Vehicles:**
car, truck, bus, motorcycle, bicycle, train, airplane, boat

**Common Objects:**
cell phone, laptop, keyboard, mouse, backpack, umbrella, handbag, bottle, cup, knife, fork, spoon

**And many more!**

Run `python scripts/test_yolo.py` to see the full list.

## Performance Optimization

### Current Performance (Pi 5 16GB)
- **Motion Detection:** ~30 FPS, real-time (no slowdown)
- **YOLO Inference:** ~500-1000ms per detection (CPU-only, expected)
- **Live View with YOLO:** ~1-2 FPS during detection (normal)
- **With Frame Skip (--yolo-skip 2):** ~15-20 FPS (smoother)
- **Combined Strategy:** Only runs YOLO when motion detected (efficient!)

**The slowdown during YOLO is expected and normal for CPU-based inference on Pi 5.**

### Tips for Better Performance

1. **Use target_classes filter:**
   - Only detect what you care about
   - Reduces processing time

2. **Adjust confidence threshold:**
   - Higher threshold = fewer false positives
   - Lower threshold = detect more objects (may have false positives)

3. **Model variants:**
   - `yolov8n`: Fastest, less accurate
   - `yolov8s`: Balanced (current, recommended)
   - `yolov8m`: More accurate, slower

4. **Motion sensitivity:**
   - Lower sensitivity = fewer YOLO calls = better performance
   - Higher sensitivity = more detections but more processing

## Troubleshooting

### Issue: YOLO not initializing
**Solution:**
```bash
# Reinstall ultralytics
pip install --upgrade ultralytics
# Test again
python scripts/test_yolo.py
```

### Issue: Slow frame rate with YOLO enabled
**This is normal!** YOLO inference takes ~0.5-1.0 seconds on Pi 5 CPU.
**Solutions:**
- Use frame skipping for smoother view: `--yolo-skip 2`
- Switch to yolov8n model for faster inference (edit config)
- Toggle YOLO off when not needed (press `O` key)
- Accept the trade-off (accuracy requires computation time)

### Issue: First detection very slow (3-4 seconds)
**Cause:** Model warmup (one-time per session)
**Solution:** This is normal, subsequent detections will be faster (~500-1000ms)

### Issue: No objects detected (but person works fine)
**Most common cause:** Object is filtered by target_classes!

**Check config:**
```bash
grep target_classes config/system_config.yaml
```

If you see: `target_classes: ["person", "car", ...]`  
Then only those objects will be detected!

**Solutions:**
1. Use `--all-classes` flag to bypass filter
2. Edit config to set `target_classes: []` (detect all)
3. Add specific objects to target_classes list

**Other checks:**
1. Lower confidence: use `--confidence 0.25`
2. Object presentation (see small objects guide)
3. Press `O` to make sure YOLO is enabled

### Issue: Too many false detections
**Solution:**
1. Increase confidence_threshold to 0.6-0.7
2. Use target_classes to filter specific objects
3. Adjust min_object_size to ignore small artifacts

## Example Session Output

```
============================================================
LIVE MOTION DETECTION + OBJECT DETECTION
============================================================
Starting live visualization...
Controls: Q=Quit, R=Reset, S=Screenshot, 1-9=Sensitivity, O=Toggle YOLO

Initializing YOLOv8 object detection...
✓ YOLOv8 initialized successfully
✓ Live view started
Move in front of the camera to trigger motion detection!

[Motion detected]
Objects detected: count=2, objects=['person 0.87', 'cell phone 0.62'], inference_ms=645.3

[User presses S]
💾 Screenshot saved: screenshot_0001.jpg

[User presses O]
YOLO detection: OFF

[User presses Q]
Quit requested

============================================================
SESSION STATISTICS
============================================================
Total frames: 523
Motion detected: 47 times
Detection rate: 9.0%
Screenshots saved: 1

OBJECT DETECTION STATISTICS
Objects detected: 45 times
Avg inference time: 678.2ms
```

## Next Steps

1. ✅ **Done:** YOLOv8 integration complete
2. **Next:** Integrate with notification system (get alerts when specific objects detected)
3. **Next:** Add event logging to database
4. **Next:** Build web dashboard to review detections

## References

- **YOLOv8 Documentation:** https://docs.ultralytics.com/
- **Model Details:** Using YOLOv8s (small) variant
- **Classes:** COCO dataset (80 classes)
- **Performance:** Optimized for Raspberry Pi 5 with 16GB RAM

