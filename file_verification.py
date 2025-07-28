"""
File Verification Tool for Food Service 2025 Document Processing
Comprehensive testing suite to diagnose PDF processing, text extraction, and vector store indexing issues
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import traceback
from datetime import datetime

# PDF processing imports
try:
    import PyPDF2
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("❌ PyPDF2 not available")

# Vector store and embedding imports
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    print("❌ Vector store dependencies not available")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileVerificationTool:
    """
    Comprehensive file verification and diagnosis tool
    Tests all stages of document processing pipeline
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize the verification tool"""
        self.verbose = verbose
        self.results = {}
        self.errors = []
        
        print("🔍 Initializing File Verification Tool...")
        
        # Initialize components if available
        if VECTOR_STORE_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Sentence transformer loaded")
            except Exception as e:
                print(f"❌ Failed to load sentence transformer: {e}")
                self.embedder = None
        else:
            self.embedder = None
            
        print("✅ File Verification Tool initialized")
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with console output"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
        
        if level == "ERROR":
            logger.error(message)
            self.errors.append(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def verify_file_existence(self, file_path: str) -> Dict[str, Any]:
        """Verify file exists and get basic info"""
        self.log(f"🔍 Checking file existence: {file_path}")
        
        result = {
            "exists": False,
            "size": 0,
            "extension": "",
            "is_readable": False,
            "error": None
        }
        
        try:
            path = Path(file_path)
            result["exists"] = path.exists()
            
            if result["exists"]:
                stat = path.stat()
                result["size"] = stat.st_size
                result["extension"] = path.suffix.lower()
                result["is_readable"] = os.access(file_path, os.R_OK)
                
                self.log(f"✅ File exists - Size: {result['size']} bytes, Extension: {result['extension']}")
            else:
                self.log(f"❌ File does not exist", "ERROR")
                
        except Exception as e:
            error_msg = f"Error checking file: {str(e)}"
            result["error"] = error_msg
            self.log(error_msg, "ERROR")
            
        return result
    
    def verify_pdf_structure(self, file_path: str) -> Dict[str, Any]:
        """Verify PDF file structure and metadata"""
        self.log(f"📄 Analyzing PDF structure: {file_path}")
        
        result = {
            "is_valid_pdf": False,
            "num_pages": 0,
            "metadata": {},
            "encryption": False,
            "warnings": [],
            "error": None
        }
        
        if not PYPDF2_AVAILABLE:
            result["error"] = "PyPDF2 not available"
            return result
            
        try:
            with open(file_path, 'rb') as file:
                # Capture warnings
                import warnings
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    
                    reader = PdfReader(file)
                    
                    # Capture any warnings
                    for warning in w:
                        result["warnings"].append(str(warning.message))
                        self.log(f"⚠️  PDF Warning: {warning.message}", "WARNING")
                
                result["is_valid_pdf"] = True
                result["num_pages"] = len(reader.pages)
                result["encryption"] = reader.is_encrypted
                
                # Get metadata
                if reader.metadata:
                    result["metadata"] = {
                        str(key): str(value) for key, value in reader.metadata.items()
                    }
                
                self.log(f"✅ PDF structure valid - Pages: {result['num_pages']}, Encrypted: {result['encryption']}")
                
                if result["warnings"]:
                    self.log(f"⚠️  {len(result['warnings'])} PDF warnings detected")
                    
        except Exception as e:
            error_msg = f"PDF structure error: {str(e)}"
            result["error"] = error_msg
            self.log(error_msg, "ERROR")
            
        return result
    
    def verify_text_extraction(self, file_path: str) -> Dict[str, Any]:
        """Test text extraction from PDF using multiple methods"""
        self.log(f"📝 Testing text extraction: {file_path}")
        
        result = {
            "extraction_successful": False,
            "total_text_length": 0,
            "pages_with_text": 0,
            "sample_text": "",
            "empty_pages": [],
            "extraction_method": "Multiple",
            "method_results": {},
            "error": None
        }
        
        # Try PyMuPDF first (usually best results)
        pymupdf_result = self._extract_with_pymupdf(file_path)
        result["method_results"]["pymupdf"] = pymupdf_result
        
        # Try PyPDF2 as fallback
        pypdf2_result = self._extract_with_pypdf2(file_path)
        result["method_results"]["pypdf2"] = pypdf2_result
        
        # Choose the best result (most text extracted)
        best_method = "pymupdf" if pymupdf_result["total_text_length"] >= pypdf2_result["total_text_length"] else "pypdf2"
        best_result = result["method_results"][best_method]
        
        # Update main result with best extraction
        result["extraction_successful"] = best_result["extraction_successful"]
        result["total_text_length"] = best_result["total_text_length"]
        result["pages_with_text"] = best_result["pages_with_text"]
        result["sample_text"] = best_result["sample_text"]
        result["empty_pages"] = best_result["empty_pages"]
        result["extraction_method"] = f"{best_method} (best of multiple methods)"
        
        self.log(f"✅ Text extraction - Best method: {best_method}, Length: {result['total_text_length']} chars, Pages with text: {result['pages_with_text']}")
        
        if result["empty_pages"]:
            self.log(f"⚠️  Empty pages found: {result['empty_pages']}", "WARNING")
                    
        return result
    
    def _extract_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text using PyMuPDF"""
        result = {
            "extraction_successful": False,
            "total_text_length": 0,
            "pages_with_text": 0,
            "sample_text": "",
            "empty_pages": [],
            "error": None
        }
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            all_text = ""
            
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        all_text += page_text + "\n"
                        result["pages_with_text"] += 1
                    else:
                        result["empty_pages"].append(page_num + 1)
                        
                except Exception as e:
                    self.log(f"⚠️  PyMuPDF: Error extracting text from page {page_num + 1}: {e}", "WARNING")
                    result["empty_pages"].append(page_num + 1)
            
            doc.close()
            
            result["extraction_successful"] = len(all_text.strip()) > 0
            result["total_text_length"] = len(all_text)
            result["sample_text"] = all_text[:500] + "..." if len(all_text) > 500 else all_text
            
        except ImportError:
            result["error"] = "PyMuPDF not available"
        except Exception as e:
            result["error"] = f"PyMuPDF extraction error: {str(e)}"
            
        return result
    
    def _extract_with_pypdf2(self, file_path: str) -> Dict[str, Any]:
        """Extract text using PyPDF2"""
        result = {
            "extraction_successful": False,
            "total_text_length": 0,
            "pages_with_text": 0,
            "sample_text": "",
            "empty_pages": [],
            "error": None
        }
        
        if not PYPDF2_AVAILABLE:
            result["error"] = "PyPDF2 not available"
            return result
            
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                all_text = ""
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        
                        if page_text.strip():
                            all_text += page_text + "\n"
                            result["pages_with_text"] += 1
                        else:
                            result["empty_pages"].append(page_num + 1)
                            
                    except Exception as e:
                        self.log(f"⚠️  PyPDF2: Error extracting text from page {page_num + 1}: {e}", "WARNING")
                        result["empty_pages"].append(page_num + 1)
                
                result["extraction_successful"] = len(all_text.strip()) > 0
                result["total_text_length"] = len(all_text)
                result["sample_text"] = all_text[:500] + "..." if len(all_text) > 500 else all_text
                    
        except Exception as e:
            result["error"] = f"PyPDF2 extraction error: {str(e)}"
            
        return result
    
    def verify_text_chunking(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> Dict[str, Any]:
        """Test text chunking process"""
        self.log(f"✂️  Testing text chunking - Size: {chunk_size}, Overlap: {overlap}")
        
        result = {
            "chunking_successful": False,
            "num_chunks": 0,
            "average_chunk_size": 0,
            "chunks_sample": [],
            "error": None
        }
        
        try:
            if not text or len(text.strip()) == 0:
                result["error"] = "No text provided for chunking"
                return result
            
            # Simple chunking algorithm (similar to what might be used)
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + chunk_size
                
                # Find a good break point (sentence end)
                if end < len(text):
                    # Look for sentence endings near the chunk boundary
                    for i in range(min(100, len(text) - end)):
                        if text[end + i] in '.!?':
                            end = end + i + 1
                            break
                
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                start = end - overlap if end > overlap else end
            
            result["chunking_successful"] = len(chunks) > 0
            result["num_chunks"] = len(chunks)
            result["average_chunk_size"] = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
            result["chunks_sample"] = chunks[:3]  # First 3 chunks as sample
            
            self.log(f"✅ Text chunking - {result['num_chunks']} chunks, Avg size: {result['average_chunk_size']:.0f}")
            
        except Exception as e:
            error_msg = f"Text chunking error: {str(e)}"
            result["error"] = error_msg
            self.log(error_msg, "ERROR")
            
        return result
    
    def verify_embeddings_generation(self, text_chunks: List[str]) -> Dict[str, Any]:
        """Test embedding generation"""
        self.log(f"🧮 Testing embeddings generation for {len(text_chunks)} chunks")
        
        result = {
            "embeddings_successful": False,
            "num_embeddings": 0,
            "embedding_dimensions": 0,
            "sample_embedding": None,
            "error": None
        }
        
        if not self.embedder:
            result["error"] = "Sentence transformer not available"
            return result
            
        try:
            if not text_chunks:
                result["error"] = "No text chunks provided"
                return result
            
            # Generate embeddings for sample chunks (limit to avoid memory issues)
            sample_chunks = text_chunks[:5]  # Test with first 5 chunks
            
            embeddings = self.embedder.encode(sample_chunks)
            
            result["embeddings_successful"] = True
            result["num_embeddings"] = len(embeddings)
            result["embedding_dimensions"] = embeddings.shape[1] if len(embeddings) > 0 else 0
            result["sample_embedding"] = embeddings[0][:10].tolist() if len(embeddings) > 0 else None
            
            self.log(f"✅ Embeddings generated - Count: {result['num_embeddings']}, Dimensions: {result['embedding_dimensions']}")
            
        except Exception as e:
            error_msg = f"Embeddings generation error: {str(e)}"
            result["error"] = error_msg
            self.log(error_msg, "ERROR")
            
        return result
    
    def verify_vector_store_indexing(self, embeddings, metadata: List[str]) -> Dict[str, Any]:
        """Test vector store indexing"""
        self.log(f"🗂️  Testing vector store indexing")
        
        result = {
            "indexing_successful": False,
            "index_size": 0,
            "search_test_successful": False,
            "error": None
        }
        
        if not VECTOR_STORE_AVAILABLE:
            result["error"] = "FAISS not available"
            return result
            
        try:
            import numpy as np
            
            if embeddings is None or len(embeddings) == 0:
                result["error"] = "No embeddings provided"
                return result
            
            # Convert to numpy array if needed
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings)
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            
            # Add embeddings to index
            index.add(embeddings.astype('float32'))
            
            result["indexing_successful"] = True
            result["index_size"] = index.ntotal
            
            # Test search
            if len(embeddings) > 0:
                # Search with the first embedding
                query_vector = embeddings[0:1].astype('float32')
                distances, indices = index.search(query_vector, min(3, len(embeddings)))
                
                result["search_test_successful"] = len(indices[0]) > 0
                
            self.log(f"✅ Vector store indexing - Index size: {result['index_size']}, Search test: {'✅' if result['search_test_successful'] else '❌'}")
            
        except Exception as e:
            error_msg = f"Vector store indexing error: {str(e)}"
            result["error"] = error_msg
            self.log(error_msg, "ERROR")
            
        return result
    
    def run_complete_verification(self, file_path: str) -> Dict[str, Any]:
        """Run complete verification pipeline for a file"""
        self.log(f"🚀 Starting complete verification for: {file_path}")
        
        complete_result = {
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "overall_success": False,
            "stages": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Stage 1: File existence
            file_check = self.verify_file_existence(file_path)
            complete_result["stages"]["file_existence"] = file_check
            
            if not file_check["exists"]:
                complete_result["errors"].append("File does not exist")
                return complete_result
            
            # Stage 2: PDF structure
            if file_check["extension"] == ".pdf":
                pdf_check = self.verify_pdf_structure(file_path)
                complete_result["stages"]["pdf_structure"] = pdf_check
                
                if pdf_check["warnings"]:
                    complete_result["warnings"].extend(pdf_check["warnings"])
                
                if not pdf_check["is_valid_pdf"]:
                    complete_result["errors"].append("Invalid PDF structure")
                    return complete_result
                
                # Stage 3: Text extraction
                text_check = self.verify_text_extraction(file_path)
                complete_result["stages"]["text_extraction"] = text_check
                
                if not text_check["extraction_successful"]:
                    complete_result["errors"].append("Text extraction failed")
                    return complete_result
                
                # Stage 4: Text chunking
                if text_check["sample_text"]:
                    chunk_check = self.verify_text_chunking(text_check["sample_text"])
                    complete_result["stages"]["text_chunking"] = chunk_check
                    
                    if not chunk_check["chunking_successful"]:
                        complete_result["errors"].append("Text chunking failed")
                        return complete_result
                    
                    # Stage 5: Embeddings generation
                    if chunk_check["chunks_sample"]:
                        embed_check = self.verify_embeddings_generation(chunk_check["chunks_sample"])
                        complete_result["stages"]["embeddings"] = embed_check
                        
                        if not embed_check["embeddings_successful"]:
                            complete_result["errors"].append("Embeddings generation failed")
                            return complete_result
                        
                        # Stage 6: Vector store indexing
                        if embed_check["sample_embedding"]:
                            # Create sample embeddings array for testing
                            sample_embeddings = [embed_check["sample_embedding"] + [0] * (384 - len(embed_check["sample_embedding"]))]  # Pad to 384 dimensions
                            index_check = self.verify_vector_store_indexing(sample_embeddings, ["test_metadata"])
                            complete_result["stages"]["vector_indexing"] = index_check
                            
                            if not index_check["indexing_successful"]:
                                complete_result["errors"].append("Vector store indexing failed")
                                return complete_result
            
            # If we get here, all stages passed
            complete_result["overall_success"] = len(complete_result["errors"]) == 0
            
            status = "✅ SUCCESS" if complete_result["overall_success"] else "❌ FAILED"
            self.log(f"🏁 Complete verification {status} for: {file_path}")
            
        except Exception as e:
            error_msg = f"Complete verification error: {str(e)}"
            complete_result["errors"].append(error_msg)
            self.log(error_msg, "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
        
        return complete_result
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed report of verification results"""
        report = []
        report.append("=" * 80)
        report.append("FILE VERIFICATION REPORT")
        report.append("=" * 80)
        report.append(f"File: {results['file_path']}")
        report.append(f"Timestamp: {results['timestamp']}")
        report.append(f"Overall Result: {'✅ SUCCESS' if results['overall_success'] else '❌ FAILED'}")
        report.append("")
        
        if results.get("errors"):
            report.append("🚨 ERRORS:")
            for error in results["errors"]:
                report.append(f"  • {error}")
            report.append("")
        
        if results.get("warnings"):
            report.append("⚠️  WARNINGS:")
            for warning in results["warnings"]:
                report.append(f"  • {warning}")
            report.append("")
        
        report.append("📊 STAGE RESULTS:")
        for stage_name, stage_result in results.get("stages", {}).items():
            report.append(f"\n{stage_name.upper().replace('_', ' ')}:")
            for key, value in stage_result.items():
                if key == "error" and value:
                    report.append(f"  ❌ Error: {value}")
                elif key == "sample_text" and value:
                    report.append(f"  📝 Sample Text: {value[:100]}...")
                elif key == "chunks_sample" and value:
                    report.append(f"  ✂️  Sample Chunks: {len(value)} chunks")
                elif key == "sample_embedding" and value:
                    report.append(f"  🧮 Sample Embedding: [{', '.join(map(str, value[:5]))}...]")
                else:
                    report.append(f"  • {key}: {value}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)
    
    def verify_directory(self, directory_path: str, file_pattern: str = "*.pdf") -> Dict[str, Any]:
        """Verify all files matching pattern in directory"""
        self.log(f"📁 Verifying directory: {directory_path}")
        
        from glob import glob
        
        pattern_path = os.path.join(directory_path, file_pattern)
        files = glob(pattern_path)
        
        directory_result = {
            "directory": directory_path,
            "pattern": file_pattern,
            "files_found": len(files),
            "files": [],
            "summary": {
                "successful": 0,
                "failed": 0,
                "total_errors": 0,
                "total_warnings": 0
            }
        }
        
        for file_path in files:
            self.log(f"\n{'='*60}")
            result = self.run_complete_verification(file_path)
            directory_result["files"].append(result)
            
            if result["overall_success"]:
                directory_result["summary"]["successful"] += 1
            else:
                directory_result["summary"]["failed"] += 1
            
            directory_result["summary"]["total_errors"] += len(result.get("errors", []))
            directory_result["summary"]["total_warnings"] += len(result.get("warnings", []))
        
        self.log(f"\n📊 Directory verification complete:")
        self.log(f"  Files found: {directory_result['files_found']}")
        self.log(f"  Successful: {directory_result['summary']['successful']}")
        self.log(f"  Failed: {directory_result['summary']['failed']}")
        
        return directory_result

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="File Verification Tool for Food Service 2025")
    parser.add_argument("path", help="File or directory path to verify")
    parser.add_argument("--pattern", default="*.pdf", help="File pattern for directory verification")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    verifier = FileVerificationTool(verbose=args.verbose)
    
    if os.path.isfile(args.path):
        # Single file verification
        result = verifier.run_complete_verification(args.path)
        report = verifier.generate_report(result)
    elif os.path.isdir(args.path):
        # Directory verification
        result = verifier.verify_directory(args.path, args.pattern)
        report = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        print(f"❌ Path not found: {args.path}")
        return 1
    
    # Output report
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 Report saved to: {args.output}")
    else:
        print(report)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())