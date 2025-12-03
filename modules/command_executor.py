"""
Command Executor - Xử lý lệnh điều khiển thiết bị
Tích hợp với ESP32, HTTP API, hoặc Telegram Bot
"""
import re
import json
import requests
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class CommandExecutor:
    """Phát hiện và thực thi lệnh điều khiển thiết bị"""
    
    def __init__(self, config_path: str = "config/commands.json"):
        self.config_path = Path(config_path)
        self.commands = self._load_commands()
        
    def _load_commands(self) -> Dict[str, Any]:
        """Load danh sách lệnh từ config"""
        if not self.config_path.exists():
            default_commands = {
                "wake_computer": {
                    "keywords": ["mở máy tính", "bật máy tính", "wake computer", "khởi động máy"],
                    "type": "http",  # hoặc "telegram"
                    "http_config": {
                        "url": "http://your-n8n-webhook-url.com/wake",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"},
                        "body": {"action": "wake", "device": "main_pc"}
                    },
                    "telegram_config": {
                        "bot_token": "YOUR_TELETHON_BOT_TOKEN",
                        "chat_id": "YOUR_CHAT_ID",
                        "message": "wake"
                    },
                    "response": "Đã gửi lệnh mở máy tính cho anh!"
                },
                "turn_on_light": {
                    "keywords": ["bật đèn", "mở đèn", "turn on light"],
                    "type": "http",
                    "http_config": {
                        "url": "http://192.168.1.100/api/light/on",
                        "method": "GET"
                    },
                    "response": "Đã bật đèn rồi nè!"
                },
                "play_music": {
                    "keywords": ["phát nhạc", "mở nhạc", "play music"],
                    "type": "telegram",
                    "telegram_config": {
                        "bot_token": "YOUR_BOT_TOKEN",
                        "chat_id": "YOUR_CHAT_ID",
                        "message": "play_music"
                    },
                    "response": "Để em mở nhạc cho anh nghe nhé!"
                }
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_commands, f, ensure_ascii=False, indent=2)
            return default_commands
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def detect_command(self, user_input: str) -> Optional[str]:
        """
        Phát hiện lệnh từ input người dùng
        
        Args:
            user_input: Câu nói của người dùng
            
        Returns:
            Tên lệnh nếu phát hiện, None nếu không
        """
        user_input_lower = user_input.lower().strip()
        
        for command_name, command_config in self.commands.items():
            keywords = command_config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    logger.info(f"Detected command: {command_name} from input: {user_input}")
                    return command_name
        
        return None
    
    def execute_command(self, command_name: str) -> Dict[str, Any]:
        """
        Thực thi lệnh
        
        Args:
            command_name: Tên lệnh cần thực thi
            
        Returns:
            Dict chứa status, response, error (nếu có)
        """
        if command_name not in self.commands:
            return {
                "success": False,
                "error": f"Command '{command_name}' not found",
                "response": "Em không biết cách làm điều đó..."
            }
        
        command = self.commands[command_name]
        command_type = command.get("type", "http")
        
        try:
            if command_type == "http":
                return self._execute_http(command)
            elif command_type == "telegram":
                return self._execute_telegram(command)
            else:
                return {
                    "success": False,
                    "error": f"Unknown command type: {command_type}",
                    "response": "Em không biết cách thực hiện lệnh này..."
                }
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Ối, em gặp lỗi khi thực hiện lệnh: {str(e)}"
            }
    
    def _execute_http(self, command: Dict) -> Dict[str, Any]:
        """Thực thi HTTP request"""
        http_config = command.get("http_config", {})
        url = http_config.get("url")
        method = http_config.get("method", "POST").upper()
        headers = http_config.get("headers", {})
        body = http_config.get("body", {})
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body, timeout=5)
        else:
            response = requests.request(method, url, headers=headers, json=body, timeout=5)
        
        response.raise_for_status()
        
        return {
            "success": True,
            "response": command.get("response", "Đã thực hiện lệnh rồi nè!"),
            "http_status": response.status_code,
            "http_response": response.text
        }
    
    def _execute_telegram(self, command: Dict) -> Dict[str, Any]:
        """Gửi message qua Telegram Bot"""
        telegram_config = command.get("telegram_config", {})
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        message = telegram_config.get("message")
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        
        return {
            "success": True,
            "response": command.get("response", "Đã gửi lệnh rồi nè!"),
            "telegram_response": response.json()
        }
    
    def process_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Xử lý input và tự động thực thi lệnh nếu phát hiện
        
        Args:
            user_input: Câu nói của người dùng
            
        Returns:
            Kết quả thực thi hoặc None nếu không phát hiện lệnh
        """
        command_name = self.detect_command(user_input)
        if command_name:
            return self.execute_command(command_name)
        return None


# Singleton instance
_command_executor = None

def get_command_executor(config_path: str = "config/commands.json") -> CommandExecutor:
    """Get singleton instance của CommandExecutor"""
    global _command_executor
    if _command_executor is None:
        _command_executor = CommandExecutor(config_path)
    return _command_executor
