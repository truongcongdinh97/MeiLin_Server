#!/usr/bin/env python3
"""
Interactive Configuration Bot for MeiLin
With step-by-step guided setup using Telegram User ID for identification
"""

import os
import io
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any, List
from pathlib import Path
from enum import Enum, auto

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    ConversationHandler,
    filters
)

# Import managers
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.multi_user.user_manager import get_user_manager
from modules.multi_user.api_key_manager import get_api_key_manager
from modules.personal_knowledge_manager import get_knowledge_manager
from modules.esp_device_manager import get_esp_device_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# CONVERSATION STATES
# ============================================================
class State(Enum):
    """Conversation states for the wizard"""
    MAIN_MENU = auto()
    
    # API Configuration
    API_MENU = auto()
    API_SELECT_TYPE = auto()      # LLM or TTS
    API_SELECT_PROVIDER = auto()  # Which provider
    API_ENTER_KEY = auto()        # Enter API key
    API_ENTER_BASE = auto()       # Enter base URL (optional)
    API_ENTER_MODEL = auto()      # Enter model name (optional)
    API_CONFIRM = auto()          # Confirm settings
    
    # Personality Configuration
    PERSONALITY_MENU = auto()
    PERSONALITY_NAME = auto()
    PERSONALITY_WAKE_WORD = auto()
    PERSONALITY_SPEAKING_STYLE = auto()
    PERSONALITY_LANGUAGE = auto()
    PERSONALITY_CONFIRM = auto()
    
    # View/Manage
    VIEW_CONFIG = auto()
    DELETE_CONFIG = auto()
    
    # Knowledge Base
    KNOWLEDGE_MENU = auto()
    KNOWLEDGE_UPLOAD = auto()
    KNOWLEDGE_CONFIRM_DELETE = auto()
    
    # ESP Device Management (NEW)
    ESP_MENU = auto()
    ESP_REGISTER_ID = auto()
    ESP_REGISTER_NAME = auto()
    ESP_VIEW_DEVICES = auto()
    ESP_SELECT_DEVICE = auto()
    ESP_DEVICE_ACTIONS = auto()
    ESP_CONFIRM_DELETE = auto()


# ============================================================
# PROVIDER CONFIGURATIONS
# ============================================================
LLM_PROVIDERS = {
    'deepseek': {
        'name': 'DeepSeek',
        'emoji': '🧠',
        'description': 'AI mạnh mẽ với giá rẻ, hỗ trợ tiếng Việt tốt',
        'api_base': 'https://api.deepseek.com',
        'default_model': 'deepseek-chat',
        'key_format': r'^sk-[a-zA-Z0-9]{32,}$',
        'key_hint': 'Bắt đầu bằng "sk-" theo sau là 32+ ký tự'
    },
    'openai': {
        'name': 'OpenAI (GPT)',
        'emoji': '🤖',
        'description': 'ChatGPT - AI phổ biến nhất thế giới',
        'api_base': 'https://api.openai.com/v1',
        'default_model': 'gpt-4o-mini',
        'key_format': r'^sk-[a-zA-Z0-9]{48,}$',
        'key_hint': 'Bắt đầu bằng "sk-" theo sau là 48+ ký tự'
    },
    'anthropic': {
        'name': 'Anthropic (Claude)',
        'emoji': '🎭',
        'description': 'Claude - AI an toàn và thông minh',
        'api_base': 'https://api.anthropic.com',
        'default_model': 'claude-3-5-sonnet-20241022',
        'key_format': r'^sk-ant-[a-zA-Z0-9-]{90,}$',
        'key_hint': 'Bắt đầu bằng "sk-ant-"'
    },
    'google': {
        'name': 'Google (Gemini)',
        'emoji': '✨',
        'description': 'Gemini - AI đa phương thức từ Google',
        'api_base': 'https://generativelanguage.googleapis.com',
        'default_model': 'gemini-pro',
        'key_format': r'^AIza[a-zA-Z0-9-_]{35}$',
        'key_hint': 'Bắt đầu bằng "AIza"'
    },
    'ollama': {
        'name': 'Ollama (Local)',
        'emoji': '🏠',
        'description': 'Chạy AI local trên máy của bạn',
        'api_base': 'http://localhost:11434',
        'default_model': 'llama3.2',
        'key_format': None,  # No API key needed
        'key_hint': 'Không cần API key'
    }
}

TTS_PROVIDERS = {
    'edge_tts': {
        'name': 'Edge TTS (Free)',
        'emoji': '🆓',
        'description': 'Giọng nói miễn phí từ Microsoft Edge',
        'requires_key': False,
        'voices': ['vi-VN-HoaiMyNeural', 'vi-VN-NamMinhNeural']
    },
    'elevenlabs': {
        'name': 'ElevenLabs',
        'emoji': '🎵',
        'description': 'Giọng nói AI chất lượng cao',
        'requires_key': True,
        'key_hint': 'API key từ elevenlabs.io'
    },
    'google_tts': {
        'name': 'Google Cloud TTS',
        'emoji': '☁️',
        'description': 'Google Cloud Text-to-Speech',
        'requires_key': True,
        'key_hint': 'Google Cloud API key'
    },
    'azure_tts': {
        'name': 'Azure TTS',
        'emoji': '🔷',
        'description': 'Microsoft Azure Speech Services',
        'requires_key': True,
        'key_hint': 'Azure Speech API key'
    }
}

SPEAKING_STYLES = {
    'friendly': {'name': 'Thân thiện', 'emoji': '😊', 'desc': 'Nói chuyện như bạn bè'},
    'professional': {'name': 'Chuyên nghiệp', 'emoji': '👔', 'desc': 'Nghiêm túc, lịch sự'},
    'cute': {'name': 'Dễ thương', 'emoji': '🥰', 'desc': 'Ngọt ngào, đáng yêu'},
    'playful': {'name': 'Vui vẻ', 'emoji': '🎉', 'desc': 'Hài hước, năng động'},
    'formal': {'name': 'Trang trọng', 'emoji': '📜', 'desc': 'Trang trọng, kính cẩn'}
}

LANGUAGES = {
    'vi': {'name': 'Tiếng Việt', 'emoji': '🇻🇳'},
    'en': {'name': 'English', 'emoji': '🇺🇸'},
    'ja': {'name': '日本語', 'emoji': '🇯🇵'},
    'zh': {'name': '中文', 'emoji': '🇨🇳'},
    'ko': {'name': '한국어', 'emoji': '🇰🇷'}
}


