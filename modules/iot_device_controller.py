"""
IoT Device Controller for MeiLin
Handles device control via HTTP, MQTT, and messaging platforms.

This module allows MeiLin to control smart home devices based on user voice/text commands.
Devices are configured per-user in the database and can be managed via Telegram bot.

Supported device types:
- esp32_relay: Direct HTTP calls to ESP32 devices
- webhook: Generic webhook calls (for n8n, Home Assistant, etc.)
- messaging: Send messages to contacts (Telegram, etc.)
- mqtt: MQTT-based devices (future)
"""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re
import sqlite3
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DeviceType(Enum):
    """Supported device types"""
    ESP32_RELAY = "esp32_relay"
    WEBHOOK = "webhook"
    MESSAGING = "messaging"
    MQTT = "mqtt"
    HOME_ASSISTANT = "home_assistant"


class DeviceCategory(Enum):
    """Device categories for better organization"""
    LIGHT = "light"
    SWITCH = "switch"
    COMPUTER = "computer"
    AC = "ac"
    FAN = "fan"
    TV = "tv"
    DOOR = "door"
    MESSAGING = "messaging"
    OTHER = "other"


class ActionStatus(Enum):
    """Action execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"
    DEVICE_NOT_FOUND = "device_not_found"
    ACTION_NOT_FOUND = "action_not_found"


@dataclass
class DeviceAction:
    """Represents a device action configuration"""
    action_name: str
    action_aliases: List[str]
    action_type: str  # http, mqtt, websocket
    
    # HTTP config
    http_method: str = "GET"
    http_url: str = ""
    http_headers: Dict[str, str] = field(default_factory=dict)
    http_body: str = ""
    http_timeout: int = 10
    
    # MQTT config
    mqtt_topic: str = ""
    mqtt_payload: str = ""
    mqtt_qos: int = 0
    
    # Response config
    success_message: str = ""
    failure_message: str = ""
    expected_response: str = ""


@dataclass
class IoTDevice:
    """Represents an IoT device"""
    id: int
    user_id: int
    device_id: str
    device_name: str
    device_aliases: List[str]
    device_type: DeviceType
    device_category: DeviceCategory
    is_active: bool
    actions: Dict[str, DeviceAction] = field(default_factory=dict)
    contacts: Dict[str, Dict] = field(default_factory=dict)  # For messaging devices


@dataclass
class ActionResult:
    """Result of an action execution"""
    status: ActionStatus
    device_name: str
    action_name: str
    message: str
    response_data: Optional[Dict] = None
    execution_time_ms: int = 0
    error_message: str = ""


class IoTDeviceController:
    """
    Controller for IoT device management and execution.
    
    Features:
    - Load devices from database per user
    - Execute actions (HTTP, MQTT, messaging)
    - Natural language matching for devices and actions
    - Action logging for auditing
    
    Usage:
        controller = IoTDeviceController(db_path)
        result = await controller.execute_action(
            user_id=123,
            device_query="đèn phòng khách",
            action_query="bật"
        )
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the controller with database path"""
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "database" / "users.db")
        self.db_path = db_path
        self._ensure_tables()
        
        # Action aliases for common Vietnamese commands
        self.action_aliases = {
            "on": ["bật", "mở", "turn on", "켜", "开", "つける"],
            "off": ["tắt", "đóng", "turn off", "끄다", "关", "消す"],
            "toggle": ["chuyển", "switch", "切替"],
            "send_message": ["gửi tin nhắn", "nhắn", "nhắn tin", "send", "message"],
            "set_brightness": ["độ sáng", "brightness", "밝기"],
            "set_temperature": ["nhiệt độ", "temperature", "温度"]
        }
        
        # Device category keywords
        self.category_keywords = {
            DeviceCategory.LIGHT: ["đèn", "light", "lamp", "bóng", "電灯"],
            DeviceCategory.SWITCH: ["công tắc", "switch", "nút"],
            DeviceCategory.COMPUTER: ["máy tính", "computer", "pc", "laptop"],
            DeviceCategory.AC: ["điều hòa", "máy lạnh", "ac", "air conditioning"],
            DeviceCategory.FAN: ["quạt", "fan"],
            DeviceCategory.TV: ["tivi", "tv", "television", "màn hình"],
            DeviceCategory.DOOR: ["cửa", "door", "cổng", "gate"],
            DeviceCategory.MESSAGING: ["tin nhắn", "message", "nhắn tin"]
        }
    
    def _ensure_tables(self):
        """Ensure IoT tables exist in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if tables exist, if not create them
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user_iot_devices'
            """)
            if not cursor.fetchone():
                # Read and execute schema for IoT tables
                schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = f.read()
                        # Execute only IoT-related statements
                        for statement in schema.split(';'):
                            if 'user_iot' in statement.lower():
                                try:
                                    cursor.execute(statement)
                                except sqlite3.Error:
                                    pass
                    conn.commit()
                    logger.info("Created IoT tables in database")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring IoT tables: {e}")
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ============================================================
    # DEVICE LOADING
    # ============================================================
    
    def load_user_devices(self, user_id: int) -> List[IoTDevice]:
        """Load all devices for a user from database"""
        devices = []
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Get all active devices for user
            cursor.execute("""
                SELECT * FROM user_iot_devices 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            device_rows = cursor.fetchall()
            
            for row in device_rows:
                device = IoTDevice(
                    id=row['id'],
                    user_id=row['user_id'],
                    device_id=row['device_id'],
                    device_name=row['device_name'],
                    device_aliases=json.loads(row['device_aliases'] or '[]'),
                    device_type=DeviceType(row['device_type']),
                    device_category=DeviceCategory(row['device_category'] or 'other'),
                    is_active=bool(row['is_active'])
                )
                
                # Load actions for this device
                cursor.execute("""
                    SELECT * FROM user_iot_device_actions 
                    WHERE device_id = ?
                """, (row['id'],))
                
                for action_row in cursor.fetchall():
                    action = DeviceAction(
                        action_name=action_row['action_name'],
                        action_aliases=json.loads(action_row['action_aliases'] or '[]'),
                        action_type=action_row['action_type'],
                        http_method=action_row['http_method'] or 'GET',
                        http_url=action_row['http_url'] or '',
                        http_headers=json.loads(action_row['http_headers'] or '{}'),
                        http_body=action_row['http_body'] or '',
                        http_timeout=action_row['http_timeout'] or 10,
                        mqtt_topic=action_row['mqtt_topic'] or '',
                        mqtt_payload=action_row['mqtt_payload'] or '',
                        mqtt_qos=action_row['mqtt_qos'] or 0,
                        success_message=action_row['success_message'] or '',
                        failure_message=action_row['failure_message'] or '',
                        expected_response=action_row['expected_response'] or ''
                    )
                    device.actions[action.action_name] = action
                
                # Load contacts for messaging devices
                if device.device_type == DeviceType.MESSAGING:
                    cursor.execute("""
                        SELECT * FROM user_iot_contacts 
                        WHERE device_id = ? AND is_active = 1
                    """, (row['id'],))
                    
                    for contact_row in cursor.fetchall():
                        device.contacts[contact_row['contact_name']] = {
                            'name': contact_row['contact_name'],
                            'aliases': json.loads(contact_row['contact_aliases'] or '[]'),
                            'platform': contact_row['platform'],
                            'platform_id': contact_row['platform_id'],
                            'webhook_url': contact_row['webhook_url'],
                            'webhook_headers': json.loads(contact_row['webhook_headers'] or '{}'),
                            'webhook_body_template': contact_row['webhook_body_template']
                        }
                
                devices.append(device)
            
            conn.close()
            logger.info(f"Loaded {len(devices)} devices for user {user_id}")
            return devices
            
        except Exception as e:
            logger.error(f"Error loading devices for user {user_id}: {e}")
            return []
    
    # ============================================================
    # NATURAL LANGUAGE MATCHING
    # ============================================================
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        return text.lower().strip()
    
    def find_device(self, user_id: int, query: str) -> Optional[IoTDevice]:
        """
        Find device by name or alias using fuzzy matching.
        
        Args:
            user_id: User's database ID
            query: Device name or alias to search
            
        Returns:
            Matched device or None
        """
        devices = self.load_user_devices(user_id)
        query_normalized = self._normalize_text(query)
        
        # Exact match first
        for device in devices:
            if self._normalize_text(device.device_name) == query_normalized:
                return device
            for alias in device.device_aliases:
                if self._normalize_text(alias) == query_normalized:
                    return device
        
        # Partial match
        for device in devices:
            if query_normalized in self._normalize_text(device.device_name):
                return device
            for alias in device.device_aliases:
                if query_normalized in self._normalize_text(alias):
                    return device
        
        # Category-based match
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in query_normalized:
                    # Find device of this category
                    for device in devices:
                        if device.device_category == category:
                            return device
        
        return None
    
    def find_action(self, device: IoTDevice, query: str) -> Optional[DeviceAction]:
        """
        Find action by name or alias.
        
        Args:
            device: The device to search actions in
            query: Action name or alias
            
        Returns:
            Matched action or None
        """
        query_normalized = self._normalize_text(query)
        
        # Check device-specific actions first
        for action_name, action in device.actions.items():
            if self._normalize_text(action_name) == query_normalized:
                return action
            for alias in action.action_aliases:
                if self._normalize_text(alias) == query_normalized:
                    return action
        
        # Check global action aliases
        for canonical_action, aliases in self.action_aliases.items():
            if query_normalized in [self._normalize_text(a) for a in aliases]:
                # Find corresponding action in device
                if canonical_action in device.actions:
                    return device.actions[canonical_action]
        
        return None
    
    def parse_command(self, user_id: int, message: str) -> Tuple[Optional[IoTDevice], Optional[DeviceAction], Dict[str, Any]]:
        """
        Parse natural language command to extract device, action, and parameters.
        
        Examples:
            "bật đèn phòng khách" -> (light_device, on_action, {})
            "gửi tin nhắn cho A nói hello" -> (messaging_device, send_action, {contact: "A", message: "hello"})
            
        Args:
            user_id: User's database ID
            message: Natural language command
            
        Returns:
            Tuple of (device, action, parameters)
        """
        message_lower = message.lower()
        params = {}
        
        # Load user devices
        devices = self.load_user_devices(user_id)
        
        if not devices:
            return None, None, {}
        
        # Try to find device in message
        found_device = None
        found_action = None
        
        for device in devices:
            # Check device name
            if self._normalize_text(device.device_name) in message_lower:
                found_device = device
                break
            # Check aliases
            for alias in device.device_aliases:
                if self._normalize_text(alias) in message_lower:
                    found_device = device
                    break
            if found_device:
                break
        
        if not found_device:
            # Try category-based matching
            for category, keywords in self.category_keywords.items():
                for keyword in keywords:
                    if keyword in message_lower:
                        for device in devices:
                            if device.device_category == category:
                                found_device = device
                                break
                        break
                if found_device:
                    break
        
        if found_device:
            # Find action
            for action_name, action in found_device.actions.items():
                if self._normalize_text(action_name) in message_lower:
                    found_action = action
                    break
                for alias in action.action_aliases:
                    if self._normalize_text(alias) in message_lower:
                        found_action = action
                        break
                if found_action:
                    break
            
            if not found_action:
                # Check global aliases
                for canonical, aliases in self.action_aliases.items():
                    for alias in aliases:
                        if alias in message_lower:
                            if canonical in found_device.actions:
                                found_action = found_device.actions[canonical]
                                break
                    if found_action:
                        break
            
            # Extract parameters for messaging
            if found_device.device_type == DeviceType.MESSAGING:
                # Find contact name
                for contact_name, contact_info in found_device.contacts.items():
                    if self._normalize_text(contact_name) in message_lower:
                        params['contact'] = contact_name
                        params['contact_info'] = contact_info
                        break
                    for alias in contact_info.get('aliases', []):
                        if self._normalize_text(alias) in message_lower:
                            params['contact'] = contact_name
                            params['contact_info'] = contact_info
                            break
                
                # Extract message content (text after "nói", "gửi", etc.)
                message_patterns = [
                    r'nói\s+(.+)',
                    r'gửi\s+(?:tin nhắn\s+)?(?:cho\s+\w+\s+)?(.+)',
                    r'nhắn\s+(.+)',
                    r'message[:\s]+(.+)'
                ]
                for pattern in message_patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        params['message'] = match.group(1).strip()
                        break
        
        return found_device, found_action, params
    
    # ============================================================
    # ACTION EXECUTION
    # ============================================================
    
    async def execute_action(
        self,
        user_id: int,
        device_query: str = None,
        action_query: str = None,
        device: IoTDevice = None,
        action: DeviceAction = None,
        params: Dict[str, Any] = None,
        trigger_source: str = "api",
        trigger_message: str = ""
    ) -> ActionResult:
        """
        Execute an action on a device.
        
        Args:
            user_id: User's database ID
            device_query: Device name/alias to find
            action_query: Action name/alias to find
            device: Pre-resolved device (optional)
            action: Pre-resolved action (optional)
            params: Additional parameters
            trigger_source: Source of trigger (voice, telegram, api, schedule)
            trigger_message: Original message that triggered this
            
        Returns:
            ActionResult with status and details
        """
        start_time = datetime.now()
        params = params or {}
        
        # Resolve device if not provided
        if device is None and device_query:
            device = self.find_device(user_id, device_query)
        
        if device is None:
            return ActionResult(
                status=ActionStatus.DEVICE_NOT_FOUND,
                device_name=device_query or "unknown",
                action_name=action_query or "unknown",
                message=f"Không tìm thấy thiết bị '{device_query}'"
            )
        
        # Resolve action if not provided
        if action is None and action_query:
            action = self.find_action(device, action_query)
        
        if action is None:
            return ActionResult(
                status=ActionStatus.ACTION_NOT_FOUND,
                device_name=device.device_name,
                action_name=action_query or "unknown",
                message=f"Không tìm thấy hành động '{action_query}' cho thiết bị '{device.device_name}'"
            )
        
        # Execute based on action type
        try:
            if action.action_type == "http":
                result = await self._execute_http_action(device, action, params)
            elif action.action_type == "mqtt":
                result = await self._execute_mqtt_action(device, action, params)
            else:
                result = ActionResult(
                    status=ActionStatus.ERROR,
                    device_name=device.device_name,
                    action_name=action.action_name,
                    message=f"Không hỗ trợ loại action: {action.action_type}"
                )
        except Exception as e:
            result = ActionResult(
                status=ActionStatus.ERROR,
                device_name=device.device_name,
                action_name=action.action_name,
                message=f"Lỗi khi thực hiện: {str(e)}",
                error_message=str(e)
            )
        
        # Calculate execution time
        end_time = datetime.now()
        result.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Log action
        self._log_action(
            user_id=user_id,
            device_id=device.id,
            action_name=action.action_name,
            params=params,
            trigger_source=trigger_source,
            trigger_message=trigger_message,
            result=result
        )
        
        return result
    
    async def _execute_http_action(
        self,
        device: IoTDevice,
        action: DeviceAction,
        params: Dict[str, Any]
    ) -> ActionResult:
        """Execute HTTP-based action"""
        url = action.http_url
        
        # Replace placeholders in URL
        for key, value in params.items():
            url = url.replace(f"{{{{{key}}}}}", str(value))
        
        # Prepare headers
        headers = action.http_headers.copy()
        
        # Prepare body
        body = action.http_body
        if body:
            for key, value in params.items():
                body = body.replace(f"{{{{{key}}}}}", str(value))
        
        try:
            timeout = aiohttp.ClientTimeout(total=action.http_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                method = action.http_method.upper()
                
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        status_ok = response.status < 400
                elif method == "POST":
                    async with session.post(url, headers=headers, data=body) as response:
                        response_text = await response.text()
                        status_ok = response.status < 400
                elif method == "PUT":
                    async with session.put(url, headers=headers, data=body) as response:
                        response_text = await response.text()
                        status_ok = response.status < 400
                else:
                    return ActionResult(
                        status=ActionStatus.ERROR,
                        device_name=device.device_name,
                        action_name=action.action_name,
                        message=f"Phương thức HTTP không hỗ trợ: {method}"
                    )
                
                # Check expected response if configured
                if action.expected_response and action.expected_response not in response_text:
                    status_ok = False
                
                if status_ok:
                    message = action.success_message or f"Đã {action.action_name} {device.device_name}"
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        device_name=device.device_name,
                        action_name=action.action_name,
                        message=message,
                        response_data={"response": response_text, "status_code": response.status}
                    )
                else:
                    message = action.failure_message or f"Không thể {action.action_name} {device.device_name}"
                    return ActionResult(
                        status=ActionStatus.FAILURE,
                        device_name=device.device_name,
                        action_name=action.action_name,
                        message=message,
                        response_data={"response": response_text, "status_code": response.status}
                    )
                    
        except asyncio.TimeoutError:
            return ActionResult(
                status=ActionStatus.TIMEOUT,
                device_name=device.device_name,
                action_name=action.action_name,
                message=f"Thiết bị '{device.device_name}' không phản hồi (timeout)"
            )
        except aiohttp.ClientError as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                device_name=device.device_name,
                action_name=action.action_name,
                message=f"Lỗi kết nối: {str(e)}",
                error_message=str(e)
            )
    
    async def _execute_mqtt_action(
        self,
        device: IoTDevice,
        action: DeviceAction,
        params: Dict[str, Any]
    ) -> ActionResult:
        """Execute MQTT-based action (placeholder for future implementation)"""
        # TODO: Implement MQTT support
        return ActionResult(
            status=ActionStatus.ERROR,
            device_name=device.device_name,
            action_name=action.action_name,
            message="MQTT chưa được hỗ trợ"
        )
    
    async def send_message(
        self,
        user_id: int,
        contact_query: str,
        message: str,
        trigger_source: str = "api"
    ) -> ActionResult:
        """
        Send message to a contact via configured platform.
        
        Args:
            user_id: User's database ID
            contact_query: Contact name to find
            message: Message to send
            trigger_source: Source of trigger
            
        Returns:
            ActionResult with status
        """
        devices = self.load_user_devices(user_id)
        
        # Find messaging device with matching contact
        for device in devices:
            if device.device_type != DeviceType.MESSAGING:
                continue
            
            for contact_name, contact_info in device.contacts.items():
                contact_normalized = self._normalize_text(contact_name)
                query_normalized = self._normalize_text(contact_query)
                
                if contact_normalized == query_normalized or \
                   query_normalized in [self._normalize_text(a) for a in contact_info.get('aliases', [])]:
                    
                    # Found contact, send message
                    if contact_info.get('webhook_url'):
                        return await self._send_webhook_message(
                            device, contact_info, message, trigger_source
                        )
                    else:
                        return ActionResult(
                            status=ActionStatus.ERROR,
                            device_name=device.device_name,
                            action_name="send_message",
                            message=f"Không có webhook được cấu hình cho '{contact_name}'"
                        )
        
        return ActionResult(
            status=ActionStatus.DEVICE_NOT_FOUND,
            device_name="messaging",
            action_name="send_message",
            message=f"Không tìm thấy liên hệ '{contact_query}'"
        )
    
    async def _send_webhook_message(
        self,
        device: IoTDevice,
        contact_info: Dict,
        message: str,
        trigger_source: str
    ) -> ActionResult:
        """Send message via webhook"""
        url = contact_info['webhook_url']
        headers = contact_info.get('webhook_headers', {})
        body_template = contact_info.get('webhook_body_template', '{"message": "{{message}}"}')
        
        # Replace message placeholder
        body = body_template.replace("{{message}}", message)
        body = body.replace("{{contact_id}}", contact_info.get('platform_id', ''))
        body = body.replace("{{platform}}", contact_info.get('platform', ''))
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, data=body) as response:
                    response_text = await response.text()
                    
                    if response.status < 400:
                        return ActionResult(
                            status=ActionStatus.SUCCESS,
                            device_name=device.device_name,
                            action_name="send_message",
                            message=f"Đã gửi tin nhắn cho {contact_info['name']}",
                            response_data={"response": response_text}
                        )
                    else:
                        return ActionResult(
                            status=ActionStatus.FAILURE,
                            device_name=device.device_name,
                            action_name="send_message",
                            message=f"Không thể gửi tin nhắn: HTTP {response.status}"
                        )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                device_name=device.device_name,
                action_name="send_message",
                message=f"Lỗi gửi tin nhắn: {str(e)}",
                error_message=str(e)
            )
    
    # ============================================================
    # ACTION LOGGING
    # ============================================================
    
    def _log_action(
        self,
        user_id: int,
        device_id: int,
        action_name: str,
        params: Dict[str, Any],
        trigger_source: str,
        trigger_message: str,
        result: ActionResult
    ):
        """Log action to database"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_iot_action_logs 
                (user_id, device_id, action_name, action_params, trigger_source, 
                 trigger_message, status, response_data, error_message, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                device_id,
                action_name,
                json.dumps(params),
                trigger_source,
                trigger_message,
                result.status.value,
                json.dumps(result.response_data) if result.response_data else None,
                result.error_message,
                result.execution_time_ms
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging action: {e}")
    
    # ============================================================
    # DEVICE MANAGEMENT
    # ============================================================
    
    def add_device(
        self,
        user_id: int,
        device_id: str,
        device_name: str,
        device_type: str,
        device_category: str = "other",
        aliases: List[str] = None
    ) -> int:
        """
        Add a new device for user.
        
        Returns:
            Device ID in database, or -1 on error
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_iot_devices 
                (user_id, device_id, device_name, device_aliases, device_type, device_category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                device_id,
                device_name,
                json.dumps(aliases or []),
                device_type,
                device_category
            ))
            
            device_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Added device '{device_name}' for user {user_id}")
            return device_db_id
            
        except sqlite3.IntegrityError:
            logger.error(f"Device '{device_id}' already exists for user {user_id}")
            return -1
        except Exception as e:
            logger.error(f"Error adding device: {e}")
            return -1
    
    def add_action(
        self,
        device_db_id: int,
        action_name: str,
        action_type: str = "http",
        http_method: str = "GET",
        http_url: str = "",
        http_headers: Dict = None,
        http_body: str = "",
        aliases: List[str] = None,
        success_message: str = "",
        failure_message: str = ""
    ) -> int:
        """Add an action to a device"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_iot_device_actions 
                (device_id, action_name, action_aliases, action_type, 
                 http_method, http_url, http_headers, http_body,
                 success_message, failure_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_db_id,
                action_name,
                json.dumps(aliases or []),
                action_type,
                http_method,
                http_url,
                json.dumps(http_headers or {}),
                http_body,
                success_message,
                failure_message
            ))
            
            action_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return action_id
            
        except Exception as e:
            logger.error(f"Error adding action: {e}")
            return -1
    
    def add_contact(
        self,
        device_db_id: int,
        contact_name: str,
        platform: str,
        platform_id: str = "",
        webhook_url: str = "",
        webhook_headers: Dict = None,
        webhook_body_template: str = "",
        aliases: List[str] = None
    ) -> int:
        """Add a contact to a messaging device"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_iot_contacts 
                (device_id, contact_name, contact_aliases, platform, platform_id,
                 webhook_url, webhook_headers, webhook_body_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_db_id,
                contact_name,
                json.dumps(aliases or []),
                platform,
                platform_id,
                webhook_url,
                json.dumps(webhook_headers or {}),
                webhook_body_template
            ))
            
            contact_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return contact_id
            
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return -1
    
    def delete_device(self, user_id: int, device_id: str) -> bool:
        """Delete a device (cascades to actions and contacts)"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM user_iot_devices 
                WHERE user_id = ? AND device_id = ?
            """, (user_id, device_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
            
        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            return False
    
    def get_user_devices_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's IoT devices"""
        devices = self.load_user_devices(user_id)
        
        return {
            "total_devices": len(devices),
            "devices": [
                {
                    "id": d.device_id,
                    "name": d.device_name,
                    "type": d.device_type.value,
                    "category": d.device_category.value,
                    "actions": list(d.actions.keys()),
                    "contacts": list(d.contacts.keys()) if d.device_type == DeviceType.MESSAGING else []
                }
                for d in devices
            ]
        }
    
    def import_devices_from_json(self, user_id: int, json_config: Dict) -> Dict[str, Any]:
        """
        Import devices from JSON configuration.
        
        JSON format:
        {
            "devices": [
                {
                    "id": "light_living_room",
                    "name": "đèn phòng khách",
                    "aliases": ["đèn A", "living room light"],
                    "type": "esp32_relay",
                    "category": "light",
                    "actions": {
                        "on": {
                            "method": "GET",
                            "url": "http://192.168.1.100/relay/1/on",
                            "aliases": ["bật", "mở"]
                        },
                        "off": {
                            "method": "GET",
                            "url": "http://192.168.1.100/relay/1/off",
                            "aliases": ["tắt", "đóng"]
                        }
                    }
                },
                {
                    "id": "messaging",
                    "name": "Gửi tin nhắn",
                    "type": "messaging",
                    "category": "messaging",
                    "contacts": {
                        "A": {
                            "platform": "telegram",
                            "webhook_url": "https://n8n.example.com/webhook/send-telegram",
                            "webhook_body": {"chat_id": "123456", "message": "{{message}}"}
                        }
                    }
                }
            ]
        }
        """
        results = {
            "success": [],
            "failed": [],
            "total": 0
        }
        
        devices = json_config.get("devices", [])
        results["total"] = len(devices)
        
        for device_config in devices:
            try:
                # Add device
                device_db_id = self.add_device(
                    user_id=user_id,
                    device_id=device_config["id"],
                    device_name=device_config["name"],
                    device_type=device_config["type"],
                    device_category=device_config.get("category", "other"),
                    aliases=device_config.get("aliases", [])
                )
                
                if device_db_id < 0:
                    results["failed"].append({
                        "device": device_config["id"],
                        "error": "Device already exists or database error"
                    })
                    continue
                
                # Add actions
                for action_name, action_config in device_config.get("actions", {}).items():
                    self.add_action(
                        device_db_id=device_db_id,
                        action_name=action_name,
                        action_type="http",
                        http_method=action_config.get("method", "GET"),
                        http_url=action_config.get("url", ""),
                        http_headers=action_config.get("headers", {}),
                        http_body=json.dumps(action_config.get("body", {})) if action_config.get("body") else "",
                        aliases=action_config.get("aliases", []),
                        success_message=action_config.get("success_message", ""),
                        failure_message=action_config.get("failure_message", "")
                    )
                
                # Add contacts for messaging devices
                for contact_name, contact_config in device_config.get("contacts", {}).items():
                    self.add_contact(
                        device_db_id=device_db_id,
                        contact_name=contact_name,
                        platform=contact_config.get("platform", "webhook"),
                        platform_id=contact_config.get("platform_id", ""),
                        webhook_url=contact_config.get("webhook_url", ""),
                        webhook_headers=contact_config.get("webhook_headers", {}),
                        webhook_body_template=json.dumps(contact_config.get("webhook_body", {})),
                        aliases=contact_config.get("aliases", [])
                    )
                
                results["success"].append(device_config["id"])
                
            except Exception as e:
                results["failed"].append({
                    "device": device_config.get("id", "unknown"),
                    "error": str(e)
                })
        
        return results


# ============================================================
# FUNCTION CALLING TOOLS FOR LLM
# ============================================================

def get_iot_tools_for_llm(user_id: int, controller: IoTDeviceController) -> List[Dict]:
    """
    Generate function calling tools for LLM based on user's devices.
    
    This creates dynamic tools that the LLM can call to control devices.
    """
    devices = controller.load_user_devices(user_id)
    
    if not devices:
        return []
    
    tools = []
    
    # Control device tool
    tools.append({
        "type": "function",
        "function": {
            "name": "control_iot_device",
            "description": "Điều khiển thiết bị IoT trong nhà. Có thể bật/tắt đèn, máy tính, điều hòa, v.v.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": f"Tên thiết bị cần điều khiển. Các thiết bị có sẵn: {', '.join([d.device_name for d in devices])}"
                    },
                    "action": {
                        "type": "string",
                        "description": "Hành động cần thực hiện (on/off/toggle/...)",
                        "enum": list(set(
                            action_name 
                            for d in devices 
                            for action_name in d.actions.keys()
                        ))
                    }
                },
                "required": ["device_name", "action"]
            }
        }
    })
    
    # Check for messaging devices
    messaging_devices = [d for d in devices if d.device_type == DeviceType.MESSAGING]
    if messaging_devices:
        all_contacts = []
        for d in messaging_devices:
            all_contacts.extend(d.contacts.keys())
        
        if all_contacts:
            tools.append({
                "type": "function",
                "function": {
                    "name": "send_message_to_contact",
                    "description": "Gửi tin nhắn cho một người trong danh bạ",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_name": {
                                "type": "string",
                                "description": f"Tên người nhận. Danh sách: {', '.join(all_contacts)}"
                            },
                            "message": {
                                "type": "string",
                                "description": "Nội dung tin nhắn cần gửi"
                            }
                        },
                        "required": ["contact_name", "message"]
                    }
                }
            })
    
    # List devices tool
    tools.append({
        "type": "function",
        "function": {
            "name": "list_iot_devices",
            "description": "Liệt kê tất cả thiết bị IoT đã cấu hình",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    
    return tools


# Singleton instance
_controller_instance: Optional[IoTDeviceController] = None

def get_iot_controller(db_path: str = None) -> IoTDeviceController:
    """Get singleton instance of IoTDeviceController"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = IoTDeviceController(db_path)
    return _controller_instance
