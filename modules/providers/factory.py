"""
Provider Factory - Tạo instance của LLM/TTS providers
"""
from typing import Dict, Any, Optional
from .base import BaseLLMProvider, BaseTTSProvider
from .deepseek_provider import DeepseekProvider
from .openai_provider import OpenAIProvider
from .elevenlabs_provider import ElevenLabsProvider
from .edge_tts_provider import EdgeTTSProvider

class ProviderFactory:
    """Factory để tạo provider instances"""
    
    # Mapping provider name → class
    LLM_PROVIDERS = {
        'deepseek': DeepseekProvider,
        'openai': OpenAIProvider,
        # Thêm các provider khác ở đây
    }
    
    TTS_PROVIDERS = {
        'elevenlabs': ElevenLabsProvider,
        'edge_tts': EdgeTTSProvider,
        # Thêm các provider khác ở đây
    }
    
    @classmethod
    def create_llm_provider(cls, provider_name: str, config: Dict[str, Any]) -> BaseLLMProvider:
        """
        Tạo LLM provider instance
        Args:
            provider_name: Tên provider (deepseek, openai, etc.)
            config: Config dict từ ProviderManager
        Returns:
            Instance của provider
        """
        provider_class = cls.LLM_PROVIDERS.get(provider_name)
        
        if not provider_class:
            raise ValueError(f"LLM provider '{provider_name}' chưa được implement")
        
        return provider_class(config)
    
    @classmethod
    def create_tts_provider(cls, provider_name: str, config: Dict[str, Any]) -> BaseTTSProvider:
        """
        Tạo TTS provider instance
        Args:
            provider_name: Tên provider (elevenlabs, edge_tts, etc.)
            config: Config dict từ ProviderManager
        Returns:
            Instance của provider
        """
        provider_class = cls.TTS_PROVIDERS.get(provider_name)
        
        if not provider_class:
            raise ValueError(f"TTS provider '{provider_name}' chưa được implement")
        
        return provider_class(config)
