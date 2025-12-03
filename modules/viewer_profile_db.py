"""
Viewer Profile Database - Lưu thông tin viewer theo user_id/channel_id
Persistent storage cho viewer title, gender, preferences
"""
import json
import os
from typing import Optional, Dict

class ViewerProfileDB:
    """Database để lưu profile của viewer theo user_id"""
    
    def __init__(self, db_path: str = "database/viewer_profiles.json"):
        self.db_path = db_path
        self.profiles = self._load_profiles()
        
        # Owner config
        self.owner_user_id = os.getenv('OWNER_USER_ID', 'UCJl9A4BK_KPOe5WqI1zlB_w')
    
    def _load_profiles(self) -> Dict:
        """Load profiles từ JSON file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ViewerProfileDB] Lỗi load profiles: {e}")
                return {}
        return {}
    
    def _save_profiles(self):
        """Save profiles vào JSON file"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ViewerProfileDB] Lỗi save profiles: {e}")
    
    def get_profile(self, user_id: str) -> Optional[Dict]:
        """Lấy profile của viewer theo user_id"""
        if not user_id:
            return None
        return self.profiles.get(user_id)
    
    def update_profile(self, user_id: str, username: str, viewer_title: str, 
                      gender: Optional[str] = None, preferences: Optional[list] = None,
                      age: Optional[int] = None):
        """
        Cập nhật hoặc tạo mới profile
        Args:
            user_id: YouTube Channel ID hoặc Telegram User ID
            username: Display name hiện tại
            viewer_title: Anh/Chị (detected hoặc confirmed)
            gender: male/female (optional)
            preferences: List sở thích (optional)
            age: Tuổi (optional)
        """
        if not user_id:
            return
        
        # Kiểm tra nếu là owner
        is_owner = (user_id == self.owner_user_id)
        
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                'user_id': user_id,
                'username': username,
                'viewer_title': viewer_title,
                'gender': gender,
                'preferences': preferences or [],
                'age': age,
                'is_owner': is_owner,
                'first_seen': None,
                'last_seen': None,
                'message_count': 0
            }
        else:
            # Update existing profile
            profile = self.profiles[user_id]
            profile['username'] = username  # Cập nhật username mới nhất
            profile['viewer_title'] = viewer_title
            
            if gender:
                profile['gender'] = gender
            if preferences:
                profile['preferences'] = preferences
            if age:
                profile['age'] = age
            
            profile['is_owner'] = is_owner
        
        # Update timestamps
        import datetime
        now = datetime.datetime.now().isoformat()
        if not self.profiles[user_id]['first_seen']:
            self.profiles[user_id]['first_seen'] = now
        self.profiles[user_id]['last_seen'] = now
        self.profiles[user_id]['message_count'] += 1
        
        self._save_profiles()
        print(f"[ViewerProfileDB] Updated profile for {username} ({user_id}): {viewer_title}")
    
    def confirm_gender(self, user_id: str, gender: str):
        """
        Xác nhận giới tính từ tin nhắn của viewer
        Args:
            user_id: User ID
            gender: 'male' hoặc 'female'
        """
        if user_id in self.profiles:
            self.profiles[user_id]['gender'] = gender
            # Cập nhật viewer_title dựa trên gender confirmed
            self.profiles[user_id]['viewer_title'] = 'Anh' if gender == 'male' else 'Chị'
            self._save_profiles()
            print(f"[ViewerProfileDB] Confirmed gender for {user_id}: {gender} → {self.profiles[user_id]['viewer_title']}")
    
    def is_owner(self, user_id: str) -> bool:
        """Kiểm tra xem user_id có phải owner không"""
        return user_id == self.owner_user_id
    
    def get_viewer_title(self, user_id: str, username: str = None) -> str:
        """
        Lấy viewer_title từ profile (ưu tiên) hoặc detect mới
        Args:
            user_id: User ID (primary key)
            username: Display name (fallback nếu chưa có profile)
        Returns:
            'Anh' hoặc 'Chị'
        """
        # Nếu có profile, dùng viewer_title đã lưu
        profile = self.get_profile(user_id)
        if profile:
            return profile['viewer_title']
        
        # Nếu không có profile, detect từ username (legacy)
        return self._detect_title_from_username(username)
    
    def _detect_title_from_username(self, username: str) -> str:
        """
        Detect viewer_title từ username (fallback)
        Chỉ dùng khi chưa có profile
        """
        if not username:
            return "Anh"
        
        normalized_name = username.lower().replace(" ", "")
        
        # Từ khóa nữ
        female_keywords = ['linh', 'trang', 'ngan', 'huyen', 'chi', 'thao', 'ngoc', 'yen', 'nu', 'girl', 'my', 'loan']
        
        # Từ khóa nam
        male_keywords = ['anh', 'tung', 'hoang', 'duy', 'hung', 'minh', 'nam', 'boy', 'mr', 'quan', 
                        'long', 'tuan', 'son', 'dinh', 'cong', 'duc', 'dat', 'khang', 'kien', 'phong', 'cuong']
        
        for keyword in female_keywords:
            if keyword in normalized_name:
                return "Chị"
        
        for keyword in male_keywords:
            if keyword in normalized_name:
                return "Anh"
        
        return "Anh"  # Mặc định

# Singleton instance
_viewer_profile_db = None

def get_viewer_profile_db() -> ViewerProfileDB:
    """Lấy singleton instance của ViewerProfileDB"""
    global _viewer_profile_db
    if _viewer_profile_db is None:
        _viewer_profile_db = ViewerProfileDB()
    return _viewer_profile_db
