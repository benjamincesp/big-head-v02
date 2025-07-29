"""
Test script specifically for FOAMBOARD extraction and pricing
Tests both enhanced catalog processor and enhanced document processor
"""

import os
import re
from tools.enhanced_catalog_processor import EnhancedCatalogProcessor
from tools.enhanced_document_processor import EnhancedDocumentProcessor

def test_foamboard_extraction():
    """Comprehensive test for FOAMBOARD information extraction"""
    catalog_path = "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    
    if not os.path.exists(catalog_path):
        print(f"❌ Catalog file not found: {catalog_path}")
        return
    
    print("🧪 COMPREHENSIVE FOAMBOARD EXTRACTION TEST")
    print("=" * 80)
    
    # Test 1: Enhanced Catalog Processor (specialized for FOAMBOARD)
    print("\n📋 TEST 1: Enhanced Catalog Processor")
    print("-" * 50)
    
    catalog_processor = EnhancedCatalogProcessor()
    foamboard_info = catalog_processor.extract_foamboard_info(catalog_path)
    
    print(f"✅ FOAMBOARD Found: {foamboard_info['found']}")
    print(f"📄 Page: {foamboard_info['page']}")
    print(f"🏷️ Name: {foamboard_info['name']}")
    
    print(f"\n💰 PRICES EXTRACTED:")
    for i, price in enumerate(foamboard_info['prices'], 1):
        print(f"  {i}. {price['display']} ({price['type']}) - {price['currency']}")
    
    print(f"\n📏 MEASUREMENTS:")
    for measurement in foamboard_info['measurements']:
        print(f"  • {measurement}")
    
    # Test 2: Enhanced Document Processor (general approach)
    print("\n\n📄 TEST 2: Enhanced Document Processor")
    print("-" * 50)
    
    doc_processor = EnhancedDocumentProcessor("folders/exhibitors")
    result = doc_processor.process_document_intelligent(catalog_path)
    
    print(f"✅ Success: {result['success']}")
    print(f"🔧 Method: {result['extraction_method']}")
    print(f"📊 Quality Score: {result['metadata'].get('quality_score', 'N/A')}")
    print(f"📋 Tables Found: {result['metadata'].get('tables_found', 0)}")
    
    # Test 3: Search for FOAMBOARD in extracted text
    print("\n\n🔍 TEST 3: FOAMBOARD Content Analysis")
    print("-" * 50)
    
    text = result['text']
    
    # Look for FOAMBOARD mentions
    foamboard_matches = re.finditer(r'FOAMBOARD.*?(?=\n---|\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    foamboard_sections = [match.group() for match in foamboard_matches]
    
    print(f"🎯 FOAMBOARD sections found: {len(foamboard_sections)}")
    
    for i, section in enumerate(foamboard_sections, 1):
        print(f"\n📝 Section {i}:")
        print("-" * 30)
        print(section[:300] + "..." if len(section) > 300 else section)
        
        # Extract prices from this section
        price_patterns = [
            (r'US\$(\d+(?:\.\d+)?)\s*\+\s*IVA', 'USD + IVA'),
            (r'(\d+(?:\.\d+)?)\s*UF\s*\+\s*IVA', 'UF + IVA'),
            (r'US\$(\d+(?:\.\d+)?)\s*\+\s*VAT', 'USD + VAT'),
            (r'(\d+(?:\.\d+)?)\s*UF', 'UF'),
        ]
        
        section_prices = []
        for pattern, currency in price_patterns:
            matches = re.findall(pattern, section, re.IGNORECASE)
            for match in matches:
                section_prices.append(f"{match} {currency}")
        
        if section_prices:
            print(f"💰 Prices found in section {i}:")
            for price in section_prices:
                print(f"  • {price}")
    
    # Test 4: Specific price search
    print("\n\n💰 TEST 4: Specific Price Pattern Search")
    print("-" * 50)
    
    # Look for the specific prices mentioned by user: "US$175+IUS" and "3.8UF+ IVA – U$ 154 + VAT"
    target_prices = [
        (r'US\$175.*?(?:IUS|IVA)', 'Target price 1: US$175'),
        (r'3\.8\s*UF.*?154.*?VAT', 'Target price 2: 3.8 UF + 154 USD'),
        (r'175.*?175', 'Any mention of 175'),
        (r'3\.8.*?154', 'Any mention of 3.8 and 154'),
    ]
    
    for pattern, description in target_prices:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            print(f"✅ {description}: Found {len(matches)} matches")
            for match in matches[:2]:  # Show first 2 matches
                print(f"   • {match}")
        else:
            print(f"❌ {description}: Not found")
    
    # Test 5: Enhanced chunk creation
    print("\n\n📝 TEST 5: Enhanced Chunk for Vector Search")
    print("-" * 50)
    
    if foamboard_info['found']:
        enhanced_chunk = catalog_processor.create_enhanced_chunk_for_foamboard(foamboard_info)
        print(f"📏 Enhanced chunk length: {len(enhanced_chunk)} characters")
        print(f"📝 Enhanced chunk preview:")
        print("-" * 30)
        print(enhanced_chunk[:400] + "..." if len(enhanced_chunk) > 400 else enhanced_chunk)
    
    return {
        'catalog_processor_result': foamboard_info,
        'document_processor_result': result,
        'foamboard_sections': foamboard_sections
    }

if __name__ == "__main__":
    results = test_foamboard_extraction()
    
    print("\n\n🎯 SUMMARY:")
    print("=" * 50)
    print(f"Enhanced Catalog Processor: {'✅' if results['catalog_processor_result']['found'] else '❌'}")
    print(f"Enhanced Document Processor: {'✅' if results['document_processor_result']['success'] else '❌'}")
    print(f"FOAMBOARD sections found: {len(results['foamboard_sections'])}")