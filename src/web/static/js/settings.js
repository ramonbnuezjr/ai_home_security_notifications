// Settings page functionality

let currentConfig = null;

// Initialize settings page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Settings page initializing...');
    loadAllConfig();
});

// Load full configuration
async function loadAllConfig() {
    try {
        currentConfig = await API.config.getAll();
        
        // Load each section
        loadConfigSection('camera', currentConfig.camera);
        loadConfigSection('detection', currentConfig.detection);
        loadConfigSection('ai', currentConfig.ai);
        loadConfigSection('notifications', currentConfig.notifications);
        loadConfigSection('storage', currentConfig.storage);
        loadConfigSection('web', currentConfig.web);
        
    } catch (error) {
        console.error('Error loading configuration:', error);
    }
}

// Load specific configuration section
function loadConfigSection(section, config) {
    const container = document.getElementById(`${section}-config`);
    
    if (!config) {
        container.innerHTML = '<div class="loading">Configuration not available</div>';
        return;
    }
    
    container.innerHTML = renderConfig(config);
}

// Render configuration recursively
function renderConfig(config, level = 0) {
    if (typeof config !== 'object' || config === null) {
        return `<span class="config-value ${getValueClass(config)}">${formatConfigValue(config)}</span>`;
    }
    
    let html = '<div class="config-group">';
    
    for (const [key, value] of Object.entries(config)) {
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            html += `
                <div class="config-subsection">
                    <h4>${formatKey(key)}</h4>
                    ${renderConfig(value, level + 1)}
                </div>
            `;
        } else {
            html += `
                <div class="config-item">
                    <span class="config-label">${formatKey(key)}</span>
                    <span class="config-value ${getValueClass(value)}">${formatConfigValue(value)}</span>
                </div>
            `;
        }
    }
    
    html += '</div>';
    return html;
}

// Format configuration key
function formatKey(key) {
    return key
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Format configuration value
function formatConfigValue(value) {
    if (value === null || value === undefined) {
        return '<em>Not set</em>';
    }
    
    if (typeof value === 'boolean') {
        return value ? '✓ Enabled' : '✗ Disabled';
    }
    
    if (Array.isArray(value)) {
        if (value.length === 0) return '[ ]';
        return `[${value.length} items]`;
    }
    
    if (typeof value === 'string' && value.includes('REDACTED')) {
        return value;
    }
    
    return value.toString();
}

// Get CSS class for value type
function getValueClass(value) {
    if (typeof value === 'boolean') {
        return value ? 'boolean-true' : 'boolean-false';
    }
    
    if (typeof value === 'string' && value.includes('REDACTED')) {
        return 'redacted';
    }
    
    return '';
}

// Show specific tab
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Activate button
    event.target.classList.add('active');
}

// Reset configuration (disabled until Epic 6)
function resetConfig() {
    alert('Configuration editing will be enabled in Epic 6 with authentication');
}

// Save configuration (disabled until Epic 6)
function saveConfig() {
    alert('Configuration editing will be enabled in Epic 6 with authentication');
}


