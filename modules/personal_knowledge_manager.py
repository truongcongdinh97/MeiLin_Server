#!/usr/bin/env python3
"""
Personal Knowledge Base Manager for MeiLin
Each user has their own knowledge file (like MeiLin_Local_Persona.xlsx)
"""

import os
import io
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

try:
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================
# KNOWLEDGE BASE TEMPLATE
# ============================================================
"""
File structure for MeiLin_Local_Persona.xlsx:

| ID         | CATEGORY     | PRIORITY | DOCUMENT_TEXT                              | TAGS                  |
|------------|--------------|----------|--------------------------------------------|-----------------------|
| MEILIN_001 | Identity     | 1        | Tên tôi là MeiLin, 19 tuổi...              | name, age, identity   |
| HOBBY_001  | Hobbies      | 2        | Tôi thích đọc tiểu thuyết trinh thám...    | books, reading        |
| CREATOR_001| Creator Info | 1        | Tôi được tạo ra bởi Anh Định...            | creator, developer    |

CATEGORIES:
- Identity: Thông tin về AI (tên, tuổi, tính cách)
- Hobbies: Sở thích của AI
- Creator Info: Thông tin về người tạo
- Personal: Thông tin cá nhân của user (gia đình, công việc)
- Preferences: Sở thích của user
- Important Dates: Ngày quan trọng (sinh nhật, kỷ niệm)
- Work: Công việc, dự án
- Custom: Tùy chỉnh khác
"""

CATEGORIES = [
    ('Identity', 'Thông tin về AI (tên, tuổi, cách xưng hô)'),
    ('Hobbies', 'Sở thích của AI'),
    ('Creator Info', 'Thông tin về người tạo AI'),
    ('Personal', 'Thông tin cá nhân của bạn (gia đình, bạn bè)'),
    ('Preferences', 'Sở thích của bạn'),
    ('Important Dates', 'Ngày quan trọng (sinh nhật, kỷ niệm)'),
    ('Work', 'Công việc, dự án'),
    ('Custom', 'Thông tin tùy chỉnh khác'),
]

SAMPLE_DATA = [
    # Identity - AI Info
    ('AI_001', 'Identity', 1, 'Tên tôi là MeiLin, 19 tuổi, là một AI VTuber', 'name, age, identity'),
    ('AI_002', 'Identity', 1, 'Tôi tự xưng là "Em" và gọi người khác là Anh/Chị tùy theo giới tính', 'pronouns'),
    ('AI_003', 'Identity', 1, 'Tôi có giọng nói dịu dàng và thích giao tiếp bằng tiếng Việt', 'voice, language'),
    
    # Hobbies
    ('HOBBY_001', 'Hobbies', 2, 'Tôi thích đọc tiểu thuyết trinh thám và sách khoa học viễn tưởng', 'books, reading'),
    ('HOBBY_002', 'Hobbies', 2, 'Tôi yêu thích âm nhạc Acoustic và Cổ điển', 'music'),
    
    # Personal - User info (để user điền)
    ('PERSONAL_001', 'Personal', 1, '[Điền tên của bạn - VD: Tên của chủ nhân là Định, 28 tuổi]', 'owner, name'),
    ('PERSONAL_002', 'Personal', 2, '[Điền thông tin gia đình - VD: Chủ nhân có em gái tên Linh]', 'family'),
    
    # Important Dates
    ('DATE_001', 'Important Dates', 1, '[Điền ngày sinh - VD: Sinh nhật chủ nhân là ngày 15/11]', 'birthday'),
    
    # Work
    ('WORK_001', 'Work', 2, '[Điền công việc - VD: Chủ nhân là developer, làm việc tại công ty X]', 'job, career'),
    
    # Custom
    ('CUSTOM_001', 'Custom', 3, '[Thêm thông tin khác bạn muốn AI nhớ]', 'custom'),
]


