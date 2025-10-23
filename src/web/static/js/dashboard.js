// Dashboard functionality

let streamActive = false;
let metricsInterval = null;
let statsInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    loadStats();
    loadRecentEvents();
    loadSystemMetrics();
    
    // Refresh data periodically
    statsInterval = setInterval(loadStats, 30000); // Every 30 seconds
    metricsInterval = setInterval(loadSystemMetrics, 10000); // Every 10 seconds
});

// Load dashboard statistics
async function loadStats() {
    try {
        // Get event stats
        const eventStats = await API.events.getStats(1); // Last 1 day
        const notificationStats = await API.notifications.getStats(1);
        const healthData = await API.metrics.getHealth();
        
        // Update event count
        document.getElementById('stat-events-today').textContent = 
            eventStats.total_events || 0;
        
        // Update detection count (sum of all detected objects)
        const detectionCount = Object.values(eventStats.by_type || {})
            .reduce((sum, count) => sum + count, 0);
        document.getElementById('stat-detections').textContent = detectionCount;
        
        // Update notification count
        document.getElementById('stat-notifications').textContent = 
            notificationStats.total || 0;
        
        // Update system health
        const healthCard = document.getElementById('system-health-card');
        const healthStatus = document.getElementById('stat-health');
        
        if (healthData.status === 'healthy') {
            healthStatus.textContent = 'Healthy';
            healthCard.className = 'stat-card';
        } else if (healthData.status === 'warning') {
            healthStatus.textContent = 'Warning';
            healthCard.className = 'stat-card health-warning';
        } else {
            healthStatus.textContent = 'Unhealthy';
            healthCard.className = 'stat-card health-danger';
        }
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load recent events
async function loadRecentEvents() {
    try {
        const data = await API.events.getAll({ page: 1, limit: 10 });
        const eventsList = document.getElementById('recent-events-list');
        
        if (!data.events || data.events.length === 0) {
            eventsList.innerHTML = '<div class="loading">No recent events</div>';
            return;
        }
        
        eventsList.innerHTML = data.events.map(event => `
            <div class="event-item" onclick="viewEventDetails(${event.id})">
                <div class="event-header">
                    <span class="event-type">${formatEventType(event.event_type)}</span>
                    <span class="event-time">${formatRelativeTime(event.timestamp)}</span>
                </div>
                <div class="event-details">
                    ${event.zone_name ? `Zone: ${event.zone_name}` : ''}
                    ${event.motion_percentage ? `Motion: ${Math.round(event.motion_percentage)}%` : ''}
                </div>
                <span class="event-severity severity-${event.severity}">${event.severity.toUpperCase()}</span>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading recent events:', error);
        document.getElementById('recent-events-list').innerHTML = 
            '<div class="loading">Failed to load events</div>';
    }
}

// Load system metrics
async function loadSystemMetrics() {
    try {
        const metrics = await API.metrics.getCurrent();
        
        // Update CPU
        updateMetric('cpu', metrics.cpu_usage);
        
        // Update Memory
        updateMetric('memory', metrics.memory_usage);
        
        // Update Disk
        updateMetric('disk', metrics.disk_usage);
        
        // Update Temperature
        if (metrics.temperature) {
            updateMetric('temp', (metrics.temperature / 80) * 100, `${metrics.temperature.toFixed(1)}°C`);
        }
        
        // Update stream info
        const streamStatus = await API.stream.getStatus();
        document.getElementById('stream-fps').textContent = `FPS: ${streamStatus.stream_fps || '-'}`;
        document.getElementById('stream-clients').textContent = `Clients: ${streamStatus.active_clients || 0}/${streamStatus.max_clients || 5}`;
        
    } catch (error) {
        console.error('Error loading system metrics:', error);
    }
}

function updateMetric(name, percentage, displayValue = null) {
    const bar = document.getElementById(`${name}-bar`);
    const value = document.getElementById(`${name}-value`);
    
    if (bar) {
        bar.style.width = `${percentage}%`;
        
        // Color based on threshold
        bar.className = 'progress-fill';
        if (percentage > 90) {
            bar.classList.add('danger');
        } else if (percentage > 75) {
            bar.classList.add('warning');
        }
    }
    
    if (value) {
        value.textContent = displayValue || `${percentage.toFixed(1)}%`;
    }
}

// Toggle video stream
function toggleStream() {
    const btn = document.getElementById('toggle-stream-btn');
    const status = document.getElementById('stream-status');
    const video = document.getElementById('video-stream');
    const placeholder = document.getElementById('video-placeholder');
    
    if (!streamActive) {
        // Start stream
        video.src = API.stream.getLiveURL();
        video.style.display = 'block';
        placeholder.style.display = 'none';
        btn.textContent = 'Stop Stream';
        status.textContent = 'Live';
        status.className = 'status-badge status-active';
        streamActive = true;
    } else {
        // Stop stream
        video.src = '';
        video.style.display = 'none';
        placeholder.style.display = 'flex';
        btn.textContent = 'Start Stream';
        status.textContent = 'Offline';
        status.className = 'status-badge status-inactive';
        streamActive = false;
    }
}

// Refresh metrics manually
function refreshMetrics() {
    loadSystemMetrics();
}

// View event details (redirect to events page)
function viewEventDetails(eventId) {
    window.location.href = `/events?event=${eventId}`;
}

// Close alert
function closeAlert() {
    document.getElementById('alert-banner').style.display = 'none';
}

// Format event type for display
function formatEventType(type) {
    const types = {
        'motion': '🏃 Motion Detected',
        'object_detected': '🎯 Object Detected',
        'alert': '🚨 Alert'
    };
    return types[type] || type;
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (statsInterval) clearInterval(statsInterval);
    if (metricsInterval) clearInterval(metricsInterval);
});






