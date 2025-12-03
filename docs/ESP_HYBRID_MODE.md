# ESP32 Hybrid Mode - MeiLin RAG + LLM/TTS linh hoạt

## 🎯 Mục đích

Hybrid Mode cho phép người dùng ESP32 sử dụng:
- **MeiLin Knowledge Base (RAG)** - Kiến thức cá nhân hóa của bạn
- **LLM/TTS linh hoạt** - Mặc định XiaoZhi (miễn phí), hoặc đổi sang API riêng

## 📊 So sánh các chế độ

| Chế độ | LLM | TTS | RAG | Chi phí | Yêu cầu |
|--------|-----|-----|-----|---------|---------|
| **XiaoZhi Pure** | XiaoZhi | XiaoZhi | ❌ | Free | Không |
| **Hybrid Mode** | XiaoZhi *(mặc định)* | XiaoZhi *(mặc định)* | MeiLin ✅ | Free | Đăng ký Device |
| **MeiLin Full** | User's API | User's API | MeiLin ✅ | Có | Self-host Server |

### 💡 Hybrid Mode - Mặc định MIỄN PHÍ + Tùy chọn nâng cấp

**Mặc định (không cần cấu hình gì thêm):**
- ✅ RAG: MeiLin Server 
- ✅ LLM: XiaoZhi Cloud (miễn phí)
- ✅ TTS: XiaoZhi Cloud (miễn phí)

**Tùy chọn nâng cấp (qua Telegram Bot):**
- Đổi LLM: DeepSeek, OpenAI, Gemini, Groq...
- Đổi TTS: Edge TTS, ElevenLabs, OpenAI TTS...
- Điền API key an toàn, mã hóa bằng Fernet

## 🔧 Cách hoạt động Hybrid Mode

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   ESP32 Device  │      │  MeiLin Server  │      │  XiaoZhi Cloud  │
│                 │      │                 │      │                 │
│  1. Query RAG ──┼────► │  2. Search KB   │      │                 │
│                 │ ◄────┼── 3. Context    │      │                 │
│                 │      │                 │      │                 │
│  4. Add context │      │                 │      │                 │
│     to prompt   │      │                 │      │                 │
│                 │      │                 │      │                 │
│  5. Call LLM ───┼──────┼─────────────────┼────► │  6. Generate    │
│                 │ ◄────┼─────────────────┼───── │     Response    │
│                 │      │                 │      │                 │
│  7. Call TTS ───┼──────┼─────────────────┼────► │  8. Generate    │
│                 │ ◄────┼─────────────────┼───── │     Audio       │
│                 │      │                 │      │                 │
│  9. Play Audio  │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 📝 Hướng dẫn sử dụng

### Bước 1: Đăng ký Device qua Telegram Bot

