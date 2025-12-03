"""
ESP Device Manager - Quản lý ESP32 devices đăng ký qua Telegram
Liên kết device_id với telegram_user_id để sử dụng API keys
"""
import os
import secrets
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any


class ESPDeviceManager:
    """
    Quản lý ESP32 devices:
    - Đăng ký device qua Telegram bot
    - Liên kết device với user (để dùng API keys của user)
    - Tạo device API key cho ESP
    - Theo dõi usage statistics
    """
    
    def __init__(self, db_path: str = "data/esp_devices.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Khởi tạo database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bảng devices
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS esp_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_name TEXT,
                device_api_key TEXT UNIQUE NOT NULL,
                telegram_user_id INTEGER NOT NULL,
                mac_address TEXT,
                firmware_version TEXT,
                board_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                total_requests INTEGER DEFAULT 0,
                notes TEXT
            )
        ''')
        
        # Bảng device API keys settings (LLM, TTS)
        # Nếu user chưa set, sẽ dùng keys từ user_manager
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_api_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                setting_type TEXT NOT NULL,
                provider TEXT,
                api_key_encrypted TEXT,
                api_base TEXT,
                model TEXT,
                voice TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_id, setting_type)
            )
        ''')
        
        # Bảng request logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                request_type TEXT,
                request_data TEXT,
                response_status TEXT,
                tokens_used INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index cho performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_telegram ON esp_devices(telegram_user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_api_key ON esp_devices(device_api_key)')
        
        conn.commit()
        conn.close()
    
    def register_device(
        self,
        device_id: str,
        telegram_user_id: int,
        device_name: str = None,
        mac_address: str = None,
        board_type: str = None
    ) -> Dict[str, Any]:
        """
        Đăng ký device mới từ Telegram bot
        Returns: {success, device_api_key, message}
        """
        # Generate unique API key cho device
        device_api_key = f"meilin_dev_{secrets.token_hex(16)}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if device already exists
            cursor.execute('SELECT id, telegram_user_id FROM esp_devices WHERE device_id = ?', (device_id,))
            existing = cursor.fetchone()
            
            if existing:
                if existing[1] == telegram_user_id:
                    # Same user, update device
                    cursor.execute('''
                        UPDATE esp_devices 
                        SET device_name = ?, mac_address = ?, board_type = ?, last_seen = ?
                        WHERE device_id = ?
                    ''', (device_name, mac_address, board_type, datetime.now(), device_id))
                    
                    # Get existing API key
                    cursor.execute('SELECT device_api_key FROM esp_devices WHERE device_id = ?', (device_id,))
                    device_api_key = cursor.fetchone()[0]
                    
                    conn.commit()
                    return {
                        'success': True,
                        'device_api_key': device_api_key,
                        'message': 'Device updated successfully',
                        'is_new': False
                    }
                else:
                    # Different user owns this device
                    return {
                        'success': False,
                        'error': 'Device ID already registered by another user'
                    }
            
            # Register new device
            cursor.execute('''
                INSERT INTO esp_devices 
                (device_id, device_name, device_api_key, telegram_user_id, mac_address, board_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_id, device_name or device_id, device_api_key, telegram_user_id, mac_address, board_type))
            
            conn.commit()
            
            return {
                'success': True,
                'device_api_key': device_api_key,
                'message': 'Device registered successfully',
                'is_new': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def validate_device_key(self, device_api_key: str) -> Dict[str, Any]:
        """
        Validate device API key và lấy thông tin
        Returns: {valid, device_id, telegram_user_id, ...}
        """
        if not device_api_key or not device_api_key.startswith('meilin_dev_'):
            return {'valid': False, 'error': 'Invalid device key format'}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, telegram_user_id, device_name, is_active
            FROM esp_devices WHERE device_api_key = ?
        ''', (device_api_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'valid': False, 'error': 'Device not found'}
        
        device_id, telegram_user_id, device_name, is_active = row
        
        if not is_active:
            return {'valid': False, 'error': 'Device is disabled'}
        
        return {
            'valid': True,
            'device_id': device_id,
            'telegram_user_id': telegram_user_id,
            'device_name': device_name
        }
    
    def get_user_devices(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách devices của user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, device_name, device_api_key, board_type, 
                   firmware_version, last_seen, total_requests, is_active
            FROM esp_devices WHERE telegram_user_id = ?
            ORDER BY created_at DESC
        ''', (telegram_user_id,))
        
        devices = []
        for row in cursor.fetchall():
            devices.append({
                'device_id': row[0],
                'device_name': row[1],
                'device_api_key': row[2][:20] + '...',  # Hide full key
                'board_type': row[3],
                'firmware_version': row[4],
                'last_seen': row[5],
                'total_requests': row[6],
                'is_active': row[7]
            })
        
        conn.close()
        return devices
    
    def update_device_seen(self, device_id: str):
        """Cập nhật last_seen và increment request count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE esp_devices 
            SET last_seen = ?, total_requests = total_requests + 1
            WHERE device_id = ?
        ''', (datetime.now(), device_id))
        
        conn.commit()
        conn.close()
    
    def delete_device(self, device_id: str, telegram_user_id: int) -> bool:
        """Xóa device (chỉ owner mới xóa được)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM esp_devices 
            WHERE device_id = ? AND telegram_user_id = ?
        ''', (device_id, telegram_user_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def toggle_device(self, device_id: str, telegram_user_id: int, active: bool) -> bool:
        """Enable/disable device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE esp_devices 
            SET is_active = ?
            WHERE device_id = ? AND telegram_user_id = ?
        ''', (active, device_id, telegram_user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def regenerate_device_key(self, device_id: str, telegram_user_id: int) -> Optional[str]:
        """Tạo lại API key cho device"""
        new_key = f"meilin_dev_{secrets.token_hex(16)}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE esp_devices 
            SET device_api_key = ?
            WHERE device_id = ? AND telegram_user_id = ?
        ''', (new_key, device_id, telegram_user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return new_key if updated else None


# Singleton
_esp_device_manager = None

def get_esp_device_manager() -> ESPDeviceManager:
    global _esp_device_manager
    if _esp_device_manager is None:
        _esp_device_manager = ESPDeviceManager()
    return _esp_device_manager