# ============================================================
# MAIN BOT CLASS
# ============================================================
class InteractiveConfigBot:
    """
    Interactive configuration bot using Telegram User ID for identification.
    
    IMPORTANT: Server identifies users via their Telegram User ID (update.effective_user.id)
    This is unique per Telegram account and persists across sessions.
    """
    
    def __init__(self, token: str):
        self.token = token
        self.user_manager = get_user_manager()
        self.api_key_manager = get_api_key_manager()
        self.knowledge_manager = get_knowledge_manager()
        self.esp_device_manager = get_esp_device_manager()
        
        # Session data (temporary, in-memory)
        # Key: telegram_user_id (int), Value: session dict
        self.sessions: Dict[int, Dict[str, Any]] = {}
    
    # ============================================================
    # SESSION MANAGEMENT
    # ============================================================
    def get_session(self, telegram_user_id: int) -> Dict[str, Any]:
        """
        Get or create session for a Telegram user.
        
        Args:
            telegram_user_id: Telegram's unique user ID (update.effective_user.id)
        
        Returns:
            Session dictionary
        """
        if telegram_user_id not in self.sessions:
            self.sessions[telegram_user_id] = {
                'db_user_id': None,  # Internal database user ID
                'current_config': {},  # Temp config being built
                'last_activity': datetime.now()
            }
        else:
            self.sessions[telegram_user_id]['last_activity'] = datetime.now()
        
        return self.sessions[telegram_user_id]
    
    def clear_session_config(self, telegram_user_id: int):
        """Clear temporary config data but keep session"""
        if telegram_user_id in self.sessions:
            self.sessions[telegram_user_id]['current_config'] = {}
    
    def get_or_create_db_user(self, update: Update) -> Optional[int]:
        """
        Get or create database user from Telegram update.
        Uses Telegram User ID as the unique identifier.
        
        Returns:
            Internal database user ID
        """
        tg_user = update.effective_user
        session = self.get_session(tg_user.id)
        
        # Check if we already have DB user ID cached
        if session['db_user_id']:
            return session['db_user_id']
        
        # Create or get user in database
        # IMPORTANT: telegram_id is stored as string for consistency
        db_user_id = self.user_manager.create_user(
            telegram_id=str(tg_user.id),  # Telegram User ID as string
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code
        )
        
        if db_user_id:
            session['db_user_id'] = db_user_id
        
        return db_user_id
    
    # ============================================================
    # MESSAGE BUILDERS
    # ============================================================
    def build_progress_bar(self, current: int, total: int, filled: str = '🟢', empty: str = '⚪') -> str:
        """Build a visual progress bar"""
        return filled * current + empty * (total - current)
    
    def build_step_indicator(self, current: int, total: int, step_name: str) -> str:
        """Build step indicator with progress"""
        progress = self.build_progress_bar(current, total)
        return f"📍 Bước {current}/{total}: {step_name}\n{progress}"
    
    # ============================================================
    # /START COMMAND
    # ============================================================
    async def cmd_start(self, update: Update, context: CallbackContext) -> int:
        """
        Handle /start command.
        Creates user in database using Telegram User ID.
        """
        tg_user = update.effective_user
        logger.info(f"User started bot: telegram_id={tg_user.id}, username={tg_user.username}")
        
        # Get or create database user
        db_user_id = self.get_or_create_db_user(update)
        
        if not db_user_id:
            await update.message.reply_text(
                "❌ Có lỗi xảy ra khi khởi tạo tài khoản.\n"
                "Vui lòng thử lại sau: /start"
            )
            return ConversationHandler.END
        
        # Store in context for easy access
        context.user_data['db_user_id'] = db_user_id
        context.user_data['telegram_id'] = tg_user.id
        
        # Get user's current config status
        summary = self.user_manager.get_user_config_summary(db_user_id)
        
        # Build welcome message
        welcome_msg = self._build_welcome_message(tg_user, summary)
        keyboard = self._build_main_menu_keyboard(summary)
        
        await update.message.reply_text(
            welcome_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    def _build_welcome_message(self, tg_user, summary: Dict) -> str:
        """Build personalized welcome message"""
        name = tg_user.first_name or tg_user.username or "bạn"
        
        # Check config status
        has_llm = any(c.get('provider_type') == 'llm' for c in summary.get('api_configs', []))
        has_tts = any(c.get('provider_type') == 'tts' for c in summary.get('api_configs', []))
        has_personality = bool(summary.get('personality_config'))
        
        # Check knowledge base
        knowledge_summary = self.knowledge_manager.get_knowledge_summary(str(tg_user.id))
        has_knowledge = knowledge_summary.get('has_knowledge', False)
        
        # Get provider names if configured
        llm_provider_name = self._get_provider_name(summary, 'llm')
        tts_provider_name = self._get_provider_name(summary, 'tts')
        
        msg = f"""
🌸 **Xin chào {name}!**

Tôi là **MeiLin** - trợ lý AI cá nhân của bạn.

📊 **Cấu hình hiện tại:**
├─ 🤖 LLM: {"✅ " + llm_provider_name if has_llm else "🆓 XiaoZhi (miễn phí)"}
├─ 🎙️ TTS: {"✅ " + tts_provider_name if has_tts else "🆓 XiaoZhi (miễn phí)"}
├─ 😊 Personality: {"✅ Tùy chỉnh" if has_personality else "📌 Mặc định"}
└─ 📚 Knowledge: {"✅ " + str(knowledge_summary.get('items_count', 0)) + " mục" if has_knowledge else "📌 Chưa có"}

🔑 **ID của bạn:** `{tg_user.id}`

💡 **Mặc định:** ESP dùng XiaoZhi Cloud *miễn phí*.
Bạn có thể đổi sang LLM/TTS khác nếu muốn chất lượng tốt hơn.
"""
        return msg
    
    def _get_provider_name(self, summary: Dict, provider_type: str) -> str:
        """Get provider name from config"""
        for c in summary.get('api_configs', []):
            if c.get('provider_type') == provider_type:
                provider = c.get('provider', 'unknown')
                if provider_type == 'llm':
                    return LLM_PROVIDERS.get(provider, {}).get('name', provider.title())
                else:
                    return TTS_PROVIDERS.get(provider, {}).get('name', provider.title())
        return "Chưa cấu hình"
    
    def _build_main_menu_keyboard(self, summary: Dict) -> List[List[InlineKeyboardButton]]:
        """Build main menu keyboard based on user's config status"""
        
        keyboard = []
        
        # ESP Devices - Hành động chính
        keyboard.append([
            InlineKeyboardButton("📱 Đăng ký ESP Device", callback_data='menu_esp')
        ])
        
        # Optional: Đổi LLM/TTS (tùy chọn, không bắt buộc)
        keyboard.append([
            InlineKeyboardButton("🔄 Đổi LLM/TTS (tùy chọn)", callback_data='wizard_start')
        ])
        
        # Knowledge Base & Personality
        keyboard.append([
            InlineKeyboardButton("📚 Knowledge Base", callback_data='menu_knowledge'),
            InlineKeyboardButton("😊 Personality", callback_data='menu_personality')
        ])
        
        # View/Manage
        keyboard.append([
            InlineKeyboardButton("📊 Xem cấu hình", callback_data='view_config'),
            InlineKeyboardButton("❓ Hướng dẫn", callback_data='help')
        ])
        
        return keyboard
    
    # ============================================================
    # SETUP WIZARD (OPTIONAL - Default is XiaoZhi free)
    # ============================================================
    async def wizard_start(self, update: Update, context: CallbackContext) -> int:
        """Start the setup wizard - OPTIONAL: Change LLM/TTS provider"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        self.clear_session_config(tg_user_id)
        
        msg = """
🔄 **Đổi nhà cung cấp LLM/TTS (Tùy chọn)**

⚠️ **Lưu ý:** Mặc định ESP đã dùng **XiaoZhi Cloud miễn phí**.
Bạn chỉ cần đổi nếu muốn chất lượng tốt hơn.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 **Chọn nhà cung cấp AI (LLM):**

"""
        # Add provider descriptions
        keyboard = []
        for key, provider in LLM_PROVIDERS.items():
            msg += f"{provider['emoji']} **{provider['name']}**\n"
            msg += f"   _{provider['description']}_\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{provider['emoji']} {provider['name']}",
                    callback_data=f'select_llm_{key}'
                )
            ])
        
        # Add option to keep XiaoZhi (skip)
        keyboard.append([
            InlineKeyboardButton("🆓 Giữ XiaoZhi miễn phí", callback_data='back_main')
        ])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.API_SELECT_PROVIDER.value
    
    async def wizard_select_llm(self, update: Update, context: CallbackContext) -> int:
        """Handle LLM provider selection"""
        query = update.callback_query
        await query.answer()
        
        # Extract provider from callback
        provider_key = query.data.replace('select_llm_', '')
        provider = LLM_PROVIDERS.get(provider_key)
        
        if not provider:
            await query.answer("❌ Provider không hợp lệ", show_alert=True)
            return State.API_SELECT_PROVIDER.value
        
        # Store in session
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        session['current_config'] = {
            'provider_type': 'llm',
            'provider_key': provider_key,
            'provider_name': provider['name']
        }
        
        step_indicator = self.build_step_indicator(2, 4, "Nhập API Key")
        
        # Special case for Ollama (no API key needed)
        if provider_key == 'ollama':
            msg = f"""
{step_indicator}

🏠 **Ollama - Chạy AI Local**

Ollama không cần API key! Bạn chỉ cần:

1️⃣ Cài đặt Ollama từ https://ollama.ai
2️⃣ Chạy lệnh: `ollama run llama3.2`
3️⃣ Đảm bảo Ollama đang chạy trên máy

📍 **Nhập địa chỉ Ollama server:**
_(Mặc định: http://localhost:11434)_

Gửi địa chỉ hoặc gõ `skip` để dùng mặc định:
"""
            await query.edit_message_text(msg, parse_mode='Markdown')
            session['current_config']['skip_api_key'] = True
            return State.API_ENTER_BASE.value
        
        # Normal provider - need API key
        msg = f"""
{step_indicator}

🔑 **Nhập API Key cho {provider['name']}**

{provider['emoji']} Bạn cần lấy API key từ trang web của {provider['name']}.

📝 **Định dạng:** {provider.get('key_hint', 'Theo hướng dẫn của provider')}

⚠️ **Lưu ý bảo mật:**
• API key sẽ được **mã hóa** trước khi lưu
• Không chia sẻ key với người khác
• Bạn có thể xóa key bất cứ lúc nào

📨 **Gửi API key của bạn:**
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='wizard_start')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.API_ENTER_KEY.value
    
    async def wizard_enter_api_key(self, update: Update, context: CallbackContext) -> int:
        """Handle API key input"""
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        config = session['current_config']
        
        api_key = update.message.text.strip()
        provider_key = config['provider_key']
        provider = LLM_PROVIDERS.get(provider_key)
        
        # Delete user's message containing API key for security
        try:
            await update.message.delete()
        except:
            pass
        
        # Validate format (basic check)
        import re
        if provider.get('key_format'):
            if not re.match(provider['key_format'], api_key):
                await update.message.reply_text(
                    f"❌ **API Key không đúng định dạng!**\n\n"
                    f"Định dạng đúng: {provider.get('key_hint', 'Kiểm tra lại key')}\n\n"
                    f"Vui lòng gửi lại API key:",
                    parse_mode='Markdown'
                )
                return State.API_ENTER_KEY.value
        
        # Encrypt and store temporarily
        encrypted_key = self.api_key_manager.encrypt_api_key(provider_key, api_key)
        config['api_key'] = encrypted_key
        config['api_key_masked'] = self.api_key_manager.mask_api_key(api_key)
        
        step_indicator = self.build_step_indicator(3, 4, "Cấu hình nâng cao")
        
        msg = f"""
{step_indicator}

✅ **API Key đã được mã hóa!**
🔐 Key: `{config['api_key_masked']}`

⚙️ **Cấu hình nâng cao (tùy chọn):**

📍 **API Base URL:**
Mặc định: `{provider.get('api_base', 'Không có')}`

Gửi URL tùy chỉnh hoặc `skip` để dùng mặc định:
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return State.API_ENTER_BASE.value
    
    async def wizard_enter_base(self, update: Update, context: CallbackContext) -> int:
        """Handle API base URL input"""
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        config = session['current_config']
        
        text = update.message.text.strip()
        provider_key = config['provider_key']
        provider = LLM_PROVIDERS.get(provider_key)
        
        if text.lower() == 'skip' or not text:
            config['api_base'] = provider.get('api_base', '')
        else:
            config['api_base'] = text
        
        msg = f"""
🧠 **Chọn Model:**
Mặc định: `{provider.get('default_model', 'Không có')}`

Gửi tên model hoặc `skip` để dùng mặc định:
"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return State.API_ENTER_MODEL.value
    
    async def wizard_enter_model(self, update: Update, context: CallbackContext) -> int:
        """Handle model selection"""
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        config = session['current_config']
        
        text = update.message.text.strip()
        provider_key = config['provider_key']
        provider = LLM_PROVIDERS.get(provider_key)
        
        if text.lower() == 'skip' or not text:
            config['model'] = provider.get('default_model', '')
        else:
            config['model'] = text
        
        # Show confirmation
        step_indicator = self.build_step_indicator(4, 4, "Xác nhận cấu hình")
        
        msg = f"""
{step_indicator}

📋 **Xác nhận cấu hình LLM:**

{provider['emoji']} **Provider:** {config['provider_name']}
🔑 **API Key:** `{config.get('api_key_masked', '(không cần)')}`
🌐 **API Base:** `{config.get('api_base', 'Mặc định')}`
🧠 **Model:** `{config.get('model', 'Mặc định')}`

Bạn có muốn lưu cấu hình này không?
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Lưu cấu hình", callback_data='save_config'),
                InlineKeyboardButton("❌ Hủy", callback_data='cancel_config')
            ],
            [InlineKeyboardButton("🔙 Cấu hình lại", callback_data='wizard_start')]
        ]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.API_CONFIRM.value
    
    async def save_config(self, update: Update, context: CallbackContext) -> int:
        """Save the configuration to database"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        config = session['current_config']
        db_user_id = context.user_data.get('db_user_id') or session.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        # Save to database
        success = self.user_manager.save_api_config(
            user_id=db_user_id,
            provider_type=config['provider_type'],
            provider_name=config['provider_key'],
            api_key=config.get('api_key', ''),
            api_base=config.get('api_base', ''),
            model_name=config.get('model', ''),
            is_default=True
        )
        
        if success:
            # Clear temp config
            self.clear_session_config(tg_user_id)
            
            msg = f"""
🎉 **Cấu hình đã được lưu thành công!**

✅ {config['provider_name']} đã được thiết lập.

**Tiếp theo, bạn muốn làm gì?**
"""
            keyboard = [
                [InlineKeyboardButton("😊 Cấu hình Personality", callback_data='menu_personality')],
                [InlineKeyboardButton("🎙️ Thêm TTS (giọng nói)", callback_data='menu_tts')],
                [InlineKeyboardButton("💬 Bắt đầu chat ngay!", callback_data='start_chat')],
                [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
            ]
        else:
            msg = "❌ **Có lỗi xảy ra khi lưu cấu hình.**\n\nVui lòng thử lại."
            keyboard = [[InlineKeyboardButton("🔄 Thử lại", callback_data='wizard_start')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    # ============================================================
    # PERSONALITY CONFIGURATION
    # ============================================================
    async def menu_personality(self, update: Update, context: CallbackContext) -> int:
        """Show personality configuration menu"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        self.clear_session_config(tg_user_id)
        
        msg = """
😊 **Cấu hình Personality**

Tùy chỉnh tính cách và phong cách của MeiLin!

🏷️ **Tên nhân vật:** Đặt tên riêng cho AI của bạn
🎤 **Wake Word:** Từ khóa để gọi AI
💬 **Phong cách nói:** Cách AI giao tiếp với bạn
🌏 **Ngôn ngữ:** Ngôn ngữ chính

Chọn mục bạn muốn cấu hình:
"""
        
        keyboard = [
            [InlineKeyboardButton("🏷️ Đặt tên nhân vật", callback_data='personality_name')],
            [InlineKeyboardButton("🎤 Thiết lập Wake Word", callback_data='personality_wake')],
            [InlineKeyboardButton("💬 Chọn phong cách nói", callback_data='personality_style')],
            [InlineKeyboardButton("🌏 Chọn ngôn ngữ", callback_data='personality_lang')],
            [InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_MENU.value
    
    async def personality_name(self, update: Update, context: CallbackContext) -> int:
        """Handle personality name setting"""
        query = update.callback_query
        await query.answer()
        
        msg = """
🏷️ **Đặt tên cho AI của bạn**

Tên này sẽ được AI sử dụng khi tự giới thiệu.

📝 **Ví dụ:**
• MeiLin
• Luna
• Aria
• Sakura
• My Assistant

📨 **Gửi tên bạn muốn đặt:**
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='menu_personality')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_NAME.value
    
    async def save_personality_name(self, update: Update, context: CallbackContext) -> int:
        """Save personality name"""
        name = update.message.text.strip()
        
        if len(name) < 2 or len(name) > 30:
            await update.message.reply_text(
                "❌ Tên phải từ 2-30 ký tự. Vui lòng thử lại:"
            )
            return State.PERSONALITY_NAME.value
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        # Save to database
        success = self.user_manager.update_personality_config(
            user_id=db_user_id,
            character_name=name
        )
        
        if success:
            msg = f"""
✅ **Đã đặt tên thành công!**

Từ giờ, AI của bạn sẽ tự giới thiệu là **{name}**.

Bạn muốn tiếp tục cấu hình gì?
"""
        else:
            msg = "❌ Có lỗi xảy ra. Vui lòng thử lại."
        
        keyboard = [
            [InlineKeyboardButton("🎤 Thiết lập Wake Word", callback_data='personality_wake')],
            [InlineKeyboardButton("💬 Chọn phong cách nói", callback_data='personality_style')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
        ]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_MENU.value
    
    async def personality_wake_word(self, update: Update, context: CallbackContext) -> int:
        """Handle wake word setting"""
        query = update.callback_query
        await query.answer()
        
        msg = """
🎤 **Thiết lập Wake Word**

Wake word là từ khóa để "đánh thức" AI trong chat.
Khi bạn nhắn tin có chứa wake word, AI sẽ biết bạn đang gọi.

📝 **Ví dụ:**
• Hi MeiLin
• Hey Luna
• Này bạn ơi
• Xin chào

⚠️ **Lưu ý:**
• Wake word chỉ hoạt động trong chat text
• Wake word trên ESP32 được cấu hình riêng trong firmware

📨 **Gửi wake word bạn muốn sử dụng:**
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='menu_personality')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_WAKE_WORD.value
    
    async def save_wake_word(self, update: Update, context: CallbackContext) -> int:
        """Save wake word"""
        wake_word = update.message.text.strip().lower()
        
        if len(wake_word) < 2 or len(wake_word) > 50:
            await update.message.reply_text(
                "❌ Wake word phải từ 2-50 ký tự. Vui lòng thử lại:"
            )
            return State.PERSONALITY_WAKE_WORD.value
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        # Save to database
        success = self.user_manager.update_personality_config(
            user_id=db_user_id,
            wake_word=wake_word
        )
        
        if success:
            msg = f"""
✅ **Đã thiết lập Wake Word!**

Wake word của bạn: **"{wake_word}"**

Từ giờ, khi bạn nhắn tin có chứa "{wake_word}", AI sẽ biết bạn đang gọi.

Bạn muốn tiếp tục cấu hình gì?
"""
        else:
            msg = "❌ Có lỗi xảy ra. Vui lòng thử lại."
        
        keyboard = [
            [InlineKeyboardButton("💬 Chọn phong cách nói", callback_data='personality_style')],
            [InlineKeyboardButton("🌏 Chọn ngôn ngữ", callback_data='personality_lang')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
        ]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_MENU.value
    
    async def personality_style(self, update: Update, context: CallbackContext) -> int:
        """Show speaking style options"""
        query = update.callback_query
        await query.answer()
        
        msg = """
💬 **Chọn phong cách nói**

Phong cách này sẽ ảnh hưởng đến cách AI giao tiếp với bạn:

"""
        
        keyboard = []
        for key, style in SPEAKING_STYLES.items():
            msg += f"{style['emoji']} **{style['name']}** - _{style['desc']}_\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{style['emoji']} {style['name']}",
                    callback_data=f'style_{key}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='menu_personality')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_SPEAKING_STYLE.value
    
    async def save_speaking_style(self, update: Update, context: CallbackContext) -> int:
        """Save speaking style"""
        query = update.callback_query
        await query.answer()
        
        style_key = query.data.replace('style_', '')
        style = SPEAKING_STYLES.get(style_key)
        
        if not style:
            await query.answer("❌ Phong cách không hợp lệ", show_alert=True)
            return State.PERSONALITY_SPEAKING_STYLE.value
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        # Save to database
        success = self.user_manager.update_personality_config(
            user_id=db_user_id,
            speaking_style=style_key
        )
        
        if success:
            msg = f"""
✅ **Đã thiết lập phong cách nói!**

{style['emoji']} Phong cách: **{style['name']}**
_{style['desc']}_

Bạn muốn tiếp tục cấu hình gì?
"""
        else:
            msg = "❌ Có lỗi xảy ra. Vui lòng thử lại."
        
        keyboard = [
            [InlineKeyboardButton("🌏 Chọn ngôn ngữ", callback_data='personality_lang')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_MENU.value
    
    async def personality_language(self, update: Update, context: CallbackContext) -> int:
        """Show language options"""
        query = update.callback_query
        await query.answer()
        
        msg = "🌏 **Chọn ngôn ngữ chính:**\n\n"
        
        keyboard = []
        for key, lang in LANGUAGES.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{lang['emoji']} {lang['name']}",
                    callback_data=f'lang_{key}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='menu_personality')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.PERSONALITY_LANGUAGE.value
    
    async def save_language(self, update: Update, context: CallbackContext) -> int:
        """Save language preference"""
        query = update.callback_query
        await query.answer()
        
        lang_key = query.data.replace('lang_', '')
        lang = LANGUAGES.get(lang_key)
        
        if not lang:
            await query.answer("❌ Ngôn ngữ không hợp lệ", show_alert=True)
            return State.PERSONALITY_LANGUAGE.value
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        # Save to database
        success = self.user_manager.update_personality_config(
            user_id=db_user_id,
            primary_language=lang_key
        )
        
        if success:
            msg = f"""
✅ **Đã thiết lập ngôn ngữ!**

{lang['emoji']} Ngôn ngữ: **{lang['name']}**

🎉 **Cấu hình Personality hoàn tất!**

Bạn muốn làm gì tiếp theo?
"""
        else:
            msg = "❌ Có lỗi xảy ra. Vui lòng thử lại."
        
        keyboard = [
            [InlineKeyboardButton("💬 Bắt đầu chat", callback_data='start_chat')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    # ============================================================
    # KNOWLEDGE BASE
    # ============================================================
    async def menu_knowledge(self, update: Update, context: CallbackContext) -> int:
        """Show knowledge base menu"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        summary = self.knowledge_manager.get_knowledge_summary(str(tg_user_id))
        quota_summary = self.knowledge_manager.get_quota_summary(str(tg_user_id))
        
        if summary.get('has_knowledge'):
            status = f"""
📚 **Knowledge Base của bạn:**

✅ **Đã có dữ liệu:**
├─ 📄 Số mục: {summary.get('items_count', 0)}
├─ 📁 Danh mục: {', '.join(summary.get('categories', [])[:3])}
└─ 🕐 Cập nhật: {summary.get('last_updated', 'N/A')}

{quota_summary}
"""
        else:
            status = f"""
📚 **Knowledge Base**

❌ **Chưa có dữ liệu**

Knowledge Base là "bộ nhớ" cá nhân của AI.
Bạn có thể thêm thông tin về bản thân để AI hiểu bạn hơn.

{quota_summary}
"""
        
        msg = status + """
**Bạn muốn làm gì?**
"""
        
        keyboard = [
            [InlineKeyboardButton("📥 Tải template mẫu", callback_data='kb_download_template')],
        ]
        
        if summary.get('has_knowledge'):
            keyboard.append([InlineKeyboardButton("📤 Tải file hiện tại", callback_data='kb_download_current')])
        
        keyboard.append([InlineKeyboardButton("📤 Upload file Knowledge", callback_data='kb_upload')])
        
        if summary.get('has_knowledge'):
            keyboard.append([
                InlineKeyboardButton("🧹 Dọn dẹp dữ liệu cũ", callback_data='kb_cleanup'),
                InlineKeyboardButton("🗑️ Xóa tất cả", callback_data='kb_delete')
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.KNOWLEDGE_MENU.value
    
    async def kb_download_template(self, update: Update, context: CallbackContext) -> int:
        """Send knowledge base template to user"""
        query = update.callback_query
        await query.answer("📥 Đang tạo template...")
        
        try:
            # Generate template
            buffer = self.knowledge_manager.generate_template(include_samples=True)
            
            # Send file (no parse_mode to avoid Markdown issues)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename="MeiLin_Knowledge_Template.xlsx",
                caption="📚 Template Knowledge Base\n\n"
                        "Hướng dẫn sử dụng:\n"
                        "1. Mở file Excel\n"
                        "2. Xóa các dòng mẫu\n"
                        "3. Điền thông tin của bạn vào cột DOCUMENT_TEXT\n"
                        "4. Lưu file\n"
                        "5. Gửi file lại cho tôi\n\n"
                        "💡 Xem sheet 'Hướng dẫn' trong file để biết thêm chi tiết!"
            )
            
            # Show upload instruction
            keyboard = [
                [InlineKeyboardButton("📤 Upload file đã điền", callback_data='kb_upload')],
                [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
            ]
            
            await query.edit_message_text(
                "✅ **Template đã được gửi!**\n\n"
                "Sau khi điền xong, hãy upload file lại cho tôi.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending template: {e}")
            await query.edit_message_text(
                f"❌ Lỗi: {str(e)}\n\nVui lòng thử lại.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ])
            )
        
        return State.KNOWLEDGE_MENU.value
    
    async def kb_download_current(self, update: Update, context: CallbackContext) -> int:
        """Send user's current knowledge file"""
        query = update.callback_query
        await query.answer("📥 Đang tải file...")
        
        tg_user_id = update.effective_user.id
        
        try:
            buffer = self.knowledge_manager.get_user_knowledge_file(str(tg_user_id))
            
            if buffer:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=buffer,
                    filename=f"MeiLin_Knowledge_{tg_user_id}.xlsx",
                    caption="📚 **Knowledge Base hiện tại của bạn**\n\nBạn có thể chỉnh sửa và upload lại.",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Không tìm thấy file", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error downloading knowledge: {e}")
            await query.answer(f"❌ Lỗi: {str(e)}", show_alert=True)
        
        return State.KNOWLEDGE_MENU.value
    
    async def kb_upload_prompt(self, update: Update, context: CallbackContext) -> int:
        """Prompt user to upload knowledge file"""
        query = update.callback_query
        await query.answer()
        
        msg = """
📤 **Upload Knowledge Base**

Gửi file Excel (.xlsx) chứa thông tin bạn muốn AI nhớ.

📋 **Yêu cầu:**
• File phải có sheet "Knowledge Base"
• Các cột: ID, CATEGORY, PRIORITY, DOCUMENT_TEXT, TAGS
• Định dạng .xlsx

💡 Nếu chưa có file, hãy tải template mẫu trước!

**Gửi file Excel của bạn:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📥 Tải template", callback_data='kb_download_template')],
            [InlineKeyboardButton("🔙 Hủy", callback_data='menu_knowledge')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.KNOWLEDGE_UPLOAD.value
    
    async def kb_handle_upload_anytime(self, update: Update, context: CallbackContext) -> int:
        """Handle Excel file sent anytime (not just in upload state)"""
        doc = update.message.document if update.message else None
        
        if not doc:
            return State.MAIN_MENU.value
        
        file_name = doc.file_name or ""
        mime_type = doc.mime_type or ""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ""
        
        # Check file type
        is_excel = (
            ext in ['xlsx', 'xls'] or
            'spreadsheet' in mime_type.lower() or
            'excel' in mime_type.lower()
        )
        
        is_pdf = ext == 'pdf' or 'pdf' in mime_type.lower()
        is_docx = ext == 'docx' or 'word' in mime_type.lower()
        is_text = ext in ['txt', 'md', 'csv'] or 'text/plain' in mime_type.lower()
        
        if is_excel:
            await update.message.reply_text(
                "📚 Phát hiện file Excel!\n⏳ Đang xử lý như Knowledge Base..."
            )
            return await self.kb_handle_upload(update, context)
        elif is_pdf or is_docx or is_text:
            format_name = "PDF" if is_pdf else ("Word" if is_docx else "Text")
            await update.message.reply_text(
                f"📄 Phát hiện file {format_name}!\n⏳ Đang parse và lưu vào Knowledge Base..."
            )
            return await self.kb_handle_document_upload(update, context)
        else:
            await update.message.reply_text(
                f"📎 Đã nhận file: {file_name}\n\n"
                "💡 **Formats hỗ trợ:**\n"
                "• Excel (.xlsx, .xls) - Template Knowledge Base\n"
                "• PDF (.pdf) - Tài liệu PDF\n"
                "• Word (.docx) - Tài liệu Word\n"
                "• Text (.txt, .md) - File text\n\n"
                "Vào 📚 Knowledge Base để upload",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Knowledge Base", callback_data='menu_knowledge')],
                    [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
                ]),
                parse_mode='Markdown'
            )
            return State.MAIN_MENU.value
    
    async def kb_handle_document_upload(self, update: Update, context: CallbackContext) -> int:
        """Handle PDF, DOCX, TXT uploads"""
        doc = update.message.document if update.message else None
        
        if not doc:
            await update.message.reply_text("❌ Không tìm thấy file.")
            return State.MAIN_MENU.value
        
        file_name = doc.file_name or "document"
        
        # Check file size (max 10MB for documents)
        if doc.file_size > 10 * 1024 * 1024:
            await update.message.reply_text(
                "❌ File quá lớn (tối đa 10MB)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ])
            )
            return State.MAIN_MENU.value
        
        await update.message.reply_text("⏳ Đang xử lý file...")
        
        try:
            # Download file
            file = await context.bot.get_file(doc.file_id)
            buffer = io.BytesIO()
            await file.download_to_memory(buffer)
            buffer.seek(0)
            
            # Process document
            tg_user_id = update.effective_user.id
            result = self.knowledge_manager.save_document_knowledge(
                str(tg_user_id), 
                buffer, 
                file_name
            )
            
            if result['success']:
                quota_info = result.get('quota_info', {})
                msg = f"""
✅ **Upload thành công!**

📊 **Kết quả:**
├─ 📄 Format: {result.get('format', 'Unknown')}
├─ 📝 Chunks đã lưu: {result['chunks_count']}"""
                
                if result.get('chunks_skipped', 0) > 0:
                    msg += f"\n├─ ⚠️ Bỏ qua: {result['chunks_skipped']} chunks"
                
                msg += f"""
└─ 💾 Quota: {quota_info.get('documents_count', 0)}/{quota_info.get('documents_limit', 100)} ({quota_info.get('usage_percent', 0):.1f}%)

🎉 Nội dung đã được thêm vào Knowledge Base!
"""
            else:
                msg = f"❌ **Lỗi:** {result['message']}"
            
            keyboard = [
                [InlineKeyboardButton("📚 Knowledge Base", callback_data='menu_knowledge')],
                [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
            ]
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            await update.message.reply_text(
                f"❌ Lỗi xử lý file: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ])
            )
        
        return State.MAIN_MENU.value
    
    async def kb_handle_upload(self, update: Update, context: CallbackContext) -> int:
        """Handle uploaded knowledge file - supports any filename, forwarded messages"""
        
        # Check if message has document
        doc = update.message.document if update.message else None
        
        if not doc:
            await update.message.reply_text(
                "❌ Không tìm thấy file.\n\n"
                "**Formats hỗ trợ:**\n"
                "• Excel (.xlsx) - Template Knowledge Base\n"
                "• PDF, Word, Text - Tài liệu",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Tải template mẫu", callback_data='kb_download_template')],
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ]),
                parse_mode='Markdown'
            )
            return State.KNOWLEDGE_UPLOAD.value
        
        # Check file type by extension OR MIME type
        file_name = doc.file_name or ""
        mime_type = doc.mime_type or ""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ""
        
        is_excel = (
            ext in ['xlsx', 'xls'] or
            'spreadsheet' in mime_type.lower() or
            'excel' in mime_type.lower()
        )
        
        is_document = ext in ['pdf', 'docx', 'txt', 'md'] or any(
            t in mime_type.lower() for t in ['pdf', 'word', 'text/plain']
        )
        
        # Route to document handler if not Excel
        if not is_excel and is_document:
            return await self.kb_handle_document_upload(update, context)
        
        if not is_excel:
            await update.message.reply_text(
                f"❌ Format không hỗ trợ.\n\n"
                f"📄 File: {file_name}\n\n"
                f"**Formats hỗ trợ:**\n"
                f"• Excel (.xlsx) - Template\n"
                f"• PDF, Word, Text - Documents",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Tải template mẫu", callback_data='kb_download_template')],
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ]),
                parse_mode='Markdown'
            )
            return State.KNOWLEDGE_UPLOAD.value
        
        # Check file size (max 5MB for Excel)
        if doc.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ File quá lớn (tối đa 5MB)\n\nVui lòng giảm kích thước file.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ])
            )
            return State.KNOWLEDGE_UPLOAD.value
        
        await update.message.reply_text("⏳ Đang xử lý file Excel...")
        
        try:
            # Download file
            file = await context.bot.get_file(doc.file_id)
            buffer = io.BytesIO()
            await file.download_to_memory(buffer)
            buffer.seek(0)
            
            # Save knowledge
            tg_user_id = update.effective_user.id
            result = self.knowledge_manager.save_user_knowledge(str(tg_user_id), buffer)
            
            if result['success']:
                # Get quota info
                quota_info = result.get('quota_info', {})
                storage_mb = quota_info.get('storage_bytes', 0) / (1024 * 1024)
                
                msg = f"""
✅ **Upload thành công!**

📊 **Kết quả:**
├─ 📄 Đã lưu: {result['items_count']} mục
├─ 📁 Danh mục: {', '.join(result['categories'][:3])}"""
                
                if result.get('items_skipped', 0) > 0:
                    msg += f"\n├─ ⚠️ Bỏ qua: {result['items_skipped']} mục (vượt quota)"
                if result.get('items_cleaned', 0) > 0:
                    msg += f"\n├─ 🧹 Đã dọn: {result['items_cleaned']} mục cũ"
                
                msg += f"""
└─ 💾 Quota: {quota_info.get('documents_count', 0)}/{quota_info.get('documents_limit', 100)} docs ({quota_info.get('usage_percent', 0):.1f}%)

🎉 AI đã "nhớ" thông tin của bạn!
"""
            else:
                msg = f"❌ **Lỗi:** {result['message']}"
            
            keyboard = [
                [InlineKeyboardButton("📚 Xem Knowledge Base", callback_data='menu_knowledge')],
                [InlineKeyboardButton("💬 Bắt đầu chat", callback_data='start_chat')],
                [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
            ]
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            await update.message.reply_text(
                f"❌ Lỗi xử lý file: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
                ])
            )
        
        return State.MAIN_MENU.value
    
    async def kb_delete_confirm(self, update: Update, context: CallbackContext) -> int:
        """Confirm knowledge deletion"""
        query = update.callback_query
        await query.answer()
        
        msg = """
⚠️ **Xác nhận xóa Knowledge Base**

Bạn có chắc muốn xóa toàn bộ Knowledge Base?
Hành động này không thể hoàn tác!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Xác nhận xóa", callback_data='kb_delete_confirm'),
                InlineKeyboardButton("❌ Hủy", callback_data='menu_knowledge')
            ]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.KNOWLEDGE_CONFIRM_DELETE.value
    
    async def kb_delete_execute(self, update: Update, context: CallbackContext) -> int:
        """Execute knowledge deletion"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        success = self.knowledge_manager.delete_user_knowledge(str(tg_user_id))
        
        if success:
            msg = "✅ **Đã xóa Knowledge Base!**\n\nBạn có thể upload file mới bất cứ lúc nào."
        else:
            msg = "❌ Có lỗi xảy ra khi xóa."
        
        keyboard = [[InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    async def kb_cleanup(self, update: Update, context: CallbackContext) -> int:
        """Show cleanup options"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        quota = self.knowledge_manager.get_user_quota(str(tg_user_id))
        
        msg = f"""
🧹 **Dọn dẹp Knowledge Base**

Xóa các documents cũ hoặc ít sử dụng để giải phóng quota.

📊 **Tình trạng hiện tại:**
├─ 📄 Documents: {quota['documents_count']}/{quota['documents_limit']}
├─ 💾 Storage: {quota['storage_bytes'] / 1024 / 1024:.2f}/{quota['storage_limit_mb']} MB
└─ 📈 Sử dụng: {quota['usage_percent']:.1f}%

**Chọn mức độ dọn dẹp:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🧹 Dọn 20%", callback_data='kb_cleanup_20'),
                InlineKeyboardButton("🧹 Dọn 50%", callback_data='kb_cleanup_50')
            ],
            [InlineKeyboardButton("🧹 Dọn 80% (giữ lại 20%)", callback_data='kb_cleanup_80')],
            [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_knowledge')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.KNOWLEDGE_MENU.value
    
    async def kb_cleanup_execute(self, update: Update, context: CallbackContext) -> int:
        """Execute cleanup with specified amount"""
        query = update.callback_query
        await query.answer("🧹 Đang dọn dẹp...")
        
        # Parse cleanup amount from callback data
        data = query.data
        if data == 'kb_cleanup_20':
            amount = 0.2
        elif data == 'kb_cleanup_50':
            amount = 0.5
        elif data == 'kb_cleanup_80':
            amount = 0.8
        else:
            amount = 0.2
        
        tg_user_id = update.effective_user.id
        result = self.knowledge_manager.force_cleanup(str(tg_user_id), amount)
        
        if result['success']:
            quota = self.knowledge_manager.get_user_quota(str(tg_user_id))
            msg = f"""
✅ **Dọn dẹp hoàn tất!**

🧹 Đã xóa: {result['cleaned']} documents

📊 **Tình trạng mới:**
├─ 📄 Documents: {quota['documents_count']}/{quota['documents_limit']}
├─ 💾 Storage: {quota['storage_bytes'] / 1024 / 1024:.2f}/{quota['storage_limit_mb']} MB
└─ 📈 Sử dụng: {quota['usage_percent']:.1f}%
"""
        else:
            msg = f"❌ {result['message']}"
        
        keyboard = [
            [InlineKeyboardButton("📚 Knowledge Base", callback_data='menu_knowledge')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.KNOWLEDGE_MENU.value

    # ============================================================
    # VIEW CONFIGURATION
    # ============================================================
    async def view_config(self, update: Update, context: CallbackContext) -> int:
        """Show current configuration"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        summary = self.user_manager.get_user_config_summary(db_user_id)
        personality = summary.get('personality_config') or {}
        
        msg = f"""
📊 **Cấu hình hiện tại của bạn:**

🆔 **Telegram ID:** `{tg_user_id}`
🗄️ **Database ID:** `{db_user_id}`

**🔑 API Configurations:**
"""
        
        api_configs = summary.get('api_configs', [])
        if api_configs:
            for config in api_configs:
                provider = LLM_PROVIDERS.get(config.get('provider_name')) or \
                          TTS_PROVIDERS.get(config.get('provider_name')) or {}
                emoji = provider.get('emoji', '🔧')
                msg += f"├─ {emoji} {config.get('provider_name', 'Unknown')}"
                if config.get('is_default'):
                    msg += " ⭐"
                msg += "\n"
        else:
            msg += "├─ _(Chưa có cấu hình nào)_\n"
        
        msg += "\n**😊 Personality:**\n"
        if personality:
            msg += f"├─ 🏷️ Tên: {personality.get('character_name', 'MeiLin')}\n"
            msg += f"├─ 🎤 Wake Word: {personality.get('wake_word', 'hi meilin')}\n"
            msg += f"├─ 💬 Phong cách: {personality.get('speaking_style', 'friendly')}\n"
            msg += f"└─ 🌏 Ngôn ngữ: {personality.get('primary_language', 'vi')}\n"
        else:
            msg += "└─ _(Sử dụng mặc định)_\n"
        
        keyboard = [
            [
                InlineKeyboardButton("⚙️ Chỉnh sửa API", callback_data='menu_api'),
                InlineKeyboardButton("😊 Chỉnh sửa Personality", callback_data='menu_personality')
            ],
            [InlineKeyboardButton("🗑️ Xóa cấu hình", callback_data='delete_config')],
            [InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.VIEW_CONFIG.value
    
    # ============================================================
    # NAVIGATION
    # ============================================================
    async def back_to_main(self, update: Update, context: CallbackContext) -> int:
        """Go back to main menu"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        db_user_id = session.get('db_user_id') or context.user_data.get('db_user_id')
        
        if not db_user_id:
            db_user_id = self.get_or_create_db_user(update)
        
        summary = self.user_manager.get_user_config_summary(db_user_id)
        
        tg_user = update.effective_user
        welcome_msg = self._build_welcome_message(tg_user, summary)
        keyboard = self._build_main_menu_keyboard(summary)
        
        await query.edit_message_text(
            welcome_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    async def cancel(self, update: Update, context: CallbackContext) -> int:
        """Cancel current operation"""
        query = update.callback_query
        if query:
            await query.answer()
            await query.edit_message_text(
                "❌ Đã hủy thao tác.\n\nSử dụng /start để bắt đầu lại."
            )
        else:
            await update.message.reply_text(
                "❌ Đã hủy thao tác.\n\nSử dụng /start để bắt đầu lại."
            )
        
        return ConversationHandler.END
    
    async def start_chat(self, update: Update, context: CallbackContext) -> int:
        """Start chat mode"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "💬 **Chế độ Chat đã bật!**\n\n"
            "Bạn có thể bắt đầu gửi tin nhắn ngay bây giờ.\n\n"
            "📌 Các lệnh hữu ích:\n"
            "• /config - Mở menu cấu hình\n"
            "• /status - Xem trạng thái\n"
            "• /help - Xem hướng dẫn",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def show_help(self, update: Update, context: CallbackContext) -> int:
        """Show help message"""
        query = update.callback_query
        await query.answer()
        
        msg = """
❓ **Hướng dẫn sử dụng MeiLin**

**📱 Các lệnh cơ bản:**
• `/start` - Bắt đầu / Menu chính
• `/config` - Mở cấu hình
• `/status` - Xem trạng thái
• `/help` - Xem hướng dẫn này

**🔐 Về bảo mật:**
• Telegram User ID của bạn được dùng để nhận diện
• API Keys được mã hóa trước khi lưu
• Bạn có thể xóa dữ liệu bất cứ lúc nào

**🤖 Về AI:**
• Bạn cần cấu hình LLM để chat
• TTS là tùy chọn (cho giọng nói)
• Personality tùy chỉnh tính cách AI

**📞 Hỗ trợ:**
Liên hệ admin nếu cần giúp đỡ.
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.MAIN_MENU.value
    
    # ============================================================
    # ESP DEVICE MANAGEMENT
    # ============================================================
    async def menu_esp(self, update: Update, context: CallbackContext) -> int:
        """Show ESP device management menu"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        devices = self.esp_device_manager.get_user_devices(tg_user_id)
        
        msg = """
📱 **Quản lý ESP32 Devices**

Đăng ký ESP32 của bạn để:
• ✅ Sử dụng API keys của bạn trên ESP
• ✅ Truy cập MeiLin Knowledge Base
• ✅ Custom persona và cài đặt

"""
        
        if devices:
            msg += f"**📋 Devices của bạn ({len(devices)}):**\n"
            for i, dev in enumerate(devices, 1):
                status = "🟢" if dev['is_active'] else "🔴"
                msg += f"{i}. {status} **{dev['device_name']}**\n"
                msg += f"   └ ID: `{dev['device_id']}`\n"
        else:
            msg += "_Bạn chưa đăng ký device nào._\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Đăng ký Device mới", callback_data='esp_register')],
        ]
        
        if devices:
            keyboard.append([
                InlineKeyboardButton("📋 Xem chi tiết Devices", callback_data='esp_list_details')
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='back_main')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.ESP_MENU.value
    
    async def esp_register_start(self, update: Update, context: CallbackContext) -> int:
        """Start ESP device registration - ask for device ID"""
        query = update.callback_query
        await query.answer()
        
        msg = """
➕ **Đăng ký ESP32 Device**

**Bước 1/2: Nhập Device ID**

Device ID là mã định danh duy nhất của ESP32.
Bạn có thể tự đặt hoặc dùng MAC address.

📌 **Ví dụ:**
• `esp32_living_room`
• `meilin_bedroom_01`
• `AA:BB:CC:DD:EE:FF`

💡 _Yêu cầu: 6-50 ký tự, không có khoảng trắng_

Nhập Device ID:
"""
        
        keyboard = [[InlineKeyboardButton("❌ Hủy", callback_data='menu_esp')]]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.ESP_REGISTER_ID.value
    
    async def esp_register_id_received(self, update: Update, context: CallbackContext) -> int:
        """Receive Device ID, ask for name"""
        tg_user_id = update.effective_user.id
        device_id = update.message.text.strip()
        
        # Validate device_id
        if len(device_id) < 6 or len(device_id) > 50:
            await update.message.reply_text(
                "❌ Device ID phải từ 6-50 ký tự.\n\nVui lòng nhập lại:"
            )
            return State.ESP_REGISTER_ID.value
        
        if ' ' in device_id:
            await update.message.reply_text(
                "❌ Device ID không được chứa khoảng trắng.\n\nVui lòng nhập lại:"
            )
            return State.ESP_REGISTER_ID.value
        
        # Save to session
        session = self.get_session(tg_user_id)
        session['esp_register'] = {'device_id': device_id}
        
        msg = f"""
✅ **Device ID:** `{device_id}`

**Bước 2/2: Nhập tên Device (tùy chọn)**

Đặt tên dễ nhớ cho device của bạn.

📌 **Ví dụ:**
• MeiLin Phòng khách
• ESP32 Phòng ngủ
• My Smart Speaker

💡 _Hoặc gửi /skip để dùng Device ID làm tên_
"""
        
        keyboard = [[InlineKeyboardButton("⏭️ Bỏ qua", callback_data='esp_skip_name')]]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.ESP_REGISTER_NAME.value
    
    async def esp_register_name_received(self, update: Update, context: CallbackContext) -> int:
        """Receive device name and complete registration"""
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        
        device_name = update.message.text.strip() if update.message else None
        device_id = session.get('esp_register', {}).get('device_id')
        
        if not device_id:
            await update.message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại với /start")
            return ConversationHandler.END
        
        # Register device
        result = self.esp_device_manager.register_device(
            device_id=device_id,
            telegram_user_id=tg_user_id,
            device_name=device_name
        )
        
        if not result['success']:
            await update.message.reply_text(
                f"❌ Đăng ký thất bại: {result.get('error')}\n\n"
                "Vui lòng thử lại với Device ID khác."
            )
            return await self.menu_esp(update, context)
        
        # Success message with API key
        msg = f"""
🎉 **Đăng ký thành công!**

📱 **Device:** {device_name or device_id}
🆔 **Device ID:** `{device_id}`

🔑 **Device API Key:**
```
{result['device_api_key']}
```

⚠️ **QUAN TRỌNG:**
1. Copy API key này và lưu lại
2. Cấu hình trong ESP32 menuconfig:
   ```
   → MeiLin Configuration
     → Device API Key: {result['device_api_key']}
   ```

💡 Device sẽ tự động sử dụng API keys (LLM, TTS) mà bạn đã cấu hình trong bot này.
"""
        
        keyboard = [
            [InlineKeyboardButton("📱 Quản lý Devices", callback_data='menu_esp')],
            [InlineKeyboardButton("🔙 Menu chính", callback_data='back_main')]
        ]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Clear session
        session.pop('esp_register', None)
        
        return State.ESP_MENU.value
    
    async def esp_skip_name(self, update: Update, context: CallbackContext) -> int:
        """Skip device name and use device_id as name"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        session = self.get_session(tg_user_id)
        device_id = session.get('esp_register', {}).get('device_id')
        
        if not device_id:
            await query.edit_message_text("❌ Có lỗi xảy ra. Vui lòng thử lại với /start")
            return ConversationHandler.END
        
        # Register device with device_id as name
        result = self.esp_device_manager.register_device(
            device_id=device_id,
            telegram_user_id=tg_user_id,
            device_name=device_id
        )
        
        if not result['success']:
            await query.edit_message_text(
                f"❌ Đăng ký thất bại: {result.get('error')}\n\n"
                "Vui lòng thử lại với Device ID khác."
            )
            return State.ESP_MENU.value
        
        # Success message
        msg = f"""
🎉 **Đăng ký thành công!**

📱 **Device:** {device_id}

🔑 **Device API Key:**
```
{result['device_api_key']}
```

⚠️ **Lưu API key này** và cấu hình trong ESP32!

💡 Device sẽ tự động sử dụng API keys của bạn.
"""
        
        keyboard = [
            [InlineKeyboardButton("📱 Quản lý Devices", callback_data='menu_esp')],
            [InlineKeyboardButton("🔙 Menu chính", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        session.pop('esp_register', None)
        return State.ESP_MENU.value
    
    async def esp_list_details(self, update: Update, context: CallbackContext) -> int:
        """Show detailed list of user's devices"""
        query = update.callback_query
        await query.answer()
        
        tg_user_id = update.effective_user.id
        devices = self.esp_device_manager.get_user_devices(tg_user_id)
        
        if not devices:
            await query.edit_message_text(
                "📱 Bạn chưa có device nào.\n\nSử dụng nút bên dưới để đăng ký.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Đăng ký Device", callback_data='esp_register')],
                    [InlineKeyboardButton("🔙 Quay lại", callback_data='menu_esp')]
                ])
            )
            return State.ESP_MENU.value
        
        msg = "📱 **Chi tiết ESP32 Devices:**\n\n"
        
        keyboard = []
        for dev in devices:
            status = "🟢 Active" if dev['is_active'] else "🔴 Disabled"
            msg += f"**{dev['device_name']}**\n"
            msg += f"├─ ID: `{dev['device_id']}`\n"
            msg += f"├─ Key: `{dev['device_api_key']}`\n"
            msg += f"├─ Status: {status}\n"
            msg += f"├─ Requests: {dev['total_requests']}\n"
            msg += f"└─ Last seen: {dev['last_seen'] or 'Never'}\n\n"
            
            # Add button for each device
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ {dev['device_name'][:20]}", 
                    callback_data=f"esp_manage_{dev['device_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='menu_esp')])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return State.ESP_VIEW_DEVICES.value
    
    # ============================================================
    # BUILD APPLICATION
    # ============================================================
    def build_application(self) -> Application:
        """Build the Telegram application with all handlers"""
        
        app = Application.builder().token(self.token).build()
        
        # Main conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.cmd_start),
                CommandHandler('config', self.cmd_start),
            ],
            states={
                State.MAIN_MENU.value: [
                    CallbackQueryHandler(self.wizard_start, pattern='^wizard_start$'),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                    CallbackQueryHandler(self.menu_knowledge, pattern='^menu_knowledge$'),
                    CallbackQueryHandler(self.menu_esp, pattern='^menu_esp$'),
                    CallbackQueryHandler(self.view_config, pattern='^view_config$'),
                    CallbackQueryHandler(self.start_chat, pattern='^start_chat$'),
                    CallbackQueryHandler(self.show_help, pattern='^help$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^menu_api$'),
                    # Accept Excel file anytime from main menu
                    MessageHandler(filters.Document.ALL, self.kb_handle_upload_anytime),
                ],
                State.API_SELECT_PROVIDER.value: [
                    CallbackQueryHandler(self.wizard_select_llm, pattern='^select_llm_'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                ],
                State.API_ENTER_KEY.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.wizard_enter_api_key),
                    CallbackQueryHandler(self.wizard_start, pattern='^wizard_start$'),
                ],
                State.API_ENTER_BASE.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.wizard_enter_base),
                ],
                State.API_ENTER_MODEL.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.wizard_enter_model),
                ],
                State.API_CONFIRM.value: [
                    CallbackQueryHandler(self.save_config, pattern='^save_config$'),
                    CallbackQueryHandler(self.wizard_start, pattern='^wizard_start$'),
                    CallbackQueryHandler(self.cancel, pattern='^cancel_config$'),
                ],
                State.PERSONALITY_MENU.value: [
                    CallbackQueryHandler(self.personality_name, pattern='^personality_name$'),
                    CallbackQueryHandler(self.personality_wake_word, pattern='^personality_wake$'),
                    CallbackQueryHandler(self.personality_style, pattern='^personality_style$'),
                    CallbackQueryHandler(self.personality_language, pattern='^personality_lang$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                ],
                State.PERSONALITY_NAME.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_personality_name),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                ],
                State.PERSONALITY_WAKE_WORD.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_wake_word),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                ],
                State.PERSONALITY_SPEAKING_STYLE.value: [
                    CallbackQueryHandler(self.save_speaking_style, pattern='^style_'),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                ],
                State.PERSONALITY_LANGUAGE.value: [
                    CallbackQueryHandler(self.save_language, pattern='^lang_'),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                ],
                State.VIEW_CONFIG.value: [
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                    CallbackQueryHandler(self.menu_personality, pattern='^menu_personality$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^menu_api$'),
                ],
                # Knowledge Base states
                State.KNOWLEDGE_MENU.value: [
                    CallbackQueryHandler(self.kb_download_template, pattern='^kb_download_template$'),
                    CallbackQueryHandler(self.kb_download_current, pattern='^kb_download_current$'),
                    CallbackQueryHandler(self.kb_upload_prompt, pattern='^kb_upload$'),
                    CallbackQueryHandler(self.kb_delete_confirm, pattern='^kb_delete$'),
                    CallbackQueryHandler(self.kb_cleanup, pattern='^kb_cleanup$'),
                    CallbackQueryHandler(self.kb_cleanup_execute, pattern='^kb_cleanup_\\d+$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                ],
                State.KNOWLEDGE_UPLOAD.value: [
                    MessageHandler(filters.Document.ALL, self.kb_handle_upload),
                    CallbackQueryHandler(self.kb_download_template, pattern='^kb_download_template$'),
                    CallbackQueryHandler(self.menu_knowledge, pattern='^menu_knowledge$'),
                ],
                State.KNOWLEDGE_CONFIRM_DELETE.value: [
                    CallbackQueryHandler(self.kb_delete_execute, pattern='^kb_delete_confirm$'),
                    CallbackQueryHandler(self.menu_knowledge, pattern='^menu_knowledge$'),
                ],
                # ESP Device Management states
                State.ESP_MENU.value: [
                    CallbackQueryHandler(self.esp_register_start, pattern='^esp_register$'),
                    CallbackQueryHandler(self.esp_list_details, pattern='^esp_list_details$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                ],
                State.ESP_REGISTER_ID.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.esp_register_id_received),
                    CallbackQueryHandler(self.menu_esp, pattern='^menu_esp$'),
                ],
                State.ESP_REGISTER_NAME.value: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.esp_register_name_received),
                    CallbackQueryHandler(self.esp_skip_name, pattern='^esp_skip_name$'),
                    CallbackQueryHandler(self.menu_esp, pattern='^menu_esp$'),
                ],
                State.ESP_VIEW_DEVICES.value: [
                    CallbackQueryHandler(self.menu_esp, pattern='^menu_esp$'),
                    CallbackQueryHandler(self.back_to_main, pattern='^back_main$'),
                ],
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                CallbackQueryHandler(self.cancel, pattern='^cancel'),
                # Catch-all for expired callbacks - redirect to main menu
                CallbackQueryHandler(self.handle_expired_callback),
            ],
            per_user=True,
            per_chat=True,
        )
        
        app.add_handler(conv_handler)
        
        # Global handler for any callback that wasn't handled (expired sessions)
        app.add_handler(CallbackQueryHandler(self.handle_expired_callback))
        
        return app
    
    async def handle_expired_callback(self, update: Update, context: CallbackContext) -> int:
        """Handle callbacks from old messages after bot restart"""
        query = update.callback_query
        await query.answer("⏰ Phiên đã hết hạn. Đang tải lại...")
        
        # Get user info and show main menu
        tg_user = update.effective_user
        db_user_id = self.get_or_create_db_user(update)
        
        if db_user_id:
            summary = self.user_manager.get_user_config_summary(db_user_id)
            welcome_msg = self._build_welcome_message(tg_user, summary)
            keyboard = self._build_main_menu_keyboard(summary)
            
            try:
                await query.edit_message_text(
                    welcome_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception:
                # If edit fails, send new message
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text(
                "⏰ Phiên đã hết hạn.\n\nVui lòng gõ /start để bắt đầu lại."
            )
        
        return State.MAIN_MENU.value
    
    def run(self):
        """Run the bot"""
        app = self.build_application()
        logger.info("Starting Interactive Config Bot...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    """Main entry point"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("Please set it in .env file or environment.")
        return
    
    bot = InteractiveConfigBot(token)
    bot.run()


if __name__ == '__main__':
    main()
