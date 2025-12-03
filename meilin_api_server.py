"""
MeiLin API Server - Dành cho ESP32/IoT Devices
Chạy Flask server để nhận request từ ESP32 và trả response từ MeiLin
"""
from flask import Flask, request, jsonify, send_file
from modules.chat_processor import ChatProcessor
from modules.rag_system import RAGSystem
from modules.provider_manager import get_provider_manager
from modules.providers.factory import ProviderFactory
from modules.ota_manager import get_ota_manager
from modules.esp_device_manager import get_esp_device_manager
from modules.user_manager import get_user_manager
from modules.api_key_manager import get_api_key_manager
import logging

app = Flask(__name__)

# Khởi tạo MeiLin modules
print("Đang khởi tạo MeiLin API Server...")
rag_system = RAGSystem()
chat_processor = ChatProcessor(rag_system)
provider_manager = get_provider_manager()
tts_config = provider_manager.get_tts_config()
tts_engine = ProviderFactory.create_tts_provider(tts_config['provider'], tts_config)
ota_manager = get_ota_manager()
esp_device_manager = get_esp_device_manager()
user_manager = get_user_manager()
api_key_manager = get_api_key_manager()
print(f"✅ MeiLin API Server đã sẵn sàng! (TTS: {tts_config['provider']})")

# Tắt log Flask mặc định (chỉ hiển thị error)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/health', methods=['GET'])
def health_check():
    """Kiểm tra server có hoạt động không"""
    return jsonify({
        "status": "online",
        "message": "MeiLin API Server đang hoạt động"
    }), 200

