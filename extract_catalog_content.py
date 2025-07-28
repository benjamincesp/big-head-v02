"""
Extract and analyze complete content from furniture catalog
"""

import fitz  # PyMuPDF
import re

def extract_full_catalog_text(file_path):
    """Extract complete text from catalog PDF"""
    print(f"📄 Extracting complete text from: {file_path}")
    
    doc = fitz.open(file_path)
    all_text = ""
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_text = page.get_text()
        
        if page_text.strip():
            print(f"\n{'='*60}")
            print(f"PÁGINA {page_num + 1}")
            print(f"{'='*60}")
            print(page_text)
            all_text += f"\n--- PÁGINA {page_num + 1} ---\n{page_text}\n"
    
    doc.close()
    return all_text

def find_prices_and_products(text):
    """Find all prices and product information"""
    print(f"\n🔍 ANÁLISIS DE PRECIOS Y PRODUCTOS")
    print("="*80)
    
    # Pattern for prices in UF
    uf_pattern = r'(\d+(?:\.\d+)?)\s*UF\s*\+?\s*IVA'
    uf_matches = re.findall(uf_pattern, text, re.IGNORECASE)
    
    if uf_matches:
        print("💰 PRECIOS EN UF ENCONTRADOS:")
        for price in uf_matches:
            print(f"  • {price} UF + IVA")
    
    # Pattern for USD prices
    usd_pattern = r'US\$(\d+(?:\.\d+)?)\s*\+?\s*IVA'
    usd_matches = re.findall(usd_pattern, text, re.IGNORECASE)
    
    if usd_matches:
        print("💵 PRECIOS EN USD ENCONTRADOS:")
        for price in usd_matches:
            print(f"  • US${price} + IVA")
    
    # Look for specific furniture types
    furniture_keywords = [
        'repisas', 'shelves', 'mesa', 'table', 'silla', 'chair', 
        'gabetero', 'lockable', 'vitrina', 'showcase', 'mueble',
        'furniture', 'papelero', 'wastebasket'
    ]
    
    print("\n🪑 TIPOS DE MOBILIARIO MENCIONADOS:")
    for keyword in furniture_keywords:
        if re.search(keyword, text, re.IGNORECASE):
            print(f"  ✅ {keyword.upper()}")
    
    # Extract dimensions
    dimension_pattern = r'(\d+)\s*x\s*(\d+)\s*x?\s*H?:?(\d+)\s*cm'
    dimension_matches = re.findall(dimension_pattern, text)
    
    if dimension_matches:
        print("\n📏 DIMENSIONES ENCONTRADAS:")
        for dim in dimension_matches:
            print(f"  • {dim[0]} x {dim[1]} x H:{dim[2]} cm")
    
    # Look for colors
    color_pattern = r'Color.*?(?:Disponible|Available).*?(?:Colour)?\s*([A-Za-z\s]+)'
    color_matches = re.findall(color_pattern, text, re.IGNORECASE)
    
    if color_matches:
        print("\n🎨 COLORES DISPONIBLES:")
        for color in color_matches:
            clean_color = color.strip()
            if clean_color:
                print(f"  • {clean_color}")

def main():
    catalog_path = "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    
    print("🏢 ANÁLISIS COMPLETO DEL CATÁLOGO DE MOBILIARIO")
    print("="*80)
    
    # Extract complete text
    full_text = extract_full_catalog_text(catalog_path)
    
    # Analyze prices and products
    find_prices_and_products(full_text)
    
    print(f"\n📊 ESTADÍSTICAS GENERALES:")
    print(f"  • Texto total extraído: {len(full_text):,} caracteres")
    print(f"  • Palabras aproximadas: {len(full_text.split()):,}")

if __name__ == "__main__":
    main()