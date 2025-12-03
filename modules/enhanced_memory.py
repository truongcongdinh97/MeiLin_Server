"""
Enhanced Memory System - Long-term memory xuyên suốt sessions
Hỗ trợ persistent conversation context và user profiles
"""

import json
import os
import pickle
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import sqlite3
from collections import defaultdict

class EnhancedMemory:
    """
    Hệ thống memory nâng cao với long-term storage
    Lưu trữ conversation context, user profiles, và semantic memories
    """
    
    def __init__(self, db_path: str = "database/enhanced_memory.db"):
        self.db_path = db_path
        self._init_database()
        
        # Cache để tăng performance
        self.user_cache = {}
        self.conversation_cache = {}
        
    def _init_database(self):
        """Khởi tạo database schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bảng user profiles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                preferences TEXT,
                conversation_style TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng conversation history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message TEXT,
                response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_hash TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')
        
        # Bảng semantic memories (key-value storage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_memories (
                memory_key TEXT PRIMARY KEY,
                memory_value TEXT,
                memory_type TEXT,
                user_id TEXT,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')
        
        # Bảng conversation context
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_context (
                context_id TEXT PRIMARY KEY,
                user_id TEXT,
                context_data TEXT,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')
        
        # Indexes để tăng performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_history ON conversation_history(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_user ON semantic_memories(user_id, memory_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_user ON conversation_context(user_id)')
        
        conn.commit()
        conn.close()
    
    def save_conversation_context(self, user_id: str, context: Dict) -> bool:
        """
        Lưu conversation context để tiếp tục sau này
        """
        try:
            context_id = f"{user_id}_{hash(str(context))}"
            context_data = json.dumps(context, ensure_ascii=False)
            
            # Context tồn tại trong 7 ngày
            expires_at = datetime.now() + timedelta(days=7)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversation_context 
                (context_id, user_id, context_data, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (context_id, user_id, context_data, expires_at))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.conversation_cache[context_id] = context
            
            return True
            
        except Exception as e:
            print(f"Lỗi khi lưu conversation context: {e}")
            return False
    
    def load_conversation_context(self, user_id: str, days: int = 7) -> Dict:
        """
        Load conversation context từ database
        Trả về context trong vòng số ngày chỉ định
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT context_data FROM conversation_context
                WHERE user_id = ? AND last_accessed >= ?
                ORDER BY last_accessed DESC
                LIMIT 1
            ''', (user_id, cutoff_date))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                context_data = json.loads(result[0])
                
                # Update last accessed time
                self._update_context_access(user_id)
                
                return context_data
            else:
                return {}
                
        except Exception as e:
            print(f"Lỗi khi load conversation context: {e}")
            return {}
    
    def _update_context_access(self, user_id: str):
        """Cập nhật thời gian truy cập context"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE conversation_context 
                SET last_accessed = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Lỗi khi update context access: {e}")
    
    def get_long_term_memory(self, user_id: str, days: int = 7) -> List[Dict]:
        """
        Lấy long-term memory từ database
        Trả về các cuộc hội thoại trong vòng số ngày chỉ định
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message, response, timestamp 
                FROM conversation_history
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (user_id, cutoff_date))
            
            results = cursor.fetchall()
            conn.close()
            
            memories = []
            for message, response, timestamp in results:
                memories.append({
                    'message': message,
                    'response': response,
                    'timestamp': timestamp,
                    'days_ago': (datetime.now() - datetime.fromisoformat(timestamp)).days
                })
            
            return memories
            
        except Exception as e:
            print(f"Lỗi khi lấy long-term memory: {e}")
            return []
    
    def add_conversation_memory(self, user_id: str, username: str, 
                              user_message: str, ai_response: str,
                              preferences: Dict = None) -> bool:
        """
        Thêm memory cho cuộc hội thoại hiện tại
        """
        try:
            # Tạo hoặc update user profile
            self._update_user_profile(user_id, username, preferences)
            
            # Lưu conversation history
            context_hash = self._generate_context_hash(user_message, ai_response)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversation_history 
                (user_id, message, response, context_hash)
                VALUES (?, ?, ?, ?)
            ''', (user_id, user_message, ai_response, context_hash))
            
            conn.commit()
            conn.close()
            
            # Extract và lưu semantic memories
            self._extract_semantic_memories(user_id, user_message, ai_response)
            
            return True
            
        except Exception as e:
            print(f"Lỗi khi thêm conversation memory: {e}")
            return False
    
    def _update_user_profile(self, user_id: str, username: str, preferences: Dict = None):
        """Cập nhật user profile"""
        try:
            preferences_json = json.dumps(preferences or {}, ensure_ascii=False)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, username, preferences, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, preferences_json))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.user_cache[user_id] = {
                'username': username,
                'preferences': preferences or {}
            }
            
        except Exception as e:
            print(f"Lỗi khi update user profile: {e}")
    
    def _extract_semantic_memories(self, user_id: str, user_message: str, ai_response: str):
        """Trích xuất và lưu semantic memories từ conversation"""
        try:
            import re  # Thêm import re
            # Phân tích user message để tìm thông tin quan trọng
            important_info = self._analyze_for_important_info(user_message, ai_response)
            
            if important_info:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for memory_key, memory_value in important_info.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO semantic_memories 
                        (memory_key, memory_value, memory_type, user_id, accessed_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (memory_key, memory_value, 'user_preference', user_id))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"Lỗi khi extract semantic memories: {e}")
    
    def _analyze_for_important_info(self, user_message: str, ai_response: str) -> Dict:
        """Phân tích conversation để tìm thông tin quan trọng"""
        important_info = {}
        
        # Tìm thông tin cá nhân (tên, tuổi, sở thích, etc.)
        personal_patterns = {
            'tên': r'tên\s+(?:tôi\s+là|tôi\s+tên|là)\s+([^\s,.!?]+)',
            'tuổi': r'tuổi\s+(?:tôi\s+là|tôi\s+)\s*(\d+)',
            'thích': r'(?:thích|yêu thích)\s+([^.!?]+)',
            'ghét': r'(?:ghét|không thích)\s+([^.!?]+)',
        }
        
        for key, pattern in personal_patterns.items():
            matches = re.findall(pattern, user_message.lower())
            if matches:
                important_info[key] = matches[0]
        
        # Tìm preferences từ AI response
        if "thích" in ai_response.lower() or "prefer" in ai_response.lower():
            # Extract preferences từ response
            preference_matches = re.findall(r'(\w+)\s+(?:này|đó)', ai_response)
            if preference_matches:
                important_info['preferences'] = ', '.join(preference_matches)
        
        return important_info
    
    def _generate_context_hash(self, user_message: str, ai_response: str) -> str:
        """Tạo hash để nhận diện context tương tự"""
        context_text = f"{user_message} {ai_response}"
        return hashlib.md5(context_text.encode()).hexdigest()
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Lấy thông tin user profile"""
        # Kiểm tra cache trước
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, preferences FROM user_profiles
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                username, preferences_json = result
                preferences = json.loads(preferences_json) if preferences_json else {}
                
                profile = {
                    'username': username,
                    'preferences': preferences
                }
                
                # Lưu cache
                self.user_cache[user_id] = profile
                return profile
            else:
                return {}
                
        except Exception as e:
            print(f"Lỗi khi lấy user profile: {e}")
            return {}
    
    def get_semantic_memories(self, user_id: str, memory_type: str = None) -> List[Dict]:
        """Lấy semantic memories của user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if memory_type:
                cursor.execute('''
                    SELECT memory_key, memory_value, memory_type, importance
                    FROM semantic_memories
                    WHERE user_id = ? AND memory_type = ?
                    ORDER BY importance DESC, accessed_at DESC
                ''', (user_id, memory_type))
            else:
                cursor.execute('''
                    SELECT memory_key, memory_value, memory_type, importance
                    FROM semantic_memories
                    WHERE user_id = ?
                    ORDER BY importance DESC, accessed_at DESC
                    LIMIT 20
                ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            memories = []
            for memory_key, memory_value, mem_type, importance in results:
                memories.append({
                    'key': memory_key,
                    'value': memory_value,
                    'type': mem_type,
                    'importance': importance
                })
            
            return memories
            
        except Exception as e:
            print(f"Lỗi khi lấy semantic memories: {e}")
            return []
    
    def build_context_summary(self, user_id: str, days: int = 7) -> str:
        """
        Xây dựng summary của context để sử dụng trong prompt
        """
        try:
            # Lấy long-term memory
            memories = self.get_long_term_memory(user_id, days)
            
            # Lấy semantic memories
            semantic_memories = self.get_semantic_memories(user_id)
            
            # Lấy user profile
            user_profile = self.get_user_profile(user_id)
            
            # Xây dựng summary
            summary_parts = []
            
            # User profile
            if user_profile:
                summary_parts.append(f"THÔNG TIN USER:")
                summary_parts.append(f"- Username: {user_profile.get('username', 'Unknown')}")
                if user_profile.get('preferences'):
                    prefs = user_profile['preferences']
                    if isinstance(prefs, dict):
                        for key, value in prefs.items():
                            summary_parts.append(f"- {key}: {value}")
            
            # Semantic memories
            if semantic_memories:
                summary_parts.append("\nTHÔNG TIN QUAN TRỌNG:")
                for memory in semantic_memories[:5]:  # Lấy 5 memories quan trọng nhất
                    summary_parts.append(f"- {memory['key']}: {memory['value']}")
            
            # Recent conversations
            if memories:
                summary_parts.append("\nLỊCH SỬ GẦN ĐÂY:")
                for i, memory in enumerate(memories[:3]):  # Lấy 3 conversations gần nhất
                    days_ago = memory.get('days_ago', 0)
                    time_desc = "hôm nay" if days_ago == 0 else f"{days_ago} ngày trước"
                    
                    summary_parts.append(f"\n{time_desc}:")
                    summary_parts.append(f"User: {memory['message']}")
                    summary_parts.append(f"AI: {memory['response']}")
            
            return "\n".join(summary_parts) if summary_parts else "Không có context history."
            
        except Exception as e:
            print(f"Lỗi khi build context summary: {e}")
            return "Không thể load context history."
    
    def cleanup_old_data(self, days: int = 30):
        """Dọn dẹp dữ liệu cũ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Xóa conversation history cũ
            cursor.execute('''
                DELETE FROM conversation_history 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            # Xóa expired context
            cursor.execute('''
                DELETE FROM conversation_context 
                WHERE expires_at < CURRENT_TIMESTAMP
            ''')
            
            # Xóa semantic memories ít quan trọng và lâu không dùng
            cursor.execute('''
                DELETE FROM semantic_memories 
                WHERE importance < 2 AND accessed_at < ?
            ''', (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            print(f"Đã dọn dẹp dữ liệu cũ hơn {days} ngày")
            
        except Exception as e:
            print(f"Lỗi khi cleanup old data: {e}")
    
    def get_memory_stats(self) -> Dict:
        """Lấy thống kê về memory system"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Đếm user profiles
            cursor.execute('SELECT COUNT(*) FROM user_profiles')
            stats['total_users'] = cursor.fetchone()[0]
            
            # Đếm conversation history
            cursor.execute('SELECT COUNT(*) FROM conversation_history')
            stats['total_conversations'] = cursor.fetchone()[0]
            
            # Đếm semantic memories
            cursor.execute('SELECT COUNT(*) FROM semantic_memories')
            stats['total_memories'] = cursor.fetchone()[0]
            
            # Đếm active context
            cursor.execute('SELECT COUNT(*) FROM conversation_context WHERE expires_at > CURRENT_TIMESTAMP')
            stats['active_contexts'] = cursor.fetchone()[0]
            
            conn.close()
            return stats
            
        except Exception as e:
            print(f"Lỗi khi lấy memory stats: {e}")
            return {}


# Factory function
def get_enhanced_memory(db_path: str = "database/enhanced_memory.db"):
    """Factory function để tạo EnhancedMemory"""
    return EnhancedMemory(db_path=db_path)


# Test the module
if __name__ == "__main__":
    memory = EnhancedMemory()
