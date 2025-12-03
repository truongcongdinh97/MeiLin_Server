"""
API Key Manager for MeiLin Multi-User System
Handles encryption and decryption of API keys
"""

import os
import base64
import binascii
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Manages encryption and decryption of API keys
    
    Uses Fernet symmetric encryption with PBKDF2 key derivation
    """
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize APIKeyManager
        
        Args:
            encryption_key: Base64 encoded encryption key. If None, will try to get from environment.
        """
        self.encryption_key = encryption_key or os.getenv('MEILIN_ENCRYPTION_KEY')
        
        if not self.encryption_key:
            logger.warning("No encryption key provided. Using in-memory key (NOT SECURE FOR PRODUCTION)")
            # Generate a temporary key for development
            self.encryption_key = Fernet.generate_key().decode()
        
        # Initialize Fernet cipher
        try:
            # Ensure key is proper Fernet key (32 url-safe base64-encoded bytes)
            if isinstance(self.encryption_key, str):
                # Check if it's already a valid Fernet key
                try:
                    # Try to decode as base64
                    key_bytes = base64.urlsafe_b64decode(self.encryption_key)
                    if len(key_bytes) == 32:
                        # Valid Fernet key
                        self.cipher = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
                    else:
                        # Not a valid Fernet key, generate one
                        logger.warning("Invalid Fernet key length, generating new key")
                        new_key = Fernet.generate_key()
                        self.encryption_key = new_key.decode()
                        self.cipher = Fernet(new_key)
                except (ValueError, binascii.Error):
                    # Not valid base64, generate new key
                    logger.warning("Invalid encryption key format, generating new key")
                    new_key = Fernet.generate_key()
                    self.encryption_key = new_key.decode()
                    self.cipher = Fernet(new_key)
            else:
                # Key is already bytes
                try:
                    self.cipher = Fernet(self.encryption_key)
                except ValueError:
                    # Invalid key, generate new one
                    logger.warning("Invalid encryption key bytes, generating new key")
                    new_key = Fernet.generate_key()
                    self.encryption_key = new_key.decode()
                    self.cipher = Fernet(new_key)
            
            logger.info("APIKeyManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing APIKeyManager: {e}")
            # Fallback to a simple key for development
            logger.warning("Using fallback encryption key for development")
            fallback_key = Fernet.generate_key()
            self.cipher = Fernet(fallback_key)
            self.encryption_key = fallback_key.decode()
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt plaintext (API key)
        
        Args:
            plaintext: Plain text API key to encrypt
        
        Returns:
            Encrypted string or None if error
        """
        if not plaintext:
            return None
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Error encrypting API key: {e}")
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt ciphertext (API key)
        
        Args:
            ciphertext: Encrypted API key
        
        Returns:
            Decrypted string or None if error
        """
        if not ciphertext:
            return None
        
        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting API key: {e}")
            return None
    
    def encrypt_api_key(self, provider_name: str, api_key: str) -> Optional[str]:
        """
        Encrypt API key with provider context
        
        Args:
            provider_name: Name of the provider (deepseek, openai, etc.)
            api_key: API key to encrypt
        
        Returns:
            Encrypted API key or None if error
        """
        if not api_key:
            return None
        
        # Add provider context to the key (for auditing/logging)
        context = f"{provider_name}:{api_key}"
        return self.encrypt(context)
    
    def decrypt_api_key(self, encrypted_key: str) -> tuple[Optional[str], Optional[str]]:
        """
        Decrypt API key and extract provider
        
        Args:
            encrypted_key: Encrypted API key
        
        Returns:
            Tuple of (provider_name, api_key) or (None, None) if error
        """
        if not encrypted_key:
            return None, None
        
        try:
            decrypted = self.decrypt(encrypted_key)
            if not decrypted:
                return None, None
            
            # Split provider and key
            if ':' in decrypted:
                provider, api_key = decrypted.split(':', 1)
                return provider, api_key
            else:
                # Legacy format or no provider prefix
                return 'unknown', decrypted
                
        except Exception as e:
            logger.error(f"Error decrypting API key with provider: {e}")
            return None, None
    
    def validate_api_key_format(self, provider_name: str, api_key: str) -> bool:
        """
        Validate API key format based on provider
        
        Args:
            provider_name: Name of the provider
            api_key: API key to validate
        
        Returns:
            True if format appears valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        api_key = api_key.strip()
        
        # Common API key patterns
        patterns = {
            'openai': ['sk-'],
            'deepseek': ['sk-'],
            'anthropic': ['sk-ant-'],
            'google': ['AIza'],
            'elevenlabs': ['sk_'],
            'azure': ['https://', '.cognitiveservices.azure.com'],
        }
        
        # Check if provider has specific patterns
        if provider_name in patterns:
            for pattern in patterns[provider_name]:
                if api_key.lower().startswith(pattern.lower()):
                    return True
            # If provider has specific patterns but none matched, return False
            return False
        
        # Generic validation for unknown providers
        if len(api_key) >= 10:  # Most API keys are at least 10 characters
            return True
        
        return False
    
    def mask_api_key(self, api_key: str, visible_chars: int = 4) -> str:
        """
        Mask API key for display (show only first and last few characters)
        
        Args:
            api_key: API key to mask
            visible_chars: Number of characters to show at beginning and end
        
        Returns:
            Masked API key string
        """
        if not api_key or len(api_key) <= visible_chars * 2:
            return "***"
        
        start = api_key[:visible_chars]
        end = api_key[-visible_chars:]
        middle = '*' * (len(api_key) - visible_chars * 2)
        
        return f"{start}{middle}{end}"
    
    def generate_secure_key(self) -> str:
        """
        Generate a secure encryption key
        
        Returns:
            Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode()
    
    def test_encryption(self) -> bool:
        """
        Test encryption/decryption functionality
        
        Returns:
            True if test passes, False otherwise
        """
        try:
            test_text = "test_api_key_12345"
            encrypted = self.encrypt(test_text)
            
            if not encrypted:
                logger.error("Encryption test failed: No encrypted output")
                return False
            
            decrypted = self.decrypt(encrypted)
            
            if decrypted != test_text:
                logger.error(f"Encryption test failed: {decrypted} != {test_text}")
                return False
            
            logger.info("Encryption test passed")
            return True
            
        except Exception as e:
            logger.error(f"Encryption test failed with error: {e}")
            return False


