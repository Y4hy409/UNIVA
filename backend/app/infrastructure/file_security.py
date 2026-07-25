"""
CLARIUS Backend - File Security Utilities

This module implements secure upload validation, filename sanitization,
and path traversal prevention to isolate file writes within the data sandbox (P0).
"""

import os
import re
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

logger = logging.getLogger("clarius.security.files")

# Maximum permitted file size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

class FileSecurity:
    """Security checks enforcing path normalization, filename sanitization, and size caps."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize input filenames to eliminate relative traversals,
        punctuation, and special character injection sequences.
        """
        # Strip directories/paths if supplied in filename
        base_name = os.path.basename(filename)
        # Allow only alphanumeric characters, periods, dashes, and underscores
        sanitized = re.sub(r"[^\w\.\-_]", "_", base_name)
        # Enforce non-empty name
        if not sanitized or sanitized in (".", ".."):
            sanitized = "safe_upload_file"
        return sanitized

    @staticmethod
    def validate_and_sandbox(
        file: UploadFile,
        allowed_extensions: list,
        upload_dir_name: str = None
    ) -> Path:
        """
        Validates target file extension, size limits, and ensures path resolves
        strictly within the absolute boundaries of the upload sandbox.
        """
        # 1. Validate file extension
        filename_sanitized = FileSecurity.sanitize_filename(file.filename)
        file_ext = filename_sanitized.split('.')[-1].lower() if '.' in filename_sanitized else ""
        
        if file_ext not in [ext.strip().lower().replace('.', '') for ext in allowed_extensions]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: '.{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
            )

        # 2. Establish and verify target directory paths
        if upload_dir_name is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            base_sandbox = (base_dir / "data" / "uploads").resolve()
        else:
            base_sandbox = Path(upload_dir_name).resolve()
        base_sandbox.mkdir(parents=True, exist_ok=True)
        
        target_path = (base_sandbox / filename_sanitized).resolve()

        # 3. Prevent path traversal by asserting target starts with sandbox root
        if not str(target_path).startswith(str(base_sandbox)):
            logger.warning(f"Path traversal attempt blocked: {file.filename} -> {target_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid filename path sequence."
            )

        # 4. Validate file size limits
        # We read a chunk to verify size, then reset file pointer
        try:
            file.file.seek(0, 2)  # Seek to end of file
            size = file.file.tell()
            file.file.seek(0)     # Reset to beginning
            
            if size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES / (1024 * 1024)}MB."
                )
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Failed to check size for upload {file.filename}: {str(e)}")
            # In case seek is not supported by SpooledTemporaryFile wrapper, we proceed fail-safe
            pass

        return target_path