1. Mở Telegram Bot: [@MeiLinProject_bot](https://t.me/MeiLinProject_bot)
2. Gõ `/start` để bắt đầu
3. Chọn **📱 ESP Devices**
4. Chọn **➕ Đăng ký Device mới**
5. Nhập Device ID (ví dụ: `esp32_living_room`)
6. Nhập tên Device (tùy chọn)
7. **Lưu Device API Key** hiển thị

### Bước 2: Cấu hình ESP32

#### Trong `menuconfig`:

```
→ MeiLin Configuration
  → Connection Mode: Hybrid (MeiLin RAG + XiaoZhi LLM)
  → MeiLin Server URL: https://meilin.truongcongdinh.org
  → Device API Key: meilin_dev_xxxxx (key từ Bước 1)
```

#### Hoặc trong code:

```cpp
#define CONFIG_MEILIN_MODE_HYBRID   1
#define CONFIG_MEILIN_SERVER_URL    "https://meilin.truongcongdinh.org"
#define CONFIG_MEILIN_DEVICE_KEY    "meilin_dev_xxxxx"
```

### Bước 3: Upload Knowledge (Tùy chọn)

1. Mở Telegram Bot
2. Chọn **📚 Knowledge Base**
3. Upload file Excel với kiến thức của bạn
4. ESP sẽ tự động sử dụng kiến thức này

### Bước 4: Cấu hình API riêng (Tùy chọn - Hybrid Premium)

Nếu bạn muốn dùng LLM/TTS chất lượng cao hơn XiaoZhi miễn phí:

1. Mở Telegram Bot: [@MeiLinProject_bot](https://t.me/MeiLinProject_bot)
2. Chọn **🔧 Cấu hình API**
3. Chọn **LLM Provider** (DeepSeek, OpenAI, Gemini...)
4. Nhập API Key của bạn
5. (Tùy chọn) Chọn TTS Provider và nhập API Key

**Lưu ý bảo mật:**
- 🔒 API keys được mã hóa bằng Fernet (AES-128-CBC)
- 🔒 Keys chỉ được giải mã khi cần sử dụng
- 🔒 Mỗi user có encryption key riêng
- 🔒 Không ai (kể cả admin) có thể đọc được API key gốc

**Providers hỗ trợ:**

| LLM | TTS |
|-----|-----|
| DeepSeek ⭐ (giá rẻ) | Edge TTS (miễn phí) |
| OpenAI | ElevenLabs |
| Gemini | OpenAI TTS |
| Ollama (local) | |
| Groq | |

## 🔌 API Endpoints

### 1. Validate Device

```http
POST /esp/validate
Content-Type: application/json

{
    "device_api_key": "meilin_dev_xxxxx"
}
```

**Response:**
```json
{
    "valid": true,
    "device_id": "esp32_living_room",
    "device_name": "ESP32 Phòng khách",
    "personality": {
        "name": "MeiLin",
        "wake_word": "Hi MeiLin",
        "speaking_style": "friendly",
        "language": "vi"
    },
    "status": "success"
}
```

### 2. Query RAG

```http
POST /esp/rag
Content-Type: application/json

{
    "device_api_key": "meilin_dev_xxxxx",
    "query": "MeiLin thích ăn gì?"
}
```

**Response:**
```json
{
    "status": "success",
    "context": "MeiLin thích ăn phở và bánh mì...",
    "sources": ["MeiLin Knowledge Base"],
    "system_prompt": "Bạn là MeiLin, một AI assistant...\n\nKiến thức cá nhân:\n...",
    "personality": {
        "name": "MeiLin",
        "style": "friendly",
        "language": "vi"
    }
}
```

### 3. Full Chat (sử dụng owner's API keys)

```http
POST /esp/chat
Content-Type: application/json

{
    "device_api_key": "meilin_dev_xxxxx",
    "message": "Xin chào MeiLin"
}
```

**Response:**
```json
{
    "status": "success",
    "response": "Xin chào! Em là MeiLin đây ạ! Hôm nay anh/chị có khỏe không?",
    "device": "ESP32 Phòng khách"
}
```

## 🔒 Bảo mật

- Device API Key được mã hóa lưu trữ
- Mỗi device chỉ có thể truy cập knowledge của owner
- Rate limiting: 30 requests/phút
- Logging đầy đủ cho audit

## 📱 ESP32 Code Flow (Hybrid Mode)

```cpp
void handleVoiceQuery(const char* query) {
    // 1. Query MeiLin RAG để lấy context
    HTTPClient http;
    http.begin("https://meilin.truongcongdinh.org/esp/rag");
    http.addHeader("Content-Type", "application/json");
    
    String payload = "{\"device_api_key\":\"" + deviceKey + 
                     "\",\"query\":\"" + query + "\"}";
    
    int httpCode = http.POST(payload);
    if (httpCode == 200) {
        String response = http.getString();
        DynamicJsonDocument doc(2048);
        deserializeJson(doc, response);
        
        String context = doc["context"];
        String systemPrompt = doc["system_prompt"];
        
        // 2. Gọi XiaoZhi LLM với system prompt đã có context
        xiaozhi_chat_with_context(query, systemPrompt);
    }
    http.end();
}
```

## ❓ FAQ

### Q: Hybrid Mode có miễn phí không?
**A:** Có! Bạn chỉ cần host MeiLin Server. LLM và TTS sử dụng XiaoZhi Cloud hoàn toàn miễn phí.

### Q: Knowledge Base được lưu ở đâu?
**A:** Trên MeiLin Server của bạn, trong ChromaDB local. Dữ liệu không rời khỏi server.

### Q: Tôi có thể thêm nhiều device không?
**A:** Có! Mỗi device sẽ có API key riêng nhưng chia sẻ chung knowledge base.

### Q: Có giới hạn số request không?
**A:** Có rate limiting 30 requests/phút để bảo vệ server.

## 📞 Support

- Telegram: [@MeiLinProject_bot](https://t.me/MeiLinProject_bot)
- GitHub Issues: https://github.com/truongcongdinh97/MeiLin_Server/issues