@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint chính để chat với MeiLin
    Request JSON:
    {
        "message": "Xin chào MeiLin",
        "username": "ESP32_User",
        "user_id": "esp32_001" (optional)
    }
    Response JSON:
    {
        "response": "Câu trả lời từ MeiLin",
        "status": "success"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "error": "Thiếu trường 'message' trong request",
                "status": "error"
            }), 400
        
        user_message = data.get('message', '').strip()
        username = data.get('username', 'ESP32_User')
        user_id = data.get('user_id', username)
        
        if not user_message:
            return jsonify({
                "error": "Tin nhắn không được để trống",
                "status": "error"
            }), 400
        
        print(f"\n[ESP32] {username}: {user_message}")
        
        # Xử lý tin nhắn qua ChatProcessor
        response_text = chat_processor.process_message(
            user_message=user_message,
            username=username,
            user_id=user_id
        )
        
        print(f"[MeiLin] → {username}: {response_text}")
        
        return jsonify({
            "response": response_text,
            "status": "success",
            "username": username
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Lỗi xử lý request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Endpoint chuyển text thành audio (optional)
    Request JSON:
    {
        "text": "Xin chào các Anh Chị"
    }
    Response: Audio file (MP3)
    """
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                "error": "Thiếu trường 'text'",
                "status": "error"
            }), 400
        
        # Tạo audio file
        audio_path = tts_engine.generate_audio_file(text)
        
        if audio_path:
            from flask import send_file
            return send_file(audio_path, mimetype='audio/mpeg')
        else:
            return jsonify({
                "error": "Không thể tạo audio",
                "status": "error"
            }), 500
            
    except Exception as e:
        print(f"[ERROR] Lỗi TTS: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/user/info', methods=['GET'])
def get_user_info():
    """
    Lấy thông tin người dùng từ lịch sử chat
    Query params: ?username=ESP32_User
    """
    try:
        username = request.args.get('username', '')
        
        if not username:
            return jsonify({
                "error": "Thiếu tham số 'username'",
                "status": "error"
            }), 400
        
        # Lấy lịch sử chat
        history = chat_processor.chat_db.filter_history_by_username(username)
        
        return jsonify({
            "username": username,
            "history_count": len(history) if isinstance(history, list) else 0,
            "status": "success"
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Lỗi lấy thông tin user: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

# ============================================================================
# Wake Word and Command Endpoints (for ESP32)
# ============================================================================

@app.route('/wake', methods=['POST'])
def wake_event():
    """
    Nhận sự kiện wake word từ ESP32
    Request JSON:
    {
        "device_id": "ESP32_001",
        "timestamp": "2024-12-03T20:00:00",
        "confidence": 0.95
    }
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'unknown')
        confidence = data.get('confidence', 0.0)
        timestamp = data.get('timestamp', '')
        
        print(f"\n[WAKE] Device {device_id} woke up (confidence: {confidence:.2f})")
        
        # Trả về greeting message
        return jsonify({
            "status": "success",
            "message": "MeiLin đây! Em nghe đây ạ!",
            "device_id": device_id
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Wake event error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/command', methods=['POST'])
def command():
    """
    Xử lý voice command từ ESP32
    Request JSON:
    {
        "command": "bật đèn phòng khách",
        "username": "ESP32_User",
        "device_id": "ESP32_001"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'command' not in data:
            return jsonify({
                "error": "Missing 'command' field",
                "status": "error"
            }), 400
        
        command_text = data.get('command', '').strip()
        username = data.get('username', 'ESP32_User')
        device_id = data.get('device_id', 'unknown')
        
        print(f"\n[COMMAND] {username}@{device_id}: {command_text}")
        
        # Xử lý command như một chat message
        response_text = chat_processor.process_message(
            user_message=f"[Command] {command_text}",
            username=username,
            user_id=device_id
        )
        
        return jsonify({
            "status": "success",
            "response": response_text,
            "command": command_text,
            "audio_url": None  # TTS audio URL nếu có
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Command error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

# ============================================================================
# ESP32 Hybrid Mode - Sử dụng MeiLin RAG + XiaoZhi LLM (Free)
# ============================================================================

@app.route('/esp/validate', methods=['POST'])
def esp_validate_device():
    """
    Validate ESP device API key và trả về thông tin device
    Request JSON:
    {
        "device_api_key": "meilin_dev_xxxx"
    }
    Response: Device info + owner's personality settings
    """
    try:
        data = request.get_json()
        device_key = data.get('device_api_key', '')
        
        if not device_key:
            return jsonify({
                "valid": False,
                "error": "Missing device_api_key"
            }), 400
        
        # Validate device
        result = esp_device_manager.validate_device_key(device_key)
        
        if not result['valid']:
            return jsonify(result), 401
        
        # Update device seen
        esp_device_manager.update_device_seen(result['device_id'])
        
        # Get owner's personality settings
        telegram_user_id = result['telegram_user_id']
        user_profile = user_manager.get_user(str(telegram_user_id))
        
        personality = {}
        if user_profile:
            personality = {
                'name': user_profile.get('personality', {}).get('name', 'MeiLin'),
                'wake_word': user_profile.get('personality', {}).get('wake_word', 'Hi MeiLin'),
                'speaking_style': user_profile.get('personality', {}).get('speaking_style', 'friendly'),
                'language': user_profile.get('personality', {}).get('language', 'vi')
            }
        
        return jsonify({
            "valid": True,
            "device_id": result['device_id'],
            "device_name": result['device_name'],
            "personality": personality,
            "status": "success"
        }), 200
        
    except Exception as e:
        print(f"[ERROR] ESP validate error: {e}")
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 500

@app.route('/esp/rag', methods=['POST'])
def esp_query_rag():
    """
    ESP truy vấn MeiLin Knowledge Base (RAG)
    Dùng cho Hybrid Mode: ESP sử dụng MeiLin RAG + XiaoZhi LLM
    
    Request JSON:
    {
        "device_api_key": "meilin_dev_xxxx",
        "query": "MeiLin thích ăn gì?"
    }
    Response:
    {
        "context": "MeiLin thích ăn phở và bánh mì...",
        "sources": ["Personal Knowledge", "User Upload"],
        "prompt_template": "Bạn là MeiLin, một AI assistant..."
    }
    """
    try:
        data = request.get_json()
        device_key = data.get('device_api_key', '')
        query = data.get('query', '').strip()
        
        if not device_key:
            return jsonify({
                "status": "error",
                "error": "Missing device_api_key"
            }), 400
        
        if not query:
            return jsonify({
                "status": "error",
                "error": "Missing query"
            }), 400
        
        # Validate device
        device_info = esp_device_manager.validate_device_key(device_key)
        
        if not device_info['valid']:
            return jsonify({
                "status": "error",
                "error": device_info.get('error', 'Invalid device key')
            }), 401
        
        # Update device activity
        esp_device_manager.update_device_seen(device_info['device_id'])
        
        # Get owner info for personalized RAG
        telegram_user_id = device_info['telegram_user_id']
        user_id_str = str(telegram_user_id)
        
        # Query RAG for context
        context = rag_system.get_context(query=query, n_results=3)
        
        # Get personality for prompt template
        user_profile = user_manager.get_user(user_id_str)
        personality = {}
        if user_profile:
            personality = user_profile.get('personality', {})
        
        # Build system prompt suggestion
        name = personality.get('name', 'MeiLin')
        style = personality.get('speaking_style', 'friendly')
        lang = personality.get('language', 'vi')
        
        system_prompt = f"""Bạn là {name}, một AI assistant thân thiện.
Phong cách: {style}
Ngôn ngữ: {lang}

Kiến thức cá nhân:
{context}

Hãy trả lời câu hỏi của người dùng dựa trên kiến thức trên."""
        
        print(f"[ESP/RAG] {device_info['device_name']}: {query[:50]}...")
        
        return jsonify({
            "status": "success",
            "context": context,
            "sources": ["MeiLin Knowledge Base"],
            "system_prompt": system_prompt,
            "personality": {
                "name": name,
                "style": style,
                "language": lang
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] ESP RAG error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/esp/chat', methods=['POST'])
def esp_chat_with_keys():
    """
    ESP chat sử dụng API keys của owner (Full Mode)
    Dùng khi user muốn ESP dùng API keys của họ để chat
    
    Request JSON:
    {
        "device_api_key": "meilin_dev_xxxx",
        "message": "Xin chào MeiLin"
    }
    Response:
    {
        "response": "Xin chào! Em là MeiLin...",
        "status": "success"
    }
    """
    try:
        data = request.get_json()
        device_key = data.get('device_api_key', '')
        message = data.get('message', '').strip()
        
        if not device_key:
            return jsonify({
                "status": "error",
                "error": "Missing device_api_key"
            }), 400
        
        if not message:
            return jsonify({
                "status": "error",
                "error": "Missing message"
            }), 400
        
        # Validate device
        device_info = esp_device_manager.validate_device_key(device_key)
        
        if not device_info['valid']:
            return jsonify({
                "status": "error",
                "error": device_info.get('error', 'Invalid device key')
            }), 401
        
        # Update device activity
        esp_device_manager.update_device_seen(device_info['device_id'])
        
        # Get owner's API keys
        telegram_user_id = device_info['telegram_user_id']
        user_id_str = str(telegram_user_id)
        
        # Check if user has configured LLM
        llm_config = api_key_manager.get_api_key(user_id_str, 'llm')
        
        if not llm_config or not llm_config.get('api_key'):
            return jsonify({
                "status": "error",
                "error": "Owner has not configured LLM API key. Please configure via Telegram bot.",
                "needs_config": True
            }), 403
        
        # Create personalized chat processor for this user
        print(f"[ESP/Chat] {device_info['device_name']}: {message[:50]}...")
        
        # Use the chat processor with user context
        response_text = chat_processor.process_message(
            user_message=message,
            username=device_info['device_name'],
            user_id=user_id_str
        )
        
        print(f"[MeiLin] → {device_info['device_name']}: {response_text[:80]}...")
        
        return jsonify({
            "status": "success",
            "response": response_text,
            "device": device_info['device_name']
        }), 200
        
    except Exception as e:
        print(f"[ERROR] ESP chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# ============================================================================
# OTA (Over-the-Air) Firmware Update Endpoints
# ============================================================================

@app.route('/api/ota/check', methods=['GET'])
def check_ota_update():
    """
    Kiểm tra có firmware update không
    Query params: 
    ?device_id=esp32_001&version=v1.0.0&board_type=esp32s3
    """
    try:
        device_id = request.args.get('device_id', '')
        current_version = request.args.get('version', 'v1.0.0')
        board_type = request.args.get('board_type', 'esp32s3')
        
        if not device_id:
            return jsonify({
                "error": "Thiếu tham số 'device_id'",
                "status": "error"
            }), 400
        
        # Đăng ký device
        client_ip = request.remote_addr
        ota_manager.register_device(device_id, board_type, current_version, client_ip)
        
        # Kiểm tra update
        update_info = ota_manager.check_for_updates(device_id, current_version, board_type)
        
        return jsonify({
            "status": "success",
            "device_id": device_id,
            **update_info
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Lỗi kiểm tra OTA: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/ota/download/<version>/<board_type>', methods=['GET'])
def download_ota_firmware(version: str, board_type: str):
    """
    Download firmware binary file
    """
    try:
        firmware_info = ota_manager.get_firmware_file(version, board_type)
        
        if not firmware_info:
            return jsonify({
                "error": f"Firmware không tồn tại: {version}-{board_type}",
                "status": "error"
            }), 404
        
        # Log download attempt
        device_id = request.args.get('device_id', 'unknown')
        ota_manager.log_update_attempt(
            device_id=device_id,
            from_version=request.args.get('current_version', 'unknown'),
            to_version=version,
            success=True,
            error_msg="Download initiated"
        )
        
        print(f"[OTA] Firmware download: {device_id} → {version}-{board_type}")
        
        # Send firmware file
        return send_file(
            firmware_info.file_path,
            as_attachment=True,
            download_name=f"meilin-{version}-{board_type}.bin",
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        print(f"[ERROR] Lỗi download firmware: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/ota/status', methods=['POST'])
def report_ota_status():
    """
    ESP32 report OTA update status
    Request JSON:
    {
        "device_id": "esp32_001",
        "from_version": "v1.0.0",
        "to_version": "v1.1.0", 
        "success": true,
        "error_message": "" (nếu có lỗi)
    }
    """
    try:
        data = request.get_json()
        
        device_id = data.get('device_id', '')
        from_version = data.get('from_version', '')
        to_version = data.get('to_version', '')
        success = data.get('success', False)
        error_message = data.get('error_message', '')
        
        if not device_id:
            return jsonify({
                "error": "Thiếu trường 'device_id'",
                "status": "error"
            }), 400
        
        # Log OTA result
        ota_manager.log_update_attempt(
            device_id=device_id,
            from_version=from_version,
            to_version=to_version,
            success=success,
            error_msg=error_message
        )
        
        status = "success" if success else "failed"
        print(f"[OTA] Update {status}: {device_id} {from_version} → {to_version}")
        
        return jsonify({
            "status": "success",
            "message": f"OTA status recorded: {status}"
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Lỗi report OTA status: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/ota/stats', methods=['GET'])
def get_ota_stats():
    """Lấy thống kê OTA updates"""
    try:
        stats = ota_manager.get_update_stats()
        
        return jsonify({
            "status": "success",
            "stats": stats
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Lỗi lấy OTA stats: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


# ============================================================
# PUBLIC RAG API - Cho ESP32 devices (read-only knowledge base)
# ============================================================
from modules.public_rag_api import get_public_rag_api, require_api_key

@app.route('/public/rag/query', methods=['POST'])
@require_api_key
def public_rag_query():
    """
    Query knowledge base (PUBLIC - read-only)
    Yêu cầu API key trong header: X-API-Key
    
    Request JSON:
    {
        "query": "Câu hỏi về MeiLin",
        "top_k": 3  (optional, default 3)
    }
    
    Response JSON:
    {
        "results": [
            {"content": "...", "relevance": 0.85},
            ...
        ],
        "count": 3
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        top_k = min(data.get('top_k', 3), 5)  # Max 5 results
        
        if not query:
            return jsonify({
                'error': 'Query is required',
                'status': 'error'
            }), 400
        
        api = get_public_rag_api()
        results = api.query_knowledge(query, top_k)
        
        # Log request
        api.log_request(request.api_key, query, len(results))
        
        return jsonify({
            'results': results,
            'count': len(results),
            'status': 'success'
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Public RAG query: {e}")
        return jsonify({
            'error': 'Internal error',
            'status': 'error'
        }), 500


@app.route('/public/register', methods=['POST'])
def public_register_device():
    """
    Đăng ký device mới để nhận API key
    
    Request JSON:
    {
        "device_id": "esp32_abc123",
        "device_name": "Living Room MeiLin" (optional)
    }
    
    Response JSON:
    {
        "api_key": "meilin_pk_...",
        "message": "Device registered successfully"
    }
    """
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', '').strip()
        device_name = data.get('device_name', '')
        
        if not device_id:
            return jsonify({
                'error': 'device_id is required',
                'status': 'error'
            }), 400
        
        # Validate device_id format
        if len(device_id) < 6 or len(device_id) > 50:
            return jsonify({
                'error': 'device_id must be 6-50 characters',
                'status': 'error'
            }), 400
        
        api = get_public_rag_api()
        api_key = api.generate_api_key(device_id, device_name)
        
        print(f"[PublicAPI] New device registered: {device_id}")
        
        return jsonify({
            'api_key': api_key,
            'device_id': device_id,
            'message': 'Device registered successfully. Save your API key!',
            'usage': {
                'endpoint': '/public/rag/query',
                'header': 'X-API-Key: ' + api_key,
                'rate_limit': '30 requests/minute'
            },
            'status': 'success'
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Device registration: {e}")
        return jsonify({
            'error': 'Registration failed',
            'status': 'error'
        }), 500


@app.route('/public/stats', methods=['GET'])
@require_api_key
def public_device_stats():
    """Lấy thống kê sử dụng của device"""
    try:
        api = get_public_rag_api()
        stats = api.get_device_stats(request.api_key)
        
        return jsonify({
            'stats': stats,
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get stats',
            'status': 'error'
        }), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 MeiLin API Server for ESP32/IoT Devices")
    print("="*60)
    print("\n📡 Private Endpoints (full access):")
    print("  - GET  /health          : Kiểm tra server")
    print("  - POST /chat            : Chat với MeiLin")
    print("  - POST /tts             : Text-to-Speech")
    print("  - GET  /user/info       : Lấy thông tin user")
    print("  - GET  /api/ota/*       : OTA updates")
    print("\n📱 ESP32 Hybrid Mode Endpoints:")
    print("  - POST /esp/validate    : Validate device API key")
    print("  - POST /esp/rag         : Query RAG với device key")
    print("  - POST /esp/chat        : Chat sử dụng owner's API keys")
    print("\n🌐 Public Endpoints (read-only, API key required):")
    print("  - POST /public/register     : Đăng ký device, nhận API key")
    print("  - POST /public/rag/query    : Query knowledge base")
    print("  - GET  /public/stats        : Xem thống kê sử dụng")
    print("\n🔑 ESP32 Usage Modes:")
    print("  1. XiaoZhi Pure: ESP → XiaoZhi Cloud (free)")
    print("  2. Hybrid Mode : ESP → MeiLin RAG + XiaoZhi LLM (free)")
    print("  3. Full Mode   : ESP → MeiLin Server (needs API keys)")
    print("\n🌐 Server đang chạy tại:")
    print("  - Local:   http://127.0.0.1:5000")
    print("  - Network: http://<your_ip>:5000")
    print("\n" + "="*60 + "\n")
    
    # Chạy server
    app.run(host='0.0.0.0', port=5000, debug=False)
