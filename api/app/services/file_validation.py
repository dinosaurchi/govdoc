ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class FileValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_file(filename: str, content: bytes, mime_type: str | None = None) -> str:
    """Validate uploaded file. Returns validated mime_type. Raises FileValidationError."""
    if not content or len(content) == 0:
        raise FileValidationError("CORRUPT_FILE", "File is empty")

    if len(content) > MAX_FILE_SIZE:
        raise FileValidationError("CORRUPT_FILE", f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})")

    # Determine mime type from extension if not provided
    if not mime_type:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        mime_type = mime_map.get(ext)

    if mime_type not in ALLOWED_MIME_TYPES:
        raise FileValidationError("UNSUPPORTED_MIME", f"Unsupported file type: {mime_type}")

    return mime_type
