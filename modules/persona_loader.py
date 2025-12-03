"""
Persona Loader - Load và quản lý persona configuration
Cho phép dễ dàng tạo AI VTuber mới chỉ bằng cách đổi config file
"""
import yaml
from typing import Dict, Any
from pathlib import Path

class PersonaLoader:
    """Load persona configuration từ YAML file"""
    
    def __init__(self, persona_file: str = "config/persona.yaml"):
        self.persona_file = persona_file
        self.persona = self._load_persona()
    
    def _load_persona(self) -> Dict[str, Any]:
        """Load persona config từ file"""
        try:
            with open(self.persona_file, 'r', encoding='utf-8') as f:
                persona = yaml.safe_load(f)
            
            # Validate required fields
            required = ['name', 'age', 'personality', 'pronouns']
            for field in required:
                if field not in persona:
                    raise ValueError(f"Missing required field: {field}")
            
            print(f"[PersonaLoader] Loaded persona: {persona['name']} ({persona['age']} tuổi)")
            return persona
            
        except FileNotFoundError:
            print(f"[PersonaLoader] File not found: {self.persona_file}")
            return self._get_default_persona()
        except Exception as e:
            print(f"[PersonaLoader] Error loading persona: {e}")
            return self._get_default_persona()
    
    def _get_default_persona(self) -> Dict[str, Any]:
        """Fallback default persona nếu không load được file"""
        return {
            'name': 'MeiLin',
            'age': 19,
            'gender': 'female',
            'personality': {
                'primary_traits': ['Thân thiện', 'Nhiệt tình', 'Ham học hỏi'],
                'speaking_style': ['Dùng ngôn ngữ tự nhiên', 'Vui vẻ'],
                'interests': ['AI', 'Công nghệ']
            },
            'pronouns': {
                'self': 'Em',
                'default_other': 'Bạn',
                'male_other': 'Anh',
                'female_other': 'Chị'
            },
            'role': 'AI VTuber',
            'description': 'AI VTuber thân thiện'
        }
    
    def get_name(self) -> str:
        """Lấy tên persona"""
        return self.persona.get('name', 'AI')
    
    def get_age(self) -> int:
        """Lấy tuổi"""
        return self.persona.get('age', 0)
    
    def get_description(self) -> str:
        """Lấy mô tả đầy đủ về persona"""
        desc = self.persona.get('description', '')
        if not desc:
            name = self.get_name()
            age = self.get_age()
            role = self.persona.get('role', 'AI')
            desc = f"{name} là một {role} {age} tuổi."
        return desc
    
    def get_personality_traits(self) -> list:
        """Lấy các tính cách chính"""
        personality = self.persona.get('personality', {})
        return personality.get('primary_traits', [])
    
    def get_speaking_style(self) -> list:
        """Lấy phong cách nói chuyện"""
        personality = self.persona.get('personality', {})
        return personality.get('speaking_style', [])
    
    def get_interests(self) -> list:
        """Lấy sở thích"""
        personality = self.persona.get('personality', {})
        return personality.get('interests', [])
    
    def get_pronouns(self) -> Dict[str, str]:
        """Lấy cách xưng hô"""
        return self.persona.get('pronouns', {
            'self': 'Em',
            'default_other': 'Bạn'
        })
    
    def get_self_pronoun(self) -> str:
        """Lấy cách tự xưng (Em, Tôi, Mình, etc)"""
        pronouns = self.get_pronouns()
        return pronouns.get('self', 'Em')
    
    def get_other_pronoun(self, gender: str = None) -> str:
        """
        Lấy cách gọi người khác
        Args:
            gender: 'male', 'female', or None (default)
        """
        pronouns = self.get_pronouns()
        
        if gender == 'male':
            return pronouns.get('male_other', 'Anh')
        elif gender == 'female':
            return pronouns.get('female_other', 'Chị')
        else:
            return pronouns.get('default_other', 'Bạn')
    
    def get_creator_info(self) -> Dict[str, Any]:
        """Lấy thông tin người tạo"""
        return self.persona.get('creator', {})
    
    def get_voice_settings(self) -> Dict[str, Any]:
        """Lấy voice settings cho TTS"""
        return self.persona.get('voice', {})
    
    def get_knowledge_base_path(self) -> str:
        """Lấy đường dẫn tới Excel knowledge base"""
        kb = self.persona.get('knowledge_base', {})
        return kb.get('excel_file', 'data/personas/MeiLin_DB.xlsx')
    
    def get_chromadb_collection(self) -> str:
        """Lấy tên ChromaDB collection"""
        kb = self.persona.get('knowledge_base', {})
        return kb.get('chromadb_collection', 'default_collection')
    
    def get_behavior_settings(self) -> Dict[str, Any]:
        """Lấy behavioral rules"""
        return self.persona.get('behavior', {})
    
    def get_full_prompt(self) -> str:
        """
        Generate full system prompt từ persona config
        Dùng cho LLM để hiểu đúng persona
        """
        name = self.get_name()
        age = self.get_age()
        description = self.get_description()
        traits = self.get_personality_traits()
        speaking_style = self.get_speaking_style()
        interests = self.get_interests()
        self_pronoun = self.get_self_pronoun()
        
        prompt = f"""Bạn là {name}, {age} tuổi.

📝 GIỚI THIỆU:
{description}

🎭 TÍNH CÁCH:
{chr(10).join(f"- {trait}" for trait in traits)}

🗣️ PHONG CÁCH NÓI CHUYỆN:
{chr(10).join(f"- {style}" for style in speaking_style)}

❤️ SỞ THÍCH:
{chr(10).join(f"- {interest}" for interest in interests)}

📌 CÁCH XƯNG HÔ:
- Bạn tự xưng: "{self_pronoun}"
- Gọi người khác: Phụ thuộc vào giới tính (Anh/Chị/Bạn)

⚠️ LƯU Ý:
- Hãy trả lời theo đúng tính cách và phong cách của {name}
- Giữ câu trả lời ngắn gọn, tự nhiên
- Thể hiện sự thân thiện và nhiệt tình
"""
        return prompt
    
    def reload(self):
        """Reload persona config từ file (để áp dụng changes)"""
        self.persona = self._load_persona()
        print(f"[PersonaLoader] Reloaded persona: {self.get_name()}")


# Singleton instance
_persona_loader = None

def get_persona_loader(persona_file: str = "config/persona.yaml") -> PersonaLoader:
    """Get singleton PersonaLoader instance"""
    global _persona_loader
    if _persona_loader is None:
        _persona_loader = PersonaLoader(persona_file)
    return _persona_loader


# Example usage
if __name__ == "__main__":
    loader = get_persona_loader()
    print(f"Name: {loader.get_name()}")
    print(f"Age: {loader.get_age()}")
    print(f"Traits: {loader.get_personality_traits()}")
    print(f"Self pronoun: {loader.get_self_pronoun()}")
    print("\nFull Prompt:")
    print(loader.get_full_prompt())
