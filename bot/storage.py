from __future__ import annotations

import json
from pathlib import Path


class AuthorizedChatsStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(set())

    def _read(self) -> set[int]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return set()

        chat_ids = raw.get("authorized_chat_ids", [])
        return {int(chat_id) for chat_id in chat_ids}

    def _write(self, chat_ids: set[int]) -> None:
        payload = {"authorized_chat_ids": sorted(chat_ids)}
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def is_authorized(self, chat_id: int) -> bool:
        return chat_id in self._read()

    def add_chat(self, chat_id: int) -> None:
        current = self._read()
        current.add(chat_id)
        self._write(current)
