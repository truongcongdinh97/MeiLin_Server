def build_context_from_roles(roles, knowledge_docs):
    """
    Tổng hợp context từ các role và knowledge_docs để truyền vào prompt cho AI.
    Args:
        roles: Danh sách role liên quan
        knowledge_docs: Danh sách document từ ChromaDB
    Returns:
        context: Chuỗi tổng hợp context
    """
    context_parts = []
    for role in roles:
        docs_for_role = [doc for doc in knowledge_docs if doc.get('role') == role]
        if docs_for_role:
            context_parts.append(f"--- Context cho role: {role} ---")
            for doc in docs_for_role:
                context_parts.append(doc.get('text', str(doc)))
    if not context_parts:
        context_parts.append("(Không tìm thấy context phù hợp cho role)")
    return '\n'.join(context_parts)
import chromadb
import json
import os
import requests
from modules.config_loader import load_config_with_env
from modules.local_chromadb import get_local_chromadb


class EmbeddingClient:
    """Client để gọi embedding service API"""
    def __init__(self, api_url: str = None):
        self.api_url = api_url or os.getenv('EMBEDDING_API_URL', 'http://embedding_service:8008')
    
    def encode(self, texts):
        """Encode texts thành embeddings qua API"""
        if isinstance(texts, str):
            texts = [texts]
        try:
            response = requests.post(
                f"{self.api_url}/embed",
                json={"texts": texts},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('embeddings', [])
            else:
                print(f"[Embedding] API error: {response.status_code}")
                return [[0.0] * 384] * len(texts)  # Fallback
        except Exception as e:
            print(f"[Embedding] Error: {e}")
            return [[0.0] * 384] * len(texts)  # Fallback

class RAGSystem:
    def __init__(self):
        print("[RAG] Initializing RAG System...", flush=True)
        
        # Load config
        db_config = load_config_with_env('config/database.yaml')
        mode = db_config.get('mode', 'auto')
        
        # Auto-detect mode based on environment variables
        if mode == 'auto':
            chromadb_url = os.getenv('CHROMADB_API_URL')
            if chromadb_url and chromadb_url.strip():
                mode = 'cloud'
                print("[RAG] 🌐 Detected cloud ChromaDB config", flush=True)
            else:
                mode = 'local'
                print("[RAG] 💾 No cloud config found, using local ChromaDB", flush=True)
        
        self.mode = mode
        
        if self.mode == 'local':
            # Sử dụng Local ChromaDB
            print("[RAG] ✅ Using LOCAL ChromaDB (database/vector_db/)", flush=True)
            self.local_db = get_local_chromadb()
        else:
            # Sử dụng Cloud ChromaDB
            print("[RAG] ✅ Using CLOUD ChromaDB", flush=True)
            # Sử dụng embedding API thay vì local SentenceTransformer
            self.chromadb_config = db_config.get('chromadb', {})
    
    def load_personality_data(self):
        """Tải dữ liệu tính cách từ file JSON"""
        try:
            with open('./config/personality.json', 'r', encoding='utf-8') as f:
                personality_data = json.load(f)
            
            documents = []
            metadatas = []
            ids = []
            
            # Thêm base personality
            base_personality = personality_data["base_personality"]
            docs = [
                f"Tên: {base_personality['name']}",
                f"Tính cách: {', '.join(base_personality['traits'])}",
                f"Phong cách nói: {base_personality['speaking_style']}",
                f"Sở thích: {', '.join(base_personality['interests'])}",
                f"Catchphrases: {' | '.join(base_personality['catchphrases'])}"
            ]
            
            for doc in docs:
                documents.append(doc)
                metadatas.append({"type": "base_personality"})
                ids.append(f"base_{hash(doc)}")
            
            # Thêm knowledge base
            knowledge_base = personality_data["knowledge_base"]
            for category, items in knowledge_base.items():
                for i, item in enumerate(items):
                    documents.append(item)
                    metadatas.append({"type": "knowledge", "category": category})
                    ids.append(f"knowledge_{category}_{i}")
            
            # Encode và thêm vào collection
            if documents:
                embeddings = get_embedding_from_api(documents)
                self.collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print("Đã tải dữ liệu tính cách vào RAG system")
                print(f"Số lượng documents: {len(documents)}")
            else:
                print("Không có dữ liệu tính cách để tải")
                
        except Exception as e:
            print(f"Lỗi tải dữ liệu tính cách: {e}")
    
    def get_context(self, query, n_results=2, timeout=8, role=None):
        """Lấy context liên quan từ ChromaDB (local hoặc cloud)"""
        try:
            import sys
            print("   → Querying knowledge base...", end='', flush=True)
            
            if self.mode == "local":
                # Sử dụng Local ChromaDB
                results = self.local_db.query(
                    query_text=query,
                    n_results=n_results,
                    collection_name="base_ai_knowledge",
                    role=role
                )
                print(" OK", flush=True)
                # Format kết quả
                if results['documents']:
                    context = "\n".join(results['documents'])
                    print(f"   ✓ Found {len(results['documents'])} relevant documents", flush=True)
                    return context
                else:
                    print("   ⚠ No relevant context found", flush=True)
                    return ""
            
            else:
                # Sử dụng Cloud ChromaDB
                print("   → Encoding query via API...", end='', flush=True)
                query_embedding = get_embedding_from_api([query])[0]
                print(" OK", flush=True)
                
                print("   → Querying ChromaDB...", end='', flush=True)
                base_url = self.chromadb_config.get('api_url', '')
                collection_id = self.chromadb_config.get('collections', {}).get('knowledge', {}).get('id', '')
                
                if not base_url or not collection_id:
                    print(" ❌ Cloud ChromaDB not configured", flush=True)
                    return ""
                
                url = f"{base_url}/{collection_id}/query"
            
            headers_config = self.chromadb_config.get('headers', {})
            headers = {
                "CF-Access-Client-Id": headers_config.get('CF-Access-Client-Id', ''),
                "CF-Access-Client-Secret": headers_config.get('CF-Access-Client-Secret', ''),
                "Content-Type": "application/json"
            }
            payload = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            if role:
                payload["where"] = {"role": role}
            # Timeout ngắn hơn cho UX tốt (mặc định 8s)
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            print(" OK", flush=True)
            
            if response.status_code == 200:
                results = response.json()
                if results.get('documents') and len(results['documents']) > 0:
                    context = " ".join(results['documents'][0])
                    return context
                else:
                    return ""
            else:
                print(f"Lỗi query RAG API: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"Lỗi query RAG API: {e}")
            return ""

    def add_conversation_memory(self, user_message, ai_response):
        """Thêm cuộc hội thoại vào memory (tuỳ chọn)"""
        try:
            conversation = f"User: {user_message} | AI: {ai_response}"
            self.collection.add(
                documents=[conversation],
                metadatas=[{"type": "conversation_memory"}],
                ids=[f"memory_{hash(conversation)}"]
            )
        except Exception as e:
            print(f"Lỗi thêm memory: {e}")