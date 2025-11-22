# User Settings Encryption Helper
from cryptography.fernet import Fernet
import os
import base64
from typing import Optional

class SettingsEncryption:
    """Handles encryption/decryption of sensitive user settings"""
    
    def __init__(self):
        # Get or generate encryption key
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate new one"""
        key_str = os.getenv('SETTINGS_ENCRYPTION_KEY')
        
        if key_str:
            return base64.urlsafe_b64decode(key_str.encode())
        
        # Generate new key (in production, this should be set in env)
        key = Fernet.generate_key()
        print(f"⚠️  WARNING: Generated new encryption key. Add to .env:")
        print(f"SETTINGS_ENCRYPTION_KEY={base64.urlsafe_b64encode(key).decode()}")
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value"""
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt a string value"""
        if not ciphertext:
            return None
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None


# Global instance
encryption = SettingsEncryption()
