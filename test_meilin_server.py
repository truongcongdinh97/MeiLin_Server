#!/usr/bin/env python3
"""
Test script for MeiLin Full Control Server components
Run this to verify all components are working correctly before deployment

Usage:
    python test_meilin_server.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported"""
    print("=" * 60)
    print("🧪 Testing Module Imports")
    print("=" * 60)
    
    results = []
    
    # Test STT Engine
    try:
        from modules.stt_engine import STTEngine, STT_PROVIDERS, VoskSTTProvider, GroqSTTProvider, OpenAISTTProvider
        results.append(("✅", "stt_engine", "All STT providers imported"))
    except ImportError as e:
        results.append(("❌", "stt_engine", f"Import error: {e}"))
    
    # Test WebSocket Server
    try:
        from modules.websocket_server import MeiLinWebSocketServer, ClientSession
        results.append(("✅", "websocket_server", "WebSocket server imported"))
    except ImportError as e:
        results.append(("❌", "websocket_server", f"Import error: {e}"))
    
    # Test User Manager
    try:
        from modules.multi_user.user_manager import UserManager, get_user_manager
        results.append(("✅", "user_manager", "User manager imported"))
    except ImportError as e:
        results.append(("❌", "user_manager", f"Import error: {e}"))
    
    # Test Chat Processor
    try:
        from modules.chat_processor import ChatProcessor
        results.append(("✅", "chat_processor", "Chat processor imported"))
    except ImportError as e:
        results.append(("❌", "chat_processor", f"Import error: {e}"))
    
    # Test RAG System
    try:
        from modules.rag_system import RAGSystem
        results.append(("✅", "rag_system", "RAG system imported"))
    except ImportError as e:
        results.append(("❌", "rag_system", f"Import error: {e}"))
    
    # Print results
    for status, module, message in results:
        print(f"{status} {module}: {message}")
    
    passed = sum(1 for r in results if r[0] == "✅")
    total = len(results)
    print(f"\n📊 Import Tests: {passed}/{total} passed")
    
    return passed == total


def test_stt_providers():
    """Test STT provider registry"""
    print("\n" + "=" * 60)
    print("🧪 Testing STT Providers Registry")
    print("=" * 60)
    
    try:
        from modules.stt_engine import STT_PROVIDERS, STTEngine
        
        print(f"📋 Available STT Providers: {len(STT_PROVIDERS)}")
        for provider_id, info in STT_PROVIDERS.items():
            key_status = "🔑 Requires API key" if info['requires_api_key'] else "🆓 No API key needed"
            print(f"  • {provider_id}: {info['name']} - {key_status}")
        
        # Test default provider creation
        print("\n🔧 Testing default provider (Vosk)...")
        try:
            default_provider = STTEngine.get_default_provider()
            print(f"✅ Default provider created: {default_provider.name}")
        except Exception as e:
            print(f"⚠️ Default provider not available (Vosk model may need download): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ STT Provider test failed: {e}")
        return False