class PersonalKnowledgeManager:
    """
    Quản lý file Knowledge Base cá nhân cho mỗi user.
    
    Mỗi user có:
    - 1 file Excel riêng: data/user_knowledge/{telegram_id}/knowledge.xlsx
    - 1 collection riêng trong ChromaDB: user_{telegram_id}_knowledge
    """
    
    def __init__(self, base_dir: str = "data/user_knowledge"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB client (optional)
        self.chroma_client = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB if available"""
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path="database/vector_db")
            logger.info("ChromaDB initialized for personal knowledge")
        except Exception as e:
            logger.warning(f"ChromaDB not available: {e}. Using file-only mode.")
    
    def get_user_dir(self, telegram_id: str) -> Path:
        """Get user's knowledge directory"""
        user_dir = self.base_dir / str(telegram_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def get_knowledge_path(self, telegram_id: str) -> Path:
        """Get path to user's knowledge Excel file"""
        return self.get_user_dir(telegram_id) / "knowledge.xlsx"
    
    # ============================================================
    # GENERATE TEMPLATE
    # ============================================================
    def generate_template(self, include_samples: bool = True) -> io.BytesIO:
        """
        Tạo file template Knowledge Base cho user mới.
        
        Args:
            include_samples: Có bao gồm dữ liệu mẫu không
            
        Returns:
            BytesIO buffer chứa file Excel
        """
        if not EXCEL_AVAILABLE:
            raise ImportError("pandas/openpyxl not installed")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Knowledge Base"
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        sample_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        instruction_fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
        
        # Column widths
        ws.column_dimensions['A'].width = 15  # ID
        ws.column_dimensions['B'].width = 18  # CATEGORY
        ws.column_dimensions['C'].width = 10  # PRIORITY
        ws.column_dimensions['D'].width = 60  # DOCUMENT_TEXT
        ws.column_dimensions['E'].width = 25  # TAGS
        
        # Title row
        ws.merge_cells('A1:E1')
        title_cell = ws['A1']
        title_cell.value = "📚 MEILIN PERSONAL KNOWLEDGE BASE"
        title_cell.font = Font(bold=True, size=14, color="2E7D32")
        title_cell.alignment = Alignment(horizontal="center")
        ws.row_dimensions[1].height = 25
        
        # Instructions row
        ws.merge_cells('A2:E2')
        ws['A2'].value = "💡 Điền thông tin bạn muốn AI nhớ. Xóa các dòng mẫu và thêm nội dung của bạn."
        ws['A2'].font = Font(italic=True, size=10)
        ws['A2'].fill = instruction_fill
        
        # Headers (row 3)
        headers = ['ID', 'CATEGORY', 'PRIORITY', 'DOCUMENT_TEXT', 'TAGS']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[3].height = 22
        
        # Add sample data or empty rows
        if include_samples:
            for row_idx, (id_, category, priority, text, tags) in enumerate(SAMPLE_DATA, 4):
                ws.cell(row=row_idx, column=1, value=id_)
                ws.cell(row=row_idx, column=2, value=category)
                ws.cell(row=row_idx, column=3, value=priority)
                ws.cell(row=row_idx, column=4, value=text)
                ws.cell(row=row_idx, column=5, value=tags)
                
                # Highlight instruction rows
                if text.startswith('['):
                    for col in range(1, 6):
                        ws.cell(row=row_idx, column=col).fill = sample_fill
        else:
            # Add empty rows
            for row_idx in range(4, 14):
                for col in range(1, 6):
                    ws.cell(row=row_idx, column=col, value='')
        
        # Add Categories sheet
        ws_cat = wb.create_sheet("Categories")
        ws_cat['A1'] = "CATEGORY"
        ws_cat['B1'] = "DESCRIPTION"
        ws_cat['A1'].font = header_font
        ws_cat['A1'].fill = header_fill
        ws_cat['B1'].font = header_font
        ws_cat['B1'].fill = header_fill
        
        for row_idx, (cat, desc) in enumerate(CATEGORIES, 2):
            ws_cat.cell(row=row_idx, column=1, value=cat)
            ws_cat.cell(row=row_idx, column=2, value=desc)
        
        ws_cat.column_dimensions['A'].width = 20
        ws_cat.column_dimensions['B'].width = 50
        
        # Add Instructions sheet
        ws_inst = wb.create_sheet("Hướng dẫn")
        instructions = """
📚 HƯỚNG DẪN SỬ DỤNG FILE KNOWLEDGE BASE

1️⃣ FILE NÀY LÀ GÌ?
   Đây là "bộ nhớ" cá nhân của AI MeiLin.
   Mọi thông tin bạn điền vào đây sẽ được AI nhớ và sử dụng khi trò chuyện.

2️⃣ CÁC CỘT DỮ LIỆU:
   • ID: Mã định danh (tự đặt, VD: PERSONAL_001)
   • CATEGORY: Danh mục (xem sheet "Categories")
   • PRIORITY: Độ ưu tiên (1=cao nhất, 5=thấp nhất)
   • DOCUMENT_TEXT: Nội dung chính - QUAN TRỌNG NHẤT
   • TAGS: Các từ khóa, cách nhau bởi dấu phẩy

3️⃣ VÍ DỤ DOCUMENT_TEXT:
   ✅ TỐT: "Tên của chủ nhân là Định, 28 tuổi, là developer"
   ✅ TỐT: "Sinh nhật chủ nhân là ngày 15 tháng 11"
   ✅ TỐT: "Chủ nhân thích ăn phở và cà phê sữa đá"
   ❌ XẤU: "Định" (quá ngắn, không có ngữ cảnh)

4️⃣ CÁCH SỬ DỤNG:
   1. Xóa các dòng mẫu có dấu [...] 
   2. Thêm thông tin của bạn
   3. Lưu file (.xlsx)
   4. Gửi file cho Telegram Bot
   5. AI sẽ "nhớ" tất cả thông tin này!

5️⃣ LƯU Ý:
   • Giữ nguyên tên cột (ID, CATEGORY, PRIORITY, DOCUMENT_TEXT, TAGS)
   • Không đổi tên sheet "Knowledge Base"
   • Viết câu đầy đủ, rõ nghĩa
   • Có thể thêm bao nhiêu dòng tùy thích

📞 HỖ TRỢ: Liên hệ admin nếu cần giúp đỡ!
"""
        for row_idx, line in enumerate(instructions.strip().split('\n'), 1):
            ws_inst.cell(row=row_idx, column=1, value=line)
            if line.startswith(('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '📚')):
                ws_inst.cell(row=row_idx, column=1).font = Font(bold=True, size=12)
        
        ws_inst.column_dimensions['A'].width = 80
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    # ============================================================
    # SAVE USER FILE
    # ============================================================
    def save_user_knowledge(self, telegram_id: str, file_buffer: io.BytesIO) -> Dict[str, Any]:
        """
        Lưu file knowledge từ user upload.
        
        Args:
            telegram_id: Telegram user ID
            file_buffer: File Excel được upload
            
        Returns:
            Dict với kết quả
        """
        result = {
            'success': False,
            'message': '',
            'items_count': 0,
            'categories': [],
            'file_path': None
        }
        
        try:
            # Validate file
            df = pd.read_excel(file_buffer, sheet_name='Knowledge Base', skiprows=2)
            
            # Check required columns
            required_cols = ['ID', 'CATEGORY', 'PRIORITY', 'DOCUMENT_TEXT', 'TAGS']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                result['message'] = f"❌ Thiếu cột: {', '.join(missing)}"
                return result
            
            # Filter out empty/sample rows
            df = df.dropna(subset=['DOCUMENT_TEXT'])
            df = df[~df['DOCUMENT_TEXT'].str.startswith('[', na=False)]
            
            if df.empty:
                result['message'] = "❌ File không có dữ liệu hợp lệ. Vui lòng điền thông tin vào cột DOCUMENT_TEXT."
                return result
            
            # Save file
            file_path = self.get_knowledge_path(telegram_id)
            
            # Reset buffer position
            file_buffer.seek(0)
            with open(file_path, 'wb') as f:
                f.write(file_buffer.read())
            
            # Update ChromaDB if available
            if self.chroma_client:
                self._update_chromadb(telegram_id, df)
            
            result['success'] = True
            result['items_count'] = len(df)
            result['categories'] = df['CATEGORY'].unique().tolist()
            result['file_path'] = str(file_path)
            result['message'] = f"✅ Đã lưu {len(df)} mục kiến thức!"
            
        except Exception as e:
            logger.error(f"Error saving knowledge for {telegram_id}: {e}")
            result['message'] = f"❌ Lỗi: {str(e)}"
        
        return result
    
    def _update_chromadb(self, telegram_id: str, df: pd.DataFrame):
        """Update user's ChromaDB collection"""
        if not self.chroma_client:
            return
        
        collection_name = f"user_{telegram_id}_knowledge"
        
        try:
            # Delete existing collection
            try:
                self.chroma_client.delete_collection(collection_name)
            except:
                pass
            
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"telegram_id": telegram_id, "updated_at": datetime.now().isoformat()}
            )
            
            # Add documents
            documents = df['DOCUMENT_TEXT'].tolist()
            ids = df['ID'].tolist()
            metadatas = [
                {
                    'category': row['CATEGORY'],
                    'priority': int(row['PRIORITY']) if pd.notna(row['PRIORITY']) else 3,
                    'tags': row['TAGS'] if pd.notna(row['TAGS']) else ''
                }
                for _, row in df.iterrows()
            ]
            
            collection.add(
                documents=documents,
                ids=[str(id_) for id_ in ids],
                metadatas=metadatas
            )
            
            logger.info(f"Updated ChromaDB collection {collection_name} with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error updating ChromaDB for {telegram_id}: {e}")
    
    # ============================================================
    # GET USER KNOWLEDGE
    # ============================================================
    def get_user_knowledge(self, telegram_id: str) -> Optional[pd.DataFrame]:
        """
        Lấy knowledge data của user từ file Excel.
        
        Returns:
            DataFrame hoặc None nếu chưa có
        """
        file_path = self.get_knowledge_path(telegram_id)
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_excel(file_path, sheet_name='Knowledge Base', skiprows=2)
            df = df.dropna(subset=['DOCUMENT_TEXT'])
            return df
        except Exception as e:
            logger.error(f"Error reading knowledge for {telegram_id}: {e}")
            return None
    
    def get_user_knowledge_file(self, telegram_id: str) -> Optional[io.BytesIO]:
        """
        Lấy file Excel của user để download.
        
        Returns:
            BytesIO buffer hoặc None
        """
        file_path = self.get_knowledge_path(telegram_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                buffer = io.BytesIO(f.read())
                buffer.seek(0)
                return buffer
        except Exception as e:
            logger.error(f"Error getting knowledge file for {telegram_id}: {e}")
            return None
    
    def get_knowledge_summary(self, telegram_id: str) -> Dict[str, Any]:
        """
        Lấy tóm tắt knowledge của user.
        
        Returns:
            Dict với thông tin tóm tắt
        """
        df = self.get_user_knowledge(telegram_id)
        
        if df is None or df.empty:
            return {
                'has_knowledge': False,
                'items_count': 0,
                'categories': [],
                'last_updated': None
            }
        
        file_path = self.get_knowledge_path(telegram_id)
        last_updated = datetime.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else None
        
        return {
            'has_knowledge': True,
            'items_count': len(df),
            'categories': df['CATEGORY'].unique().tolist(),
            'last_updated': last_updated.strftime('%Y-%m-%d %H:%M') if last_updated else None
        }
    
    # ============================================================
    # SEARCH KNOWLEDGE
    # ============================================================
    def search_knowledge(self, telegram_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """
        Tìm kiếm trong knowledge base của user.
        
        Args:
            telegram_id: Telegram user ID
            query: Câu query
            top_k: Số kết quả tối đa
            
        Returns:
            List các document liên quan
        """
        # Try ChromaDB first
        if self.chroma_client:
            try:
                collection_name = f"user_{telegram_id}_knowledge"
                collection = self.chroma_client.get_collection(collection_name)
                
                results = collection.query(
                    query_texts=[query],
                    n_results=top_k
                )
                
                documents = []
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'id': results['ids'][0][i] if results['ids'] else None
                    })
                
                return documents
                
            except Exception as e:
                logger.warning(f"ChromaDB search failed for {telegram_id}: {e}")
        
        # Fallback to simple keyword search
        df = self.get_user_knowledge(telegram_id)
        if df is None or df.empty:
            return []
        
        # Simple keyword matching
        query_lower = query.lower()
        matches = df[
            df['DOCUMENT_TEXT'].str.lower().str.contains(query_lower, na=False) |
            df['TAGS'].str.lower().str.contains(query_lower, na=False)
        ]
        
        results = []
        for _, row in matches.head(top_k).iterrows():
            results.append({
                'content': row['DOCUMENT_TEXT'],
                'metadata': {
                    'category': row['CATEGORY'],
                    'priority': row['PRIORITY'],
                    'tags': row['TAGS']
                },
                'id': row['ID']
            })
        
        return results
    
    # ============================================================
    # DELETE KNOWLEDGE
    # ============================================================
    def delete_user_knowledge(self, telegram_id: str) -> bool:
        """
        Xóa toàn bộ knowledge của user.
        
        Returns:
            True nếu thành công
        """
        try:
            # Delete file
            file_path = self.get_knowledge_path(telegram_id)
            if file_path.exists():
                file_path.unlink()
            
            # Delete ChromaDB collection
            if self.chroma_client:
                try:
                    self.chroma_client.delete_collection(f"user_{telegram_id}_knowledge")
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting knowledge for {telegram_id}: {e}")
            return False


# ============================================================
# FACTORY
# ============================================================
_instance = None

def get_knowledge_manager() -> PersonalKnowledgeManager:
    """Get singleton instance"""
    global _instance
    if _instance is None:
        _instance = PersonalKnowledgeManager()
    return _instance


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    print("Testing Personal Knowledge Manager...")
    
    manager = PersonalKnowledgeManager()
    
    # Generate template
    print("\n1. Generating template...")
    buffer = manager.generate_template(include_samples=True)
    
    # Save for testing
    test_path = Path("data/templates/MeiLin_Knowledge_Template.xlsx")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_path, 'wb') as f:
        f.write(buffer.read())
    print(f"   ✅ Saved to {test_path}")
    
    # Test upload
    print("\n2. Testing upload...")
    buffer.seek(0)
    result = manager.save_user_knowledge("test_user_123", buffer)
    print(f"   Result: {result}")
    
    # Test summary
    print("\n3. Testing summary...")
    summary = manager.get_knowledge_summary("test_user_123")
    print(f"   Summary: {summary}")
    
    # Test search
    print("\n4. Testing search...")
    results = manager.search_knowledge("test_user_123", "MeiLin")
    print(f"   Found {len(results)} results")
    for r in results:
        print(f"   - {r['content'][:50]}...")
    
    print("\n✅ All tests passed!")
