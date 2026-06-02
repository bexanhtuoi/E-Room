from __future__ import annotations

import json
import os
from pathlib import Path

from app.log import get_logger

logger = get_logger(__name__)


class CMUDictionary:
    _dict: dict[str, list[str]] = {}

    def __init__(self) -> None:
        if CMUDictionary._dict:
            return
        local = Path(__file__).parent / "cmudict.json"
        if local.exists():
            with open(local) as f:
                CMUDictionary._dict = json.load(f)
            logger.info("Đã tải CMUdict từ file local",
                extra={"entries": len(self._dict)})
            return
        logger.info("Bắt đầu tải CMUdict...")
        import urllib.request

        url = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
        raw = urllib.request.urlopen(url).read().decode("latin-1")
        for line in raw.splitlines():
            parts = line.strip().split()
            if parts:
                word = parts[0].lower().rstrip("(0123456789)")
                phones = [p.rstrip("0123456789") for p in parts[1:]]
                if word and phones:
                    CMUDictionary._dict[word] = phones
        with open(local, "w") as f:
            json.dump(CMUDictionary._dict, f)
        logger.info("Tải CMUdict hoàn tất",
            extra={"entries": len(self._dict)})

    def lookup(self, word: str) -> list[str]:
        phones = self._dict.get(word)
        if phones is None:
            logger.debug("CMUdict: từ '%s' không tìm thấy", word)
        return phones or []
