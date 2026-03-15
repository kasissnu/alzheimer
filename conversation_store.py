import json
import time
from pathlib import Path
from typing import Dict, List, Optional


class ConversationStore:
    def __init__(self, base_dir: str = "./conversation_logs"):
        self.base_dir = Path(base_dir)

    def _history_path(self, user_id: str) -> Path:
        safe_user_id = "".join(
            char if (char.isalnum() or char in ("-", "_")) else "_"
            for char in (user_id or "unknown")
        )
        safe_user_id = safe_user_id[:100] if safe_user_id else "unknown"
        return self.base_dir / f"{safe_user_id}.jsonl"

    def store_utterance(self, user_id: str, text: str, source: str) -> Path:
        path = self._history_path(user_id)
        cleaned_text = text.strip()
        if not cleaned_text:
            return path

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "text": cleaned_text,
            "source": source,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def get_history(self, user_id: str, limit: Optional[int] = 20) -> List[Dict]:
        path = self._history_path(user_id)
        if not path.exists():
            return []
        if limit is not None and limit <= 0:
            return []

        entries: List[Dict] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if limit is None:
            return entries
        return entries[-limit:]

    def format_entries_for_summary(
        self,
        entries: List[Dict],
        max_chars: Optional[int] = None
    ) -> str:
        formatted_entries: List[str] = []
        for index, entry in enumerate(entries, start=1):
            text = " ".join(str(entry.get("text", "")).split())
            if not text:
                continue

            timestamp = entry.get("timestamp", "unknown time")
            source = entry.get("source", "memory")
            formatted_entries.append(
                f"{index}. [{timestamp}] ({source}) {text}"
            )

        history_text = "\n".join(formatted_entries)
        if max_chars is not None and max_chars > 0 and len(history_text) > max_chars:
            return history_text[-max_chars:]
        return history_text

    def format_history_for_summary(
        self,
        user_id: str,
        max_chars: Optional[int] = None
    ) -> str:
        return self.format_entries_for_summary(
            self.get_history(user_id, limit=None),
            max_chars=max_chars
        )

    def list_users(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        return sorted(path.stem for path in self.base_dir.glob("*.jsonl"))

    def delete_history(self, user_id: str) -> bool:
        path = self._history_path(user_id)
        if not path.exists():
            return False
        path.unlink()
        return True
