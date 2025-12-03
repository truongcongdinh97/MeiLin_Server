"""
ElevenLabs TTS Provider
"""
import requests
import pygame
import io
from typing import Dict, Any
from .base import BaseTTSProvider

class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs TTS Provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Khởi tạo pygame mixer
        try:
            pygame.mixer.init()
        except:
            print("[ElevenLabs] Không thể khởi tạo pygame mixer")
    
    def speak(self, text: str, **kwargs) -> bool:
        """Chuyển text thành speech và phát ra loa"""
        try:
            # Generate audio bytes
            audio_bytes = self._generate_audio_bytes(text, **kwargs)
            
            if not audio_bytes:
                return False
            
            # Phát audio bằng pygame
            sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
            sound.play()
            
            # Chờ phát xong
            while pygame.mixer.get_busy():
                pygame.time.Clock().tick(10)
            
            return True
            
        except Exception as e:
            print(f"[ElevenLabs] Lỗi speak: {e}")
            return False
    
    def generate_audio(self, text: str, output_path: str, **kwargs) -> bool:
        """Tạo file audio từ text"""
        try:
            audio_bytes = self._generate_audio_bytes(text, **kwargs)
            
            if not audio_bytes:
                return False
            
            # Lưu file
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"[ElevenLabs] Đã lưu audio: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ElevenLabs] Lỗi generate_audio: {e}")
            return False
    
    def _generate_audio_bytes(self, text: str, **kwargs) -> bytes:
        """Generate audio bytes từ text (internal method)"""
        try:
            # Merge default params với kwargs
            params = {**self.default_params, **kwargs}
            
            # Voice ID - ưu tiên từ config default_voice, fallback sang d5HVupAWCwe4e6GvMCAL
            voice_id = kwargs.get('voice_id') or self.config.get('default_voice') or 'd5HVupAWCwe4e6GvMCAL'
            model = kwargs.get('model', self.config.get('default_model', 'eleven_v3'))
            
            # API URL - đảm bảo không None
            base_url = self.config.get('api_url') or 'https://api.elevenlabs.io/v1/text-to-speech'
            url = f"{base_url}/{voice_id}"
            
            # Headers
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Payload
            payload = {
                "text": text,
                "model_id": model,
                "voice_settings": {
                    "stability": params.get('stability', 0.5),
                    "similarity_boost": params.get('similarity_boost', 0.7),
                    "style": params.get('style', 0.5),
                    "use_speaker_boost": params.get('use_speaker_boost', True)
                }
            }
            
            # Gọi API
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"[ElevenLabs] Lỗi API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"[ElevenLabs] Lỗi _generate_audio_bytes: {e}")
            return None
