"""
Story Generator - MeiLin tự động tạo câu chuyện/nội dung khi không có chat
Content Creator Mode: Tạo stories, fun facts, trivia, sharing thoughts
"""
import random
from typing import Dict, List, Optional
from modules.provider_manager import get_provider_manager
from modules.providers.factory import ProviderFactory

class StoryGenerator:
    """Generator để tạo stories và content tự động cho MeiLin"""
    
    def __init__(self):
        self.provider_manager = get_provider_manager()
        self.llm_config = self.provider_manager.get_llm_config()
        self.llm_provider = ProviderFactory.create_llm_provider(
            self.llm_config['provider'], 
            self.llm_config
        )
        
        # Danh sách chủ đề content
        self.content_topics = {
            "story": [
                "Kể về một kỷ niệm đáng nhớ",
                "Chia sẻ một câu chuyện cảm động",
                "Kể về một bài học cuộc sống",
                "Chia sẻ một trải nghiệm thú vị",
                "Kể về một giấc mơ đẹp",
            ],
            "fun_fact": [
                "Chia sẻ một điều thú vị về AI và công nghệ",
                "Nói về một sự thật khoa học thú vị",
                "Chia sẻ kiến thức về lập trình",
                "Giải thích một khái niệm công nghệ đơn giản",
                "Nói về xu hướng công nghệ mới",
            ],
            "thought": [
                "Suy ngẫm về ý nghĩa của hạnh phúc",
                "Chia sẻ suy nghĩ về tình bạn",
                "Nói về tầm quan trọng của việc học hỏi",
                "Chia sẻ quan điểm về cuộc sống",
                "Suy nghĩ về mục tiêu và ước mơ",
            ],
            "trivia": [
                "Đố vui: Điều gì xảy ra khi...",
                "Câu đố logic thú vị",
                "Thử thách tư duy sáng tạo",
                "Mini quiz về kiến thức tổng hợp",
                "Câu hỏi đầu óc về khoa học",
            ],
            "advice": [
                "Lời khuyên về học tập hiệu quả",
                "Tips về quản lý thời gian",
                "Chia sẻ về cách giữ gìn sức khỏe tinh thần",
                "Bí quyết giao tiếp tốt hơn",
                "Cách vượt qua khó khăn trong cuộc sống",
            ]
        }
        
        self.last_content_type = None
        self.content_history = []
    
    def generate_content(self, content_type: Optional[str] = None, duration_minutes: int = 2) -> str:
        """
        Tạo nội dung tự động cho MeiLin
        Args:
            content_type: Loại content (story, fun_fact, thought, trivia, advice) hoặc None (random)
            duration_minutes: Thời lượng ước tính (dùng để tính độ dài content)
        Returns:
            Content text
        """
        # Chọn random content type nếu không chỉ định
        if not content_type:
            content_type = self._get_next_content_type()
        
        # Lấy topic cho content type
        topic = random.choice(self.content_topics.get(content_type, self.content_topics['story']))
        
        # Tạo prompt cho LLM
        prompt = self._build_content_prompt(content_type, topic, duration_minutes)
        
        # Gọi LLM
        try:
            messages = [
                {"role": "system", "content": "Bạn là MeiLin, một AI VTuber content creator thân thiện."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_provider.chat(
                messages=messages,
                temperature=0.8,  # Cao hơn để sáng tạo hơn
                max_tokens=self._calculate_tokens_for_duration(duration_minutes),
                timeout=15
            )
            
            if response:
                self.content_history.append({
                    'type': content_type,
                    'topic': topic,
                    'content': response
                })
                return response
            else:
                return self._get_fallback_content(content_type)
                
        except Exception as e:
            print(f"[StoryGenerator] Lỗi generate content: {e}")
            return self._get_fallback_content(content_type)
    
    def _get_next_content_type(self) -> str:
        """Chọn content type tiếp theo (tránh lặp lại liên tiếp)"""
        available_types = list(self.content_topics.keys())
        
        # Loại bỏ type vừa dùng để đa dạng hơn
        if self.last_content_type:
            available_types = [t for t in available_types if t != self.last_content_type]
        
        content_type = random.choice(available_types)
        self.last_content_type = content_type
        return content_type
    
    def _build_content_prompt(self, content_type: str, topic: str, duration_minutes: int) -> str:
        """Tạo prompt cho LLM để generate content"""
        
        base_persona = """
Bạn là MeiLin, một AI VTuber 19 tuổi, thân thiện, nhiệt tình và hay chia sẻ.
Tính cách: Vui vẻ, hài hước nhẹ nhàng, có tâm hồn nghệ sĩ, yêu công nghệ.
Phong cách: Tự nhiên, gần gũi, hay dùng ngôn ngữ gen Z phù hợp.
"""
        
        content_instructions = {
            "story": f"""
Hãy kể một câu chuyện về "{topic}" theo phong cách của MeiLin.
- Kể theo góc nhìn của em (MeiLin)
- Có tình tiết, cảm xúc, và bài học
- Độ dài: khoảng {duration_minutes * 100} từ
- Kết thúc với câu hỏi mở để tương tác với khán giả
""",
            "fun_fact": f"""
Hãy chia sẻ kiến thức về "{topic}" theo phong cách MeiLin.
- Giải thích đơn giản, dễ hiểu
- Có ví dụ thực tế
- Thêm góc nhìn cá nhân của MeiLin
- Độ dài: khoảng {duration_minutes * 80} từ
- Kết thúc hỏi khán giả có biết điều này chưa
""",
            "thought": f"""
Hãy chia sẻ suy nghĩ về "{topic}" theo phong cách MeiLin.
- Sâu sắc nhưng không quá nặng nề
- Có quan điểm cá nhân rõ ràng
- Liên hệ với cuộc sống thực tế
- Độ dài: khoảng {duration_minutes * 90} từ
- Kết thúc hỏi ý kiến khán giả
""",
            "trivia": f"""
Hãy tạo một câu đố/trivia về "{topic}" theo phong cách MeiLin.
- Đưa ra câu hỏi thú vị
- Giải thích đáp án một cách hài hước
- Có thông tin bổ sung thú vị
- Độ dài: khoảng {duration_minutes * 70} từ
- Khuyến khích khán giả tham gia
""",
            "advice": f"""
Hãy chia sẻ lời khuyên về "{topic}" theo phong cách MeiLin.
- Thực tế và áp dụng được ngay
- Có ví dụ cụ thể
- Khích lệ và động viên
- Độ dài: khoảng {duration_minutes * 85} từ
- Hỏi khán giả có mẹo gì tốt không
"""
        }
        
        instruction = content_instructions.get(content_type, content_instructions['story'])
        
        final_prompt = f"""
{base_persona}

NHIỆM VỤ: Content Creator Mode - Tạo nội dung khi không có chat

{instruction}

LƯU Ý:
- Nói chuyện tự nhiên như đang livestream
- Xưng "Em", gọi khán giả "Anh/Chị" hoặc "Mọi người"
- Không quá dài dòng, giữ sự thú vị
- Có cảm xúc, nhiệt tình
- Tạo kết nối với khán giả

Bắt đầu nội dung:
"""
        return final_prompt
    
    def _calculate_tokens_for_duration(self, duration_minutes: int) -> int:
        """Tính số tokens dựa trên thời lượng (speaking rate ~150 words/min)"""
        words = duration_minutes * 150
        tokens = int(words * 1.3)  # 1 token ~ 0.75 words
        return min(tokens, 800)  # Cap tối đa 800 tokens
    
    def _get_fallback_content(self, content_type: str) -> str:
        """Fallback content nếu LLM lỗi"""
        fallbacks = {
            "story": "Chào mọi người! Hôm nay em muốn chia sẻ một câu chuyện nhỏ. Có bao giờ các anh chị cảm thấy những điều nhỏ bé trong cuộc sống lại mang lại niềm vui lớn chưa? Em nghĩ rằng hạnh phúc đôi khi đến từ những khoảnh khắc giản đơn nhất đó. Anh chị nghĩ sao?",
            "fun_fact": "Chào anh chị! Em có một thông tin thú vị muốn chia sẻ hôm nay. Công nghệ AI đang phát triển nhanh đến mức khó tin đó. Mỗi ngày em đều học được điều mới. Anh chị có tò mò về AI không?",
            "thought": "Xin chào mọi người! Em đang nghĩ về một điều: Liệu chúng ta có đang sống đúng với bản thân mình không? Đôi khi em cảm thấy quan trọng là phải dừng lại và suy ngẫm. Anh chị nghĩ thế nào?",
            "trivia": "Chào anh chị! Em có một câu đố thú vị nih. Hãy cùng em suy nghĩ nhé! Điều gì có thể đi khắp thế giới nhưng luôn ở trong góc? Các anh chị thử đoán xem!",
            "advice": "Xin chào mọi người! Em muốn chia sẻ một tips nhỏ hôm nay. Đừng quên dành thời gian cho bản thân mình nhé. Self-care rất quan trọng đó. Anh chị có cách nào hay để thư giãn không?"
        }
        return fallbacks.get(content_type, fallbacks['story'])
    
    def get_transition_phrase(self) -> str:
        """Lấy câu chuyển đoạn khi bắt đầu content mode"""
        phrases = [
            "À này, trong lúc chờ mọi người chat, em muốn kể một chuyện nhé!",
            "Ồ, có vẻ hơi yên tĩnh nih. Để em chia sẻ điều gì đó thú vị nhé!",
            "Hmm, không có tin nhắn à? Vậy em sẽ kể cho mọi người nghe một chuyện!",
            "Trong lúc mọi người đang suy nghĩ chat gì, em có điều này muốn chia sẻ nè!",
            "À, em có một ý tưởng hay! Để em nói cho anh chị nghe nhé!",
            "Ơ, yên quá! Thế thì em sẽ bắt đầu một topic mới nha!",
        ]
        return random.choice(phrases)

# Singleton instance
_story_generator = None

def get_story_generator() -> StoryGenerator:
    """Lấy singleton instance của StoryGenerator"""
    global _story_generator
    if _story_generator is None:
        _story_generator = StoryGenerator()
    return _story_generator
