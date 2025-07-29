"""
Advanced Catalog Analysis for PyMuPDF extraction optimization
Analyzes the specific structure of the furniture catalog PDF
"""

import fitz  # PyMuPDF
import re
import json
from typing import Dict, List, Any

def analyze_catalog_structure(file_path: str):
    """Analyze the structure and content of the catalog PDF"""
    print(f"🔍 ANALYZING CATALOG: {file_path}")
    print("="*80)
    
    doc = fitz.open(file_path)
    analysis = {
        'pages': [],
        'text_extraction_methods': {},
        'structured_content': {},
        'issues_found': []
    }
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        
        print(f"\n📄 PAGE {page_num + 1}:")
        print("-" * 40)
        
        page_analysis = {
            'page_number': page_num + 1,
            'methods': {}
        }
        
        # Method 1: Standard text extraction
        standard_text = page.get_text()
        page_analysis['methods']['standard'] = {
            'length': len(standard_text),
            'text': standard_text
        }
        print(f"Standard extraction: {len(standard_text)} chars")
        
        # Method 2: Text with layout preservation
        layout_text = page.get_text("text")
        page_analysis['methods']['layout'] = {
            'length': len(layout_text),
            'text': layout_text
        }
        print(f"Layout preservation: {len(layout_text)} chars")
        
        # Method 3: Dictionary/structured approach
        try:
            text_dict = page.get_text("dict")
            dict_text = extract_text_from_dict(text_dict)
            page_analysis['methods']['dict'] = {
                'length': len(dict_text),
                'text': dict_text,
                'structure': analyze_text_blocks(text_dict)
            }
            print(f"Dictionary method: {len(dict_text)} chars")
        except Exception as e:
            page_analysis['methods']['dict'] = {'error': str(e)}
            print(f"Dictionary method failed: {e}")
        
        # Method 4: Block-based extraction
        try:
            blocks = page.get_text("blocks")
            block_text = extract_text_from_blocks(blocks)
            page_analysis['methods']['blocks'] = {
                'length': len(block_text),
                'text': block_text,
                'block_count': len(blocks)
            }
            print(f"Block method: {len(block_text)} chars, {len(blocks)} blocks")
        except Exception as e:
            page_analysis['methods']['blocks'] = {'error': str(e)}
            print(f"Block method failed: {e}")
        
        # Find the best method for this page
        best_method = find_best_method(page_analysis['methods'])
        page_analysis['best_method'] = best_method
        print(f"🏆 Best method: {best_method}")
        
        # Analyze content structure
        best_text = page_analysis['methods'][best_method].get('text', '')
        if best_text:
            content_analysis = analyze_content_structure(best_text)
            page_analysis['content_analysis'] = content_analysis
            print(f"Found: {len(content_analysis.get('products', []))} products, {len(content_analysis.get('prices', []))} prices")
        
        analysis['pages'].append(page_analysis)
    
    doc.close()
    
    # Generate summary
    print(f"\n📊 SUMMARY:")
    print("="*50)
    
    total_chars_standard = sum(p['methods'].get('standard', {}).get('length', 0) for p in analysis['pages'])
    total_chars_best = sum(p['methods'].get(p.get('best_method', 'standard'), {}).get('length', 0) for p in analysis['pages'])
    
    print(f"Total characters (standard): {total_chars_standard}")
    print(f"Total characters (optimized): {total_chars_best}")
    print(f"Improvement: {((total_chars_best - total_chars_standard) / total_chars_standard * 100):.1f}%")
    
    return analysis

def extract_text_from_dict(text_dict: Dict) -> str:
    """Extract text from PyMuPDF dictionary structure"""
    text_parts = []
    
    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                line_text = ""
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                if line_text.strip():
                    text_parts.append(line_text.strip())
    
    return "\n".join(text_parts)

def extract_text_from_blocks(blocks: List) -> str:
    """Extract text from PyMuPDF blocks"""
    text_parts = []
    
    for block in blocks:
        if len(block) >= 5:  # Text block
            text = block[4].strip()
            if text:
                text_parts.append(text)
    
    return "\n".join(text_parts)

