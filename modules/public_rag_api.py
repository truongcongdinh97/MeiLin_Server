"""
Public RAG API - Cho phép ESP32 devices query knowledge base
Bảo mật bằng API Key (read-only access)
"""
import os
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from modules.rag_system import RAGSystem


class PublicRAGAPI:
    """
    API công khai cho ESP32 devices
    - Read-only access to knowledge base
    - Rate limiting
    - API key authentication
    """
    
    def __init__(self, db_path: str = "data/public_api_keys.db"):
        self.db_path = db_path
        self.rag_system = RAGSystem()
        self._init_db()
        
        # Rate limiting: max requests per device per minute
        self.rate_limit = int(os.getenv('PUBLIC_API_RATE_LIMIT', '30'))
        self.request_counts = {}  # {api_key: [(timestamp, count)]}
    
    def _init_db(self):
        """Khởi tạo database cho API keys"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                total_requests INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                query TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_count INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_api_key(self, device_id: str, device_name: str = None) -> str:
        """
        Tạo API key mới cho device
        Format: meilin_pk_{random_32_chars}
        """
        random_part = secrets.token_hex(16)
        api_key = f"meilin_pk_{random_part}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_keys (api_key, device_id, device_name)
            VALUES (?, ?, ?)
        ''', (api_key, device_id, device_name or device_id))
        
        conn.commit()
        conn.close()
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> dict:
        """
        Xác thực API key
        Returns: {valid: bool, device_id: str, error: str}
        """
        if not api_key or not api_key.startswith('meilin_pk_'):
            return {'valid': False, 'error': 'Invalid API key format'}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, is_active FROM api_keys 
            WHERE api_key = ?
        ''', (api_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'valid': False, 'error': 'API key not found'}
        
        device_id, is_active = row
        
        if not is_active:
            return {'valid': False, 'error': 'API key is disabled'}
        
        return {'valid': True, 'device_id': device_id}
    
    def check_rate_limit(self, api_key: str) -> bool:
        """
        Kiểm tra rate limit
        Returns: True nếu được phép, False nếu vượt limit
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        if api_key not in self.request_counts:
            self.request_counts[api_key] = []
        
        # Xóa requests cũ hơn 1 phút
        self.request_counts[api_key] = [
            (ts, count) for ts, count in self.request_counts[api_key]
            if ts > minute_ago
        ]
        
        # Đếm requests trong phút qua
        total_requests = sum(count for _, count in self.request_counts[api_key])
        
        if total_requests >= self.rate_limit:
            return False
        
        # Thêm request mới
        self.request_counts[api_key].append((now, 1))
        return True
    
    def log_request(self, api_key: str, query: str, response_count: int):
        """Log request để tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Log request
        cursor.execute('''
            INSERT INTO request_logs (api_key, query, response_count)
            VALUES (?, ?, ?)
        ''', (api_key, query[:500], response_count))  # Truncate query
        
        # Update last_used và total_requests
        cursor.execute('''
            UPDATE api_keys 
            SET last_used = CURRENT_TIMESTAMP, 
                total_requests = total_requests + 1
            WHERE api_key = ?
        ''', (api_key,))
        
        conn.commit()
        conn.close()
    
    def query_knowledge(self, query: str, top_k: int = 3) -> list:
        """
        Query knowledge base (read-only)
        Returns: List of relevant documents
        """
        try:
            results = self.rag_system.query(query, n_results=top_k)
            
            # Chỉ trả về text, không trả metadata nhạy cảm
            safe_results = []
            for doc in results:
                safe_results.append({
                    'content': doc.get('text', doc.get('content', '')),
                    'relevance': doc.get('score', doc.get('distance', 0))
                })
            
            return safe_results
        except Exception as e:
            print(f"[PublicRAG] Error querying: {e}")
            return []
    
    def get_device_stats(self, api_key: str) -> dict:
        """Lấy thống kê sử dụng của device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, device_name, created_at, last_used, total_requests
            FROM api_keys WHERE api_key = ?
        ''', (api_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        return {
            'device_id': row[0],
            'device_name': row[1],
            'created_at': row[2],
            'last_used': row[3],
            'total_requests': row[4]
        }


# Global instance
_public_rag_api = None

def get_public_rag_api() -> PublicRAGAPI:
    """Get singleton instance"""
    global _public_rag_api
    if _public_rag_api is None:
        _public_rag_api = PublicRAGAPI()
    return _public_rag_api


def require_api_key(f):
    """Decorator để yêu cầu API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'hint': 'Add X-API-Key header or api_key parameter'
            }), 401
        
        api = get_public_rag_api()
        validation = api.validate_api_key(api_key)
        
        if not validation['valid']:
            return jsonify({
                'error': validation['error']
            }), 403
        
        # Check rate limit
        if not api.check_rate_limit(api_key):
            return jsonify({
                'error': 'Rate limit exceeded',
                'limit': f'{api.rate_limit} requests per minute'
            }), 429
        
        # Inject device_id vào request
        request.device_id = validation['device_id']
        request.api_key = api_key
        
        return f(*args, **kwargs)
    return decorated
