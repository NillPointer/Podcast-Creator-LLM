import os
import tempfile
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from typing import Optional, List
from io import BytesIO
from app.logger import setup_logger

logger = setup_logger('pdf_processor')

def extract_text_from_pdf(pdf_file: BytesIO) -> str:
    """
    Extract text content from a PDF file using docling.

    Args:
        pdf_file: BytesIO object containing PDF data

    Returns:
        Extracted text content as markdown string

    Raises:
        Exception: If PDF processing fails
    """
    try:
        # Convert PDF to markdown using docling
        source = DocumentStream(name="source.pdf", stream=pdf_file)
        converter = DocumentConverter()
        result = converter.convert(source)
        markdown_text = result.document.export_to_markdown()

        if not markdown_text:
            raise ValueError("No text found in PDF")

        logger.info(f"Successfully extracted text from PDF ({len(markdown_text)} characters)")
        return markdown_text
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

    except Exception:
        return False