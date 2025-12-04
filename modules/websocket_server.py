"""
MeiLin WebSocket Server
Tương thích với XiaoZhi ESP32 protocol
Xử lý: Audio Stream → STT → LLM → TTS → Audio Stream

Protocol:
- Client gửi "hello" message với audio_params
- Server trả về "hello" với session_id
- Client gửi binary audio (Opus encoded)
- Server trả về:
  - {"type": "stt", "text": "..."} khi nhận diện xong
  - {"type": "tts", "state": "start"} khi bắt đầu TTS
  - Binary audio (Opus encoded) cho TTS
  - {"type": "tts", "state": "stop"} khi kết thúc TTS
"""

import os
import io
import json
import uuid
import struct
import asyncio
import logging
import tempfile
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Opus decoder/encoder
try:
    import opuslib
    OPUS_AVAILABLE = True
except ImportError:
    OPUS_AVAILABLE = False
    logger.warning("opuslib not available, will use raw audio")


@dataclass
class ClientSession:
    """Represents a connected client session"""
    session_id: str
    device_id: str
    client_id: str
    protocol_version: int
    audio_format: str
    sample_rate: int
    channels: int
    frame_duration: int
    websocket: Any
    user_id: Optional[str] = None
    db_user_id: Optional[int] = None
    audio_buffer: bytes = b""
    is_listening: bool = False
    opus_decoder: Any = None
    opus_encoder: Any = None


