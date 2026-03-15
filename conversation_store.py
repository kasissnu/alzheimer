import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "i", "in", "is", "it", "its",
    "me", "my", "of", "on", "or", "our", "she", "that", "the", "their",
    "them", "there", "they", "this", "to", "was", "we", "were", "with",
    "you", "your",
}


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

    def summarize_history(self, user_id: str) -> str:
        entries = self.get_history(user_id, limit=None)
        if not entries:
            return "No prior conversations stored for this user."

        oldest_timestamp = entries[0].get("timestamp", "unknown")
        newest_timestamp = entries[-1].get("timestamp", "unknown")
        topics = self._extract_topics(entries)
        recent_points = self._recent_points(entries, count=3)

        parts = [
            f"There are {len(entries)} stored memories from {oldest_timestamp} to {newest_timestamp}."
        ]
        if topics:
            parts.append(f"Main topics include {', '.join(topics)}.")
        if recent_points:
            parts.append(f"Recent memories mention {recent_points}.")

        return " ".join(parts)

    def _extract_topics(self, entries: List[Dict], limit: int = 5) -> List[str]:
        words = Counter()
        for entry in entries:
            text = entry.get("text", "").lower()
            for token in re.findall(r"[a-zA-Z']+", text):
                if len(token) <= 3 or token in STOPWORDS:
                    continue
                words[token] += 1
        return [word for word, _count in words.most_common(limit)]

    def _recent_points(self, entries: List[Dict], count: int = 3) -> str:
        recent_texts = []
        for entry in entries[-count:]:
            text = " ".join(entry.get("text", "").split())
            if not text:
                continue
            if len(text) > 80:
                text = text[:77].rstrip() + "..."
            recent_texts.append(text)
        return "; ".join(recent_texts)

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
