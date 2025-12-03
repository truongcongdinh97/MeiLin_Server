"""
Base classes cho LLM và TTS providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMProvider(ABC):
    """Base class cho tất cả LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_url = config['api_url']
        self.api_key = config['api_key']
        self.model = config['default_model']
        self.default_params = config['default_params']
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text từ prompt
        Args:
            prompt: Input text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def chat(self, messages: list, **kwargs) -> str:
        """
        Chat với nhiều messages (conversation history)
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            **kwargs: Additional parameters
        Returns:
            Response text
        """
        pass

class BaseTTSProvider(ABC):
    """Base class cho tất cả TTS providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.voice = config['default_voice']
        self.default_params = config['default_params']
    
    @abstractmethod
    def speak(self, text: str, **kwargs) -> bool:
        """
        Chuyển text thành speech và phát ra loa
        Args:
            text: Text cần đọc
            **kwargs: Additional parameters (voice_id, speed, etc.)
        Returns:
            True nếu thành công, False nếu lỗi
        """
        pass
    
    @abstractmethod
    def generate_audio(self, text: str, output_path: str, **kwargs) -> bool:
        """
        Tạo file audio từ text
        Args:
            text: Text cần đọc
            output_path: Đường dẫn file output
            **kwargs: Additional parameters
        Returns:
            True nếu thành công, False nếu lỗi
        """
        pass
