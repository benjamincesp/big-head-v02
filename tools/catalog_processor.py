"""
Specialized Catalog Processor for Furniture Catalog
Optimized processing specifically for the Catálogo Mobiliario PDF
"""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class CatalogItem:
    name: str
    price_uf: str = ""
    price_usd: str = ""
    measurements: str = ""
    colors: List[str] = None
    description: str = ""
    page: int = 0

class CatalogProcessor:
    """Specialized processor for furniture catalog"""
    
    def __init__(self):
        # Enhanced patterns for better recognition
        self.product_patterns = [
            r'(\d+\.?\s*[A-ZÑ][A-ZÑÁÉÍÓÚ\s/]+(?:\s*\d+)?)',  # "1.REPISAS/SHELVES"
            r'([A-ZÑ][A-ZÑÁÉÍÓÚ\s/]+(?:\s*\d+)?)',           # "MESA MODULACIÓN"
        ]
        
        self.price_patterns = [
            (r'(\d+(?:\.\d+)?)\s*UF\s*\+\s*IVA', 'UF'),
            (r'US\$(\d+(?:\.\d+)?)\s*\+\s*IVA', 'USD'),
            (r'(\d+(?:\.\d+)?)\s*\+\s*IVA', 'UF_NO_SYMBOL'),
        ]
        
        self.measurement_patterns = [
            r'(\d+)\s*x\s*(\d+)\s*x?\s*H?:?(\d+)\s*cm',
            r'Medidas[^:]*:\s*([^\n]+)',
        ]
        
        self.color_patterns = [
            r'Color\s+Disponible[^:]*:\s*([^\n]+)',
            r'(Blanco|Negro|Aluminio|White|Black|Aluminum)(?:\s*/\s*(White|Black|Aluminum))?'
        ]
    
    def extract_structured_catalog(self, file_path: str) -> List[CatalogItem]:
        """Extract structured catalog items from PDF"""
        print(f"📋 Extracting structured catalog from: {file_path}")
        
        doc = fitz.open(file_path)
        catalog_items = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            
            if not text.strip():
                continue
                
            print(f"📄 Processing page {page_num + 1}")
            
            # Split text into logical sections
            sections = self._split_into_sections(text)
            
            for section in sections:
                item = self._parse_section(section, page_num + 1)
                if item and item.name:
                    catalog_items.append(item)
        
        doc.close()
        
        print(f"✅ Extracted {len(catalog_items)} catalog items")
        return catalog_items
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into logical product sections"""
        # Split by numbered items or major headings
        sections = []
        
        # Split by patterns like "1.PRODUCT", "02 PRODUCT", etc.
        parts = re.split(r'(?=\d+\.?\s*[A-ZÑ])', text)
        
        for part in parts:
            part = part.strip()
            if len(part) > 20:  # Ignore very short sections
                sections.append(part)
        
        return sections
    
    def _parse_section(self, section: str, page_num: int) -> CatalogItem:
        """Parse a section into a structured catalog item"""
        item = CatalogItem(name="", colors=[], page=page_num)
        
        # Extract product name
        item.name = self._extract_product_name(section)
        
        # Extract prices
        item.price_uf, item.price_usd = self._extract_prices(section)
        
        # Extract measurements
        item.measurements = self._extract_measurements(section)
        
        # Extract colors
        item.colors = self._extract_colors(section)
        
        # Store full description
        item.description = section[:200] + "..." if len(section) > 200 else section
        
        return item
    
    def _extract_product_name(self, text: str) -> str:
        """Extract product name from section"""
        # Try numbered patterns first
        for pattern in self.product_patterns:
            matches = re.findall(pattern, text)
            if matches:
                name = matches[0].strip()
                # Clean up the name
                name = re.sub(r'^\d+\.?\s*', '', name)  # Remove leading numbers
                name = re.sub(r'\s+', ' ', name)        # Normalize spaces
                return name
        
        # Fallback: use first line
        lines = text.split('\n')
        if lines:
            return lines[0].strip()[:50]  # Limit length
        
        return ""
    
    def _extract_prices(self, text: str) -> Tuple[str, str]:
        """Extract UF and USD prices"""
        uf_price = ""
        usd_price = ""
        
        for pattern, currency in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if currency == 'UF' or currency == 'UF_NO_SYMBOL':
                    if not uf_price:  # Take first UF price found
                        uf_price = f"{match} UF + IVA"
                elif currency == 'USD':
                    if not usd_price:  # Take first USD price found
                        usd_price = f"US${match} + IVA"
        
        return uf_price, usd_price
    
    def _extract_measurements(self, text: str) -> str:
        """Extract measurements from text"""
        measurements = []
        
        for pattern in self.measurement_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 3:
                    # Format: "100 x 30 x H:15 cm"
                    measurements.append(f"{match[0]} x {match[1]} x H:{match[2]} cm")
                elif isinstance(match, str):
                    measurements.append(match.strip())
        
        return "; ".join(measurements) if measurements else ""
    
    def _extract_colors(self, text: str) -> List[str]:
        """Extract available colors"""
        colors = []
        
        for pattern in self.color_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    colors.extend([c for c in match if c])
                else:
                    colors.append(match)
        
        # Clean and deduplicate
        colors = list(set([c.strip() for c in colors if c and len(c.strip()) > 2]))
        return colors
    
    def generate_enhanced_chunks(self, catalog_items: List[CatalogItem], chunk_size: int = 800) -> List[Dict[str, Any]]:
        """Generate enhanced chunks from catalog items"""
        chunks = []
        current_chunk = ""
        current_metadata = {"items": [], "source": "Catálogo Mobiliario"}
        
        for item in catalog_items:
            # Create detailed item text
            item_text = self._format_item_for_indexing(item)
            
            # Check if adding this item would exceed chunk size
            if len(current_chunk) + len(item_text) > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk.strip(),
                    "metadata": current_metadata.copy()
                })
                
                # Start new chunk
                current_chunk = item_text
                current_metadata = {"items": [item.name], "source": "Catálogo Mobiliario"}
            else:
                # Add to current chunk
                current_chunk += "\n" + item_text
                current_metadata["items"].append(item.name)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": current_metadata.copy()
            })
        
        print(f"📝 Generated {len(chunks)} enhanced chunks")
        return chunks
    
    def _format_item_for_indexing(self, item: CatalogItem) -> str:
        """Format catalog item for optimal indexing and search"""
        lines = []
        
        # Product name (multiple formats for better matching)
        lines.append(f"PRODUCTO: {item.name}")
        lines.append(f"Nombre: {item.name}")
        
        # Prices (multiple formats)
        if item.price_uf:
            lines.append(f"PRECIO: {item.price_uf}")
            lines.append(f"Precio UF: {item.price_uf}")
            lines.append(f"Costo: {item.price_uf}")
        
        if item.price_usd:
            lines.append(f"PRECIO USD: {item.price_usd}")
            lines.append(f"Precio dólares: {item.price_usd}")
        
        # Measurements
        if item.measurements:
            lines.append(f"MEDIDAS: {item.measurements}")
            lines.append(f"Dimensiones: {item.measurements}")
            lines.append(f"Tamaño: {item.measurements}")
        
        # Colors
        if item.colors:
            colors_str = ", ".join(item.colors)
            lines.append(f"COLORES: {colors_str}")
            lines.append(f"Color disponible: {colors_str}")
        
        # Add searchable keywords
        keywords = self._generate_keywords(item)
        if keywords:
            lines.append(f"Palabras clave: {', '.join(keywords)}")
        
        return "\n".join(lines)
    
    def _generate_keywords(self, item: CatalogItem) -> List[str]:
        """Generate searchable keywords for the item"""
        keywords = []
        
        name_lower = item.name.lower()
        
        # Add Spanish/English equivalents
        keyword_map = {
            'repisas': ['shelves', 'estante', 'repisa'],
            'mesa': ['table', 'escritorio', 'superficie'],
            'silla': ['chair', 'asiento', 'butaca'],
            'gabetero': ['lockable', 'cajon', 'cajón'],
            'vitrina': ['showcase', 'display', 'mostrador'],
            'taburete': ['stool', 'banco'],
            'papelero': ['wastebasket', 'basura', 'residuos']
        }
        
        for spanish, equivalents in keyword_map.items():
            if spanish in name_lower:
                keywords.extend(equivalents)
        
        return keywords

def test_catalog_processor():
    """Test the catalog processor"""
    processor = CatalogProcessor()
    
    # Extract structured data
    catalog_items = processor.extract_structured_catalog(
        "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    )
    
    # Display results
    print(f"\n📊 CATALOG ANALYSIS RESULTS:")
    print("="*60)
    
    for i, item in enumerate(catalog_items[:5]):  # Show first 5
        print(f"\nItem {i+1}: {item.name}")
        if item.price_uf:
            print(f"  Precio UF: {item.price_uf}")
        if item.price_usd:
            print(f"  Precio USD: {item.price_usd}")
        if item.measurements:
            print(f"  Medidas: {item.measurements}")
        if item.colors:
            print(f"  Colores: {', '.join(item.colors)}")
    
    # Generate enhanced chunks
    chunks = processor.generate_enhanced_chunks(catalog_items)
    
    print(f"\n📝 SAMPLE CHUNK:")
    print("-"*40)
    if chunks:
        print(chunks[0]["content"][:300] + "...")
    
    return catalog_items, chunks

if __name__ == "__main__":
    test_catalog_processor()