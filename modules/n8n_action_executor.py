"""
N8n Action Executor - Thực thi các action từ N8n workflows trong MeiLin
Cung cấp unified interface để N8n có thể trigger mọi tính năng của MeiLin
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

class ActionType(Enum):
    """Các loại action có thể thực thi từ N8n"""
    CHAT = "chat"
    DOCUMENT_PROCESSING = "document_processing"
    COMMAND_EXECUTION = "command_execution"
    DATA_ANALYSIS = "data_analysis"
    NOTIFICATION = "notification"
    REPORT_GENERATION = "report_generation"
    TTS = "text_to_speech"
    MEMORY_QUERY = "memory_query"
    WORKFLOW_TRIGGER = "workflow_trigger"

class N8nActionExecutor:
    """
    Executor để thực thi các action từ N8n workflows
    Cung cấp unified interface cho tất cả MeiLin capabilities
    """
    
    def __init__(self):
        # Action registry
        self.action_handlers = {}
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Register default actions
        self._register_default_actions()
    
    def _setup_logging(self):
        """Setup logging cho action executor"""
        logger = logging.getLogger('n8n_action_executor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _register_default_actions(self):
        """Đăng ký các action handlers mặc định"""
        
        # Chat action
        self.register_action(
            ActionType.CHAT,
            self._handle_chat_action
        )
        
        # Document processing action
        self.register_action(
            ActionType.DOCUMENT_PROCESSING,
            self._handle_document_processing_action
        )
        
        # Command execution action
        self.register_action(
            ActionType.COMMAND_EXECUTION,
            self._handle_command_execution_action
        )
        
        # Data analysis action
        self.register_action(
            ActionType.DATA_ANALYSIS,
            self._handle_data_analysis_action
        )
        
        # Notification action
        self.register_action(
            ActionType.NOTIFICATION,
            self._handle_notification_action
        )
        
        # Report generation action
        self.register_action(
            ActionType.REPORT_GENERATION,
            self._handle_report_generation_action
        )
        
        # TTS action
        self.register_action(
            ActionType.TTS,
            self._handle_tts_action
        )
        
        # Memory query action
        self.register_action(
            ActionType.MEMORY_QUERY,
            self._handle_memory_query_action
        )
        
        # Workflow trigger action
        self.register_action(
            ActionType.WORKFLOW_TRIGGER,
            self._handle_workflow_trigger_action
        )
        
        self.logger.info("Registered default action handlers")
    
    def register_action(self, action_type: ActionType, handler: Callable):
        """Đăng ký action handler"""
        self.action_handlers[action_type] = handler
        self.logger.info(f"Registered handler for action: {action_type.value}")
    
    def unregister_action(self, action_type: ActionType):
        """Hủy đăng ký action handler"""
        if action_type in self.action_handlers:
            del self.action_handlers[action_type]
            self.logger.info(f"Unregistered handler for action: {action_type.value}")
    
    def execute_action(self, action_type: str, parameters: Dict) -> Dict:
        """
        Thực thi action với parameters
        """
        try:
            # Convert string action type to enum
            try:
                action_enum = ActionType(action_type)
            except ValueError:
                return {
                    'status': 'error',
                    'message': f'Unknown action type: {action_type}',
                    'available_actions': [action.value for action in ActionType]
                }
            
            # Tìm handler
            handler = self.action_handlers.get(action_enum)
            if not handler:
                return {
                    'status': 'error',
                    'message': f'No handler registered for action: {action_type}'
                }
            
            self.logger.info(f"Executing action: {action_type} with parameters: {parameters}")
            
            # Thực thi handler
            result = handler(parameters)
            
            # Thêm metadata
            result['action_type'] = action_type
            result['executed_at'] = datetime.now().isoformat()
            
            self.logger.info(f"Action {action_type} executed successfully")
            
            return {
                'status': 'success',
                'message': f'Action {action_type} executed successfully',
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error executing action {action_type}: {e}")
            return {
                'status': 'error',
                'message': f'Error executing action {action_type}: {e}',
                'action_type': action_type,
                'executed_at': datetime.now().isoformat()
            }
    
    def _handle_chat_action(self, parameters: Dict) -> Dict:
        """Xử lý chat action"""
        try:
            message = parameters.get('message', '')
            user_id = parameters.get('user_id', 'n8n_user')
            username = parameters.get('username', 'N8n System')
            context = parameters.get('context', {})
            
            from modules.chat_processor import ChatProcessor
            from modules.rag_system import RAGSystem
            
            rag_system = RAGSystem()
            chat_processor = ChatProcessor(rag_system)
            
            # Sử dụng long context manager nếu có context
            if context:
                from modules.long_context_manager import get_long_context_manager
                context_manager = get_long_context_manager()
                
                # Build mega prompt với context
                history = context.get('history', [])
                documents = context.get('documents', [])
                
                prompt = context_manager.build_mega_prompt(
                    user_input=message,
                    history=history,
                    documents=documents
                )
                
                # Ghi đè message với prompt đã được xử lý
                message = prompt
            
            response = chat_processor.process_message(
                user_message=message,
                username=username,
                user_id=user_id
            )
            
            return {
                'input_message': message,
                'ai_response': response,
                'user_id': user_id,
                'username': username
            }
            
        except Exception as e:
            self.logger.error(f"Error in chat action: {e}")
            return {
                'error': str(e),
                'action': 'chat'
            }
    
    def _handle_document_processing_action(self, parameters: Dict) -> Dict:
        """Xử lý document processing action"""
        try:
            file_path = parameters.get('file_path', '')
            collection_name = parameters.get('collection_name')
            chunk_size = parameters.get('chunk_size', 500)
            chunk_overlap = parameters.get('chunk_overlap', 50)
            
            from modules.file_processor import get_file_processor
            
            processor = get_file_processor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            result = processor.process_file_upload(file_path, collection_name)
            
            return {
                'file_path': file_path,
                'processing_result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error in document processing action: {e}")
            return {
                'error': str(e),
                'action': 'document_processing'
            }
    
    def _handle_command_execution_action(self, parameters: Dict) -> Dict:
        """Xử lý command execution action"""
        try:
            command_name = parameters.get('command', '')
            command_params = parameters.get('parameters', {})
            
            from modules.command_executor import get_command_executor
            
            executor = get_command_executor()
            
            # Detect command từ input
            detected_command = executor.detect_command(command_name)
            if detected_command:
                command_name = detected_command
            
            result = executor.execute_command(command_name)
            
            return {
                'command': command_name,
                'execution_result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error in command execution action: {e}")
            return {
                'error': str(e),
                'action': 'command_execution'
            }
    
    def _handle_data_analysis_action(self, parameters: Dict) -> Dict:
        """Xử lý data analysis action"""
        try:
            data_source = parameters.get('data_source', '')
            analysis_type = parameters.get('analysis_type', 'statistical')
            output_format = parameters.get('output_format', 'json')
            
            # Sử dụng file processor để query data
            from modules.file_processor import get_file_processor
            
            processor = get_file_processor()
            
            # Query documents liên quan đến data analysis
            query = f"{analysis_type} analysis of {data_source}"
            results = processor.query_documents(query, n_results=5)
            
            # Tạo analysis summary
            analysis_result = {
                'data_source': data_source,
                'analysis_type': analysis_type,
                'relevant_documents': len(results),
                'key_insights': [],
                'recommendations': []
            }
            
            # Extract insights từ query results
            for result in results:
                document = result.get('document', '')
                if 'insight' in document.lower() or 'finding' in document.lower():
                    analysis_result['key_insights'].append(document[:200] + '...')
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in data analysis action: {e}")
            return {
                'error': str(e),
                'action': 'data_analysis'
            }
    
    def _handle_notification_action(self, parameters: Dict) -> Dict:
        """Xử lý notification action"""
        try:
            message = parameters.get('message', '')
            channels = parameters.get('channels', ['telegram'])
            priority = parameters.get('priority', 'medium')
            recipients = parameters.get('recipients', [])
            
            # Sử dụng command executor để gửi notification
            from modules.command_executor import get_command_executor
            
            executor = get_command_executor()
            
            notification_result = {
                'message': message,
                'channels': channels,
                'priority': priority,
                'recipients': recipients,
                'delivery_status': {}
            }
            
            # Gửi notification qua các kênh
            for channel in channels:
                if channel == 'telegram':
                    # Trigger Telegram notification command
                    result = executor.execute_command('send_telegram_message')
                    notification_result['delivery_status']['telegram'] = result
                
                elif channel == 'email':
                    # Trigger email notification command
                    result = executor.execute_command('send_email')
                    notification_result['delivery_status']['email'] = result
            
            return notification_result
            
        except Exception as e:
            self.logger.error(f"Error in notification action: {e}")
            return {
                'error': str(e),
                'action': 'notification'
            }
    
    def _handle_report_generation_action(self, parameters: Dict) -> Dict:
        """Xử lý report generation action"""
        try:
            report_type = parameters.get('report_type', 'summary')
            data_source = parameters.get('data_source', '')
            format = parameters.get('format', 'pdf')
            
            # Sử dụng file processor để query data cho report
            from modules.file_processor import get_file_processor
            
            processor = get_file_processor()
            
            # Query documents liên quan đến report
            query = f"{report_type} report for {data_source}"
            results = processor.query_documents(query, n_results=10)
            
            # Tạo report structure
            report = {
                'type': report_type,
                'data_source': data_source,
                'format': format,
                'generated_at': datetime.now().isoformat(),
                'sections': [],
                'key_findings': [],
                'recommendations': []
            }
            
            # Process query results thành report sections
            for i, result in enumerate(results[:5]):
                section = {
                    'title': f'Section {i+1}',
                    'content': result.get('document', '')[:500] + '...',
                    'source': result.get('metadata', {}).get('source', 'unknown')
                }
                report['sections'].append(section)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error in report generation action: {e}")
            return {
                'error': str(e),
                'action': 'report_generation'
            }
    
    def _handle_tts_action(self, parameters: Dict) -> Dict:
        """Xử lý text-to-speech action"""
        try:
            text = parameters.get('text', '')
            voice = parameters.get('voice', 'default')
            speed = parameters.get('speed', 1.0)
            
            from modules.tts_engine import TTSEngine
            
            tts = TTSEngine()
            
            # Trong thực tế sẽ generate audio file
            # Tạm thời chỉ log và trả về metadata
            tts_result = {
                'text': text,
                'voice': voice,
                'speed': speed,
                'status': 'processed',
                'audio_file': f'/tmp/tts_{int(datetime.now().timestamp())}.wav'
            }
            
            self.logger.info(f"TTS action processed: {text[:50]}...")
            
            return tts_result
            
        except Exception as e:
            self.logger.error(f"Error in TTS action: {e}")
            return {
                'error': str(e),
                'action': 'text_to_speech'
            }
    
    def _handle_memory_query_action(self, parameters: Dict) -> Dict:
        """Xử lý memory query action"""
        try:
            user_id = parameters.get('user_id')
            query_type = parameters.get('query_type', 'all')
            days = parameters.get('days', 7)
            
            from modules.enhanced_memory import get_enhanced_memory
            
            memory = get_enhanced_memory()
            
            memory_result = {
                'user_id': user_id,
                'query_type': query_type,
                'time_range_days': days
            }
            
            if query_type == 'profile' or query_type == 'all':
                profile = memory.get_user_profile(user_id)
                memory_result['user_profile'] = profile
            
            if query_type == 'conversations' or query_type == 'all':
                conversations = memory.get_long_term_memory(user_id, days)
                memory_result['recent_conversations'] = conversations
            
            if query_type == 'memories' or query_type == 'all':
                semantic_memories = memory.get_semantic_memories(user_id)
                memory_result['semantic_memories'] = semantic_memories
            
            if query_type == 'context' or query_type == 'all':
                context_summary = memory.build_context_summary(user_id, days)
                memory_result['context_summary'] = context_summary
            
            return memory_result
            
        except Exception as e:
            self.logger.error(f"Error in memory query action: {e}")
            return {
                'error': str(e),
                'action': 'memory_query'
            }
    
    def _handle_workflow_trigger_action(self, parameters: Dict) -> Dict:
        """Xử lý workflow trigger action (N8n -> N8n)"""
        try:
            workflow_id = parameters.get('workflow_id', '')
            data = parameters.get('data', {})
            wait_for_completion = parameters.get('wait_for_completion', False)
            
            from modules.n8n_integration import get_n8n_integration
            
            # Sử dụng N8n integration để trigger workflow khác
            n8n = get_n8n_integration("http://localhost:5678")  # URL mặc định
            
            result = n8n.trigger_workflow(
                workflow_id=workflow_id,
                data=data,
                wait_for_completion=wait_for_completion
            )
            
            return {
                'triggered_workflow': workflow_id,
                'trigger_result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error in workflow trigger action: {e}")
            return {
                'error': str(e),
                'action': 'workflow_trigger'
            }
    
    def list_available_actions(self) -> List[Dict]:
        """Liệt kê tất cả actions có sẵn"""
        actions = []
        
        for action_type in ActionType:
            handler = self.action_handlers.get(action_type)
            actions.append({
                'type': action_type.value,
                'description': self._get_action_description(action_type),
                'handler_registered': handler is not None,
                'parameters': self._get_action_parameters(action_type)
            })
        
        return actions
    
    def _get_action_description(self, action_type: ActionType) -> str:
        """Lấy description cho action"""
        descriptions = {
            ActionType.CHAT: "Chat với MeiLin AI assistant",
            ActionType.DOCUMENT_PROCESSING: "Xử lý và upload documents",
            ActionType.COMMAND_EXECUTION: "Thực thi system commands",
            ActionType.DATA_ANALYSIS: "Phân tích dữ liệu từ nhiều nguồn",
            ActionType.NOTIFICATION: "Gửi thông báo qua nhiều kênh",
            ActionType.REPORT_GENERATION: "Tạo báo cáo tự động",
            ActionType.TTS: "Chuyển text thành speech",
            ActionType.MEMORY_QUERY: "Truy vấn memory và user context",
            ActionType.WORKFLOW_TRIGGER: "Trigger N8n workflows khác"
        }
        
        return descriptions.get(action_type, "No description available")
    
    def _get_action_parameters(self, action_type: ActionType) -> List[str]:
        """Lấy danh sách parameters cho action"""
        parameters = {
            ActionType.CHAT: ["message", "user_id", "username", "context"],
            ActionType.DOCUMENT_PROCESSING: ["file_path", "collection_name", "chunk_size", "chunk_overlap"],
            ActionType.COMMAND_EXECUTION: ["command", "parameters"],
            ActionType.DATA_ANALYSIS: ["data_source", "analysis_type", "output_format"],
            ActionType.NOTIFICATION: ["message", "channels", "priority", "recipients"],
            ActionType.REPORT_GENERATION: ["report_type", "data_source", "format"],
            ActionType.TTS: ["text", "voice", "speed"],
            ActionType.MEMORY_QUERY: ["user_id", "query_type", "days"],
            ActionType.WORKFLOW_TRIGGER: ["workflow_id", "data", "wait_for_completion"]
        }
        
        return parameters.get(action_type, [])


# Factory function
def get_n8n_action_executor():
    """Factory function để tạo N8nActionExecutor"""
    return N8nActionExecutor()


# Test the module
if __name__ == "__main__":
    # Test action executor
    executor = get_n8n_action_executor()
    
    print("N8n Action Executor initialized")
    print("Available actions:")
    
    actions = executor.list_available_actions()
    for action in actions:
        print(f"- {action['type']}: {action['description']}")
        print(f"  Parameters: {action['parameters']}")
        print(f"  Handler registered: {action['handler_registered']}")
        print()
    
    # Test chat action
    print("Testing chat action...")
    result = executor.execute_action(
        "chat",
        {
            "message": "Xin chào từ N8n!",
            "user_id": "n8n_test_user",
            "username": "N8n Tester"
        }
    )
    
    print(f"Chat action result: {result}")
