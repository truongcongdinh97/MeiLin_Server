"""
Environment Configuration Manager for MeiLin
Quản lý các API keys và configuration từ file .env
"""

import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class EnvConfigManager:
    """Quản lý configuration từ environment variables"""
    
    def __init__(self):
        # Load environment variables từ .env file
        load_dotenv()
        self.config = {}
        self.load_all_config()
    
    def load_all_config(self):
        """Load tất cả configuration từ environment variables"""
        try:
            # Telegram Bot Configuration
            self.config['telegram_bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
            
            # AI Provider API Keys
            self.config['elevenlabs_api_key'] = os.getenv('ELEVENLABS_API_KEY')
            self.config['deepseek_api_key'] = os.getenv('DEEPSEEK_API_KEY')
            self.config['openai_api_key'] = os.getenv('OPENAI_API_KEY')
            self.config['claude_api_key'] = os.getenv('CLAUDE_API_KEY')
            self.config['gemini_api_key'] = os.getenv('GEMINI_API_KEY')
            
            # ChromaDB Configuration
            self.config['chromadb_api_url'] = os.getenv('CHROMADB_API_URL')
            self.config['chromadb_cf_client_id'] = os.getenv('CHROMADB_CF_CLIENT_ID')
            self.config['chromadb_cf_client_secret'] = os.getenv('CHROMADB_CF_CLIENT_SECRET')
            self.config['chromadb_knowledge_collection_id'] = os.getenv('CHROMADB_KNOWLEDGE_COLLECTION_ID')
            self.config['chromadb_chat_history_collection_id'] = os.getenv('CHROMADB_CHAT_HISTORY_COLLECTION_ID')
            
            # Embedding Service
            self.config['embedding_api_url'] = os.getenv('EMBEDDING_API_URL')
            self.config['embedding_model'] = os.getenv('EMBEDDING_MODEL')
            
            # N8N Webhook
            self.config['n8n_webhook_url'] = os.getenv('N8N_WEBHOOK_URL')
            
            # Owner Information
            self.config['owner_username'] = os.getenv('OWNER_USERNAME')
            
            logger.info("✅ Environment configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading environment configuration: {e}")
    
    def get_telegram_config(self) -> Dict:
        """Lấy Telegram bot configuration"""
        return {
            'token': self.config.get('telegram_bot_token'),
            'available': bool(self.config.get('telegram_bot_token'))
        }
    
    def get_ai_providers_config(self) -> Dict:
        """Lấy AI providers configuration"""
        return {
            'elevenlabs': {
                'api_key': self.config.get('elevenlabs_api_key'),
                'available': bool(self.config.get('elevenlabs_api_key'))
            },
            'deepseek': {
                'api_key': self.config.get('deepseek_api_key'),
                'available': bool(self.config.get('deepseek_api_key'))
            },
            'openai': {
                'api_key': self.config.get('openai_api_key'),
                'available': bool(self.config.get('openai_api_key'))
            },
            'claude': {
                'api_key': self.config.get('claude_api_key'),
                'available': bool(self.config.get('claude_api_key'))
            },
            'gemini': {
                'api_key': self.config.get('gemini_api_key'),
                'available': bool(self.config.get('gemini_api_key'))
            }
        }
    
    def get_chromadb_config(self) -> Dict:
        """Lấy ChromaDB configuration"""
        return {
            'api_url': self.config.get('chromadb_api_url'),
            'cf_client_id': self.config.get('chromadb_cf_client_id'),
            'cf_client_secret': self.config.get('chromadb_cf_client_secret'),
            'knowledge_collection_id': self.config.get('chromadb_knowledge_collection_id'),
            'chat_history_collection_id': self.config.get('chromadb_chat_history_collection_id'),
            'available': all([
                self.config.get('chromadb_api_url'),
                self.config.get('chromadb_cf_client_id'),
                self.config.get('chromadb_cf_client_secret')
            ])
        }
    
    def get_embedding_config(self) -> Dict:
        """Lấy embedding service configuration"""
        return {
            'api_url': self.config.get('embedding_api_url'),
            'model': self.config.get('embedding_model'),
            'available': bool(self.config.get('embedding_api_url'))
        }
    
    def get_n8n_config(self) -> Dict:
        """Lấy N8N configuration"""
        return {
            'webhook_url': self.config.get('n8n_webhook_url'),
            'available': bool(self.config.get('n8n_webhook_url'))
        }
    
    def get_owner_info(self) -> Dict:
        """Lấy owner information"""
        return {
            'username': self.config.get('owner_username', 'Unknown'),
            'available': bool(self.config.get('owner_username'))
        }
    
    def get_config_summary(self) -> Dict:
        """Lấy summary của tất cả configuration"""
        telegram_config = self.get_telegram_config()
        ai_config = self.get_ai_providers_config()
        chromadb_config = self.get_chromadb_config()
        embedding_config = self.get_embedding_config()
        n8n_config = self.get_n8n_config()
        owner_info = self.get_owner_info()
        
        # Count available providers
        available_ai_providers = sum(1 for provider in ai_config.values() if provider['available'])
        
        return {
            'status': 'success',
            'summary': {
                'owner': owner_info,
                'telegram_bot': {
                    'available': telegram_config['available'],
                    'token_present': bool(telegram_config['token'])
                },
                'ai_providers': {
                    'total': len(ai_config),
                    'available': available_ai_providers,
                    'providers': {name: config['available'] for name, config in ai_config.items()}
                },
                'chromadb': {
                    'available': chromadb_config['available'],
                    'collections': {
                        'knowledge': bool(chromadb_config['knowledge_collection_id']),
                        'chat_history': bool(chromadb_config['chat_history_collection_id'])
                    }
                },
                'embedding_service': {
                    'available': embedding_config['available'],
                    'model': embedding_config['model']
                },
                'n8n_integration': {
                    'available': n8n_config['available'],
                    'webhook_url_present': bool(n8n_config['webhook_url'])
                }
            }
        }
    
    def update_ai_provider_config(self, provider_name: str, api_key: str) -> Dict:
        """Cập nhật AI provider configuration"""
        try:
            # Map provider names to environment variable names
            provider_map = {
                'elevenlabs': 'ELEVENLABS_API_KEY',
                'deepseek': 'DEEPSEEK_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'claude': 'CLAUDE_API_KEY',
                'gemini': 'GEMINI_API_KEY'
            }
            
            if provider_name not in provider_map:
                return {
                    'status': 'error',
                    'message': f'❌ Provider {provider_name} không được hỗ trợ'
                }
            
            env_var_name = provider_map[provider_name]
            
            # Update environment variable (in memory)
            os.environ[env_var_name] = api_key
            self.config[f'{provider_name}_api_key'] = api_key
            
            # Update .env file
            self._update_env_file(env_var_name, api_key)
            
            logger.info(f"✅ AI provider {provider_name} configuration updated")
            return {
                'status': 'success',
                'message': f'✅ AI provider {provider_name} đã được cập nhật thành công!'
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating AI provider {provider_name}: {e}")
            return {
                'status': 'error',
                'message': f'❌ Lỗi khi cập nhật AI provider {provider_name}: {e}'
            }
    
    def _update_env_file(self, env_var_name: str, value: str):
        """Cập nhật giá trị trong file .env"""
        try:
            env_file_path = '.env'
            
            # Read current .env file
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Find and update the variable
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f'{env_var_name}='):
                    lines[i] = f'{env_var_name}={value}\n'
                    updated = True
                    break
            
            # If not found, add new line
            if not updated:
                lines.append(f'{env_var_name}={value}\n')
            
            # Write back to .env file
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
                
            logger.info(f"✅ .env file updated for {env_var_name}")
            
        except Exception as e:
            logger.error(f"❌ Error updating .env file: {e}")
            raise


# Factory function
def get_env_config_manager() -> EnvConfigManager:
    """Factory function để tạo EnvConfigManager instance"""
    return EnvConfigManager()


# Test function
if __name__ == "__main__":
    # Test the environment config manager
    manager = get_env_config_manager()
    
    print("=== TESTING ENVIRONMENT CONFIG MANAGER ===")
    
    # Get config summary
    summary = manager.get_config_summary()
    print(f"Config Summary: {summary}")
    
    # Test individual configurations
    print(f"\nTelegram Config: {manager.get_telegram_config()}")
    print(f"AI Providers Config: {manager.get_ai_providers_config()}")
    print(f"ChromaDB Config: {manager.get_chromadb_config()}")
    print(f"Embedding Config: {manager.get_embedding_config()}")
    print(f"N8N Config: {manager.get_n8n_config()}")
    print(f"Owner Info: {manager.get_owner_info()}")
