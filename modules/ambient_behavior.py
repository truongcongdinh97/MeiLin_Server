"""
Ambient Behavior System - MeiLin tự động thực hiện các hành động tự nhiên
Tạo cảm giác như người thật: thở dài, cười, ho, ngáp, hừm, v.v.
+ Idle/Sleep responses với pre-generated audio
"""
import random
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class AmbientBehavior:
    """Quản lý các hành động tự nhiên/ambient của MeiLin"""
    
    def __init__(self):
        # Danh sách behaviors với tần suất và âm thanh
        self.behaviors = {
            "sigh": {
                "name": "thở dài",
                "sounds": ["Haaaa~", "Phù~", "Hơi mệt nè~"],
                "text": [
                    "*thở dài nhẹ* Haaa~",
                    "*thở phào* Phù, hơi mệt nè~",
                    "*thở ra nhẹ nhàng* Hmm~"
                ],
                "weight": 2,  # Độ ưu tiên (càng cao càng hay xảy ra)
                "min_interval": 180  # Tối thiểu 3 phút giữa các lần
            },
            "giggle": {
                "name": "cười khúc khích",
                "sounds": ["Hehe~", "Hihi~", "Hihihi~", "*cười khúc khích*"],
                "text": [
                    "*cười khúc khích* Hehe, em vừa nghĩ ra điều gì đó vui~",
                    "*cười nhẹ* Hihi, thật thú vị~",
                    "*mỉm cười* Hehe, đáng yêu quá~"
                ],
                "weight": 3,
                "min_interval": 120
            },
            "cough": {
                "name": "ho nhẹ",
                "sounds": ["*khẽ ho* Khò khò~", "Khẹc khẹc~"],
                "text": [
                    "*ho nhẹ* Khò khò~ Xin lỗi nha~",
                    "*khẽ ho* Uh, throat a bit dry~",
                    "*ho khẽ* Khẹc, hơi khô họng~"
                ],
                "weight": 1,
                "min_interval": 300  # 5 phút
            },
            "yawn": {
                "name": "ngáp",
                "sounds": ["*ngáp* Haa~", "Hơaaa~"],
                "text": [
                    "*ngáp ngái* Haa~ Hơi buồn ngủ chút nè~",
                    "*ngáp* Hoaaa~ Em mệt rồi~",
                    "*ngáp nhẹ* Hmm, hơi lười nè~"
                ],
                "weight": 1,
                "min_interval": 360  # 6 phút
            },
            "hum": {
                "name": "nghĩ ngợi",
                "sounds": ["Hmm~", "Uh~", "Nhỉ~"],
                "text": [
                    "*nghĩ ngợi* Hmm~ Em đang suy nghĩ~",
                    "*gật đầu* Uh huh~ Hiểu rồi~",
                    "*suy tư* Hmm, để xem nào~"
                ],
                "weight": 4,
                "min_interval": 90  # 1.5 phút
            },
            "stretch": {
                "name": "duỗi người",
                "sounds": ["*duỗi người* Hmm~"],
                "text": [
                    "*duỗi tay* Aaah~ Ngồi lâu mỏi lưng quá~",
                    "*duỗi người* Hmm~ Thư giãn chút nào~",
                    "*vươn vai* Phù, cần nghỉ tí~"
                ],
                "weight": 1,
                "min_interval": 240  # 4 phút
            },
            "clear_throat": {
                "name": "khẽ hừm",
                "sounds": ["*khẽ hừm* Hmm~", "A hem~"],
                "text": [
                    "*khẽ hừm* Hmm, để em nói gì nhỉ~",
                    "*hừm* À phải~",
                    "*khẽ khan* A hem~"
                ],
                "weight": 3,
                "min_interval": 120
            },
            "excitement": {
                "name": "phấn khích",
                "sounds": ["Waa~", "Ồ~", "Ố ồ~"],
                "text": [
                    "*phấn khích* Waa! Hay quá~",
                    "*hào hứng* Ố ồ! Thú vị ghê~",
                    "*excited* Ôi! Em thích cái này~"
                ],
                "weight": 2,
                "min_interval": 180
            },
            "thinking": {
                "name": "suy nghĩ sâu",
                "sounds": ["Ừm~", "Mhm~"],
                "text": [
                    "*nghiêm túc* Ừm, để em suy nghĩ~",
                    "*trầm tư* Mhm, thật sự thì~",
                    "*chăm chú* Hmm, điều này~"
                ],
                "weight": 3,
                "min_interval": 150
            },
            "surprise": {
                "name": "ngạc nhiên",
                "sounds": ["Ồ!", "Ơ!", "Hử?"],
                "text": [
                    "*ngạc nhiên* Ồ! Không ngờ~",
                    "*bất ngờ* Ơ! Thật sao~",
                    "*surprise* Hử? Vậy à~"
                ],
                "weight": 2,
                "min_interval": 200
            },
            "whistle": {
                "name": "huýt sáo",
                "sounds": ["*huýt sáo* ♪~", "Fiu fiu~", "*whistle* ♫~"],
                "text": [
                    "*huýt sáo vui vẻ* ♪~ Lalala~",
                    "*whistle* Fiu fiu~ Mood tốt quá~",
                    "*huýt sáo nhẹ nhàng* ♫~"
                ],
                "weight": 2,
                "min_interval": 240
            },
            "humming": {
                "name": "ngâm nga",
                "sounds": ["♪~ Hmm hmm~", "La la la~", "♫~ Na na na~"],
                "text": [
                    "*ngâm nga* ♪~ Hmm hmm hmm~",
                    "*hát nhỏ* La la la~ ♫",
                    "*humming* ♪~ Na na na na~"
                ],
                "weight": 3,
                "min_interval": 180
            },
            "sniff": {
                "name": "hít mũi",
                "sounds": ["*sniff*", "*hít mũi*"],
                "text": [
                    "*hít mũi* Sniff~ Có mùi gì đó~",
                    "*sniff sniff* Uh, mùi gì vậy~",
                    "*hít hít* Hmm~"
                ],
                "weight": 1,
                "min_interval": 300
            },
            "murmur": {
                "name": "lẩm bẩm",
                "sounds": ["*lẩm bẩm*", "*thì thầm*"],
                "text": [
                    "*lẩm bẩm* Để xem... hmm...",
                    "*tự nhủ* Uh huh, vậy là...",
                    "*murmur* Hmm... thế nào nhỉ..."
                ],
                "weight": 3,
                "min_interval": 150
            },
            "gasp": {
                "name": "há hốc",
                "sounds": ["*há hốc* Ohhh!", "*gasp*"],
                "text": [
                    "*há hốc mồm* Ohhh! Wow!",
                    "*gasp* Không thể tin được!",
                    "*shocked* Trời ơi!"
                ],
                "weight": 1,
                "min_interval": 250
            },
            "chuckle": {
                "name": "cười khẩy",
                "sounds": ["*cười khẩy* Heh~", "Heh heh~"],
                "text": [
                    "*cười khẩy* Heh~ Vui nhỉ~",
                    "*chuckle* Heh heh, hay đấy~",
                    "*grin* Hehe, thú vị~"
                ],
                "weight": 3,
                "min_interval": 120
            },
            "pout": {
                "name": "bĩu môi",
                "sounds": ["*bĩu môi* Hmph~", "Mou~"],
                "text": [
                    "*bĩu môi* Hmph~ Không vui~",
                    "*pout* Mou~ Buồn quá~",
                    "*ngậm ngùi* Ưm... chán thật~"
                ],
                "weight": 1,
                "min_interval": 240
            },
            "sniffle": {
                "name": "thút thít",
                "sounds": ["*thút thít*", "*sniff sniff*"],
                "text": [
                    "*thút thít* Sniff sniff~ Buồn quá~",
                    "*sniffle* Huhu~ Sad~",
                    "*sụt sùi* Ưm ưm~"
                ],
                "weight": 1,
                "min_interval": 360
            },
            "groan": {
                "name": "rên rỉ",
                "sounds": ["*rên* Uhhh~", "Ugh~"],
                "text": [
                    "*rên rỉ* Uhhh~ Mệt quá~",
                    "*groan* Ugh~ Không thể nào~",
                    "*kêu ca* Ahhh~ Khó quá~"
                ],
                "weight": 1,
                "min_interval": 240
            },
            "cheerful": {
                "name": "vui vẻ",
                "sounds": ["Yay~!", "Woohoo~!", "Yatta~!"],
                "text": [
                    "*vui vẻ* Yay~! Tuyệt vời!",
                    "*cheerful* Woohoo~! Vui quá!",
                    "*hào hứng* Yatta~! Làm được rồi!"
                ],
                "weight": 2,
                "min_interval": 200
            },
            "nervous": {
                "name": "lo lắng",
                "sounds": ["*lo lắng* Uh oh...", "Ehehe..."],
                "text": [
                    "*lo lắng* Uh oh... Không tốt lắm~",
                    "*nervous laugh* Ehehe... Hơi sợ~",
                    "*hồi hộp* Um um...걱정돼~"
                ],
                "weight": 1,
                "min_interval": 240
            },
            "determined": {
                "name": "quyết tâm",
                "sounds": ["*quyết tâm* Yosh!", "Ganbarou!"],
                "text": [
                    "*quyết tâm* Yosh! Cố lên!",
                    "*determined* Ganbarou! Làm thôi!",
                    "*fighting* Uju uju! Fighting!"
                ],
                "weight": 2,
                "min_interval": 240
            },
            "sleepy": {
                "name": "buồn ngủ",
                "sounds": ["*buồn ngủ* Zzzz~", "Fuah~"],
                "text": [
                    "*buồn ngủ* Zzzz~ Ngủ nướng~",
                    "*sleepy* Fuah~ Khó mở mắt~",
                    "*drowsy* Muon ngu qua~"
                ],
                "weight": 1,
                "min_interval": 300
            },
            "confused": {
                "name": "bối rối",
                "sounds": ["Eh?", "Nani?", "Huh?"],
                "text": [
                    "*bối rối* Eh? Sao vậy?",
                    "*confused* Nani? Gì cơ?",
                    "*puzzled* Huh? Không hiểu~"
                ],
                "weight": 2,
                "min_interval": 180
            },
            "satisfied": {
                "name": "hài lòng",
                "sounds": ["*hài lòng* Ahh~", "Nice~"],
                "text": [
                    "*hài lòng* Ahh~ Tốt rồi~",
                    "*satisfied* Nice~ Perfect!",
                    "*content* Ưm~ Vừa ý~"
                ],
                "weight": 2,
                "min_interval": 200
            },
            "playful": {
                "name": "tinh nghịch",
                "sounds": ["Tehe~", "Ehehe~", "Nyan~"],
                "text": [
                    "*tinh nghịch* Tehe~ Làm gì đó vui~",
                    "*playful* Ehehe~ Đùa thôi~",
                    "*mischievous* Nyan~ Cute không~"
                ],
                "weight": 3,
                "min_interval": 150
            },
            "shy": {
                "name": "xấu hổ",
                "sounds": ["*ngượng* Ah...", "Etto..."],
                "text": [
                    "*xấu hổ* Ah... Ngại quá~",
                    "*shy* Etto... Um...",
                    "*embarrassed* Mặt đỏ rồi~"
                ],
                "weight": 2,
                "min_interval": 180
            },
            "annoyed": {
                "name": "khó chịu",
                "sounds": ["*khó chịu* Tch!", "Mou~!"],
                "text": [
                    "*khó chịu* Tch! Bực mình~",
                    "*annoyed* Mou~! Phiền quá~",
                    "*irritated* Ugh! Chán thật~"
                ],
                "weight": 1,
                "min_interval": 240
            },
            "proud": {
                "name": "tự hào",
                "sounds": ["*tự hào* Hmph!", "Fufufu~"],
                "text": [
                    "*tự hào* Hmph! Em giỏi mà~",
                    "*proud* Fufufu~ Tự tin đây~",
                    "*confident* Đúng không nào~"
                ],
                "weight": 2,
                "min_interval": 200
            }
        }
        
        # Tracking thời gian của từng behavior
        self.last_execution = {key: 0 for key in self.behaviors.keys()}
        
        # Personality modes - Different behavior patterns
        self.personality_modes = {
            "normal": {
                "name": "Bình thường",
                "description": "MeiLin cân bằng, tự nhiên",
                "behavior_multipliers": {}  # Default weights
            },
            "energetic": {
                "name": "Năng động",
                "description": "MeiLin đầy năng lượng, hào hứng",
                "behavior_multipliers": {
                    "cheerful": 3, "excitement": 3, "giggle": 2, 
                    "whistle": 2, "humming": 2, "playful": 3
                },
                "suppress": ["sleepy", "yawn", "groan", "sniffle"]
            },
            "calm": {
                "name": "Trầm tĩnh",
                "description": "MeiLin thư thái, dịu dàng",
                "behavior_multipliers": {
                    "hum": 2, "thinking": 2, "satisfied": 2, 
                    "murmur": 2, "clear_throat": 1.5
                },
                "suppress": ["excitement", "gasp", "cheerful"]
            },
            "sleepy": {
                "name": "Buồn ngủ",
                "description": "MeiLin mệt mỏi, uể oải",
                "behavior_multipliers": {
                    "yawn": 4, "sleepy": 3, "sigh": 2, 
                    "stretch": 2, "groan": 2
                },
                "suppress": ["excitement", "cheerful", "whistle", "playful"]
            },
            "playful": {
                "name": "Tinh nghịch",
                "description": "MeiLin vui tươi, nghịch ngợm",
                "behavior_multipliers": {
                    "playful": 4, "giggle": 3, "chuckle": 3,
                    "whistle": 2, "humming": 2, "tease": 2
                },
                "suppress": ["sniffle", "groan", "pout", "annoyed"]
            },
            "shy": {
                "name": "Nhút nhát",
                "description": "MeiLin ngại ngùng, dễ thương",
                "behavior_multipliers": {
                    "shy": 4, "nervous": 3, "murmur": 2,
                    "confused": 2, "hum": 2
                },
                "suppress": ["proud", "determined", "cheerful"]
            },
            "confident": {
                "name": "Tự tin",
                "description": "MeiLin mạnh mẽ, quyết đoán",
                "behavior_multipliers": {
                    "proud": 3, "determined": 3, "satisfied": 2,
                    "chuckle": 2, "thinking": 2
                },
                "suppress": ["shy", "nervous", "sniffle", "pout"]
            },
            "moody": {
                "name": "Moody",
                "description": "MeiLin thất thường, dễ thay đổi tâm trạng",
                "behavior_multipliers": {
                    "pout": 3, "annoyed": 2, "sigh": 2,
                    "groan": 2, "sniffle": 1.5
                },
                "suppress": ["cheerful", "playful"]
            },
            "focused": {
                "name": "Tập trung",
                "description": "MeiLin chăm chú, nghiêm túc",
                "behavior_multipliers": {
                    "thinking": 3, "hum": 3, "murmur": 2,
                    "clear_throat": 2, "determined": 2
                },
                "suppress": ["giggle", "playful", "yawn", "sleepy"]
            }
        }
        
        self.current_mode = "normal"  # Default mode
        
        # Config
        self.ambient_enabled = True
        self.base_interval = 60  # Check mỗi 60s
        
        # Load idle/sleep responses config
        self.idle_responses = self._load_idle_responses()
        self.idle_config = self._load_idle_config()
        
        # Load ambient behaviors config (ngáp, thở dài, cười,...)
        self.ambient_behaviors = self._load_ambient_behaviors()
        self.behaviors_config = self._load_behaviors_config()
        self.last_behavior_time = {}  # Track last time for each behavior type
    
    def _load_idle_responses(self) -> List[Dict]:
        """Load idle/sleep response configurations"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "ambient_responses.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('responses', [])
        except Exception as e:
            print(f"[AmbientBehavior] Warning: Could not load idle responses: {e}")
            return []
    
    def _load_idle_config(self) -> Dict:
        """Load idle response settings"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "ambient_responses.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('settings', {})
        except Exception as e:
            print(f"[AmbientBehavior] Warning: Could not load idle config: {e}")
            return {}
    
    def _load_ambient_behaviors(self) -> List[Dict]:
        """Load ambient behavior configurations (ngáp, thở dài, cười,...)"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "ambient_behaviors.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('behaviors', [])
        except Exception as e:
            print(f"[AmbientBehavior] Warning: Could not load ambient behaviors: {e}")
            return []
    
    def _load_behaviors_config(self) -> Dict:
        """Load ambient behaviors settings"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "ambient_behaviors.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('settings', {})
        except Exception as e:
            print(f"[AmbientBehavior] Warning: Could not load behaviors config: {e}")
            return {}
    
    def should_trigger_ambient(self) -> bool:
        """Kiểm tra xem có nên trigger ambient behavior không"""
        if not self.ambient_enabled:
            return False
        
        # Random chance: 30% mỗi lần check
        return random.random() < 0.3
    
    def get_random_behavior(self) -> Optional[Dict]:
        """
        Chọn random behavior dựa trên weight và interval
        Returns:
            Dict với keys: behavior_type, text, sound
        """
        current_time = time.time()
        mode_config = self.personality_modes[self.current_mode]
        suppress_list = mode_config.get('suppress', [])
        multipliers = mode_config.get('behavior_multipliers', {})
        
        # Lọc behaviors có thể thực hiện (đã qua min_interval)
        available_behaviors = []
        weights = []
        
        for key, behavior in self.behaviors.items():
            # Skip suppressed behaviors
            if key in suppress_list:
                continue
                
            time_since_last = current_time - self.last_execution[key]
            
            if time_since_last >= behavior['min_interval']:
                available_behaviors.append(key)
                # Apply personality mode multipliers
                base_weight = behavior['weight']
                multiplier = multipliers.get(key, 1.0)
                weights.append(base_weight * multiplier)
        
        if not available_behaviors:
            return None
        
        # Weighted random choice
        behavior_type = random.choices(available_behaviors, weights=weights)[0]
        behavior = self.behaviors[behavior_type]
        
        # Update last execution time
        self.last_execution[behavior_type] = current_time
        
        # Random chọn text và sound
        text = random.choice(behavior['text'])
        sound = random.choice(behavior['sounds'])
        
        return {
            'type': behavior_type,
            'name': behavior['name'],
            'text': text,
            'sound': sound,
            'mode': self.current_mode
        }
    
    def get_context_aware_behavior(self, context: str = "idle") -> Optional[Dict]:
        """
        Lấy behavior phù hợp với context và personality mode
        Args:
            context: idle, active, excited, tired
        """
        context_behaviors = {
            "idle": ["sigh", "yawn", "stretch", "hum", "murmur", "humming"],
            "active": ["giggle", "excitement", "thinking", "hum", "chuckle"],
            "excited": ["excitement", "giggle", "surprise", "cheerful", "gasp"],
            "tired": ["yawn", "sigh", "stretch", "clear_throat", "sleepy", "groan"],
            "happy": ["cheerful", "giggle", "whistle", "humming", "playful"],
            "sad": ["sigh", "sniffle", "pout", "groan"],
            "confused": ["confused", "hum", "thinking", "murmur"],
            "confident": ["proud", "determined", "satisfied", "chuckle"]
        }
        
        preferred = context_behaviors.get(context, ["hum", "sigh"])
        mode_config = self.personality_modes[self.current_mode]
        suppress_list = mode_config.get('suppress', [])
        multipliers = mode_config.get('behavior_multipliers', {})
        
        # Filter available behaviors theo context và mode
        current_time = time.time()
        available = []
        weights = []
        
        for key in preferred:
            if key in self.behaviors and key not in suppress_list:
                behavior = self.behaviors[key]
                time_since_last = current_time - self.last_execution[key]
                
                if time_since_last >= behavior['min_interval']:
                    available.append(key)
                    base_weight = behavior['weight']
                    multiplier = multipliers.get(key, 1.0)
                    weights.append(base_weight * multiplier)
        
        if not available:
            return self.get_random_behavior()
        
        # Weighted choice
        behavior_type = random.choices(available, weights=weights)[0]
        behavior = self.behaviors[behavior_type]
        
        self.last_execution[behavior_type] = current_time
        
        return {
            'type': behavior_type,
            'name': behavior['name'],
            'text': random.choice(behavior['text']),
            'sound': random.choice(behavior['sounds']),
            'mode': self.current_mode
        }
    
    def set_personality_mode(self, mode: str) -> bool:
        """
        Thay đổi personality mode của MeiLin
        Args:
            mode: normal, energetic, calm, sleepy, playful, shy, confident, moody, focused
        Returns:
            True nếu thành công, False nếu mode không tồn tại
        """
        if mode not in self.personality_modes:
            print(f"[AmbientBehavior] Mode '{mode}' không tồn tại!")
            print(f"Available modes: {', '.join(self.personality_modes.keys())}")
            return False
        
        old_mode = self.current_mode
        self.current_mode = mode
        mode_info = self.personality_modes[mode]
        
        print(f"[AmbientBehavior] Đã chuyển từ '{old_mode}' sang '{mode}'")
        print(f"  → {mode_info['description']}")
        return True
    
    def get_current_mode(self) -> Dict:
        """Lấy thông tin về mode hiện tại"""
        return {
            'mode': self.current_mode,
            'info': self.personality_modes[self.current_mode]
        }
    
    def list_modes(self) -> List[Dict]:
        """Liệt kê tất cả personality modes"""
        return [
            {
                'key': key,
                'name': info['name'],
                'description': info['description'],
                'is_current': key == self.current_mode
            }
            for key, info in self.personality_modes.items()
        ]
    
    def enable_ambient(self, enabled: bool = True):
        """Bật/tắt ambient behaviors"""
        self.ambient_enabled = enabled
        print(f"[AmbientBehavior] Ambient behaviors {'enabled' if enabled else 'disabled'}")
    
    def reset_timers(self):
        """Reset tất cả timers (dùng khi restart stream)"""
        current_time = time.time()
        self.last_execution = {key: current_time for key in self.behaviors.keys()}
    
    def get_mode_stats(self) -> Dict:
        """Thống kê về mode hiện tại và behaviors"""
        mode_config = self.personality_modes[self.current_mode]
        suppress_list = mode_config.get('suppress', [])
        multipliers = mode_config.get('behavior_multipliers', {})
        
        boosted = [k for k, v in multipliers.items() if v > 1.0]
        
        return {
            'current_mode': self.current_mode,
            'mode_name': mode_config['name'],
            'description': mode_config['description'],
            'boosted_behaviors': boosted,
            'suppressed_behaviors': suppress_list,
            'total_behaviors': len(self.behaviors),
            'available_behaviors': len(self.behaviors) - len(suppress_list)
        }
    
    def _get_time_of_day(self) -> str:
        """Xác định thời điểm trong ngày"""
        hour = datetime.now().hour
        
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def get_idle_response(self, context: str = "idle_mode") -> Optional[Dict]:
        """
        Lấy idle/sleep response phù hợp với context và thời gian
        Args:
            context: idle_mode, going_to_sleep, goodbye, standby, leaving, etc.
        Returns:
            Dict với keys: id, text, filename, audio_path, emotion, context
        """
        if not self.idle_responses:
            return None
        
        current_time = self._get_time_of_day()
        
        # Filter responses theo context và time_of_day
        suitable_responses = []
        weights = []
        
        for response in self.idle_responses:
            # Check context match
            response_contexts = response.get('context', [])
            if context not in response_contexts:
                continue
            
            # Check time_of_day match
            response_times = response.get('time_of_day', [])
            if current_time not in response_times:
                continue
            
            suitable_responses.append(response)
            # Weight based on how specific the context is
            weight = len(response_contexts)  # More specific contexts get higher weight
            weights.append(weight)
        
        if not suitable_responses:
            # Fallback: just match context, ignore time
            for response in self.idle_responses:
                if context in response.get('context', []):
                    suitable_responses.append(response)
                    weights.append(1)
        
        if not suitable_responses:
            # Final fallback: any idle_mode response
            for response in self.idle_responses:
                if "idle_mode" in response.get('context', []):
                    suitable_responses.append(response)
                    weights.append(1)
        
        if not suitable_responses:
            return None
        
        # Weighted random choice
        chosen = random.choices(suitable_responses, weights=weights)[0]
        
        # Build full audio path
        cache_dir = self.idle_config.get('cache_directory', 'static/ambient_responses')
        audio_path = Path(cache_dir) / chosen['filename']
        
        return {
            'id': chosen['id'],
            'text': chosen['text'],
            'filename': chosen['filename'],
            'audio_path': str(audio_path),
            'emotion': chosen['emotion'],
            'context': chosen['context'],
            'time_of_day': current_time
        }
    
    def get_sleep_response(self) -> Optional[Dict]:
        """Shortcut để lấy sleep response"""
        return self.get_idle_response(context="going_to_sleep")
    
    def get_goodbye_response(self) -> Optional[Dict]:
        """Shortcut để lấy goodbye response"""
        return self.get_idle_response(context="goodbye")
    
    def get_standby_response(self) -> Optional[Dict]:
        """Shortcut để lấy standby response"""
        return self.get_idle_response(context="standby")
    
    def get_behavior(self, context: str = "idle") -> Optional[Dict]:
        """
        Lấy ambient behavior (ngáp, thở dài, cười,...) phù hợp với context
        Args:
            context: waiting_api, after_command, idle, processing, after_success, etc.
        Returns:
            Dict với keys: id, type, text, filename, audio_path, emotion, context, weight
        """
        if not self.ambient_behaviors:
            return None
        
        current_time = time.time()
        
        # Filter behaviors theo context
        suitable_behaviors = []
        weights = []
        
        for behavior in self.ambient_behaviors:
            # Check context match
            behavior_contexts = behavior.get('context', [])
            if context not in behavior_contexts:
                continue
            
            # Check min_interval
            behavior_type = behavior.get('type', '')
            min_interval = behavior.get('min_interval_seconds', 0)
            last_time = self.last_behavior_time.get(behavior_type, 0)
            
            if current_time - last_time < min_interval:
                continue  # Too soon
            
            suitable_behaviors.append(behavior)
            weights.append(behavior.get('weight', 1))
        
        if not suitable_behaviors:
            # Fallback: match any idle context
            for behavior in self.ambient_behaviors:
                if "idle" in behavior.get('context', []):
                    behavior_type = behavior.get('type', '')
                    min_interval = behavior.get('min_interval_seconds', 0)
                    last_time = self.last_behavior_time.get(behavior_type, 0)
                    
                    if current_time - last_time >= min_interval:
                        suitable_behaviors.append(behavior)
                        weights.append(behavior.get('weight', 1))
        
        if not suitable_behaviors:
            return None
        
        # Weighted random choice
        chosen = random.choices(suitable_behaviors, weights=weights)[0]
        
        # Update last behavior time for this type
        self.last_behavior_time[chosen['type']] = current_time
        
        # Build full audio path
        cache_dir = self.behaviors_config.get('cache_directory', 'static/ambient_behaviors')
        audio_path = Path(cache_dir) / chosen['filename']
        
        return {
            'id': chosen['id'],
            'type': chosen['type'],
            'text': chosen['text'],
            'filename': chosen['filename'],
            'audio_path': str(audio_path),
            'emotion': chosen['emotion'],
            'context': chosen['context'],
            'weight': chosen.get('weight', 1)
        }
    
    def get_waiting_behavior(self) -> Optional[Dict]:
        """Shortcut: Lấy behavior khi đang đợi API"""
        return self.get_behavior(context="waiting_api")
    
    def get_after_command_behavior(self) -> Optional[Dict]:
        """Shortcut: Lấy behavior sau khi nghe lệnh"""
        return self.get_behavior(context="after_command")
    
    def get_processing_behavior(self) -> Optional[Dict]:
        """Shortcut: Lấy behavior khi đang xử lý"""
        return self.get_behavior(context="processing")

# Singleton instance
_ambient_behavior = None

def get_ambient_behavior() -> AmbientBehavior:
    """Lấy singleton instance của AmbientBehavior"""
    global _ambient_behavior
    if _ambient_behavior is None:
        _ambient_behavior = AmbientBehavior()
    return _ambient_behavior
