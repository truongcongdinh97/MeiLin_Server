"""
Config Loader with Environment Variable Support
Load YAML configs and replace ${VAR} with values from .env
"""
import os
import re
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def replace_env_vars(value):
    """
    Replace ${VAR_NAME} in string with environment variable value
    
    Examples:
        "${API_KEY}" -> "sk-abc123..."
        "https://${HOST}/api" -> "https://example.com/api"
    """
    if not isinstance(value, str):
        return value
    
    # Pattern: ${VAR_NAME}
    pattern = r'\$\{([^}]+)\}'
    
    def replacer(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        
        if env_value is None:
            print(f"⚠️ Warning: Environment variable '{var_name}' not found, using empty string")
            return ""
        
        return env_value
    
    return re.sub(pattern, replacer, value)

def load_config_with_env(config_path):
    """
    Load YAML config and replace all ${VAR} with environment variables
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        dict: Config with environment variables replaced
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return replace_env_recursive(config)

def replace_env_recursive(obj):
    """
    Recursively replace ${VAR} in all strings in nested dict/list
    """
    if isinstance(obj, dict):
        return {k: replace_env_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_env_recursive(item) for item in obj]
    elif isinstance(obj, str):
        return replace_env_vars(obj)
    else:
        return obj

def get_env(var_name, default=None):
    """
    Get environment variable with fallback
    
    Args:
        var_name: Environment variable name
        default: Default value if not found
        
    Returns:
        str: Environment variable value or default
    """
    return os.getenv(var_name, default)

# Export functions
__all__ = ['load_config_with_env', 'get_env', 'replace_env_vars']

if __name__ == "__main__":
    # Test
    print("Testing config loader...")
    
    # Test database.yaml
    db_config = load_config_with_env('config/database.yaml')
    print("\nDatabase Config:")
    print(f"  API URL: {db_config['chromadb']['api_url']}")
    print(f"  Knowledge Collection: {db_config['chromadb']['collections']['knowledge']['id']}")
    print(f"  CF Client ID: {db_config['chromadb']['headers']['CF-Access-Client-Id'][:20]}...")
    
    # Test ai_providers.yaml
    ai_config = load_config_with_env('config/ai_providers.yaml')
    print("\nAI Providers Config:")
    deepseek_key_env = ai_config['llm_providers']['deepseek']['api_key_env']
    print(f"  Deepseek API Key Env: {deepseek_key_env}")
    print(f"  Deepseek API Key Value: {get_env(deepseek_key_env, 'not found')[:20]}...")
    print(f"  Active LLM: {ai_config['active']['llm']}")
