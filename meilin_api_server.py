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

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 MeiLin API Server for ESP32/IoT Devices")
    print("="*60)
    print("\n📡 Endpoints:")
    print("  - GET  /health          : Kiểm tra server")
    print("  - POST /chat            : Chat với MeiLin")
    print("  - POST /tts             : Text-to-Speech (optional)")
    print("  - GET  /user/info       : Lấy thông tin user")
    print("  - GET  /api/ota/check   : Kiểm tra firmware update")
    print("  - GET  /api/ota/download: Download firmware")
    print("  - POST /api/ota/status  : Report OTA status")
    print("  - GET  /api/ota/stats   : Lấy thống kê OTA")
    print("\n🌐 Server đang chạy tại:")
    print("  - Local:   http://127.0.0.1:5000")
    print("  - Network: http://<your_ip>:5000")
    print("\n💡 Ví dụ request từ ESP32:")
    print('  POST http://<your_ip>:5000/chat')
    print('  Body: {"message": "Xin chào", "username": "ESP32_001"}')
    print("\n" + "="*60 + "\n")
    
    # Chạy server
    # host='0.0.0.0' cho phép ESP32 truy cập từ mạng LAN
    app.run(host='0.0.0.0', port=5000, debug=False)
