# Epic 5: Web Dashboard & Monitoring - Design Document

## Overview
Create a comprehensive web-based interface for monitoring, controlling, and reviewing the security system. The dashboard provides live video feeds, event history, system configuration, and performance monitoring.

## Database Design

### Storage Location
- **Primary Database**: `/mnt/ssd/security_data/database/security.db` (SanDisk SSD)
- **Backup Location**: `/home/ramon/security_data/database/` (SD card fallback)
- **Rationale**: SSD provides faster I/O, reduces SD card wear, and better performance for concurrent reads/writes

### Database Schema

#### 1. Events Table
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'motion', 'object_detected', 'alert'
    severity VARCHAR(20) NOT NULL,     -- 'low', 'medium', 'high', 'critical'
    zone_name VARCHAR(100),
    motion_percentage FLOAT,
    threat_level VARCHAR(20),
    image_path VARCHAR(500),
    video_path VARCHAR(500),
    metadata TEXT,                     -- JSON blob for additional data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity)
);
```

#### 2. Detected Objects Table
```sql
CREATE TABLE detected_objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL,
    bbox_x1 INTEGER,
    bbox_y1 INTEGER,
    bbox_x2 INTEGER,
    bbox_y2 INTEGER,
    threat_level VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    INDEX idx_event_id (event_id),
    INDEX idx_class_name (class_name)
);
```

#### 3. Notifications Table
```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    channel VARCHAR(50) NOT NULL,      -- 'email', 'sms', 'push', 'voice'
    priority VARCHAR(20) NOT NULL,     -- 'low', 'medium', 'high', 'critical'
    status VARCHAR(20) NOT NULL,       -- 'pending', 'sent', 'failed'
    sent_at DATETIME,
    error_message TEXT,
    metadata TEXT,                     -- JSON blob
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    INDEX idx_event_id (event_id),
    INDEX idx_status (status),
    INDEX idx_sent_at (sent_at)
);
```

#### 4. System Metrics Table
```sql
CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_usage FLOAT,
    temperature FLOAT,
    fps FLOAT,
    yolo_inference_time FLOAT,
    active_services TEXT,              -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp)
);
```

#### 5. Configuration History Table
```sql
CREATE TABLE config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    config_section VARCHAR(100),
    changes TEXT NOT NULL,             -- JSON blob of changes
    changed_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp)
);
```

#### 6. Users Table (for Epic 6, but included now)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',  -- 'admin', 'user', 'viewer'
    is_active BOOLEAN DEFAULT 1,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);
```

## Web Application Architecture

### Technology Stack
- **Backend Framework**: Flask 3.0+
- **Database**: SQLite 3 with JSON1 extension
- **Video Streaming**: MJPEG over HTTP (simple, no WebRTC needed initially)
- **Frontend**: Vanilla JavaScript + modern CSS (no framework, keep it lightweight)
- **API Style**: RESTful JSON API
- **Real-time Updates**: Server-Sent Events (SSE) for live notifications

### Application Structure
```
src/web/
├── __init__.py
├── app.py                    # Flask application factory
├── api/
│   ├── __init__.py
│   ├── events.py            # Event endpoints
│   ├── stream.py            # Video streaming
│   ├── config.py            # Configuration endpoints
│   ├── metrics.py           # System metrics
│   └── notifications.py     # Notification history
├── templates/
│   ├── base.html            # Base template
│   ├── dashboard.html       # Main dashboard
│   ├── events.html          # Event history
│   ├── settings.html        # System configuration
│   └── monitoring.html      # System monitoring
├── static/
│   ├── css/
│   │   ├── main.css         # Main styles
│   │   └── dashboard.css    # Dashboard-specific
│   ├── js/
│   │   ├── dashboard.js     # Dashboard logic
│   │   ├── events.js        # Event viewer
│   │   └── api.js           # API client
│   └── images/
│       └── logo.png
└── middleware/
    ├── __init__.py
    └── auth.py              # Authentication (Epic 6)
```

### Database Service
```
src/services/
└── database_service.py      # Database operations
```

## API Endpoints

### Events API
- `GET /api/events` - List events (with pagination, filters)
  - Query params: `?page=1&limit=50&event_type=motion&severity=high&start_date=2025-01-01`
- `GET /api/events/{id}` - Get specific event
- `GET /api/events/stats` - Get event statistics
- `DELETE /api/events/{id}` - Delete event (admin only)

### Video Stream API
- `GET /api/stream/live` - Live MJPEG stream
- `GET /api/stream/snapshot` - Current frame snapshot

### System Metrics API
- `GET /api/metrics/current` - Current system status
- `GET /api/metrics/history` - Historical metrics
  - Query params: `?start_time=...&end_time=...&interval=5min`
- `GET /api/metrics/health` - System health check

### Configuration API
- `GET /api/config` - Get current configuration
- `GET /api/config/{section}` - Get specific section
- `PUT /api/config/{section}` - Update section (admin only)
- `GET /api/config/history` - Configuration change history

### Notifications API
- `GET /api/notifications` - List notification history
- `GET /api/notifications/stats` - Notification statistics by channel

### Real-time Updates
- `GET /api/events/stream` - Server-Sent Events for live updates

## Frontend Pages

### 1. Dashboard (Home)
**URL**: `/`

**Features**:
- Live video feed with detection overlays
- Recent events timeline (last 10)
- System status widgets (CPU, memory, disk, temperature)
- Quick stats (events today, detections, notifications sent)
- Active alerts banner

**Layout**: 2-column grid
- Left: Live video feed (70%)
- Right: Stats and recent events (30%)

### 2. Event History
**URL**: `/events`

