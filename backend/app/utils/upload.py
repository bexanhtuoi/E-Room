from fastapi import HTTPException, UploadFile, status

FILE_MEDIA = {"pdf": "application/pdf", "md": "text/markdown", "txt": "text/plain"}


def media_type_for(suffix: str | None) -> str:
    return FILE_MEDIA.get((suffix or "").lower(), "application/octet-stream")


def file_suffix(filename: str | None) -> str:
    name = filename or ""
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


async def read_upload(file: UploadFile, allowed: set, max_bytes: int, label: str) -> tuple[bytes, str]:
    suffix = file_suffix(file.filename)
    if suffix not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(sorted(allowed))} files are supported",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} must be at most {max_bytes // (1024 * 1024)}MB",
        )

    return raw, suffix
