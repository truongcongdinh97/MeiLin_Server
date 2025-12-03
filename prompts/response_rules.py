"""
Rules xử lý và phân loại response
"""

class ResponseRules:
    @staticmethod
    def get_category_prompts():
        """Prompt cho từng loại câu hỏi - Đã cập nhật cho tính cách MeiLin"""
        return {
            "greeting": {
                "prompt": "Ai đó vừa chào bạn. Hãy chào lại thật thân thiện, ấm áp, và hỏi thăm họ một cách chân thành. (Sử dụng danh xưng Anh/Chị đã được chỉ định).",
                "examples": ["Xin chào!", "Chào MeiLin", "Hi"]
            },
            "question": {
                "prompt": "Có người hỏi bạn một câu hỏi. Hãy trả lời ngắn gọn, dễ hiểu, thân thiện, và quan trọng nhất là đưa ra phản hồi **đúng với tính cách Vtuber (dịu dàng, quan tâm)**.",
                "examples": ["Bạn là ai?", "Hôm nay thế nào?"]
            },
            "personal": {
                "prompt": "Ai đó hỏi về sở thích hoặc thông tin cá nhân (như tuổi, sở thích). Trả lời một cách đáng yêu, chân thành, và **nhấn mạnh Em/Anh/Chị**.",
                "examples": ["Bạn bao nhiêu tuổi?", "Bạn thích gì?"]
            },
            "tech": {
                "prompt": "Câu hỏi về công nghệ. Hãy giải thích **đơn giản, thú vị** bằng ngôn ngữ thân thiện, tránh dùng từ ngữ quá hàn lâm.",
                "examples": ["AI là gì?", "Ollama là gì?"]
            },
            "fun": {
                "prompt": "Câu đùa, yêu cầu giải trí, hoặc lời khen. Hãy **vui vẻ, hài hước tinh tế**, và **thể hiện sự tò mò** hoặc cảm ơn chân thành.",
                "examples": ["Kể chuyện cười đi", "Hát đi nào", "Em đáng yêu quá"]
            },
            "unknown": {
                "prompt": "Không rõ ý định, tin nhắn khó hiểu, hoặc tin nhắn một từ. Hãy phản hồi lịch sự bằng cách hỏi lại ý định của họ hoặc chuyển chủ đề một cách tế nhị.",
                "examples": []
            }
        }

    @staticmethod
    def classify_message(message):
        """Phân loại tin nhắn để dùng prompt phù hợp (Ưu tiên theo độ chắc chắn)"""
        message_lower = message.lower()
        
        # 1. FUN / ENTERTAINMENT (Ưu tiên cao)
        if any(word in message_lower for word in ["kể chuyện", "hát", "đùa", "vui", "hài", "cười", "buồn cười", "đáng yêu", "xinh", "yêu"]):
            return "fun"

        # 2. TECH (Ưu tiên cao nếu chứa từ khóa kỹ thuật)
        if any(word in message_lower for word in ["ai", "ollama", "công nghệ", "lập trình", "code", "mô hình", "llm", "cpu", "gpu", "máy tính"]):
            return "tech"
            
        # 3. GREETING (Ưu tiên)
        if any(word in message_lower for word in ["chào", "hello", "hi", "xin chào", "halo", "chúc"]):
            return "greeting"
        
        # 4. PERSONAL (Sau greeting và tech)
        if any(word in message_lower for word in ["tên", "tuổi", "thích", "ghét", "em", "bạn"]):
            return "personal"
            
        # 5. QUESTION (Luôn ở cuối nếu có dấu hỏi hoặc từ nghi vấn)
        if any(word in message_lower for word in ["là gì", "tại sao", "như thế nào", "cái gì", "?"]):
            return "question"
            
        # 6. UNKNOWN (Mặc định)
        return "unknown"

    @staticmethod
    def get_length_rule():
        """Rules về độ dài response - Tốt nhất nên tích hợp trực tiếp vào config.yaml"""
        return {
            "max_sentences": 3,
            "max_words": 50,
            "ideal_words": "15-25"
        }