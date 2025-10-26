# Proposed Future Epics

## 🎯 High Priority Epics (Phase 2)

### Epic 7: Advanced Audio Capabilities 🎙️
**Goal:** Enhanced audio input/output for better security monitoring

#### USB Speaker Integration
- **Status:** Ready to implement
- **Why:** HAL voice notifications work great, but built-in audio quality is limited
- **Tasks:**
  - [ ] Auto-detect USB audio devices
  - [ ] Route HAL voice through USB speakers (better quality)
  - [ ] Configure ALSA for USB audio devices
  - [ ] Test with multiple audio outputs (built-in + USB)
  - [ ] Volume control and testing interface

#### USB Microphone Integration
- **Status:** New capability - voice commands
- **Why:** Enable voice control and audio event detection
- **Tasks:**
  - [ ] Auto-detect USB microphones
  - [ ] Noise level monitoring for audio events
  - [ ] Voice command recognition (optional)
  - [ ] Audio event logging (dog barking, door slams, etc.)
  - [ ] Sync audio with video events

**Estimated Effort:** 2-3 weeks  
**Dependencies:** None  
**Tools:** ALSA, alsamixer, picamera2 (already have)

---

### Epic 8: Face Recognition for Family Members 👨‍👩‍👦‍👦
**Goal:** Recognize specific people (you, wife, two sons, dog)

#### Face Recognition Pipeline
- **Status:** Requires model training
- **Why:** Reduce false alarms, personalized notifications
- **Tasks:**
  - [ ] Collect training data for each family member (~50-100 images per person)
  - [ ] Train face recognition model (FaceNet or similar)
  - [ ] Integrate with YOLO detection (person → face recognition)
  - [ ] Create family member database
  - [ ] Train pet detection separately (different model)

#### Configuration Interface
- **Status:** Requires UI work
- **Tasks:**
  - [ ] Add family member management to web dashboard
  - [ ] Photo upload interface for training
  - [ ] Name tagging for recognized faces
  - [ ] Confidence thresholds per person
  - [ ] Privacy controls (store/delete face data)

**Estimated Effort:** 4-6 weeks  
**Dependencies:** Require training data from family  
**Models:** FaceNet (recommended), Face Recognition library, or train custom

**Recommended Approach:**
1. Start with `face_recognition` library (pre-trained, easy to use)
2. Capture training photos via web dashboard
3. Migrate to FaceNet for better accuracy later

---

### Epic 9: Offline Storage & Privacy 🔒
**Goal:** Store video/images locally with encryption, no cloud

#### Local Encrypted Storage
- **Status:** Partially done (we store locally already)
- **Why:** Full privacy control, meet GDPR requirements
- **Tasks:**
  - [ ] Implement automatic encryption of stored video/images
  - [ ] Key management system for decryption
  - [ ] Automatic deletion based on retention policies
  - [ ] Export encrypted archives
  - [ ] Disk space monitoring and cleanup

#### Privacy Controls
- **Status:** Needs implementation
- **Tasks:**
  - [ ] Add data retention policies (keep 7 days, 30 days, etc.)
  - [ ] Manual deletion interface
  - [ ] Data export to encrypted ZIP
  - [ ] Face data deletion (for Epic 8)
  - [ ] Audit log of data access

**Estimated Effort:** 2-3 weeks  
**Dependencies:** Encryption service (Epic 6 foundation exists)  
**Tools:** LUKS, Fernet, disk encryption

---

### Epic 10: Hardware Optimizations & Case Selection 💪
**Goal:** Professional case, cooling, NVMe storage

#### Case Selection: Pironman 5-MAX
- **Why:** Dual NVMe M.2 slots, professional cooling, robust build
- **Tasks:**
  - [ ] Order and test Pironman 5-MAX case
  - [ ] Install NVMe drives (boot + data drive)
  - [ ] Performance testing vs SD card
  - [ ] Cooling system validation
  - [ ] Installation guide

**Benefits:**
- Faster boot times (NVMe)
- Higher write speeds for video recording
- Better thermal management
- Professional appearance
- Dual NVMe slots for redundancy

#### Active Cooling
- **Status:** May be needed with AI HAT
- **Tasks:**
  - [ ] Temperature monitoring integration (Netdata)
  - [ ] Automatic throttle detection
  - [ ] Cooling configuration guide
  - [ ] Thermal paste application

**Estimated Effort:** 1-2 weeks  
**Cost:** ~$50-80 for Pironman case

---

## ⚡ Medium Priority Epics (Phase 3)

### Epic 11: AI HAT Integration (Hailo-8L) 🚀
**Goal:** Offload YOLO processing to dedicated AI chip (20-30 FPS)

#### Hailo AI HAT+ Integration
- **Status:** Hardware upgrade
- **Why:** 15-30x faster YOLO inference
- **Current:** 1-2 FPS (CPU bottleneck)
- **Target:** 20-30 FPS with AI HAT

#### Implementation Tasks:
- [ ] Purchase AI HAT+ (~$70)
- [ ] Install hardware (M.2 slot)
- [ ] Install Hailo drivers
- [ ] Convert YOLOv8 model to Hailo format
- [ ] Update inference pipeline to use Hailo API
- [ ] Performance benchmarking
- [ ] Power consumption analysis
- [ ] Integration testing with HAL voice, notifications

