// Events page functionality

let currentPage = 1;
let currentFilters = {};
let currentView = 'list';

// Initialize events page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Events page initializing...');
    loadEventStats();
    loadEvents();
    
    // Check for event ID in URL
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('event');
    if (eventId) {
        viewEvent(eventId);
    }
});

// Load event statistics
async function loadEventStats() {
    try {
        const stats = await API.events.getStats(7); // Last 7 days
        
        // Total events
        document.getElementById('total-events').textContent = stats.total_events || 0;
        
        // High severity events
        const highSeverity = (stats.by_severity?.high || 0) + (stats.by_severity?.critical || 0);
        document.getElementById('high-severity-events').textContent = highSeverity;
        
        // Person detections
        const personCount = stats.top_objects?.find(obj => obj.class_name === 'person')?.count || 0;
        document.getElementById('person-detections').textContent = personCount;
        
        // Vehicle detections (car + truck)
        const vehicleCount = (stats.top_objects?.find(obj => obj.class_name === 'car')?.count || 0) +
                            (stats.top_objects?.find(obj => obj.class_name === 'truck')?.count || 0);
        document.getElementById('vehicle-detections').textContent = vehicleCount;
        
    } catch (error) {
        console.error('Error loading event stats:', error);
    }
}

// Load events list
async function loadEvents() {
    try {
        const params = {
            page: currentPage,
            limit: 50,
            ...currentFilters
        };
        
        const data = await API.events.getAll(params);
        const eventsList = document.getElementById('events-list');
        const pagination = document.getElementById('pagination');
        
        if (!data.events || data.events.length === 0) {
            eventsList.innerHTML = '<div class="loading">No events found</div>';
            pagination.style.display = 'none';
            return;
        }
        
        // Render events based on view mode
        if (currentView === 'list') {
            renderListView(data.events);
        } else {
            renderGalleryView(data.events);
        }
        
        // Update pagination
        updatePagination(data.pagination);
        pagination.style.display = 'flex';
        
    } catch (error) {
        console.error('Error loading events:', error);
        document.getElementById('events-list').innerHTML = 
            '<div class="loading">Failed to load events</div>';
    }
}

function renderListView(events) {
    const eventsList = document.getElementById('events-list');
    eventsList.className = 'events-list-view';
    eventsList.innerHTML = events.map(event => `
        <div class="event-list-item" onclick="viewEvent(${event.id})">
            <div class="event-thumbnail">
                ${event.image_path ? 
                    `<img src="${event.image_path}" alt="Event ${event.id}">` :
                    '<div class="no-image">📹</div>'
                }
            </div>
            <div class="event-content">
                <div class="event-header">
                    <h3>${formatEventType(event.event_type)}</h3>
                    <span class="event-severity severity-${event.severity}">${event.severity}</span>
                </div>
                <div class="event-meta">
                    <span>⏰ ${formatDate(event.timestamp)}</span>
                    ${event.zone_name ? `<span>📍 ${event.zone_name}</span>` : ''}
                    ${event.motion_percentage ? `<span>🏃 ${Math.round(event.motion_percentage)}%</span>` : ''}
                </div>
                ${event.threat_level ? `<div class="threat-level">Threat: ${event.threat_level}</div>` : ''}
            </div>
        </div>
    `).join('');
}

function renderGalleryView(events) {
    const eventsList = document.getElementById('events-list');
    eventsList.className = 'events-gallery-view';
    eventsList.innerHTML = events.map(event => `
        <div class="event-gallery-item" onclick="viewEvent(${event.id})">
            <div class="gallery-image">
                ${event.image_path ? 
                    `<img src="${event.image_path}" alt="Event ${event.id}">` :
                    '<div class="no-image">📹</div>'
                }
                <span class="gallery-severity severity-${event.severity}">${event.severity}</span>
            </div>
            <div class="gallery-info">
                <div class="gallery-type">${formatEventType(event.event_type)}</div>
                <div class="gallery-time">${formatRelativeTime(event.timestamp)}</div>
            </div>
        </div>
    `).join('');
}

