"""
User Manager for MeiLin Multi-User System
Handles user creation, configuration, and management
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class UserManager:
    """Manages user data and configuration in SQLite database"""
    
    def __init__(self, db_path: str = "database/users.db"):
        """
        Initialize UserManager with database path
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read and execute schema SQL - try multiple locations
            possible_schema_paths = [
                Path(__file__).parent.parent.parent / "database" / "schema.sql",  # server/database
                Path(__file__).parent.parent.parent.parent / "database" / "schema.sql",  # root/database
                Path("database/schema.sql"),  # relative
            ]
            
            schema_loaded = False
            for schema_path in possible_schema_paths:
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    cursor.executescript(schema_sql)
                    logger.info(f"Database schema initialized from {schema_path}")
                    schema_loaded = True
                    break
            
            if not schema_loaded:
                logger.warning("Schema file not found, creating basic tables")
                self._create_basic_tables(cursor)
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _create_basic_tables(self, cursor):
        """Create basic tables if schema file doesn't exist"""
        # Basic users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                config_state TEXT DEFAULT 'initial'
            )
        ''')
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    
    # User Management Methods
    
    def create_user(self, telegram_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None,
                   language_code: str = 'vi') -> Optional[int]:
        """
        Create a new user
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: First name
            last_name: Last name
            language_code: Language code (default: 'vi')
        
        Returns:
            User ID if successful, None otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (telegram_id, username, first_name, last_name, language_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name, language_code))
            
            if cursor.rowcount == 0:
                # User already exists, get existing user ID
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
                result = cursor.fetchone()
                user_id = result['id'] if result else None
            else:
                user_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            if user_id:
                logger.info(f"User created/retrieved: {telegram_id} (ID: {user_id})")
                # Create default personality config
                self.create_default_personality_config(user_id)
            
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
    
    def get_user(self, user_id: int = None, telegram_id: str = None) -> Optional[Dict]:
        """
        Get user by ID or Telegram ID
        
        Args:
            user_id: User ID
            telegram_id: Telegram user ID
        
        Returns:
            User dictionary or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            elif telegram_id:
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            else:
                return None
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_config_state(self, user_id: int, config_state: str) -> bool:
        """
        Update user configuration state
        
        Args:
            user_id: User ID
            config_state: New configuration state
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET config_state = ?, last_interaction = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (config_state, user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated user {user_id} config state to {config_state}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user config state: {e}")
            return False
    
    def update_last_interaction(self, user_id: int) -> bool:
        """Update user's last interaction timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET last_interaction = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating last interaction: {e}")
            return False
    
    # API Configuration Methods
    
    def save_api_config(self, user_id: int, provider_type: str, provider_name: str,
                       api_key: str = None, api_base: str = None, model: str = None,
                       is_default: bool = False) -> bool:
        """
        Save API configuration for user
        
        Args:
            user_id: User ID
            provider_type: 'llm', 'tts', or 'embedding'
            provider_name: Provider name (deepseek, openai, elevenlabs, etc.)
            api_key: API key (will be encrypted by caller)
            api_base: API base URL
            model: Model name
            is_default: Whether this is the default provider
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # If setting as default, unset other defaults of same type
            if is_default:
                cursor.execute('''
                    UPDATE user_api_configs 
                    SET is_default = 0 
                    WHERE user_id = ? AND provider_type = ?
                ''', (user_id, provider_type))
            
            # Insert or update configuration
            cursor.execute('''
                INSERT OR REPLACE INTO user_api_configs 
                (user_id, provider_type, provider_name, api_key, api_base, model, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, provider_type, provider_name, api_key, api_base, model, is_default))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved API config for user {user_id}: {provider_type}/{provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving API config: {e}")
            return False
    
    def get_api_config(self, user_id: int, provider_type: str = None, 
                      provider_name: str = None) -> List[Dict]:
        """
        Get API configuration for user
        
        Args:
            user_id: User ID
            provider_type: Filter by provider type
            provider_name: Filter by provider name
        
        Returns:
            List of API configurations
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if provider_type and provider_name:
                cursor.execute('''
                    SELECT * FROM user_api_configs 
                    WHERE user_id = ? AND provider_type = ? AND provider_name = ?
                ''', (user_id, provider_type, provider_name))
            elif provider_type:
                cursor.execute('''
                    SELECT * FROM user_api_configs 
                    WHERE user_id = ? AND provider_type = ?
                ''', (user_id, provider_type))
            else:
                cursor.execute('''
                    SELECT * FROM user_api_configs 
                    WHERE user_id = ?
                ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting API config: {e}")
            return []
    
    def get_default_api_config(self, user_id: int, provider_type: str) -> Optional[Dict]:
        """
        Get default API configuration for user
        
        Args:
            user_id: User ID
            provider_type: 'llm' or 'tts'
        
        Returns:
            Default API configuration or None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_api_configs 
                WHERE user_id = ? AND provider_type = ? AND is_default = 1
                LIMIT 1
            ''', (user_id, provider_type))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting default API config: {e}")
            return None
    
    # Personality Configuration Methods
    
    def create_default_personality_config(self, user_id: int) -> bool:
        """Create default personality configuration for user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO user_personality_configs 
                (user_id, character_name, wake_word, personality_mode, temperature, response_style)
                VALUES (?, 'MeiLin', 'hey meilin', 'friendly', 0.7, 'concise')
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating default personality config: {e}")
            return False
    
    def update_personality_config(self, user_id: int, **kwargs) -> bool:
        """
        Update personality configuration
        
        Args:
            user_id: User ID
            **kwargs: Personality configuration fields
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build update query
            fields = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['character_name', 'wake_word', 'personality_mode', 
                          'temperature', 'response_style', 'custom_responses']:
                    fields.append(f"{key} = ?")
                    
                    if key == 'custom_responses' and isinstance(value, dict):
                        values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        values.append(value)
            
            if not fields:
                return False
            
            values.append(user_id)
            
            query = f'''
                UPDATE user_personality_configs 
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            '''
            
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated personality config for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating personality config: {e}")
            return False
    
    def get_personality_config(self, user_id: int) -> Optional[Dict]:
        """Get personality configuration for user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_personality_configs 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                config = dict(row)
                # Parse custom_responses JSON
                if config.get('custom_responses'):
                    try:
                        config['custom_responses'] = json.loads(config['custom_responses'])
                    except:
                        config['custom_responses'] = {}
                return config
            return None
            
        except Exception as e:
            logger.error(f"Error getting personality config: {e}")
            return None
    
    # User Configuration Summary
    
    def get_user_config_summary(self, user_id: int) -> Dict:
        """
        Get complete user configuration summary
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with user configuration summary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_row = cursor.fetchone()
            
            if not user_row:
                return {}
            
            user_info = dict(user_row)
            
            # Get API configs
            cursor.execute('SELECT * FROM user_api_configs WHERE user_id = ?', (user_id,))
            api_configs = [dict(row) for row in cursor.fetchall()]
            
            # Get personality config
            personality_config = self.get_personality_config(user_id)
            
            # Get conversation count
            cursor.execute('SELECT COUNT(*) as count FROM user_conversation_history WHERE user_id = ?', (user_id,))
            conversation_count = cursor.fetchone()['count']
            
            conn.close()
            
            return {
                'user_info': user_info,
                'api_configs': api_configs,
                'personality_config': personality_config,
                'conversation_count': conversation_count,
                'config_complete': user_info.get('config_state') == 'completed'
            }
            
        except Exception as e:
            logger.error(f"Error getting user config summary: {e}")
            return {}
    
    # Conversation History Methods
    
    def save_conversation(self, user_id: int, message_type: str, message_text: str,
                         message_tokens: int = 0, response_tokens: int = 0,
                         provider_used: str = None) -> bool:
        """
        Save conversation message
        
        Args:
            user_id: User ID
            message_type: 'user' or 'assistant'
            message_text: Message text
            message_tokens: Number of tokens in message
            response_tokens: Number of tokens in response (for assistant messages)
            provider_used: Provider used for response
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            total_tokens = message_tokens + response_tokens
            
            cursor.execute('''
                INSERT INTO user_conversation_history 
                (user_id, message_type, message_text, message_tokens, 
                 response_tokens, total_tokens, provider_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, message_type, message_text, message_tokens, 
                  response_tokens, total_tokens, provider_used))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get conversation history for user
        
        Args:
            user_id: User ID
            limit: Maximum number of messages to return
        
        Returns:
            List of conversation messages
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_conversation_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Return in chronological order
            return [dict(row) for row in reversed(rows)]
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    # Utility Methods
    
    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Get all users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute('SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC')
            else:
                cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user and all associated data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete user (cascade will delete related records)
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1')
            result = cursor.fetchone()
            conn.close()
            
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0

    # STT Configuration Methods
    
    def save_stt_config(self, user_id: int, provider_name: str,
                       api_key: str = None, model: str = None) -> bool:
        """
        Save STT configuration for user
        
        Args:
            user_id: User ID
            provider_name: Provider name (vosk, groq, openai)
            api_key: API key (required for groq, openai)
            model: Model name (optional, e.g., whisper-large-v3)
        
        Returns:
            True if successful, False otherwise
        """
        return self.save_api_config(
            user_id=user_id,
            provider_type='stt',
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            is_default=True  # STT config is always default (only one active)
        )
    
    def get_stt_config(self, user_id: int) -> Optional[Dict]:
        """
        Get STT configuration for user
        
        Args:
            user_id: User ID
        
        Returns:
            STT configuration or default Vosk config
        """
        config = self.get_default_api_config(user_id, 'stt')
        
        # Return default Vosk config if no config exists
        if not config:
            return {
                'provider_name': 'vosk',
                'api_key': None,
                'model': 'vosk-model-small-vn-0.4',
                'is_default': True
            }
        
        return config
    
    def get_stt_provider_name(self, user_id: int) -> str:
        """
        Get current STT provider name for user
        
        Args:
            user_id: User ID
        
        Returns:
            Provider name (vosk, groq, openai)
        """
        config = self.get_stt_config(user_id)
        return config.get('provider_name', 'vosk')


# Singleton instance
_user_manager_instance = None

def get_user_manager(db_path: str = "database/users.db") -> UserManager:
    """Get or create UserManager singleton instance"""
    global _user_manager_instance
    if _user_manager_instance is None:
        _user_manager_instance = UserManager(db_path)
    return _user_manager_instance


if __name__ == "__main__":
    # Test the UserManager
    import sys
