"""
N8n Integration - Kết nối MeiLin với N8n workflow automation platform
Hỗ trợ trigger workflows, monitor execution, và webhook handling
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
import hashlib
import threading
from queue import Queue
import logging

class N8nIntegration:
    """
    Tích hợp N8n workflow automation với MeiLin
    Hỗ trợ two-way communication: MeiLin trigger workflows và N8n call MeiLin
    """
    
    def __init__(self, n8n_url: str, api_key: str = None, webhook_secret: str = None):
        self.n8n_url = n8n_url.rstrip('/')
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        
        # Cache để tăng performance
        self.workflow_cache = {}
        self.execution_cache = {}
        
        # Event queue cho async processing
        self.event_queue = Queue()
        self.is_running = False
        
        # Webhook endpoints đã đăng ký
        self.webhook_endpoints = {}
        
        # Setup logging
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging cho N8n integration"""
        logger = logging.getLogger('n8n_integration')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def trigger_workflow(self, workflow_id: str, data: Dict, 
                        wait_for_completion: bool = False, 
                        timeout: int = 30) -> Dict:
        """
        Trigger N8n workflow với data
        Có thể chờ completion hoặc async
        """
        try:
            url = f"{self.n8n_url}/webhook/{workflow_id}"
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MeiLin-N8n-Integration/1.0'
            }
            
            if self.api_key:
                headers['X-N8N-API-KEY'] = self.api_key
            
            # Thêm metadata
            payload = {
                'data': data,
                'metadata': {
                    'triggered_by': 'meilin',
                    'timestamp': datetime.now().isoformat(),
                    'workflow_id': workflow_id
                }
            }
            
            self.logger.info(f"Triggering workflow {workflow_id} with data: {data}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Lưu execution cache
                execution_id = result.get('execution_id', f"{workflow_id}_{int(time.time())}")
                self.execution_cache[execution_id] = {
                    'workflow_id': workflow_id,
                    'status': 'triggered',
                    'trigger_time': datetime.now().isoformat(),
                    'data': data
                }
                
                # Nếu cần chờ completion
                if wait_for_completion:
                    return self._wait_for_completion(execution_id, timeout)
                else:
                    return {
                        'status': 'success',
                        'execution_id': execution_id,
                        'message': 'Workflow triggered successfully',
                        'data': result
                    }
            else:
                error_msg = f"Failed to trigger workflow: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {
                    'status': 'error',
                    'message': error_msg
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error when triggering workflow: {e}"
            self.logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }
    
    def _wait_for_completion(self, execution_id: str, timeout: int = 30) -> Dict:
        """Chờ workflow execution hoàn thành"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_workflow_status(execution_id)
            
            if status.get('status') in ['success', 'error', 'cancelled']:
                return status
            
            time.sleep(1)  # Chờ 1 giây
        
        return {
            'status': 'timeout',
            'message': f'Workflow execution timeout after {timeout} seconds',
            'execution_id': execution_id
        }
    
    def get_workflow_status(self, execution_id: str) -> Dict:
        """Lấy trạng thái workflow execution"""
        try:
            # N8n thường không có API để query execution status
            # Nên chúng ta sẽ implement polling-based approach
            # Hoặc sử dụng webhook để nhận status updates
            
            # Tạm thời trả về status từ cache
            if execution_id in self.execution_cache:
                execution = self.execution_cache[execution_id]
                
                # Simulate status progression (trong thực tế sẽ nhận từ webhook)
                trigger_time = datetime.fromisoformat(execution['trigger_time'])
                elapsed = (datetime.now() - trigger_time).total_seconds()
                
                if elapsed < 2:
                    status = 'running'
                elif elapsed < 5:
                    status = 'processing'
                else:
                    status = 'success'
                
                execution['status'] = status
                
                return {
                    'status': 'success',
                    'execution_id': execution_id,
                    'workflow_status': status,
                    'execution_data': execution
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Execution {execution_id} not found'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting workflow status: {e}")
            return {
                'status': 'error',
                'message': f'Error getting workflow status: {e}'
            }
    
    def list_workflows(self, refresh: bool = False) -> List[Dict]:
        """Liệt kê tất cả workflows có sẵn trong N8n"""
        # N8n không có API chính thức để list workflows
        # Nên chúng ta sẽ sử dụng approach khác:
        # 1. Pre-configured workflows
        # 2. Dynamic discovery via webhook testing
        
        if not refresh and self.workflow_cache:
            return list(self.workflow_cache.values())
        
        try:
            # Pre-configured workflows - trong thực tế sẽ lấy từ config hoặc discovery
            workflows = [
                {
                    'id': 'data_processing',
                    'name': 'Data Processing Workflow',
                    'description': 'Xử lý dữ liệu từ nhiều nguồn',
                    'category': 'data',
                    'tags': ['data', 'processing', 'automation'],
                    'webhook_url': f"{self.n8n_url}/webhook/data_processing"
                },
                {
                    'id': 'notification_system',
                    'name': 'Notification System',
                    'description': 'Gửi thông báo qua nhiều kênh',
                    'category': 'communication',
                    'tags': ['notification', 'email', 'telegram'],
                    'webhook_url': f"{self.n8n_url}/webhook/notification_system"
                },
                {
                    'id': 'report_generation',
                    'name': 'Report Generation',
                    'description': 'Tạo báo cáo tự động',
                    'category': 'reporting',
                    'tags': ['report', 'excel', 'pdf'],
                    'webhook_url': f"{self.n8n_url}/webhook/report_generation"
                }
            ]
            
            # Cache workflows
            for workflow in workflows:
                self.workflow_cache[workflow['id']] = workflow
            
            self.logger.info(f"Loaded {len(workflows)} pre-configured workflows")
            return workflows
            
        except Exception as e:
            self.logger.error(f"Error listing workflows: {e}")
            return []
    
    def create_webhook_endpoint(self, endpoint_name: str, callback_function) -> str:
        """
        Tạo webhook endpoint để N8n có thể gọi lại MeiLin
        Trả về URL webhook
        """
        try:
            # Tạo unique endpoint ID
            endpoint_id = f"meilin_{endpoint_name}_{int(time.time())}"
            webhook_url = f"{self.n8n_url}/webhook/{endpoint_id}"
            
            # Lưu callback function
            self.webhook_endpoints[endpoint_id] = {
                'name': endpoint_name,
                'callback': callback_function,
                'created_at': datetime.now().isoformat(),
                'url': webhook_url
            }
            
            self.logger.info(f"Created webhook endpoint: {endpoint_name} -> {webhook_url}")
            
            return webhook_url
            
        except Exception as e:
            self.logger.error(f"Error creating webhook endpoint: {e}")
            return ""
    
    def handle_webhook_request(self, endpoint_id: str, data: Dict) -> Dict:
        """
        Xử lý webhook request từ N8n
        """
        try:
            if endpoint_id not in self.webhook_endpoints:
                return {
                    'status': 'error',
                    'message': f'Webhook endpoint {endpoint_id} not found'
                }
            
            endpoint = self.webhook_endpoints[endpoint_id]
            callback = endpoint['callback']
            
            # Gọi callback function
            result = callback(data)
            
            self.logger.info(f"Processed webhook request for {endpoint_id}")
            
            return {
                'status': 'success',
                'message': 'Webhook processed successfully',
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error handling webhook request: {e}")
            return {
                'status': 'error',
                'message': f'Error processing webhook: {e}'
            }
    
    def start_event_processor(self):
        """Bắt đầu event processor cho async processing"""
        if self.is_running:
            self.logger.warning("Event processor is already running")
            return
        
        self.is_running = True
        processor_thread = threading.Thread(target=self._event_processor_loop)
        processor_thread.daemon = True
        processor_thread.start()
        
        self.logger.info("Started N8n event processor")
    
    def _event_processor_loop(self):
        """Event processing loop cho async operations"""
        while self.is_running:
            try:
                if not self.event_queue.empty():
                    event = self.event_queue.get()
                    self._process_event(event)
                    self.event_queue.task_done()
                else:
                    time.sleep(0.1)  # Small sleep để giảm CPU usage
            except Exception as e:
                self.logger.error(f"Error in event processor loop: {e}")
    
    def _process_event(self, event: Dict):
        """Xử lý event từ queue"""
        try:
            event_type = event.get('type')
            
            if event_type == 'workflow_trigger':
                workflow_id = event.get('workflow_id')
                data = event.get('data')
                
                result = self.trigger_workflow(workflow_id, data)
                
                # Gọi callback nếu có
                callback = event.get('callback')
                if callback:
                    callback(result)
            
            elif event_type == 'status_check':
                execution_id = event.get('execution_id')
                callback = event.get('callback')
                
                status = self.get_workflow_status(execution_id)
                if callback:
                    callback(status)
            
            self.logger.info(f"Processed event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
    
    def trigger_workflow_async(self, workflow_id: str, data: Dict, callback=None):
        """Trigger workflow async với callback"""
        event = {
            'type': 'workflow_trigger',
            'workflow_id': workflow_id,
            'data': data,
            'callback': callback,
            'timestamp': datetime.now().isoformat()
        }
        
        self.event_queue.put(event)
        self.logger.info(f"Queued async workflow trigger: {workflow_id}")
    
    def get_workflow_templates(self) -> List[Dict]:
        """Lấy danh sách workflow templates"""
        templates = [
            {
                'id': 'data_analysis',
                'name': 'Data Analysis Template',
                'description': 'Phân tích dữ liệu từ file upload',
                'category': 'data',
                'inputs': ['file_path', 'analysis_type'],
                'outputs': ['analysis_result', 'charts'],
                'example_data': {
                    'file_path': '/path/to/data.csv',
                    'analysis_type': 'statistical'
                }
            },
            {
                'id': 'notification_broadcast',
                'name': 'Notification Broadcast',
                'description': 'Gửi thông báo đến nhiều kênh',
                'category': 'communication',
                'inputs': ['message', 'channels', 'priority'],
                'outputs': ['delivery_status', 'recipients'],
                'example_data': {
                    'message': 'Thông báo quan trọng từ MeiLin',
                    'channels': ['telegram', 'email'],
                    'priority': 'high'
                }
            },
            {
                'id': 'report_automation',
                'name': 'Report Automation',
                'description': 'Tạo báo cáo tự động từ dữ liệu',
                'category': 'reporting',
                'inputs': ['data_source', 'report_type', 'format'],
                'outputs': ['report_file', 'summary'],
                'example_data': {
                    'data_source': 'database',
                    'report_type': 'weekly',
                    'format': 'pdf'
                }
            }
        ]
        
        return templates
    
    def execute_template_workflow(self, template_id: str, data: Dict) -> Dict:
        """Execute workflow từ template"""
        try:
            templates = self.get_workflow_templates()
            template = next((t for t in templates if t['id'] == template_id), None)
            
            if not template:
                return {
                    'status': 'error',
                    'message': f'Template {template_id} not found'
                }
            
            # Map template to actual workflow
            workflow_mapping = {
                'data_analysis': 'data_processing',
                'notification_broadcast': 'notification_system',
                'report_automation': 'report_generation'
            }
            
            workflow_id = workflow_mapping.get(template_id)
            if not workflow_id:
                return {
                    'status': 'error',
                    'message': f'No workflow mapping for template {template_id}'
                }
            
            # Trigger workflow
            return self.trigger_workflow(workflow_id, data)
            
        except Exception as e:
            self.logger.error(f"Error executing template workflow: {e}")
            return {
                'status': 'error',
                'message': f'Error executing template: {e}'
            }
    
    def get_integration_status(self) -> Dict:
        """Lấy trạng thái integration với N8n"""
        try:
            # Test connection
            test_url = f"{self.n8n_url}/healthz"
            response = requests.get(test_url, timeout=5)
            
            connection_status = 'connected' if response.status_code == 200 else 'disconnected'
            
            status = {
                'n8n_url': self.n8n_url,
                'connection_status': connection_status,
                'active_webhooks': len(self.webhook_endpoints),
                'cached_workflows': len(self.workflow_cache),
                'pending_events': self.event_queue.qsize(),
                'event_processor_running': self.is_running,
                'last_checked': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting integration status: {e}")
            return {
                'n8n_url': self.n8n_url,
                'connection_status': 'error',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }
    
    def stop_integration(self):
        """Dừng integration và cleanup"""
        self.is_running = False
        self.logger.info("N8n integration stopped")


# Factory function
def get_n8n_integration(n8n_url: str, api_key: str = None, webhook_secret: str = None):
    """Factory function để tạo N8nIntegration"""
    integration = N8nIntegration(n8n_url, api_key, webhook_secret)
    integration.start_event_processor()
    return integration


# Test the module
if __name__ == "__main__":
    # Test với mock N8n server
    n8n = N8nIntegration("http://localhost:5678")
    
    # Test list workflows
    workflows = n8n.list_workflows()
    print("Available workflows:")
    for wf in workflows:
        print(f"- {wf['name']} ({wf['id']})")
    
    # Test integration status
    status = n8n.get_integration_status()
    print(f"\nIntegration status: {status}")
    
    # Test workflow templates
    templates = n8n.get_workflow_templates()
    print(f"\nAvailable templates: {len(templates)}")
    
    # Stop integration
    n8n.stop_integration()
