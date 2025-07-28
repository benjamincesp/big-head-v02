"""
Hybrid Search System for Food Service 2025
Combines semantic vector search with keyword-based fallback search
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    search_method: str
    chunk_index: int

class HybridSearchEngine:
    """
    Hybrid search that combines:
    1. Semantic vector search (primary)
    2. Keyword-based search (fallback)
    3. Fuzzy matching for prices and products
    """
    
    def __init__(self):
        self.catalog_keywords = {
            'furniture_types': [
                'repisas', 'shelves', 'mesa', 'table', 'silla', 'chair', 
                'gabetero', 'lockable', 'vitrina', 'showcase', 'mueble',
                'furniture', 'papelero', 'wastebasket', 'poltrona', 'armchair',
                'taburete', 'stool', 'portafolleto', 'brochure'
            ],
            'price_indicators': [
                'uf', 'usd', 'precio', 'price', 'costo', 'cost', 'valor', 'value',
                'cuánto', 'cuanto', 'how much', '$', 'iva', 'vat'
            ],
            'measurement_patterns': [
                r'\d+\s*x\s*\d+\s*x?\s*h?:?\d+\s*cm',
                r'\d+\s*cm',
                r'medidas?', 'measures?', 'dimensiones?', 'dimensions?'
            ],
            'color_indicators': [
                'color', 'colour', 'blanco', 'white', 'negro', 'black', 
                'aluminio', 'aluminum'
            ]
        }
        
        # Price patterns for exact matching
        self.price_patterns = [
            r'(\d+(?:\.\d+)?)\s*uf\s*\+?\s*iva',  # UF prices
            r'us\$(\d+(?:\.\d+)?)\s*\+?\s*iva',   # USD prices
            r'(\d+(?:\.\d+)?)\s*\+\s*iva'         # General + IVA
        ]
    
    def extract_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query to understand what user is looking for"""
        query_lower = query.lower()
        
        intent = {
            'is_price_query': False,
            'is_product_query': False,
            'furniture_types': [],
            'price_terms': [],
            'has_measurements': False,
            'has_colors': False,
            'keywords': []
        }
        
        # Check for price-related terms
        for price_term in self.catalog_keywords['price_indicators']:
            if price_term in query_lower:
                intent['is_price_query'] = True
                intent['price_terms'].append(price_term)
        
        # Check for furniture types
        for furniture in self.catalog_keywords['furniture_types']:
            if furniture in query_lower:
                intent['is_product_query'] = True
                intent['furniture_types'].append(furniture)
        
        # Check for measurements
        for pattern in self.catalog_keywords['measurement_patterns']:
            if re.search(pattern, query_lower):
                intent['has_measurements'] = True
                break
        
        # Check for colors
        for color in self.catalog_keywords['color_indicators']:
            if color in query_lower:
                intent['has_colors'] = True
                break
        
        # Extract all significant keywords
        # Remove common words and keep important terms
        stop_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te',
            'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'una', 'las', 'los',
            'del', 'al', 'como', 'para', 'si', 'me', 'o', 'pero', 'ya', 'muy',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        words = re.findall(r'\b\w+\b', query_lower)
        intent['keywords'] = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return intent
    
    def keyword_search(self, documents: List[str], metadata: List[Dict], 
                      query: str, intent: Dict[str, Any]) -> List[SearchResult]:
        """Perform keyword-based search with scoring"""
        results = []
        query_lower = query.lower()
        
        print(f"🔍 DEBUG: Hybrid Search - Performing keyword search")
        print(f"🔍 DEBUG: Intent: {intent}")
        
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            score = 0.0
            
            # High priority scoring for catalog content
            if any(term in doc_lower for term in ['catálogo', 'mobiliario', 'furniture', 'catalog']):
                score += 5.0
                
            # Score for furniture type matches
            for furniture_type in intent['furniture_types']:
                if furniture_type in doc_lower:
                    score += 10.0  # High score for furniture matches
                    
            # Score for price-related content if it's a price query
            if intent['is_price_query']:
                # Look for price patterns in document
                for pattern in self.price_patterns:
                    if re.search(pattern, doc_lower):
                        score += 8.0
                        
                # Bonus for UF and IVA terms
                if 'uf' in doc_lower and 'iva' in doc_lower:
                    score += 5.0
            
            # Score for general keyword matches
            for keyword in intent['keywords']:
                # Exact matches
                if keyword in doc_lower:
                    score += 2.0
                    
                # Partial matches (fuzzy)
                if any(keyword in word for word in doc_lower.split()):
                    score += 1.0
            
            # Bonus for documents with measurements
            if intent['has_measurements'] or re.search(r'\d+\s*x\s*\d+', doc_lower):
                score += 2.0
                
            # Bonus for documents with colors
            if intent['has_colors']:
                for color in self.catalog_keywords['color_indicators']:
                    if color in doc_lower:
                        score += 1.0
            
            if score > 0:
                results.append(SearchResult(
                    content=doc,
                    score=score,
                    source=metadata[i].get('source', 'unknown'),
                    search_method='keyword',
                    chunk_index=i
                ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"🔍 DEBUG: Keyword search found {len(results)} results")
        if results:
            print(f"🔍 DEBUG: Top result score: {results[0].score}")
            print(f"🔍 DEBUG: Top result preview: {results[0].content[:100]}...")
        
        return results[:5]  # Return top 5 results
    
    def find_price_information(self, documents: List[str], query: str) -> List[SearchResult]:
        """Specialized search for price information"""
        results = []
        query_lower = query.lower()
        
        print(f"🔍 DEBUG: Searching for price information")
        
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            score = 0.0
            
            # Look for price patterns
            for pattern in self.price_patterns:
                matches = re.findall(pattern, doc_lower)
                if matches:
                    score += len(matches) * 5.0  # 5 points per price found
            
            # Look for specific furniture mentioned in query
            query_words = set(query_lower.split())
            doc_words = set(doc_lower.split())
            
            # Find intersection of words
            common_words = query_words.intersection(doc_words)
            
            # Higher score for documents that mention same furniture types
            furniture_matches = 0
            for furniture in self.catalog_keywords['furniture_types']:
                if furniture in query_lower and furniture in doc_lower:
                    furniture_matches += 1
                    score += 8.0
            
            # Look for exact price mentions from query
            price_numbers = re.findall(r'(\d+(?:\.\d+)?)', query)
            for price in price_numbers:
                if price in doc:
                    score += 10.0  # Exact price match
            
            if score > 0:
                results.append(SearchResult(
                    content=doc,
                    score=score,
                    source=f"chunk_{i}",
                    search_method='price_search',
                    chunk_index=i
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"🔍 DEBUG: Price search found {len(results)} results")
        
        return results[:3]
    
    def enhance_search_results(self, vector_results: List[Any], 
                             documents: List[str], metadata: List[Dict],
                             query: str) -> List[SearchResult]:
        """
        Enhance vector search results with keyword-based fallback
        """
        print(f"🔍 DEBUG: Enhancing search results for query: {query}")
        
        # Analyze query intent
        intent = self.extract_query_intent(query)
        
        # Convert vector results to SearchResult format
        enhanced_results = []
        
        # Add vector search results (if any)
        if vector_results:
            print(f"🔍 DEBUG: Processing {len(vector_results)} vector results")
            for i, (content, score, metadata_item) in enumerate(vector_results):
                enhanced_results.append(SearchResult(
                    content=content,
                    score=score + 0.1,  # Small bonus for vector results
                    source=metadata_item.get('source', 'unknown'),
                    search_method='vector',
                    chunk_index=i
                ))
        
        # If vector search didn't find good results or it's a specific query, add keyword results
        if not enhanced_results or intent['is_price_query'] or intent['is_product_query']:
            print(f"🔍 DEBUG: Adding keyword search results")
            
            # Keyword-based search
            keyword_results = self.keyword_search(documents, metadata, query, intent)
            enhanced_results.extend(keyword_results)
            
            # Specialized price search for price queries
            if intent['is_price_query'] and intent['furniture_types']:
                print(f"🔍 DEBUG: Adding specialized price search")
                price_results = self.find_price_information(documents, query)
                enhanced_results.extend(price_results)
        
        # Remove duplicates and sort by score
        seen_content = set()
        unique_results = []
        
        for result in enhanced_results:
            # Use first 100 characters as uniqueness key
            content_key = result.content[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        # Sort by score
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"🔍 DEBUG: Final results: {len(unique_results)} unique results")
        if unique_results:
            print(f"🔍 DEBUG: Best result method: {unique_results[0].search_method}")
            print(f"🔍 DEBUG: Best result score: {unique_results[0].score}")
        
        # Return top results
        return unique_results[:5]
    
    def get_search_explanation(self, results: List[SearchResult], query: str) -> str:
        """Generate explanation of search process"""
        intent = self.extract_query_intent(query)
        
        explanation = f"🔍 **Análisis de Búsqueda Híbrida**\\n\\n"
        explanation += f"**Consulta:** {query}\\n"
        explanation += f"**Intención detectada:**\\n"
        explanation += f"  • Consulta de precios: {'Sí' if intent['is_price_query'] else 'No'}\\n"
        explanation += f"  • Consulta de productos: {'Sí' if intent['is_product_query'] else 'No'}\\n"
        
        if intent['furniture_types']:
            explanation += f"  • Mobiliario mencionado: {', '.join(intent['furniture_types'])}\\n"
        
        if results:
            explanation += f"\\n**Resultados encontrados:** {len(results)}\\n"
            explanation += f"**Método principal:** {results[0].search_method}\\n"
            explanation += f"**Puntuación:** {results[0].score:.1f}\\n"
        else:
            explanation += f"\\n**No se encontraron resultados específicos**\\n"
        
        return explanation