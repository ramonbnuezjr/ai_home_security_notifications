# Quick Start Guide - Motion Detection + YOLOv8

## Status: ✅ READY TO TEST!

Your AI Home Security system with YOLOv8 object detection is fully operational!

## What's Working

- ✅ **Camera**: Pi Camera Module (IMX708) @ 1920x1080, 15 FPS
- ✅ **Motion Detection**: MOG2 background subtraction algorithm
- ✅ **Object Detection**: YOLOv8s (80 classes) with ~500-1000ms inference
- ✅ **Integration**: YOLO only runs when motion is detected (efficient!)

## Prerequisites

Before running the system, ensure you have:
1. **Downloaded the YOLO model:**
   ```bash
   cd /home/ramon/ai_projects/ai_home_security_notifications
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt
   ```
   *Note: The model file is ~20MB and not included in the git repository.*

2. **Activated the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

## Run the System

### Option 1: Full System (Motion + YOLO)

```bash
cd /home/ramon/ai_projects/ai_home_security_notifications
source venv/bin/activate
python scripts/live_motion_detection.py
```

**Requirements:** Display connected (HDMI/VNC) - won't work over SSH  
**Performance:** ~1-2 FPS during object detection (normal for Pi 5 CPU)

### Option 2: Faster YOLO (Recommended for Smooth Live View)

```bash
python scripts/live_motion_detection.py --yolo-skip 2
```

**Performance:** Smoother ~15-20 FPS, runs YOLO every 3rd motion frame

### Option 3: Lower Confidence (Detect More Objects)

```bash
python scripts/live_motion_detection.py --confidence 0.25
```

**Performance:** Same speed, but detects smaller/less obvious objects

### Option 4: Motion Only (Fastest)

```bash
python scripts/live_motion_detection.py --no-yolo
```

**Performance:** Real-time 30 FPS, no object classification

### Option 5: Remote Testing (No Display)

```bash
python scripts/test_object_detection.py --confidence 0.25
```

This will save detected object frames to disk (works over SSH).

## How to Test (With Display)

1. **Start the system:**
   ```bash
   python scripts/live_motion_detection.py
   ```

2. **Initial setup (important!):**
   - **Stay still for 2-3 seconds** - lets algorithm learn background
   - You'll see "YOLO: ON" in bottom right corner

3. **Trigger detection:**
   - **Wave your hand** - motion boxes appear (gray)
   - **Wait a second** - YOLO analyzes the motion
   - **Green box appears** with "person 0.XX" label!

4. **Try different scenarios:**
   - Walk around - tracks multiple objects
   - Hold your phone - detects "person" + "cell phone"
   - Adjust sensitivity: Press **3** (low), **7** (medium), **9** (high)

## Interactive Controls

| Key | Action |
|-----|--------|
| **Q** | Quit |
| **O** | Toggle YOLO on/off (temporarily disable for speed) |
| **S** | Save screenshot |
| **R** | Reset motion detector |
| **1-9** | Adjust sensitivity (1=10%, 9=90%) |
| **M** | Toggle motion mask window |

## Command Line Options

| Flag | Description | Example |
|------|-------------|---------|
| `--confidence 0.25` | Lower detection threshold (default: 0.5) | Detects more objects |
| `--yolo-skip 2` | Run YOLO every 3rd frame | Smoother live view |
| `--all-classes` | Detect all 80 classes | Overrides config filter |
| `--no-yolo` | Disable YOLO entirely | 30 FPS motion only |
| `--fps 15` | Limit display FPS | Reduce CPU usage |

## Expected Performance

- **Motion Detection:** Real-time, ~30 FPS (no slowdown)
- **YOLO First Detection:** ~3-4 seconds (model warmup, one-time)
- **YOLO Subsequent:** ~0.5-1.0 seconds per detection
- **Live View with YOLO:** ~1-2 FPS during detection (expected on Pi 5 CPU)
- **With Frame Skip:** ~15-20 FPS (smoother, use `--yolo-skip 2`)
- **CPU Usage:** ~50-70% during YOLO inference
- **Memory:** ~2-3 GB with YOLOv8s model loaded

