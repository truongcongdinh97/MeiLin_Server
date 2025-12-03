"""
Long Context Manager - Hỗ trợ prompt cực dài >10.000 tokens
Tích hợp smart context compression và token optimization
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import tiktoken

class LongContextManager:
    """
    Quản lý context dài với khả năng nén thông minh và tối ưu hóa token
    """
    
    def __init__(self, max_tokens: int = 10000, model: str = "gpt-4"):
        self.max_tokens = max_tokens
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
        
        # Cache cho context compression
        self.context_cache = {}
        self.compression_history = {}
        
    def count_tokens(self, text: str) -> int:
        """Đếm số tokens trong text"""
        return len(self.encoding.encode(text))
    
    def compress_context(self, context: str, target_tokens: int = None) -> str:
        """
        Nén context thông minh để phù hợp với token limit
        Giữ lại thông tin quan trọng, loại bỏ redundancy
        """
        if target_tokens is None:
            target_tokens = self.max_tokens // 2  # Dành chỗ cho prompt và response
        
        current_tokens = self.count_tokens(context)
        
        # Nếu context đã đủ ngắn
        if current_tokens <= target_tokens:
            return context
        
        # Cache để tránh tính toán lại
        cache_key = f"{hash(context)}_{target_tokens}"
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Phân tích và nén context
        compressed = self._smart_compress(context, target_tokens)
        
        # Lưu cache
        self.context_cache[cache_key] = compressed
        return compressed
    
    def _smart_compress(self, text: str, target_tokens: int) -> str:
        """Nén thông minh với các kỹ thuật khác nhau"""
        
        # 1. Loại bỏ whitespace thừa
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 2. Tách thành các đoạn và xác định độ quan trọng
        paragraphs = self._split_into_paragraphs(text)
        scored_paragraphs = self._score_paragraphs(paragraphs)
        
        # 3. Chọn các đoạn quan trọng nhất
        selected_paragraphs = self._select_paragraphs_by_score(
            scored_paragraphs, target_tokens
        )
        
        # 4. Tối ưu hóa từng đoạn
        optimized_paragraphs = [
            self._optimize_paragraph(p) for p in selected_paragraphs
        ]
        
        # 5. Ghép lại với transition mượt mà
        compressed_text = self._join_paragraphs(optimized_paragraphs)
        
        # 6. Kiểm tra và điều chỉnh nếu cần
        final_text = self._final_adjustment(compressed_text, target_tokens)
        
        return final_text
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Tách text thành các đoạn có ý nghĩa"""
        # Tách bằng dấu xuống dòng kép
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Nếu không có paragraph rõ ràng, tách bằng câu
        if len(paragraphs) == 1:
            sentences = re.split(r'[.!?]+', text)
            paragraphs = [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)]
        
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _score_paragraphs(self, paragraphs: List[str]) -> List[Tuple[str, float]]:
        """Đánh giá độ quan trọng của từng đoạn"""
        scored = []
        
        for paragraph in paragraphs:
            score = self._calculate_paragraph_score(paragraph)
            scored.append((paragraph, score))
        
        # Sắp xếp theo điểm số giảm dần
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _calculate_paragraph_score(self, paragraph: str) -> float:
        """Tính điểm quan trọng của đoạn"""
        score = 0.0
        
        # Keywords quan trọng
        important_keywords = [
            'quan trọng', 'chính', 'mục tiêu', 'yêu cầu', 'bắt buộc',
            'important', 'key', 'main', 'objective', 'requirement',
            'phải', 'cần', 'nên', 'không được'
        ]
        
        # Điểm cho keywords
        for keyword in important_keywords:
            if keyword.lower() in paragraph.lower():
                score += 2.0
        
        # Điểm cho độ dài (đoạn quá ngắn hoặc quá dài có thể ít quan trọng)
        tokens = self.count_tokens(paragraph)
        if 10 <= tokens <= 200:  # Đoạn có độ dài hợp lý
            score += 1.0
        
        # Điểm cho cấu trúc (có số, bullet points)
        if re.search(r'\d+\.|\*|\-', paragraph):
            score += 1.5
        
        # Điểm cho câu hỏi
        if '?' in paragraph:
            score += 1.0
        
        return score
    
    def _select_paragraphs_by_score(self, scored_paragraphs: List[Tuple[str, float]], 
                                  target_tokens: int) -> List[str]:
        """Chọn các đoạn dựa trên điểm số và token limit"""
        selected = []
        current_tokens = 0
        
        for paragraph, score in scored_paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            
            if current_tokens + paragraph_tokens <= target_tokens:
                selected.append(paragraph)
                current_tokens += paragraph_tokens
            else:
                # Thử cắt ngắn đoạn nếu vẫn còn chỗ
                remaining_tokens = target_tokens - current_tokens
                if remaining_tokens >= 20:  # Ít nhất 20 tokens
                    shortened = self._shorten_paragraph(paragraph, remaining_tokens)
                    if shortened:
                        selected.append(shortened)
                        break
        
        return selected
    
    def _optimize_paragraph(self, paragraph: str) -> str:
        """Tối ưu hóa từng đoạn để giảm tokens nhưng giữ ý nghĩa"""
        # Loại bỏ từ thừa
        optimizations = [
            (r'\s+', ' '),  # Multiple spaces to single
            (r'\.\s+\.', '.'),  # Multiple dots
            (r',\s+,', ','),  # Multiple commas
        ]
        
        for pattern, replacement in optimizations:
            paragraph = re.sub(pattern, replacement, paragraph)
        
        # Rút gọn cụm từ phổ biến
        phrase_shortcuts = {
            'ví dụ như': 'vd:',
            'có nghĩa là': 'tức là',
            'trong trường hợp': 'nếu',
            'đối với': 'với',
            'thông qua': 'qua',
        }
        
        for long, short in phrase_shortcuts.items():
            paragraph = paragraph.replace(long, short)
        
        return paragraph.strip()
    
    def _shorten_paragraph(self, paragraph: str, max_tokens: int) -> str:
        """Cắt ngắn đoạn để phù hợp với token limit"""
        sentences = re.split(r'[.!?]+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        selected_sentences = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            if current_tokens + sentence_tokens <= max_tokens:
                selected_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        return '. '.join(selected_sentences) + '.' if selected_sentences else ""
    
    def _join_paragraphs(self, paragraphs: List[str]) -> str:
        """Ghép các đoạn lại với transition mượt mà"""
        if not paragraphs:
            return ""
        
        # Thêm transition giữa các đoạn
        transitions = ["", "Tiếp theo,", "Ngoài ra,", "Đồng thời,"]
        
        result = []
        for i, paragraph in enumerate(paragraphs):
            if i > 0 and i - 1 < len(transitions):
                result.append(transitions[i - 1])
            result.append(paragraph)
        
        return ' '.join(result)
    
    def _final_adjustment(self, text: str, target_tokens: int) -> str:
        """Điều chỉnh cuối cùng để đảm bảo phù hợp token limit"""
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= target_tokens:
            return text
        
        # Cắt bớt từ cuối nếu vẫn vượt quá
        words = text.split()
        while words and self.count_tokens(' '.join(words)) > target_tokens:
            words.pop()
        
        return ' '.join(words)
    
    def build_mega_prompt(self, user_input: str, history: List[Dict], 
                         documents: List[Dict] = None) -> str:
        """
        Xây dựng prompt siêu dài từ nhiều nguồn context
        """
        components = []
        
        # 1. System prompt cố định
        system_prompt = self._get_system_prompt()
        components.append(system_prompt)
        
        # 2. Conversation history
        if history:
            history_text = self._format_history(history)
            compressed_history = self.compress_context(history_text, 2000)
            components.append(f"LỊCH SỬ CHAT:\n{compressed_history}")
        
        # 3. Document context
        if documents:
            doc_text = self._format_documents(documents)
            compressed_docs = self.compress_context(doc_text, 3000)
            components.append(f"TÀI LIỆU THAM KHẢO:\n{compressed_docs}")
        
        # 4. Current user input
        components.append(f"YÊU CẦU HIỆN TẠI:\n{user_input}")
        
        # 5. Ghép tất cả lại
        full_prompt = "\n\n".join(components)
        
        # 6. Nén tổng thể nếu cần
        final_prompt = self.compress_context(full_prompt, self.max_tokens - 1000)
        
        return final_prompt
    
    def _get_system_prompt(self) -> str:
        """System prompt cố định cho MeiLin"""
        return """Bạn là MeiLin - một AI assistant thông minh và hữu ích. 
Hãy trả lời câu hỏi dựa trên context được cung cấp và lịch sử chat.
Giữ phong cách thân thiện, tự nhiên và hữu ích."""
    
    def _format_history(self, history: List[Dict]) -> str:
        """Định dạng lịch sử chat"""
        lines = []
        for entry in history[-10:]:  # Lấy 10 tin nhắn gần nhất
            role = entry.get('role', 'user')
            content = entry.get('content', '')
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines)
    
    def _format_documents(self, documents: List[Dict]) -> str:
        """Định dạng tài liệu tham khảo"""
        lines = []
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', '')
            source = doc.get('source', 'unknown')
            lines.append(f"TÀI LIỆU {i} ({source}):\n{content}")
        return "\n\n".join(lines)
    
    def token_optimization(self, text: str) -> str:
        """
        Tối ưu hóa token - loại bỏ redundancy, giữ thông tin quan trọng
        """
        # Loại bỏ các từ/cụm từ lặp lại
        text = self._remove_redundancy(text)
        
        # Rút gọn câu phức tạp
        text = self._simplify_sentences(text)
        
        # Chuẩn hóa formatting
        text = self._normalize_formatting(text)
        
        return text
    
    def _remove_redundancy(self, text: str) -> str:
        """Loại bỏ các phần thừa trong text"""
        # Loại bỏ các câu lặp lại ý nghĩa
        sentences = re.split(r'[.!?]+', text)
        unique_sentences = []
        seen_meanings = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Tạo "signature" đơn giản để phát hiện lặp
            words = set(re.findall(r'\w+', sentence.lower()))
            signature = frozenset(words)
            
            if signature not in seen_meanings:
                unique_sentences.append(sentence)
                seen_meanings.add(signature)
        
        return '. '.join(unique_sentences) + '.' if unique_sentences else text
    
    def _simplify_sentences(self, text: str) -> str:
        """Đơn giản hóa câu phức tạp"""
        # Thay thế các cấu trúc phức tạp bằng đơn giản
        simplifications = [
            (r'mặc dù.*?nhưng', 'tuy nhiên'),
            (r'không chỉ.*?mà còn', 'vừa... vừa'),
            (r'có thể.*?được', 'có thể'),
        ]
        
        for pattern, replacement in simplifications:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_formatting(self, text: str) -> str:
        """Chuẩn hóa formatting"""
        # Chuẩn hóa khoảng trắng
        text = re.sub(r'\s+', ' ', text)
        
        # Chuẩn hóa dấu câu
        text = re.sub(r'\s*([.,!?])\s*', r'\1 ', text)
        
        # Loại bỏ các ký tự đặc biệt không cần thiết
        text = re.sub(r'[^\w\s.,!?\-]', '', text)
        
        return text.strip()


# Factory function
def get_long_context_manager(max_tokens: int = 10000, model: str = "gpt-4"):
    """Factory function để tạo LongContextManager"""
    return LongContextManager(max_tokens=max_tokens, model=model)


# Test the module
if __name__ == "__main__":
    manager = LongContextManager()
    
    # Test với text dài
    long_text = "Đây là một đoạn văn bản rất dài. " * 1000
    compressed = manager.compress_context(long_text, 1000)
    
    print(f"Original tokens: {manager.count_tokens(long_text)}")
    print(f"Compressed tokens: {manager.count_tokens(compressed)}")
    print(f"Compression ratio: {manager.count_tokens(compressed)/manager.count_tokens(long_text):.2%}")