**Features**:
- Searchable/filterable event list
- Date range picker
- Event type filter (motion, detection, alert)
- Severity filter
- Image gallery view
- Event details modal
- Export to CSV functionality
- Pagination (50 events per page)

**Layout**: Table view with thumbnail gallery option

### 3. System Settings
**URL**: `/settings`

**Features**:
- Camera settings (resolution, FPS, rotation)
- Motion detection settings (sensitivity, zones)
- AI settings (confidence threshold, target classes)
- Notification settings (channels, recipients, throttling)
- Storage settings (retention, limits)
- Save/Reset buttons
- Configuration validation

**Layout**: Tabbed interface with sections

### 4. System Monitoring
**URL**: `/monitoring`

**Features**:
- Real-time performance graphs (CPU, memory, temperature)
- Service status indicators
- FPS and inference time charts
- Storage usage breakdown
- Network statistics
- System logs viewer
- Service restart buttons (admin only)

**Layout**: Grid of monitoring cards with graphs

## Configuration Updates

Add to `system_config.yaml`:

```yaml
# Database Configuration
database:
  # Primary database location (SSD)
  path: "/mnt/ssd/security_data/database/security.db"
  # Fallback location (SD card)
  fallback_path: "/home/ramon/security_data/database/security.db"
  # Create parent directories automatically
  auto_create_dirs: true
  # Database settings
  connection_timeout: 30
  journal_mode: "WAL"  # Write-Ahead Logging for better concurrency
  synchronous: "NORMAL"  # Balance between safety and performance
  # Retention policies
  retention:
    events_days: 30
    metrics_days: 7
    notifications_days: 30
    config_history_days: 90
  # Maintenance
  auto_vacuum: true
  vacuum_interval_hours: 168  # Weekly
  backup_enabled: true
  backup_interval_hours: 24
  backup_location: "/home/ramon/security_data/backups"

# Web Dashboard Configuration
web:
  enabled: true
  host: "0.0.0.0"  # Listen on all interfaces
  port: 5000
  debug: false
  # Security
  secret_key: "generate-secure-key-here"
  session_timeout: 3600  # seconds
  max_content_length: 16777216  # 16MB
  # Performance
  threaded: true
  use_reloader: false  # Disable in production
  # CORS settings (for future mobile app)
  cors_enabled: false
  cors_origins: []
  # Rate limiting
  rate_limit_enabled: true
  rate_limit_per_minute: 60
  # Streaming settings
  stream_fps: 15
  stream_quality: 85
  stream_max_clients: 5
```

## Performance Considerations

### Database Optimization
1. **WAL Mode**: Better concurrent read/write performance
2. **Indexes**: Created on frequently queried columns
3. **JSON Storage**: Use JSON for flexible metadata
4. **Retention Policies**: Automatic cleanup of old data
5. **Connection Pooling**: Reuse database connections

### Video Streaming
1. **MJPEG**: Simple, no complex codec needed
2. **Frame Rate Limiting**: Cap at 15 FPS to reduce bandwidth
3. **Quality Control**: JPEG quality 85% (good balance)
4. **Client Limit**: Max 5 concurrent streams to prevent overload
5. **Conditional Processing**: Only encode frames when clients connected

### Frontend Optimization
1. **Lazy Loading**: Load images on scroll
2. **Pagination**: Limit results to 50 per page
3. **Caching**: Cache static assets
4. **Minification**: Minify CSS/JS in production
5. **SSE over Polling**: More efficient for live updates

## Security Considerations (Epic 6 Preview)

### Authentication
- Session-based authentication
- Password hashing with bcrypt
- CSRF protection
- Secure cookie flags

### Authorization
- Role-based access control (admin, user, viewer)
- API endpoint protection
- Configuration changes require admin

### Data Protection
- Input validation and sanitization
- SQL injection prevention (parameterized queries)
- XSS protection
- Rate limiting

## Testing Strategy

### Unit Tests
- Database service operations
- API endpoint responses
- Configuration validation
- Data serialization

### Integration Tests
- End-to-end event creation and retrieval
- Video streaming functionality
- Real-time updates delivery
- Configuration persistence

### Performance Tests
- Database query performance
- Concurrent stream handling
- API response times
- Memory usage under load

## Deployment Steps

1. **Database Setup**
   - Create database directory on SSD
   - Initialize schema
   - Create default admin user
   - Set up automated backups

2. **Web Application**
   - Install Flask dependencies
   - Configure production settings
   - Set up systemd service
   - Configure Nginx reverse proxy (optional)

3. **Integration**
   - Update existing services to log to database
   - Test notification delivery and logging
   - Verify metric collection

4. **Monitoring**
   - Set up health checks
   - Configure alerting
   - Enable logging

## Success Criteria

- ✅ Database stores events with full metadata
- ✅ Live video stream viewable in browser
- ✅ Event history displays past detections with images
- ✅ System configuration editable via web UI
- ✅ Performance metrics visible on monitoring page
- ✅ Real-time updates appear without page refresh
- ✅ Mobile-responsive design works on phones/tablets
- ✅ System runs stably for 24+ hours
- ✅ Database queries complete in < 100ms
- ✅ Video stream maintains 10+ FPS

## Future Enhancements (Post-Epic 5)

- WebRTC for lower latency streaming
- Mobile app integration
- Video clip playback
- Event annotations
- Advanced search and filtering
- Export functionality (video clips, reports)
- Multi-camera support
- Custom dashboards
- Webhook integrations

---

**Status**: Design Complete - Ready for Implementation
**Created**: 2025-10-18
**Epic**: 5 - Web Dashboard & Monitoring






