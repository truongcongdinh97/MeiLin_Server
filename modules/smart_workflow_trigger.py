"""
Smart Workflow Trigger for Voice Command N8n Integration
Tích hợp với N8n để trigger workflows từ voice commands
"""

import logging
from typing import Dict, Optional
from modules.n8n_integration import get_n8n_integration
from modules.excel_data_manager import get_excel_data_manager
from modules.voice_command_processor import get_voice_command_processor

logger = logging.getLogger(__name__)

class SmartWorkflowTrigger:
    """Smart workflow trigger cho voice command integration"""
    
    def __init__(self, n8n_url: str = "http://localhost:5678"):
        self.n8n_integration = get_n8n_integration(n8n_url)
        self.excel_manager = get_excel_data_manager()
        self.voice_processor = get_voice_command_processor()
        
        logger.info("Smart Workflow Trigger initialized")
    
    def trigger_workflow_from_voice(self, voice_text: str) -> Dict:
        """
        Trigger workflow từ voice command
        
        Args:
            voice_text: Voice command text từ speech-to-text
            
        Returns:
            Dict với kết quả execution
        """
        logger.info(f"Triggering workflow from voice: {voice_text}")
        
        # Process voice command
        command_result = self.voice_processor.process_voice_command(voice_text)
        
        if command_result["status"] != "success":
            return {
                "status": "error",
                "error": command_result.get("error", "Lỗi xử lý lệnh thoại"),
                "voice_processing": command_result
            }
        
        # Extract workflow information
        workflow_info = command_result["workflow"]
        if workflow_info["status"] != "success":
            return {
                "status": "error",
                "error": workflow_info.get("error", "Lỗi mapping workflow"),
                "voice_processing": command_result
            }
        
        # Trigger N8n workflow
        workflow_id = workflow_info["workflow_id"]
        parameters = workflow_info["parameters"]
        
        try:
            # Trigger workflow
            trigger_result = self.n8n_integration.trigger_workflow(
                workflow_id=workflow_id,
                data=parameters,
                wait_for_completion=True  # Wait for workflow completion
            )
            
            logger.info(f"Workflow {workflow_id} triggered successfully")
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "parameters": parameters,
                "trigger_result": trigger_result,
                "voice_processing": command_result,
                "message": self._generate_success_message(command_result)
            }
            
        except Exception as e:
            logger.error(f"Error triggering workflow {workflow_id}: {e}")
            return {
                "status": "error",
                "error": f"Lỗi trigger workflow: {str(e)}",
                "workflow_id": workflow_id,
                "parameters": parameters,
                "voice_processing": command_result
            }
    
    def trigger_workflow_smart(self, command_data: Dict) -> Dict:
        """
        Smart workflow trigger với structured command data
        
        Args:
            command_data: Structured command data từ voice processor
            
        Returns:
            Dict với kết quả execution
        """
        logger.info(f"Smart workflow trigger with command: {command_data}")
        
        if command_data["status"] != "success":
            return {
                "status": "error",
                "error": "Invalid command data",
                "command_data": command_data
            }
        
        workflow_info = command_data["workflow"]
        if workflow_info["status"] != "success":
            return {
                "status": "error",
                "error": workflow_info.get("error", "Workflow mapping failed"),
                "command_data": command_data
            }
        
        workflow_id = workflow_info["workflow_id"]
        parameters = workflow_info["parameters"]
        
        try:
            # Apply template formatting nếu có
            formatted_parameters = self._apply_template_formatting(
                workflow_info["workflow_config"],
                parameters
            )
            
            # Trigger workflow
            trigger_result = self.n8n_integration.trigger_workflow(
                workflow_id=workflow_id,
                data=formatted_parameters,
                wait_for_completion=True
            )
            
            logger.info(f"Smart workflow {workflow_id} triggered successfully")
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "original_parameters": parameters,
                "formatted_parameters": formatted_parameters,
                "trigger_result": trigger_result,
                "command_data": command_data,
                "message": self._generate_success_message(command_data)
            }
            
        except Exception as e:
            logger.error(f"Error in smart workflow trigger: {e}")
            return {
                "status": "error",
                "error": f"Smart workflow trigger failed: {str(e)}",
                "workflow_id": workflow_id,
                "parameters": parameters,
                "command_data": command_data
            }
    
    def _apply_template_formatting(self, workflow_config: Dict, parameters: Dict) -> Dict:
        """Apply template formatting cho parameters"""
        formatted_params = parameters.copy()
        
        # Get template từ workflow config
        template = workflow_config.get("Template", "")
        if not template:
            return formatted_params
        
        try:
            # Apply template formatting
            # Ví dụ: template = "📱 {content}" -> format với parameters
            if "content" in formatted_params:
                formatted_content = template.format(**formatted_params)
                formatted_params["formatted_content"] = formatted_content
            
            # For email với subject và body
            if "subject" in formatted_params and "body" in formatted_params:
                formatted_email = template.format(**formatted_params)
                formatted_params["formatted_email"] = formatted_email
            
        except Exception as e:
            logger.warning(f"Template formatting failed: {e}. Using original parameters.")
        
        return formatted_params
    
    def _generate_success_message(self, command_data: Dict) -> str:
        """Generate success message cho user"""
        intent = command_data["intent"]
        entities = command_data["entities"]
        workflow_info = command_data["workflow"]
        
        platform = entities.get("platform", "").title()
        recipient = entities.get("recipient", "")
        
        messages = {
            "send_message": f"Đã gửi tin nhắn {platform} cho {recipient} thành công!",
            "create_task": f"Đã tạo task {platform} cho {recipient} thành công!",
            "send_email": f"Đã gửi email cho {recipient} thành công!",
            "create_event": f"Đã tạo sự kiện cho {recipient} thành công!"
        }
        
        return messages.get(intent, "Đã thực hiện lệnh thành công!")
    
    def get_available_workflows(self) -> Dict:
        """Get danh sách workflows có sẵn"""
        try:
            workflows = self.n8n_integration.list_workflows()
            excel_workflows = self.excel_manager.get_all_workflows()
            
            return {
                "status": "success",
                "n8n_workflows": workflows,
                "excel_workflows": excel_workflows,
                "total_workflows": len(workflows) + len(excel_workflows)
            }
        except Exception as e:
            logger.error(f"Error getting available workflows: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def test_voice_command(self, voice_text: str) -> Dict:
        """Test voice command mà không trigger workflow thực tế"""
        logger.info(f"Testing voice command: {voice_text}")
        
        # Process voice command
        command_result = self.voice_processor.process_voice_command(voice_text)
        
        if command_result["status"] != "success":
            return {
                "status": "test_failed",
                "test_type": "voice_processing",
                "result": command_result
            }
        
        # Check workflow mapping
        workflow_info = command_result["workflow"]
        if workflow_info["status"] != "success":
            return {
                "status": "test_failed", 
                "test_type": "workflow_mapping",
                "result": command_result
            }
        
        # Check if workflow exists in N8n
        workflow_id = workflow_info["workflow_id"]
        try:
            workflows = self.n8n_integration.list_workflows()
            workflow_exists = any(wf["id"] == workflow_id for wf in workflows)
            
            if not workflow_exists:
                return {
                    "status": "test_failed",
                    "test_type": "workflow_existence",
                    "result": command_result,
                    "message": f"Workflow {workflow_id} không tồn tại trong N8n"
                }
            
        except Exception as e:
            return {
                "status": "test_failed",
                "test_type": "n8n_connection",
                "result": command_result,
                "message": f"Lỗi kết nối N8n: {str(e)}"
            }
        
        return {
            "status": "test_success",
            "result": command_result,
            "message": "Voice command test passed successfully"
        }
    
    def get_system_status(self) -> Dict:
        """Get system status và health check"""
        status = {
            "n8n_connection": "unknown",
            "excel_data": "unknown", 
            "voice_processor": "unknown",
            "available_workflows": 0
        }
        
        try:
            # Check N8n connection
            n8n_status = self.n8n_integration.get_integration_status()
            status["n8n_connection"] = "connected" if n8n_status["connection_status"] == "connected" else "disconnected"
        except:
            status["n8n_connection"] = "disconnected"
        
        # Check Excel data
        users = self.excel_manager.get_all_users()
        workflows = self.excel_manager.get_all_workflows()
        templates = self.excel_manager.get_all_templates()
        
        status["excel_data"] = "loaded" if users and workflows and templates else "missing"
        status["available_workflows"] = len(workflows)
        
        # Check voice processor
        try:
            test_command = "gửi tin nhắn zalo cho A rằng test"
            result = self.voice_processor.process_voice_command(test_command)
            status["voice_processor"] = "working" if result["status"] == "success" else "error"
        except:
            status["voice_processor"] = "error"
        
        overall_status = "healthy" if all(
            status[key] in ["connected", "loaded", "working"] 
            for key in ["n8n_connection", "excel_data", "voice_processor"]
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "components": status
        }


# Factory function
def get_smart_workflow_trigger(n8n_url: str = "http://localhost:5678") -> SmartWorkflowTrigger:
    """Factory function để tạo SmartWorkflowTrigger instance"""
    return SmartWorkflowTrigger(n8n_url)


# Test function
if __name__ == "__main__":
    # Test the smart workflow trigger
    trigger = SmartWorkflowTrigger()
    
    print("=== TESTING SMART WORKFLOW TRIGGER ===")
    
    # Test system status
    status = trigger.get_system_status()
    print(f"System Status: {status}")
    
    # Test voice commands
    test_commands = [
        "gửi tin nhắn zalo cho A rằng meeting lúc 3h chiều",
        "tạo task jira cho B với tiêu đề Fix bug và mô tả Critical issue",
        "gửi email cho C với tiêu đề Báo cáo và nội dung Đã hoàn thành"
    ]
    
    for command in test_commands:
        print(f"\nTesting command: {command}")
        
        # Test without actual trigger
        test_result = trigger.test_voice_command(command)
        print(f"Test Result: {test_result}")
        
        if test_result["status"] == "test_success":
            print("✅ Command test passed!")
        else:
            print("❌ Command test failed!")
    
    # Show available workflows
    workflows = trigger.get_available_workflows()
    print(f"\n=== AVAILABLE WORKFLOWS ===")
    print(f"Total workflows: {workflows.get('total_workflows', 0)}")
    
    if workflows["status"] == "success":
        excel_wfs = workflows.get("excel_workflows", [])
        for wf in excel_wfs:
            print(f"- {wf['Workflow_ID']}: {wf['Description']}")
