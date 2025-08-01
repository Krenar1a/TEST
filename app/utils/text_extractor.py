import requests
import logging
from typing import Optional
from bs4 import BeautifulSoup
from io import BytesIO
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage
from urllib.parse import urlparse

class TextExtractor:
    """Utility class for extracting text from various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Redbird Bot 1.0 (California Legislation Tracker)'
        })
    
    def extract_from_url(self, url: str) -> Optional[str]:
        """
        Extract text content from a URL (PDF or HTML)
        
        Args:
            url: URL to extract text from
            
        Returns:
            Extracted text string or None if error
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                return self._extract_from_pdf_content(response.content)
            elif 'html' in content_type or 'xml' in content_type:
                return self._extract_from_html_content(response.text)
            else:
                # Try to detect format from content
                if response.content.startswith(b'%PDF'):
                    return self._extract_from_pdf_content(response.content)
                else:
                    return self._extract_from_html_content(response.text)
                    
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching URL {url}: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Error extracting text from URL {url}: {str(e)}")
            return None
    
    def _extract_from_pdf_content(self, pdf_content: bytes) -> Optional[str]:
        """
        Extract text from PDF content bytes
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text string or None if error
        """
        try:
            pdf_file = BytesIO(pdf_content)
            
            # Check if PDF has pages
            pages = list(PDFPage.get_pages(pdf_file))
            if not pages:
                logging.warning("PDF has no pages")
                return None
            
            # Reset file pointer
            pdf_file.seek(0)
            
            # Extract text
            text = extract_text(pdf_file)
            
            if not text or not text.strip():
                logging.warning("No text extracted from PDF")
                return None
            
            # Clean up the text
            cleaned_text = self._clean_extracted_text(text)
            
            logging.info(f"Successfully extracted {len(cleaned_text)} characters from PDF")
            return cleaned_text
            
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            return None
    
    def _extract_from_html_content(self, html_content: str) -> Optional[str]:
        """
        Extract text from HTML content
        
        Args:
            html_content: HTML content string
            
        Returns:
            Extracted text string or None if error
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            if not text or not text.strip():
                logging.warning("No text extracted from HTML")
                return None
            
            # Clean up the text
            cleaned_text = self._clean_extracted_text(text)
            
            logging.info(f"Successfully extracted {len(cleaned_text)} characters from HTML")
            return cleaned_text
            
        except Exception as e:
            logging.error(f"Error extracting text from HTML: {str(e)}")
            return None
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text string
        """
        if not text:
            return ""
        
        # Split into lines and clean each line
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines and very short lines
            if len(line) < 3:
                continue
            
            # Skip lines that are mostly numbers or symbols
            if len([c for c in line if c.isalpha()]) < len(line) * 0.5:
                continue
            
            cleaned_lines.append(line)
        
        # Join lines with single spaces
        cleaned_text = ' '.join(cleaned_lines)
        
        # Remove multiple spaces
        while '  ' in cleaned_text:
            cleaned_text = cleaned_text.replace('  ', ' ')
        
        return cleaned_text.strip()
    
    def extract_from_text_file(self, file_path: str) -> Optional[str]:
        """
        Extract text from a text file
        
        Args:
            file_path: Path to text file
            
        Returns:
            File content as string or None if error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._clean_extracted_text(content)
            
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {str(e)}")
            return None
