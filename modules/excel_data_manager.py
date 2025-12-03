"""
Excel Data Manager for Voice Command N8n Integration
Quản lý dữ liệu từ các file Excel: users, workflows, templates
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ExcelDataManager:
    """Quản lý dữ liệu từ các file Excel cho voice command system"""
    
    def __init__(self, data_dir: str = "data/voice_commands"):
        self.data_dir = data_dir
        self.users_df = None
        self.workflows_df = None
        self.templates_df = None
        
        # Load data khi khởi tạo
        self.load_all_data()
    
    def load_all_data(self):
        """Load tất cả dữ liệu từ các file CSV"""
        try:
            # Load users data
            users_path = os.path.join(self.data_dir, "users_contacts.csv")
            if os.path.exists(users_path):
                self.users_df = pd.read_csv(users_path)
                logger.info(f"Loaded {len(self.users_df)} users from {users_path}")
            else:
                logger.warning(f"Users file not found: {users_path}")
            
            # Load workflows data
            workflows_path = os.path.join(self.data_dir, "workflows_config.csv")
            if os.path.exists(workflows_path):
                self.workflows_df = pd.read_csv(workflows_path)
                logger.info(f"Loaded {len(self.workflows_df)} workflows from {workflows_path}")
            else:
                logger.warning(f"Workflows file not found: {workflows_path}")
            
            # Load templates data
            templates_path = os.path.join(self.data_dir, "message_templates.csv")
            if os.path.exists(templates_path):
                self.templates_df = pd.read_csv(templates_path)
                logger.info(f"Loaded {len(self.templates_df)} templates from {templates_path}")
            else:
                logger.warning(f"Templates file not found: {templates_path}")
                
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
    
    def get_user_uid(self, name: str) -> Optional[str]:
        """Tìm UID của user bằng tên"""
        if self.users_df is None:
            logger.error("Users data not loaded")
            return None
        
        try:
            user_row = self.users_df[self.users_df['Name'].str.lower() == name.lower()]
            if not user_row.empty:
                uid = user_row.iloc[0]['UID']
                logger.info(f"Found UID {uid} for user {name}")
                return uid
            else:
                logger.warning(f"User {name} not found in contacts")
                return None
        except Exception as e:
            logger.error(f"Error finding user UID for {name}: {e}")
            return None
    
    def get_user_info(self, name: str) -> Optional[Dict]:
        """Lấy thông tin đầy đủ của user"""
        if self.users_df is None:
            return None
        
        try:
            user_row = self.users_df[self.users_df['Name'].str.lower() == name.lower()]
            if not user_row.empty:
                user_info = user_row.iloc[0].to_dict()
                logger.info(f"Found user info for {name}: {user_info}")
                return user_info
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting user info for {name}: {e}")
            return None
    
    def get_workflow_config(self, platform: str, action_type: str) -> Optional[Dict]:
        """Lấy cấu hình workflow dựa trên platform và action type"""
        if self.workflows_df is None:
            return None
        
        try:
            workflow_row = self.workflows_df[
                (self.workflows_df['Platform'].str.lower() == platform.lower()) & 
                (self.workflows_df['Action_Type'].str.lower() == action_type.lower())
            ]
            
            if not workflow_row.empty:
                config = workflow_row.iloc[0].to_dict()
                logger.info(f"Found workflow config for {platform}/{action_type}: {config['Workflow_ID']}")
                return config
            else:
                logger.warning(f"No workflow found for {platform}/{action_type}")
                return None
        except Exception as e:
            logger.error(f"Error getting workflow config for {platform}/{action_type}: {e}")
            return None
    
    def get_all_workflows(self) -> List[Dict]:
        """Lấy danh sách tất cả workflows"""
        if self.workflows_df is None:
            return []
        
        return self.workflows_df.to_dict('records')
    
    def get_message_template(self, platform: str, scenario: str = "Normal") -> Optional[Dict]:
        """Lấy message template dựa trên platform và scenario"""
        if self.templates_df is None:
            return None
        
        try:
            template_row = self.templates_df[
                (self.templates_df['Platform'].str.lower() == platform.lower()) & 
                (self.templates_df['Scenario'].str.lower() == scenario.lower())
            ]
            
            if not template_row.empty:
                template = template_row.iloc[0].to_dict()
                logger.info(f"Found template for {platform}/{scenario}: {template['Template_ID']}")
                return template
            else:
                # Fallback to Normal scenario
                template_row = self.templates_df[
                    (self.templates_df['Platform'].str.lower() == platform.lower()) & 
                    (self.templates_df['Scenario'].str.lower() == "normal")
                ]
                if not template_row.empty:
                    template = template_row.iloc[0].to_dict()
                    logger.info(f"Using fallback template for {platform}: {template['Template_ID']}")
                    return template
                else:
                    logger.warning(f"No template found for {platform}/{scenario}")
                    return None
        except Exception as e:
            logger.error(f"Error getting template for {platform}/{scenario}: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Lấy danh sách tất cả users"""
        if self.users_df is None:
            return []
        
        return self.users_df.to_dict('records')
    
    def get_all_templates(self) -> List[Dict]:
        """Lấy danh sách tất cả templates"""
        if self.templates_df is None:
            return []
        
        return self.templates_df.to_dict('records')
    
    def refresh_data(self):
        """Refresh dữ liệu từ file Excel"""
        logger.info("Refreshing Excel data...")
        self.load_all_data()
    
    def validate_user_exists(self, name: str) -> bool:
        """Kiểm tra user có tồn tại không"""
        return self.get_user_uid(name) is not None
    
    def validate_workflow_exists(self, platform: str, action_type: str) -> bool:
        """Kiểm tra workflow có tồn tại không"""
        return self.get_workflow_config(platform, action_type) is not None


# Factory function
def get_excel_data_manager(data_dir: str = "data/voice_commands") -> ExcelDataManager:
    """Factory function để tạo ExcelDataManager instance"""
    return ExcelDataManager(data_dir)


# Test function
if __name__ == "__main__":
    # Test the Excel data manager
    manager = ExcelDataManager()
    
    print("=== TESTING EXCEL DATA MANAGER ===")
    
    # Test user lookup
    uid = manager.get_user_uid("A")
    print(f"User A UID: {uid}")
    
    # Test workflow lookup
    workflow = manager.get_workflow_config("Zalo", "Message")
    print(f"Zalo Message workflow: {workflow}")
    
    # Test template lookup
    template = manager.get_message_template("Zalo", "Normal")
    print(f"Zalo Normal template: {template}")
    
    # Test all data
    print(f"Total users: {len(manager.get_all_users())}")
    print(f"Total workflows: {len(manager.get_all_workflows())}")
    print(f"Total templates: {len(manager.get_all_templates())}")
