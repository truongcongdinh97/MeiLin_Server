"""
Local ChromaDB Manager
Automatically create and manage local ChromaDB collections
Người dùng có thể tự embedding mà không cần cloud API
"""
import chromadb
from chromadb.config import Settings
from pathlib import Path
import os

class LocalChromaDB:
    """Quản lý ChromaDB local trong thư mục database/"""

    def get_all_documents(self):
        """
        Trả về tất cả document từ collection knowledge dưới dạng list dict có 'role' và 'text'.
        """
        results = self.knowledge_collection.get()
        documents = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            item = {'text': doc}
            item.update(meta)
            documents.append(item)
        return documents

    def __init__(self, persist_directory: str = "database/vector_db"):
        """
        Initialize local ChromaDB client
        Args:
            persist_directory: Thư mục lưu ChromaDB data (default: database/vector_db)
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        print(f"[LocalChromaDB] Initializing local ChromaDB at: {self.persist_directory}")

        # Khởi tạo ChromaDB client với persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Tạo collections nếu chưa tồn tại
        self.knowledge_collection = self._get_or_create_collection(
            name="base_ai_knowledge",
            metadata={
                "description": "Generic AI VTuber knowledge base",
                "type": "knowledge",
                "version": "2.0"
            }
        )

        self.chat_history_collection = self._get_or_create_collection(
            name="chat_history",
            metadata={
                "description": "Conversation history with users",
                "type": "history",
                "version": "2.0"
            }
        )

        print(f"[LocalChromaDB] Collections ready:")
        print(f"  - base_ai_knowledge: {self.knowledge_collection.count()} documents")
        print(f"  - chat_history: {self.chat_history_collection.count()} documents")

    def query_knowledge_by_role(self, role, query):
        """
        Truy vấn các document theo role và query text.
        Returns: List[dict]
        """
        results = []
        # Giả sử self.get_all_documents() trả về list các dict có 'role' và 'text'
        for doc in self.get_all_documents():
            if doc.get('role') == role and query.lower() in doc.get('text', '').lower():
                results.append(doc)
        return results
    
    def _get_or_create_collection(self, name: str, metadata: dict):
        """
        Lấy collection nếu đã tồn tại, hoặc tạo mới
        
        Args:
            name: Tên collection
            metadata: Metadata cho collection
            
        Returns:
            Collection object
        """
        try:
            # Thử lấy collection hiện có
            collection = self.client.get_collection(name=name)
            print(f"  Loaded existing collection: {name}")
            return collection
        except:
            # Tạo mới nếu chưa có
            collection = self.client.create_collection(
                name=name,
                metadata=metadata
            )
            print(f"  🆕 Created new collection: {name}")
            return collection
    
    def add_documents(self, documents: list, metadatas: list = None, 
                     ids: list = None, collection_name: str = "base_ai_knowledge"):
        """
        Thêm documents vào collection
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dicts (optional)
            ids: List of document IDs (optional, auto-generate nếu không có)
            collection_name: Tên collection (default: base_ai_knowledge)
        """
        collection = self.knowledge_collection if collection_name == "base_ai_knowledge" else self.chat_history_collection
        
        # Auto-generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]
        
        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"[LocalChromaDB] Added {len(documents)} documents to {collection_name}")
    
    def query(self, query_text: str, n_results: int = 3, 
             collection_name: str = "base_ai_knowledge", role: str = None):
        """
        Query collection
        
        Args:
            query_text: Text to search
            n_results: Number of results to return
            collection_name: Collection to search in
            
        Returns:
            dict with 'documents', 'metadatas', 'distances'
        """
        collection = self.knowledge_collection if collection_name == "base_ai_knowledge" else self.chat_history_collection
        
        query_args = {
            "query_texts": [query_text],
            "n_results": n_results
        }
        if role:
            query_args["where"] = {"role": role}
        results = collection.query(**query_args)
        
        return {
            'documents': results['documents'][0] if results['documents'] else [],
            'metadatas': results['metadatas'][0] if results['metadatas'] else [],
            'distances': results['distances'][0] if results['distances'] else []
        }
    
    def add_chat_message(self, username: str, message: str, response: str, timestamp: str):
        """
        Thêm chat message vào history
        
        Args:
            username: Username của người chat
            message: Tin nhắn của user
            response: Phản hồi của AI
            timestamp: Thời gian (ISO format)
        """
        import uuid
        
        self.chat_history_collection.add(
            documents=[f"User: {message}\nAI: {response}"],
            metadatas=[{
                "username": username,
                "user_message": message,
                "ai_response": response,
                "timestamp": timestamp,
                "type": "conversation"
            }],
            ids=[str(uuid.uuid4())]
        )
    
    def get_chat_history(self, username: str = None, limit: int = 10):
        """
        Lấy chat history
        
        Args:
            username: Filter by username (optional)
            limit: Số lượng messages tối đa
            
        Returns:
            List of chat messages
        """
        if username:
            results = self.chat_history_collection.get(
                where={"username": username},
                limit=limit
            )
        else:
            results = self.chat_history_collection.get(limit=limit)
        
        return {
            'documents': results['documents'],
            'metadatas': results['metadatas'],
            'ids': results['ids']
        }
    
    def delete_collection(self, collection_name: str):
        """Xóa collection"""
        self.client.delete_collection(name=collection_name)
        print(f"[LocalChromaDB] 🗑️ Deleted collection: {collection_name}")
    
    def reset_collection(self, collection_name: str):
        """Reset collection (xóa tất cả documents)"""
        collection = self.knowledge_collection if collection_name == "base_ai_knowledge" else self.chat_history_collection
        
        # Get all IDs
        all_data = collection.get()
        ids = all_data['ids']
        
        if len(ids) > 0:
            collection.delete(ids=ids)
            print(f"[LocalChromaDB] 🧹 Reset {collection_name}: deleted {len(ids)} documents")
        else:
            print(f"[LocalChromaDB] ℹ️ {collection_name} already empty")
    
    def get_stats(self):
        """Lấy thống kê về collections"""
        return {
            'knowledge_count': self.knowledge_collection.count(),
            'chat_history_count': self.chat_history_collection.count(),
            'persist_directory': str(self.persist_directory)
        }

# Singleton instance
_local_chromadb_instance = None

def get_local_chromadb():
    """Get singleton instance of LocalChromaDB"""
    global _local_chromadb_instance
    if _local_chromadb_instance is None:
        _local_chromadb_instance = LocalChromaDB()
    return _local_chromadb_instance

if __name__ == "__main__":
    # Test
    print("Testing LocalChromaDB...")
    
    db = LocalChromaDB()
    
    # Test add documents
    print("\n📝 Testing add documents...")
    db.add_documents(
        documents=["Hello, I am an AI assistant", "I can help you with various tasks"],
        metadatas=[{"category": "greeting"}, {"category": "capability"}]
    )
    
    # Test query
    print("\n🔍 Testing query...")
    results = db.query("What can you do?", n_results=2)
    print(f"Found {len(results['documents'])} results:")
    for i, doc in enumerate(results['documents']):
        print(f"  {i+1}. {doc}")
    
    # Test stats
    print("\n📊 Stats:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
