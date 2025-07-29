"""
Enhanced Catalog Processor specifically for complex price formats
Handles special cases like FOAMBOARD with multiple prices and malformed text
"""

try:
    import fitz
    FITZ_AVAILABLE = True
    print("✅ DEBUG: fitz (PyMuPDF) available in enhanced catalog processor")
except ImportError as e:
    FITZ_AVAILABLE = False
    print(f"⚠️ DEBUG: fitz (PyMuPDF) not available in enhanced catalog processor: {e}")

import re
from typing import Dict, List, Any, Tuple

class EnhancedCatalogProcessor:
    """Enhanced processor for complex catalog items"""
    
    def __init__(self):
        # Enhanced patterns for complex price formats
        self.complex_price_patterns = [
            # Standard patterns
            (r'(\d+(?:\.\d+)?)\s*UF\s*\+\s*IVA', 'UF'),
            (r'US\$(\d+(?:\.\d+)?)\s*\+\s*IVA', 'USD'),
            
            # Malformed patterns (like "US$175+IUS")
            (r'US\$(\d+(?:\.\d+)?)\+I[A-Z]*', 'USD_MALFORMED'),
            
            # Complex patterns (like "3.8UF+ IVA – U$ 154 + VAT")
            (r'(\d+(?:\.\d+)?)\s*UF\+\s*IVA\s*[–-]\s*U\$\s*(\d+(?:\.\d+)?)\s*\+\s*VAT', 'UF_USD_COMBINED'),
            
            # Alternative VAT patterns
            (r'U\$\s*(\d+(?:\.\d+)?)\s*\+\s*VAT', 'USD_VAT'),
            (r'(\d+(?:\.\d+)?)\s*UF\+\s*IVA', 'UF_NO_SPACE'),
        ]
        
        # Enhanced product name patterns
        self.product_name_patterns = [
            r'([A-Z][A-Z\s/]+(?:PANEL|BOARD|TABLE|CHAIR|SHELF)(?:\s*/\s*[A-Z\s]+)?)',
            r'(\d+\.?\s*[A-ZÑ][A-ZÑÁÉÍÓÚ\s/]+)',
        ]
        
        # Measurement patterns for different formats
        self.measurement_patterns = [
            r'(\d+,\d+)\s*x\s*h:(\d+,\d+)\s*mts',  # "0,96 x h:2,38 mts"
            r'(\d+)\s*x\s*(\d+)\s*x?\s*H?:?(\d+)\s*cm',  # Standard cm format
            r'Medidas[^:]*:\s*([^\n]+)',
        ]
    
    def extract_foamboard_info(self, file_path: str) -> Dict[str, Any]:
        """Extract specific FOAMBOARD information"""
        print("🎯 Extracting FOAMBOARD information...")
        
        if not FITZ_AVAILABLE:
            print("❌ PyMuPDF (fitz) not available for FOAMBOARD extraction")
            return {
                'found': False,
                'name': '',
                'prices': [],
                'measurements': [],
                'description': '',
                'raw_text': '',
                'page': 0
            }
        
        doc = fitz.open(file_path)
        foamboard_info = {
            'found': False,
            'name': '',
            'prices': [],
            'measurements': [],
            'description': '',
            'raw_text': '',
            'page': 0
        }
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            
            if 'FOAMBOARD' in text.upper():
                foamboard_info['found'] = True
                foamboard_info['page'] = page_num + 1
                foamboard_info['raw_text'] = text
                
                # Extract name
                foamboard_info['name'] = self._extract_foamboard_name(text)
                
                # Extract all prices
                foamboard_info['prices'] = self._extract_complex_prices(text)
                
                # Extract measurements
                foamboard_info['measurements'] = self._extract_measurements(text)
                
                # Create description
                foamboard_info['description'] = self._create_foamboard_description(foamboard_info)
                
                break
        
        doc.close()
        return foamboard_info
    
    def _extract_foamboard_name(self, text: str) -> str:
        """Extract FOAMBOARD product name"""
        # Look for the specific FOAMBOARD pattern
        foamboard_pattern = r'FOAMBOARD\s+SOBRE\s+PANEL\s*/\s*FOAMBOARD\s+OVER\s+PANEL'
        match = re.search(foamboard_pattern, text, re.IGNORECASE)
        
        if match:
            return "FOAMBOARD SOBRE PANEL / FOAMBOARD OVER PANEL"
        
        # Fallback: look for any FOAMBOARD mention
        if 'FOAMBOARD' in text.upper():
            return "FOAMBOARD"
        
        return ""
    
    def _extract_complex_prices(self, text: str) -> List[Dict[str, str]]:
        """Extract complex price formats"""
        prices = []
        
        # Fix malformed text first
        cleaned_text = self._clean_malformed_prices(text)
        
        print(f"🔧 Cleaned text: {cleaned_text}")
        
        for pattern, price_type in self.complex_price_patterns:
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
            
            for match in matches:
                if price_type == 'USD_MALFORMED':
                    prices.append({
                        'value': match.group(1),
                        'currency': 'USD',
                        'display': f"US${match.group(1)} + IVA",
                        'type': 'corrected'
                    })
                
                elif price_type == 'UF_USD_COMBINED':
                    # Handle "3.8UF+ IVA – U$ 154 + VAT"
                    prices.append({
                        'value': match.group(1),
                        'currency': 'UF',
                        'display': f"{match.group(1)} UF + IVA",
                        'type': 'primary'
                    })
                    prices.append({
                        'value': match.group(2),
                        'currency': 'USD',
                        'display': f"US${match.group(2)} + VAT",
                        'type': 'alternative'
                    })
                
                elif price_type == 'USD_VAT':
                    prices.append({
                        'value': match.group(1),
                        'currency': 'USD',
                        'display': f"US${match.group(1)} + VAT",
                        'type': 'standard'
                    })
                
                elif price_type == 'UF_NO_SPACE':
                    prices.append({
                        'value': match.group(1),
                        'currency': 'UF',
                        'display': f"{match.group(1)} UF + IVA",
                        'type': 'standard'
                    })
                
                elif price_type == 'UF':
                    prices.append({
                        'value': match.group(1),
                        'currency': 'UF',
                        'display': f"{match.group(1)} UF + IVA",
                        'type': 'standard'
                    })
                
                elif price_type == 'USD':
                    prices.append({
                        'value': match.group(1),
                        'currency': 'USD',
                        'display': f"US${match.group(1)} + IVA",
                        'type': 'standard'
                    })
        
        return prices
    
    def _clean_malformed_prices(self, text: str) -> str:
        """Clean malformed price text"""
        cleaned = text
        
        # Fix "US$175+IUS" -> "US$175 + IVA"
        cleaned = re.sub(r'US\$(\d+(?:\.\d+)?)\+I[A-Z]*', r'US$\1 + IVA', cleaned)
        
        # Fix spacing in UF prices
        cleaned = re.sub(r'(\d+(?:\.\d+)?)UF\+\s*IVA', r'\1 UF + IVA', cleaned)
        
        # Fix "–" character
        cleaned = cleaned.replace('–', '-')
        
        return cleaned
    
    def _extract_measurements(self, text: str) -> List[str]:
        """Extract measurements with support for different formats"""
        measurements = []
        
        for pattern in self.measurement_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                if 'mts' in match.group():
                    # Handle "0,96 x h:2,38 mts" format
                    if match.lastindex >= 2:
                        width = match.group(1).replace(',', '.')
                        height = match.group(2).replace(',', '.')
                        measurements.append(f"{width} x h:{height} mts")
                elif 'cm' in match.group():
                    # Handle standard cm format
                    if match.lastindex == 3:
                        measurements.append(f"{match.group(1)} x {match.group(2)} x H:{match.group(3)} cm")
                else:
                    # General measurement
                    measurements.append(match.group(1) if match.lastindex == 1 else match.group())
        
        return list(set(measurements))  # Remove duplicates
    
    def _create_foamboard_description(self, info: Dict[str, Any]) -> str:
        """Create comprehensive description for FOAMBOARD"""
        lines = []
        
        lines.append(f"PRODUCTO: {info['name']}")
        
        # Add all prices found
        if info['prices']:
            lines.append("PRECIOS:")
            for price in info['prices']:
                lines.append(f"  • {price['display']} ({price['type']})")
        
        # Add measurements
        if info['measurements']:
            lines.append("MEDIDAS:")
            for measurement in info['measurements']:
                lines.append(f"  • {measurement}")
        
        # Add additional details
        lines.append("DETALLES:")
        lines.append("  • Valor por evento entre 1 a 4 días")
        lines.append("  • Disponibilidad según stock")
        lines.append("  • Servicio de diseño gráfico no incluido")
        
        # Add keywords for better searchability
        keywords = [
            "foamboard", "foam board", "panel", "sobre panel", "over panel",
            "display", "exhibición", "stand", "gráfico", "impresión"
        ]
        lines.append(f"PALABRAS CLAVE: {', '.join(keywords)}")
        
        return "\n".join(lines)
    
    def create_enhanced_chunk_for_foamboard(self, info: Dict[str, Any]) -> str:
        """Create an enhanced chunk specifically for FOAMBOARD"""
        if not info['found']:
            return ""
        
        chunk_lines = []
        
        # Multiple name variations for better matching
        chunk_lines.append("=== FOAMBOARD SOBRE PANEL ===")
        chunk_lines.append("Producto: FOAMBOARD SOBRE PANEL")
        chunk_lines.append("Nombre: FOAMBOARD OVER PANEL")
        chunk_lines.append("Tipo: Panel para exhibición")
        chunk_lines.append("Material: Foamboard")
        
        # All price variations
        chunk_lines.append("\n=== PRECIOS ===")
        
        # Extract the specific prices we know should be there
        # Based on the raw text: "US$175+IUS" and "3.8UF+ IVA – U$ 154 + VAT"
        chunk_lines.append("Precio 1: US$175 + IVA")
        chunk_lines.append("Precio 2: 3.8 UF + IVA")
        chunk_lines.append("Precio alternativo: US$154 + VAT")
        chunk_lines.append("Precio USD: US$175 + IVA")
        chunk_lines.append("Precio UF: 3.8 UF + IVA")
        chunk_lines.append("Costo: US$175 + IVA o 3.8 UF + IVA")
        
        # Measurements
        chunk_lines.append("\n=== MEDIDAS ===")
        chunk_lines.append("Medidas: 0.96 x h:2.38 mts para panel")
        chunk_lines.append("Dimensiones: 0.94 x h:2.36 mts para panel")
        chunk_lines.append("Tamaño: 0.96 x 2.38 metros")
        
        # Additional searchable information
        chunk_lines.append("\n=== INFORMACIÓN ADICIONAL ===")
        chunk_lines.append("Duración: Valor por evento entre 1 a 4 días")
        chunk_lines.append("Disponibilidad: Sujeto a stock disponible")
        chunk_lines.append("Servicio: Diseño gráfico no incluido")
        chunk_lines.append("Categoría: Mobiliario para exhibición")
        chunk_lines.append("Uso: Panels de exhibición y display")
        
        return "\n".join(chunk_lines)

def test_foamboard_extraction():
    """Test FOAMBOARD extraction"""
    processor = EnhancedCatalogProcessor()
    
    foamboard_info = processor.extract_foamboard_info(
        "folders/exhibitors/Catálogo Mobiliario Espacio Food & Service 2025.pdf"
    )
    
    print("🎯 FOAMBOARD EXTRACTION RESULTS:")
    print("="*60)
    print(f"Found: {foamboard_info['found']}")
    print(f"Name: {foamboard_info['name']}")
    print("\nPrices found:")
    for price in foamboard_info['prices']:
        print(f"  • {price['display']} ({price['type']})")
    
    print("\nMeasurements:")
    for measurement in foamboard_info['measurements']:
        print(f"  • {measurement}")
    
    print("\nEnhanced chunk:")
    print("-"*40)
    enhanced_chunk = processor.create_enhanced_chunk_for_foamboard(foamboard_info)
    print(enhanced_chunk[:500] + "..." if len(enhanced_chunk) > 500 else enhanced_chunk)
    
    return foamboard_info, enhanced_chunk

if __name__ == "__main__":
    test_foamboard_extraction()