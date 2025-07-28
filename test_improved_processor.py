"""
Test script for improved document processor with PyMuPDF
"""

import sys
import os

# Add the tools directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

from smart_document_processor import SmartDocumentProcessor

def test_pdf_processing():
    """Test the improved PDF processing"""
    print("🧪 Testing improved PDF processing with PyMuPDF...")
    
    # Test the problematic catalog file
    catalog_path = "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    
    if not os.path.exists(catalog_path):
        print(f"❌ File not found: {catalog_path}")
        return
    
    # Create processor
    processor = SmartDocumentProcessor("folders/exhibitors")
    
    # Extract text from the catalog
    print("\n" + "="*80)
    print("Testing Catálogo Mobiliario processing...")
    print("="*80)
    
    extracted_text = processor.extract_text_from_pdf(catalog_path)
    
    print(f"\n📊 RESULTS:")
    print(f"Text length: {len(extracted_text)}")
    print(f"First 300 characters:")
    print("-" * 50)
    print(extracted_text[:300])
    print("-" * 50)
    
    # Test chunking
    print(f"\n📝 Testing text chunking...")
    chunks = processor.chunk_text(extracted_text)
    print(f"Created {len(chunks)} chunks")
    
    if chunks:
        print(f"First chunk length: {len(chunks[0])}")
        print("First chunk preview:")
        print("-" * 30)
        print(chunks[0][:200] + "...")
        print("-" * 30)

def test_media_kit():
    """Test the Media Kit (image-based PDF)"""
    print("\n🧪 Testing Media Kit (image-based PDF)...")
    
    media_kit_path = "folders/exhibitors/Media Kit  ESpacio Food & Service 2025.pdf"
    
    if not os.path.exists(media_kit_path):
        print(f"❌ File not found: {media_kit_path}")
        return
    
    processor = SmartDocumentProcessor("folders/exhibitors")
    
    print("\n" + "="*80)
    print("Testing Media Kit processing...")
    print("="*80)
    
    extracted_text = processor.extract_text_from_pdf(media_kit_path)
    
    print(f"\n📊 RESULTS:")
    print(f"Text length: {len(extracted_text)}")
    print(f"Content: {extracted_text[:200]}")

def main():
    print("🚀 Testing Improved Document Processor")
    print("="*80)
    
    # Test catalog processing
    test_pdf_processing()
    
    # Test media kit processing  
    test_media_kit()
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()