from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


def ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write_text(path: str, content: str, encoding: str = "utf-8") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)
    return p


def read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str, data: Any, indent: int = 2) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=indent, default=str), encoding="utf-8")
    return p


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")


def file_size(path: str) -> int:
    return Path(path).stat().st_size


def list_files(path: str, pattern: str = "*", recursive: bool = False) -> list[Path]:
    p = Path(path)
    if not p.is_dir():
        return []
    iterator = p.rglob(pattern) if recursive else p.glob(pattern)
    return sorted(iterator)


def delete_path(path: str, missing_ok: bool = True) -> bool:
    p = Path(path)
    try:
        if p.is_dir():
            shutil.rmtree(p)
        elif p.is_file():
            p.unlink()
        return True
    except FileNotFoundError:
        if not missing_ok:
            raise
        return False
    except Exception:
        return False
