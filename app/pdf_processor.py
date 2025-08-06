import os
import time
import re
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from typing import Optional, List
from io import BytesIO
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('pdf_processor')

DOCLING_MODELS_PATH = "/root/.cache/docling/models"

class PDFProcessor:
    def __init__(self):
        pipeline_options = PdfPipelineOptions(artifacts_path=DOCLING_MODELS_PATH)
        if hasattr(pipeline_options, "do_ocr"):
            pipeline_options.do_ocr = False
        if hasattr(pipeline_options, "do_table_structure"):
            pipeline_options.do_table_structure = True
        if hasattr(pipeline_options, "accelerator_device"):
            pipeline_options.accelerator_device = "cpu"
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def extract_text_from_pdf(self, pdf_file: BytesIO) -> str:
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
            result = self.converter.convert(source)
            markdown_text = result.document.export_to_markdown()
            
            if not markdown_text:
                raise ValueError("No text found in Arxiv document")

            markdown_text = remove_references(markdown_text)
            markdown_text = truncate_string(markdown_text)

            # Write debug to file in tmp
            if settings.DEBUG:
                os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                timestamp = int(time.time())
                file_path = os.path.join(settings.DEBUG_DIR, f"pdf-{timestamp}.md")
                with open(file_path, "w") as f:
                    f.write(markdown_text)

            logger.info(f"Successfully extracted text from PDF ({len(markdown_text)} characters)")
            return markdown_text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def extract_text_from_arxiv(self, arxiv_url: str) -> str:
        """
        Extract text content from an Arxiv URL using docling.

        Args:
            arxiv_url: Arxiv URL (e.g., "https://arxiv.org/pdf/2408.09869")

        Returns:
            Extracted text content as markdown string

        Raises:
            Exception: If Arxiv processing fails
        """
        try:
            # Convert Arxiv URL to markdown using docling
            result = self.converter.convert(arxiv_url)
            markdown_text = result.document.export_to_markdown()

            if not markdown_text:
                raise ValueError("No text found in Arxiv document")

            markdown_text = remove_references(markdown_text)
            markdown_text = truncate_string(markdown_text)

            # Write debug to file in tmp
            if settings.DEBUG:
                os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                timestamp = int(time.time())
                file_path = os.path.join(settings.DEBUG_DIR, f"pdf-{timestamp}.md")
                with open(file_path, "w") as f:
                    f.write(markdown_text)

            logger.info(f"Successfully extracted text from Arxiv URL ({len(markdown_text)} characters)")
            return markdown_text
        except Exception as e:
            logger.error(f"Failed to extract text from Arxiv URL: {str(e)}")
            raise Exception(f"Failed to extract text from Arxiv URL: {str(e)}")
        
def remove_references(text):
    # Regex to find the exact line containing '## References' (with optional trailing spaces)
    pattern = r'^#+\s*references\s*$'
    
    # Find the index of the first match of '## References'
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    
    if match:
        # If found, take the part of the text before the match
        return text[:match.start()]
    else:
        # If not found, return the text as is
        return text

def truncate_string(input_string):
    # Check if the string length is greater than 92,000 characters
    if len(input_string) > settings.MAX_CHARACTER_SIZE:
        # Truncate the string to exactly 92,000 characters
        return input_string[:settings.MAX_CHARACTER_SIZE]
    else:
        # Return the string as is if it's already 92,000 characters or less
        return input_string