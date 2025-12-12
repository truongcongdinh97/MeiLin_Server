# MeiLin Full Control Mode - Quick Start Guide

## Tổng quan

MeiLin Full Control Mode cho phép bạn tự host toàn bộ pipeline xử lý giọng nói:
- **STT (Speech-to-Text)**: Nhận diện giọng nói
- **LLM (Language Model)**: Xử lý và trả lời
- **TTS (Text-to-Speech)**: Tổng hợp giọng nói

### Ưu điểm của MeiLin Full Control

| Tính năng | MeiLin Full Control |
|-----------|---------------------|
| Chi phí | Miễn phí (Vosk) hoặc tùy chọn |
| STT | Tự host (Vosk/Groq/OpenAI) |
| LLM | Tự host |
| TTS | Tự host |
| Latency | Có thể thấp hơn nếu local |
| Privacy | 100% local với Vosk |
| Customization | Hoàn toàn tùy chỉnh |

## Cài đặt

### 1. Cài đặt Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Cấu hình STT Provider

Có 3 lựa chọn STT:

#### a) Vosk (Mặc định - Miễn phí, Offline)
- Không cần API key
- Model Vietnamese sẽ được tự động tải (~40MB)
- Chạy hoàn toàn offline

```bash
# Model sẽ được tải tự động khi lần đầu sử dụng
# Hoặc tải thủ công:
mkdir -p modules/models
cd modules/models
wget https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip
unzip vosk-model-small-vn-0.4.zip
```

#### b) Groq Whisper (Miễn phí với API key)
1. Đăng ký tại https://console.groq.com
2. Tạo API key (miễn phí)
3. Cấu hình qua Telegram bot

#### c) OpenAI Whisper (Trả phí)
1. Có OpenAI API key
2. Chi phí: ~$0.006/phút
3. Cấu hình qua Telegram bot

### 3. Chạy Server

```bash
python run_meilin_server.py
```

Server sẽ khởi động:
- **HTTP API**: http://0.0.0.0:5000
- **WebSocket**: ws://0.0.0.0:8765

### 4. Cấu hình ESP32

Trong firmware ESP32, thay đổi WebSocket URL:

```cpp
// Cấu hình WebSocket URL cho MeiLin Server
#define MEILIN_WS_URL "ws://YOUR_SERVER_IP:8765"
```

### 5. Cấu hình STT qua Telegram

1. Mở Telegram bot
2. Gõ `/start` hoặc `/config`
3. Chọn "🎤 Đổi STT (Nhận diện giọng nói)"
4. Chọn provider:
   - 🆓 Vosk (Free Local) - Mặc định
   - ⚡ Groq Whisper (Free API)
   - 🎤 OpenAI Whisper
5. Nhập API key nếu cần

## Kiểm tra

Chạy script test để kiểm tra tất cả components:

```bash
python test_meilin_server.py
```

## Ports và Firewall

Đảm bảo các ports sau được mở:

| Port | Protocol | Mục đích |
|------|----------|----------|
| 5000 | TCP | Flask API Server |
| 8765 | TCP | WebSocket Server |

```bash
# Ubuntu/Debian
sudo ufw allow 5000/tcp
sudo ufw allow 8765/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --add-port=8765/tcp --permanent
sudo firewall-cmd --reload
```

## WebSocket Protocol

MeiLin WebSocket Server sử dụng protocol tương thích:

### Kết nối (Hello)
```json
{
  "type": "hello",
  "version": 3,
  "device_id": "esp32_001",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

### Bắt đầu nghe
```json
{
  "type": "listen",
  "state": "start",
  "mode": "manual"
}
```

### Gửi audio
- Binary data (Opus encoded)

### Kết thúc nghe
```json
{
  "type": "listen",
  "state": "stop"
}
```

### Nhận kết quả

STT result:
```json
{
  "type": "stt",
  "text": "Xin chào MeiLin"
}
```

TTS start:
```json
{
  "type": "tts",
  "state": "start"
}
```

TTS audio:
- Binary data (Opus encoded)

TTS end:
```json
{
  "type": "tts",
  "state": "stop"
}
```

## Troubleshooting

### 1. Vosk model không tải được

```bash
# Tải thủ công
wget https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip
unzip vosk-model-small-vn-0.4.zip -d modules/models/
```

### 2. opuslib không cài được

```bash
# Ubuntu/Debian
sudo apt install libopus-dev
pip install opuslib

# macOS
brew install opus
pip install opuslib

# Windows
# Dùng wheel từ https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

### 3. WebSocket connection refused

- Kiểm tra firewall
- Kiểm tra IP address
- Đảm bảo server đang chạy

### 4. STT không nhận diện được

- Kiểm tra microphone trên ESP32
- Kiểm tra audio format (Opus, 16kHz, mono)
- Thử provider khác (Groq thường chính xác hơn)

## Cấu trúc Files

```
server/
├── run_meilin_server.py     # Entry point
├── test_meilin_server.py    # Test script
├── meilin_api_server.py     # Flask API
├── modules/
│   ├── stt_engine.py        # STT providers
│   ├── websocket_server.py  # WebSocket server
│   ├── chat_processor.py    # LLM processing
│   ├── tts_engine.py        # TTS providers
│   └── models/              # STT models (Vosk)
│       └── vosk-model-small-vn-0.4/
├── bot/
│   └── telegram_bot.py      # Telegram bot with STT config
└── database/
    └── schema.sql           # Database schema
```

## STT Providers Comparison

| Provider | Free | Offline | Speed | Accuracy | Setup |
|----------|------|---------|-------|----------|-------|
| Vosk | ✅ | ✅ | Medium | Good | Easy |
| Groq | ✅ | ❌ | Fast | Excellent | API key |
| OpenAI | ❌ | ❌ | Medium | Excellent | API key |

## Liên hệ

- GitHub: https://github.com/truongcongdinh97/MeiLin_Project
- Issues: [GitHub Issues](https://github.com/truongcongdinh97/MeiLin_Project/issues)
