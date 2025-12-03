import asyncio
import time
import os
import threading
import keyboard
from modules.rag_system import RAGSystem
from modules.chat_processor import ChatProcessor
from modules.provider_manager import get_provider_manager
from modules.providers.factory import ProviderFactory
from modules.youtube_client import YouTubeClient # Giả định module này trả về username
from dotenv import load_dotenv

load_dotenv()

class AIVTuber:
    tts_active = True

    def toggle_tts(self):
        self.tts_active = not self.tts_active
        status = "BẬT" if self.tts_active else "TẮT"
        provider_name = self.tts_config['provider'] if hasattr(self, 'tts_config') else 'TTS'
        print(f"\n[MeiLin] {provider_name.upper()} TTS hiện đang: {status}")

    def __init__(self):
        print("Khởi tạo AI VTuber...")
        os.makedirs("./logs", exist_ok=True)
        # Khởi tạo từng module với log riêng biệt
        try:
            print("[LOG] Khởi tạo RAGSystem...")
            self.rag_system = RAGSystem()
            print("[LOG] Khởi tạo ChatProcessor...")
            self.chat_processor = ChatProcessor(self.rag_system)
            print("[LOG] Khởi tạo TTS Provider...")
            provider_manager = get_provider_manager()
            self.tts_config = provider_manager.get_tts_config()
            self.tts_engine = ProviderFactory.create_tts_provider(self.tts_config['provider'], self.tts_config)
            print(f"[LOG] TTS Provider: {self.tts_config['provider']}")
            print("[LOG] Đọc video_id từ youtube.txt...")
            video_id = None
            try:
                with open("youtube.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            video_id = line
                            break
            except Exception as e:
                print(f"[ERROR] Không đọc được youtube.txt: {e}")
            
            # Khởi tạo YouTubeClient (optional, bỏ qua nếu lỗi)
            print(f"[LOG] Khởi tạo YouTubeClient với video_id: {video_id}")
            try:
                self.youtube_client = YouTubeClient(video_id=video_id)
                print("[LOG] YouTubeClient đã sẵn sàng!")
            except Exception as e:
                print(f"[WARNING] Không thể khởi tạo YouTubeClient: {e}")
                print("[INFO] Bỏ qua YouTube integration. Chỉ sử dụng Telegram hoặc các chức năng khác.")
                self.youtube_client = None
        except Exception as e:
            import traceback
            print(f"[ERROR] Lỗi khởi tạo module: {e}")
            traceback.print_exc()
            raise
        print("Tất cả modules đã sẵn sàng!")
        print("VTuber MeiLin đã sẵn sàng hoạt động!")

    def speak_with_fallback(self, text: str) -> bool:
        """Phát TTS với fallback tự động sang Edge TTS nếu lỗi"""
        try:
            success = self.tts_engine.speak(text)
            if success:
                return True
            
            # Nếu lỗi, thử fallback
            print(f"[WARNING] {self.tts_config['provider']} lỗi, chuyển sang fallback...")
            provider_manager = get_provider_manager()
            fallback_config = provider_manager.get_fallback_tts_config()
            
            if fallback_config:
                fallback_engine = ProviderFactory.create_tts_provider(
                    fallback_config['provider'], fallback_config
                )
                print(f"[INFO] Đang sử dụng fallback TTS: {fallback_config['provider']}")
                return fallback_engine.speak(text)
            
            return False
        except Exception as e:
            print(f"[ERROR] Lỗi TTS: {e}")
            return False
    
    def simulate_chat(self, message: str, username: str = "Tester"):
        """Xử lý tin nhắn và mô phỏng phản hồi TTS"""
        print(f"{username}: {message}")
        # Xử lý tin nhắn (truyền username vào)
        response = self.chat_processor.process_message(message, username)
        print(f"MeiLin: {response}")
        # Phát âm thanh với fallback
        if self.tts_active:
            self.speak_with_fallback(response)
        return response

    async def run_live_simulation(self):
        from modules.message_filter import MessageFilter
        from modules.story_generator import get_story_generator
        from modules.ambient_behavior import get_ambient_behavior
        
        print("\nBắt đầu mô phỏng livestream...")
        print("=" * 50)
        msg_filter = MessageFilter()
        msg_filter.set_start_timestamp()
        poll_count = 1
        
        # Story Generator cho Content Creator Mode
        story_generator = get_story_generator()
        idle_count = 0  # Đếm số lần polling không có tin nhắn
        IDLE_THRESHOLD = 3  # Sau 3 lần không có tin nhắn (30s) thì tạo content
        
        # Ambient Behavior System - Hành động tự nhiên
        ambient_behavior = get_ambient_behavior()
        ambient_count = 0  # Đếm số lần polling cho ambient
        AMBIENT_CHECK_INTERVAL = 6  # Check ambient mỗi 60s (6 x 10s polling)

        def listen_toggle():
            while True:
                keyboard.wait('ctrl+e')
                self.toggle_tts()
        
        def listen_mode_change():
            """Lắng nghe phím tắt để đổi personality mode"""
            modes = list(ambient_behavior.personality_modes.keys())
            mode_index = 0
            
            print("\n🎭 [Personality Modes] Phím tắt:")
            print("  Ctrl+M: Chuyển mode kế tiếp")
            print("  Ctrl+Shift+M: Hiển thị mode hiện tại")
            
            while True:
                event = keyboard.read_event(suppress=False)
                if event.event_type == 'down':
                    # Ctrl+M: Next mode
                    if event.name == 'm' and keyboard.is_pressed('ctrl') and not keyboard.is_pressed('shift'):
                        mode_index = (mode_index + 1) % len(modes)
                        new_mode = modes[mode_index]
                        ambient_behavior.set_personality_mode(new_mode)
                    
                    # Ctrl+Shift+M: Show current mode
                    elif event.name == 'm' and keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift'):
                        mode_info = ambient_behavior.get_current_mode()
                        print(f"\n🎭 [Current Mode] {mode_info['info']['name']}")
                        print(f"   {mode_info['info']['description']}")

        toggle_thread = threading.Thread(target=listen_toggle, daemon=True)
        toggle_thread.start()
        
        mode_thread = threading.Thread(target=listen_mode_change, daemon=True)
        mode_thread.start()

        try:
            # Kiểm tra YouTube client có sẵn không
            if self.youtube_client is None:
                print("[ERROR] YouTube client chưa được khởi tạo. Không thể chạy YouTube mode.")
                print("[INFO] Vui lòng setup OAuth credentials hoặc sử dụng Telegram bot.")
                return
            
            while True:
                print(f"\n--- Đang Polling chat lần {poll_count} ---")
                messages = await self.youtube_client.get_new_messages()
                filtered_msgs = msg_filter.filter_new_messages(messages, timestamp_key='timestamp', id_key='id')
                
                if not filtered_msgs:
                    print("Không có tin nhắn mới...")
                    idle_count += 1
                    ambient_count += 1
                    
                    # Ambient Behaviors: Hành động tự nhiên định kỳ
                    if ambient_count >= AMBIENT_CHECK_INTERVAL:
                        if ambient_behavior.should_trigger_ambient():
                            behavior = ambient_behavior.get_context_aware_behavior("idle")
                            if behavior:
                                print(f"\n🎭 [Ambient] MeiLin {behavior['name']}: {behavior['sound']}")
                                
                                # Phát TTS với sound effect
                                if self.tts_active:
                                    self.speak_with_fallback(behavior['sound'])
                        
                        ambient_count = 0  # Reset ambient counter
                    
                    # Content Creator Mode: Tạo story khi không có chat
                    if idle_count >= IDLE_THRESHOLD:
                        print("\n🎭 [Content Creator Mode] Tạo nội dung tự động...")
                        
                        # Chọn random content type
                        content_types = ['story', 'fun_fact', 'thought', 'trivia', 'advice']
                        content_type = content_types[poll_count % len(content_types)]
                        
                        # Tạo content
                        transition = story_generator.get_transition_phrase()
                        content = story_generator.generate_content(content_type, duration_minutes=2)
                        
                        full_message = f"{transition}\n\n{content}"
                        
                        print(f"\nMeiLin (Content Creator): {full_message}")
                        
                        # Phát TTS
                        if self.tts_active:
                            self.speak_with_fallback(full_message)
                        
                        # Reset idle counter
                        idle_count = 0
                    
                    await asyncio.sleep(10)
                    poll_count += 1
                    continue
                
                # Có tin nhắn mới - reset idle counter và ambient counter
                idle_count = 0
                ambient_count = 0
                short_msgs = [m for m in filtered_msgs if msg_filter.is_short_message(m)]
                if len(short_msgs) >= 3:
                    print("MeiLin: Chào các Anh/Chị ạ! Rất vui được gặp mọi người!")
                    if self.tts_active:
                        self.speak_with_fallback("Chào các Anh/Chị ạ! Rất vui được gặp mọi người!")
                    for m in short_msgs:
                        msg_filter.save_sample_message(m, self.chat_processor.chat_db)
                else:
                    for msg in filtered_msgs:
                        user_message = msg.get("message", "")
                        username = msg.get("username", "Người xem ẩn danh")
                        user_id = msg.get("user_id")  # Lấy user_id từ YouTube
                        print(f"\n{username}: {user_message}")
                        
                        # Đôi khi thêm ambient behavior trước khi trả lời (10% chance)
                        if ambient_behavior.should_trigger_ambient() and self.tts_active:
                            behavior = ambient_behavior.get_context_aware_behavior("active")
                            if behavior:
                                print(f"[Ambient] {behavior['sound']}")
                                self.speak_with_fallback(behavior['sound'])
                                await asyncio.sleep(0.5)  # Ngắt giữa ambient và response
                        
                        response = self.chat_processor.process_message(user_message, username, user_id=user_id)
                        print(f"MeiLin: {response}")
                        if self.tts_active:
                            self.speak_with_fallback(response)
                        if msg_filter.is_short_message(msg):
                            msg_filter.save_sample_message(msg, self.chat_processor.chat_db)
                        await asyncio.sleep(self.chat_processor.config['stream']['chat_delay'] if self.chat_processor.config.get('stream') else 3)
                await asyncio.sleep(10)
                poll_count += 1
        except KeyboardInterrupt:
            print("\nĐã dừng livestream MeiLin!")

def main():
    try:
        vtuber = AIVTuber()
    except Exception:
        print("\nKhông thể khởi tạo AI VTuber do lỗi module. Vui lòng kiểm tra lại cấu hình.")
        return

    print("\nBắt đầu livestream YouTube với MeiLin...")
    asyncio.run(vtuber.run_live_simulation())

if __name__ == "__main__":
    main()