def analyze_text_blocks(text_dict: Dict) -> Dict:
    """Analyze the structure of text blocks"""
    structure = {
        'blocks': len(text_dict.get("blocks", [])),
        'fonts_used': set(),
        'font_sizes': set()
    }
    
    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line.get("spans", []):
                    if "font" in span:
                        structure['fonts_used'].add(span["font"])
                    if "size" in span:
                        structure['font_sizes'].add(round(span["size"], 1))
    
    structure['fonts_used'] = list(structure['fonts_used'])
    structure['font_sizes'] = sorted(list(structure['font_sizes']))
    
    return structure

def find_best_method(methods: Dict) -> str:
    """Find the method that extracted the most text"""
    best_method = 'standard'
    best_length = 0
    
    for method, data in methods.items():
        if isinstance(data, dict) and 'length' in data:
            if data['length'] > best_length:
                best_length = data['length']
                best_method = method
    
    return best_method

def analyze_content_structure(text: str) -> Dict:
    """Analyze the content structure to find products and prices"""
    analysis = {
        'products': [],
        'prices': [],
        'measurements': [],
        'colors': []
    }
    
    # Find product names/types
    product_patterns = [
        r'(\w+(?:\s+\w+)*)\s*(?:/\s*[A-Z\s]+)?(?:\s+\d+)?',
        r'(\d+\.?\s*[A-ZÑ\s]+(?:/[A-Z\s]+)?)',
    ]
    
    # Find prices
    price_patterns = [
        r'(\d+(?:\.\d+)?)\s*UF\s*\+?\s*IVA',
        r'US\$(\d+(?:\.\d+)?)\s*\+?\s*IVA',
        r'(\d+(?:\.\d+)?)\s*\+\s*IVA'
    ]
    
    # Find measurements
    measurement_patterns = [
        r'(\d+)\s*x\s*(\d+)\s*x?\s*H?:?(\d+)\s*cm',
        r'Medidas[^:]*:\s*([^\n]+)',
    ]
    
    # Find colors
    color_patterns = [
        r'Color\s+Disponible[^:]*:\s*([^\n]+)',
        r'(Blanco|Negro|Aluminio|White|Black|Aluminum)'
    ]
    
    # Extract products
    for pattern in product_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        analysis['products'].extend(matches)
    
    # Extract prices
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        analysis['prices'].extend(matches)
    
    # Extract measurements
    for pattern in measurement_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        analysis['measurements'].extend(matches)
    
    # Extract colors
    for pattern in color_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        analysis['colors'].extend(matches)
    
    return analysis

def generate_optimized_extraction(file_path: str) -> str:
    """Generate optimized text extraction based on analysis"""
    print(f"\n🔧 GENERATING OPTIMIZED EXTRACTION...")
    
    doc = fitz.open(file_path)
    optimized_text = []
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        
        # Try different methods and use the best one
        methods = {}
        
        # Standard
        methods['standard'] = page.get_text()
        
        # Blocks
        try:
            blocks = page.get_text("blocks")
            methods['blocks'] = extract_text_from_blocks(blocks)
        except:
            methods['blocks'] = ""
        
        # Dictionary
        try:
            text_dict = page.get_text("dict")
            methods['dict'] = extract_text_from_dict(text_dict)
        except:
            methods['dict'] = ""
        
        # Choose best method
        best_text = max(methods.values(), key=len)
        
        if best_text.strip():
            optimized_text.append(f"--- Página {page_num + 1} ---")
            optimized_text.append(best_text)
    
    doc.close()
    
    final_text = "\n".join(optimized_text)
    print(f"✅ Optimized extraction: {len(final_text)} characters")
    
    return final_text

if __name__ == "__main__":
    catalog_path = "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    
    # Analyze structure
    analysis = analyze_catalog_structure(catalog_path)
    
    # Generate optimized extraction
    optimized_text = generate_optimized_extraction(catalog_path)
    
    print(f"\n📄 OPTIMIZED CATALOG TEXT:")
    print("="*80)
    print(optimized_text[:1000] + "..." if len(optimized_text) > 1000 else optimized_text)
    
    # Save analysis to file
    with open("catalog_analysis.json", "w", encoding="utf-8") as f:
        # Convert sets to lists for JSON serialization
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, set):
                return list(obj)
            return obj
        
        json.dump(clean_for_json(analysis), f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Analysis saved to catalog_analysis.json")