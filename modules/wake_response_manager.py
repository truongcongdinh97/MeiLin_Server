"""
Wake Response Manager
Quản lý các câu trả lời wake word pre-generated với time-based, mood-based, context-aware selection
"""
import json
import random
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import deque

class WakeResponseManager:
    """Quản lý wake word responses với smart selection"""
    
    def __init__(self, config_path: str = "config/wake_responses.json"):
        """
        Initialize Wake Response Manager
        
        Args:
            config_path: Đường dẫn đến file config
        """
        self.config_path = config_path
        self.responses = []
        self.settings = {}
        self.time_ranges = {}
        self.mood_keywords = {}
        self.context_rules = {}
        
        self.usage_stats = {}  # Track usage frequency
        self.last_used_index = -1  # Tránh lặp lại liên tiếp
        self.last_wake_time = None  # Track last wake time
        self.wake_history = deque(maxlen=10)  # Recent wake events
        self.current_mood = "neutral"  # Track current mood
        self.mood_last_updated = None
        self.context_state = "normal"  # Current context
        self.boot_time = datetime.now()
        self.first_wake_done = False
        self.error_count = 0
        self.success_count = 0
        
        self._load_config()
        self._verify_audio_files()
    
    def _load_config(self):
        """Load config từ JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.responses = config.get('wake_responses', [])
                self.settings = config.get('settings', {})
                self.time_ranges = config.get('time_ranges', {})
                self.mood_keywords = config.get('mood_keywords', {})
                self.context_rules = config.get('context_rules', {})
            
            # Initialize usage stats
            for response in self.responses:
                self.usage_stats[response['id']] = {
                    'count': 0,
                    'last_used': None,
                    'context_used': []
                }
            
            print(f"[WakeResponseManager] Loaded {len(self.responses)} wake responses")
            print(f"   Time-based: {'✓' if self.settings.get('enable_time_based') else '✗'}")
            print(f"   Mood-based: {'✓' if self.settings.get('enable_mood_based') else '✗'}")
            print(f"   Context-aware: {'✓' if self.settings.get('enable_context_aware') else '✗'}")
        except Exception as e:
            print(f"[WakeResponseManager] Error loading config: {e}")
            self.responses = []
            self.settings = {}
    
    def _verify_audio_files(self):
        """Kiểm tra xem audio files đã tồn tại chưa"""
        cache_dir = Path(self.settings.get('cache_directory', 'static/wake_responses'))
        
        missing_files = []
        existing_count = 0
        
        for response in self.responses:
            audio_path = cache_dir / response['filename']
            if audio_path.exists():
                existing_count += 1
            else:
                missing_files.append(response['filename'])
        
        if missing_files:
            print(f"[WakeResponseManager] ⚠️ Missing {len(missing_files)} audio files")
            print(f"   Run scripts/generate_wake_audio.py to generate them")
        else:
            print(f"[WakeResponseManager] ✅ All {existing_count} audio files available")
    
    def _get_time_of_day(self) -> str:
        """Xác định time of day hiện tại"""
        hour = datetime.now().hour
        
        for period, (start, end) in self.time_ranges.items():
            if start <= end:
                if start <= hour < end:
                    return period
            else:  # night period crosses midnight
                if hour >= start or hour < end:
                    return period
        
        return "any"
    
    def _detect_context(self, confidence: float = None) -> str:
        """Detect context dựa trên lịch sử và state"""
        now = datetime.now()
        
        # First wake after boot
        if not self.first_wake_done:
            return "first_wake"
        
        # After error
        if self.error_count > 0:
            self.error_count = 0  # Reset
            return "after_error"
        
        # After success
        if self.success_count > 0:
            self.success_count = 0
            return "after_success"
        
        # Repeated wake (< 2 minutes)
        if self.last_wake_time:
            time_since_last = (now - self.last_wake_time).total_seconds()
            if time_since_last < 120:  # 2 minutes
                return "repeated"
        
        # After silence (> 30 minutes)
        if self.last_wake_time:
            time_since_last = (now - self.last_wake_time).total_seconds()
            if time_since_last > 1800:  # 30 minutes
                return "after_silence"
        
        # Urgent (high confidence or frequent)
        if confidence and confidence > 0.9:
            return "urgent"
        
        # Late night
        if self._get_time_of_day() == "night":
            return "late_night"
        
        return "normal"
    
    def _update_mood(self, message: str = None):
        """Update mood dựa trên message hoặc decay theo thời gian"""
        now = datetime.now()
        
        # Mood decay
        if self.mood_last_updated:
            minutes_passed = (now - self.mood_last_updated).total_seconds() / 60
            decay_minutes = self.settings.get('mood_decay_minutes', 30)
            
            if minutes_passed > decay_minutes:
                self.current_mood = "neutral"
                self.mood_last_updated = now
                return
        
        # Detect mood from message
        if message:
            message_lower = message.lower()
            for mood, keywords in self.mood_keywords.items():
                if any(kw in message_lower for kw in keywords):
                    self.current_mood = mood
                    self.mood_last_updated = now
                    return
    
    def _filter_by_criteria(self, responses: List[Dict], 
                           time_of_day: str, 
                           mood: str, 
                           context: str) -> List[Dict]:
        """Filter responses dựa trên criteria"""
        filtered = []
        
        for r in responses:
            # Check time
            if self.settings.get('enable_time_based', True):
                if "any" not in r.get('time_of_day', ['any']):
                    if time_of_day not in r.get('time_of_day', []):
                        continue
            
            # Check mood
            if self.settings.get('enable_mood_based', True):
                if mood not in r.get('mood', ['neutral']):
                    continue
            
            # Check context
            if self.settings.get('enable_context_aware', True):
                if context not in r.get('context', ['normal']):
                    continue
            
            filtered.append(r)
        
        return filtered
    
    def get_response(self, mode: Optional[str] = None, 
                    confidence: float = None,
                    user_message: str = None) -> Optional[Dict]:
        """
        Lấy một wake response với smart selection
        
        Args:
            mode: Selection mode override
            confidence: Wake confidence (0-1)
            user_message: Last user message for mood detection
        
        Returns:
            Dict với keys: id, text, emotion, filename, audio_url, context, mood
        """
        if not self.responses:
            return None
        
        # Detect current state
        time_of_day = self._get_time_of_day()
        context = self._detect_context(confidence)
        self._update_mood(user_message)
        mood = self.current_mood
        
        # Filter responses by criteria
        candidates = self._filter_by_criteria(
            self.responses, time_of_day, mood, context
        )
        
        # Fallback if no candidates
        if not candidates:
            # Try with relaxed context
            candidates = self._filter_by_criteria(
                self.responses, time_of_day, mood, "normal"
            )
        
        if not candidates:
            # Try with only time filter
            candidates = [r for r in self.responses 
                         if "any" in r.get('time_of_day', ['any']) 
                         or time_of_day in r.get('time_of_day', [])]
        
        if not candidates:
            candidates = self.responses  # Last resort
        
        # Selection algorithm
        selection_mode = mode or self.settings.get('selection_mode', 'smart')
        
        if selection_mode == 'smart' or selection_mode == 'weighted':
            # Smart weighted selection
            weights = []
            for r in candidates:
                count = self.usage_stats[r['id']]['count']
                weight = 1.0 / (count + 1)  # Less used = higher weight
                
                # Boost weight for perfect context match
                if context in r.get('context', []):
                    weight *= 1.5
                
                weights.append(weight)
            
            selected = random.choices(candidates, weights=weights, k=1)[0]
        
        elif selection_mode == 'random':
            selected = random.choice(candidates)
        
        else:
            selected = random.choice(candidates)
        
        # Update stats
        if self.settings.get('enable_tracking', True):
            self.usage_stats[selected['id']]['count'] += 1
            self.usage_stats[selected['id']]['last_used'] = datetime.now().isoformat()
            self.usage_stats[selected['id']]['context_used'].append(context)
        
        # Update state
        self.last_wake_time = datetime.now()
        self.wake_history.append({
            'time': datetime.now().isoformat(),
            'response_id': selected['id'],
            'context': context,
            'mood': mood,
            'time_of_day': time_of_day
        })
        self.first_wake_done = True
        
        # Build audio URL
        cache_dir = self.settings.get('cache_directory', 'static/wake_responses')
        audio_url = f"/{cache_dir}/{selected['filename']}"
        
        return {
            'id': selected['id'],
            'text': selected['text'],
            'emotion': selected['emotion'],
            'filename': selected['filename'],
            'audio_url': audio_url,
            'context': context,
            'mood': mood,
            'time_of_day': time_of_day
        }
    
    def get_all_responses(self) -> List[Dict]:
        """Lấy tất cả wake responses"""
        return self.responses
    
    def get_usage_stats(self) -> Dict:
        """Lấy thống kê sử dụng"""
        return self.usage_stats
    
    def reset_stats(self):
        """Reset usage statistics"""
        for response in self.responses:
            self.usage_stats[response['id']] = {
                'count': 0,
                'last_used': None
            }
        print("[WakeResponseManager] Usage stats reset")
    
    def get_response_by_emotion(self, emotion: str) -> Optional[Dict]:
        """
        Lấy response theo emotion cụ thể
        
        Args:
            emotion: Emotion type (polite, friendly, excited, etc.)
        
        Returns:
            Random response matching the emotion
        """
        matching = [r for r in self.responses if r.get('emotion') == emotion]
        if not matching:
            return self.get_response()  # Fallback to any response
        
        selected = random.choice(matching)
        
        # Update stats
        if self.settings.get('enable_tracking', True):
            self.usage_stats[selected['id']]['count'] += 1
            self.usage_stats[selected['id']]['last_used'] = datetime.now().isoformat()
        
        # Build audio URL
        cache_dir = self.settings.get('cache_directory', 'static/wake_responses')
        audio_url = f"/{cache_dir}/{selected['filename']}"
        
        return {
            'id': selected['id'],
            'text': selected['text'],
            'emotion': selected['emotion'],
            'filename': selected['filename'],
            'audio_url': audio_url
        }
    
    def set_mood(self, mood: str):
        """Manually set mood"""
        self.current_mood = mood
        self.mood_last_updated = datetime.now()
        print(f"[WakeResponseManager] Mood set to: {mood}")
    
    def report_error(self):
        """Report error để ảnh hưởng response selection"""
        self.error_count += 1
        print(f"[WakeResponseManager] Error reported, count: {self.error_count}")
    
    def report_success(self):
        """Report success để ảnh hưởng response selection"""
        self.success_count += 1
        print(f"[WakeResponseManager] Success reported, count: {self.success_count}")
    
    def get_state(self) -> Dict:
        """Get current state"""
        return {
            'current_mood': self.current_mood,
            'mood_last_updated': self.mood_last_updated.isoformat() if self.mood_last_updated else None,
            'context_state': self.context_state,
            'first_wake_done': self.first_wake_done,
            'time_of_day': self._get_time_of_day(),
            'last_wake_time': self.last_wake_time.isoformat() if self.last_wake_time else None,
            'wake_count': len(self.wake_history),
            'error_count': self.error_count,
            'success_count': self.success_count
        }
    
    def get_wake_history(self, limit: int = 10) -> List[Dict]:
        """Get recent wake history"""
        return list(self.wake_history)[-limit:]

# Singleton instance
_wake_manager_instance = None

def get_wake_response_manager() -> WakeResponseManager:
    """Get singleton instance"""
    global _wake_manager_instance
    if _wake_manager_instance is None:
        _wake_manager_instance = WakeResponseManager()
    return _wake_manager_instance


if __name__ == "__main__":
    # Test
    print("Testing WakeResponseManager...")
    
    manager = WakeResponseManager()
    
    print("\n📊 Testing response selection:")
    for i in range(5):
        response = manager.get_response()
        if response:
            print(f"  {i+1}. [{response['emotion']}] {response['text']} → {response['audio_url']}")
    
    print("\n😊 Testing emotion-based selection:")
    emotions = ['polite', 'excited', 'friendly']
    for emotion in emotions:
        response = manager.get_response_by_emotion(emotion)
        if response:
            print(f"  [{emotion}] → {response['text']}")
    
    print("\n📈 Usage Statistics:")
    stats = manager.get_usage_stats()
    for response_id, stat in sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)[:5]:
        print(f"  {response_id}: {stat['count']} times")
