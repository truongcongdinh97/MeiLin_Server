"""
Provider Manager - Quản lý các AI providers (LLM + TTS)
Tự động load config, khởi tạo provider, và handle fallback
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from modules.config_loader import load_config_with_env

load_dotenv()

class ProviderManager:
    """Manager để quản lý tất cả AI providers"""
    
    def __init__(self, config_path: str = "config/ai_providers.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Lấy active providers
        self.active_llm = self.config['active']['llm']
        self.active_tts = self.config['active']['tts']
        
        # Lấy fallback providers
        self.fallback_enabled = self.config['fallback'].get('enabled', True)
        self.fallback_llm = self.config['fallback'].get('llm')
        self.fallback_tts = self.config['fallback'].get('tts')
        
        print(f"[ProviderManager] Active LLM: {self.active_llm}")
        print(f"[ProviderManager] Active TTS: {self.active_tts}")
    
    def _load_config(self) -> Dict:
        """Load config từ YAML file với env vars"""
        try:
            return load_config_with_env(self.config_path)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            raise
    
    def get_llm_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy config của LLM provider
        Args:
            provider_name: Tên provider (deepseek, openai, etc.). Nếu None, dùng active provider
        Returns:
            Dict chứa config đầy đủ của provider
        """
        provider_name = provider_name or self.active_llm
        
        if provider_name not in self.config['llm_providers']:
            raise ValueError(f"LLM provider '{provider_name}' không tồn tại trong config")
        
        provider_config = self.config['llm_providers'][provider_name]
        
        # Kiểm tra enabled
        if not provider_config.get('enabled', False):
            print(f"[WARNING] LLM provider '{provider_name}' chưa được bật trong config")
        
        # Lấy API key từ env
        api_key_env = provider_config.get('api_key_env')
        api_key = os.getenv(api_key_env) if api_key_env else None
        
        if api_key_env and not api_key:
            print(f"[WARNING] API key '{api_key_env}' không tìm thấy trong .env")
        
        return {
            'provider': provider_config['provider'],
            'api_url': provider_config['api_url'],
            'api_key': api_key,
            'default_model': provider_config['default_model'],
            'models': provider_config['models'],
            'default_params': provider_config['default_params'],
            'enabled': provider_config.get('enabled', False)
        }
    
    def get_tts_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy config của TTS provider
        Args:
            provider_name: Tên provider (elevenlabs, google_tts, etc.). Nếu None, dùng active provider
        Returns:
            Dict chứa config đầy đủ của provider
        """
        provider_name = provider_name or self.active_tts
        
        if provider_name not in self.config['tts_providers']:
            raise ValueError(f"TTS provider '{provider_name}' không tồn tại trong config")
        
        provider_config = self.config['tts_providers'][provider_name]
        
        # Kiểm tra enabled
        if not provider_config.get('enabled', False):
            print(f"[WARNING] TTS provider '{provider_name}' chưa được bật trong config")
        
        # Lấy API key từ env
        api_key_env = provider_config.get('api_key_env')
        api_key = os.getenv(api_key_env) if api_key_env else None
        
        if api_key_env and not api_key:
            print(f"[WARNING] API key '{api_key_env}' không tìm thấy trong .env")
        
        return {
            'provider': provider_config['provider'],
            'api_url': provider_config.get('api_url'),
            'api_key': api_key,
            'default_voice': provider_config.get('default_voice'),
            'voices': provider_config.get('voices', []),
            'default_model': provider_config.get('default_model'),
            'models': provider_config.get('models', []),
            'default_params': provider_config.get('default_params', {}),
            'enabled': provider_config.get('enabled', False),
            'region': provider_config.get('region')  # Cho Azure
        }
    
    def list_available_llm_providers(self) -> list:
        """Liệt kê tất cả LLM providers có sẵn"""
        return list(self.config['llm_providers'].keys())
    
    def list_available_tts_providers(self) -> list:
        """Liệt kê tất cả TTS providers có sẵn"""
        return list(self.config['tts_providers'].keys())
    
    def list_enabled_llm_providers(self) -> list:
        """Liệt kê LLM providers đã bật"""
        return [
            name for name, config in self.config['llm_providers'].items()
            if config.get('enabled', False)
        ]
    
    def list_enabled_tts_providers(self) -> list:
        """Liệt kê TTS providers đã bật"""
        return [
            name for name, config in self.config['tts_providers'].items()
            if config.get('enabled', False)
        ]
    
    def switch_llm_provider(self, provider_name: str):
        """
        Chuyển sang LLM provider khác (runtime)
        Lưu ý: Chỉ thay đổi trong memory, không ghi vào file
        """
        if provider_name not in self.config['llm_providers']:
            raise ValueError(f"LLM provider '{provider_name}' không tồn tại")
        
        self.active_llm = provider_name
        print(f"[ProviderManager] Đã chuyển sang LLM: {provider_name}")
    
    def switch_tts_provider(self, provider_name: str):
        """
        Chuyển sang TTS provider khác (runtime)
        Lưu ý: Chỉ thay đổi trong memory, không ghi vào file
        """
        if provider_name not in self.config['tts_providers']:
            raise ValueError(f"TTS provider '{provider_name}' không tồn tại")
        
        self.active_tts = provider_name
        print(f"[ProviderManager] Đã chuyển sang TTS: {provider_name}")
    
    def get_fallback_llm_config(self) -> Optional[Dict[str, Any]]:
        """Lấy config của fallback LLM provider"""
        if not self.fallback_enabled or not self.fallback_llm:
            return None
        
        try:
            return self.get_llm_config(self.fallback_llm)
        except Exception as e:
            print(f"[ERROR] Không thể load fallback LLM: {e}")
            return None
    
    def get_fallback_tts_config(self) -> Optional[Dict[str, Any]]:
        """Lấy config của fallback TTS provider"""
        if not self.fallback_enabled or not self.fallback_tts:
            return None
        
        try:
            return self.get_tts_config(self.fallback_tts)
        except Exception as e:
            print(f"[ERROR] Không thể load fallback TTS: {e}")
            return None
    
    def print_status(self):
        """In ra trạng thái hiện tại của các providers"""
        print("\n" + "="*60)
        print("🤖 AI PROVIDERS STATUS")
        print("="*60)
        
        print(f"\n📚 LLM (Não bộ):")
        print(f"  Active: {self.active_llm}")
        llm_config = self.get_llm_config()
        print(f"  Model: {llm_config['default_model']}")
        print(f"  Enabled: {llm_config['enabled']}")
        print(f"  API Key: {'✅ OK' if llm_config['api_key'] else '❌ Missing'}")
        
        print(f"\n🎙️ TTS (Giọng nói):")
        print(f"  Active: {self.active_tts}")
        tts_config = self.get_tts_config()
        print(f"  Voice: {tts_config['default_voice']}")
        print(f"  Enabled: {tts_config['enabled']}")
        print(f"  API Key: {'✅ OK' if tts_config['api_key'] else '❌ Missing' if tts_config.get('api_key') is not None else 'N/A (Local)'}")
        
        if self.fallback_enabled:
            print(f"\n🔄 Fallback:")
            print(f"  LLM: {self.fallback_llm}")
            print(f"  TTS: {self.fallback_tts}")
        
        print("\n" + "="*60 + "\n")

# Singleton instance
_provider_manager = None

def get_provider_manager() -> ProviderManager:
    """Lấy singleton instance của ProviderManager"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
