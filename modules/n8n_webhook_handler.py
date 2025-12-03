"""
N8n Webhook Handler - Xử lý webhook requests từ N8n và tích hợp với MeiLin
Hỗ trợ real-time communication giữa N8n workflows và MeiLin AI
"""

import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import hashlib
import hmac
from flask import Flask, request, jsonify
import threading

class N8nWebhookHandler:
    """
    Webhook handler để nhận và xử lý requests từ N8n workflows
    Cung cấp REST API endpoints cho N8n để trigger MeiLin actions
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5001, 
                 webhook_secret: str = None):
        self.host = host
        self.port = port
        self.webhook_secret = webhook_secret
        
        # Flask app cho webhook server
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Registered webhook handlers
        self.handlers = {}
        
        # Server thread
        self.server_thread = None
        self.is_running = False
        
        # Setup logging
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging cho webhook handler"""
        logger = logging.getLogger('n8n_webhook_handler')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def setup_routes(self):
        """Setup Flask routes cho webhook endpoints"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'service': 'n8n_webhook_handler',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/webhook/<endpoint_id>', methods=['POST'])
        def handle_webhook(endpoint_id):
            """Main webhook handler endpoint"""
            return self._process_webhook_request(endpoint_id)
        
        @self.app.route('/api/meilin/chat', methods=['POST'])
        def chat_with_meilin():
            """API endpoint để N8n có thể chat với MeiLin"""
            return self._handle_chat_request()
        
        @self.app.route('/api/meilin/process_document', methods=['POST'])
        def process_document():
            """API endpoint để N8n có thể trigger document processing"""
            return self._handle_document_processing()
        
        @self.app.route('/api/meilin/execute_command', methods=['POST'])
        def execute_command():
            """API endpoint để N8n có thể trigger command execution"""
            return self._handle_command_execution()
    
    def _process_webhook_request(self, endpoint_id: str):
        """Xử lý webhook request từ N8n"""
        try:
            # Verify webhook signature nếu có secret
            if self.webhook_secret and not self._verify_webhook_signature():
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid webhook signature'
                }), 401
            
            # Get request data
            data = request.get_json()
            
            self.logger.info(f"Received webhook for endpoint: {endpoint_id}")
            self.logger.debug(f"Webhook data: {data}")
            
            # Tìm handler cho endpoint này
            handler = self.handlers.get(endpoint_id)
            if handler:
                result = handler(data)
                return jsonify({
                    'status': 'success',
                    'message': 'Webhook processed successfully',
                    'result': result,
                    'endpoint_id': endpoint_id,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Default handler nếu không có custom handler
                result = self._default_webhook_handler(endpoint_id, data)
                return jsonify({
                    'status': 'success',
                    'message': 'Webhook processed with default handler',
                    'result': result,
                    'endpoint_id': endpoint_id,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error processing webhook: {e}',
                'endpoint_id': endpoint_id,
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def _verify_webhook_signature(self) -> bool:
        """Verify webhook signature để đảm bảo security"""
        try:
            signature = request.headers.get('X-N8N-Signature')
            if not signature:
                self.logger.warning("No webhook signature provided")
                return False
            
            # Tính toán expected signature
            body = request.get_data()
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            # So sánh signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _default_webhook_handler(self, endpoint_id: str, data: Dict) -> Dict:
        """Default webhook handler"""
        self.logger.info(f"Default handler for {endpoint_id} with data: {data}")
        
        # Log webhook và trả về response đơn giản
        return {
            'handler': 'default',
            'endpoint': endpoint_id,
            'received_data': data,
            'processed_at': datetime.now().isoformat(),
            'message': 'Webhook received and logged'
        }
    
    def _handle_chat_request(self) -> Dict:
        """Xử lý chat request từ N8n"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            user_id = data.get('user_id', 'n8n_user')
            username = data.get('username', 'N8n System')
            
            self.logger.info(f"Chat request from N8n: {message}")
            
            # Import và sử dụng MeiLin chat processor
            from modules.chat_processor import ChatProcessor
            from modules.rag_system import RAGSystem
            
            # Khởi tạo chat processor
            rag_system = RAGSystem()
            chat_processor = ChatProcessor(rag_system)
            
            # Process message
            response = chat_processor.process_message(
                user_message=message,
                username=username,
                user_id=user_id
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Chat processed successfully',
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error handling chat request: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error processing chat: {e}',
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def _handle_document_processing(self) -> Dict:
        """Xử lý document processing request từ N8n"""
        try:
            data = request.get_json()
            file_path = data.get('file_path', '')
            collection_name = data.get('collection_name')
            
            self.logger.info(f"Document processing request: {file_path}")
            
            # Import và sử dụng File Processor
            from modules.file_processor import get_file_processor
            
            processor = get_file_processor()
            result = processor.process_file_upload(file_path, collection_name)
            
            return jsonify({
                'status': 'success',
                'message': 'Document processing completed',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error handling document processing: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error processing document: {e}',
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def _handle_command_execution(self) -> Dict:
        """Xử lý command execution request từ N8n"""
        try:
            data = request.get_json()
            command = data.get('command', '')
            parameters = data.get('parameters', {})
            
            self.logger.info(f"Command execution request: {command}")
            
            # Import và sử dụng Command Executor
            from modules.command_executor import get_command_executor
            
            executor = get_command_executor()
            result = executor.execute_command(command)
            
            return jsonify({
                'status': 'success',
                'message': 'Command executed successfully',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error handling command execution: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error executing command: {e}',
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def register_webhook_handler(self, endpoint_id: str, handler: Callable):
        """Đăng ký custom webhook handler"""
        self.handlers[endpoint_id] = handler
        self.logger.info(f"Registered webhook handler for endpoint: {endpoint_id}")
    
    def unregister_webhook_handler(self, endpoint_id: str):
        """Hủy đăng ký webhook handler"""
        if endpoint_id in self.handlers:
            del self.handlers[endpoint_id]
            self.logger.info(f"Unregistered webhook handler for endpoint: {endpoint_id}")
    
    def start_server(self):
        """Bắt đầu webhook server"""
        if self.is_running:
            self.logger.warning("Webhook server is already running")
            return
        
        def run_server():
            self.is_running = True
            self.logger.info(f"Starting N8n webhook server on {self.host}:{self.port}")
            
            # Disable Flask development server warning
            import os
            os.environ['WERKZEUG_RUN_MAIN'] = 'true'
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False
            )
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.logger.info("N8n webhook server started")
    
    def stop_server(self):
        """Dừng webhook server"""
        self.is_running = False
        
        # Flask server không có cách dừng trực tiếp
        # Nên chúng ta sẽ đánh dấu và để thread tự kết thúc
        self.logger.info("N8n webhook server stopping...")
        
        # Trong production, sử dụng proper shutdown mechanism
        # Tạm thời chỉ log thông báo
    
    def get_server_status(self) -> Dict:
        """Lấy trạng thái webhook server"""
        return {
            'host': self.host,
            'port': self.port,
            'is_running': self.is_running,
            'registered_handlers': len(self.handlers),
            'webhook_secret_configured': self.webhook_secret is not None,
            'timestamp': datetime.now().isoformat()
        }
    
    def create_meilin_integration_endpoints(self):
        """Tạo các integration endpoints mặc định cho MeiLin"""
        
        # Endpoint để N8n có thể query document knowledge
        def document_query_handler(data):
            query = data.get('query', '')
            file_filter = data.get('file_filter')
            
            from modules.file_processor import get_file_processor
            processor = get_file_processor()
            
            results = processor.query_documents(query, file_filter)
            return {
                'query': query,
                'results': results,
                'result_count': len(results)
            }
        
        self.register_webhook_handler('document_query', document_query_handler)
        
        # Endpoint để N8n có thể get user context
        def user_context_handler(data):
            user_id = data.get('user_id')
            days = data.get('days', 7)
            
            from modules.enhanced_memory import get_enhanced_memory
            memory = get_enhanced_memory()
            
            context_summary = memory.build_context_summary(user_id, days)
            user_profile = memory.get_user_profile(user_id)
            
            return {
                'user_id': user_id,
                'context_summary': context_summary,
                'user_profile': user_profile
            }
        
        self.register_webhook_handler('user_context', user_context_handler)
        
        # Endpoint để N8n có thể trigger TTS
        def tts_handler(data):
            text = data.get('text', '')
            voice = data.get('voice', 'default')
            
            from modules.tts_engine import TTSEngine
            tts = TTSEngine()
            
            # Trong thực tế sẽ trả về audio file path hoặc URL
            # Tạm thời chỉ log
            self.logger.info(f"TTS request: {text} with voice: {voice}")
            
            return {
                'text': text,
                'voice': voice,
                'status': 'processed',
                'message': 'TTS request logged'
            }
        
        self.register_webhook_handler('text_to_speech', tts_handler)
        
        self.logger.info("Created default MeiLin integration endpoints")


# Factory function
def get_n8n_webhook_handler(host: str = '0.0.0.0', port: int = 5001, 
                           webhook_secret: str = None):
    """Factory function để tạo N8nWebhookHandler"""
    handler = N8nWebhookHandler(host, port, webhook_secret)
    handler.create_meilin_integration_endpoints()
    handler.start_server()
    return handler


# Test the module
if __name__ == "__main__":
    # Test webhook handler
    handler = get_n8n_webhook_handler(host='localhost', port=5001)
    
    print("N8n Webhook Handler started")
    print(f"Server status: {handler.get_server_status()}")
    
    # Thêm test webhook handler
    def test_handler(data):
        print(f"Test handler received: {data}")
        return {'processed': True, 'test': 'success'}
    
    handler.register_webhook_handler('test_endpoint', test_handler)
    
    print("Registered test endpoint: /webhook/test_endpoint")
    print("Webhook server is running... Press Ctrl+C to stop")
    
    try:
        # Giữ server chạy
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping webhook server...")
        handler.stop_server()
