import os
import hmac
import hashlib
import time
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException, UploadFile, status
from backend.app.core.config import settings

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png"
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

def validate_and_scan_file(file: UploadFile, file_bytes: bytes) -> Tuple[str, str]:
    """
    Validates file extension, MIME type, file size, magic bytes,
    and runs a malware scan stub.
    Returns (cleaned_filename, verified_mime_type).
    """
    filename = file.filename or "uploaded_document.pdf"
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: PDF, JPG, JPEG, PNG."
        )

    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024*1024)}MB."
        )

    # Magic byte inspection
    mime_type = file.content_type or "application/octet-stream"
    if file_bytes.startswith(b"%PDF"):
        detected_mime = "application/pdf"
    elif file_bytes.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    else:
        # Check if declared mime is allowed
        if mime_type in ALLOWED_MIME_TYPES:
            detected_mime = mime_type
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format header. Allowed formats: PDF, JPG, PNG."
            )

    # Malware Scan Stub
    # Detects EICAR test signature and suspicious executable headers
    if EICAR_SIGNATURE in file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SECURITY ALERT: Malware/EICAR signature detected in uploaded file. Upload rejected."
        )
    if file_bytes.startswith(b"MZ") or file_bytes.startswith(b"\x7fELF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SECURITY ALERT: Executable binary payload detected. Upload rejected."
        )

    return filename, detected_mime


def compute_file_sha256(data: bytes) -> str:
    """Computes SHA-256 byte digest."""
    return hashlib.sha256(data).hexdigest()


def generate_document_identifier(doc_id: int, year: Optional[int] = None) -> str:
    """
    Standard AICTE Regulation Bureau Document ID
    e.g., FDR-2026-00145
    """
    target_year = year or 2026
    return f"FDR-{target_year}-{doc_id:05d}"


def create_signed_download_token(document_id: int, expires_in_seconds: int = 900) -> Dict[str, Any]:
    """
    Creates an HMAC-signed token for expiring download URL (15 minutes default).
    Token format: {document_id}:{timestamp}:{signature}
    """
    expires_at = int(time.time()) + expires_in_seconds
    message = f"{document_id}:{expires_at}".encode()
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    token = f"{document_id}.{expires_at}.{signature}"
    return {
        "token": token,
        "document_id": document_id,
        "expires_at": expires_at,
        "expires_in_seconds": expires_in_seconds
    }


def verify_signed_download_token(token: str) -> int:
    """
    Verifies the HMAC signature and expiration of a download token.
    Returns document_id if valid, raises HTTPException otherwise.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid download token structure"
        )
    
    try:
        doc_id_str, expires_at_str, signature = parts
        document_id = int(doc_id_str)
        expires_at = int(expires_at_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed download token parameters"
        )
    
    # Check expiry
    current_time = int(time.time())
    if current_time > expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Download token has expired. Please request a new signed URL."
        )

    # Check signature
    message = f"{document_id}:{expires_at}".encode()
    expected_sig = hmac.new(
        settings.SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tampered or invalid token signature"
        )

    return document_id

