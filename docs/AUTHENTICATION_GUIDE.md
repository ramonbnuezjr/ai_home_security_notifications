# Authentication & Security Guide

Complete guide for setting up authentication, user management, and security features in the AI Home Security System.

## Table of Contents

1. [Overview](#overview)
2. [First-Time Setup](#first-time-setup)
3. [User Management](#user-management)
4. [HTTPS/TLS Setup](#httpstls-setup)
5. [Security Best Practices](#security-best-practices)
6. [API Authentication](#api-authentication)
7. [MFA Setup](#mfa-setup)
8. [Troubleshooting](#troubleshooting)

## Overview

Epic 6 brings enterprise-grade security to the AI Home Security System:

- **JWT-based Authentication**: Secure token-based authentication
- **Role-Based Access Control (RBAC)**: Admin, User, and Viewer roles
- **Multi-Factor Authentication (MFA)**: Optional TOTP-based 2FA
- **Encryption**: Fernet encryption for sensitive data
- **HTTPS/TLS**: Secure communication with TLS certificates
- **Privacy Controls**: GDPR-compliant data management
- **Audit Logging**: Comprehensive activity tracking

### Security Architecture

```
┌─────────────┐     JWT Token     ┌──────────────┐
│   Client    │ ─────────────────▶│  Flask App   │
│  (Browser)  │◀───────────────── │ (Auth Check) │
└─────────────┘     API Response  └──────────────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │ Auth Service │
                                   │  (JWT+RBAC)  │
                                   └──────────────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │   Database   │
                                   │ (Encrypted)  │
                                   └──────────────┘
```

## First-Time Setup

### 1. Initialize Encryption

Before creating any users, initialize the encryption system:

```bash
cd /home/ramon/ai_projects/ai_home_security_notifications

# Initialize encryption (creates encryption key)
python scripts/epic6_cli.py encryption init
```

This creates `/config/.encryption_key` with secure permissions (600).

### 2. Create Admin User

Create the first admin user:

```bash
# Interactive user creation
python scripts/epic6_cli.py user create

# Or specify details directly
python scripts/epic6_cli.py user create --username admin --role admin
```

You'll be prompted for:
- Username (required)
- Password (required, min 8 chars with uppercase, lowercase, numbers)
- Email (optional, for notifications)

**First user is automatically assigned admin role** regardless of the role parameter.

### 3. Access Web Dashboard

Start the dashboard and login:

```bash
# HTTP mode (development)
python scripts/run_dashboard.py

# HTTPS mode (recommended)
python scripts/run_dashboard_https.py
```

Navigate to:
- HTTP: `http://localhost:5000`
- HTTPS: `https://localhost:5000`

Login with the admin credentials you created.

## User Management

### Web Interface

Admin users can manage users through the web dashboard:

1. Login as admin
2. Navigate to **Users** page (user menu → Manage Users)
3. View, create, edit, or delete users

### CLI Management

Use the Epic 6 CLI for user management:

```bash
# Create user
python scripts/epic6_cli.py user create --username john --role user

# List users
python scripts/epic6_cli.py user list

# Update user
python scripts/epic6_cli.py user update <user_id> --email john@example.com

# Disable user
python scripts/epic6_cli.py user disable <user_id>

# Delete user
python scripts/epic6_cli.py user delete <user_id>
```

### User Roles

**Admin**
- Full system access
- User management
- Configuration changes
- Delete events

**User** (default)
- View dashboard
- View events
- View live stream
- View system metrics

**Viewer**
- View-only access
- Cannot modify anything
- Good for monitoring displays

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

Change passwords:
```bash
# Via CLI
python scripts/epic6_cli.py user change-password <user_id>

# Via web dashboard
Login → User menu → Change Password
```

## HTTPS/TLS Setup

### Quick Setup (Self-Signed Certificate)

For development and testing:

```bash
# Generate self-signed certificate
python scripts/setup_https.py

# Test HTTPS server
python scripts/setup_https.py --test

# Run dashboard with HTTPS
python scripts/run_dashboard_https.py
```

The script generates:
- `/config/certs/cert.pem` - TLS certificate
- `/config/certs/key.pem` - Private key (600 permissions)

**Note**: Self-signed certificates will show browser warnings. This is expected.

### Production Setup (Let's Encrypt)

For production with a real domain:

1. **Install Certbot**:
```bash
sudo apt-get update
sudo apt-get install certbot
```

2. **Get Certificate**:
```bash
# Stop any web server first
sudo certbot certonly --standalone -d yourdomain.com

# Or use webroot if server is running
sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com
```

3. **Update Configuration**:
```yaml
# config/system_config.yaml
web:
  use_https: true
  cert_file: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
  key_file: /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

4. **Run Dashboard**:
```bash
python scripts/run_dashboard_https.py
```

### Custom Certificates

If you have your own certificates:

```bash
python scripts/run_dashboard_https.py \
  --cert /path/to/your/cert.pem \
  --key /path/to/your/key.pem
```

## Security Best Practices

### 1. Configuration Security

```bash
# Secure configuration file permissions
chmod 600 config/system_config.yaml

# Generate strong secret key (32+ characters)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Update config/system_config.yaml:
web:
  secret_key: "<your-generated-secret-key>"
  debug: false  # Always false in production
  use_https: true
```

### 2. Database Security

```bash
# Secure database file
chmod 600 data/security_events.db

# Regular backups
cp data/security_events.db backups/security_events_$(date +%Y%m%d).db
```

### 3. Certificate Security

```bash
# Ensure private key is secure
chmod 600 config/certs/key.pem
chmod 600 config/.encryption_key

# Never commit certificates or keys to git
echo "config/certs/*.pem" >> .gitignore
echo "config/.encryption_key" >> .gitignore
```

### 4. Run Security Audit

Regular security audits:

```bash
# Run comprehensive security audit
python scripts/security_audit.py

# Review and fix any issues found
```

### 5. System Updates

Keep system and dependencies up to date:

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python dependencies
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip audit  # Or use safety: pip install safety && safety check
```

## API Authentication

All API endpoints (except `/login` and `/health`) require JWT authentication.

### Getting a Token

**Via Login Page**:
```javascript
// Automatic - handled by login.html
// Token stored in localStorage as 'auth_token'
```

**Via API**:
```bash
curl -X POST https://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'

# Response:
# {"success": true, "token": "eyJ0eXAiOi...", "user": {...}}
```

### Using Tokens

**In Headers** (preferred):
```bash
curl https://localhost:5000/api/events \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**As Query Parameter** (for streaming):
```bash
# Video stream
<img src="https://localhost:5000/api/stream/live?token=YOUR_JWT_TOKEN">
```

### JavaScript API Client

The built-in API client handles authentication automatically:

```javascript
// All API calls include token from localStorage
const events = await API.events.getAll();
const metrics = await API.metrics.getCurrent();

// Automatic logout on 401 response
```

## MFA Setup

### Enable MFA

**Via Web Dashboard**:
1. Login
2. User menu → Settings
3. Security → Enable MFA
4. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
5. Enter verification code
6. Save backup codes

**Via CLI**:
```bash
python scripts/epic6_cli.py mfa enable <user_id>
# Returns QR code and secret for authenticator app
```

### Login with MFA

1. Enter username and password
2. Enter 6-digit code from authenticator app
3. Login successful

### Disable MFA

**Web Dashboard**: User menu → Settings → Disable MFA (requires password)

**CLI**:
```bash
python scripts/epic6_cli.py mfa disable <user_id>
```

## Audit Logging

All authentication and security events are logged:

```bash
# View recent audit logs
python scripts/epic6_cli.py audit logs --limit 50

# Filter by event type
python scripts/epic6_cli.py audit logs --event-type login

# Export audit logs
python scripts/epic6_cli.py audit export --output audit_$(date +%Y%m%d).json
```

Logged events:
- User login/logout
- Failed login attempts
- User creation/deletion
- Role changes
- MFA enable/disable
- Configuration changes
- Data exports

## Privacy & GDPR

### Data Export

Users can export their data:

```bash
# Via CLI
python scripts/epic6_cli.py privacy export <user_id>

# Via API (logged in user)
curl -X POST https://localhost:5000/api/privacy/export \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Data Deletion

Delete user data:

```bash
# Via CLI (admin)
python scripts/epic6_cli.py privacy delete <user_id>

# Via web dashboard
User Management → Delete User → Confirm
```

## Troubleshooting

### "Invalid or expired token"

**Solution**: Token expired (default: 24 hours). Login again.

```bash
# Check token expiry in config
grep jwt_expiry_hours config/system_config.yaml

# Adjust if needed (in hours)
web:
  jwt_expiry_hours: 24
```

### "Module 'yaml' not found"

**Solution**: Install PyYAML

```bash
pip install pyyaml
```

### "Certificate verify failed"

**Solution**: You're using a self-signed certificate. Either:
1. Accept the browser warning (dev/testing)
2. Use Let's Encrypt certificate (production)
3. Add certificate to trusted store

### Can't access dashboard after enabling HTTPS

**Solution**: Use `https://` not `http://` in URL

```bash
# Wrong
http://localhost:5000

# Correct
https://localhost:5000
```

### Forgot admin password

**Solution**: Create new admin user via CLI

```bash
# Create new admin
python scripts/epic6_cli.py user create --username newadmin --role admin

# Or reset via database (requires sqlite3)
# This is advanced - backup database first!
```

### Session expires too quickly

**Solution**: Adjust session timeout

```yaml
# config/system_config.yaml
web:
  jwt_expiry_hours: 168  # 7 days
  session_timeout: 604800  # 7 days in seconds
```

## System Status

Check overall system status:

```bash
python scripts/epic6_cli.py status
```

Shows:
- Encryption status
- User count
- Active sessions
- Database health
- Certificate validity
- Recent activity

## Quick Reference

```bash
# First-time setup
python scripts/epic6_cli.py encryption init
python scripts/epic6_cli.py user create
python scripts/setup_https.py
python scripts/run_dashboard_https.py

# Daily operations
python scripts/epic6_cli.py user list
python scripts/epic6_cli.py audit logs
python scripts/security_audit.py

# Maintenance
python scripts/epic6_cli.py status
chmod 600 config/system_config.yaml
chmod 600 data/security_events.db
```

## Further Reading

- [Epic 6 Architecture](architecture.md#epic-6-security)
- [API Documentation](API_REFERENCE.md)
- [Deployment Guide](deployment.md)
- [Project Status](../project_status.md)

---

**Security is a continuous process. Review these settings regularly and keep the system updated.**

