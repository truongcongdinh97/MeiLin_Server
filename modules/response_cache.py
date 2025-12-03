"""
Response Cache - Lưu trữ và quản lý câu trả lời có sẵn
Tích hợp với ChromaDB để lưu text + audio path
Fallback sang in-memory mode khi không có PersistentClient
"""
import json
import random
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

# Thử import chromadb, nếu lỗi thì dùng fallback
try:
    import chromadb
    from chromadb.config import Settings
    # Kiểm tra xem có thể dùng PersistentClient không
    # chromadb-client (http-only) sẽ raise RuntimeError
    _USE_CHROMADB = True
except ImportError:
    _USE_CHROMADB = False

logger = logging.getLogger(__name__)

class ResponseCache:
    """
    Quản lý cache câu trả lời thường dùng
    - Wake word responses (MeiLin có mặt, Em đây, ...)
    - Greeting responses (Chào anh, Xin chào, ...)
    - Common reactions (Ừ, Okay, Được rồi, ...)
    """
    
    def __init__(self, db_path: str = "database/response_cache"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory fallback storage
        self._memory_storage: Dict[str, Dict[str, Any]] = {}
        self._use_memory = False
        
        # Thử kết nối ChromaDB
        if _USE_CHROMADB:
            try:
                self.client = chromadb.PersistentClient(
                    path=str(self.db_path),
                    settings=Settings(anonymized_telemetry=False)
                )
                self.collection = self.client.get_or_create_collection(
                    name="cached_responses",
                    metadata={"description": "Pre-recorded responses for common situations"}
                )
                logger.info("ResponseCache using ChromaDB PersistentClient")
            except RuntimeError as e:
                # chromadb-client (http-only) không hỗ trợ PersistentClient
                logger.warning(f"ChromaDB PersistentClient not available: {e}")
                logger.info("ResponseCache using in-memory fallback mode")
                self._use_memory = True
                self.client = None
                self.collection = None
        else:
            logger.info("ResponseCache using in-memory mode (chromadb not installed)")
            self._use_memory = True
            self.client = None
            self.collection = None
        
        # Audio cache folder
        self.audio_folder = Path("audio_cache")
        self.audio_folder.mkdir(exist_ok=True)
        
        self._init_default_responses()
    
    def _init_default_responses(self):
        """Khởi tạo các câu trả lời mặc định nếu DB trống"""
        try:
            # Kiểm tra xem đã có data chưa
            if self._use_memory:
                if self._memory_storage:
                    logger.info(f"Response cache already has {len(self._memory_storage)} responses")
                    return
            else:
                existing = self.collection.get()
                if existing['ids']:
                    logger.info(f"Response cache already has {len(existing['ids'])} responses")
                    return
            
            # Thêm wake word responses
            wake_responses = [
                "MeiLin có mặt!",
                "MeiLin đây!",
                "Em đây!",
                "Ơi!",
                "Em nè!",
                "Dạ!",
                "Có gì ạ?",
                "Em nghe đây!"
            ]
            
            for idx, text in enumerate(wake_responses):
                self.add_response(
                    response_id=f"wake_{idx}",
                    text=text,
                    category="wake_word",
                    audio_path=None,  # Sẽ được generate sau
                    metadata={"priority": 1}
                )
            
            # Thêm greeting responses
            greeting_responses = [
                "Chào anh!",
                "Xin chào!",
                "Hi anh!",
                "Anh khỏe không?",
                "Chào anh nha!"
            ]
            
            for idx, text in enumerate(greeting_responses):
                self.add_response(
                    response_id=f"greeting_{idx}",
                    text=text,
                    category="greeting",
                    audio_path=None
                )
            
            # Thêm common reactions
            reactions = [
                "Ừ!",
                "Okay!",
                "Được rồi!",
                "Oki!",
                "Dạ!",
                "Vâng ạ!",
                "Hiểu rồi!",
                "Em hiểu rồi!"
            ]
            
            for idx, text in enumerate(reactions):
                self.add_response(
                    response_id=f"reaction_{idx}",
                    text=text,
                    category="reaction",
                    audio_path=None
                )
            
            logger.info("Initialized default responses in cache")
            
        except Exception as e:
            logger.error(f"Error initializing default responses: {e}")
    
    def add_response(
        self,
        response_id: str,
        text: str,
        category: str,
        audio_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Thêm câu trả lời vào cache
        
        Args:
            response_id: ID duy nhất
            text: Nội dung text
            category: Loại (wake_word, greeting, reaction, etc.)
            audio_path: Đường dẫn file audio (tương đối từ audio_cache/)
            metadata: Metadata bổ sung (priority, emotion, etc.)
        """
        meta = metadata or {}
        meta['category'] = category
        if audio_path:
            meta['audio_path'] = audio_path
        
        if self._use_memory:
            # In-memory mode
            self._memory_storage[response_id] = {
                'id': response_id,
                'text': text,
                'metadata': meta
            }
        else:
            self.collection.add(
                ids=[response_id],
                documents=[text],
                metadatas=[meta]
            )
        logger.info(f"Added response: {response_id} - {text}")
    
    def get_random_response(
        self,
        category: str,
        exclude_recent: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lấy câu trả lời ngẫu nhiên theo category
        
        Args:
            category: Loại câu trả lời (wake_word, greeting, etc.)
            exclude_recent: List các ID đã dùng gần đây (để tránh lặp)
            
        Returns:
            Dict chứa id, text, audio_path (nếu có)
        """
        try:
            if self._use_memory:
                # In-memory mode
                matching = [
                    r for r in self._memory_storage.values()
                    if r['metadata'].get('category') == category
                ]
                if not matching:
                    logger.warning(f"No responses found for category: {category}")
                    return None
                
                # Filter out recently used
                if exclude_recent:
                    available = [r for r in matching if r['id'] not in exclude_recent]
                else:
                    available = matching
                
                if not available:
                    available = matching
                
                selected = random.choice(available)
                return {
                    "id": selected['id'],
                    "text": selected['text'],
                    "metadata": selected['metadata'],
                    "audio_path": selected['metadata'].get('audio_path')
                }
            else:
                results = self.collection.get(
                    where={"category": category}
                )
                
                if not results['ids']:
                    logger.warning(f"No responses found for category: {category}")
                    return None
                
                # Filter out recently used
                available_ids = results['ids']
                if exclude_recent:
                    available_ids = [id for id in available_ids if id not in exclude_recent]
                
                if not available_ids:
                    # Nếu đã dùng hết, reset về toàn bộ
                    available_ids = results['ids']
                
                # Random selection
                selected_idx = available_ids.index(random.choice(available_ids))
                original_idx = results['ids'].index(available_ids[selected_idx])
                
                return {
                    "id": results['ids'][original_idx],
                    "text": results['documents'][original_idx],
                    "metadata": results['metadatas'][original_idx],
                    "audio_path": results['metadatas'][original_idx].get('audio_path')
                }
            
        except Exception as e:
            logger.error(f"Error getting random response: {e}")
            return None
    
    def get_response_by_id(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Lấy câu trả lời theo ID"""
        try:
            if self._use_memory:
                r = self._memory_storage.get(response_id)
                if r:
                    return {
                        "id": r['id'],
                        "text": r['text'],
                        "metadata": r['metadata'],
                        "audio_path": r['metadata'].get('audio_path')
                    }
                return None
            else:
                result = self.collection.get(ids=[response_id])
                if result['ids']:
                    return {
                        "id": result['ids'][0],
                        "text": result['documents'][0],
                        "metadata": result['metadatas'][0],
                        "audio_path": result['metadatas'][0].get('audio_path')
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting response by ID: {e}")
            return None
    
    def update_audio_path(self, response_id: str, audio_path: str):
        """Cập nhật đường dẫn audio cho response"""
        try:
            if self._use_memory:
                if response_id in self._memory_storage:
                    self._memory_storage[response_id]['metadata']['audio_path'] = audio_path
                    logger.info(f"Updated audio path for {response_id}: {audio_path}")
                else:
                    logger.warning(f"Response {response_id} not found")
            else:
                # Get existing metadata
                result = self.collection.get(ids=[response_id])
                if not result['ids']:
                    logger.warning(f"Response {response_id} not found")
                    return
                
                metadata = result['metadatas'][0]
                metadata['audio_path'] = audio_path
                
                # Update
                self.collection.update(
                    ids=[response_id],
                    metadatas=[metadata]
                )
                logger.info(f"Updated audio path for {response_id}: {audio_path}")
            
        except Exception as e:
            logger.error(f"Error updating audio path: {e}")
    
    def list_responses(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tất cả responses (hoặc theo category)"""
        try:
            if self._use_memory:
                if category:
                    matching = [
                        {"id": r['id'], "text": r['text'], "metadata": r['metadata']}
                        for r in self._memory_storage.values()
                        if r['metadata'].get('category') == category
                    ]
                else:
                    matching = [
                        {"id": r['id'], "text": r['text'], "metadata": r['metadata']}
                        for r in self._memory_storage.values()
                    ]
                return matching
            else:
                if category:
                    results = self.collection.get(where={"category": category})
                else:
                    results = self.collection.get()
                
                responses = []
                for i in range(len(results['ids'])):
                    responses.append({
                        "id": results['ids'][i],
                        "text": results['documents'][i],
                        "metadata": results['metadatas'][i]
                    })
                
                return responses
            
        except Exception as e:
            logger.error(f"Error listing responses: {e}")
            return []


# Singleton instance
_response_cache = None

def get_response_cache(db_path: str = "database/response_cache") -> ResponseCache:
    """Get singleton instance của ResponseCache"""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(db_path)
    return _response_cache


# Recent usage tracker (để tránh lặp lại câu trả lời)
class ResponseTracker:
    """Track các response đã dùng gần đây"""
    
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.history: Dict[str, List[str]] = {}  # category -> [response_ids]
    
    def add_used(self, category: str, response_id: str):
        """Đánh dấu response đã được dùng"""
        if category not in self.history:
            self.history[category] = []
        
        self.history[category].append(response_id)
        
        # Keep only recent history
        if len(self.history[category]) > self.max_history:
            self.history[category] = self.history[category][-self.max_history:]
    
    def get_recent(self, category: str) -> List[str]:
        """Lấy list response IDs đã dùng gần đây"""
        return self.history.get(category, [])


_response_tracker = ResponseTracker()

def get_response_tracker() -> ResponseTracker:
    """Get global ResponseTracker instance"""
    return _response_tracker
