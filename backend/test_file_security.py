"""
CLARIUS Backend - File Security Test Suite

This module runs comprehensive tests on the FileSecurity class,
verifying that file paths are sanitized, sized correctly, and sandboxed.
"""

import io
import sys
import unittest
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Add app to python path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.file_security import FileSecurity, MAX_FILE_SIZE_BYTES


class TestFileSecurity(unittest.TestCase):

    def setUp(self):
        self.sandbox_dir = "data/test_uploads"
        # Ensure clean sandbox directory path
        p = Path(self.sandbox_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)

    def test_filename_sanitization(self):
        test_cases = [
            ("sales.csv", "sales.csv"),
            ("some/path/sales.csv", "sales.csv"),
            ("some\\path\\sales.csv", "sales.csv"),
            ("sales space.csv", "sales_space.csv"),
            ("sales*special$.csv", "sales_special_.csv"),
            ("../../evil.csv", "evil.csv"),
            ("..\\..\\evil.csv", "evil.csv"),
            ("", "safe_upload_file"),
            (".", "safe_upload_file"),
            ("..", "safe_upload_file")
        ]
        for inp, expected in test_cases:
            with self.subTest(input=inp):
                self.assertEqual(FileSecurity.sanitize_filename(inp), expected)

    def test_allowed_extensions(self):
        # Create a mock file
        file_obj = io.BytesIO(b"id,amount\n1,100")
        upload_file = UploadFile(filename="sales.csv", file=file_obj)
        
        # Should succeed
        path = FileSecurity.validate_and_sandbox(upload_file, ["csv"], self.sandbox_dir)
        self.assertEqual(path.name, "sales.csv")

    def test_rejected_extensions(self):
        file_obj = io.BytesIO(b"some text")
        upload_file = UploadFile(filename="evil.exe", file=file_obj)
        
        with self.assertRaises(HTTPException) as context:
            FileSecurity.validate_and_sandbox(upload_file, ["txt", "pdf"], self.sandbox_dir)
        self.assertEqual(context.exception.status_code, 400)

    def test_path_traversal_prevention(self):
        file_obj = io.BytesIO(b"data")
        # Direct traversal in filename
        upload_file = UploadFile(filename="../../../../etc/passwd.txt", file=file_obj)
        
        # Sanitizer cleans the name to "passwd.txt" so it is written in sandbox safely
        path = FileSecurity.validate_and_sandbox(upload_file, ["txt"], self.sandbox_dir)
        self.assertTrue(path.resolve().is_relative_to(Path(self.sandbox_dir).resolve()))

    def test_file_size_limit(self):
        # Create file exceeding limit
        oversized_data = b"0" * (MAX_FILE_SIZE_BYTES + 1024)
        file_obj = io.BytesIO(oversized_data)
        upload_file = UploadFile(filename="large.txt", file=file_obj)
        
        with self.assertRaises(HTTPException) as context:
            FileSecurity.validate_and_sandbox(upload_file, ["txt"], self.sandbox_dir)
        self.assertEqual(context.exception.status_code, 413)

    def tearDown(self):
        # Clean test directories
        p = Path(self.sandbox_dir).resolve()
        if p.exists():
            for f in p.glob("*"):
                f.unlink()
            p.rmdir()


if __name__ == '__main__':
    unittest.main()
