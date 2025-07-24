"""
Exhibitor Query Tool for Food Service 2025
Specialized tool for extracting exhibitor information from documents
"""

import os
import logging
import PyPDF2
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ExhibitorQueryTool:
    def __init__(self, folder_path: str):
        """
        Initialize exhibitor query tool
        
        Args:
            folder_path: Path to the folder containing exhibitor documents
        """
        self.folder_path = folder_path
        self.indexed_data = {}
        self.company_patterns = [
            r'\b[A-Z][a-zA-Z\s&\.,]+(?:S\.A\.|S\.L\.|Inc\.|Corp\.|Ltd\.|LLC|Co\.)\b',
            r'\b[A-Z][a-zA-Z\s&\.,]{2,30}\b(?=\s*[-–]\s*(?:Stand|Booth|Pabellón))',
            r'(?:Empresa|Company|Exhibitor):\s*([A-Z][a-zA-Z\s&\.,]+)',
            r'\b[A-Z][A-Z\s&]+\b(?=\s*Stand)',
        ]
        self.stand_patterns = [
            r'(?:Stand|Booth|Pabellón)\s*:?\s*([A-Z]?\d+[A-Z]?)',
            r'(?:Stand|Booth|Pabellón)\s+([A-Z]?\d+[A-Z]?)',
            r'(\d+[A-Z]?)\s*(?:Stand|Booth)',
        ]
        self.index_documents()
    
    def index_documents(self) -> None:
        """Index all exhibitor documents (PDF and Excel)"""
        if not os.path.exists(self.folder_path):
            logger.warning(f"Exhibitor folder does not exist: {self.folder_path}")
            return
        
        try:
            for filename in os.listdir(self.folder_path):
                file_path = os.path.join(self.folder_path, filename)
                content = None
                companies = []
                
                if filename.lower().endswith('.pdf'):
                    content = self._extract_pdf_content(file_path)
                    if content:
                        companies = self._extract_companies_from_text(content)
                elif filename.lower().endswith(('.xlsx', '.xls')):
                    content = self._extract_excel_content(file_path)
                    companies = self._extract_companies_from_excel(file_path)
                
                if content or companies:
                    self.indexed_data[filename] = {
                        'content': content or '',
                        'companies': companies,
                        'path': file_path,
                        'type': 'pdf' if filename.lower().endswith('.pdf') else 'excel'
                    }
                    logger.info(f"Indexed exhibitor document: {filename} with {len(companies)} companies")
            
            logger.info(f"Indexed {len(self.indexed_data)} exhibitor documents")
            
        except Exception as e:
            logger.error(f"Error indexing exhibitor documents: {str(e)}")
    
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
    
    def _extract_companies_from_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract companies directly from Excel structure"""
        companies = []
        try:
            if file_path.lower().endswith('.xlsx'):
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            else:
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
            
            for sheet_name, df in df_dict.items():
                if df.empty:
                    continue
                
                # Look for columns that might contain company names
                company_columns = []
                stand_columns = []
                
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(keyword in col_str for keyword in ['empresa', 'company', 'expositor', 'exhibitor', 'nombre']):
                        company_columns.append(col)
                    elif any(keyword in col_str for keyword in ['stand', 'booth', 'pabellón']):
                        stand_columns.append(col)
                
                # Extract companies from identified columns
                for _, row in df.iterrows():
                    for company_col in company_columns:
                        company_name = str(row[company_col]) if pd.notna(row[company_col]) else ""
                        if company_name and company_name != "nan" and len(company_name) > 2:
                            # Look for corresponding stand
                            stand = ""
                            for stand_col in stand_columns:
                                if pd.notna(row[stand_col]):
                                    stand = str(row[stand_col])
                                    break
                            
                            companies.append({
                                'name': company_name.strip(),
                                'stand': stand.strip() if stand else None,
                                'source_sheet': sheet_name,
                                'line': f"Sheet: {sheet_name}, Row: {row.name + 1}"
                            })
                
                # If no specific columns found, try text extraction from all cells
                if not company_columns:
                    for _, row in df.iterrows():
                        for col in df.columns:
                            cell_value = str(row[col]) if pd.notna(row[col]) else ""
                            if cell_value and len(cell_value) > 3:
                                # Try to extract companies from cell text
                                text_companies = self._extract_companies_from_text(cell_value)
                                for company in text_companies:
                                    company['source_sheet'] = sheet_name
                                    companies.append(company)
            
            return self._remove_duplicate_companies(companies)
            
        except Exception as e:
            logger.error(f"Error extracting companies from Excel {file_path}: {str(e)}")
            return []
    
    def _extract_companies_from_text(self, content: str) -> List[Dict[str, Any]]:
        """Extract company names and stands from content"""
        companies = []
        
        try:
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or len(line) < 3:
                    continue
                
                # Try to extract company and stand information
                company_match = None
                stand_match = None
                
                # Look for company patterns
                for pattern in self.company_patterns:
                    match = re.search(pattern, line)
                    if match:
                        company_name = match.group(1) if match.groups() else match.group(0)
                        company_name = company_name.strip()
                        if len(company_name) > 2 and len(company_name) < 100:
                            company_match = company_name
                            break
                
                # Look for stand patterns in the same line
                for pattern in self.stand_patterns:
                    match = re.search(pattern, line)
                    if match:
                        stand_match = match.group(1).strip()
                        break
                
                # If we found a company, add it
                if company_match:
                    companies.append({
                        'name': company_match,
                        'stand': stand_match,
                        'line': line
                    })
            
            # Remove duplicates based on company name similarity
            unique_companies = self._remove_duplicate_companies(companies)
            
            return unique_companies
            
        except Exception as e:
            logger.error(f"Error extracting companies: {str(e)}")
            return []
    
    def _remove_duplicate_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate companies based on name similarity"""
        unique_companies = []
        
        for company in companies:
            is_duplicate = False
            
            for existing in unique_companies:
                similarity = SequenceMatcher(None, 
                                           company['name'].lower(), 
                                           existing['name'].lower()).ratio()
                
                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    # Keep the one with stand info if available
                    if company.get('stand') and not existing.get('stand'):
                        unique_companies.remove(existing)
                        unique_companies.append(company)
                    break
            
            if not is_duplicate:
                unique_companies.append(company)
        
        return unique_companies
    
    def extract_exhibitor_info(self, query: str) -> Dict[str, Any]:
        """
        Extract exhibitor information based on query
        
        Args:
            query: Search query for exhibitor information
            
        Returns:
            Dictionary containing companies and statistics
        """
        result = {
            "companies": [],
            "stats": {},
            "query": query
        }
        
        if not self.indexed_data:
            return result
        
        try:
            query_lower = query.lower()
            all_companies = []
            
            # Collect all companies from indexed documents
            for filename, doc_data in self.indexed_data.items():
                companies = doc_data.get('companies', [])
                for company in companies:
                    company['source_file'] = filename
                    all_companies.append(company)
            
            # Filter companies based on query
            if any(keyword in query_lower for keyword in ['todos', 'all', 'lista', 'completa']):
                # Return all companies
                result["companies"] = all_companies
            elif any(keyword in query_lower for keyword in ['stand', 'pabellón', 'booth']):
                # Filter companies with stand information
                result["companies"] = [c for c in all_companies if c.get('stand')]
            else:
                # Search by company name or general terms
                matching_companies = []
                for company in all_companies:
                    company_name_lower = company['name'].lower()
                    
                    # Check if query matches company name
                    if (query_lower in company_name_lower or 
                        any(word in company_name_lower for word in query_lower.split() if len(word) > 2)):
                        matching_companies.append(company)
                
                result["companies"] = matching_companies if matching_companies else all_companies[:20]
            
            # Generate statistics
            result["stats"] = self._generate_exhibitor_stats(all_companies)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting exhibitor info: {str(e)}")
            return result
    
    def _generate_exhibitor_stats(self, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from company data"""
        if not companies:
            return {}
        
        stats = {
            "Total de expositores": len(companies),
            "Con información de stand": len([c for c in companies if c.get('stand')]),
            "Sin información de stand": len([c for c in companies if not c.get('stand')])
        }
        
        # Count by source file
        file_counts = {}
        for company in companies:
            source_file = company.get('source_file', 'Unknown')
            file_counts[source_file] = file_counts.get(source_file, 0) + 1
        
        if file_counts:
            stats["Distribución por documento"] = file_counts
        
        return stats
    
    def refresh_index(self) -> None:
        """Refresh the exhibitor data index"""
        self.indexed_data.clear()
        self.index_documents()
        logger.info("Exhibitor data index refreshed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool statistics"""
        total_companies = sum(len(doc_data.get('companies', [])) 
                            for doc_data in self.indexed_data.values())
        
        return {
            "documents_processed": len(self.indexed_data),
            "total_companies": total_companies,
            "folder_path": self.folder_path
        }