function updatePagination(pagination) {
    document.getElementById('page-info').textContent = 
        `Page ${pagination.page} of ${pagination.total_pages}`;
    
    document.getElementById('prev-btn').disabled = !pagination.has_prev;
    document.getElementById('next-btn').disabled = !pagination.has_next;
}

// Apply filters
function applyFilters() {
    currentFilters = {};
    
    const eventType = document.getElementById('event-type-filter').value;
    if (eventType) currentFilters.event_type = eventType;
    
    const severity = document.getElementById('severity-filter').value;
    if (severity) currentFilters.severity = severity;
    
    const startDate = document.getElementById('start-date-filter').value;
    if (startDate) currentFilters.start_date = new Date(startDate).toISOString();
    
    const endDate = document.getElementById('end-date-filter').value;
    if (endDate) currentFilters.end_date = new Date(endDate).toISOString();
    
    currentPage = 1;
    loadEvents();
}

// Clear filters
function clearFilters() {
    document.getElementById('event-type-filter').value = '';
    document.getElementById('severity-filter').value = '';
    document.getElementById('start-date-filter').value = '';
    document.getElementById('end-date-filter').value = '';
    
    currentFilters = {};
    currentPage = 1;
    loadEvents();
}

// Change view mode
function setView(view) {
    currentView = view;
    
    // Update button states
    document.getElementById('list-view-btn').classList.toggle('active', view === 'list');
    document.getElementById('gallery-view-btn').classList.toggle('active', view === 'gallery');
    
    // Reload events with new view
    loadEvents();
}

// Pagination
function nextPage() {
    currentPage++;
    loadEvents();
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        loadEvents();
    }
}

// View event details
async function viewEvent(eventId) {
    try {
        const event = await API.events.getById(eventId);
        showEventModal(event);
    } catch (error) {
        console.error('Error loading event details:', error);
        alert('Failed to load event details');
    }
}

function showEventModal(event) {
    const modal = document.getElementById('event-modal');
    const modalBody = document.getElementById('modal-body');
    
    modalBody.innerHTML = `
        <div class="event-detail">
            ${event.image_path ? 
                `<img src="${event.image_path}" alt="Event ${event.id}" class="event-detail-image">` :
                '<div class="no-image-large">📹 No Image Available</div>'
            }
            
            <div class="event-detail-info">
                <div class="detail-row">
                    <span class="detail-label">Event Type:</span>
                    <span class="detail-value">${formatEventType(event.event_type)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Severity:</span>
                    <span class="event-severity severity-${event.severity}">${event.severity}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Timestamp:</span>
                    <span class="detail-value">${formatDate(event.timestamp)}</span>
                </div>
                ${event.zone_name ? `
                <div class="detail-row">
                    <span class="detail-label">Zone:</span>
                    <span class="detail-value">${event.zone_name}</span>
                </div>
                ` : ''}
                ${event.motion_percentage ? `
                <div class="detail-row">
                    <span class="detail-label">Motion:</span>
                    <span class="detail-value">${Math.round(event.motion_percentage)}%</span>
                </div>
                ` : ''}
                ${event.threat_level ? `
                <div class="detail-row">
                    <span class="detail-label">Threat Level:</span>
                    <span class="detail-value">${event.threat_level}</span>
                </div>
                ` : ''}
            </div>
            
            ${event.detected_objects && event.detected_objects.length > 0 ? `
                <div class="detected-objects">
                    <h3>Detected Objects</h3>
                    <div class="objects-list">
                        ${event.detected_objects.map(obj => `
                            <div class="object-item">
                                <span class="object-class">${obj.class_name}</span>
                                <span class="object-confidence">${Math.round(obj.confidence * 100)}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    modal.style.display = 'flex';
}

function closeModal(event) {
    if (!event || event.target.id === 'event-modal') {
        document.getElementById('event-modal').style.display = 'none';
    }
}

// Format event type
function formatEventType(type) {
    const types = {
        'motion': 'Motion Detected',
        'object_detected': 'Object Detected',
        'alert': 'Alert'
    };
    return types[type] || type;
}


