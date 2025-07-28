"""
PDF Reading Comparison Tool
Tests multiple PDF extraction libraries to compare results
"""

import os
import sys
from pathlib import Path

def test_pypdf2(file_path):
    """Test with PyPDF2"""
    try:
        import PyPDF2
        from PyPDF2 import PdfReader
        
        print("🔍 Testing with PyPDF2...")
        
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            text = ""
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"  Page {page_num + 1}: {len(page_text)} characters")
        
        print(f"📄 PyPDF2 Total: {len(text)} characters")
        print(f"📝 Sample text: {text[:200]}...")
        return text
        
    except Exception as e:
        print(f"❌ PyPDF2 Error: {e}")
        return ""

def test_pdfplumber(file_path):
    """Test with pdfplumber"""
    try:
        import pdfplumber
        
        print("\n🔍 Testing with pdfplumber...")
        
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                print(f"  Page {page_num + 1}: {len(page_text)} characters")
        
        print(f"📄 pdfplumber Total: {len(text)} characters")
        print(f"📝 Sample text: {text[:200]}...")
        return text
        
    except Exception as e:
        print(f"❌ pdfplumber Error: {e}")
        return ""

def test_pymupdf(file_path):
    """Test with PyMuPDF (fitz)"""
    try:
        import fitz  # PyMuPDF
        
        print("\n🔍 Testing with PyMuPDF...")
        
        text = ""
        doc = fitz.open(file_path)
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text()
            text += page_text + "\n"
            print(f"  Page {page_num + 1}: {len(page_text)} characters")
        
        doc.close()
        
        print(f"📄 PyMuPDF Total: {len(text)} characters")
        print(f"📝 Sample text: {text[:200]}...")
        return text
        
    except Exception as e:
        print(f"❌ PyMuPDF Error: {e}")
        return ""

def compare_pdf_extraction(file_path):
    """Compare all PDF extraction methods"""
    print(f"🚀 Comparing PDF extraction methods for: {file_path}")
    print("=" * 80)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    file_size = os.path.getsize(file_path)
    print(f"📁 File size: {file_size:,} bytes")
    
    results = {}
    
    # Test PyPDF2
    results['pypdf2'] = test_pypdf2(file_path)
    
    # Test pdfplumber
    results['pdfplumber'] = test_pdfplumber(file_path)
    
    # Test PyMuPDF
    results['pymupdf'] = test_pymupdf(file_path)
    
    print("\n" + "=" * 80)
    print("📊 COMPARISON SUMMARY")
    print("=" * 80)
    
    for method, text in results.items():
        length = len(text)
        print(f"{method:12}: {length:6,} characters")
    
    # Find the best result (most text extracted)
    best_method = max(results.items(), key=lambda x: len(x[1]))
    print(f"\n🏆 Best method: {best_method[0]} ({len(best_method[1]):,} characters)")
    
    # Show differences
    print("\n🔍 TEXT CONTENT COMPARISON:")
    for method, text in results.items():
        if len(text) > 0:
            print(f"\n{method.upper()} - First 300 characters:")
            print("-" * 50)
            print(text[:300])
            print("-" * 50)
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_comparison_test.py <pdf_file_path>")
        return
    
    file_path = sys.argv[1]
    compare_pdf_extraction(file_path)

if __name__ == "__main__":
    main()