class MeiLinWebSocketServer:
    """
    WebSocket Server for MeiLin ESP32 communication
    Compatible with XiaoZhi protocol
    """
    
    def __init__(self, 
                 stt_engine=None,
                 chat_processor=None,
                 tts_engine=None,
                 user_manager=None,
                 esp_device_manager=None,
                 api_key_manager=None):
        """
        Initialize WebSocket server
        
        Args:
            stt_engine: STT engine for speech recognition
            chat_processor: Chat processor for LLM
            tts_engine: TTS engine for speech synthesis
            user_manager: User manager for database
            esp_device_manager: ESP device manager
            api_key_manager: API key manager
        """
        self.stt_engine = stt_engine
        self.chat_processor = chat_processor
        self.tts_engine = tts_engine
        self.user_manager = user_manager
        self.esp_device_manager = esp_device_manager
        self.api_key_manager = api_key_manager
        
        # Active sessions
        self.sessions: Dict[str, ClientSession] = {}
        
        # Server config
        self.output_sample_rate = 16000
        self.output_frame_duration = 60  # ms
        
    async def handle_connection(self, websocket, path=None):
        """Handle new WebSocket connection"""
        session_id = str(uuid.uuid4())
        session = None
        
        try:
            # Get headers for device info
            headers = dict(websocket.request_headers) if hasattr(websocket, 'request_headers') else {}
            device_id = headers.get('Device-Id', 'unknown')
            client_id = headers.get('Client-Id', 'unknown')
            protocol_version = int(headers.get('Protocol-Version', '1'))
            auth_token = headers.get('Authorization', '')
            
            logger.info(f"New connection: device={device_id}, version={protocol_version}")
            
            # Create session
            session = ClientSession(
                session_id=session_id,
                device_id=device_id,
                client_id=client_id,
                protocol_version=protocol_version,
                audio_format='opus',
                sample_rate=16000,
                channels=1,
                frame_duration=60,
                websocket=websocket
            )
            
            # Validate device and get user info
            if self.esp_device_manager and auth_token:
                # Extract token from "Bearer xxx" format
                token = auth_token.replace('Bearer ', '').strip()
                device_info = self.esp_device_manager.validate_device_key(token)
                if device_info and device_info.get('valid'):
                    session.user_id = str(device_info.get('telegram_user_id'))
                    session.db_user_id = device_info.get('user_id')
                    logger.info(f"Authenticated user: {session.user_id}")
            
            self.sessions[session_id] = session
            
            # Initialize Opus codec
            if OPUS_AVAILABLE:
                session.opus_decoder = opuslib.Decoder(16000, 1)
                session.opus_encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_VOIP)
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(session, message)
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if session_id in self.sessions:
                del self.sessions[session_id]
            logger.info(f"Connection closed: {session_id}")
    
    async def _handle_message(self, session: ClientSession, message):
        """Handle incoming message"""
        if isinstance(message, bytes):
            # Binary message - audio data
            await self._handle_audio(session, message)
        else:
            # Text message - JSON command
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'hello':
                    await self._handle_hello(session, data)
                elif msg_type == 'listen':
                    await self._handle_listen(session, data)
                elif msg_type == 'abort':
                    await self._handle_abort(session, data)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
    
    async def _handle_hello(self, session: ClientSession, data: dict):
        """Handle hello message from client"""
        # Parse audio params
        audio_params = data.get('audio_params', {})
        session.audio_format = audio_params.get('format', 'opus')
        session.sample_rate = audio_params.get('sample_rate', 16000)
        session.channels = audio_params.get('channels', 1)
        session.frame_duration = audio_params.get('frame_duration', 60)
        
        features = data.get('features', {})
        logger.info(f"Client hello: format={session.audio_format}, rate={session.sample_rate}, features={features}")
        
        # Send server hello
        response = {
            "type": "hello",
            "session_id": session.session_id,
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": self.output_sample_rate,
                "channels": 1,
                "frame_duration": self.output_frame_duration
            }
        }
        
        await session.websocket.send(json.dumps(response))
        logger.info(f"Sent server hello: session={session.session_id}")
    
    async def _handle_listen(self, session: ClientSession, data: dict):
        """Handle listen state change"""
        state = data.get('state', '')
        mode = data.get('mode', 'manual')
        
        if state == 'start':
            session.is_listening = True
            session.audio_buffer = b""
            logger.info(f"Start listening: mode={mode}")
            
        elif state == 'stop':
            session.is_listening = False
            logger.info("Stop listening, processing audio...")
            
            # Process accumulated audio
            if session.audio_buffer:
                await self._process_audio(session)
            
        elif state == 'detect':
            # Wake word detected
            wake_word = data.get('text', '')
            logger.info(f"Wake word detected: {wake_word}")
    
    async def _handle_audio(self, session: ClientSession, data: bytes):
        """Handle incoming audio data"""
        if not session.is_listening:
            return
        
        # Decode based on protocol version
        if session.protocol_version == 2:
            # BinaryProtocol2: version(2) + type(2) + reserved(4) + timestamp(4) + payload_size(4) + payload
            if len(data) < 16:
                return
            version, msg_type, _, timestamp, payload_size = struct.unpack('>HHIII', data[:16])
            audio_data = data[16:16 + payload_size]
        elif session.protocol_version == 3:
            # BinaryProtocol3: type(1) + reserved(1) + payload_size(2) + payload
            if len(data) < 4:
                return
            msg_type, _, payload_size = struct.unpack('>BBH', data[:4])
            audio_data = data[4:4 + payload_size]
        else:
            # Raw audio
            audio_data = data
        
        # Decode Opus to PCM
        if session.opus_decoder and session.audio_format == 'opus':
            try:
                pcm_data = session.opus_decoder.decode(audio_data, session.frame_duration * session.sample_rate // 1000)
                session.audio_buffer += pcm_data
            except Exception as e:
                logger.error(f"Opus decode error: {e}")
        else:
            session.audio_buffer += audio_data
    
    async def _handle_abort(self, session: ClientSession, data: dict):
        """Handle abort request"""
        reason = data.get('reason', '')
        logger.info(f"Abort requested: reason={reason}")
        session.is_listening = False
        session.audio_buffer = b""
    
    async def _process_audio(self, session: ClientSession):
        """Process audio buffer: STT → LLM → TTS"""
        try:
            audio_data = session.audio_buffer
            session.audio_buffer = b""
            
            if len(audio_data) < 1600:  # Less than 100ms of audio
                logger.warning("Audio too short, ignoring")
                return
            
            # Step 1: STT
            logger.info(f"Processing {len(audio_data)} bytes of audio")
            
            try:
                stt_provider = self._get_stt_provider(session)
                text = stt_provider.transcribe(audio_data, session.sample_rate)
            except Exception as stt_error:
                logger.error(f"STT error: {stt_error}")
                # Send error notification to client
                await session.websocket.send(json.dumps({
                    "type": "error",
                    "error": "stt_failed",
                    "message": "Không thể nhận diện giọng nói"
                }))
                return
            
            if not text or not text.strip():
                logger.warning("No speech detected")
                return
            
            logger.info(f"STT result: {text}")
            
            # Send STT result to client
            await session.websocket.send(json.dumps({
                "type": "stt",
                "text": text
            }))
            
            # Step 2: LLM
            response_text = await self._process_llm(session, text)
            
            if not response_text:
                return
            
            logger.info(f"LLM response: {response_text[:100]}...")
            
            # Send LLM emotion (optional)
            await session.websocket.send(json.dumps({
                "type": "llm",
                "emotion": "happy"
            }))
            
            # Step 3: TTS
            await self._send_tts(session, response_text)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_stt_provider(self, session: ClientSession):
        """Get STT provider for user"""
        from modules.stt_engine import STTEngine
        
        # Check if user has custom STT config
        if session.db_user_id and self.user_manager:
            stt_config = self.user_manager.get_stt_config(session.db_user_id)
            if stt_config:
                provider_name = stt_config.get('provider_name', 'vosk')
                
                # Get API key if needed (encrypted)
                api_key = stt_config.get('api_key')
                if api_key and self.api_key_manager:
                    try:
                        api_key = self.api_key_manager.decrypt_api_key(api_key)
                    except:
                        api_key = None
                
                config = {}
                if api_key is not None:
                    config['api_key'] = api_key
                model = stt_config.get('model')
                if model:
                    config['model'] = model
                
                try:
                    return STTEngine.create_provider(provider_name, config)
                except Exception as e:
                    logger.error(f"Failed to create STT provider {provider_name}: {e}")
                    # Fall back to default
        
        # Use default (Vosk - free offline)
        return STTEngine.get_default_provider()
    
    async def _process_llm(self, session: ClientSession, text: str) -> str:
        """Process text through LLM"""
        if not self.chat_processor:
            return "Xin lỗi, hệ thống chat chưa được cấu hình."
        
        try:
            # Get user's device name for context
            device_name = "User"
            if session.db_user_id and self.esp_device_manager:
                # Get device info
                device_name = session.device_id
            
            response = self.chat_processor.process_message(
                user_message=text,
                username=device_name,
                user_id=session.user_id or session.device_id
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."
    
    async def _send_tts(self, session: ClientSession, text: str):
        """Generate and send TTS audio"""
        try:
            # Send TTS start
            await session.websocket.send(json.dumps({
                "type": "tts",
                "state": "start"
            }))
            
            # Send text being spoken (for display)
            await session.websocket.send(json.dumps({
                "type": "tts",
                "state": "sentence_start",
                "text": text
            }))
            
            # Generate TTS audio
            if self.tts_engine:
                # Get TTS provider for user
                tts_provider = self._get_tts_provider(session)
                audio_path = tts_provider.generate_audio_file(text)
                
                if audio_path and os.path.exists(audio_path):
                    await self._stream_audio_file(session, audio_path)
            
            # Send TTS stop
            await session.websocket.send(json.dumps({
                "type": "tts",
                "state": "stop"
            }))
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    def _get_tts_provider(self, session: ClientSession):
        """Get TTS provider for user"""
        # Use default TTS for now
        # TODO: Get user's TTS config
        return self.tts_engine
    
    async def _stream_audio_file(self, session: ClientSession, audio_path: str):
        """Stream audio file to client"""
        import wave
        
        temp_wav_path = None
        
        try:
            # Convert to WAV if needed
            if not audio_path.endswith('.wav'):
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(audio_path)
                    temp_wav_path = audio_path.rsplit('.', 1)[0] + '_temp.wav'
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    audio.export(temp_wav_path, format='wav')
                    audio_path = temp_wav_path
                except ImportError:
                    logger.error("pydub not installed, cannot convert audio format")
                    return
                except Exception as e:
                    logger.error(f"Audio conversion error: {e}")
                    return
            
            # Read and stream audio
            with wave.open(audio_path, 'rb') as wf:
                frame_size = self.output_frame_duration * self.output_sample_rate // 1000
                
                while True:
                    pcm_data = wf.readframes(frame_size)
                    if not pcm_data:
                        break
                    
                    # Encode to Opus
                    if session.opus_encoder:
                        opus_data = session.opus_encoder.encode(pcm_data, frame_size)
                        
                        # Pack with protocol header
                        if session.protocol_version == 3:
                            header = struct.pack('>BBH', 0, 0, len(opus_data))
                            await session.websocket.send(header + opus_data)
                        else:
                            await session.websocket.send(opus_data)
                    else:
                        await session.websocket.send(pcm_data)
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Audio streaming error: {e}")
        finally:
            # Cleanup temp WAV file if created
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except Exception:
                    pass


# ============================================================================
# WebSocket Server Runner
# ============================================================================

async def run_websocket_server(host: str = "0.0.0.0", port: int = 8765, **kwargs):
    """Run WebSocket server"""
    import websockets
    
    server = MeiLinWebSocketServer(**kwargs)
    
    logger.info(f"Starting MeiLin WebSocket Server on ws://{host}:{port}")
    
    async with websockets.serve(server.handle_connection, host, port):
        await asyncio.Future()  # Run forever


def start_websocket_server(host: str = "0.0.0.0", port: int = 8765, **kwargs):
    """Start WebSocket server in background thread"""
    import threading
    
    def run():
        asyncio.run(run_websocket_server(host, port, **kwargs))
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logger.info(f"WebSocket server started on ws://{host}:{port}")
    return thread
