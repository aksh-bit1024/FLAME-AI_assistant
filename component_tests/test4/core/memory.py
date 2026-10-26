import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

class MemoryManager:
    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = Path(__file__).resolve().parent.parent / "memory.json"
        self.storage_path = Path(storage_path)
        self._lock = RLock()
        self._init_storage()

    def _init_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_data({"preferences": {}})

    def _read_data(self) -> dict[str, Any]:
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {"preferences": {}}
        if not isinstance(data, dict) or not isinstance(data.get("preferences"), dict):
            return {"preferences": {}}
        return data

    def _write_data(self, data: dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(
            dir=self.storage_path.parent, prefix=f".{self.storage_path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.storage_path)
        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def get_all_preferences(self) -> dict:
        with self._lock:
            return dict(self._read_data()["preferences"])

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.get_all_preferences().get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._read_data()
            data["preferences"][key] = value
            self._write_data(data)

    def save_memory(self, key: str, value: Any) -> None:
        self.set_preference(key, value)

    def delete_preference(self, key: str) -> bool:
        with self._lock:
            data = self._read_data()
            existed = key in data["preferences"]
            data["preferences"].pop(key, None)
            if existed:
                self._write_data(data)
            return existed

    def trim_history(self, history: list, max_messages: int = 10) -> list:
        """
        Trims history while preserving index 0 (system prompt) and
        preventing orphaned 'tool' role messages at the trim boundary.
        """
        if max_messages < 0:
            raise ValueError("max_messages must be non-negative")

        system_msg = history[0] if history and self._role(history[0]) == "system" else None
        if max_messages == 0:
            return [system_msg] if system_msg else []

        if len(history) <= max_messages + 1:
            return history

        recent = history[-max_messages:]

        # Do not send tool results without the assistant tool-call request.
        while recent and self._role(recent[0]) == "tool":
            recent.pop(0)
        if recent and self._role(recent[0]) == "assistant" and self._has_tool_calls(recent[0]):
            recent.pop(0)
            while recent and self._role(recent[0]) == "tool":
                recent.pop(0)

        if system_msg:
            return [system_msg] + recent
        return recent

    @staticmethod
    def _role(message: Any) -> str | None:
        return message.get("role") if isinstance(message, dict) else getattr(message, "role", None)

    @staticmethod
    def _has_tool_calls(message: Any) -> bool:
        calls = message.get("tool_calls") if isinstance(message, dict) else getattr(message, "tool_calls", None)
        return bool(calls)