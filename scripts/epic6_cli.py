#!/usr/bin/env python3
"""
Epic 6 CLI Utility - Security & Privacy Management
Provides command-line tools for managing authentication, encryption, privacy, and audit logs.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click
import json
import logging
from datetime import datetime
from src.services.database_service import DatabaseService
from src.services.auth_service import AuthService
from src.services.encryption_service import EncryptionService, TLSHelper
from src.services.privacy_service import PrivacyService
from src.utils.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """AI Home Security - Epic 6 Management CLI"""
    pass


# ==================== User Management ====================

@cli.group()
def user():
    """User management commands"""
    pass


@user.command()
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--email', prompt=True, help='Email address')
@click.option('--role', type=click.Choice(['admin', 'moderator', 'user', 'viewer']), default='admin', help='User role')
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def create(username, password, email, role, config):
    """Create a new user"""
    try:
        # Load config and initialize services
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        auth_service = AuthService(
            database_service=db_service,
            jwt_secret='temporary-key-for-cli',
            jwt_expiry_hours=24
        )
        
        # Create user
        success, user_id, errors = auth_service.create_user(
            username=username,
            password=password,
            email=email,
            role=role
        )
        
        if success:
            click.echo(click.style(f"✓ User created successfully!", fg='green'))
            click.echo(f"  User ID: {user_id}")
            click.echo(f"  Username: {username}")
            click.echo(f"  Email: {email}")
            click.echo(f"  Role: {role}")
        else:
            click.echo(click.style(f"✗ Failed to create user:", fg='red'))
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@user.command()
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def list(config):
    """List all users"""
    try:
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        auth_service = AuthService(
            database_service=db_service,
            jwt_secret='temporary-key-for-cli',
            jwt_expiry_hours=24
        )
        
        users, total = auth_service.list_users(limit=100)
        
        if total == 0:
            click.echo(click.style("No users found", fg='yellow'))
            return
        
        click.echo(click.style(f"\nTotal users: {total}\n", fg='cyan'))
        
        for user in users:
            status = "✓" if user['is_active'] else "✗"
            mfa = "🔐" if user.get('mfa_enabled') else "  "
            click.echo(f"{status} {mfa} {user['username']:<20} {user['role']:<12} {user['email'] or 'N/A':<30} (ID: {user['id']})")
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@user.command()
@click.argument('username')
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def delete(username, config):
    """Delete a user"""
    try:
        if not click.confirm(f"Are you sure you want to delete user '{username}'?"):
            click.echo("Cancelled")
            return
        
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        auth_service = AuthService(
            database_service=db_service,
            jwt_secret='temporary-key-for-cli',
            jwt_expiry_hours=24
        )
        
        # Get user
        user = auth_service.get_user_by_username(username)
        if not user:
            click.echo(click.style(f"✗ User '{username}' not found", fg='red'))
            sys.exit(1)
        
        # Delete user
        success, errors = auth_service.delete_user(user['id'])
        
        if success:
            click.echo(click.style(f"✓ User '{username}' deleted successfully", fg='green'))
        else:
            click.echo(click.style(f"✗ Failed to delete user:", fg='red'))
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


# ==================== Encryption ====================

@cli.group()
def encryption():
    """Encryption management commands"""
    pass


@encryption.command()
@click.option('--key-file', help='Path to key file (default: ~/.ai_security_key)')
def init(key_file):
    """Initialize encryption key"""
    try:
        enc_service = EncryptionService(key_file=key_file)
        
        if enc_service.verify_key():
            click.echo(click.style("✓ Encryption key initialized and verified", fg='green'))
            click.echo(f"  Key file: {enc_service.key_file}")
            click.echo(click.style("\n⚠️  IMPORTANT: Back up this key file securely!", fg='yellow'))
        else:
            click.echo(click.style("✗ Failed to verify encryption key", fg='red'))
            sys.exit(1)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@encryption.command()
@click.argument('data')
@click.option('--key-file', help='Path to key file')
def encrypt(data, key_file):
    """Encrypt a string"""
    try:
        enc_service = EncryptionService(key_file=key_file)
        encrypted = enc_service.encrypt(data)
        
        click.echo(click.style("✓ Data encrypted:", fg='green'))
        click.echo(encrypted)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@encryption.command()
@click.argument('encrypted_data')
@click.option('--key-file', help='Path to key file')
def decrypt(encrypted_data, key_file):
    """Decrypt a string"""
    try:
        enc_service = EncryptionService(key_file=key_file)
        decrypted = enc_service.decrypt(encrypted_data)
        
        click.echo(click.style("✓ Data decrypted:", fg='green'))
        click.echo(decrypted)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@encryption.command()
@click.option('--cert-file', default='certs/cert.pem', help='Certificate file path')
@click.option('--key-file', default='certs/key.pem', help='Key file path')
@click.option('--common-name', default='localhost', help='Common name for certificate')
@click.option('--days', default=365, help='Days certificate is valid')
def generate_cert(cert_file, key_file, common_name, days):
    """Generate self-signed TLS certificate"""
    try:
        # Create certs directory
        Path(cert_file).parent.mkdir(parents=True, exist_ok=True)
        
        cert_path, key_path = TLSHelper.generate_self_signed_cert(
            cert_file=cert_file,
            key_file=key_file,
            common_name=common_name,
            days_valid=days
        )
        
        click.echo(click.style("✓ TLS certificate generated successfully:", fg='green'))
        click.echo(f"  Certificate: {cert_path}")
        click.echo(f"  Private Key: {key_path}")
        click.echo(f"  Common Name: {common_name}")
        click.echo(f"  Valid for: {days} days")
        click.echo(click.style("\n⚠️  Self-signed certificate - use proper CA cert in production!", fg='yellow'))
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


# ==================== Privacy ====================

@cli.group()
def privacy():
    """Privacy management commands"""
    pass


@privacy.command()
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def enforce_retention(config):
    """Enforce data retention policies"""
    try:
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        privacy_service = PrivacyService(
            database_service=db_service,
            media_base_path=system_config.get('storage', {}).get('media_path', '/tmp/ai_security_media')
        )
        
        click.echo("Enforcing retention policies...")
        results = privacy_service.enforce_retention_policies()
        
        click.echo(click.style("\n✓ Retention policies enforced:", fg='green'))
        for data_type, count in results.items():
            if count > 0:
                click.echo(f"  {data_type}: {count} items deleted")
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


# ==================== Audit ====================

@cli.group()
def audit():
    """Audit log commands"""
    pass


@audit.command()
@click.option('--limit', default=50, help='Number of logs to display')
@click.option('--action', help='Filter by action')
@click.option('--user', help='Filter by username')
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def logs(limit, action, user, config):
    """View recent audit logs"""
    try:
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        # Build query
        where_clauses = []
        params = []
        
        if action:
            where_clauses.append("action = ?")
            params.append(action)
        
        if user:
            where_clauses.append("username = ?")
            params.append(user)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT timestamp, username, action, status, resource, ip_address
                FROM audit_log
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params + [limit])
            
            logs = cursor.fetchall()
        
        if not logs:
            click.echo(click.style("No audit logs found", fg='yellow'))
            return
        
        click.echo(click.style(f"\nRecent audit logs (showing {len(logs)}):\n", fg='cyan'))
        
        for log in logs:
            status_symbol = "✓" if log['status'] == 'success' else "✗"
            status_color = 'green' if log['status'] == 'success' else 'red'
            
            click.echo(
                f"{log['timestamp']} "
                f"{click.style(status_symbol, fg=status_color)} "
                f"{log['username'] or 'N/A':<15} "
                f"{log['action']:<25} "
                f"{log['resource'] or 'N/A':<30} "
                f"{log['ip_address'] or 'N/A'}"
            )
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@audit.command()
@click.option('--days', default=7, help='Days to analyze')
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def stats(days, config):
    """Show audit log statistics"""
    try:
        from datetime import timedelta
        
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        start_date = datetime.now() - timedelta(days=days)
        
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total logs
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?
            """, (start_date,))
            total = cursor.fetchone()[0]
            
            # By action
            cursor.execute("""
                SELECT action, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """, (start_date,))
            by_action = cursor.fetchall()
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY status
            """, (start_date,))
            by_status = cursor.fetchall()
        
        click.echo(click.style(f"\n📊 Audit Log Statistics (Last {days} days)\n", fg='cyan', bold=True))
        click.echo(f"Total logs: {total}\n")
        
        if by_action:
            click.echo(click.style("Top Actions:", fg='cyan'))
            for row in by_action:
                click.echo(f"  {row['action']:<30} {row['count']:>6}")
        
        if by_status:
            click.echo(click.style("\nBy Status:", fg='cyan'))
            for row in by_status:
                click.echo(f"  {row['status']:<30} {row['count']:>6}")
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


# ==================== System ====================

@cli.command()
@click.option('--config', default='config/system_config.yaml', help='Path to config file')
def status(config):
    """Show Epic 6 system status"""
    try:
        system_config = load_config(config)
        db_config = system_config.get('database', {})
        
        db_service = DatabaseService(
            db_path=db_config.get('path'),
            fallback_path=db_config.get('fallback_path')
        )
        
        auth_service = AuthService(
            database_service=db_service,
            jwt_secret='temporary-key',
            jwt_expiry_hours=24
        )
        
        click.echo(click.style("\n🔒 Epic 6: Security & Privacy Status\n", fg='cyan', bold=True))
        
        # User count
        users, total_users = auth_service.list_users(limit=1)
        click.echo(f"👥 Users: {total_users}")
        
        # Active sessions
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE expires_at > datetime('now')")
            active_sessions = cursor.fetchone()[0]
        
        click.echo(f"🔑 Active Sessions: {active_sessions}")
        
        # Audit logs
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM audit_log")
            audit_count = cursor.fetchone()[0]
        
        click.echo(f"📝 Audit Logs: {audit_count}")
        
        # Privacy settings
        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM privacy_settings")
            privacy_count = cursor.fetchone()[0]
        
        click.echo(f"🔐 Privacy Settings: {privacy_count} configured")
        
        # Encryption
        try:
            enc_service = EncryptionService()
            if enc_service.verify_key():
                click.echo(click.style("✓ Encryption: Enabled", fg='green'))
            else:
                click.echo(click.style("✗ Encryption: Key verification failed", fg='red'))
        except:
            click.echo(click.style("✗ Encryption: Not initialized", fg='yellow'))
        
        click.echo("\n" + click.style("Epic 6 system is operational!", fg='green', bold=True))
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        sys.exit(1)


@cli.command()
def version():
    """Show Epic 6 version information"""
    click.echo(click.style("\n🏆 AI Home Security - Epic 6", fg='cyan', bold=True))
    click.echo(click.style("Security & Privacy Controls\n", fg='cyan'))
    click.echo("Version: 1.0.0")
    click.echo("Features:")
    click.echo("  ✓ User Authentication (JWT)")
    click.echo("  ✓ Multi-Factor Authentication (TOTP)")
    click.echo("  ✓ Role-Based Access Control")
    click.echo("  ✓ Data Encryption")
    click.echo("  ✓ Privacy Controls")
    click.echo("  ✓ Audit Logging")
    click.echo("  ✓ Data Export/Deletion (GDPR)")
    click.echo("\nFor help: python scripts/epic6_cli.py --help\n")


if __name__ == '__main__':
    cli()




