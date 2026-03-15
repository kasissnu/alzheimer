import json
import time
from pathlib import Path
from typing import Dict, List


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

    def get_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        path = self._history_path(user_id)
        if not path.exists() or limit <= 0:
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

        return entries[-limit:]

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
