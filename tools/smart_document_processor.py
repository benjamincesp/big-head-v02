"""
Smart Document Processor for Food Service 2025
Enhanced document reading with intelligent chunking and fallback mechanisms
"""

import os
import logging
import pandas as pd
import json
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import traceback

# PDF processing imports - prefer PyMuPDF for better text extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)

class SmartDocumentProcessor:
    """Enhanced document processor with intelligent parsing"""
    
    def __init__(self, folder_path: str):
        """
        Initialize smart document processor
        
        Args:
            folder_path: Path to folder containing documents
        """
        self.folder_path = folder_path
        self.supported_extensions = {'.pdf', '.xlsx', '.xls', '.txt', '.docx'}
        
        # Ensure folder exists
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            print(f"📁 DEBUG: Created folder: {folder_path}")
    
    def get_all_files(self) -> List[str]:
        """Get all supported files in the folder"""
        files = []
        if not os.path.exists(self.folder_path):
            return files
        
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in self.supported_extensions:
                    files.append(file_path)
        
        print(f"📚 DEBUG: Found {len(files)} supported files in {self.folder_path}")
        return sorted(files)
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with multiple fallback methods - PyMuPDF preferred"""
        text = ""
        extraction_method = ""
        
        print(f"📄 DEBUG: Processing PDF: {os.path.basename(file_path)}")
        
        # Method 1: Try PyMuPDF first (best results)
        if PYMUPDF_AVAILABLE:
            try:
                print("🔧 DEBUG: Trying PyMuPDF extraction...")
                text = self._extract_with_pymupdf(file_path)
                if text.strip():
                    extraction_method = "PyMuPDF"
                    print(f"✅ DEBUG: PyMuPDF extracted {len(text)} characters")
            except Exception as e:
                print(f"⚠️ DEBUG: PyMuPDF failed: {str(e)}")
        
        # Method 2: Fallback to PyPDF2 if PyMuPDF failed or unavailable
        if not text.strip() and PYPDF2_AVAILABLE:
            try:
                print("🔧 DEBUG: Trying PyPDF2 extraction...")
                text = self._extract_with_pypdf2(file_path)
                if text.strip():
                    extraction_method = "PyPDF2"
                    print(f"✅ DEBUG: PyPDF2 extracted {len(text)} characters")
            except Exception as e:
                print(f"⚠️ DEBUG: PyPDF2 failed: {str(e)}")
        
        # Clean and normalize text
        if text.strip():
            text = self._clean_text(text)
            print(f"✅ DEBUG: Final extraction ({extraction_method}): {len(text)} characters")
            return text
        else:
            print("⚠️ DEBUG: No text extracted from PDF with any method")
            return f"Documento PDF: {os.path.basename(file_path)} (contenido no disponible para extracción de texto)"
    
    def _extract_with_pymupdf(self, file_path: str) -> str:
        """Extract text using PyMuPDF (fitz)"""
        text = ""
        
        doc = fitz.open(file_path)
        
        for page_num in range(doc.page_count):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text.strip():
                    text += f"\\n--- Página {page_num + 1} ---\\n{page_text}\\n"
            except Exception as e:
                logger.warning(f"PyMuPDF: Error extracting page {page_num + 1}: {str(e)}")
                continue
        
        doc.close()
        return text
    
    def _extract_with_pypdf2(self, file_path: str) -> str:
        """Extract text using PyPDF2 as fallback"""
        text = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\\n--- Página {page_num + 1} ---\\n{page_text}\\n"
                except Exception as e:
                    logger.warning(f"PyPDF2: Error extracting page {page_num + 1}: {str(e)}")
                    continue
        
        return text
    
    def extract_text_from_excel(self, file_path: str) -> str:
        """Extract text from Excel files"""
        try:
            print(f"📊 DEBUG: Processing Excel: {os.path.basename(file_path)}")
            
            # Try different engines
            for engine in ['openpyxl', 'xlrd']:
                try:
                    if file_path.endswith('.xlsx'):
                        df = pd.read_excel(file_path, engine='openpyxl', sheet_name=None)
                    else:
                        df = pd.read_excel(file_path, engine='xlrd', sheet_name=None)
                    break
                except Exception as e:
                    continue
            else:
                raise Exception("Could not read Excel file with any engine")
            
            text_parts = []
            
            # Process each sheet
            for sheet_name, sheet_df in df.items():
                text_parts.append(f"\\n=== Hoja: {sheet_name} ===\\n")
                
                # Convert DataFrame to text intelligently
                if not sheet_df.empty:
                    # Get column headers
                    headers = [str(col) for col in sheet_df.columns if str(col) != 'nan']
                    if headers:
                        text_parts.append(f"Columnas: {', '.join(headers)}\\n")
                    
                    # Process rows
                    for idx, row in sheet_df.iterrows():
                        row_values = []
                        for col in sheet_df.columns:
                            value = row[col]
                            if pd.notna(value) and str(value).strip():
                                row_values.append(str(value).strip())
                        
                        if row_values:
                            text_parts.append(" | ".join(row_values))
                
                text_parts.append("\\n")
            
            text = "\\n".join(text_parts)
            text = self._clean_text(text)
            
            if text.strip():
                print(f"✅ DEBUG: Extracted {len(text)} characters from Excel")
                return text
            else:
                return f"Documento Excel: {os.path.basename(file_path)} (sin contenido legible)"
                
        except Exception as e:
            logger.error(f"Error processing Excel {file_path}: {str(e)}")
            print(f"❌ DEBUG: Excel processing failed: {str(e)}")
            return f"Documento Excel: {os.path.basename(file_path)} (error al procesar: {str(e)})"
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from any supported file type"""
        if not os.path.exists(file_path):
            return ""
        
        _, ext = os.path.splitext(file_path.lower())
        
        try:
            if ext == '.pdf':
                return self.extract_text_from_pdf(file_path)
            elif ext in ['.xlsx', '.xls']:
                return self.extract_text_from_excel(file_path)
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                return self._clean_text(text)
            else:
                return f"Archivo {os.path.basename(file_path)} (tipo {ext} no soportado completamente)"
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return f"Archivo {os.path.basename(file_path)} (error al extraer contenido: {str(e)})"
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\\s+', ' ', text)
        
        # Remove empty lines
        lines = [line.strip() for line in text.split('\\n') if line.strip()]
        
        # Join with single newlines
        text = '\\n'.join(lines)
        
        # Remove problematic characters
        text = text.replace('\\x00', '').replace('\\ufeff', '')
        
        return text.strip()
    
    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Intelligently chunk text for better vector search"""
        if not text or len(text) < chunk_size:
            return [text] if text else []
        
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap
                    if overlap > 0 and len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:] + "\\n" + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    # Paragraph itself is too long, split it
                    if len(paragraph) > chunk_size:
                        sentences = [s.strip() for s in paragraph.split('.') if s.strip()]
                        temp_chunk = ""
                        for sentence in sentences:
                            if len(temp_chunk) + len(sentence) > chunk_size:
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = sentence + "."
                            else:
                                temp_chunk += sentence + "."
                        if temp_chunk:
                            current_chunk = temp_chunk
                    else:
                        current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\\n\\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Filter out very short chunks
        chunks = [chunk for chunk in chunks if len(chunk) > 50]
        
        print(f"📝 DEBUG: Created {len(chunks)} chunks from text")
        return chunks
    
    def process_all_documents(self, chunk_size: int = 800, overlap: int = 100) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Process all documents in the folder and return chunks with metadata"""
        all_chunks = []
        all_metadata = []
        
        files = self.get_all_files()
        
        if not files:
            print("⚠️ DEBUG: No files found to process")
            # Create a fallback document
            fallback_text = f"""
            Food Service 2025 - Sistema de Información
            
            Este es un evento especializado en el sector de alimentos y servicios.
            El sistema está diseñado para proporcionar información sobre:
            
            - Expositores y empresas participantes
            - Estadísticas de visitantes y asistencia
            - Información general del evento
            - Planos y distribución del espacio
            - Programación y actividades
            
            Para obtener información específica, consulte los documentos disponibles
            en las carpetas correspondientes del sistema.
            """
            
            all_chunks.append(fallback_text.strip())
            all_metadata.append({
                'source': 'sistema_informacion',
                'file_type': 'texto',
                'chunk_index': 0,
                'total_chunks': 1,
                'processed_at': datetime.now().isoformat()
            })
        
        for file_path in files:
            try:
                print(f"🔄 DEBUG: Processing file: {os.path.basename(file_path)}")
                
                # Extract text
                text = self.extract_text_from_file(file_path)
                
                if not text.strip():
                    print(f"⚠️ DEBUG: No text extracted from {os.path.basename(file_path)}")
                    continue
                
                # Create chunks
                chunks = self.chunk_text(text, chunk_size, overlap)
                
                # Create metadata for each chunk
                for i, chunk in enumerate(chunks):
                    metadata = {
                        'source': os.path.basename(file_path),
                        'file_path': file_path,
                        'file_type': os.path.splitext(file_path)[1][1:],
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'chunk_size': len(chunk),
                        'processed_at': datetime.now().isoformat()
                    }
                    
                    all_chunks.append(chunk)
                    all_metadata.append(metadata)
                
                print(f"✅ DEBUG: Processed {len(chunks)} chunks from {os.path.basename(file_path)}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                print(f"❌ DEBUG: Failed to process {os.path.basename(file_path)}: {str(e)}")
                
                # Add error info as a document
                error_text = f"Error al procesar archivo {os.path.basename(file_path)}: {str(e)}"
                all_chunks.append(error_text)
                all_metadata.append({
                    'source': os.path.basename(file_path),
                    'file_path': file_path,
                    'file_type': 'error',
                    'chunk_index': 0,
                    'total_chunks': 1,
                    'error': str(e),
                    'processed_at': datetime.now().isoformat()
                })
        
        print(f"📚 DEBUG: Total processed: {len(all_chunks)} chunks from {len(files)} files")
        return all_chunks, all_metadata
    
    def get_folder_hash(self) -> str:
        """Calculate hash of all files in folder for change detection"""
        hash_md5 = hashlib.md5()
        
        files = self.get_all_files()
        for file_path in sorted(files):
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                file_info = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
                hash_md5.update(file_info.encode())
        
        return hash_md5.hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        files = self.get_all_files()
        
        stats = {
            'folder_path': self.folder_path,
            'total_files': len(files),
            'file_types': {},
            'folder_exists': os.path.exists(self.folder_path),
            'supported_extensions': list(self.supported_extensions)
        }
        
        for file_path in files:
            _, ext = os.path.splitext(file_path.lower())
            stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
        
        return stats