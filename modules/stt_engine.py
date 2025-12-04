"""
MeiLin STT (Speech-to-Text) Engine
Hỗ trợ nhiều providers với default là Vosk (miễn phí, offline)

Providers:
- vosk: Miễn phí, chạy local, không cần API key (DEFAULT)
- groq: Miễn phí, cần API key, nhanh và chính xác
- openai: Trả phí, cần API key, chính xác nhất
- google: Trả phí, cần API key
"""

import os
import io
import json
import wave
import tempfile
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# Base STT Provider
# ============================================================================

class BaseSTTProvider(ABC):
    """Base class for STT providers"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Raw PCM audio data (16-bit, mono)
            sample_rate: Sample rate of audio (default 16000)
            
        Returns:
            Transcribed text
        """
        pass
    
    @abstractmethod
    def transcribe_file(self, file_path: str) -> str:
        """Transcribe audio file to text"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    def requires_api_key(self) -> bool:
        """Whether this provider requires API key"""
        return True


# ============================================================================
# Vosk Provider (Free, Offline)
# ============================================================================

class VoskSTTProvider(BaseSTTProvider):
    """
    Vosk STT - Miễn phí, chạy offline
    Download model từ: https://alphacephei.com/vosk/models
    Model tiếng Việt: vosk-model-small-vn-0.4 (~40MB)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._model = None
        self._recognizer = None
        
        # Model path - có thể config hoặc dùng default
        self.model_path = config.get('model_path') if config else None
        if not self.model_path:
            self.model_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 'models', 'vosk-model-small-vn-0.4'
            )
    
    def _init_model(self):
        """Lazy load model"""
        if self._model is None:
            try:
                from vosk import Model, KaldiRecognizer
                
                if not os.path.exists(self.model_path):
                    logger.warning(f"Vosk model not found at {self.model_path}")
                    logger.info("Downloading Vosk Vietnamese model...")
                    self._download_model()
                
                logger.info(f"Loading Vosk model from {self.model_path}")
                self._model = Model(self.model_path)
                logger.info("Vosk model loaded successfully")
                
            except ImportError:
                raise RuntimeError("Vosk not installed. Run: pip install vosk")
            except Exception as e:
                raise RuntimeError(f"Failed to load Vosk model: {e}")
    
    def _download_model(self):
        """Download Vosk Vietnamese model"""
        import urllib.request
        import zipfile
        
        model_url = "https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip"
        model_dir = os.path.dirname(self.model_path)
        os.makedirs(model_dir, exist_ok=True)
        
        # Check if model already exists
        if os.path.exists(self.model_path):
            logger.info(f"Vosk model already exists at {self.model_path}")
            return
        
        zip_path = os.path.join(model_dir, "vosk-model.zip")
        
        logger.info(f"Downloading Vosk model from {model_url}")
        urllib.request.urlretrieve(model_url, zip_path)
        
        logger.info("Extracting model...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        
        os.remove(zip_path)
        logger.info("Vosk model downloaded successfully")
    
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio data"""
        self._init_model()
        
        from vosk import KaldiRecognizer
        
        rec = KaldiRecognizer(self._model, sample_rate)
        rec.SetWords(True)
        
        # Process audio in chunks
        chunk_size = 4000
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            rec.AcceptWaveform(chunk)
        
        # Get final result
        result = json.loads(rec.FinalResult())
        return result.get('text', '')
    
    def transcribe_file(self, file_path: str) -> str:
        """Transcribe audio file"""
        self._init_model()
        
        from vosk import KaldiRecognizer
        
        with wave.open(file_path, 'rb') as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise ValueError("Audio must be mono 16-bit WAV")
            
            sample_rate = wf.getframerate()
            rec = KaldiRecognizer(self._model, sample_rate)
            rec.SetWords(True)
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)
            
            result = json.loads(rec.FinalResult())
            return result.get('text', '')
    
    @property
    def name(self) -> str:
        return "Vosk (Offline)"
    
    @property
    def requires_api_key(self) -> bool:
        return False


# ============================================================================
# Groq Whisper Provider (Free with API key)
# ============================================================================

class GroqSTTProvider(BaseSTTProvider):
    """
    Groq Whisper - Miễn phí với API key
    Rất nhanh, chính xác cao
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = config.get('api_key') if config else None
        self.model = config.get('model', 'whisper-large-v3-turbo') if config else 'whisper-large-v3-turbo'
        self._client = None
    
    def _init_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("Groq API key required")
            
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("Groq not installed. Run: pip install groq")
    
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio data"""
        # Convert to WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return self._transcribe_buffer(wav_buffer)
    
    def _transcribe_buffer(self, audio_buffer: io.BytesIO) -> str:
        self._init_client()
        
        # Create a file-like object with name attribute for Groq API
        class NamedBytesIO(io.BytesIO):
            name = "audio.wav"
        
        named_buffer = NamedBytesIO(audio_buffer.getvalue())
        
        transcription = self._client.audio.transcriptions.create(
            file=named_buffer,
            model=self.model,
            language="vi",
            response_format="text"
        )
        
        return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
    
    def transcribe_file(self, file_path: str) -> str:
        """Transcribe audio file"""
        self._init_client()
        
        with open(file_path, 'rb') as audio_file:
            transcription = self._client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language="vi",
                response_format="text"
            )
        
        return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
    
    @property
    def name(self) -> str:
        return "Groq Whisper"


# ============================================================================
# OpenAI Whisper Provider
# ============================================================================

class OpenAISTTProvider(BaseSTTProvider):
    """OpenAI Whisper - Trả phí, chính xác nhất"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = config.get('api_key') if config else None
        self.model = config.get('model', 'whisper-1') if config else 'whisper-1'
        self._client = None
    
    def _init_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("OpenAI API key required")
            
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("OpenAI not installed. Run: pip install openai")
    
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio data"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        
        # Create a file-like object with name attribute for OpenAI API
        class NamedBytesIO(io.BytesIO):
            name = "audio.wav"
        
        named_buffer = NamedBytesIO(wav_buffer.getvalue())
        
        self._init_client()
        
        transcription = self._client.audio.transcriptions.create(
            file=named_buffer,
            model=self.model,
            language="vi"
        )
        
        return transcription.text.strip()
    
    def transcribe_file(self, file_path: str) -> str:
        self._init_client()
        
        with open(file_path, 'rb') as audio_file:
            transcription = self._client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language="vi"
            )
        
        return transcription.text.strip()
    
    @property
    def name(self) -> str:
        return "OpenAI Whisper"


