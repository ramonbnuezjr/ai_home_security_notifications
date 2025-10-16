# Technical Specifications

## Hardware Requirements

### Primary Hardware
- **Raspberry Pi 5**: 16GB RAM model (confirmed)
- **Pi Camera Module**: Official Raspberry Pi Camera Module 3 or compatible
- **Storage**: 
  - Primary: 64GB+ microSD card (Class 10, A2 rating) OR
  - Alternative: 128GB+ SSD with USB 3.0 adapter (recommended for better performance)
- **Power Supply**: Official Pi 5 power supply (27W) or equivalent
- **Cooling**: Active cooling solution required for sustained AI workloads with 16GB model

### Optional Hardware
- **Case**: Official Pi 5 case with cooling fan
- **Network**: Ethernet cable for stable connection
- **Storage Expansion**: External USB drive for extended video retention

### Performance Considerations
- **CPU**: Quad-core ARM Cortex-A76 @ 2.4GHz
- **GPU**: VideoCore VII GPU for hardware-accelerated video processing
- **Memory**: 16GB LPDDR4X-4267 for AI model loading
- **Storage I/O**: SSD recommended for better video write performance

## Software Stack

### Operating System
- **Base OS**: Raspberry Pi OS (64-bit) - Bookworm or later
- **Kernel**: Linux 6.1+ with hardware acceleration support
- **Python**: 3.11+ (system default)

### Core Dependencies
```yaml
system_packages:
  - python3-pip
  - python3-venv
  - python3-picamera2  # Native Pi camera library (REQUIRED for Pi Camera)
  - ffmpeg
  - libhdf5-dev
  - libatlas-base-dev
  - libjasper-dev
  - libqtgui4
  - libqt4-test
  - python3-pyqt5

python_packages:
  - opencv-python>=4.8.0  # For image processing (not camera capture)
  - numpy>=1.24.0
  - pillow>=10.0.0
  - sqlite3 (built-in)
  - requests>=2.31.0
  - pyyaml>=6.0
  - openai-whisper>=20231117  # Whisper small model
  - ultralytics>=8.0.0  # YOLOv8s
  - transformers>=4.35.0  # For Llama model
  - torch>=2.1.0  # PyTorch for model inference
  - bitsandbytes>=0.41.0  # For 4-bit quantization
  - accelerate>=0.24.0  # For optimized loading
  - redis>=4.5.0
  - flask>=2.3.0
  - gunicorn>=21.0.0

note:
  - Virtual environment must be created with --system-site-packages flag
  - This allows access to system-installed picamera2 while maintaining isolated Python packages
```

### Development Tools
- **IDE**: VS Code with Python extension
- **Version Control**: Git 2.40+
- **Testing**: pytest, pytest-cov
- **Linting**: flake8, black, mypy
- **Monitoring**: htop, iotop, nethogs

## AI Model Selection

### Camera Capture
- **Library**: picamera2 (native Raspberry Pi camera interface)
- **Backend**: libcamera with Pi ISP (Image Signal Processor)
- **Resolution**: 1920x1080 @ 15 FPS (configurable)
- **Format**: RGB888 (converted to BGR for OpenCV compatibility)
- **Performance**: ~20 FPS capture rate, 40ms frame time

### Motion Detection Algorithm
- **Primary**: Background Subtraction (MOG2) with OpenCV
- **Alternative**: Frame differencing with adaptive thresholding
- **Performance Target**: <50ms processing time per frame
- **Note**: OpenCV used for processing, not camera capture

### Object Classification Model
- **Primary**: YOLOv8s (small) - leveraging 16GB RAM for better accuracy
- **Alternative**: YOLOv8n (nano) for faster inference if needed
- **Fallback**: MobileNetV3 for CPU-only inference
- **Model Size**: <100MB (16GB RAM allows larger models)
- **Accuracy Target**: >90% mAP on common security scenarios

### Voice Processing (Whisper)
- **Model**: Whisper small (244M parameters) - taking advantage of 16GB RAM
- **Alternative**: Whisper base (74M parameters) for faster processing
- **Language**: English (primary), multilingual support
- **Processing**: CPU-based inference with optimizations
- **Latency Target**: <3 seconds for 10-second audio clips

