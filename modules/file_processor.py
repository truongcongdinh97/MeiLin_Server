"""
File Processor - Hỗ trợ upload và parse documents đa định dạng
Tích hợp auto-chunking và vector storage
"""

import os
import re
import PyPDF2
import docx
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import hashlib
import json
from datetime import datetime

class FileProcessor:
    """
    Xử lý file đa định dạng: PDF, DOCX, TXT, Excel
    Tự động parse, chunk, và lưu vào vector database
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_formats = ['.pdf', '.docx', '.txt', '.xlsx', '.csv']
        
        # Cache để tránh parse lại file
        self.file_cache = {}
        self.chunk_cache = {}
    
    def parse_document(self, file_path: str) -> List[Dict]:
        """
        Parse document từ nhiều định dạng
        Trả về danh sách các đoạn với metadata
        """
        file_path = Path(file_path)
        
        # Kiểm tra định dạng hỗ trợ
        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Định dạng không hỗ trợ: {file_path.suffix}")
        
        # Cache để tránh parse lại
        file_hash = self._get_file_hash(file_path)
        if file_hash in self.file_cache:
            return self.file_cache[file_hash]
        
        # Parse theo định dạng
        if file_path.suffix.lower() == '.pdf':
            content = self._parse_pdf(file_path)
        elif file_path.suffix.lower() == '.docx':
            content = self._parse_docx(file_path)
        elif file_path.suffix.lower() == '.txt':
            content = self._parse_txt(file_path)
        elif file_path.suffix.lower() in ['.xlsx', '.csv']:
            content = self._parse_excel(file_path)
        else:
            content = []
        
        # Thêm metadata
        parsed_docs = []
        for i, doc in enumerate(content):
            parsed_docs.append({
                'content': doc,
                'source': file_path.name,
                'page': i + 1 if file_path.suffix.lower() == '.pdf' else None,
                'file_type': file_path.suffix.lower(),
                'file_size': file_path.stat().st_size,
                'parse_date': datetime.now().isoformat()
            })
        
        # Lưu cache
        self.file_cache[file_hash] = parsed_docs
        return parsed_docs
    
    def _parse_pdf(self, file_path: Path) -> List[str]:
        """Parse PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Làm sạch text
                    text = self._clean_text(text)
                    if text.strip():
                        pages.append(text)
                
                return pages
        except Exception as e:
            raise Exception(f"Lỗi khi parse PDF: {e}")
    
    def _parse_docx(self, file_path: Path) -> List[str]:
        """Parse DOCX file"""
        try:
            doc = docx.Document(file_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            return paragraphs
        except Exception as e:
            raise Exception(f"Lỗi khi parse DOCX: {e}")
    
    def _parse_txt(self, file_path: Path) -> List[str]:
        """Parse TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Tách thành các đoạn
            paragraphs = re.split(r'\n\s*\n', content)
            return [p.strip() for p in paragraphs if p.strip()]
        except Exception as e:
            raise Exception(f"Lỗi khi parse TXT: {e}")
    
    def _parse_excel(self, file_path: Path) -> List[str]:
        """Parse Excel/CSV file"""
        try:
            if file_path.suffix.lower() == '.xlsx':
                df = pd.read_excel(file_path)
            else:  # .csv
                df = pd.read_csv(file_path)
            
            # Chuyển DataFrame thành text
            content = []
            
            # Thêm thông tin về cấu trúc
            content.append(f"File: {file_path.name}")
            content.append(f"Số dòng: {len(df)}, Số cột: {len(df.columns)}")
            content.append(f"Các cột: {', '.join(df.columns)}")
            
            # Thêm dữ liệu mẫu
            sample_size = min(10, len(df))
            for i in range(sample_size):
                row_data = []
                for col in df.columns:
                    row_data.append(f"{col}: {df.iloc[i][col]}")
                content.append(f"Dòng {i+1}: {', '.join(row_data)}")
            
            return ['\n'.join(content)]
        except Exception as e:
            raise Exception(f"Lỗi khi parse Excel/CSV: {e}")
    
    def _clean_text(self, text: str) -> str:
        """Làm sạch text"""
        # Loại bỏ các ký tự đặc biệt không cần thiết
        text = re.sub(r'[^\w\s.,!?\-:;\n]', '', text)
        
        # Chuẩn hóa khoảng trắng
        text = re.sub(r'\s+', ' ', text)
        
        # Loại bỏ các dòng trống liên tiếp
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Tạo hash để cache file"""
        file_stat = file_path.stat()
        hash_input = f"{file_path.name}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def chunk_documents(self, documents: List[Dict], chunk_size: int = None, 
                       chunk_overlap: int = None) -> List[Dict]:
        """
        Chia documents thành các chunks với overlap
        """
        if chunk_size is None:
            chunk_size = self.chunk_size
        if chunk_overlap is None:
            chunk_overlap = self.chunk_overlap
        
        all_chunks = []
        
        for doc in documents:
            content = doc['content']
            chunks = self._split_text_into_chunks(content, chunk_size, chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = doc.copy()
                chunk_metadata.update({
                    'chunk_id': f"{doc['source']}_chunk_{i+1}",
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': len(chunk),
                    'chunk_content': chunk
                })
                all_chunks.append(chunk_metadata)
        
        return all_chunks
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, 
                               chunk_overlap: int) -> List[str]:
        """Chia text thành các chunks với overlap"""
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text]
        
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            # Di chuyển với overlap
            start += chunk_size - chunk_overlap
            
            # Đảm bảo không bị lặp vô hạn
            if start >= len(words):
                break
        
        return chunks
    
    def upload_to_vector_db(self, chunks: List[Dict], collection_name: str = None, 
                           metadata: Dict = None) -> Dict:
        """
        Upload chunks vào vector database
        Trả về thông tin về quá trình upload
        """
        from modules.local_chromadb import get_local_chromadb
        
        if not chunks:
            return {'status': 'error', 'message': 'Không có chunks để upload'}
        
        # Tạo collection name nếu không có
        if collection_name is None:
            first_chunk = chunks[0]
            collection_name = f"documents_{first_chunk['source']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Kết nối với ChromaDB
        try:
            chroma_db = get_local_chromadb()
            
            # Tạo collection
            collection_metadata = {
                'type': 'document_collection',
                'source_file': chunks[0]['source'],
                'total_chunks': len(chunks),
                'upload_date': datetime.now().isoformat()
            }
            
            if metadata:
                collection_metadata.update(metadata)
            
            # Chuẩn bị documents và metadatas
            documents = []
            metadatas = []
            
            for chunk in chunks:
                documents.append(chunk['chunk_content'])
                chunk_metadata = {
                    'chunk_id': chunk['chunk_id'],
                    'chunk_index': chunk['chunk_index'],
                    'total_chunks': chunk['total_chunks'],
                    'source': chunk['source'],
                    'file_type': chunk['file_type'],
                    'file_size': chunk['file_size'],
                    'parse_date': chunk['parse_date']
                }
                metadatas.append(chunk_metadata)
            
            # Thêm vào ChromaDB
            chroma_db.add_documents(
                documents=documents,
                metadatas=metadatas,
                collection_name=collection_name
            )
            
            return {
                'status': 'success',
                'collection_name': collection_name,
                'total_chunks': len(chunks),
                'uploaded_chunks': len(documents),
                'metadata': collection_metadata
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Lỗi khi upload lên vector database: {e}'
            }
    
    def query_documents(self, query: str, file_filter: str = None, 
                       n_results: int = 5, collection_filter: str = None) -> List[Dict]:
        """
        Query documents từ vector database
        Có thể filter theo file hoặc collection
        """
        from modules.local_chromadb import get_local_chromadb
        
        try:
            chroma_db = get_local_chromadb()
            
            # Tạo filter metadata
            where_filter = {}
            if file_filter:
                where_filter['source'] = file_filter
            if collection_filter:
                # Nếu có collection filter, query trong collection đó
                results = chroma_db.query(
                    query_text=query,
                    n_results=n_results,
                    collection_name=collection_filter,
                    where=where_filter if where_filter else None
                )
            else:
                # Query tất cả collections
                results = chroma_db.query(
                    query_text=query,
                    n_results=n_results,
                    where=where_filter if where_filter else None
                )
            
            return results
            
        except Exception as e:
            print(f"Lỗi khi query documents: {e}")
            return []
    
    def process_file_upload(self, file_path: str, collection_name: str = None, 
                           metadata: Dict = None) -> Dict:
        """
        Xử lý toàn bộ quá trình upload file:
        1. Parse document
        2. Chunk documents
        3. Upload to vector database
        """
        try:
            # 1. Parse document
            print(f"Đang parse file: {file_path}")
            documents = self.parse_document(file_path)
            
            if not documents:
                return {'status': 'error', 'message': 'Không thể parse document'}
            
            # 2. Chunk documents
            print(f"Đang chunk documents...")
            chunks = self.chunk_documents(documents)
            
            # 3. Upload to vector database
            print(f"Đang upload {len(chunks)} chunks lên vector database...")
            upload_result = self.upload_to_vector_db(chunks, collection_name, metadata)
            
            # Tổng hợp kết quả
            result = {
                'status': upload_result['status'],
                'file_path': file_path,
                'parsed_documents': len(documents),
                'created_chunks': len(chunks),
                'upload_result': upload_result
            }
            
            if upload_result['status'] == 'success':
                result['collection_name'] = upload_result['collection_name']
                result['message'] = f"Upload thành công {len(chunks)} chunks vào collection {upload_result['collection_name']}"
            else:
                result['message'] = upload_result['message']
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Lỗi khi xử lý file upload: {e}',
                'file_path': file_path
            }
    
    def list_uploaded_documents(self) -> List[Dict]:
        """Liệt kê tất cả documents đã upload"""
        from modules.local_chromadb import get_local_chromadb
        
        try:
            chroma_db = get_local_chromadb()
            collections = chroma_db.client.list_collections()
            
            documents_info = []
            for collection in collections:
                # Lấy metadata từ collection
                count = collection.count()
                metadata = collection.metadata or {}
                
                documents_info.append({
                    'collection_name': collection.name,
                    'document_count': count,
                    'source_file': metadata.get('source_file', 'unknown'),
                    'upload_date': metadata.get('upload_date', 'unknown'),
                    'total_chunks': metadata.get('total_chunks', 0)
                })
            
            return documents_info
            
        except Exception as e:
            print(f"Lỗi khi lấy danh sách documents: {e}")
            return []
    
    def delete_document_collection(self, collection_name: str) -> Dict:
        """Xóa collection document"""
        from modules.local_chromadb import get_local_chromadb
        
        try:
            chroma_db = get_local_chromadb()
            chroma_db.delete_collection(collection_name)
            
            return {
                'status': 'success',
                'message': f'Đã xóa collection {collection_name}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Lỗi khi xóa collection: {e}'
            }


# Factory function
def get_file_processor(chunk_size: int = 500, chunk_overlap: int = 50):
    """Factory function để tạo FileProcessor"""
    return FileProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


# Test the module
if __name__ == "__main__":
    processor = FileProcessor()
    
    # Test với file mẫu (tạo file test trước)
    test_file = "test_document.txt"
    
    # Tạo file test nếu chưa có
    if not os.path.exists(test_file):
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Đây là file test cho File Processor.\n\n")
            f.write("File này chứa nội dung mẫu để test chức năng parse và chunk.\n\n")
            f.write("Chúng ta có thể test với nhiều đoạn văn khác nhau.\n\n")
            f.write("Mỗi đoạn sẽ được xử lý thành các chunks riêng biệt.\n\n")
    
    # Test parse và upload
    result = processor.process_file_upload(test_file)
    print("Kết quả upload:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test query
    if result.get('status') == 'success':
        query_results = processor.query_documents("test chức năng")
        print("\nKết quả query:")
        print(json.dumps(query_results, indent=2, ensure_ascii=False))
