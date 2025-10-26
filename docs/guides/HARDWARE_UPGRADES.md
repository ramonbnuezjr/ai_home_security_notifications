# Hardware Upgrade Guide

## System Monitoring with Netdata

### Real-Time Performance Monitoring

**Install Netdata (recommended):**

```bash
# Update and install
sudo apt-get update
sudo apt-get install netdata -y

# Configure network access
sudo nano /etc/netdata/netdata.conf
```

**Find this line:**
```ini
bind socket to IP = 127.0.0.1
```

**Change to:**
```ini
bind socket to IP = 0.0.0.0
```

**Save and restart:**
```bash
# Save: Ctrl+O, Enter, Ctrl+X
sudo systemctl restart netdata
sudo systemctl enable netdata
```

**Access from your computer:**
```
http://192.168.7.210:19999
```

**What you'll see:**
- ✅ Real-time CPU usage (per core)
- ✅ RAM usage and availability
- ✅ Temperature monitoring (critical for Pi 5)
- ✅ YOLO process performance
- ✅ Network traffic
- ✅ Disk I/O
- ✅ Updates every 1 second

**Benefits:**
- Monitor YOLO's impact on CPU/RAM while it's running
- Watch temperature to prevent throttling
- See which processes are using resources
- Mobile-friendly interface for remote monitoring

**Temperature Alerts:**
```bash
# Edit health config
sudo nano /etc/netdata/health.d/cpu_temp.conf
```

Add alert rules:
```python
alarm: cpu_temperature
   on: cpu.cpu_temperature
 calc: $temperature
every: 10s
 warn: $this > 75
 crit: $this > 80
 info: CPU temperature monitoring
```

---

## Current System Performance

### Pi 5 16GB (CPU-Only) - Current Setup

| Operation | Performance | Notes |
|-----------|-------------|-------|
| Motion Detection | 30 FPS | ✅ Excellent - lightweight algorithm |
| Camera Capture | 1920x1080 @ 19.5 FPS | ✅ Good - camera module limitation |
| YOLO Object Detection | 1-2 FPS | ⚠️ Slow - CPU bottleneck |
| Combined (Motion + YOLO) | 1-2 FPS | ⚠️ Limited by YOLO inference |

**Bottleneck**: YOLOv8s inference takes 500-1000ms per frame on ARM CPU

## Recommended Upgrades

### 🌟 Option 1: AI HAT+ (Hailo-8L) - RECOMMENDED

**Product**: Raspberry Pi AI HAT+ with Hailo-8L NPU

**Specifications**:
- **AI Performance**: 26 TOPS (Tera Operations Per Second)
- **Connector**: M.2 M-key via PCIe 2.0 x1
- **Power**: Powered via Pi 5 GPIO
- **Compatibility**: Raspberry Pi 5 only

**Expected Performance**:
- YOLO Object Detection: **20-30 FPS** 🚀
- Combined Motion + YOLO: **20-30 FPS**
- Power consumption: +3W additional

**Pricing**:
- ~$70 USD
- Available from: Raspberry Pi approved retailers

**Installation**:
1. Power off Pi 5
2. Attach AI HAT+ to M.2 slot (on bottom of Pi 5)
3. Secure with included standoffs
4. Install Hailo drivers:
   ```bash
   sudo apt update
   sudo apt install hailo-all
   ```
5. Convert YOLOv8 model to Hailo format
6. Update configuration to use Hailo backend

**Pros**:
- ✅ Massive performance boost (15-30x faster)
- ✅ Official Pi accessory (good support)
- ✅ Low power consumption
- ✅ Easy to install
- ✅ Doesn't require USB port

**Cons**:
- ❌ Requires model conversion (one-time setup)
- ❌ Pi 5 specific (not compatible with older models)
- ❌ Additional cost

**Links**:
- Product: https://www.raspberrypi.com/products/ai-hat/
- Documentation: https://www.raspberrypi.com/documentation/accessories/ai-hat.html

---

### Option 2: Google Coral USB Accelerator

**Product**: Google Coral USB Accelerator TPU

**Specifications**:
- **AI Performance**: 4 TOPS
- **Connector**: USB 3.0 Type-A
- **Power**: USB powered
- **Compatibility**: Any device with USB

**Expected Performance**:
- YOLO Object Detection: **10-15 FPS** (after conversion)
- Note: Requires TensorFlow Lite model

**Pricing**:
- ~$60 USD
- Available from: Amazon, Adafruit, others

**Installation**:
1. Plug into USB 3.0 port
2. Install Edge TPU runtime:
   ```bash
   echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
   sudo apt update
   sudo apt install libedgetpu1-std python3-pycoral
   ```
