import os
import tempfile
from PyPDF2 import PdfReader
from typing import Optional, List
from io import BytesIO
from app.logger import setup_logger

logger = setup_logger('pdf_processor')

def extract_text_from_pdf(pdf_file: BytesIO) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_file: BytesIO object containing PDF data
        
    Returns:
        Extracted text content as string
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        reader = PdfReader(pdf_file)
        text = ""
        
        # Extract text from each page
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        # Clean up the text
        text = text.strip()
        
        if not text:
            raise ValueError("No text found in PDF")
            
        logger.info(f"Successfully extracted text from PDF ({len(text)} characters)")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def validate_pdf_file(file_content: bytes) -> bool:
    """
    Validate that the file is a valid PDF.
    
    Args:
        file_content: Raw bytes of the file
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        # Check if file starts with PDF header
        if not file_content.startswith(b'%PDF'):
            return False
            
        # Try to read with PyPDF2 to verify
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
            
        try:
            reader = PdfReader(tmp_path)
            return True
        finally:
            os.unlink(tmp_path)
            
    except Exception:
        return False