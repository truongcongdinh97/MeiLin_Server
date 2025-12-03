"""
OTA Manager for MeiLin ESP32 Firmware
Quản lý Over-the-Air firmware updates với version control và rollback protection
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class FirmwareInfo:
    """Thông tin firmware version"""
    version: str
    file_path: str
    file_size: int
    md5_hash: str
    release_date: str
    changelog: str
    compatible_boards: List[str]
    min_esp_idf_version: str
    requires_partition_change: bool

class OTAManager:
    """Quản lý OTA firmware updates cho MeiLin ESP32"""
    
    def __init__(self, firmware_dir: str = "firmware", config_path: str = "config/ota_config.json"):
        """
        Initialize OTA Manager
        
        Args:
            firmware_dir: Thư mục chứa firmware binaries
            config_path: Đường dẫn đến file config OTA
        """
        self.firmware_dir = Path(firmware_dir)
        self.config_path = config_path
        self.firmware_versions = {}
        self.device_registry = {}
        self.update_log = []
        
        # Tạo thư mục firmware nếu chưa có
        self.firmware_dir.mkdir(exist_ok=True)
        
        self._load_config()
        self._scan_firmware_files()
    
    def _load_config(self):
        """Load OTA configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.settings = config.get('settings', {})
                    self.board_compatibility = config.get('board_compatibility', {})
                    self.update_policies = config.get('update_policies', {})
            else:
                # Default configuration
                self.settings = {
                    'enable_ota': True,
                    'require_https': False,
                    'max_firmware_size': 4194304,  # 4MB
                    'auto_rollback': True,
                    'rollback_timeout': 300,  # 5 minutes
                    'signature_required': False
                }
                self.board_compatibility = {
                    'esp32-s3': ['ESP32-S3', 'ESP-BOX', 'M5Stack-CoreS3'],
                    'esp32-c3': ['ESP32-C3', 'XiaGe-Mini-C3'],
                    'esp32-p4': ['ESP32-P4']
                }
                self.update_policies = {
                    'force_update': False,
                    'staged_rollout': True,
                    'max_concurrent_updates': 10
                }
                self._save_config()
        except Exception as e:
            logging.error(f"Error loading OTA config: {e}")
            self.settings = {}
            self.board_compatibility = {}
            self.update_policies = {}
    
    def _save_config(self):
        """Save OTA configuration"""
        try:
            config = {
                'settings': self.settings,
                'board_compatibility': self.board_compatibility,
                'update_policies': self.update_policies,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving OTA config: {e}")
    
    def _scan_firmware_files(self):
        """Scan firmware directory và load firmware info"""
        self.firmware_versions = {}
        
        for firmware_file in self.firmware_dir.glob("*.bin"):
            try:
                # Parse version từ filename: meilin-v1.2.3-esp32s3.bin
                filename = firmware_file.stem
                parts = filename.split('-')
                
                if len(parts) >= 3 and parts[0] == 'meilin':
                    version = parts[1]  # v1.2.3
                    board_type = parts[2]  # esp32s3
                    
                    # Calculate file hash
                    file_size = firmware_file.stat().st_size
                    md5_hash = self._calculate_file_hash(firmware_file)
                    
                    firmware_info = FirmwareInfo(
                        version=version,
                        file_path=str(firmware_file),
                        file_size=file_size,
                        md5_hash=md5_hash,
                        release_date=datetime.fromtimestamp(firmware_file.stat().st_mtime).isoformat(),
                        changelog=f"Firmware version {version} for {board_type}",
                        compatible_boards=[board_type],
                        min_esp_idf_version="5.1",
                        requires_partition_change=False
                    )
                    
                    key = f"{version}-{board_type}"
                    self.firmware_versions[key] = firmware_info
                    
            except Exception as e:
                logging.error(f"Error parsing firmware file {firmware_file}: {e}")
        
        logging.info(f"Loaded {len(self.firmware_versions)} firmware versions")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash của firmware file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def check_for_updates(self, device_id: str, current_version: str, board_type: str) -> Dict:
        """
        Kiểm tra có firmware update không
        
        Args:
            device_id: ID của ESP32 device
            current_version: Version hiện tại (v1.0.0)
            board_type: Loại board (esp32s3, esp32c3, etc.)
        
        Returns:
            Dict với update info hoặc empty nếu không có update
        """
        if not self.settings.get('enable_ota', True):
            return {}
        
        # Tìm firmware mới nhất cho board type
        latest_firmware = None
        for key, firmware in self.firmware_versions.items():
            if board_type in firmware.compatible_boards:
                if not latest_firmware or self._compare_versions(firmware.version, latest_firmware.version) > 0:
                    latest_firmware = firmware
        
        if not latest_firmware:
            return {}  # Không có firmware cho board này
        
        # So sánh version
        if self._compare_versions(latest_firmware.version, current_version) > 0:
            # Có update available
            return {
                'update_available': True,
                'latest_version': latest_firmware.version,
                'current_version': current_version,
                'file_size': latest_firmware.file_size,
                'md5_hash': latest_firmware.md5_hash,
                'changelog': latest_firmware.changelog,
                'download_url': f"/api/ota/download/{latest_firmware.version}/{board_type}",
                'requires_restart': True
            }
        
        return {'update_available': False}
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        So sánh hai version strings
        
        Returns:
            -1 if version1 < version2
            0 if version1 == version2  
            1 if version1 > version2
        """
        # Remove 'v' prefix và split thành parts
        v1_parts = version1.lstrip('v').split('.')
        v2_parts = version2.lstrip('v').split('.')
        
        # Compare từng part
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = int(v1_parts[i]) if i < len(v1_parts) else 0
            v2 = int(v2_parts[i]) if i < len(v2_parts) else 0
            
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        
        return 0
    
    def get_firmware_file(self, version: str, board_type: str) -> Optional[FirmwareInfo]:
        """Lấy firmware file info theo version và board type"""
        key = f"{version}-{board_type}"
        return self.firmware_versions.get(key)
    
    def register_device(self, device_id: str, board_type: str, current_version: str, ip_address: str):
        """Đăng ký device vào OTA system"""
        self.device_registry[device_id] = {
            'board_type': board_type,
            'current_version': current_version,
            'ip_address': ip_address,
            'last_seen': datetime.now().isoformat(),
            'update_status': 'idle'
        }
        
        logging.info(f"Device registered: {device_id} ({board_type}) v{current_version}")
    
    def log_update_attempt(self, device_id: str, from_version: str, to_version: str, success: bool, error_msg: str = ""):
        """Log OTA update attempt"""
        log_entry = {
            'device_id': device_id,
            'from_version': from_version,
            'to_version': to_version,
            'success': success,
            'error_message': error_msg,
            'timestamp': datetime.now().isoformat()
        }
        
        self.update_log.append(log_entry)
        
        # Giữ log trong giới hạn
        if len(self.update_log) > 1000:
            self.update_log = self.update_log[-1000:]
        
        # Update device registry
        if device_id in self.device_registry:
            self.device_registry[device_id]['update_status'] = 'success' if success else 'failed'
            self.device_registry[device_id]['last_update'] = datetime.now().isoformat()
    
    def get_update_stats(self) -> Dict:
        """Lấy thống kê OTA updates"""
        total_attempts = len(self.update_log)
        successful = sum(1 for log in self.update_log if log['success'])
        failed = total_attempts - successful
        
        return {
            'total_devices': len(self.device_registry),
            'total_update_attempts': total_attempts,
            'successful_updates': successful,
            'failed_updates': failed,
            'success_rate': successful / total_attempts if total_attempts > 0 else 0
        }
    
    def validate_firmware_upload(self, file_path: str, board_type: str) -> Dict:
        """
        Validate firmware file trước khi upload
        
        Returns:
            Dict với validation result
        """
        try:
            file_size = os.path.getsize(file_path)
            
            # Check file size
            max_size = self.settings.get('max_firmware_size', 4194304)
            if file_size > max_size:
                return {
                    'valid': False,
                    'error': f"Firmware quá lớn ({file_size} > {max_size})"
                }
            
            # Check file type (basic)
            if not file_path.endswith('.bin'):
                return {
                    'valid': False,
                    'error': "File phải có định dạng .bin"
                }
            
            # TODO: Add signature verification nếu cần
            
            return {
                'valid': True,
                'file_size': file_size,
                'md5_hash': self._calculate_file_hash(Path(file_path))
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Validation error: {str(e)}"
            }

# Singleton instance
_ota_manager_instance = None

def get_ota_manager() -> OTAManager:
    """Get singleton OTA manager instance"""
    global _ota_manager_instance
    if _ota_manager_instance is None:
        _ota_manager_instance = OTAManager()
    return _ota_manager_instance


if __name__ == "__main__":
    # Test OTA Manager
    print("Testing OTA Manager...")
    
    manager = OTAManager()
    
    print("\n📊 Firmware versions loaded:")
    for key, firmware in manager.firmware_versions.items():
        print(f"  {key}: {firmware.file_size} bytes, MD5: {firmware.md5_hash[:8]}...")
    
    print("\n🔍 Testing update check:")
    update_info = manager.check_for_updates(
        device_id="esp32-test-001",
        current_version="v1.0.0", 
        board_type="esp32s3"
    )
    
    if update_info.get('update_available'):
        print(f"  Update available: {update_info['latest_version']}")
        print(f"  Download URL: {update_info['download_url']}")
    else:
        print("  No updates available")
    
    print("\n📈 Update statistics:")
    stats = manager.get_update_stats()
    print(f"  Total devices: {stats['total_devices']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
