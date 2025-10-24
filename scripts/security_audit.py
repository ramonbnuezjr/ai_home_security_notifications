#!/usr/bin/env python3
"""
Security audit script for AI Home Security System.
Performs comprehensive security checks on the system.
"""

import sys
import os
import stat
import logging
from pathlib import Path
from typing import List, Tuple, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import config loader if available
try:
    from src.utils.config import load_config
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    def load_config(path):
        """Dummy function if yaml not available"""
        return {}

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityAudit:
    """Security audit checker"""
    
    def __init__(self):
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: List[str] = []
        self.project_root = Path(__file__).parent.parent
    
    def add_issue(self, category: str, message: str, severity: str = 'HIGH'):
        """Add a security issue"""
        self.issues.append({
            'category': category,
            'message': message,
            'severity': severity
        })
    
    def add_warning(self, category: str, message: str):
        """Add a security warning"""
        self.warnings.append({
            'category': category,
            'message': message
        })
    
    def add_pass(self, message: str):
        """Add a passed check"""
        self.passed.append(message)
    
    def check_config_security(self):
        """Check configuration security"""
        logger.info("Checking configuration security...")
        
        config_path = self.project_root / "config" / "system_config.yaml"
        
        if not config_path.exists():
            self.add_warning("Configuration", f"Config file not found: {config_path}")
            return
        
        if not HAS_YAML:
            self.add_warning("Configuration", "PyYAML not installed, skipping config content checks")
            # Still check file permissions
            file_stat = config_path.stat()
            if file_stat.st_mode & stat.S_IROTH:
                self.add_issue(
                    "Configuration",
                    f"Config file is world-readable: {config_path}. Run: chmod 600 {config_path}",
                    "MEDIUM"
                )
            else:
                self.add_pass("Config file permissions are secure")
            return
        
        # Check file permissions
        file_stat = config_path.stat()
        file_mode = stat.filemode(file_stat.st_mode)
        
        # Should not be world-readable (contains sensitive data)
        if file_stat.st_mode & stat.S_IROTH:
            self.add_issue(
                "Configuration",
                f"Config file is world-readable: {config_path}. Run: chmod 600 {config_path}",
                "MEDIUM"
            )
        else:
            self.add_pass(f"Config file permissions are secure: {file_mode}")
        
        # Check for sensitive data in config
        try:
            config = load_config(str(config_path))
            
            # Check for default/weak secret keys
            web_config = config.get('web', {})
            secret_key = web_config.get('secret_key', '')
            
            if not secret_key or secret_key == 'dev-key-change-in-production':
                self.add_issue(
                    "Configuration",
                    "Default/weak secret key detected. Generate a strong random key.",
                    "HIGH"
                )
            elif len(secret_key) < 32:
                self.add_warning(
                    "Configuration",
                    "Secret key should be at least 32 characters long"
                )
            else:
                self.add_pass("Secret key is configured")
            
            # Check for HTTPS configuration
            use_https = web_config.get('use_https', False)
            if not use_https:
                self.add_warning(
                    "Configuration",
                    "HTTPS is not enabled. Run: python scripts/setup_https.py"
                )
            else:
                self.add_pass("HTTPS is enabled in configuration")
            
            # Check for production debug mode
            if web_config.get('debug', False):
                self.add_issue(
                    "Configuration",
                    "Debug mode is enabled. Disable for production.",
                    "HIGH"
                )
            else:
                self.add_pass("Debug mode is disabled")
        
        except Exception as e:
            self.add_warning("Configuration", f"Failed to parse config: {e}")
    
    def check_database_security(self):
        """Check database security"""
        logger.info("Checking database security...")
        
        db_path = self.project_root / "data" / "security_events.db"
        
        if not db_path.exists():
            self.add_pass("Database does not exist yet (will be created on first run)")
            return
        
        # Check file permissions
        file_stat = db_path.stat()
        
        if file_stat.st_mode & stat.S_IROTH or file_stat.st_mode & stat.S_IWOTH:
            self.add_issue(
                "Database",
                f"Database has insecure permissions: {db_path}. Run: chmod 600 {db_path}",
                "HIGH"
            )
        else:
            self.add_pass("Database file permissions are secure")
    
    def check_certificate_security(self):
        """Check TLS certificate security"""
        logger.info("Checking TLS certificate security...")
        
        cert_dir = self.project_root / "config" / "certs"
        
        if not cert_dir.exists():
            self.add_warning(
                "TLS",
                "TLS certificates not found. Run: python scripts/setup_https.py"
            )
            return
        
        cert_path = cert_dir / "cert.pem"
        key_path = cert_dir / "key.pem"
        
        if not cert_path.exists():
            self.add_warning("TLS", "Certificate file not found")
        
        if not key_path.exists():
            self.add_warning("TLS", "Private key file not found")
        
        if key_path.exists():
            # Check private key permissions
            key_stat = key_path.stat()
            
            if key_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                self.add_issue(
                    "TLS",
                    f"Private key has insecure permissions: {key_path}. Run: chmod 600 {key_path}",
                    "CRITICAL"
                )
            else:
                self.add_pass("Private key permissions are secure")
    
    def check_code_security(self):
        """Check code security patterns"""
        logger.info("Checking code security patterns...")
        
        # Check for hardcoded secrets
        patterns_to_check = [
            ('password', 'Hardcoded passwords'),
            ('api_key', 'Hardcoded API keys'),
            ('secret', 'Hardcoded secrets'),
        ]
        
        suspicious_files = []
        
        # Scan Python files
        for py_file in self.project_root.rglob('*.py'):
            # Skip this audit script and test files
            if 'security_audit.py' in str(py_file) or 'test' in str(py_file).lower():
                continue
            
            try:
                content = py_file.read_text().lower()
                
                for pattern, description in patterns_to_check:
                    if f'{pattern} =' in content or f'{pattern}=' in content:
                        # Simple check - may have false positives
                        suspicious_files.append((py_file, description))
                        break
            
            except Exception:
                pass
        
        if suspicious_files:
            self.add_warning(
                "Code Security",
                f"Found {len(suspicious_files)} files with potential hardcoded secrets. Manual review recommended."
            )
        else:
            self.add_pass("No obvious hardcoded secrets found")
    
    def check_dependencies(self):
        """Check for dependency security issues"""
        logger.info("Checking dependencies...")
        
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            self.add_warning("Dependencies", "requirements.txt not found")
            return
        
        try:
            requirements = requirements_file.read_text()
            
            # Check for unpinned dependencies (security risk)
            unpinned = []
            for line in requirements.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' not in line and '>=' not in line:
                        unpinned.append(line)
            
            if unpinned:
                self.add_warning(
                    "Dependencies",
                    f"Found {len(unpinned)} unpinned dependencies. Consider pinning versions."
                )
            else:
                self.add_pass("All dependencies are pinned")
        
        except Exception as e:
            self.add_warning("Dependencies", f"Failed to check requirements: {e}")
    
    def check_authentication(self):
        """Check authentication implementation"""
        logger.info("Checking authentication implementation...")
        
        # Check if auth service exists
        auth_service = self.project_root / "src" / "services" / "auth_service.py"
        
        if not auth_service.exists():
            self.add_issue(
                "Authentication",
                "Authentication service not found",
                "CRITICAL"
            )
            return
        
        self.add_pass("Authentication service exists")
        
        # Check if auth middleware is applied
        auth_api = self.project_root / "src" / "web" / "api" / "auth.py"
        
        if auth_api.exists():
            content = auth_api.read_text()
            
            if 'require_auth' in content and 'require_role' in content:
                self.add_pass("Authentication decorators are implemented")
            else:
                self.add_warning(
                    "Authentication",
                    "Authentication decorators may not be fully implemented"
                )
    
    def check_encryption(self):
        """Check encryption implementation"""
        logger.info("Checking encryption implementation...")
        
        encryption_service = self.project_root / "src" / "services" / "encryption_service.py"
        
        if not encryption_service.exists():
            self.add_issue(
                "Encryption",
                "Encryption service not found",
                "HIGH"
            )
            return
        
        self.add_pass("Encryption service exists")
        
        # Check for encryption key file
        encryption_key = self.project_root / "config" / ".encryption_key"
        
        if encryption_key.exists():
            key_stat = encryption_key.stat()
            
            if key_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
                self.add_issue(
                    "Encryption",
                    f"Encryption key has insecure permissions: {encryption_key}. Run: chmod 600 {encryption_key}",
                    "CRITICAL"
                )
            else:
                self.add_pass("Encryption key permissions are secure")
    
    def run_audit(self) -> Tuple[int, int, int]:
        """
        Run all security checks.
        
        Returns:
            Tuple of (issues_count, warnings_count, passed_count)
        """
        print("\n" + "=" * 60)
        print("🔒 AI Home Security System - Security Audit")
        print("=" * 60 + "\n")
        
        self.check_config_security()
        self.check_database_security()
        self.check_certificate_security()
        self.check_code_security()
        self.check_dependencies()
        self.check_authentication()
        self.check_encryption()
        
        # Print results
        print("\n" + "=" * 60)
        print("AUDIT RESULTS")
        print("=" * 60 + "\n")
        
        # Print issues
        if self.issues:
            print(f"❌ SECURITY ISSUES ({len(self.issues)}):\n")
            for issue in self.issues:
                severity_icon = "🔴" if issue['severity'] == 'CRITICAL' else "🟠" if issue['severity'] == 'HIGH' else "🟡"
                print(f"{severity_icon} [{issue['severity']}] {issue['category']}: {issue['message']}")
            print()
        
        # Print warnings
        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):\n")
            for warning in self.warnings:
                print(f"   {warning['category']}: {warning['message']}")
            print()
        
        # Print passed checks
        if self.passed:
            print(f"✅ PASSED CHECKS ({len(self.passed)}):\n")
            for check in self.passed:
                print(f"   ✓ {check}")
            print()
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Issues:   {len(self.issues)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Passed:   {len(self.passed)}")
        print()
        
        if len(self.issues) == 0 and len(self.warnings) == 0:
            print("🎉 All security checks passed!")
        elif len(self.issues) == 0:
            print("✓ No critical issues found, but there are some warnings to address.")
        else:
            print("❌ Security issues found! Please address them before deploying to production.")
        
        print()
        
        return len(self.issues), len(self.warnings), len(self.passed)


def main():
    """Run security audit"""
    try:
        audit = SecurityAudit()
        issues_count, warnings_count, passed_count = audit.run_audit()
        
        # Exit with error code if critical issues found
        if issues_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

