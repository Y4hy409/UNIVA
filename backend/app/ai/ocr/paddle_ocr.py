"""
CLARIUS Backend - PaddleOCR Wrapper

This module handles OCR text extraction for scanned documents and images.
It supports dynamic import to fail gracefully on systems without compilation tools (P1.3).
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("clarius.ai.ocr")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


class PaddleOCRWrapper:
    """Wrapper class managing the local PaddleOCR runtime context."""

    def __init__(self, use_gpu: bool = False, lang: str = "en"):
        self.ocr_engine = None
        self.lang = lang
        self.use_gpu = use_gpu
        self._initialized = False

    def _lazy_init(self) -> None:
        """Initialize the OCR engine instance if paddleocr is installed."""
        if self._initialized:
            return
            
        if PADDLE_AVAILABLE:
            try:
                # Initialize local models context
                self.ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR engine: {str(e)}")
                self.ocr_engine = None
        else:
            logger.warning("PaddleOCR is not installed in the current environment. Operating in simulation mode.")
            
        self._initialized = True

    def extract_text_from_image(self, image_path: Path) -> str:
        """Extract text lines from image file."""
        self._lazy_init()
        
        if not PADDLE_AVAILABLE or self.ocr_engine is None:
            return self._simulate_ocr_extraction(image_path)

        try:
            results = self.ocr_engine.ocr(str(image_path), cls=True)
            if not results or not results[0]:
                return ""
                
            text_lines = []
            for line in results[0]:
                # line format: [[coords], (text, confidence)]
                text_lines.append(line[1][0])
                
            return "\n".join(text_lines).strip()
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed for {image_path.name}: {str(e)}")
            return self._simulate_ocr_extraction(image_path)

    def _simulate_ocr_extraction(self, file_path: Path) -> str:
        """Provide a clean fallback text when OCR is run without local binaries."""
        logger.info(f"Generating simulated OCR text for {file_path.name}")
        base_name = file_path.stem.replace('_', ' ').replace('-', ' ').title()
        
        return (
            f"[OCR SIMULATION EXTRACT - {file_path.name}]\n"
            f"Document Title: {base_name}\n"
            f"Generated: {Path(file_path).stat().st_mtime if file_path.exists() else 'N/A'}\n"
            f"Content: Standard processed image text context for {base_name}."
        )


# Global singleton instance
paddle_ocr_wrapper = PaddleOCRWrapper()
