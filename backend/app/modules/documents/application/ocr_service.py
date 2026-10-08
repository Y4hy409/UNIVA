"""
CLARIUS Backend - Document OCR & Text Extraction Service

This module handles text extraction from multi-format document uploads (PDF, DOCX, CSV, Excel, TXT, Markdown, Images)
with PaddleOCR fallback and robust offline parsers (ADR-006).
"""

import os
import zipfile
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
import pypdf
import pdfplumber

from app.ai.ocr.paddle_ocr import paddle_ocr_wrapper

logger = logging.getLogger("clarius.documents.ocr")


class OCRService:
    """Extracts text from files offline using standard parsers and OCR helpers."""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from the given file path based on its extension."""
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext in (".txt", ".md", ".markdown", ".json", ".log"):
            return self._extract_plain_text(file_path)
        elif ext in (".docx", ".doc"):
            return self._extract_docx(file_path)
        elif ext == ".csv":
            return self._extract_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            return self._extract_excel(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".webp", ".bmp"):
            return self._extract_image(file_path)
        else:
            # Fallback text read
            try:
                return self._extract_plain_text(file_path)
            except Exception:
                raise ValueError(f"Unsupported document file extension: {ext}")

    def _extract_plain_text(self, file_path: Path) -> str:
        """Read plain text / markdown file."""
        for enc in ("utf-8", "latin-1", "utf-16", "cp1252"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except Exception:
                continue
        with open(file_path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")

    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file using docx library or internal XML parser."""
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            text = "\n\n".join(paragraphs).strip()
            if text:
                return text
        except Exception as e:
            logger.warning(f"python-docx extraction failed for {file_path}, trying raw XML parser: {str(e)}")
            
        # Fallback XML parser inside DOCX zip
        try:
            with zipfile.ZipFile(file_path) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                text_fragments = []
                for elem in tree.iter():
                    if elem.tag.endswith("t"):
                        if elem.text:
                            text_fragments.append(elem.text)
                return " ".join(text_fragments)
        except Exception as e2:
            logger.error(f"DOCX XML extraction failed: {str(e2)}")
            return f"DOCX Document {file_path.name}"

    def _extract_csv(self, file_path: Path) -> str:
        """Extract text from CSV file."""
        try:
            with open(file_path, "rb") as bf:
                magic = bf.read(4)
            if magic.startswith(b'PK\x03\x04') or magic.startswith(b'\xd0\xcf\x11\xe0') or file_path.suffix.lower() in ('.xlsx', '.xls'):
                return self._extract_excel(file_path)
            import pandas as pd
            df = pd.read_csv(file_path, nrows=200)
            return f"CSV Table: {file_path.name}\nColumns: {', '.join(df.columns.astype(str))}\n\n" + df.to_string(index=False)
        except Exception:
            return self._extract_plain_text(file_path)

    def _extract_excel(self, file_path: Path) -> str:
        """Extract text from Excel file."""
        try:
            import pandas as pd
            excel_file = pd.ExcelFile(file_path)
            sheets_text = []
            for sheet_name in excel_file.sheet_names[:5]:
                df = excel_file.parse(sheet_name, nrows=100)
                sheets_text.append(f"Sheet: {sheet_name}\nColumns: {', '.join(df.columns.astype(str))}\n" + df.to_string(index=False))
            return f"Excel Workbook: {file_path.name}\n\n" + "\n\n---\n\n".join(sheets_text)
        except Exception as e:
            logger.error(f"Excel extraction failed: {str(e)}")
            return f"Excel Document: {file_path.name}"

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from standard text-based PDF, falling back to page-by-page plumber extraction."""
        text_content = []
        
        try:
            # 1. Try reading with pdfplumber
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
            
        # 3. Fallback OCR for scanned PDF
        return self._extract_pdf_ocr(file_path)

    def _extract_pdf_ocr(self, file_path: Path) -> str:
        """Fallback OCR for scanned PDFs using PaddleOCR wrapper."""
        logger.info(f"Performing OCR on scanned PDF: {file_path}")
        return paddle_ocr_wrapper.extract_text_from_image(file_path)

    def _extract_image(self, file_path: Path) -> str:
        """Extract text from images using the PaddleOCR wrapper."""
        logger.info(f"Performing OCR on image: {file_path}")
        return paddle_ocr_wrapper.extract_text_from_image(file_path)


# Global instance
ocr_service = OCRService()
