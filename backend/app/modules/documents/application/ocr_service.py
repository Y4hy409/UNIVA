"""
CLARIUS Backend - Document OCR Parsing Service

This module handles text extraction from document uploads (PDF, images)
with PaddleOCR fallback and pypdf/pdfplumber text parsers (ADR-006).
"""

import os
import logging
from pathlib import Path
import pypdf
import pdfplumber

from app.ai.ocr.paddle_ocr import paddle_ocr_wrapper

logger = logging.getLogger("clarius.documents.ocr")


class OCRService:
    """Extracts text from files offline using pypdf/pdfplumber and OCR helpers."""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from the given PDF or image file path."""
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext in (".png", ".jpg", ".jpeg", ".tiff"):
            return self._extract_image(file_path)
        else:
            raise ValueError(f"Unsupported document file extension: {ext}")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from standard text-based PDF, falling back to page-by-page plumber extraction."""
        text_content = []
        
        try:
            # 1. Try reading with pdfplumber (very good layout preservation)
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                        
            extracted = "\n".join(text_content).strip()
            if extracted:
                return extracted
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {file_path}, trying pypdf: {str(e)}")
            
        try:
            # 2. Try reading with pypdf
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_content.append(t)
            extracted = "\n".join(text_content).strip()
            if extracted:
                return extracted
        except Exception as e:
            logger.error(f"pypdf extraction failed for {file_path}: {str(e)}")
            
        # 3. If no text extracted (scanned PDF), we perform OCR fallback
        return self._extract_pdf_ocr(file_path)

    def _extract_pdf_ocr(self, file_path: Path) -> str:
        """Fallback OCR for scanned PDFs using PaddleOCR wrapper."""
        logger.info(f"Performing OCR on scanned PDF: {file_path}")
        
        # Scanned PDF path: pass the document path to image extraction helper
        # If paddleocr is installed, it extracts images from the PDF page-by-page.
        # Otherwise, the wrapper handles simulated fallback gracefully.
        return paddle_ocr_wrapper.extract_text_from_image(file_path)

    def _extract_image(self, file_path: Path) -> str:
        """Extract text from images using the PaddleOCR wrapper."""
        logger.info(f"Performing OCR on image: {file_path}")
        return paddle_ocr_wrapper.extract_text_from_image(file_path)


# Global instance
ocr_service = OCRService()
