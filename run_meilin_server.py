#!/usr/bin/env python3
"""
MeiLin Full Control Server
Runs both Flask API server and WebSocket server for ESP32 devices

This server provides:
1. HTTP API at port 5000 (Flask) - for device registration, chat, TTS
2. WebSocket at port 8765 (MeiLin WebSocket) - for real-time audio streaming

Usage:
    python run_meilin_server.py
    
The server will:
1. Start Flask API server on http://0.0.0.0:5000
2. Start WebSocket server on ws://0.0.0.0:8765
"""

import os
import sys
import asyncio
import threading
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_flask_server():
    """Run Flask API server in a separate thread"""
    from meilin_api_server import app
    
    logger.info("Starting Flask API server on port 5000...")
    # Disable Flask's default logging to avoid duplicate logs
    import logging as flask_logging
    flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


def create_websocket_server():
    """Create and configure WebSocket server with all dependencies"""
    try:
        # Import all needed modules
        from modules.websocket_server import MeiLinWebSocketServer
        from modules.chat_processor import ChatProcessor
        from modules.rag_system import RAGSystem
        from modules.provider_manager import get_provider_manager
        from modules.providers.factory import ProviderFactory
        from modules.esp_device_manager import get_esp_device_manager
        from modules.multi_user.user_manager import get_user_manager
        from modules.multi_user.api_key_manager import get_api_key_manager
        
        # Initialize components
        logger.info("Initializing MeiLin components...")
        
        rag_system = RAGSystem()
        chat_processor = ChatProcessor(rag_system)
        provider_manager = get_provider_manager()
        
        # Get TTS config and engine
        tts_config = provider_manager.get_tts_config()
        tts_engine = ProviderFactory.create_tts_provider(tts_config['provider'], tts_config)
        
        esp_device_manager = get_esp_device_manager()
        user_manager = get_user_manager()
        api_key_manager = get_api_key_manager()
        
        # Create WebSocket server with all dependencies
        ws_server = MeiLinWebSocketServer(
            chat_processor=chat_processor,
            tts_engine=tts_engine,
            user_manager=user_manager,
            esp_device_manager=esp_device_manager,
            api_key_manager=api_key_manager
        )
        
        logger.info("✅ MeiLin WebSocket Server initialized")
        return ws_server
        
    except ImportError as e:
        logger.error(f"Failed to import module: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket server: {e}")
        raise


async def run_websocket_server():
    """Run WebSocket server for ESP32 audio streaming"""
    try:
        import websockets
        
        ws_server = create_websocket_server()
        
        host = '0.0.0.0'
        port = 8765
        
        logger.info(f"Starting WebSocket server on ws://{host}:{port}")
        
        async with websockets.serve(
            ws_server.handle_connection, 
            host, 
            port,
            # WebSocket configuration for audio streaming
            max_size=10 * 1024 * 1024,  # 10MB max message size
            ping_interval=30,
            ping_timeout=10,
        ):
            logger.info(f"✅ WebSocket server started on ws://{host}:{port}")
            await asyncio.Future()  # Run forever
        
    except ImportError as e:
        logger.error(f"websockets library not installed: {e}")
        logger.error("Install with: pip install websockets")
        raise
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        raise


def main():
    """Main entry point - run both servers"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MeiLin Full Control Server')
    parser.add_argument('--websocket-only', action='store_true', 
                        help='Run only WebSocket server (no Flask)')
    parser.add_argument('--flask-only', action='store_true',
                        help='Run only Flask API server (no WebSocket)')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 MeiLin Full Control Server")
    print("="*70)
    
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│  MeiLin Full Control Mode                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🌐 HTTP API Server (Flask):      http://0.0.0.0:5000              │
│  🔌 WebSocket Server (STT/LLM/TTS): ws://0.0.0.0:8765              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ESP32 Connection:                                                  │
│  1. Configure ESP32 to connect to ws://<your-ip>:8765              │
│  2. Audio will be processed: STT → LLM → TTS → Audio Stream        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  STT Providers (configured via Telegram bot):                       │
│  🆓 Vosk (Default) - Free, offline, no API key needed              │
│  ⚡ Groq Whisper   - Free API, fast, online                         │
│  🎤 OpenAI Whisper - Paid, high quality                            │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  HTTP Endpoints:                                                    │
│  GET  /health           - Check server status                       │
│  POST /chat             - Chat with MeiLin                          │
│  POST /esp/chat         - ESP32 chat endpoint                       │
│  POST /esp/validate     - Validate device                           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  WebSocket Protocol (XiaoZhi Compatible):                          │
│  {"type":"hello","version":3,"device_id":"..."}  → Connect         │
│  {"type":"listen","state":"start"}               → Start listening │
│  Binary data (Opus)                              → Audio frames     │
│  {"type":"listen","state":"stop"}                → Stop listening  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
""")
    
    print("Starting servers...")
    print("-" * 70)
    
    # Handle different modes
    if args.websocket_only:
        logger.info("Running WebSocket server only (port 8765)")
        try:
            asyncio.run(run_websocket_server())
        except KeyboardInterrupt:
            logger.info("Shutting down WebSocket server...")
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
            raise
    elif args.flask_only:
        logger.info("Running Flask API server only (port 5000)")
        run_flask_server()
    else:
        # Start Flask server in a separate thread
        flask_thread = threading.Thread(target=run_flask_server, daemon=True)
        flask_thread.start()
        logger.info("✅ Flask API server started on http://0.0.0.0:5000")
        
        # Run WebSocket server in main asyncio loop
        try:
            asyncio.run(run_websocket_server())
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


if __name__ == '__main__':
    main()
