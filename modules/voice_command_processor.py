"""
Voice Command Processor for N8n Integration
Xử lý voice commands và extract intent, entities từ natural language
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from modules.excel_data_manager import get_excel_data_manager

logger = logging.getLogger(__name__)

class VoiceCommandProcessor:
    """Xử lý voice commands và extract thông tin từ natural language"""
    
    def __init__(self):
        self.excel_manager = get_excel_data_manager()
        
        # Define patterns cho voice commands
        self.patterns = {
            "send_message": [
                r"gửi tin nhắn\s+(\w+)\s+cho\s+(\w+)\s+rằng\s+(.+)",
                r"gửi\s+(\w+)\s+cho\s+(\w+)\s+với\s+nội\s+dung\s+(.+)",
                r"nhắn\s+(\w+)\s+cho\s+(\w+)\s+rằng\s+(.+)"
            ],
            "create_task": [
                r"tạo task\s+(\w+)\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+và\s+mô\s+tả\s+(.+)",
                r"tạo công việc\s+(\w+)\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+và\s+mô\s+tả\s+(.+)"
            ],
            "send_email": [
                r"gửi email\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+và\s+nội\s+dung\s+(.+)",
                r"gửi thư\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+và\s+nội\s+dung\s+(.+)"
            ],
            "create_event": [
                r"tạo sự kiện\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+thời\s+gian\s+(.+?)\s+địa\s+điểm\s+(.+)",
                r"tạo lịch hẹn\s+cho\s+(\w+)\s+với\s+tiêu\s+đề\s+(.+?)\s+thời\s+gian\s+(.+?)\s+địa\s+điểm\s+(.+)"
            ]
        }
        
        # Supported platforms và actions
        self.supported_platforms = ["zalo", "telegram", "email", "jira", "slack", "sms", "calendar", "report"]
        self.supported_actions = ["send_message", "create_task", "send_email", "create_event"]
    
    def process_voice_command(self, text: str) -> Dict:
        """
        Process voice command và extract structured information
        
        Args:
            text: Voice command text từ speech-to-text
            
        Returns:
            Dict với structured command information
        """
        logger.info(f"Processing voice command: {text}")
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract intent và entities
        intent_result = self._extract_intent_and_entities(cleaned_text)
        
        if not intent_result:
            return {
                "status": "error",
                "error": "Không thể hiểu lệnh. Vui lòng thử lại.",
                "original_text": text
            }
        
        intent, entities = intent_result
        
        # Validate entities
        validation_result = self._validate_entities(intent, entities)
        if not validation_result["valid"]:
            return {
                "status": "error",
                "error": validation_result["error"],
                "original_text": text,
                "intent": intent,
                "entities": entities
            }
        
        # Map to workflow
        workflow_result = self._map_to_workflow(intent, entities)
        
        return {
            "status": "success",
            "original_text": text,
            "intent": intent,
            "entities": entities,
            "workflow": workflow_result,
            "validation": validation_result
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean và normalize text"""
        # Remove "MeiLin" prefix nếu có
        text = re.sub(r'^mei\s*lin\s*,?\s*', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Lowercase
        text = text.lower()
        
        return text
    
    def _extract_intent_and_entities(self, text: str) -> Optional[Tuple[str, Dict]]:
        """
        Extract intent và entities từ text
        
        Returns:
            Tuple (intent, entities) hoặc None nếu không match
        """
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.match(pattern, text)
                if match:
                    entities = self._extract_entities_from_match(intent, match.groups())
                    logger.info(f"Matched intent '{intent}' with entities: {entities}")
                    return intent, entities
        
        # Fallback: Try simple keyword matching
        return self._fallback_extraction(text)
    
    def _extract_entities_from_match(self, intent: str, groups: Tuple) -> Dict:
        """Extract entities từ regex match groups"""
        entities = {}
        
        if intent == "send_message":
            entities = {
                "platform": groups[0],
                "recipient": groups[1],
                "content": groups[2]
            }
        elif intent == "create_task":
            entities = {
                "platform": groups[0],
                "recipient": groups[1],
                "title": groups[2],
                "description": groups[3]
            }
        elif intent == "send_email":
            entities = {
                "platform": "email",  # Always email for this intent
                "recipient": groups[0],
                "subject": groups[1],
                "body": groups[2]
            }
        elif intent == "create_event":
            entities = {
                "platform": "calendar",
                "recipient": groups[0],
                "title": groups[1],
                "datetime": groups[2],
                "location": groups[3]
            }
        
        return entities
    
    def _fallback_extraction(self, text: str) -> Optional[Tuple[str, Dict]]:
        """Fallback extraction sử dụng keyword matching"""
        entities = {}
        intent = None
        
        # Check for platform keywords
        platform_keywords = {
            "zalo": "zalo",
            "telegram": "telegram", 
            "email": "email",
            "jira": "jira",
            "slack": "slack",
            "sms": "sms",
            "calendar": "calendar"
        }
        
        # Check for action keywords
        if any(word in text for word in ["gửi tin nhắn", "nhắn tin", "gửi"]):
            intent = "send_message"
        elif any(word in text for word in ["tạo task", "tạo công việc"]):
            intent = "create_task"
        elif any(word in text for word in ["gửi email", "gửi thư"]):
            intent = "send_email"
            entities["platform"] = "email"
        elif any(word in text for word in ["tạo sự kiện", "tạo lịch hẹn"]):
            intent = "create_event"
            entities["platform"] = "calendar"
        
        if not intent:
            return None
        
        # Extract platform từ keyword
        for keyword, platform in platform_keywords.items():
            if keyword in text and "platform" not in entities:
                entities["platform"] = platform
                break
        
        # Simple recipient extraction (tìm từ đứng sau "cho")
        recipient_match = re.search(r'cho\s+(\w+)', text)
        if recipient_match:
            entities["recipient"] = recipient_match.group(1)
        
        # Simple content extraction (phần còn lại của câu)
        content_match = re.search(r'rằng\s+(.+)', text)
        if content_match:
            entities["content"] = content_match.group(1)
        
        logger.info(f"Fallback extraction - Intent: {intent}, Entities: {entities}")
        return intent, entities
    
    def _validate_entities(self, intent: str, entities: Dict) -> Dict:
        """Validate extracted entities"""
        errors = []
        
        # Check required entities
        required_entities = {
            "send_message": ["platform", "recipient", "content"],
            "create_task": ["platform", "recipient", "title", "description"],
            "send_email": ["recipient", "subject", "body"],
            "create_event": ["recipient", "title", "datetime", "location"]
        }
        
        required = required_entities.get(intent, [])
        for entity in required:
            if entity not in entities or not entities[entity]:
                errors.append(f"Thiếu thông tin: {entity}")
        
        # Validate platform
        if "platform" in entities:
            platform = entities["platform"].lower()
            if platform not in self.supported_platforms:
                errors.append(f"Platform '{platform}' không được hỗ trợ")
        
        # Validate recipient exists in Excel
        if "recipient" in entities:
            recipient = entities["recipient"]
            if not self.excel_manager.validate_user_exists(recipient):
                errors.append(f"Người nhận '{recipient}' không tồn tại trong danh bạ")
        
        # Validate workflow exists
        if "platform" in entities and intent:
            platform = entities["platform"].lower()
            # Map intent to action type in Excel
            intent_to_action = {
                "send_message": "Message",
                "create_task": "Task", 
                "send_email": "Message",
                "create_event": "Event"
            }
            action_type = intent_to_action.get(intent, intent)
            if not self.excel_manager.validate_workflow_exists(platform, action_type):
                errors.append(f"Không tìm thấy workflow cho {platform}/{intent}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "error_message": "; ".join(errors) if errors else None
        }
    
    def _map_to_workflow(self, intent: str, entities: Dict) -> Dict:
        """Map intent và entities đến workflow configuration"""
        platform = entities.get("platform", "").lower()
        
        # Map intent to action type in Excel
        intent_to_action = {
            "send_message": "Message",
            "create_task": "Task", 
            "send_email": "Message",
            "create_event": "Event"
        }
        action_type = intent_to_action.get(intent, intent)
        
        # Get workflow config từ Excel
        workflow_config = self.excel_manager.get_workflow_config(platform, action_type)
        
        if not workflow_config:
            return {
                "status": "error",
                "error": f"Không tìm thấy workflow cho {platform}/{intent}"
            }
        
        # Get user UID
        recipient = entities.get("recipient")
        user_uid = self.excel_manager.get_user_uid(recipient) if recipient else None
        
        # Prepare parameters
        parameters = {}
        if user_uid:
            parameters["uid"] = user_uid
        
        # Add other parameters based on workflow requirements
        param_requirements = workflow_config.get("Parameters_Required", "")
        if param_requirements:
            required_params = [p.strip() for p in param_requirements.split(",")]
            for param in required_params:
                if param in entities:
                    parameters[param] = entities[param]
        
        return {
            "status": "success",
            "workflow_id": workflow_config["Workflow_ID"],
            "workflow_config": workflow_config,
            "parameters": parameters,
            "user_uid": user_uid
        }
    
    def get_supported_commands(self) -> List[Dict]:
        """Get danh sách các commands được hỗ trợ"""
        commands = []
        
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                # Convert regex pattern to human-readable format
                readable_pattern = pattern.replace(r'\s+', ' ').replace(r'(\w+)', '{platform}').replace(r'(.+)', '{content}')
                commands.append({
                    "intent": intent,
                    "pattern": readable_pattern,
                    "example": self._generate_example(intent, pattern)
                })
        
        return commands
    
    def _generate_example(self, intent: str, pattern: str) -> str:
        """Generate example command từ pattern"""
        examples = {
            "send_message": "gửi tin nhắn zalo cho A rằng meeting lúc 3h",
            "create_task": "tạo task jira cho B với tiêu đề Fix bug và mô tả Critical issue",
            "send_email": "gửi email cho C với tiêu đề Báo cáo và nội dung Đã hoàn thành",
            "create_event": "tạo sự kiện cho D với tiêu đề Team Meeting thời gian 14:00 địa điểm Phòng họp A"
        }
        return examples.get(intent, "Ví dụ command")


# Factory function
def get_voice_command_processor() -> VoiceCommandProcessor:
    """Factory function để tạo VoiceCommandProcessor instance"""
    return VoiceCommandProcessor()


# Test function
if __name__ == "__main__":
    # Test the voice command processor
    processor = VoiceCommandProcessor()
    
    print("=== TESTING VOICE COMMAND PROCESSOR ===")
    
    # Test commands
    test_commands = [
        "gửi tin nhắn zalo cho A rằng meeting lúc 3h chiều",
        "tạo task jira cho B với tiêu đề Fix bug và mô tả Critical issue",
        "gửi email cho C với tiêu đề Báo cáo và nội dung Đã hoàn thành",
        "nhắn telegram cho D với nội dung Hello world",
        "invalid command test"
    ]
    
    for command in test_commands:
        print(f"\nCommand: {command}")
        result = processor.process_voice_command(command)
        print(f"Result: {result}")
    
    # Show supported commands
    print(f"\n=== SUPPORTED COMMANDS ===")
    commands = processor.get_supported_commands()
    for cmd in commands:
        print(f"Intent: {cmd['intent']}")
        print(f"Pattern: {cmd['pattern']}")
        print(f"Example: {cmd['example']}")
        print()