**Estimated Effort:** 2-3 weeks  
**Cost:** ~$70 for hardware  
**Impact:** Huge performance boost, enables real-time detection

**Resources:**
- [Raspberry Pi AI HAT+ Docs](https://www.raspberrypi.com/documentation/computers/ai-hat-plus.html)
- Jeff Geerling AI HAT review video

---

### Epic 12: Touchscreen Display Integration 📱
**Goal:** Local display with touch controls for on-device monitoring

#### Hardware Options:
1. **SunFounder 3.5 Inch 480x320 Touch Screen**
   - Small, portable
   - SPI interface
   - Good for status display

2. **SunFounder Picar-X AI (Full Package)**
   - Complete robotic platform
   - Multiple sensors
   - Could pivot to robotics project

3. **SunFounder Latest 10 Inch DIY Touch Screen**
   - Larger display
   - Better for detailed information
   - More expensive

#### Implementation Tasks:
- [ ] Choose display based on use case
- [ ] Install display drivers
- [ ] Create local dashboard (Qt/Flask)
- [ ] Touch interface for controls
- [ ] Live video display
- [ ] Event history viewing
- [ ] System configuration UI

**Estimated Effort:** 3-4 weeks (depends on display choice)  
**Cost:** $20-150 depending on display  
**Use Case:** Monitor system without network access

---

## 🔬 Experimental Epics (Phase 4)

### Epic 13: Arduino/Microcontroller Version 🔋
**Goal:** Battery-powered version for remote/outdoor monitoring

#### Arduino Compatibility
- **Status:** Complex - would require major rework
- **Why:** Battery power, lower cost, distributed sensors
- **Challenges:**
  - Limited processing power
  - No YOLO capability (too heavy)
  - Would need ESP32-CAM or similar
  - Cloud inference required

#### Feasibility Assessment:
**Option A: ESP32-CAM + Battery**
- Pros: Low cost, wireless, battery powered
- Cons: No local YOLO, requires cloud AI
- Best for: Remote motion sensors (no object detection)

**Option B: Raspberry Pi Zero 2W + Battery Pack**
- Pros: Can run Python, potential for edge AI
- Cons: Limited performance
- Best for: Simplified motion detection only

**Recommended:** Start with Pi Zero 2W experiment, keep Pi 5 as main system

---

### Epic 14: Multi-Device Deployment 🏠
**Goal:** Sync multiple cameras/devices

#### Distributed Architecture
- [ ] Network synchronization protocol
- [ ] Central dashboard aggregating multiple devices
- [ ] Device management interface
- [ ] Load balancing (if using cloud inference)
- [ ] Storage coordination across devices

**Estimated Effort:** 6-8 weeks  
**Complexity:** High - requires architectural redesign

---

## 📊 Recommended Implementation Order

### Phase 2 (Next 8-12 weeks)
1. **Epic 7:** USB Speaker/Mic Integration (week 1-3)
2. **Epic 9:** Offline Storage & Privacy (week 4-6)
3. **Epic 8:** Face Recognition (week 7-10)
4. **Epic 10:** Case & Hardware Optimization (week 11-12)

### Phase 3 (Weeks 13-20)
5. **Epic 11:** AI HAT Integration (week 13-16)
6. **Epic 12:** Touchscreen Display (week 17-20)

### Phase 4 (Experimental)
7. **Epic 13:** Arduino/Battery Version (experimental)
8. **Epic 14:** Multi-Device (if needed)

---

## 💡 Quick Wins (Can start immediately)

1. **USB Speaker Setup** - 1-2 days
   ```bash
   # Test USB speaker
   lsusb | grep -i audio
   aplay -l  # List audio devices
   speakertest -c 2  # Test stereo
   ```

2. **Temperature Monitoring** - Already done (Netdata setup)

3. **NVMe Performance Test** - 1 day
   ```bash
   # Test current storage
   sudo hdparm -tT /dev/mmcblk0
   # vs NVMe when installed
   sudo hdparm -tT /dev/nvme0n1p1
   ```

4. **External Storage for Video** - 2 days
   - Add USB SSD for video storage
   - Update retention policies
   - Auto-mount configuration

---

## 🤔 Questions to Answer

1. **Audio Priority:** USB speakers first (quick win) or USB mic (new capability)?
2. **Face Recognition:** Start simple with library or train custom model?
3. **Case:** Buy Pironman 5-MAX now or wait for AI HAT first?
4. **Touchscreen:** Need local display or happy with web dashboard?
5. **Battery Version:** Priority or experimental/learning project?

---

## 💰 Budget Estimate

| Item | Cost | Priority |
|------|------|----------|
| Pironman 5-MAX Case | ~$70 | High |
| NVMe SSD (512GB) | ~$40 | High |
| AI HAT+ | ~$70 | High |
| USB Speakers | ~$20 | Medium |
| USB Microphone | ~$10 | Medium |
| 3.5" Touchscreen | ~$20 | Low |
| Battery Pack | ~$30 | Experimental |
| **Total (High Priority)** | **~$180** | |

---

## 🎯 Next Steps Recommendation

**Start with Epic 7 (USB Audio)** - Quick wins, builds on existing HAL voice

Then move to **Epic 10 (Case & NVMe)** - Improves base hardware before adding AI HAT

Then tackle **Epic 11 (AI HAT)** - Requires good cooling from new case

Face recognition (Epic 8) can happen in parallel - requires family participation for training data.

