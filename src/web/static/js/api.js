// API client for AI Security System

const API = {
    baseURL: '',
    
    // Helper function for fetch requests
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    },
    
    // Events API
    events: {
        async getAll(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            return await API.request(`/api/events?${queryString}`);
        },
        
        async getById(id) {
            return await API.request(`/api/events/${id}`);
        },
        
        async delete(id) {
            return await API.request(`/api/events/${id}`, { method: 'DELETE' });
        },
        
        async getStats(days = 7) {
            return await API.request(`/api/events/stats?days=${days}`);
        }
    },
    
    // Metrics API
    metrics: {
        async getCurrent() {
            return await API.request('/api/metrics/current');
        },
        
        async getHistory(startTime, endTime, interval = 5) {
            const params = new URLSearchParams({
                start_time: startTime,
                end_time: endTime,
                interval: interval
            });
            return await API.request(`/api/metrics/history?${params}`);
        },
        
        async getHealth() {
            return await API.request('/api/metrics/health');
        },
        
        async getDatabaseStats() {
            return await API.request('/api/metrics/database');
        }
    },
    
    // Stream API
    stream: {
        getLiveURL() {
            return `${API.baseURL}/api/stream/live`;
        },
        
        getSnapshotURL() {
            return `${API.baseURL}/api/stream/snapshot`;
        },
        
        async getStatus() {
            return await API.request('/api/stream/status');
        }
    },
    
    // Config API
    config: {
        async getAll() {
            return await API.request('/api/config');
        },
        
        async getSection(section) {
            return await API.request(`/api/config/${section}`);
        }
    },
    
    // Notifications API
    notifications: {
        async getStats(days = 7) {
            return await API.request(`/api/notifications/stats?days=${days}`);
        }
    }
};

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin} min ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
    return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}






