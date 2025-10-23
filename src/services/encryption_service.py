"""
Encryption service for data-at-rest and key management.
Provides encryption for sensitive configuration data and file encryption.
"""

import os
import logging
import json
import base64
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import secrets

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data.
    Uses Fernet (symmetric encryption) for configuration data.
    """
    
    def __init__(self, key_file: Optional[str] = None, master_password: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            key_file: Path to key file (will be created if doesn't exist)
            master_password: Master password for key derivation
        """
        self.key_file = key_file or os.path.join(os.path.expanduser('~'), '.ai_security_key')
        self.master_password = master_password
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with key from file or generate new key"""
        try:
            # Try to load existing key
            if os.path.exists(self.key_file):
                logger.info(f"Loading encryption key from {self.key_file}")
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                
                # Verify key is valid Fernet key
                try:
                    self._fernet = Fernet(key)
                    logger.info("Encryption key loaded successfully")
                except Exception as e:
                    logger.error(f"Invalid encryption key: {e}")
                    raise ValueError("Invalid encryption key file")
            
            else:
                # Generate new key
                logger.warning(f"No encryption key found, generating new key at {self.key_file}")
                key = Fernet.generate_key()
                
                # Save key securely
                key_path = Path(self.key_file)
                key_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                
                # Set secure permissions (owner read/write only)
                os.chmod(self.key_file, 0o600)
                
                self._fernet = Fernet(key)
                logger.info(f"New encryption key generated and saved to {self.key_file}")
                logger.warning("⚠️  IMPORTANT: Back up this key file in a secure location!")
        
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt string data.
        
        Args:
            data: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted = self._fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted string
        """
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or corrupted data")
            raise ValueError("Decryption failed: Invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary data (serializes to JSON first).
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            json_str = json.dumps(data)
            return self.encrypt(json_str)
        except Exception as e:
            logger.error(f"Dictionary encryption failed: {e}")
            raise
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt and parse dictionary data.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted dictionary
        """
        try:
            json_str = self.decrypt(encrypted_data)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Dictionary decryption failed: {e}")
            raise
    
    def encrypt_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """
        Encrypt a file.
        
        Args:
            input_file: Path to file to encrypt
            output_file: Path to encrypted output file (optional)
            
        Returns:
            Path to encrypted file
        """
        try:
            if output_file is None:
                output_file = f"{input_file}.encrypted"
            
            with open(input_file, 'rb') as f:
                data = f.read()
            
            encrypted = self._fernet.encrypt(data)
            
            with open(output_file, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"File encrypted: {input_file} -> {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise
    
    def decrypt_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """
        Decrypt a file.
        
        Args:
            input_file: Path to encrypted file
            output_file: Path to decrypted output file (optional)
            
        Returns:
            Path to decrypted file
        """
        try:
            if output_file is None:
                if input_file.endswith('.encrypted'):
                    output_file = input_file[:-10]  # Remove .encrypted extension
                else:
                    output_file = f"{input_file}.decrypted"
            
            with open(input_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted = self._fernet.decrypt(encrypted_data)
            
            with open(output_file, 'wb') as f:
                f.write(decrypted)
            
            logger.info(f"File decrypted: {input_file} -> {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise
    
    def rotate_key(self, new_key_file: Optional[str] = None) -> str:
        """
        Generate new encryption key and save to file.
        NOTE: You'll need to re-encrypt all data with the new key!
        
        Args:
            new_key_file: Path for new key file (optional)
            
        Returns:
            Path to new key file
        """
        try:
            new_key = Fernet.generate_key()
            
            key_file = new_key_file or self.key_file
            
            # Backup old key
            if os.path.exists(key_file):
                backup_file = f"{key_file}.backup.{secrets.token_hex(8)}"
                os.rename(key_file, backup_file)
                logger.info(f"Old key backed up to {backup_file}")
            
            # Save new key
            with open(key_file, 'wb') as f:
                f.write(new_key)
            
            os.chmod(key_file, 0o600)
            
            # Update current Fernet instance
            self._fernet = Fernet(new_key)
            
            logger.warning(f"⚠️  Encryption key rotated. Old data must be re-encrypted!")
            logger.info(f"New key saved to {key_file}")
            
            return key_file
        
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise
    
    def verify_key(self) -> bool:
        """
        Verify that the encryption key is valid by attempting a test encryption/decryption.
        
        Returns:
            True if key is valid
        """
        try:
            test_data = "test_encryption_key_validity"
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
        except Exception as e:
            logger.error(f"Key verification failed: {e}")
            return False


class KeyManager:
    """
    Manages encryption keys and key derivation.
    """
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if None)
            
        Returns:
            (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key, salt
    
    @staticmethod
    def generate_random_key() -> bytes:
        """Generate a random Fernet key."""
        return Fernet.generate_key()
    
    @staticmethod
    def generate_secret_token(length: int = 32) -> str:
        """Generate a random secret token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_data(data: str) -> str:
        """
        Hash data using SHA-256.
        
        Args:
            data: String to hash
            
        Returns:
            Hex-encoded hash
        """
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data.encode('utf-8'))
        return digest.finalize().hex()


