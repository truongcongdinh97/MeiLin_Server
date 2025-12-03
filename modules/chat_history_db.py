import requests
from modules.config_loader import load_config_with_env
from modules.local_chromadb import get_local_chromadb

class ChatHistoryDB:
    def __init__(self):
        """Initialize ChatHistoryDB với auto-detect local/cloud mode"""
        import os
        db_config = load_config_with_env('config/database.yaml')
        mode = db_config.get('mode', 'auto')
        
        # Auto-detect mode based on environment variables
        if mode == 'auto':
            chromadb_url = os.getenv('CHROMADB_API_URL')
            mode = 'cloud' if (chromadb_url and chromadb_url.strip()) else 'local'
        
        self.mode = mode
        
        if self.mode == 'local':
            self.local_db = get_local_chromadb()
        # Cloud config sẽ được load khi cần
    def get_embedding(self, text, model="paraphrase-multilingual-MiniLM-L12-v2", retries=2):
        import requests
        import time
        
        # Đọc embedding config từ database.yaml với env vars
        db_config = load_config_with_env('config/database.yaml')
        embedding_config = db_config.get('embedding', {})
        url = embedding_config.get('api_url', '')
        payload = {
            "input": [text],
            "model": model
        }
        headers = {"Content-Type": "application/json"}
        
        # Retry mechanism với backoff
        for attempt in range(retries):
            try:
                # Timeout 8s cho UX tốt hơn, retry x2 = max 16s
                resp = requests.post(url, json=payload, headers=headers, timeout=8)
                resp.raise_for_status()
                data = resp.json()
                
                # Nếu trả về dạng {'data': [[...]]} thì lấy luôn data[0]
                if "data" in data and data["data"]:
                    emb = data["data"][0]
                    # Nếu emb là dict, lấy trường 'embedding' hoặc 'vector'
                    if isinstance(emb, dict):
                        if "embedding" in emb:
                            return emb["embedding"]
                        elif "vector" in emb:
                            return emb["vector"]
                        else:
                            print(f"Không tìm thấy trường embedding/vector trong kết quả: {emb}")
                            return None
                    elif isinstance(emb, list):
                        return emb
                    else:
                        print(f"Kết quả embedding không đúng dạng: {emb}")
                        return None
                else:
                    print(f"Không lấy được embedding cho text: {text}")
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2  # Backoff: 2s, 4s
                    print(f"[WARNING] Embedding timeout, retry {attempt + 1}/{retries} sau {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] Embedding timeout sau {retries} lần thử")
                    return None
            except Exception as e:
                print(f"[ERROR] Lỗi lấy embedding: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                else:
                    return None
        
        return None

    def query_by_text(self, text, n_results=10, model="paraphrase-multilingual-MiniLM-L12-v2"):
        embedding = self.get_embedding(text, model)
        if embedding is None:
            print("Không lấy được embedding, dừng truy vấn.")
            return []
        query_url = f"{self.api_url}/{self.collection_id}/query"
        payload = {
            "query_embeddings": [embedding],
            "n_results": n_results
        }
        import requests
        resp = requests.post(query_url, json=payload, headers=self.headers, timeout=8)
        if resp.status_code == 200:
            try:
                docs = resp.json()
                return docs
            except Exception as e:
                print(f"Lỗi parse JSON kết quả truy vấn: {e}")
                return []
        else:
            print(f"Lỗi truy vấn ChromaDB: {resp.text}")
            return []

    def get_all_voices(self):
        # Truy vấn toàn bộ documents từ collection
        if not self.collection_id:
            print("Collection chưa được tạo hoặc chưa lấy được ID.")
            return []
        query_url = f"{self.api_url}/{self.collection_id}/documents"
        resp = requests.get(query_url, headers=self.headers, timeout=8)
        if resp.status_code == 200:
            docs = resp.json()
            # docs có thể là list hoặc dict
            if isinstance(docs, list):
                return [doc.get("response", "") for doc in docs if doc.get("response", "")]
            elif isinstance(docs, dict):
                return [doc.get("response", "") for doc in docs.get("documents", []) if doc.get("response", "")]
            else:
                print("Không nhận diện được cấu trúc dữ liệu trả về!")
                return []
        else:
            print("Lỗi truy vấn:", resp.text)
            return []

    def __init__(self, api_url, collection_name="chat_history", headers=None):
        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.api_url = api_url
        self.collection_name = collection_name
        # Tạo headers mặc định nếu chưa truyền vào
        default_headers = {
            "Content-Type": "application/json",
            "CF-Access-Client-Id": os.getenv("CF_ACCESS_CLIENT_ID", ""),
            "CF-Access-Client-Secret": os.getenv("CF_ACCESS_CLIENT_SECRET", "")
        }
        self.headers = headers or default_headers
        self.collection_id = None

    def create_collection(self, metadata=None):
        data = {
            "name": self.collection_name,
            "metadata": metadata or {"type": "chat"}
        }
        response = requests.post(self.api_url, json=data, headers=self.headers, timeout=8)
        if response.status_code == 201:
            print(f"Tạo collection {self.collection_name} thành công!")
            self.collection_id = response.json().get("id")
            return True
        elif response.status_code == 400 and "already exists" in response.text:
            # Nếu collection đã tồn tại, lấy lại ID chính xác
            get_url = f"{self.api_url}?name={self.collection_name}"
            get_resp = requests.get(get_url, headers=self.headers, timeout=8)
            if get_resp.status_code == 200:
                collections = get_resp.json()
                print(f"[DEBUG] API trả về khi truy vấn collection: {collections}")
                # Chuẩn hóa: nếu là dict có key 'collections', lấy ra list
                if isinstance(collections, dict):
                    if "collections" in collections and isinstance(collections["collections"], list):
                        collections = collections["collections"]
                    else:
                        # Nếu là dict nhưng không có key 'collections', kiểm tra xem có phải là 1 collection duy nhất
                        if collections.get("name") == self.collection_name and "id" in collections:
                            self.collection_id = collections["id"]
                            print(f"Đã lấy lại collection_id: {self.collection_id}")
                            return True
                        print("Không tìm thấy collection phù hợp trong dict trả về.")
                        return False
                # Nếu là list, kiểm tra từng phần tử
                if isinstance(collections, list):
                    for col in collections:
                        if isinstance(col, dict) and col.get("name") == self.collection_name and "id" in col:
                            self.collection_id = col["id"]
                            print(f"Đã lấy lại collection_id: {self.collection_id}")
                            return True
                    print("Không tìm thấy collection phù hợp trong danh sách trả về.")
                    return False
                print("Danh sách collections trả về rỗng hoặc không đúng định dạng.")
                return False
            else:
                print(f"Lỗi truy vấn lấy lại collection: {get_resp.text}")
                return False
        else:
            print(f"Lỗi tạo collection: {response.text}")
            return False

    def add_chat_history(self, user_id, username, preferences, message, response):
        # Thêm một bản ghi chat vào collection với làm sạch emoji/ký tự đặc biệt
        def remove_emoji(text):
            import re
            emoji_pattern = re.compile(
                "["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags
                u"\U00002700-\U000027BF"  # dingbats
                u"\U000024C2-\U0001F251"  # enclosed characters
                "]+", flags=re.UNICODE)
            return emoji_pattern.sub(r'', text)

        if not self.collection_id:
            print("Collection chưa được tạo hoặc chưa lấy được ID.")
            return False
        
        # ChromaDB API v2: Sử dụng endpoint /add với format đúng
        add_url = f"{self.api_url}/{self.collection_id}/add"
        clean_message = remove_emoji(str(message))
        clean_response = remove_emoji(str(response))
        
        # Tạo document text (kết hợp message + response)
        document_text = f"User: {clean_message}\nMeiLin: {clean_response}"
        
        # Tạo unique ID cho document
        import hashlib
        import time
        doc_id = hashlib.md5(f"{username}_{user_id}_{time.time()}".encode()).hexdigest()
        
        # Generate embedding cho document (với retry)
        embedding = self.get_embedding(document_text, retries=2)
        if not embedding:
            print("[WARNING] Không thể tạo embedding, bỏ qua lưu lịch sử để không block chat")
            # Không return False, để chat tiếp tục hoạt động
            return True  # Trả về True để không ảnh hưởng flow
        
        # Format payload theo ChromaDB v2 API spec (bắt buộc phải có embeddings)
        data = {
            "ids": [doc_id],
            "embeddings": [embedding],  # Bắt buộc phải có
            "documents": [document_text],
            "metadatas": [{
                "user_id": user_id,
                "username": username,
                "preferences": str(preferences),  # ChromaDB metadata phải là string/number/bool
                "message": clean_message,
                "response": clean_response,
                "timestamp": str(time.time())
            }]
        }
        
        print(f"[DEBUG] Gửi dữ liệu lên DB: Collection={self.collection_id}")
        resp = requests.post(add_url, json=data, headers=self.headers, timeout=15)
        
        if resp.status_code in [200, 201]:
            print("✅ Thêm lịch sử chat thành công!")
            return True
        else:
            print(f"[ERROR] Lỗi thêm lịch sử chat: {resp.status_code}")
            print(f"[ERROR] Response: {resp.text}")
            return False

    def update_preferences(self, user_id, new_preferences):
        # Cập nhật sở thích cho user
        print("Hàm cập nhật sở thích cần endpoint cụ thể của ChromaDB server.")

    def filter_history_by_username(self, username):
        """Lọc lịch sử chat theo username với timeout và error handling"""
        try:
            if not self.collection_id:
                print("Collection chưa được tạo hoặc chưa lấy được ID.")
                return []
            
            # ChromaDB v2 API: Dùng /get với filter, không phải /documents:search
            query_url = f"{self.api_url}/{self.collection_id}/get"
            data = {"where": {"username": username}}  # ChromaDB v2 dùng "where", không phải "filter"
            resp = requests.post(query_url, json=data, headers=self.headers, timeout=15)  # Tăng timeout
            
            if resp.status_code == 200:
                docs = resp.json().get("documents", [])
                if isinstance(docs, list):
                    return docs
                else:
                    print("Kết quả truy vấn không phải list.")
                    return []
            else:
                print(f"Lỗi truy vấn lịch sử: {resp.status_code}")
                return []
        except requests.exceptions.Timeout:
            print("⚠️ Timeout truy vấn lịch sử (bỏ qua)")
            return []
        except Exception as e:
            print(f"⚠️ Lỗi truy vấn lịch sử: {e}")
            return []

# Ví dụ sử dụng:
# api_url from config/database.yaml via environment variables
# db = ChatHistoryDB(api_url)
# db.create_collection()
# db.add_chat_history(user_id="123", username="Định", preferences=["music", "coding"], message="Chào MeiLin", response="Chào Anh Định!")
# history = db.filter_history_by_username("Định")
# print(history)
