"""
Visitor Query Tool for Food Service 2025
Specialized tool for extracting visitor information and statistics from documents
"""

import os
import logging
import PyPDF2
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VisitorQueryTool:
    def __init__(self, folder_path: str):
        """
        Initialize visitor query tool
        
        Args:
            folder_path: Path to the folder containing visitor documents
        """
        self.folder_path = folder_path
        self.indexed_data = {}
        
        # Patterns for extracting visitor data
        self.visitor_number_patterns = [
            r'(?:visitantes?|visitors?|asistentes?)\s*:?\s*(\d{1,6})',
            r'(\d{1,6})\s*(?:visitantes?|visitors?|asistentes?)',
            r'(?:total|total de)\s*(?:visitantes?|visitors?)\s*:?\s*(\d{1,6})',
            r'(?:attendance|asistencia)\s*:?\s*(\d{1,6})',
        ]
        
        self.daily_patterns = [
            r'(?:día|day)\s*(\d{1,2})\s*:?\s*(\d{1,6})\s*(?:visitantes?|visitors?)',
            r'(\d{1,2})/(\d{1,2})/(\d{4})\s*:?\s*(\d{1,6})',
            r'(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s*:?\s*(\d{1,6})',
        ]
        
        self.demographic_patterns = [
            r'(?:hombres?|men|male)\s*:?\s*(\d{1,6}|\d{1,3}%)',
            r'(?:mujeres?|women|female)\s*:?\s*(\d{1,6}|\d{1,3}%)',
            r'(?:edad|age)\s*(?:promedio|average)\s*:?\s*(\d{1,3})',
            r'(?:profesionales?|professionals?)\s*:?\s*(\d{1,6}|\d{1,3}%)',
            r'(?:estudiantes?|students?)\s*:?\s*(\d{1,6}|\d{1,3}%)',
        ]
        
        self.index_documents()
    
    def index_documents(self) -> None:
        """Index all visitor documents (PDF and Excel)"""
        if not os.path.exists(self.folder_path):
            logger.warning(f"Visitor folder does not exist: {self.folder_path}")
            return
        
        try:
            for filename in os.listdir(self.folder_path):
                file_path = os.path.join(self.folder_path, filename)
                content = None
                visitor_data = {}
                
                if filename.lower().endswith('.pdf'):
                    content = self._extract_pdf_content(file_path)
                    if content:
                        visitor_data = self._extract_visitor_data_from_text(content)
                elif filename.lower().endswith(('.xlsx', '.xls')):
                    content = self._extract_excel_content(file_path)
                    visitor_data = self._extract_visitor_data_from_excel(file_path)
                
                if content or visitor_data:
                    self.indexed_data[filename] = {
                        'content': content or '',
                        'visitor_data': visitor_data,
                        'path': file_path,
                        'type': 'pdf' if filename.lower().endswith('.pdf') else 'excel'
                    }
                    logger.info(f"Indexed visitor document: {filename}")
            
            logger.info(f"Indexed {len(self.indexed_data)} visitor documents")
            
        except Exception as e:
            logger.error(f"Error indexing visitor documents: {str(e)}")
    
    def _extract_pdf_content(self, file_path: str) -> Optional[str]:
        """Extract text content from PDF file"""
        try:
            content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + "\n"
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting PDF content from {file_path}: {str(e)}")
            return None
    
    def _extract_excel_content(self, file_path: str) -> Optional[str]:
        """Extract text content from Excel file"""
        try:
            if file_path.lower().endswith('.xlsx'):
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            else:
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
            
            content_parts = []
            for sheet_name, df in df_dict.items():
                content_parts.append(f"HOJA: {sheet_name}")
                if not df.empty:
                    content_parts.append(df.to_string())
            
            return "\n".join(content_parts)
        except Exception as e:
            logger.error(f"Error extracting Excel content from {file_path}: {str(e)}")
            return None
    
    def _extract_visitor_data_from_excel(self, file_path: str) -> Dict[str, Any]:
        """Extract visitor data directly from Excel structure"""
        visitor_data = {
            "total_visitors": None,
            "daily_stats": {},
            "demographics": {},
            "trends": []
        }
        
        try:
            if file_path.lower().endswith('.xlsx'):
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            else:
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
            
            for sheet_name, df in df_dict.items():
                if df.empty:
                    continue
                
                # Look for visitor-related columns
                for col in df.columns:
                    col_str = str(col).lower()
                    
                    # Total visitors
                    if any(keyword in col_str for keyword in ['total', 'visitantes', 'visitors', 'asistentes']):
                        for _, row in df.iterrows():
                            value = row[col]
                            if pd.notna(value) and str(value).isdigit():
                                visitor_count = int(value)
                                if visitor_count > (visitor_data["total_visitors"] or 0):
                                    visitor_data["total_visitors"] = visitor_count
                    
                    # Daily stats
                    elif any(keyword in col_str for keyword in ['día', 'day', 'fecha', 'date']):
                        # Look for corresponding visitor count column
                        for other_col in df.columns:
                            other_col_str = str(other_col).lower()
                            if any(keyword in other_col_str for keyword in ['visitantes', 'visitors', 'cantidad', 'count']):
                                for _, row in df.iterrows():
                                    day_value = row[col]
                                    count_value = row[other_col]
                                    if pd.notna(day_value) and pd.notna(count_value):
                                        day_str = str(day_value)
                                        if str(count_value).replace('.', '').isdigit():
                                            visitor_data["daily_stats"][day_str] = int(float(count_value))
                                break
                    
                    # Demographics
                    elif any(keyword in col_str for keyword in ['hombres', 'men', 'male', 'mujeres', 'women', 'female']):
                        for _, row in df.iterrows():
                            value = row[col]
                            if pd.notna(value):
                                if 'hombres' in col_str or 'men' in col_str or 'male' in col_str:
                                    visitor_data["demographics"]["Hombres"] = str(value)
                                elif 'mujeres' in col_str or 'women' in col_str or 'female' in col_str:
                                    visitor_data["demographics"]["Mujeres"] = str(value)
                
                # Extract trends from text content
                text_content = df.to_string()
                trends = self._extract_trends(text_content)
                visitor_data["trends"].extend(trends)
            
            return visitor_data
            
        except Exception as e:
            logger.error(f"Error extracting visitor data from Excel {file_path}: {str(e)}")
            return visitor_data
    
    def _extract_visitor_data_from_text(self, content: str) -> Dict[str, Any]:
        """Extract visitor statistics and information from content"""
        visitor_data = {
            "total_visitors": None,
            "daily_stats": {},
            "demographics": {},
            "trends": []
        }
        
        try:
            content_lower = content.lower()
            
            # Extract total visitor numbers
            for pattern in self.visitor_number_patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                if matches:
                    # Take the largest number found (likely the total)
                    numbers = [int(match) for match in matches if match.isdigit()]
                    if numbers:
                        visitor_data["total_visitors"] = max(numbers)
                        break
            
            # Extract daily statistics
            lines = content.split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                
                # Look for daily patterns
                for pattern in self.daily_patterns:
                    matches = re.findall(pattern, line_lower)
                    if matches:
                        for match in matches:
                            if len(match) == 2:  # Day number and visitors
                                day, visitors = match
                                if day.isdigit() and visitors.isdigit():
                                    visitor_data["daily_stats"][f"Día {day}"] = int(visitors)
                            elif len(match) == 4:  # Date format
                                day, month, year, visitors = match
                                if visitors.isdigit():
                                    date_key = f"{day}/{month}/{year}"
                                    visitor_data["daily_stats"][date_key] = int(visitors)
                
                # Look for demographic information
                for pattern in self.demographic_patterns:
                    matches = re.findall(pattern, line_lower)
                    if matches:
                        for match in matches:
                            if 'hombres' in pattern or 'men' in pattern or 'male' in pattern:
                                visitor_data["demographics"]["Hombres"] = match
                            elif 'mujeres' in pattern or 'women' in pattern or 'female' in pattern:
                                visitor_data["demographics"]["Mujeres"] = match
                            elif 'edad' in pattern or 'age' in pattern:
                                visitor_data["demographics"]["Edad promedio"] = match
                            elif 'profesionales' in pattern or 'professionals' in pattern:
                                visitor_data["demographics"]["Profesionales"] = match
                            elif 'estudiantes' in pattern or 'students' in pattern:
                                visitor_data["demographics"]["Estudiantes"] = match
            
            # Extract trends and insights
            trends = self._extract_trends(content)
            visitor_data["trends"] = trends
            
            return visitor_data
            
        except Exception as e:
            logger.error(f"Error extracting visitor data: {str(e)}")
            return visitor_data
    
    def _extract_trends(self, content: str) -> List[str]:
        """Extract visitor trends and insights from content"""
        trends = []
        
        trend_keywords = [
            'aumento', 'increase', 'incremento', 'crecimiento', 'growth',
            'disminución', 'decrease', 'reducción', 'decline',
            'pico', 'peak', 'máximo', 'maximum',
            'tendencia', 'trend', 'patrón', 'pattern'
        ]
        
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) < 10:  # Skip very short lines
                    continue
                
                line_lower = line.lower()
                
                # Check if line contains trend keywords
                if any(keyword in line_lower for keyword in trend_keywords):
                    # Check if line also contains numbers (likely statistical)
                    if re.search(r'\d+', line):
                        trends.append(line)
                        
                        if len(trends) >= 5:  # Limit to 5 trends
                            break
            
            return trends
            
        except Exception as e:
            logger.error(f"Error extracting trends: {str(e)}")
            return []
    
    def extract_visitor_info(self, query: str) -> Dict[str, Any]:
        """
        Extract visitor information based on query
        
        Args:
            query: Search query for visitor information
            
        Returns:
            Dictionary containing visitor statistics and demographics
        """
        result = {
            "total_visitors": None,
            "daily_stats": {},
            "demographics": {},
            "trends": [],
            "query": query
        }
        
        if not self.indexed_data:
            return result
        
        try:
            query_lower = query.lower()
            
            # Aggregate data from all documents
            all_visitor_data = []
            for filename, doc_data in self.indexed_data.items():
                visitor_data = doc_data.get('visitor_data', {})
                visitor_data['source_file'] = filename
                all_visitor_data.append(visitor_data)
            
            # Process based on query type
            if any(keyword in query_lower for keyword in ['total', 'cuantos', 'cantidad']):
                # Return total visitor numbers
                totals = [data.get('total_visitors') for data in all_visitor_data 
                         if data.get('total_visitors')]
                if totals:
                    result["total_visitors"] = max(totals)  # Take the highest total
            
            if any(keyword in query_lower for keyword in ['día', 'day', 'diario', 'daily']):
                # Aggregate daily statistics
                for data in all_visitor_data:
                    daily_stats = data.get('daily_stats', {})
                    result["daily_stats"].update(daily_stats)
            
            if any(keyword in query_lower for keyword in ['demografía', 'demographics', 'perfil']):
                # Aggregate demographic information
                for data in all_visitor_data:
                    demographics = data.get('demographics', {})
                    result["demographics"].update(demographics)
            
            if any(keyword in query_lower for keyword in ['tendencia', 'trend', 'patrón']):
                # Aggregate trends
                for data in all_visitor_data:
                    trends = data.get('trends', [])
                    result["trends"].extend(trends)
            
            # If no specific type requested, return everything
            if not any(keyword in query_lower for keyword in 
                      ['total', 'día', 'demografía', 'tendencia']):
                # Aggregate all data
                totals = [data.get('total_visitors') for data in all_visitor_data 
                         if data.get('total_visitors')]
                if totals:
                    result["total_visitors"] = max(totals)
                
                for data in all_visitor_data:
                    result["daily_stats"].update(data.get('daily_stats', {}))
                    result["demographics"].update(data.get('demographics', {}))
                    result["trends"].extend(data.get('trends', []))
            
            # Remove duplicate trends
            result["trends"] = list(set(result["trends"]))[:5]
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting visitor info: {str(e)}")
            return result
    
    def refresh_index(self) -> None:
        """Refresh the visitor data index"""
        self.indexed_data.clear()
        self.index_documents()
        logger.info("Visitor data index refreshed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool statistics"""
        total_data_points = 0
        for doc_data in self.indexed_data.values():
            visitor_data = doc_data.get('visitor_data', {})
            total_data_points += len(visitor_data.get('daily_stats', {}))
            total_data_points += len(visitor_data.get('demographics', {}))
            total_data_points += len(visitor_data.get('trends', []))
            if visitor_data.get('total_visitors'):
                total_data_points += 1
        
        return {
            "documents_processed": len(self.indexed_data),
            "total_data_points": total_data_points,
            "folder_path": self.folder_path
        }