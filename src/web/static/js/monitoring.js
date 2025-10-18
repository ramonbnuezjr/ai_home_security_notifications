// Monitoring page functionality

let refreshInterval = null;

// Initialize monitoring page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Monitoring page initializing...');
    loadSystemHealth();
    loadDatabaseStats();
    loadStreamStatus();
    
    // Auto-refresh every 5 seconds
    refreshInterval = setInterval(() => {
        loadSystemHealth();
        loadStreamStatus();
    }, 5000);
});

// Load system health
async function loadSystemHealth() {
    try {
        const health = await API.metrics.getHealth();
        const healthCard = document.querySelector('.health-card');
        const healthStatus = document.getElementById('health-status');
        const healthDetails = document.getElementById('health-details');
        
        // Update status badge
        healthStatus.textContent = health.status.charAt(0).toUpperCase() + health.status.slice(1);
        healthStatus.className = `status-badge status-${health.status === 'healthy' ? 'healthy' : 
                                                          health.status === 'warning' ? 'warning' : 'danger'}`;
        
        // Update card class
        healthCard.className = `card health-card ${health.status}`;
        
        // Display metrics
        const metrics = health.metrics;
        healthDetails.innerHTML = `
            <div class="health-item ${getHealthClass(metrics.cpu_usage, 90)}">
                <div class="health-label">CPU Usage</div>
                <div class="health-value">${metrics.cpu_usage?.toFixed(1) || '-'}%</div>
            </div>
            <div class="health-item ${getHealthClass(metrics.memory_usage, 95)}">
                <div class="health-label">Memory Usage</div>
                <div class="health-value">${metrics.memory_usage?.toFixed(1) || '-'}%</div>
            </div>
            <div class="health-item ${getHealthClass(metrics.disk_usage, 90)}">
                <div class="health-label">Disk Usage</div>
                <div class="health-value">${metrics.disk_usage?.toFixed(1) || '-'}%</div>
            </div>
            <div class="health-item ${getHealthClass((metrics.temperature || 0) / 80 * 100, 100)}">
                <div class="health-label">Temperature</div>
                <div class="health-value">${metrics.temperature?.toFixed(1) || '-'}°C</div>
            </div>
        `;
        
        // Display issues if any
        if (health.issues && health.issues.length > 0) {
            healthDetails.innerHTML += `
                <div class="health-issues">
                    <h4>Issues Detected:</h4>
                    <ul>
                        ${health.issues.map(issue => `<li>${issue}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Update current metrics in chart headers
        document.getElementById('cpu-current').textContent = `${metrics.cpu_usage?.toFixed(1) || '-'}%`;
        document.getElementById('memory-current').textContent = `${metrics.memory_usage?.toFixed(1) || '-'}%`;
        document.getElementById('disk-current').textContent = `${metrics.disk_usage?.toFixed(1) || '-'}%`;
        document.getElementById('temp-current').textContent = `${metrics.temperature?.toFixed(1) || '-'}°C`;
        
    } catch (error) {
        console.error('Error loading system health:', error);
        document.getElementById('health-details').innerHTML = 
            '<div class="loading">Failed to load health status</div>';
    }
}

function getHealthClass(value, threshold) {
    if (!value) return '';
    if (value > threshold) return 'danger';
    if (value > threshold * 0.85) return 'warning';
    return '';
}

// Load database statistics
async function loadDatabaseStats() {
    try {
        const stats = await API.metrics.getDatabaseStats();
        const dbStats = document.getElementById('db-stats');
        
        dbStats.innerHTML = `
            <div class="db-stat-item">
                <div class="db-stat-value">${stats.total_events || 0}</div>
                <div class="db-stat-label">Total Events</div>
            </div>
            <div class="db-stat-item">
                <div class="db-stat-value">${stats.total_objects || 0}</div>
                <div class="db-stat-label">Detected Objects</div>
            </div>
            <div class="db-stat-item">
                <div class="db-stat-value">${stats.total_notifications || 0}</div>
                <div class="db-stat-label">Notifications</div>
            </div>
            <div class="db-stat-item">
                <div class="db-stat-value">${stats.total_metrics || 0}</div>
                <div class="db-stat-label">Metrics Records</div>
            </div>
            <div class="db-stat-item">
                <div class="db-stat-value">${stats.database_size_mb?.toFixed(2) || '-'} MB</div>
                <div class="db-stat-label">Database Size</div>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading database stats:', error);
        document.getElementById('db-stats').innerHTML = 
            '<div class="loading">Failed to load database statistics</div>';
    }
}

// Load stream status
async function loadStreamStatus() {
    try {
        const status = await API.stream.getStatus();
        const streamStatusDiv = document.getElementById('stream-status');
        
        streamStatusDiv.innerHTML = `
            <div class="stream-info-item">
                <span class="stream-info-label">Active Clients</span>
                <span class="stream-info-value">${status.active_clients} / ${status.max_clients}</span>
            </div>
            <div class="stream-info-item">
                <span class="stream-info-label">Stream FPS</span>
                <span class="stream-info-value">${status.stream_fps}</span>
            </div>
            <div class="stream-info-item">
                <span class="stream-info-label">Quality</span>
                <span class="stream-info-value">${status.quality}%</span>
            </div>
            <div class="stream-info-item">
                <span class="stream-info-label">Status</span>
                <span class="stream-info-value ${status.active_clients > 0 ? 'text-success' : ''}"}>
                    ${status.active_clients > 0 ? 'Active' : 'Idle'}
                </span>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading stream status:', error);
        document.getElementById('stream-status').innerHTML = 
            '<div class="loading">Failed to load stream status</div>';
    }
}

// Refresh database stats manually
function refreshDatabaseStats() {
    loadDatabaseStats();
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (refreshInterval) clearInterval(refreshInterval);
});


