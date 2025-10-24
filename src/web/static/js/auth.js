/**
 * Authentication and JWT handling for AI Security System
 */

// Authentication state
const auth = {
    token: null,
    user: null,
    isAuthenticated: false
};

/**
 * Initialize authentication state from localStorage
 */
function initAuth() {
    const token = localStorage.getItem('auth_token');
    const userStr = localStorage.getItem('user');
    
    if (token && userStr) {
        try {
            auth.token = token;
            auth.user = JSON.parse(userStr);
            auth.isAuthenticated = true;
            
            // Update UI to show user info
            updateAuthUI();
            
            // Verify token is still valid
            verifyToken().catch(() => {
                // Token invalid, clear auth
                clearAuth();
                redirectToLogin();
            });
            
        } catch (error) {
            console.error('Failed to parse user data:', error);
            clearAuth();
        }
    } else if (!isPublicPage()) {
        // Not authenticated and not on public page
        redirectToLogin();
    }
}

/**
 * Verify JWT token is still valid
 */
async function verifyToken() {
    if (!auth.token) {
        throw new Error('No token');
    }
    
    const response = await fetch('/api/auth/verify', {
        headers: {
            'Authorization': `Bearer ${auth.token}`
        }
    });
    
    if (!response.ok) {
        throw new Error('Token invalid');
    }
    
    const data = await response.json();
    
    if (data.success) {
        // Update user data
        auth.user = data.user;
        localStorage.setItem('user', JSON.stringify(data.user));
        updateAuthUI();
        return true;
    }
    
    throw new Error('Token verification failed');
}

/**
 * Logout user
 */
async function logout() {
    try {
        // Call logout API
        if (auth.token) {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${auth.token}`
                }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear local auth state
        clearAuth();
        redirectToLogin();
    }
}

/**
 * Clear authentication state
 */
function clearAuth() {
    auth.token = null;
    auth.user = null;
    auth.isAuthenticated = false;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
}

/**
 * Redirect to login page
 */
function redirectToLogin() {
    if (!isPublicPage()) {
        window.location.href = '/login';
    }
}

/**
 * Check if current page is public (doesn't require auth)
 */
function isPublicPage() {
    const publicPages = ['/login', '/health'];
    return publicPages.some(page => window.location.pathname === page);
}

/**
 * Update UI to show user info and logout button
 */
function updateAuthUI() {
    if (!auth.user) return;
    
    // Add user menu to navbar
    const navMenu = document.querySelector('.nav-menu');
    if (navMenu && !document.getElementById('user-menu')) {
        const userMenuItem = document.createElement('li');
        userMenuItem.id = 'user-menu';
        userMenuItem.innerHTML = `
            <div style="position: relative;">
                <button id="user-menu-btn" class="nav-link" style="cursor: pointer; border: none; background: none; font: inherit;">
                    <span class="nav-link-icon">👤</span>
                    ${auth.user.username}
                </button>
                <div id="user-dropdown" style="display: none; position: absolute; right: 0; top: 100%; margin-top: 0.5rem; background: white; border-radius: 0.5rem; box-shadow: var(--shadow-lg); min-width: 200px; z-index: 1000;">
                    <div style="padding: 1rem; border-bottom: 1px solid var(--border-color);">
                        <div style="font-weight: 600;">${auth.user.username}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; margin-top: 0.25rem;">
                            ${auth.user.role}
                        </div>
                    </div>
                    ${auth.user.role === 'admin' ? `
                    <a href="/users" style="display: block; padding: 0.75rem 1rem; text-decoration: none; color: var(--text-primary); transition: background 0.2s;">
                        <span style="margin-right: 0.5rem;">👥</span> Manage Users
                    </a>` : ''}
                    <button onclick="logout()" style="width: 100%; text-align: left; padding: 0.75rem 1rem; border: none; background: none; color: var(--danger-color); cursor: pointer; font: inherit; border-top: 1px solid var(--border-color);">
                        <span style="margin-right: 0.5rem;">🚪</span> Logout
                    </button>
                </div>
            </div>
        `;
        navMenu.appendChild(userMenuItem);
        
        // Toggle dropdown on click
        document.getElementById('user-menu-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = document.getElementById('user-dropdown');
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            const dropdown = document.getElementById('user-dropdown');
            if (dropdown) {
                dropdown.style.display = 'none';
            }
        });
    }
}

/**
 * Make authenticated API request
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<Response>}
 */
async function authenticatedFetch(url, options = {}) {
    if (!auth.token) {
        throw new Error('Not authenticated');
    }
    
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${auth.token}`
    };
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // Handle 401 unauthorized
    if (response.status === 401) {
        clearAuth();
        redirectToLogin();
        throw new Error('Unauthorized');
    }
    
    return response;
}

/**
 * Check if user has required role
 * @param {string} requiredRole - Required role (admin, user, viewer)
 * @returns {boolean}
 */
function hasRole(requiredRole) {
    if (!auth.user) return false;
    
    const roleHierarchy = {
        'admin': 3,
        'user': 2,
        'viewer': 1
    };
    
    const userRoleLevel = roleHierarchy[auth.user.role] || 0;
    const requiredRoleLevel = roleHierarchy[requiredRole] || 0;
    
    return userRoleLevel >= requiredRoleLevel;
}

/**
 * Show unauthorized message and redirect
 */
function showUnauthorized() {
    alert('You do not have permission to access this page.');
    window.location.href = '/';
}

/**
 * Protect page - require authentication and optionally a specific role
 * @param {string} requiredRole - Optional required role
 */
function protectPage(requiredRole = null) {
    // Check authentication
    if (!auth.isAuthenticated) {
        redirectToLogin();
        return false;
    }
    
    // Check role if specified
    if (requiredRole && !hasRole(requiredRole)) {
        showUnauthorized();
        return false;
    }
    
    return true;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 minute
    if (diff < 60000) {
        return 'Just now';
    }
    
    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }
    
    // Less than 1 day
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }
    
    // Less than 1 week
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }
    
    // Format as date
    return date.toLocaleDateString();
}

// Initialize auth on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
} else {
    initAuth();
}

// Export functions for use in other scripts
if (typeof window !== 'undefined') {
    window.auth = auth;
    window.logout = logout;
    window.authenticatedFetch = authenticatedFetch;
    window.hasRole = hasRole;
    window.protectPage = protectPage;
    window.formatDate = formatDate;
}

