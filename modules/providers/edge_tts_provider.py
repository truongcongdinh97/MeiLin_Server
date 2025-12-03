"""
Edge TTS Provider (Free, không cần API key)
Tối ưu: Stream trực tiếp vào memory thay vì qua file
"""
import asyncio
import edge_tts
import pygame
import io
from typing import Dict, Any
from .base import BaseTTSProvider

class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS Provider (Free)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Khởi tạo pygame mixer 1 lần duy nhất với buffer nhỏ để giảm latency
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=256)
                print("[EdgeTTS] Đã khởi tạo pygame mixer")
        except Exception as e:
            print(f"[EdgeTTS] Không thể khởi tạo pygame mixer: {e}")
    
    def speak(self, text: str, **kwargs) -> bool:
        """Chuyển text thành speech và phát ra loa (stream trực tiếp vào memory)"""
        try:
            # Merge default params với kwargs
            params = {**self.default_params, **kwargs}
            
            # Voice settings
            voice = kwargs.get('voice', self.voice)
            rate = params.get('rate', '+0%')
            volume = params.get('volume', '+0%')
            pitch = params.get('pitch', '+0Hz')
            
            # Generate audio bytes - xử lý event loop đúng cách
            try:
                loop = asyncio.get_running_loop()
                # Nếu có loop đang chạy, dùng nest_asyncio hoặc threading
                import concurrent.futures
                import threading
                
                result = [None]
                exception = [None]
                
                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result[0] = new_loop.run_until_complete(
                            self._async_generate_audio_bytes(text, voice, rate, volume, pitch)
                        )
                        new_loop.close()
                    except Exception as e:
                        exception[0] = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=30)
                
                if exception[0]:
                    raise exception[0]
                
                audio_bytes = result[0]
            except RuntimeError:
                # Nếu không có loop, dùng asyncio.run()
                audio_bytes = asyncio.run(self._async_generate_audio_bytes(
                    text, voice, rate, volume, pitch
                ))
            
            if not audio_bytes:
                return False
            
            # Phát audio từ memory (không qua file)
            audio_stream = io.BytesIO(audio_bytes)
            pygame.mixer.music.load(audio_stream)
            pygame.mixer.music.play()
            
            # Chờ phát xong với timeout (tránh treo vô hạn)
            import time
            timeout = 30  # 30 giây timeout
            start_time = time.time()
            
            while pygame.mixer.music.get_busy():
                if time.time() - start_time > timeout:
                    print(f"[EdgeTTS] Timeout sau {timeout}s, dừng phát")
                    pygame.mixer.music.stop()
                    return False
                pygame.time.Clock().tick(10)
            
            return True
            
        except Exception as e:
            print(f"[EdgeTTS] Lỗi speak: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_audio(self, text: str, output_path: str, **kwargs) -> bool:
        """Tạo file audio từ text"""
        try:
            # Merge default params với kwargs
            params = {**self.default_params, **kwargs}
            
            # Voice
            voice = kwargs.get('voice', self.voice)
            
            # Rate, volume, pitch
            rate = params.get('rate', '+0%')
            volume = params.get('volume', '+0%')
            pitch = params.get('pitch', '+0Hz')
            
            # Generate audio - xử lý event loop đúng cách
            try:
                loop = asyncio.get_running_loop()
                # Dùng thread mới với event loop riêng
                import threading
                
                exception = [None]
                
                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(
                            self._async_generate_audio(text, output_path, voice, rate, volume, pitch)
                        )
                        new_loop.close()
                    except Exception as e:
                        exception[0] = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=30)
                
                if exception[0]:
                    raise exception[0]
            except RuntimeError:
                asyncio.run(self._async_generate_audio(
                    text, output_path, voice, rate, volume, pitch
                ))
            
            return True
            
        except Exception as e:
            print(f"[EdgeTTS] Lỗi generate_audio: {e}")
            return False
    
    async def _async_generate_audio_bytes(self, text: str, voice: str, 
                                          rate: str, volume: str, pitch: str) -> bytes:
        """Async method để generate audio trực tiếp vào memory (tối ưu)"""
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch
            )
            
            # Tối ưu: Dùng list comprehension + join (nhanh hơn concatenation)
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            return b''.join(audio_chunks)
            
        except Exception as e:
            print(f"[EdgeTTS] Lỗi _async_generate_audio_bytes: {e}")
            return None
    
    async def _async_generate_audio(self, text: str, output_path: str, 
                                     voice: str, rate: str, volume: str, pitch: str):
        """Async method để generate audio file (cho generate_audio method)"""
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch
        )
        await communicate.save(output_path)