### Language Model (Optional Enhanced Features)
- **Primary**: Llama 3.2 3B (quantized to 4-bit) - for intelligent event descriptions
- **Alternative**: TinyLlama 1.1B (already installed, can be used for basic descriptions)
- **Use Case**: Generate natural language descriptions of security events
- **Memory Footprint**: ~2-3GB for Llama 3.2 3B quantized
- **Note**: With 16GB RAM, we can run YOLOv8s + Whisper small + Llama 3B simultaneously

## Performance Targets

### Real-time Processing
- **Video Resolution**: 1920x1080 @ 15 FPS (configurable)
- **Motion Detection Latency**: <100ms end-to-end
- **Classification Latency**: <500ms per detection
- **Notification Delivery**: <5 seconds from detection to delivery

### Resource Utilization Limits
- **CPU Usage**: <80% sustained load
- **Memory Usage**: <14GB peak (leaving 2GB for system, comfortably supporting multiple AI models)
- **Storage I/O**: <50MB/s sustained write
- **Network Bandwidth**: <1Mbps average (notifications only)

### Memory Allocation Strategy (16GB Total)
- **System/OS**: ~1-2GB
- **YOLOv8s Model**: ~20MB loaded, ~500MB inference
- **Whisper Small**: ~1GB loaded
- **Llama 3.2 3B (4-bit)**: ~2-3GB loaded
- **Video Buffers**: ~500MB
- **Application**: ~1GB
- **Available Headroom**: ~6-8GB for peak loads

### Quality Metrics
- **False Positive Rate**: <5% for motion detection
- **Detection Accuracy**: >90% for human detection
- **System Uptime**: >99% availability
- **Storage Efficiency**: <1GB/day for typical usage

## API Specifications

### Internal Service APIs
```yaml
camera_service:
  endpoints:
    - GET /camera/status
    - POST /camera/start
    - POST /camera/stop
    - GET /camera/stream

detection_service:
  endpoints:
    - POST /detection/process_frame
    - GET /detection/config
    - POST /detection/config

ai_service:
  endpoints:
    - POST /ai/classify
    - GET /ai/models
    - POST /ai/models/load

notification_service:
  endpoints:
    - POST /notify/send
    - GET /notify/history
    - POST /notify/test
```

### External Notification APIs
- **Email**: SMTP (Gmail, Outlook, custom SMTP)
- **SMS**: Twilio API, AWS SNS
- **Push Notifications**: Firebase Cloud Messaging
- **Voice**: Text-to-Speech via local synthesis

### Data Formats
```yaml
detection_event:
  timestamp: ISO 8601
  confidence: float (0.0-1.0)
  bounding_box: [x, y, width, height]
  classification: string
  image_path: string

notification_payload:
  event_id: string
  timestamp: ISO 8601
  severity: enum [low, medium, high, critical]
  message: string
  channels: array of strings
  attachments: array of file paths
```

## Configuration Management

### Environment Variables
```bash
# System Configuration
PI_CAMERA_INDEX=0
VIDEO_RESOLUTION=1920x1080
VIDEO_FPS=15
STORAGE_PATH=/home/pi/security_data

# AI Model Configuration
YOLO_MODEL_PATH=/home/pi/models/yolov8n.pt
WHISPER_MODEL_SIZE=base
CONFIDENCE_THRESHOLD=0.5

# Notification Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
NOTIFICATION_EMAIL=user@example.com
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

### Configuration File Structure
- **Primary Config**: `config/system_config.yaml`
- **Environment Overrides**: `.env` file
- **Runtime Config**: Database-stored user preferences
- **Backup Strategy**: Versioned configuration backups

## Security Specifications

### Authentication & Authorization
- **Admin Access**: Multi-factor authentication required
- **API Security**: JWT tokens with expiration
- **Network Security**: TLS 1.3 for all external communications
- **Local Access**: SSH key-based authentication only

### Data Protection
- **Encryption at Rest**: Optional LUKS disk encryption
- **Encryption in Transit**: TLS for all network communications
- **Key Management**: Hardware security module (HSM) integration
- **Audit Logging**: Comprehensive access and modification logs

### Privacy Compliance
- **Data Minimization**: Only essential data collected and stored
- **Retention Policies**: Configurable data retention with automatic cleanup
- **User Rights**: Data export and deletion capabilities
- **Consent Management**: Granular privacy controls
