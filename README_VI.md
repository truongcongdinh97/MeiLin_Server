# 🎭 MeiLin AI VTuber Dự Án

[![GitHub](https://img.shields.io/badge/GitHub-PROJECT__MEILIN__AIVTUBER-blue?logo=github)](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER)
[![Python](https://img.shields.io/badge/Python-3.13-green?logo=python)](https://www.python.org/)
[![Giấy Phép](https://img.shields.io/badge/Giấy Phép-MIT-yellow.svg)](LICENSE)

**Production-ready AI VTuber framework** with advanced personality system, multi-platform support, and intelligent content generation. Create a living, breathing virtual character that can stream on YouTube, chat on Telegram, and interact naturally like a real person.

---

## ✨ Core Tính Năng

### 🎭 **Living Personality System**
- **30 Ambient Behaviors**: Natural actions like sighing, giggling, yawning, humming - making your VTuber feel alive
- **8 Personality Modes**: Switch between Energetic, Calm, Sleepy, Playful, Shy, Confident, Moody, and Focused
- **Context-Aware**: Behaviors adapt to stream context (idle, active, excited, tired, happy, sad)
- **Real-time Mode Switching**: Change personality on-the-fly with keyboard shortcuts

### 🎬 **Content Creator Mode**
- **Auto-Story Generation**: Creates engaging stories, fun facts, thoughts, trivia, and advice when idle
- **Natural Transitions**: Smooth flow between viewer interactions and generated content
- **Customizable Duration**: Control content length based on speaking time
- **LLM-Powered**: Uses AI to generate contextually relevant and entertaining content

### 🌐 **Multi-Platform Support**
- **YouTube Livestream**: Full integration with YouTube chat, OAuth authentication, owner detection
- **Telegram Bot**: Complete bot with commands, voice messages, provider switching
- **ESP32 Hardware**: Physical device integration with wake word detection and IoT control
- **IoT Commands**: Control smart devices via HTTP/Telegram (lights, computers, etc.)
- **API Server**: RESTful API for custom integrations and ESP32 communication

### 🤖 **Advanced AI System**
- **Multi-Provider LLM**: Deepseek, OpenAI, Claude, Gemini, Ollama - switch anytime
- **Multi-TTS Engine**: ElevenLabs, Edge TTS (free), Google TTS, Azure TTS, pyttsx3
- **Automatic Fallback**: Seamlessly switches to backup provider on failure
- **RAG (Retrieval-Augmented Generation)**: Context-aware responses using knowledge base
- **Response Cache**: Pre-recorded audio for instant responses (wake words, greetings)
- **Command Detection**: Automatic detection of IoT commands without LLM call

### 👤 **Smart User Management**
- **Persistent Profiles**: Remembers viewers by user_id across sessions
- **Owner Recognition**: Special treatment for channel owner (configurable via user_id)
- **Gender Detection**: Automatically detects and uses appropriate pronouns (Anh/Chị)
- **Conversation History**: Maintains context across messages, never repeats greetings

### 💾 **Flexible Database**
- **Auto-Detection**: Seamlessly switches between Cloud and Local ChromaDB
- **Role-Based Retrieval**: Query knowledge by role (friend, assistant, expert, entertainer)
- **Pre-loaded Knowledge**: Ready-to-use database included
- **Easy Updates**: Scripts for adding custom knowledge

### 🎮 **Interactive Controls**
- **Hotkeys**: `Ctrl+E` (TTS toggle), `Ctrl+M` (mode switch), `Ctrl+Shift+M` (show mode)
- **Command System**: Full-featured commands for Telegram (`/set_llm`, `/set_tts`, `/info`)
- **Real-time Adjustments**: Change settings without restarting

### 🔐 **Production-Ready**
- **Security First**: Environment-based secrets, never commit credentials
- **Error Handling**: Comprehensive error handling and graceful fallbacks
- **Logging System**: Detailed logs for gỡ lỗi and monitoring
- **Modular Kiến Trúc**: Easy to extend and customize

---

## 🚀 Bắt Đầu Nhanh

### Prerequisites
- Python 3.13+
- API Key from [Deepseek](https://platform.deepseek.com/) (free tier available)
- Optional: API keys for other LLM/TTS providers

### Cài Đặt

```bash
# 1. Clone repository
git clone https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER.git
cd PROJECT_MEILIN_AIVTUBER

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Edit .env and add your API keys (minimum: DEEPSEEK_API_KEY)

# 4. Customize personality (optional)
# Edit config/personality.json and config/config.yaml

# 5. Choose your platform:

# ⭐ Standalone Console (Recommended for testing)
# Interactive chat, IoT commands, no YouTube needed
python meilin_standalone.py

# YouTube Livestream (requires OAuth setup)
# Add video_id to youtube.txt, setup oauth credentials
python main.py

# Telegram Bot
# Add TELEGRAM_BOT_TOKEN to .env
python telegram_bot.py

# API Server (for ESP32/custom integrations)
python api_server.py
```

📖 **[Detailed Thiết Lập Hướng Dẫns](#-tài liệu)**

---

## 🎯 Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                    MeiLin AI VTuber                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   YouTube    │  │   Telegram   │  │   ESP32/API  │      │
│  │  Livestream  │  │     Bot      │  │   Hardware   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            ↓                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Chat Processor & Context Manager            │    │
│  │  • User Profile Management (Persistent Storage)     │    │
│  │  • Owner Detection (user_id based)                  │    │
│  │  • Gender Detection & Pronoun Handling              │    │
│  │  • Conversation History Tracking                    │    │
│  └──────────┬──────────────────────────────┬───────────┘    │
│             │                               │                │
│    ┌────────▼────────┐            ┌────────▼────────┐       │
│    │   RAG System    │            │ Content Creator │       │
│    │ • Role-based    │            │ • Story Gen     │       │
│    │ • ChromaDB      │            │ • Auto Content  │       │
│    │ • Context       │            │ • Idle Detection│       │
│    └────────┬────────┘            └────────┬────────┘       │
│             │                               │                │
│    ┌────────▼───────────────────────────────▼────────┐      │
│    │         LLM Provider Manager                     │      │
│    │  Deepseek | OpenAI | Claude | Gemini | Ollama   │      │
│    └────────┬─────────────────────────────────────────┘      │
│             │                                                │
│    ┌────────▼────────┐          ┌──────────────────┐        │
│    │  TTS Engine     │          │ Ambient Behavior │        │
│    │  (with fallback)│          │ • 30 Behaviors   │        │
│    │  ElevenLabs →   │          │ • 8 Modes        │        │
│    │  Edge TTS       │          │ • Context-aware  │        │
│    └─────────────────┘          └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 🔄 Message Flow

1. **Input**: User message from YouTube/Telegram/API
2. **Profile**: Load/create persistent user profile (user_id based)
3. **Context**: Retrieve relevant knowledge via RAG (role-based)
4. **Content**: Generate story if idle (Content Creator Mode)
5. **LLM**: Generate response using context + history + personality
6. **Ambient**: Add natural behaviors (sighs, giggles, etc.)
7. **TTS**: Synthesize voice with automatic fallback
8. **Output**: Deliver response with personality

### 💾 Database Kiến Trúc

**🏠 Local ChromaDB (Default)**
- ✅ Zero cấu hình required
- ✅ Works completely offline
- ✅ Pre-loaded knowledge base
- 📁 Location: `database/vector_db/`
- 🔍 Role-based metadata queries

**🌐 Cloud ChromaDB (Optional)**
- Multi-device synchronization
- Team collaboration support
- Centralized knowledge base
- Enable: Add `CHROMADB_API_URL` to `.env`

---

## 📚 Tài Liệu

### 🎓 User Hướng Dẫns
| Document | Description | Topics |
|----------|-------------|--------|
| [QUICKSTART.md](QUICKSTART.md) | Cài Đặt & first run | Thiết Lập, basic sử dụng |
| [docs/SECURITY_SETUP.md](docs/SECURITY_SETUP.md) | Environment & API keys | Security, credentials |
| [docs/DATABASE_FAQ.md](docs/DATABASE_FAQ.md) | Database sử dụng & FAQ | ChromaDB, knowledge base |
| [docs/CREATE_YOUR_OWN_AI.md](docs/CREATE_YOUR_OWN_AI.md) | Customize personality | Persona, voice, behavior |
| [docs/PERSONALITY_MODES.md](docs/PERSONALITY_MODES.md) | Ambient behaviors & modes | 30 behaviors, 8 modes |

### 🔧 Developer Hướng Dẫns
| Document | Description | Topics |
|----------|-------------|--------|
| [MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md) | Maintenance & updates | Database sync, triển khai |
| [docs/API.md](docs/API.md) | API endpoints | Integration, webhooks |
| [docs/XIAOZHI_INTEGRATION_PLAN.md](docs/XIAOZHI_INTEGRATION_PLAN.md) | **ESP32 Hardware** | XiaoZhi fork, wake word, IoT |

### 📖 Feature Tài Liệu
- **YouTube Integration**: OAuth thiết lập, chat polling, owner detection
- **Telegram Bot**: Commands, voice messages, provider switching
- **Content Creator Mode**: Auto-story generation, idle detection
- **Ambient Behaviors**: Natural actions, personality modes
- **RAG System**: Role-based queries, context retrieval
- **IoT Commands**: Device control via HTTP/Telegram, wake word detection
- **Response Cache**: Pre-recorded audio for instant responses

---

## ⚙️ Cấu Hình

### 🎭 Personality System
**`config/personality.json`** - Core character definition
```json
{
  "name": "MeiLin",
  "age": 19,
  "personality_traits": ["friendly", "energetic", "caring"],
  "speaking_style": "casual with occasional Vietnamese",
  "interests": ["technology", "music", "chatting"]
}
```

**`config/config.yaml`** - Behavioral settings
```yaml
personality:
  viewer_title_default: "Anh"  # Default pronoun
  
stream:
  chat_delay: 3  # Seconds between responses
  
ambient:
  enabled: true
  check_interval: 60  # Seconds
```

### 🤖 AI Providers
**`config/ai_providers.yaml`**
```yaml
active:
  llm: "deepseek"      # Default LLM
  tts: "elevenlabs"    # Default TTS

fallback:
  tts: "edge_tts"      # Free fallback

providers:
  deepseek:
    model: "deepseek-chat"
    temperature: 0.7
  
  elevenlabs:
    voice_id: "d5HVupAWCwe4e6GvMCAL"
```

### 💾 Database
**`config/database.yaml`**
```yaml
mode: "auto"  # auto | local | cloud
local:
  path: "./database/vector_db"
cloud:
  # Set CHROMADB_API_URL in .env
```

### 🔐 Environment Variables
**`.env`** - API keys and secrets (never commit!)
```env
# Required
DEEPSEEK_API_KEY=your_key_here

# Optional LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Optional TTS
ELEVENLABS_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=

# Owner Recognition
OWNER_USER_ID=UCJl9A4BK_KPOe5WqI1zlB_w
OWNER_USERNAME=YourName

# ChromaDB Cloud (optional)
CHROMADB_API_URL=
CHROMADB_API_TOKEN=
```

---

## 🛠️ Sử Dụng Ví Dụ

### 🎥 YouTube Livestream
```bash
# 1. Setup OAuth credentials (youtube_credentials.json)
python youtube_auth.py

# 2. Add video ID to youtube.txt
echo "YOUR_VIDEO_ID" > youtube.txt

# 3. Start livestream
python main.py

# Hotkeys:
# Ctrl+E: Toggle TTS
# Ctrl+M: Switch personality mode
# Ctrl+Shift+M: Show current mode
```

**Tính Năng:**
- Real-time chat processing with RAG context
- Owner detection by user_id
- Persistent viewer profiles
- Auto-story generation when idle (30s)
- Ambient behaviors every 60s

### 💬 Telegram Bot
```bash
# 1. Get bot token from @BotFather
# 2. Add to .env: TELEGRAM_BOT_TOKEN=your_token

# 3. Start bot
python telegram_bot.py

# Available commands:
# /start - Start bot
# /set_llm deepseek - Switch LLM
# /set_tts elevenlabs - Switch TTS
# /tts_on - Enable voice messages
# /tts_off - Disable voice messages
# /info - Show current config
```

**Tính Năng:**
- Full RAG-powered conversations
- Voice message responses
- Real-time provider switching
- User profile persistence

### 🖥️ Standalone Console (No YouTube)
```bash
# Interactive console chat
python meilin_standalone.py

# Demo mode (auto-test features)
python meilin_standalone.py --mode demo

# Text only (no TTS)
python meilin_standalone.py --no-tts

# Available commands in console:
# exit              - Quit
# tts on/off        - Toggle voice
# mode <name>       - Change personality (ENERGETIC, CALM, PLAYFUL, etc.)
# cache <category>  - Test cached response (wake_word, greeting, reaction)
# info              - System information
```

**Tính Năng:**
- ✅ Full IoT command support ("MeiLin, mở máy tính")
- ✅ Cached responses for wake words
- ✅ Ambient behaviors
- ✅ Personality modes
- ✅ No YouTube/OAuth needed
- ✅ Perfect for kiểm thử and phát triển

**Example interaction:**
```
👤 User: MeiLin!
🤖 MeiLin: Em đây! [plays cached audio]

👤 User: MeiLin, mở máy tính
🤖 MeiLin: Đã gửi lệnh mở máy tính cho anh! [executes HTTP/Telegram command]

👤 User: Em tên là gì?
🤖 MeiLin: Em là MeiLin, một AI VTuber 19 tuổi đây ạ! *hehe* 😊
```

### 🔌 API Server (ESP32/IoT)
```bash
python api_server.py
# Access at http://localhost:5000/docs (Swagger UI)

# POST /api/wake
# Body: {"timestamp": "...", "device": "esp32"}
# Response: {"status": "success", "response": "MeiLin đây!", "audio_url": "..."}

# POST /api/command
# Body: {"command": "mở máy tính", "device": "esp32"}
# Response: {"status": "success", "response": "Đã gửi lệnh...", "audio_url": "..."}
```

### 📊 Add Custom Knowledge
```bash
# Upload Excel/CSV knowledge base
python scripts/upload_to_local_chromadb.py my_knowledge.xlsx

# Upload with role metadata
python scripts/upload_to_local_chromadb.py --role friend data.xlsx
```

### 🧪 Test Tính Năng
```bash
# Test personality modes
python test_personality_modes.py

# Test TTS with fallback
python test_tts_fix.py

# Test v3 features
python test_v3_features.py
```

---

## 🔧 System Yêu Cầu

### Minimum Yêu Cầu
- **Python**: 3.13+
- **RAM**: 4GB
- **Storage**: 5GB free disk space
- **Internet**: Required for LLM/TTS API calls

### Required API Keys
- **Deepseek API**: Free tier available at [platform.deepseek.com](https://platform.deepseek.com/)

### Optional API Keys
- **OpenAI**: GPT-4, GPT-3.5 support
- **Anthropic Claude**: Claude 3 models
- **Google Gemini**: Gemini Pro
- **ElevenLabs**: High-quality TTS (paid, free tier available)

### Platform-Specific
- **YouTube**: OAuth 2.0 credentials (for livestream)
- **Telegram**: Bot token from @BotFather
- **ESP32**: WiFi-enabled microcontroller (optional)

---

## 📦 Dự Án Cấu Trúc

```
PROJECT_MEILIN_AIVTUBER/
├── 📁 config/                      # Configuration Files
│   ├── config.yaml                 # Main settings
│   ├── personality.json            # Character definition
│   ├── ai_providers.yaml           # LLM/TTS providers
│   └── database.yaml               # Database settings
│
├── 📁 modules/                     # Core System
│   ├── chat_processor.py           # ⚙️ Message processing & context
│   ├── rag_system.py               # 🔍 Knowledge retrieval (RAG)
│   ├── local_chromadb.py           # 💾 Local vector database
│   ├── provider_manager.py         # 🤖 LLM/TTS management
│   ├── youtube_client.py           # 📺 YouTube integration
│   ├── viewer_profile_db.py        # 👤 User profile storage
│   ├── story_generator.py          # 📖 Content generation
│   ├── ambient_behavior.py         # 🎭 Personality behaviors
│   ├── message_filter.py           # 🔍 Chat filtering
│   └── providers/                  # TTS/LLM providers
│       ├── edge_tts_provider.py
│       ├── elevenlabs_provider.py
│       └── factory.py
│
├── 📁 prompts/                     # Prompt Engineering
│   ├── system_prompts.py           # System instructions
│   ├── persona_templates.py        # Character templates
│   └── response_rules.py           # Response guidelines
│
├── 📁 database/                    # Vector Database
│   ├── vector_db/                  # 💾 Pre-loaded ChromaDB
│   └── viewer_profiles.json        # 👥 User profiles
│
├── 📁 scripts/                     # Utility Scripts
│   ├── upload_to_local_chromadb.py # Add knowledge
│   └── update_local_db.py          # Sync from cloud
│
├── 📁 docs/                        # Documentation
│   ├── PERSONALITY_MODES.md        # Behavior system guide
│   ├── SECURITY_SETUP.md           # Security configuration
│   ├── DATABASE_FAQ.md             # Database usage
│   └── CREATE_YOUR_OWN_AI.md       # Customization guide
│
├── 🐍 main.py                      # YouTube Livestream
├── 🤖 telegram_bot.py              # Telegram Bot
├── 🌐 meilin_api_server.py         # REST API Server
├── 🔐 .env.example                 # Environment template
├── 📋 requirements.txt             # Python dependencies
└── 📖 README.md                    # This file
```

### Key Modules Explained

| Module | Purpose | Key Tính Năng |
|--------|---------|--------------|
| `chat_processor.py` | Core message processing | Context management, history, profiles |
| `rag_system.py` | Knowledge retrieval | Role-based queries, embedding search |
| `ambient_behavior.py` | Personality system | 30 behaviors, 8 modes, context-aware |
| `story_generator.py` | Content creation | Auto-story generation, idle detection |
| `viewer_profile_db.py` | User management | Persistent profiles, owner detection |
| `youtube_client.py` | YouTube integration | Chat polling, OAuth, message parsing |
| `command_executor.py` | IoT control | Device commands, HTTP/Telegram |
| `response_cache.py` | Audio cache | Pre-recorded responses, ChromaDB |

---

## 🎨 Showcase

### What You Can Build

**🎬 Livestream VTuber**
- Autonomous YouTube streaming with natural interactions
- Automatic content generation during idle periods
- Real-time personality adaptation based on chat mood

**💬 Multi-Platform Chatbot**
- Telegram bot with voice messages
- Discord integration (extensible)
- Custom platform via REST API

**🤖 IoT Assistant**
- ESP32-powered physical assistant
- Smart home integration
- Voice-controlled devices

**📚 Knowledge Base Assistant**
- Custom domain expert (upload your own knowledge)
- Role-based responses (friend, tutor, expert)
- Context-aware conversations

---

## 🤝 Đóng Góp

We welcome contributions from the community!

### 🐛 Bug Reports
- Use [GitHub Issues](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER/issues)
- Include Python version, OS, error logs
- Describe steps to reproduce

### 💡 Feature Requests
- Suggest new personality modes
- Propose platform integrations
- Request LLM/TTS provider support

### 🔧 Pull Requests
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### 📝 Tài Liệu
- Improve README or hướng dẫns
- Add sử dụng ví dụ
- Translate tài liệu

### 🎨 Share Your Creation
- Share your customized AI VTuber
- Post your cấu hình
- Write blog posts/hướng dẫns



---

## 🌟 Key Highlights

### What Makes MeiLin Special?

1. **🎭 Living Personality**
   - Not just a chatbot - a character with moods, behaviors, and natural actions
   - Dynamically adapts to stream context and viewer interactions
   - 8 distinct personality modes for different streaming scenarios

2. **🎬 Content Creator, Not Just Reactor**
   - Automatically generates engaging content during idle periods
   - Creates stories, shares fun facts, offers advice
   - Maintains natural flow between viewer interactions and solo content

3. **🧠 Intelligent Context Management**
   - Remembers viewers across sessions (persistent profiles)
   - Never repeats greetings inappropriately
   - Uses RAG for contextually relevant responses
   - Role-based knowledge retrieval

4. **🔌 Multi-Platform Native**
   - YouTube livestream with full OAuth integration
   - Telegram bot with complete feature parity
   - REST API for custom integrations
   - Hardware support (ESP32)

5. **🛡️ Production-Ready**
   - Comprehensive error handling and fallbacks
   - Automatic provider switching on failure
   - Security-first design (environment-based secrets)
   - Modular, extensible kiến trúc

6. **🎮 Interactive & Controllable**
   - Real-time mode switching with hotkeys
   - Command system for on-the-fly adjustments
   - No restart required for config changes

---

## 📄 Giấy Phép

This dự án is giấy phépd under the MIT Giấy Phép - see the [LICENSE](LICENSE) file for details.

**Free to use, modify, and distribute. Commercial use allowed.**

---

## 🙏 Lời Cảm Ơn

### Core Technologies
- [ChromaDB](https://www.trychroma.com/) - Vector database for knowledge storage
- [Sentence-Transformers](https://www.sbert.net/) - Embedding generation
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram integration

### AI Providers
- [Deepseek](https://www.deepseek.com/) - Default LLM provider
- [OpenAI](https://openai.com/) - GPT models support
- [Anthropic](https://www.anthropic.com/) - Claude models support
- [Google AI](https://ai.google.dev/) - Gemini models support

### TTS Providers
- [Edge-TTS](https://github.com/rany2/edge-tts) - Free unlimited TTS
- [ElevenLabs](https://elevenlabs.io/) - High-quality voice synthesis
- [Google Cloud TTS](https://cloud.google.com/text-to-speech) - Neural voices

### Inspiration
Thanks to the VTuber community for inspiration and the open-source community for making dự áns like this possible.

---

## 📞 Support & Community

### 🆘 Need Help?
- 📖 **Tài Liệu**: Check the [docs/](docs/) folder
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER/discussions)
- 📧 **Email**: Create an issue for direct support

### 💡 Common Issues
| Issue | Solution |
|-------|----------|
| ChromaDB connection error | Check CHROMADB_API_URL or use local mode |
| TTS not working | Verify API keys, check fallback cấu hình |
| YouTube OAuth fails | Re-run `youtube_auth.py`, check credentials.json |
| Telegram bot conflict | Kill existing bot instances, check token |

### 🚀 Stay Updated
- ⭐ **Star** this repository to receive updates
- 👁️ **Watch** for new releases and tính năng
- 🍴 **Fork** to customize and contribute

---

## 🎉 Ready to Start?

### Quick Thiết Lập (5 minutes)
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER.git
cd PROJECT_MEILIN_AIVTUBER
pip install -r requirements.txt
cp .env.example .env
# Add DEEPSEEK_API_KEY to .env
python main.py
```

### Next Steps
1. ⭐ **Star this repository** if you find it useful
2. 📖 Read [QUICKSTART.md](QUICKSTART.md) for detailed thiết lập
3. 🎨 Customize personality in `config/personality.json`
4. 🚀 Choose your platform (YouTube/Telegram/API)
5. 🎭 Explore personality modes and ambient behaviors
6. 📚 Add your own knowledge base

### Join the Community
- Share your MeiLin customization
- Contribute new tính năng
- Help others in discussions
- Report bugs and suggest improvements

---

## 🏆 Dự Án Stats

![GitHub stars](https://img.shields.io/github/stars/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER?style=social)
![GitHub forks](https://img.shields.io/github/forks/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER?style=social)

---

<div align="center">

### 🎭 Build Your Own AI VTuber Today!

**[⭐ Star](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER)** • **[🍴 Fork](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER/fork)** • **[📖 Tài Liệu](docs/)** • **[🐛 Issues](https://github.com/YOUR_GITHUB_USERNAME/PROJECT_MEILIN_AIVTUBER/issues)**

---

Made with ❤️ by [Truong Cong Dinh](https://github.com/YOUR_GITHUB_USERNAME)

**MIT Giấy Phép** • **Free to use** • **Open Source**

</div>