class ConfigEncryption:
    """
    Helper for encrypting sensitive configuration values.
    """
    
    def __init__(self, encryption_service: EncryptionService):
        """
        Initialize config encryption helper.
        
        Args:
            encryption_service: EncryptionService instance
        """
        self.encryption = encryption_service
    
    def encrypt_config_value(self, value: Any) -> Dict[str, str]:
        """
        Encrypt a configuration value.
        
        Returns:
            Dict with 'encrypted' key containing encrypted value
        """
        if isinstance(value, (dict, list)):
            json_str = json.dumps(value)
            encrypted = self.encryption.encrypt(json_str)
        else:
            encrypted = self.encryption.encrypt(str(value))
        
        return {
            'encrypted': True,
            'value': encrypted
        }
    
    def decrypt_config_value(self, encrypted_value: Dict[str, str]) -> Any:
        """
        Decrypt a configuration value.
        
        Args:
            encrypted_value: Dict with 'encrypted' and 'value' keys
            
        Returns:
            Decrypted value
        """
        if not encrypted_value.get('encrypted'):
            return encrypted_value.get('value')
        
        decrypted = self.encryption.decrypt(encrypted_value['value'])
        
        # Try to parse as JSON (for dict/list values)
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return decrypted
    
    def encrypt_sensitive_config(self, config: Dict[str, Any], sensitive_keys: list) -> Dict[str, Any]:
        """
        Encrypt sensitive keys in a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            sensitive_keys: List of keys to encrypt
            
        Returns:
            Config with sensitive values encrypted
        """
        encrypted_config = config.copy()
        
        for key in sensitive_keys:
            if key in encrypted_config:
                encrypted_config[key] = self.encrypt_config_value(encrypted_config[key])
        
        return encrypted_config
    
    def decrypt_sensitive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt all encrypted values in a configuration dictionary.
        
        Args:
            config: Configuration dictionary with encrypted values
            
        Returns:
            Config with decrypted values
        """
        decrypted_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict) and value.get('encrypted'):
                decrypted_config[key] = self.decrypt_config_value(value)
            else:
                decrypted_config[key] = value
        
        return decrypted_config


class TLSHelper:
    """
    Helper for TLS/SSL configuration and certificate generation.
    """
    
    @staticmethod
    def generate_self_signed_cert(
        cert_file: str,
        key_file: str,
        common_name: str = "localhost",
        days_valid: int = 365
    ) -> Tuple[str, str]:
        """
        Generate a self-signed SSL certificate.
        
        Args:
            cert_file: Path to save certificate
            key_file: Path to save private key
            common_name: Common name for certificate
            days_valid: Days certificate is valid
            
        Returns:
            (cert_file_path, key_file_path)
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from datetime import datetime, timedelta
            from ipaddress import IPv4Address
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AI Home Security"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=days_valid)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(common_name),
                    x509.DNSName("localhost"),
                    x509.IPAddress(IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Write private key
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            os.chmod(key_file, 0o600)
            
            # Write certificate
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            logger.info(f"Self-signed certificate generated: {cert_file}, {key_file}")
            logger.warning("⚠️  Self-signed certificate - use proper CA cert in production!")
            
            return cert_file, key_file
        
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            raise
    
    @staticmethod
    def get_tls_config_for_flask(cert_file: str, key_file: str) -> Dict[str, str]:
        """
        Get TLS configuration dict for Flask app.
        
        Returns:
            Dict with ssl_context parameters
        """
        return {
            'ssl_context': (cert_file, key_file)
        }
    
    @staticmethod
    def verify_cert_files(cert_file: str, key_file: str) -> bool:
        """
        Verify that certificate and key files exist and are readable.
        
        Returns:
            True if files are valid
        """
        try:
            if not os.path.exists(cert_file):
                logger.error(f"Certificate file not found: {cert_file}")
                return False
            
            if not os.path.exists(key_file):
                logger.error(f"Key file not found: {key_file}")
                return False
            
            # Try to read files
            with open(cert_file, 'r') as f:
                cert_data = f.read()
                if 'BEGIN CERTIFICATE' not in cert_data:
                    logger.error("Invalid certificate file format")
                    return False
            
            with open(key_file, 'r') as f:
                key_data = f.read()
                if 'BEGIN' not in key_data:
                    logger.error("Invalid key file format")
                    return False
            
            logger.info("TLS certificate files verified")
            return True
        
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return False


# Convenience functions
def create_encryption_service(key_file: Optional[str] = None) -> EncryptionService:
    """Create and return an EncryptionService instance."""
    return EncryptionService(key_file=key_file)


def encrypt_string(data: str, key_file: Optional[str] = None) -> str:
    """Convenience function to encrypt a string."""
    service = create_encryption_service(key_file)
    return service.encrypt(data)


def decrypt_string(encrypted_data: str, key_file: Optional[str] = None) -> str:
    """Convenience function to decrypt a string."""
    service = create_encryption_service(key_file)
    return service.decrypt(encrypted_data)




