"""
CLARIUS Backend - OCR Parsing Service Test Suite

This suite verifies that:
1. Image extraction calls PaddleOCR wrapper correctly.
2. Scanned PDFs without text layers fall back to OCR extraction.
3. The simulation mode works gracefully without crashing when PaddleOCR package is absent.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.documents.application.ocr_service import ocr_service
from app.ai.ocr.paddle_ocr import paddle_ocr_wrapper


class TestOCRService(unittest.TestCase):

    def test_txt_file_direct_read(self):
        # Create temp file
        temp_txt = Path("test_sample.txt")
        temp_txt.write_text("Hello, CLARIUS OCR!", encoding="utf-8")
        
        try:
            res = ocr_service.extract_text(temp_txt)
            self.assertEqual(res, "Hello, CLARIUS OCR!")
        finally:
            if temp_txt.exists():
                temp_txt.unlink()

    def test_image_ocr_simulation_fallback(self):
        # Even if paddleocr package isn't installed, wrapper must fall back cleanly
        temp_img = Path("test_invoice.png")
        temp_img.write_text("dummy bytes", encoding="utf-8")
        
        try:
            res = ocr_service.extract_text(temp_img)
            self.assertIn("[OCR SIMULATION EXTRACT", res)
            self.assertIn("Test Invoice", res)
        finally:
            if temp_img.exists():
                temp_img.unlink()

    @patch("app.modules.documents.application.ocr_service.pdfplumber.open")
    def test_scanned_pdf_triggers_ocr(self, mock_pdfplumber):
        # Configure pdfplumber to open but return no pages containing text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None  # Scanned page
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        # Mock pypdf read return empty text
        with patch("app.modules.documents.application.ocr_service.pypdf.PdfReader") as mock_pypdf:
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()]
            mock_reader.pages[0].extract_text.return_value = ""
            mock_pypdf.return_value = mock_reader
            
            temp_pdf = Path("scanned_doc.pdf")
            temp_pdf.write_text("dummy pdf struct", encoding="utf-8")
            
            try:
                res = ocr_service.extract_text(temp_pdf)
                self.assertIn("[OCR SIMULATION EXTRACT - scanned_doc.pdf]", res)
            finally:
                if temp_pdf.exists():
                    temp_pdf.unlink()


if __name__ == '__main__':
    unittest.main()