# ============================================================================
# Google Speech-to-Text Provider
# ============================================================================

class GoogleSTTProvider(BaseSTTProvider):
    """
    Google Speech-to-Text - Trả phí
    
    Yêu cầu:
    - Google Cloud credentials JSON file
    - Set GOOGLE_APPLICATION_CREDENTIALS environment variable
    
    Hoặc truyền credentials_path trong config
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # Google Cloud uses credentials file, not simple API key
        self.credentials_path = config.get('credentials_path') if config else None
        self._client = None
    
    def _init_client(self):
        if self._client is None:
            try:
                from google.cloud import speech
                
                # If credentials_path is provided, set environment variable
                if self.credentials_path:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
                
                # Check if credentials are available
                if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                    raise RuntimeError(
                        "Google Cloud credentials required. "
                        "Set GOOGLE_APPLICATION_CREDENTIALS environment variable "
                        "or provide credentials_path in config"
                    )
                
                self._client = speech.SpeechClient()
            except ImportError:
                raise RuntimeError("Google Cloud Speech not installed. Run: pip install google-cloud-speech")
    
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        self._init_client()
        from google.cloud import speech
        
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code="vi-VN"
        )
        
        response = self._client.recognize(config=config, audio=audio)
        
        if response.results:
            return response.results[0].alternatives[0].transcript
        return ""
    
    def transcribe_file(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        return self.transcribe(audio_data)
    
    @property
    def name(self) -> str:
        return "Google Speech-to-Text"


# ============================================================================
# STT Provider Registry
# ============================================================================

STT_PROVIDERS = {
    'vosk': {
        'name': 'Vosk (Miễn phí, Offline)',
        'class': VoskSTTProvider,
        'requires_api_key': False,
        'description': 'Chạy offline, không cần internet. Độ chính xác tốt.'
    },
    'groq': {
        'name': 'Groq Whisper (Miễn phí)',
        'class': GroqSTTProvider,
        'requires_api_key': True,
        'description': 'Miễn phí với API key. Rất nhanh và chính xác.'
    },
    'openai': {
        'name': 'OpenAI Whisper (Trả phí)',
        'class': OpenAISTTProvider,
        'requires_api_key': True,
        'description': 'Chính xác nhất. $0.006/phút.'
    },
    'google': {
        'name': 'Google Speech (Trả phí)',
        'class': GoogleSTTProvider,
        'requires_api_key': False,  # Uses credentials file, not API key
        'requires_credentials': True,  # Requires GOOGLE_APPLICATION_CREDENTIALS
        'description': 'Độ chính xác cao. Cần Google Cloud credentials file.'
    }
}


# ============================================================================
# STT Engine Factory
# ============================================================================

class STTEngine:
    """
    STT Engine - Factory for creating STT providers
    Default provider is Vosk (free, offline)
    """
    
    _default_provider: BaseSTTProvider = None
    
    @classmethod
    def create_provider(cls, provider_name: str = 'vosk', config: Dict[str, Any] = None) -> BaseSTTProvider:
        """
        Create STT provider instance
        
        Args:
            provider_name: Provider name (vosk, groq, openai, google)
            config: Provider configuration
            
        Returns:
            STT provider instance
        """
        if provider_name not in STT_PROVIDERS:
            raise ValueError(f"Unknown STT provider: {provider_name}")
        
        provider_info = STT_PROVIDERS[provider_name]
        provider_class = provider_info['class']
        
        return provider_class(config)
    
    @classmethod
    def get_default_provider(cls) -> BaseSTTProvider:
        """Get or create default STT provider (Vosk)"""
        if cls._default_provider is None:
            cls._default_provider = cls.create_provider('vosk')
        return cls._default_provider
    
    @classmethod
    def transcribe(cls, audio_data: bytes, provider: BaseSTTProvider = None, sample_rate: int = 16000) -> str:
        """
        Transcribe audio using specified or default provider
        
        Args:
            audio_data: Raw PCM audio data
            provider: STT provider (optional, uses default if not specified)
            sample_rate: Audio sample rate
            
        Returns:
            Transcribed text
        """
        if provider is None:
            provider = cls.get_default_provider()
        
        return provider.transcribe(audio_data, sample_rate)


# ============================================================================
# Singleton
# ============================================================================

_stt_engine_instance: Optional[STTEngine] = None

def get_stt_engine() -> STTEngine:
    """Get STT Engine singleton"""
    global _stt_engine_instance
    if _stt_engine_instance is None:
        _stt_engine_instance = STTEngine()
    return _stt_engine_instance
