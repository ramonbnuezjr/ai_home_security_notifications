"""
Unit tests for EncryptionService - Epic 6
Tests encryption/decryption, file operations, key management, and TLS helpers.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
import tempfile
import os
import json

from src.services.encryption_service import (
    EncryptionService, 
    KeyManager, 
    ConfigEncryption,
    TLSHelper
)


class TestEncryptionService(unittest.TestCase):
    """Test EncryptionService functionality"""
    
    def setUp(self):
        """Set up test encryption service"""
        # Create temporary key file
        self.key_fd, self.key_file = tempfile.mkstemp(suffix='.key')
        os.close(self.key_fd)
        os.unlink(self.key_file)  # Remove so service creates it
        
        self.enc_service = EncryptionService(key_file=self.key_file)
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.key_file):
            os.unlink(self.key_file)
    
    def test_encrypt_decrypt_string(self):
        """Test basic string encryption and decryption"""
        original_data = "This is secret data"
        
        # Encrypt
        encrypted = self.enc_service.encrypt(original_data)
        self.assertNotEqual(encrypted, original_data)
        
        # Decrypt
        decrypted = self.enc_service.decrypt(encrypted)
        self.assertEqual(decrypted, original_data)
    
    def test_encrypt_decrypt_unicode(self):
        """Test encryption with unicode characters"""
        original_data = "Ñoño 中文 العربية 🔒"
        
        encrypted = self.enc_service.encrypt(original_data)
        decrypted = self.enc_service.decrypt(encrypted)
        
        self.assertEqual(decrypted, original_data)
    
    def test_encrypt_decrypt_dict(self):
        """Test dictionary encryption and decryption"""
        original_data = {
            'username': 'testuser',
            'password': 'secret123',
            'api_key': 'abc123def456',
            'config': {
                'nested': 'value'
            }
        }
        
        # Encrypt
        encrypted = self.enc_service.encrypt_dict(original_data)
        self.assertIsInstance(encrypted, str)
        
        # Decrypt
        decrypted = self.enc_service.decrypt_dict(encrypted)
        self.assertEqual(decrypted, original_data)
    
    def test_decrypt_invalid_data_fails(self):
        """Test decryption of invalid data raises error"""
        with self.assertRaises(Exception):
            self.enc_service.decrypt("invalid_encrypted_data")
    
    def test_encrypt_file(self):
        """Test file encryption"""
        # Create test file
        test_fd, test_file = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(test_fd, 'w') as f:
            f.write("This is secret file content")
        
        try:
            # Encrypt file
            encrypted_file = self.enc_service.encrypt_file(test_file)
            
            self.assertTrue(os.path.exists(encrypted_file))
            self.assertTrue(encrypted_file.endswith('.encrypted'))
            
            # Verify encrypted content is different
            with open(encrypted_file, 'rb') as f:
                encrypted_content = f.read()
            
            with open(test_file, 'rb') as f:
                original_content = f.read()
            
            self.assertNotEqual(encrypted_content, original_content)
        
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
            if os.path.exists(encrypted_file):
                os.unlink(encrypted_file)
    
    def test_decrypt_file(self):
        """Test file decryption"""
        # Create and encrypt test file
        test_fd, test_file = tempfile.mkstemp(suffix='.txt')
        original_content = b"This is secret file content"
        with os.fdopen(test_fd, 'wb') as f:
            f.write(original_content)
        
        try:
            # Encrypt file
            encrypted_file = self.enc_service.encrypt_file(test_file)
            
            # Decrypt file
            decrypted_file = self.enc_service.decrypt_file(encrypted_file)
            
            # Verify decrypted content matches original
            with open(decrypted_file, 'rb') as f:
                decrypted_content = f.read()
            
            self.assertEqual(decrypted_content, original_content)
        
        finally:
            # Cleanup
            for f in [test_file, encrypted_file, decrypted_file]:
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_verify_key(self):
        """Test key verification"""
        is_valid = self.enc_service.verify_key()
        self.assertTrue(is_valid)
    
    def test_rotate_key(self):
        """Test key rotation"""
        # Get original key
        with open(self.key_file, 'rb') as f:
            original_key = f.read()
        
        # Rotate key
        new_key_file = self.enc_service.rotate_key()
        
        # Verify new key is different
        with open(new_key_file, 'rb') as f:
            new_key = f.read()
        
        self.assertNotEqual(original_key, new_key)
        
        # Verify backup was created
        backup_files = [f for f in os.listdir(os.path.dirname(self.key_file)) 
                       if f.startswith(os.path.basename(self.key_file) + '.backup')]
        self.assertGreater(len(backup_files), 0)
        
        # Cleanup backup
        for backup in backup_files:
            os.unlink(os.path.join(os.path.dirname(self.key_file), backup))


class TestKeyManager(unittest.TestCase):
    """Test KeyManager functionality"""
    
    def test_derive_key_from_password(self):
        """Test key derivation from password"""
        password = "SecurePassword123!"
        
        key1, salt1 = KeyManager.derive_key_from_password(password)
        
        self.assertIsNotNone(key1)
        self.assertIsNotNone(salt1)
        self.assertEqual(len(salt1), 16)  # Salt should be 16 bytes
        
        # Same password with same salt should produce same key
        key2, salt2 = KeyManager.derive_key_from_password(password, salt=salt1)
        self.assertEqual(key1, key2)
    
    def test_generate_random_key(self):
        """Test random key generation"""
        key1 = KeyManager.generate_random_key()
        key2 = KeyManager.generate_random_key()
        
        self.assertIsNotNone(key1)
        self.assertIsNotNone(key2)
        self.assertNotEqual(key1, key2)  # Keys should be different
    
    def test_generate_secret_token(self):
        """Test secret token generation"""
        token1 = KeyManager.generate_secret_token()
        token2 = KeyManager.generate_secret_token()
        
        self.assertIsNotNone(token1)
        self.assertIsNotNone(token2)
        self.assertNotEqual(token1, token2)
        self.assertGreater(len(token1), 20)  # Should be reasonably long
    
    def test_hash_data(self):
        """Test data hashing"""
        data = "test data to hash"
        
        hash1 = KeyManager.hash_data(data)
        hash2 = KeyManager.hash_data(data)
        
        self.assertEqual(hash1, hash2)  # Same data should produce same hash
        self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 hex characters
        
        # Different data should produce different hash
        hash3 = KeyManager.hash_data("different data")
        self.assertNotEqual(hash1, hash3)


class TestConfigEncryption(unittest.TestCase):
    """Test ConfigEncryption helper"""
    
    def setUp(self):
        """Set up test encryption"""
        self.key_fd, self.key_file = tempfile.mkstemp(suffix='.key')
        os.close(self.key_fd)
        os.unlink(self.key_file)
        
        self.enc_service = EncryptionService(key_file=self.key_file)
        self.config_enc = ConfigEncryption(self.enc_service)
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.key_file):
            os.unlink(self.key_file)
    
    def test_encrypt_config_value_string(self):
        """Test encrypting config string value"""
        value = "secret_api_key_123"
        
        encrypted = self.config_enc.encrypt_config_value(value)
        
        self.assertIsInstance(encrypted, dict)
        self.assertTrue(encrypted.get('encrypted'))
        self.assertIsNotNone(encrypted.get('value'))
    
    def test_decrypt_config_value(self):
        """Test decrypting config value"""
        original_value = "secret_api_key_123"
        
        encrypted = self.config_enc.encrypt_config_value(original_value)
        decrypted = self.config_enc.decrypt_config_value(encrypted)
        
        self.assertEqual(decrypted, original_value)
    
    def test_encrypt_sensitive_config(self):
        """Test encrypting sensitive keys in config"""
        config = {
            'api_key': 'secret123',
            'database_password': 'dbpass456',
            'public_setting': 'not_secret',
            'smtp_password': 'smtppass789'
        }
        
        sensitive_keys = ['api_key', 'database_password', 'smtp_password']
        
        encrypted_config = self.config_enc.encrypt_sensitive_config(config, sensitive_keys)
        
        # Sensitive keys should be encrypted
        self.assertTrue(encrypted_config['api_key'].get('encrypted'))
        self.assertTrue(encrypted_config['database_password'].get('encrypted'))
        self.assertTrue(encrypted_config['smtp_password'].get('encrypted'))
        
        # Public setting should not be encrypted
        self.assertEqual(encrypted_config['public_setting'], 'not_secret')
    
    def test_decrypt_sensitive_config(self):
        """Test decrypting sensitive config"""
        config = {
            'api_key': 'secret123',
            'database_password': 'dbpass456',
            'public_setting': 'not_secret'
        }
        
        sensitive_keys = ['api_key', 'database_password']
        
        # Encrypt
        encrypted_config = self.config_enc.encrypt_sensitive_config(config, sensitive_keys)
        
        # Decrypt
        decrypted_config = self.config_enc.decrypt_sensitive_config(encrypted_config)
        
        # Should match original
        self.assertEqual(decrypted_config['api_key'], 'secret123')
        self.assertEqual(decrypted_config['database_password'], 'dbpass456')
        self.assertEqual(decrypted_config['public_setting'], 'not_secret')


class TestTLSHelper(unittest.TestCase):
    """Test TLS helper functionality"""
    
    def test_generate_self_signed_cert(self):
        """Test self-signed certificate generation"""
        # Create temp directory for certs
        with tempfile.TemporaryDirectory() as temp_dir:
            cert_file = os.path.join(temp_dir, 'cert.pem')
            key_file = os.path.join(temp_dir, 'key.pem')
            
            # Generate certificate
            cert_path, key_path = TLSHelper.generate_self_signed_cert(
                cert_file=cert_file,
                key_file=key_file,
                common_name="test.localhost",
                days_valid=30
            )
            
            # Verify files were created
            self.assertTrue(os.path.exists(cert_path))
            self.assertTrue(os.path.exists(key_path))
            
            # Verify content
            with open(cert_path, 'r') as f:
                cert_content = f.read()
                self.assertIn('BEGIN CERTIFICATE', cert_content)
            
            with open(key_path, 'r') as f:
                key_content = f.read()
                self.assertIn('BEGIN', key_content)
    
    def test_verify_cert_files(self):
        """Test certificate file verification"""
        # Create valid cert files
        with tempfile.TemporaryDirectory() as temp_dir:
            cert_file = os.path.join(temp_dir, 'cert.pem')
            key_file = os.path.join(temp_dir, 'key.pem')
            
            TLSHelper.generate_self_signed_cert(
                cert_file=cert_file,
                key_file=key_file
            )
            
            # Verify valid files
            is_valid = TLSHelper.verify_cert_files(cert_file, key_file)
            self.assertTrue(is_valid)
    
    def test_verify_cert_files_missing(self):
        """Test verification fails with missing files"""
        is_valid = TLSHelper.verify_cert_files(
            '/nonexistent/cert.pem',
            '/nonexistent/key.pem'
        )
        self.assertFalse(is_valid)
    
    def test_get_tls_config_for_flask(self):
        """Test getting TLS config for Flask"""
        config = TLSHelper.get_tls_config_for_flask('cert.pem', 'key.pem')
        
        self.assertIsInstance(config, dict)
        self.assertIn('ssl_context', config)
        self.assertEqual(config['ssl_context'], ('cert.pem', 'key.pem'))


if __name__ == '__main__':
    unittest.main()

