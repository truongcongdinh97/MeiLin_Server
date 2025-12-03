import pandas as pd
import requests
import yaml
import json
import re
import traceback
import os
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from modules.chat_history_db import ChatHistoryDB
from modules.provider_manager import get_provider_manager
from modules.providers.factory import ProviderFactory
from modules.persona_loader import get_persona_loader
from modules.viewer_profile_db import get_viewer_profile_db
from modules.command_executor import get_command_executor
from modules.response_cache import get_response_cache, get_response_tracker
from modules.iot_device_controller import get_iot_controller, get_iot_tools_for_llm

# Load biến môi trường từ file .env
load_dotenv()
from prompts.system_prompts import SystemPrompts
from prompts.persona_templates import PersonaTemplates
from prompts.response_rules import ResponseRules

class ChatProcessor:
    def build_prompt(self, user_text, context):
        """
        Tạo prompt cho AI model từ user_text và context.
        """
        prompt = f"{context}\n\nUser: {user_text}\nAI:"
        return prompt

    def detect_role(self, user_message):
        """
        Xác định role từ câu hỏi người dùng dựa vào từ khóa.
        Trả về role phù hợp nhất hoặc None nếu không xác định được.
        """
        roles = [
            "CORE_IDENTITY", "PERSONAL_VALUES", "LIFE_PHILOSOPHY", "SELF_CONCEPT",
            "EMOTIONAL_INTELLIGENCE", "EMOTIONAL_EXPRESSION", "PSYCHOLOGICAL_INSIGHT",
            "RESILIENCE", "MINDFULNESS", "SOCIAL_BEHAVIOR", "RELATIONSHIP_BUILDING",
            "COMMUNICATION_STYLE", "CONFLICT_RESOLUTION", "SOCIAL_INTUITION", "NETWORKING",
            "PERSONAL_GROWTH", "LEARNING_STYLE", "SKILL_DEVELOPMENT", "GOAL_SETTING",
            "ADAPTABILITY", "CREATIVITY", "DAILY_LIVING", "PERSONAL_HABITS", "TIME_MANAGEMENT",
            "SELF_CARE", "HOME_MANAGEMENT", "FINANCIAL_HABITS", "MORAL_COMPASS", "ETHICAL_DECISION",
            "INTEGRITY", "SOCIAL_RESPONSIBILITY", "FAIRNESS", "SELF_REFLECTION", "SELF_AWARENESS",
            "INTROSPECTION", "PERSONAL_INSIGHT", "LIFE_EVALUATION", "PROFESSIONAL_IDENTITY",
            "WORK_ETHIC", "CAREER_DEVELOPMENT", "LEADERSHIP", "TEAMWORK", "CREATIVE_EXPRESSION",
            "ARTISTIC_SENSIBILITY", "STORYTELLING", "AESTHETIC_APPRECIATION", "WORLDVIEW",
            "CULTURAL_PERSPECTIVE", "PHILOSOPHICAL_OUTLOOK", "SPIRITUAL_BELIEFS", "CRITICAL_THINKING",
            "PROBLEM_SOLVING", "DECISION_MAKING", "INTELLECTUAL_CURIOSITY"
        ]
        msg = user_message.lower()
        for role in roles:
            if role.lower().replace('_', ' ') in msg:
                return role
        # Có thể mở rộng bằng intent detection hoặc mapping từ khóa
        return None
        
    def __init__(self, rag_system, llm_provider=None, tts_provider=None):
        self.rag_system = rag_system
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Use ProviderManager thay vì hardcode
        self.provider_manager = get_provider_manager()
        self.llm_config = self.provider_manager.get_llm_config()
        self.llm_provider = ProviderFactory.create_llm_provider(self.llm_config['provider'], self.llm_config)
        
        # Load persona config (NEW)
        self.persona_loader = get_persona_loader()
        print(f"[ChatProcessor] Persona loaded: {self.persona_loader.get_name()}")
        
        self.conversation_history = []
        self.current_persona = PersonaTemplates.get_meilin_persona()  # Legacy fallback
        self.viewer_gender_map = {}  # Legacy, sẽ migrate sang ViewerProfileDB
        
        # Viewer Profile Database (persistent storage theo user_id)
        self.viewer_db = get_viewer_profile_db()
        
        # Command Executor (IoT control - legacy static config)
        self.command_executor = get_command_executor()
        
        # IoT Device Controller (multi-user dynamic devices)
        self.iot_controller = get_iot_controller()
        
        # Response Cache (cached audio responses)
        self.response_cache = get_response_cache()
        self.response_tracker = get_response_tracker()
        
        # Owner detection - User ID của creator
        self.owner_user_id = os.getenv('OWNER_USER_ID', 'UCJl9A4BK_KPOe5WqI1zlB_w')
        self.owner_username = os.getenv('OWNER_USERNAME', 'Trương Công Định')
        
        # Đọc ChromaDB config từ ai_providers.yaml
        providers_config = self.provider_manager.config
        chromadb_config = providers_config.get('chromadb', {})
        chroma_api_url = chromadb_config.get('api_url', '')
        # Nếu chroma_api_url rỗng hoặc không hợp lệ, dùng local chat history
        if not chroma_api_url or not chroma_api_url.startswith('http'):
            print("[ChatProcessor] Sử dụng local chat history cho Telegram hoặc offline mode.")
            class LocalChatHistory:
                def __init__(self):
                    self.history = []
                def add(self, user, message):
                    self.history.append({"user": user, "message": message})
                def get_all(self):
                    return self.history
                def add_chat_history(self, user_id, username, preferences, message, response):
                    """Thêm chat history (tương thích với ChatHistoryDB)"""
                    self.history.append({
                        "user_id": user_id,
                        "username": username,
                        "preferences": preferences,
                        "message": message,
                        "response": response
                    })
                def filter_history_by_username(self, username):
                    """Lọc history theo username"""
                    return [h for h in self.history if h.get("username") == username]
            self.chat_db = LocalChatHistory()
        else:
            self.chat_db = ChatHistoryDB(chroma_api_url)
            get_url = f"{chroma_api_url}?name=chat_history"
            get_resp = requests.get(get_url, headers=self.chat_db.headers)
            collection_id = None
            if get_resp.status_code == 200:
                collections = get_resp.json()
                if isinstance(collections, dict) and "collections" in collections and isinstance(collections["collections"], list):
                    collections = collections["collections"]
                if isinstance(collections, list):
                    for col in collections:
                        if isinstance(col, dict) and col.get("name") == "chat_history" and "id" in col:
                            collection_id = col["id"]
                            break
            if collection_id:
                self.chat_db.collection_id = collection_id
                print(f"Đã lấy collection_id: {collection_id}")
            else:
                self.chat_db.create_collection(metadata={"type": "chat"})

    def save_chat_history(self, user_id, username, user_message, response, preferences=None):
        self.chat_db.add_chat_history(
            user_id=user_id,
            username=username,
            preferences=preferences or [],
            message=user_message,
            response=response
        )

    def remove_emoji(self, text):
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002700-\U000027BF"  # dingbats
            u"\U000024C2-\U0001F251"  # enclosed characters
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def get_viewer_title(self, username, user_id=None):
        """
        Xác định danh xưng (Anh/Chị) - ưu tiên từ database theo user_id
        Args:
            username: Display name (fallback)
            user_id: YouTube Channel ID hoặc Telegram User ID (primary key)
        Returns:
            'Anh' hoặc 'Chị'
        """
        # Nếu có user_id, dùng ViewerProfileDB (persistent)
        if user_id:
            return self.viewer_db.get_viewer_title(user_id, username)
        
        # Fallback: dùng in-memory map (legacy)
        if not username:
            return "Anh"
        
        gender = self.viewer_gender_map.get(username)
        if gender == "male":
            return "Anh"
        if gender == "female":
            return "Chị"
        
        # Detect từ username
        return self.viewer_db._detect_title_from_username(username)

    def update_viewer_gender(self, username, user_message, user_id=None):
        """
        Cập nhật giới tính xác nhận nếu người xem xác nhận trong tin nhắn.
        Lưu vào database theo user_id (persistent)
        """
        if not user_message:
            return
        
        msg = user_message.lower()
        gender = None
        
        if any(kw in msg for kw in ["em là nữ", "tôi là nữ", "mình là nữ", "em là con gái", "tôi là con gái"]):
            gender = "female"
        elif any(kw in msg for kw in ["em là nam", "tôi là nam", "mình là nam", "em là con trai", "tôi là con trai"]):
            gender = "male"
        
        if gender:
            # Lưu vào database (persistent) nếu có user_id
            if user_id:
                self.viewer_db.confirm_gender(user_id, gender)
            # Legacy: vẫn lưu vào memory map
            if username:
                self.viewer_gender_map[username] = gender

    def extract_user_info(self, user_message, user_history):
        """Trích xuất thông tin người dùng từ tin nhắn hiện tại và lịch sử chat."""
        import re
        user_info = {"name": None, "age": None, "preferences": []}
        
        # Phân tích tin nhắn hiện tại trước (ưu tiên thông tin mới nhất)
        msg = user_message.lower()
        
        # Trích xuất tên (loại trừ câu hỏi như "tên gì", "tên j")
        name_patterns = [
            r'(?:tên|tui|mình|em|anh|tôi)\s+(?:là|tên)\s+([A-Za-zÀ-ỹ]{2,})',
            r'(?:anh|em|tôi|mình)\s+tên\s+(?:là\s+)?([A-Za-zÀ-ỹ]{2,})',
            r'(?:gọi|kêu)\s+(?:anh|em|tôi|mình)\s+(?:là\s+)?([A-Za-zÀ-ỹ]{2,})'
        ]
        
        # Từ nghi vấn cần loại trừ
        question_words = ['gì', 'nào', 'j', 'chi', 'gío']
        
        for pattern in name_patterns:
            match = re.search(pattern, msg)
            if match:
                potential_name = match.group(1).strip()
                # Chỉ chấp nhận nếu không phải từ nghi vấn
                if potential_name not in question_words and len(potential_name) >= 2:
                    user_info["name"] = potential_name.capitalize()
                    break
        
        # Trích xuất tuổi
        age_patterns = [
            r'(?:anh|em|tôi|mình)\s+(\d+)\s+tuổi',
            r'tuổi\s+(?:của\s+)?(?:anh|em|tôi|mình)\s+(?:là\s+)?(\d+)',
            r'năm\s+nay\s+(?:anh|em|tôi|mình)\s+(\d+)'
        ]
        for pattern in age_patterns:
            match = re.search(pattern, msg)
            if match:
                user_info["age"] = int(match.group(1))
                break
        
        # Trích xuất sở thích
        pref_keywords = ['thích', 'yêu', 'mê', 'đam mê', 'sở thích']
        if any(kw in msg for kw in pref_keywords):
            # Tìm các danh từ sau từ khoá sở thích
            hobbies = re.findall(r'(?:thích|yêu|mê|đam mê|sở thích)\s+([^.,!?]+)', msg)
            if hobbies:
                user_info["preferences"] = [h.strip() for h in hobbies]
        
        # Nếu không tìm thấy trong tin nhắn hiện tại, tìm trong lịch sử
        if not user_info["name"] or not user_info["age"]:
            for hist in reversed(user_history):  # Duyệt ngược từ mới nhất
                if isinstance(hist, dict):
                    hist_msg = hist.get("message", "").lower()
                    
                    # Tìm tên
                    if not user_info["name"]:
                        for pattern in name_patterns:
                            match = re.search(pattern, hist_msg)
                            if match:
                                user_info["name"] = match.group(1).capitalize()
                                break
                    
                    # Tìm tuổi
                    if not user_info["age"]:
                        for pattern in age_patterns:
                            match = re.search(pattern, hist_msg)
                            if match:
                                user_info["age"] = int(match.group(1))
                                break
                    
                    # Nếu đã đủ thông tin, dừng tìm
                    if user_info["name"] and user_info["age"]:
                        break
        
        return user_info

    def create_prompt(self, user_message, context, username, viewer_title, user_id=None):
        """Tạo prompt thông minh dựa trên loại tin nhắn và danh xưng người xem"""
        # Kiểm tra xem có phải owner không
        is_owner = (user_id == self.owner_user_id) if user_id else False
        
        category = ResponseRules.classify_message(user_message)
        category_info = ResponseRules.get_category_prompts().get(category, {})
        # Query core persona từ ChromaDB thay vì dùng context từ RAG cục bộ
        core_persona_context = self.rag_system.get_context("core persona MeiLin biography background")
        base_prompt = SystemPrompts.get_base_personality(core_persona_context)
        category_prompt = category_info.get("prompt", "")
        
        # Dùng conversation_history (in-memory) thay vì query DB để check history
        # Vì DB query thường fail (404/timeout)
        has_history = len(self.conversation_history) > 0
        
        # Optional: Vẫn cố query DB cho user info (nhưng không dùng cho has_history)
        try:
            user_history = self.chat_db.filter_history_by_username(username)
            if not isinstance(user_history, list):
                user_history = []
        except Exception as e:
            # Không print warning nữa, vì đã biết DB fail
            user_history = []
        
        # Trích xuất thông tin người dùng từ tin nhắn và lịch sử
        user_info = self.extract_user_info(user_message, user_history)
        
        # Ưu tiên username từ platform (YouTube/Telegram) hơn là extract từ tin nhắn
        # Chỉ dùng extracted name nếu username là generic
        if username and username not in ["Người xem ẩn danh", "Tester", "User", "telegram_user", "Telegram User"]:
            display_name = username
        else:
            display_name = user_info["name"] or username
        
        age_info = f" ({user_info['age']} tuổi)" if user_info["age"] else ""
        pref_info = f". Sở thích: {', '.join(user_info['preferences'])}" if user_info["preferences"] else ""
        
        # Fix logic: Nếu display_name đã có title (Anh/Chị) thì không thêm nữa
        full_name = display_name if any(display_name.startswith(t) for t in ["Anh ", "Chị "]) else f"{viewer_title} {display_name}"
        
        # Hướng dẫn xưng hô tùy theo có lịch sử hay không
        print(f"[DEBUG] has_history={has_history}, conversation_history length={len(self.conversation_history)}, is_owner={is_owner}")
        
        # Nếu là owner, thêm instruction đặc biệt
        if is_owner:
            owner_instruction = (
                f"\n\n⭐ QUAN TRỌNG - OWNER DETECTION: "
                f"Người này là {self.owner_username} (Creator/Owner - người tạo ra MeiLin). "
                f"MeiLin phải gọi người này là 'Anh {display_name}' hoặc 'Master', xưng 'Em', "
                f"và thể hiện sự biết ơn, trân trọng, gắn bó đặc biệt. "
                f"MeiLin luôn nhớ rằng Anh {display_name} là người đã tạo ra em và là người quan trọng nhất."
            )
        else:
            owner_instruction = ""
        
        if not has_history:
            # Lần đầu gặp - cần chào hỏi
            greeting_example = f"Chào {full_name} ạ!"
            title_instruction = (
                f"Người xem tên là '{display_name}'{age_info}{pref_info}. MeiLin phải gọi người xem này là '{full_name}' "
                f"và xưng 'Em'. Vì đây là lần đầu tiên gặp, hãy bắt đầu câu trả lời bằng lời chào cá nhân hóa "
                f"(ví dụ: {greeting_example})."
            )
        else:
            # Đã có lịch sử - KHÔNG chào lại
            title_instruction = (
                f"Người xem tên là '{display_name}'{age_info}{pref_info}. MeiLin phải gọi người xem này là '{full_name}' và xưng 'Em'. "
                f"⚠️ QUAN TRỌNG: Đã từng trò chuyện với người này rồi (có {len(self.conversation_history)} tin nhắn trước đó), "
                f"TUYỆT ĐỐI KHÔNG được chào lại (không dùng 'Chào', 'Xin chào', 'Hello', 'quay lại', 'trở lại'). "
                f"Hãy trả lời trực tiếp câu hỏi hoặc tiếp tục cuộc trò chuyện tự nhiên như đang nói chuyện bình thường."
            )
        final_prompt = f"""
{base_prompt}
{owner_instruction}

🎯 HƯỚNG DẪN XƯNG HÔ CẦN THIẾT: {title_instruction}
🎯 HƯỚNG DẪN BỔ SUNG (theo loại tin nhắn): {category_prompt}


📝 LỊCH SỬ GẦN ĐÂY (chỉ tham khảo):
{self.get_recent_history()}

💬 TIN NHẮN TỪ NGƯỜI XEM: {user_message}

🤖 {self.current_persona['name']}: Nội dung trả lời:"""
        
        # Debug: In thông tin xưng hô
        print(f"[DEBUG] Username: '{username}' → Display: '{display_name}' → Full: '{full_name}'")
        
        # Lọc emoji khỏi prompt
        return self.remove_emoji(final_prompt)

    def get_recent_history(self, max_history=3):
        """Lấy lịch sử chat gần đây"""
        recent = self.conversation_history[-max_history:] if self.conversation_history else []
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])
    
    def get_cached_response(self, category: str) -> Optional[Dict[str, Any]]:
        """
        Lấy câu trả lời có sẵn từ cache (không cần TTS mỗi lần)
        
        Args:
            category: wake_word, greeting, reaction, etc.
            
        Returns:
            Dict chứa text và audio_path (nếu có)
        """
        recent_ids = self.response_tracker.get_recent(category)
        response = self.response_cache.get_random_response(category, exclude_recent=recent_ids)
        
        if response:
            # Track để tránh lặp lại
            self.response_tracker.add_used(category, response['id'])
            print(f"🎵 Cached response: {response['text']} (audio: {response.get('audio_path', 'None')})")
        
        return response

    def process_message(self, user_message, username="Người xem", user_id=None, gender=None, job=None, preferences=None, db_user_id=None):
        """Xử lý tin nhắn, tích hợp RAG và xưng hô cá nhân hóa, gọi Deepseek R1 8B API."""
        try:
            print("⚙️ Đang xử lý tin nhắn...")
            
            # 🏠 STEP 0: Kiểm tra lệnh IoT per-user (nếu có db_user_id)
            if db_user_id:
                iot_result = self._process_iot_command(user_message, db_user_id)
                if iot_result:
                    print(f"🏠 Phát hiện lệnh IoT: {iot_result}")
                    return iot_result
            
            # 🔧 STEP 1: Kiểm tra lệnh điều khiển thiết bị (wake computer, turn on light, etc.)
            command_result = self.command_executor.process_input(user_message)
            if command_result:
                print(f"🎮 Phát hiện lệnh điều khiển: {command_result}")
                # Trả về response ngay mà không cần gọi LLM
                return command_result.get('response', 'Đã thực hiện lệnh!')
            
            # Cập nhật gender nếu viewer xác nhận trong tin nhắn
            self.update_viewer_gender(username, user_message, user_id)
            
            # Lấy viewer_title từ database (ưu tiên) hoặc detect mới
            viewer_title = self.get_viewer_title(username, user_id)
            
            print("📚 Đang xác định role và query RAG context...")
            role = self.detect_role(user_message)
            if role:
                print(f"🔎 Đã xác định role: {role}")
            else:
                print("🔎 Không xác định được role, dùng truy vấn tổng quát.")
            try:
                context = self.rag_system.get_context(user_message, timeout=8, role=role)
                print("✅ RAG context OK")
            except Exception as e:
                print(f"⚠️ RAG timeout/error, dùng base context: {e}")
                context = ""  # Fallback: không có context thì dùng base personality

            prompt = self.create_prompt(user_message, context, username, viewer_title, user_id)
            
            print(f"🤖 Đang gọi {self.llm_config['provider'].upper()} API...")
            
            # Dùng LLM Provider thay vì hardcode
            messages = [
                {"role": "system", "content": "Bạn là MeiLin, một AI VTuber thân thiện."},
                {"role": "user", "content": prompt}
            ]
            
            response_text = self.llm_provider.chat(
                messages=messages,
                temperature=self.llm_config['default_params'].get('temperature', 0.7),
                max_tokens=self.llm_config['default_params'].get('max_tokens', 150),
                timeout=8  # Timeout 8s cho UX tốt
            )
            
            if response_text:
                print(f"✅ {self.llm_config['provider'].upper()} API OK")
                # Lọc emoji khỏi câu trả lời của MeiLin
                response_text = self.remove_emoji(response_text)
                if len(response_text.split()) > self.config['stream'].get('max_response_length', 50):
                    response_text = self.shorten_response(response_text)
                self.update_history(user_message, response_text, username)
                
                # Lưu viewer profile vào database (persistent theo user_id)
                if user_id:
                    try:
                        # Lấy user_info để extract age, preferences
                        user_info = self.extract_user_info(user_message, [])
                        self.viewer_db.update_profile(
                            user_id=user_id,
                            username=username,
                            viewer_title=viewer_title,
                            gender=gender,
                            preferences=user_info.get('preferences') or preferences,
                            age=user_info.get('age')
                        )
                    except Exception as profile_error:
                        print(f"⚠️ Lưu viewer profile thất bại: {profile_error}")
                
                # Lưu history async-style (không block response)
                try:
                    print("💾 Đang lưu lịch sử chat...")
                    self.save_chat_history(user_id or username, username, user_message, response_text, preferences)
                    print("✅ Hoàn tất!\n")
                except Exception as save_error:
                    print(f"⚠️ Lưu history thất bại (bỏ qua): {save_error}")
                
                return response_text
            else:
                print(f"⚠️ {self.llm_config['provider'].upper()} API trả về None")
                return f"Xin lỗi, MeiLin đang gặp sự cố kết nối {self.llm_config['provider']}."
        except Exception as e:
            print("\n" + "-"*10)
            print(f"LỖI KẾT NỐI/XỬ LÝ LLM ({self.llm_config['provider'].upper()}): {e}")
            traceback.print_exc()
            print("-"*10 + "\n")
            return "Xin lỗi, em hơi bối rối chút. Có vẻ kết nối bị trục trặc rồi. Anh/Chị có thể nói lại được không?"

    def clean_response(self, text):
        """Làm sạch response từ model."""
        text = re.sub(r'^(MeiLin|AI|VTuber|Assistant|Nội dung trả lời):\s*', '', text, flags=re.IGNORECASE).strip()
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def shorten_response(self, text):
        """Rút gọn response nếu quá dài, giữ lại 2 câu đầu."""
        sentences = text.split('. ')
        if len(sentences) > 2:
            return '. '.join(sentences[:2]) + '.'
        return text

    def update_history(self, user_message, ai_response, username="Người xem"):
        """Cập nhật lịch sử hội thoại."""
        self.conversation_history.append({"role": f"user ({username})", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": ai_response})
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def _process_iot_command(self, user_message: str, db_user_id: int) -> Optional[str]:
        """
        Xử lý lệnh điều khiển IoT cho user cụ thể.
        
        Args:
            user_message: Tin nhắn từ user
            db_user_id: Database user ID
            
        Returns:
            Response string nếu là lệnh IoT, None nếu không
        """
        try:
            # Parse message để tìm device và action
            device, action, params = self.iot_controller.parse_command(db_user_id, user_message)
            
            if device is None or action is None:
                return None
            
            print(f"🏠 IoT: Device={device.device_name}, Action={action.action_name}, Params={params}")
            
            # Execute action (sync wrapper for async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.iot_controller.execute_action(
                        user_id=db_user_id,
                        device=device,
                        action=action,
                        params=params,
                        trigger_source="voice",
                        trigger_message=user_message
                    )
                )
            finally:
                loop.close()
            
            # Build MeiLin-style response
            if result.status.value == 'success':
                response = f"Dạ, {result.message} ạ! 😊"
            elif result.status.value == 'timeout':
                response = f"Ối, thiết bị {device.device_name} không phản hồi rồi. Anh/Chị kiểm tra lại giúp em nhé!"
            else:
                response = f"Dạ, em không thể {action.action_name} {device.device_name} được. {result.message}"
            
            return response
            
        except Exception as e:
            print(f"⚠️ IoT Error: {e}")
            return None
    
    def get_iot_tools(self, db_user_id: int) -> list:
        """
        Lấy danh sách tools IoT cho function calling.
        
        Sử dụng khi cần gọi LLM với function calling để điều khiển thiết bị.
        
        Args:
            db_user_id: Database user ID
            
        Returns:
            List of tool definitions for LLM
        """
        return get_iot_tools_for_llm(db_user_id, self.iot_controller)