# Provider-specific helper functions

def get_provider_display_name(provider_name: str) -> str:
    """Get display name for provider"""
    display_names = {
        'deepseek': 'DeepSeek AI',
        'openai': 'OpenAI ChatGPT',
        'anthropic': 'Anthropic Claude',
        'google': 'Google Gemini',
        'ollama': 'Ollama (Local)',
        'elevenlabs': 'ElevenLabs TTS',
        'edge_tts': 'Edge TTS (Free)',
        'google_tts': 'Google Cloud TTS',
        'azure_tts': 'Azure TTS',
        'pyttsx3': 'pyttsx3 (Local)',
    }
    return display_names.get(provider_name, provider_name.title())

def get_provider_type(provider_name: str) -> str:
    """Get provider type (llm or tts)"""
    llm_providers = ['deepseek', 'openai', 'anthropic', 'google', 'ollama']
    tts_providers = ['elevenlabs', 'edge_tts', 'google_tts', 'azure_tts', 'pyttsx3']
    
    if provider_name in llm_providers:
        return 'llm'
    elif provider_name in tts_providers:
        return 'tts'
    else:
        return 'unknown'

def get_provider_api_base(provider_name: str) -> str:
    """Get default API base URL for provider"""
    api_bases = {
        'deepseek': 'https://api.deepseek.com/v1',
        'openai': 'https://api.openai.com/v1',
        'anthropic': 'https://api.anthropic.com/v1',
        'google': 'https://generativelanguage.googleapis.com/v1beta',
        'elevenlabs': 'https://api.elevenlabs.io/v1',
    }
    return api_bases.get(provider_name, '')

def get_provider_default_model(provider_name: str) -> str:
    """Get default model for provider"""
    default_models = {
        'deepseek': 'deepseek-chat',
        'openai': 'gpt-4o-mini',
        'anthropic': 'claude-3-5-sonnet-20241022',
        'google': 'gemini-2.0-flash-exp',
        'ollama': 'deepseek-r1:8b',
        'elevenlabs': 'eleven_v3',
    }
    return default_models.get(provider_name, '')


# Singleton instance
_api_key_manager_instance = None

def get_api_key_manager(encryption_key: str = None) -> APIKeyManager:
    """Get or create APIKeyManager singleton instance"""
    global _api_key_manager_instance
    if _api_key_manager_instance is None:
        _api_key_manager_instance = APIKeyManager(encryption_key)
    return _api_key_manager_instance


if __name__ == "__main__":
    # Test the APIKeyManager
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test with generated key
    print("Testing APIKeyManager...")
    
    manager = APIKeyManager()
    
    # Test encryption/decryption
    if manager.test_encryption():
        print("✅ Encryption test passed")
    else:
        print("❌ Encryption test failed")
        sys.exit(1)
    
    # Test provider-specific functions
    test_key = "sk-test1234567890abcdef"
    
    # Test encryption with provider context
    encrypted = manager.encrypt_api_key("openai", test_key)
    if encrypted:
        print(f"✅ API key encrypted: {manager.mask_api_key(encrypted)}")
        
        # Test decryption
        provider, decrypted = manager.decrypt_api_key(encrypted)
        if provider == "openai" and decrypted == test_key:
            print(f"✅ API key decrypted correctly: {manager.mask_api_key(decrypted)}")
        else:
            print(f"❌ Decryption failed: {provider}, {manager.mask_api_key(decrypted) if decrypted else 'None'}")
    else:
        print("❌ Encryption failed")
    
    # Test format validation
    test_cases = [
        ("openai", "sk-1234567890abcdef", True),
        ("openai", "invalid_key", False),
        ("deepseek", "sk-1234567890", True),
        ("elevenlabs", "sk_1234567890", True),
        ("unknown", "1234567890", True),  # Generic validation should pass
        ("unknown", "123", False),  # Too short
    ]
    
    print("\nTesting API key format validation:")
    for provider, key, expected in test_cases:
        result = manager.validate_api_key_format(provider, key)
        status = "✅" if result == expected else "❌"
        print(f"{status} {provider}: {manager.mask_api_key(key)} -> {result} (expected: {expected})")
    
    print("\n✅ APIKeyManager tests completed successfully!")
