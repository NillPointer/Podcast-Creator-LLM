import os
import tempfile
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from typing import Optional, List
from io import BytesIO
from app.logger import setup_logger

logger = setup_logger('pdf_processor')

DOCLING_MODELS_PATH = "/root/.cache/docling/models"

class PDFProcessor:
    def __init__(self):
        pipeline_options = PdfPipelineOptions(artifacts_path=DOCLING_MODELS_PATH)
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
                raise ValueError("No text found in PDF")

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

            logger.info(f"Successfully extracted text from Arxiv URL ({len(markdown_text)} characters)")
            return markdown_text
        except Exception as e:
            logger.error(f"Failed to extract text from Arxiv URL: {str(e)}")
            raise Exception(f"Failed to extract text from Arxiv URL: {str(e)}")

    def validate_pdf_file(self, file_content: bytes) -> bool:
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