def test_user_manager_stt():
    """Test UserManager STT methods"""
    print("\n" + "=" * 60)
    print("🧪 Testing UserManager STT Methods")
    print("=" * 60)
    
    try:
        from modules.multi_user.user_manager import get_user_manager
        
        um = get_user_manager()
        
        # Check if methods exist
        methods = ['save_stt_config', 'get_stt_config', 'get_stt_provider_name']
        for method in methods:
            if hasattr(um, method):
                print(f"✅ Method exists: {method}")
            else:
                print(f"❌ Method missing: {method}")
                return False
        
        # Test get_stt_config with non-existent user (should return default)
        config = um.get_stt_config(999999)
        print(f"✅ Default STT config: {config}")
        
        return True
        
    except Exception as e:
        print(f"❌ UserManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_deps():
    """Test WebSocket dependencies"""
    print("\n" + "=" * 60)
    print("🧪 Testing WebSocket Dependencies")
    print("=" * 60)
    
    deps_status = []
    
    # Test websockets
    try:
        import websockets
        deps_status.append(("✅", "websockets", f"v{websockets.__version__}"))
    except ImportError:
        deps_status.append(("❌", "websockets", "Not installed (pip install websockets)"))
    
    # Test opuslib (optional)
    try:
        import opuslib
        deps_status.append(("✅", "opuslib", "Opus codec available"))
    except ImportError:
        deps_status.append(("⚠️", "opuslib", "Not installed (optional, needed for Opus audio)"))
    
    # Test vosk (optional)
    try:
        import vosk
        deps_status.append(("✅", "vosk", "Vosk STT available"))
    except ImportError:
        deps_status.append(("⚠️", "vosk", "Not installed (pip install vosk)"))
    
    # Test groq (optional)
    try:
        import groq
        deps_status.append(("✅", "groq", "Groq Whisper available"))
    except ImportError:
        deps_status.append(("⚠️", "groq", "Not installed (pip install groq)"))
    
    # Test pydub (for audio conversion)
    try:
        from pydub import AudioSegment
        deps_status.append(("✅", "pydub", "Audio conversion available"))
    except ImportError:
        deps_status.append(("⚠️", "pydub", "Not installed (pip install pydub)"))
    
    for status, dep, message in deps_status:
        print(f"{status} {dep}: {message}")
    
    required_ok = all(s[0] == "✅" for s in deps_status if s[1] == "websockets")
    return required_ok


def test_telegram_bot_stt():
    """Test Telegram bot STT configuration"""
    print("\n" + "=" * 60)
    print("🧪 Testing Telegram Bot STT Configuration")
    print("=" * 60)
    
    try:
        # Check if STT_PROVIDERS exists in telegram_bot
        import importlib.util
        bot_path = Path(__file__).parent / "bot" / "telegram_bot.py"
        
        if bot_path.exists():
            with open(bot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ("STT_PROVIDERS", "STT providers configuration"),
                ("STT_MENU", "STT menu state"),
                ("STT_SELECT_PROVIDER", "STT provider selection state"),
                ("STT_ENTER_KEY", "STT API key entry state"),
                ("menu_stt", "STT menu handler"),
                ("stt_select_provider", "STT provider selection handler"),
                ("stt_enter_key", "STT API key handler"),
            ]
            
            for check, desc in checks:
                if check in content:
                    print(f"✅ {desc}: Found '{check}'")
                else:
                    print(f"❌ {desc}: Missing '{check}'")
                    return False
            
            return True
        else:
            print(f"❌ Telegram bot file not found: {bot_path}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram bot test failed: {e}")
        return False


def test_database_schema():
    """Test database schema for STT configuration"""
    print("\n" + "=" * 60)
    print("🧪 Testing Database Schema for STT")
    print("=" * 60)
    
    try:
        # Check multiple possible locations
        possible_paths = [
            Path(__file__).parent / "database" / "schema.sql",
            Path(__file__).parent.parent / "database" / "schema.sql",
        ]
        
        schema_path = None
        for p in possible_paths:
            if p.exists():
                schema_path = p
                break
        
        if schema_path:
            print(f"📁 Found schema at: {schema_path}")
            with open(schema_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "default_stt_provider" in content:
                print("✅ default_stt_provider found in schema")
            else:
                print("❌ default_stt_provider not found in schema")
                return False
            
            if "vosk" in content:
                print("✅ Vosk (free default) configured in schema")
            else:
                print("⚠️ Vosk default not explicitly set")
            
            return True
        else:
            print(f"⚠️ Schema file not found in expected locations")
            print("  This is OK if database is already initialized")
            return True  # Don't fail if schema not found
            
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 MeiLin Full Control Server - Component Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Module Imports", test_imports),
        ("STT Providers", test_stt_providers),
        ("UserManager STT", test_user_manager_stt),
        ("WebSocket Dependencies", test_websocket_deps),
        ("Telegram Bot STT", test_telegram_bot_stt),
        ("Database Schema", test_database_schema),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Server is ready to run.")
        print("\nTo start the server:")
        print("  python run_meilin_server.py")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")
        print("\nYou may need to install missing dependencies:")
        print("  pip install -r requirements.txt")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
