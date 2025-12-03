from elevenlabs.client import ElevenLabs
from elevenlabs import play
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

class TTSEngine:
    def __init__(self):
        # Load config
        with open('./config/config.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )
        self.voice_id = self.config['tts']['voice_id']
        self.model_id = self.config['tts']['model']
    
    def add_audio_tags(self, text):
        """Thêm audio tags cho Eleven v3 để cải thiện biểu cảm"""
        # Phân tích văn bản để thêm tags phù hợp
        text_lower = text.lower()
        
        # Thêm tags dựa trên nội dung
        if any(word in text_lower for word in ['chào', 'xin chào', 'hello']):
            tagged_text = f"[friendly] {text}"
        elif any(word in text_lower for word in ['wow', 'tuyệt', 'thú vị']):
            tagged_text = f"[excited] {text}"
        elif any(word in text_lower for word in ['cảm ơn', 'thanks']):
            tagged_text = f"[warmly] {text}"
        elif '?' in text:
            tagged_text = f"[curious] {text}"
        else:
            tagged_text = f"[natural] {text}"
        
        # Thêm speed control nếu cần
        if len(text) > 100:
            tagged_text = f"[moderate pace] {tagged_text}"
        else:
            tagged_text = f"[normal pace] {tagged_text}"
            
        print(f"Text với audio tags: {tagged_text}")
        return tagged_text
    
    def preprocess_vietnamese_v3(self, text):
        """Xử lý văn bản tiếng Việt tối ưu cho v3"""
        if len(text) < 50:
            enhanced_text = f"{text} Đây là MeiLin, AI VTuber thân thiện và nhiệt tình."
        else:
            enhanced_text = text
        
        sentences = enhanced_text.split('.')
        processed_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                if not sentence.endswith(('.', '!', '?')):
                    sentence += '.'
                processed_sentences.append(sentence)
        
        final_text = ' '.join(processed_sentences)
        
        # Thêm audio tags
        final_text = self.add_audio_tags(final_text)
        
        return final_text
    
    def speak(self, text):
        """Chuyển text thành speech và phát với Eleven v3"""
        try:
            if not text or len(text.strip()) == 0:
                return False
                
            # Xử lý văn bản cho v3
            processed_text = self.preprocess_vietnamese_v3(text)
            
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=processed_text,
                model_id=self.model_id,
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": self.config['tts']['stability'],
                    "similarity_boost": self.config['tts']['similarity_boost'],
                    "style": self.config['tts'].get('style', 0.5),
                    "use_speaker_boost": self.config['tts'].get('use_speaker_boost', True)
                }
            )
            
            play.play(audio)
            print(f"Đã phát với Eleven v3 - Stability: {self.config['tts']['stability']}")
            return True
            
        except Exception as e:
            print(f"Lỗi TTS v3: {e}")
            return False