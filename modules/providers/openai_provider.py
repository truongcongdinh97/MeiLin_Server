"""
OpenAI ChatGPT Provider
"""
import requests
from typing import Dict, Any
from .base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    """OpenAI ChatGPT Provider"""
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text từ prompt đơn giản"""
        messages = [
            {"role": "system", "content": "Bạn là MeiLin, một AI VTuber thân thiện."},
            {"role": "user", "content": prompt}
        ]
        return self.chat(messages, **kwargs)
    
    def chat(self, messages: list, **kwargs) -> str:
        """Chat với conversation history"""
        try:
            # Merge default params với kwargs
            params = {**self.default_params, **kwargs}
            
            # Tạo payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": params.get('temperature', 0.7),
                "max_tokens": params.get('max_tokens', 150),
                "top_p": params.get('top_p', 1.0),
                "frequency_penalty": params.get('frequency_penalty', 0.0),
                "presence_penalty": params.get('presence_penalty', 0.0)
            }
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Gọi API
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"[OpenAI] Lỗi API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"[OpenAI] Lỗi: {e}")
            return None