3. Convert YOLOv8 to TensorFlow Lite + Edge TPU format
4. Update code to use Coral inference

**Pros**:
- ✅ Works with any USB device
- ✅ Mature ecosystem
- ✅ Good documentation
- ✅ Portable between devices

**Cons**:
- ❌ Requires model conversion to TFLite (more complex)
- ❌ Uses USB port
- ❌ Lower performance than Hailo
- ❌ May require code changes

---

### Option 3: Software Optimizations (Free)

**No hardware purchase required**

#### 3A. Reduce Resolution
```yaml
# config/system_config.yaml
camera:
  resolution:
    width: 640    # Down from 1920
    height: 480   # Down from 1080
```
**Expected gain**: 3-5 FPS (smaller images to process)

#### 3B. Use Smaller YOLO Model
```yaml
# config/system_config.yaml
ai:
  yolo:
    model_variant: "yolov8n"  # Change from yolov8s
```
**Expected gain**: 2-3 FPS (faster but less accurate)

#### 3C. Frame Skipping
```python
# Only run YOLO every N frames
if frame_count % 3 == 0:  # Every 3rd frame
    detection_result = object_detector.detect_objects(frame)
```
**Expected gain**: 3x smoother display, but misses frames

#### 3D. Region of Interest (ROI)
```python
# Only process part of the image
roi = frame[200:800, 300:1200]  # Crop to area of interest
detection_result = object_detector.detect_objects(roi)
```
**Expected gain**: 2-4x faster (smaller area to process)

**Pros**:
- ✅ Free
- ✅ Easy to implement
- ✅ No hardware changes

**Cons**:
- ❌ Limited performance gains (max 5 FPS realistic)
- ❌ Trade-offs in accuracy or coverage
- ❌ Won't reach real-time performance

---

## Comparison Table

| Upgrade | Cost | YOLO FPS | Installation | Effort |
|---------|------|----------|--------------|--------|
| **AI HAT+ (Hailo)** | $70 | 20-30 FPS | Medium | ⭐⭐⭐ RECOMMENDED |
| Google Coral | $60 | 10-15 FPS | Hard | ⭐⭐ |
| Software Tweaks | $0 | 3-5 FPS | Easy | ⭐ |
| No Upgrade | $0 | 1-2 FPS | N/A | Current |

## Our Recommendation

### For This Project: **AI HAT+ (Hailo-8L)**

**Why**:
1. **Best Performance**: 26 TOPS vs Coral's 4 TOPS
2. **Native Support**: Official Pi accessory with good documentation
3. **Easy Integration**: Hailo provides YOLOv8 models pre-converted
4. **Future Proof**: Newest technology, active development
5. **Reasonable Price**: $70 for 15-30x performance increase

**When to Buy**:
- If you want real-time object detection (20-30 FPS)
- If you plan to add more AI features (facial recognition, etc.)
- If you want smooth live video with YOLO enabled
- If budget allows for $70 investment

**When to Wait**:
- If 1-2 FPS is acceptable for your use case
- If only using voice notifications (detection happens, just slow)
- If primarily relying on motion detection (already 30 FPS)
- If budget is tight (system works without it)

## Current System Status

**Your system works great as-is for**:
- ✅ Motion detection (30 FPS)
- ✅ Object detection when motion occurs (works, just slower)
- ✅ Voice notifications (audio announces detections)
- ✅ Event logging and history

**Upgrade will improve**:
- 🚀 Live view smoothness with YOLO
- 🚀 Response time to fast-moving objects
- 🚀 Multiple camera support
- 🚀 More complex AI models

## Installation Priority

```
Priority 1: Get AI HAT+ when budget allows
Priority 2: Optimize software (free, do anytime)
Priority 3: Consider Coral if Hailo unavailable
```

## Future Hardware Roadmap

### Phase 1 (Current)
- ✅ Pi 5 16GB
- ✅ Camera Module 3
- ✅ 64GB microSD / SSD

### Phase 2 (Next - When Budget Allows)
- 🎯 AI HAT+ (Hailo-8L)
- Estimated investment: $70
- Expected improvement: 15-30x AI performance

### Phase 3 (Future)
- Additional camera modules (multi-camera support)
- Better audio output (speaker system)
- UPS backup power
- Larger SSD storage

## References

- Raspberry Pi AI HAT+: https://www.raspberrypi.com/products/ai-hat/
- Hailo-8L Documentation: https://hailo.ai/products/hailo-8l/
- Google Coral: https://coral.ai/products/accelerator/
- Pi 5 Specs: https://www.raspberrypi.com/products/raspberry-pi-5/

---

**Bottom Line**: The system works well now. The AI HAT+ is a great upgrade when you're ready to invest $70 for significantly faster object detection. No rush - your security system is fully operational! 🎉

