# Deployment Guide

## Pi 5 Setup and Installation

### Hardware Preparation

#### Required Hardware
- Raspberry Pi 5 (16GB RAM recommended)
- Pi Camera Module 3 or compatible
- 64GB+ microSD card (Class 10, A2 rating) OR 128GB+ SSD with USB 3.0 adapter
- Official Pi 5 power supply (27W)
- Active cooling solution (fan + heatsink)
- Ethernet cable
- Case (optional but recommended)

#### Hardware Assembly
1. **Install Cooling Solution**
   ```bash
   # Install heatsink and fan before first boot
   # Follow manufacturer instructions for your cooling solution
   ```

2. **Connect Camera Module**
   ```bash
   # Connect camera ribbon cable to Pi 5 camera connector
   # Ensure proper orientation and secure connection
   ```

3. **Insert Storage Device**
   ```bash
   # Insert microSD card or connect SSD via USB 3.0
   # Ensure proper mounting
   ```

### Operating System Installation

#### Download and Flash OS
1. **Download Raspberry Pi OS**
   - Go to [Raspberry Pi OS Downloads](https://www.raspberrypi.org/downloads/)
   - Download Raspberry Pi OS (64-bit) Bookworm or later
   - Use Raspberry Pi Imager for flashing

2. **Flash OS to Storage**
   ```bash
   # Using Raspberry Pi Imager
   # Select Raspberry Pi OS (64-bit)
   # Choose storage device
   # Configure advanced options:
   #   - Enable SSH with public key
   #   - Set hostname: security-pi
   #   - Enable WiFi (optional)
   # Flash image
   ```

3. **Initial Boot Configuration**
   ```bash
   # Boot Pi 5 and connect via SSH
   ssh pi@security-pi.local
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Enable camera interface
   sudo raspi-config
   # Navigate to Interface Options > Camera > Enable
   
   # Enable I2C (if needed for sensors)
   sudo raspi-config
   # Navigate to Interface Options > I2C > Enable
   
   # Reboot
   sudo reboot
   ```

### System Configuration

#### User and Security Setup
```bash
# Create dedicated user for security system
sudo adduser security
sudo usermod -aG sudo security
sudo usermod -aG video security
sudo usermod -aG gpio security

# Switch to security user
su - security

# Generate SSH key pair
ssh-keygen -t ed25519 -C "security@pi5"
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
```

#### Network Configuration
```bash
# Configure static IP (optional)
sudo nano /etc/dhcpcd.conf

# Add at end of file:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# Restart networking
sudo systemctl restart dhcpcd
```

#### Firewall Configuration
```bash
# Install UFW
sudo apt install ufw -y

# Configure firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Check status
sudo ufw status
```

### Software Installation

#### Python Environment Setup
```bash
# Install Python 3.11+ and pip
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip -y

# Install system dependencies (including picamera2)
sudo apt install -y \
    python3-picamera2 \
    libhdf5-dev \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    python3-pyqt5 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgtk2.0-dev \
    libcanberra-gtk* \
    ffmpeg

# Create project directory
mkdir -p /home/security/ai_home_security_notifications
cd /home/security/ai_home_security_notifications

# Clone repository
git clone <repository-url> .

# Create virtual environment with system site packages (for picamera2 access)
python3.11 -m venv --system-site-packages venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Install Python Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Install AI/ML dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics
pip install opencv-python
pip install whisper

# Install additional dependencies
pip install flask gunicorn redis sqlalchemy
pip install twilio requests pyyaml
pip install pytest pytest-cov flake8 black mypy
```

#### Camera Testing
```bash
# Test camera detection (Pi 5 uses libcamera, not vcgencmd)
libcamera-hello --list-cameras

# Expected output should show your camera (e.g., imx708)

# Test camera capture with libcamera
libcamera-still -o test_image.jpg

# Test camera with picamera2 (Python)
python3 -c "
from picamera2 import Picamera2
import time

print('Initializing camera...')
picam2 = Picamera2()
config = picam2.create_still_configuration()
picam2.configure(config)
picam2.start()
time.sleep(2)
picam2.capture_file('picamera2_test.jpg')
picam2.stop()
print('✓ Camera working! Image saved to picamera2_test.jpg')
"

# Test with camera service
source venv/bin/activate
python scripts/test_camera.py --test basic
```

### Service Configuration

#### Create Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/security-system.service

# Add content:
[Unit]
Description=AI Home Security Notifications System
After=network.target

[Service]
Type=simple
User=security
Group=security
WorkingDirectory=/home/security/ai_home_security_notifications
Environment=PATH=/home/security/ai_home_security_notifications/venv/bin
ExecStart=/home/security/ai_home_security_notifications/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable security-system
sudo systemctl start security-system

# Check status
sudo systemctl status security-system
```

#### Create Log Rotation
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/security-system

# Add content:
/home/security/ai_home_security_notifications/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 security security
    postrotate
        systemctl reload security-system
    endscript
}
```

### Configuration Setup

#### Copy Configuration Template
```bash
# Copy configuration template
cp config/system_config.yaml config/production_config.yaml

# Edit production configuration
nano config/production_config.yaml

# Key settings to configure:
# - Camera settings (resolution, FPS)
# - Detection sensitivity
# - Notification settings (email, SMS)
# - Storage paths
# - Security settings
```

#### Environment Variables
```bash
# Create environment file
nano .env

# Add production environment variables:
DEBUG=false
LOG_LEVEL=INFO
CONFIG_FILE=config/production_config.yaml
DATABASE_URL=sqlite:///data/security.db
STORAGE_PATH=/home/security/security_data
```

#### Create Data Directories
```bash
# Create data directories
mkdir -p /home/security/security_data/{videos,images,logs,models}
mkdir -p /home/security/security_data/backups

# Set permissions
chmod 755 /home/security/security_data
chmod 755 /home/security/security_data/*
```

### AI Model Setup

#### Download YOLOv8 Model
```bash
# Download YOLOv8 small model (leveraging 16GB RAM)
cd /home/security/security_data/models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

# Download YOLOv8 nano as fallback
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# Test model loading
python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8s.pt')
print('YOLOv8s model loaded successfully!')
print(f'Model parameters: {sum(p.numel() for p in model.model.parameters())}')
"
```

#### Download Whisper Model
```bash
# Download Whisper small model (better accuracy with 16GB RAM)
python3 -c "
import whisper
model = whisper.load_model('small')
print('Whisper small model loaded successfully!')
print(f'Model size: {sum(p.numel() for p in model.parameters())} parameters')
"

# Also download base as fallback
python3 -c "
import whisper
model = whisper.load_model('base')
print('Whisper base model downloaded as fallback!')
"
```

#### Download Language Model (Optional - for enhanced descriptions)
```bash
# Download Llama 3.2 3B quantized (optional feature)
python3 -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_name = 'meta-llama/Llama-3.2-3B'
print('Downloading Llama 3.2 3B model (this may take a while)...')

# Note: TinyLlama is already installed as fallback
# This step is optional and can be skipped initially
"
```

### Web Interface Setup

#### Install Web Server
```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/security-system

# Add content:
server {
    listen 80;
    server_name security-pi.local;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/security/ai_home_security_notifications/static;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/security-system /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Monitoring and Maintenance

#### System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Create monitoring script
nano /home/security/monitor.sh

# Add content:
#!/bin/bash
echo "=== System Status ==="
echo "Date: $(date)"
echo "Uptime: $(uptime)"
echo "CPU Temperature: $(vcgencmd measure_temp)"
echo "Memory Usage: $(free -h)"
echo "Disk Usage: $(df -h /)"
echo "Service Status: $(systemctl is-active security-system)"
echo "===================="

# Make executable
chmod +x /home/security/monitor.sh

# Add to crontab for regular monitoring
crontab -e

# Add line:
# */5 * * * * /home/security/monitor.sh >> /home/security/monitor.log
```

#### Backup Configuration
```bash
# Create backup script
nano /home/security/backup.sh

# Add content:
#!/bin/bash
BACKUP_DIR="/home/security/security_data/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/config_backup_$DATE.tar.gz" \
    config/ \
    .env \
    /etc/systemd/system/security-system.service \
    /etc/nginx/sites-available/security-system

# Keep only last 7 backups
find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: config_backup_$DATE.tar.gz"

# Make executable
chmod +x /home/security/backup.sh

# Add to crontab for daily backups
crontab -e

# Add line:
# 0 2 * * * /home/security/backup.sh
```

### Troubleshooting

#### Common Issues and Solutions

**Camera Not Detected:**
```bash
# Check camera connection
vcgencmd get_camera

# If not detected:
# 1. Check physical connection
# 2. Enable camera in raspi-config
# 3. Reboot system
```

**Service Won't Start:**
```bash
# Check service logs
sudo journalctl -u security-system -f

# Check service status
sudo systemctl status security-system

# Restart service
sudo systemctl restart security-system
```

**High CPU Usage:**
```bash
# Check running processes
htop

# Check system temperature
vcgencmd measure_temp

# If overheating:
# 1. Check cooling solution
# 2. Reduce AI model complexity
# 3. Lower video resolution/FPS
```

**Storage Full:**
```bash
# Check disk usage
df -h

# Clean up old files
find /home/security/security_data -name "*.jpg" -mtime +7 -delete
find /home/security/security_data -name "*.mp4" -mtime +3 -delete

# Run cleanup script
python3 cleanup_storage.py
```

**Network Issues:**
```bash
# Check network connectivity
ping google.com

# Check firewall status
sudo ufw status

# Check service ports
netstat -tlnp | grep :5000
```

### Performance Optimization

#### System Optimization
```bash
# Increase GPU memory split
sudo nano /boot/config.txt

# Add/modify:
gpu_mem=128

# Optimize for performance
sudo nano /boot/config.txt

# Add:
arm_freq=2400
over_voltage=2
gpu_freq=750
```

#### Application Optimization
```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable hciuart
```

### Security Hardening

#### Additional Security Measures
```bash
# Disable root login
sudo nano /etc/ssh/sshd_config

# Set:
PermitRootLogin no
PasswordAuthentication no

# Restart SSH
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban -y

# Configure fail2ban
sudo nano /etc/fail2ban/jail.local

# Add:
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

# Start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Maintenance Schedule

#### Daily Tasks
- [ ] Check system status and logs
- [ ] Monitor disk usage
- [ ] Verify camera functionality
- [ ] Check notification delivery

#### Weekly Tasks
- [ ] Review security logs
- [ ] Update system packages
- [ ] Clean temporary files
- [ ] Test backup procedures

#### Monthly Tasks
- [ ] Full system backup
- [ ] Security audit
- [ ] Performance review
- [ ] Update AI models (if needed)

#### Quarterly Tasks
- [ ] Hardware inspection
- [ ] Complete system test
- [ ] Documentation review
- [ ] Disaster recovery test