**Note:** The slowdown during YOLO is normal! Pi 5 runs inference on CPU (no GPU acceleration). The system is designed to run motion detection fast and only trigger YOLO when needed.

## What Objects Can It Detect?

YOLOv8 detects **80 different objects** including:

**Most Common for Security:**
- person, car, truck, bus, motorcycle, bicycle

**Animals:**
- cat, dog, bird, horse, cow, sheep

**Common Items:**
- cell phone, laptop, backpack, handbag, umbrella, bottle

Run `python scripts/test_yolo.py` to see the full list.

## Troubleshooting

### "could not connect to display"
**Cause:** Running over SSH without X11 forwarding  
**Solution:** Run on Pi with display connected, or use VNC, or test with `test_motion_detection.py`

### "YOLO not initializing"
**Cause:** Model not downloaded or package issue  
**Solution:**
```bash
source venv/bin/activate
python scripts/test_yolo.py
```

### Slow frame rate with YOLO
**This is normal!** YOLO takes ~0.5-1.0 seconds per inference on Pi 5 CPU.  
**Solutions:**
- Use frame skipping: `--yolo-skip 2` (smoother live view)
- Switch to yolov8n model (faster inference)
- Toggle YOLO off temporarily (press `O` key)
- Accept the slowdown (accuracy vs speed trade-off)

### No objects detected
**Possible issues:**
1. YOLO might be off - press **O** to toggle
2. Confidence threshold too high - edit `config/system_config.yaml`
3. Object not in target classes - check configuration

## Configuration Tips

Edit `config/system_config.yaml` to customize:

```yaml
# Current config: Detects all 80 object classes
classification:
  target_classes: []  # Empty = detect all classes
  ignore_classes: []  # No filtering
  
# For security camera (filter to relevant objects only)
classification:
  target_classes: ["person", "car", "backpack"]  # Only these objects
  
# Adjust detection confidence
yolo:
  confidence_threshold: 0.5  # Lower = more detections
  
# Use faster model (better performance)
yolo:
  model_variant: "yolov8n"  # Faster inference (~300-500ms vs 500-1000ms)
```

## Remote Testing (Without Display)

If you can't connect a display, you can still test:

```bash
# Test motion detection (saves frames to disk)
python scripts/test_motion_detection.py

# Check saved frames
ls -lh motion_test_output/

# View with scp/sftp from another machine
# Or serve via Python:
cd motion_test_output
python3 -m http.server 8000
# Then browse to http://<pi-ip>:8000
```

## System Architecture

```
┌─────────────┐
│   Camera    │
│ (Pi Camera) │
└──────┬──────┘
       │ 1920x1080 @ 15 FPS
       ▼
┌─────────────────────┐
│ Motion Detection    │
│ (MOG2 Algorithm)    │
└──────┬──────────────┘
       │ Motion detected?
       ▼
┌─────────────────────┐
│ YOLOv8 Detection   │ ◄── Only runs when motion detected
│ (80 object classes) │
└──────┬──────────────┘
       │ Classified objects
       ▼
┌─────────────────────┐
│ Live Display        │
│ (Bounding boxes +   │
│  Labels)           │
└─────────────────────┘
```

## Example Output

When you walk in front of the camera:

```
Motion detected: 2 regions, 15.3% of frame
Objects detected: person (0.87), cell phone (0.62)
Inference time: 645ms
```

Visual display shows:
- Gray boxes around motion regions
- **Green box** with "person 0.87" label
- Blue box with "cell phone 0.62" label
- Info panel with statistics

## Next Steps

Once you've tested the current system, you can:

1. **Smart Notifications** - Get alerts when specific objects detected
2. **Event Logging** - Save detections to database
3. **Web Dashboard** - View detection history remotely
4. **Zone Detection** - Only alert on specific camera areas
5. **Scheduling** - Enable detection only at certain times

## Need Help?

- **Full Documentation:** See `YOLO_INTEGRATION_GUIDE.md`
- **Camera Issues:** Run `python scripts/test_camera.py`
- **YOLO Issues:** Run `python scripts/test_yolo.py`
- **Motion Detection Issues:** Run `python scripts/test_motion_detection.py`

---

**🎉 Your system is ready! Start with the basic test and explore from there.**

