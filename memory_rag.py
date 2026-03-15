"""
MEMORA - RAG Memory System
Vector DB: Chroma
Embedding: bge-base-en-v1.5
LLM: Qwen2.5-3B-Instruct (local)

Goal:
- Store memory entries with metadata
- Retrieve relevant memories
- Generate safe, non-hallucinated responses
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import time
import json
from pathlib import Path
import torch
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM

# =========================
# CONFIG
# =========================

@dataclass
class RAGConfig:
    persist_dir: str = "./chroma_memory_db"
    collection_name: str = "memories"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    #llm_model: str = "Qwen/Qwen2.5-3B-Instruct"
    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    top_k: int = 5
    min_similarity: float = 0.55
    max_context_chars: int = 2000
    fallback_response: str = "I am here with you. Please take your time."
    conversation_log_dir: str = "./conversation_logs"
    system_prompt: str = (
        "You are a memory assistant for Alzheimer's patients.\n"
        "Use ONLY the provided memory context.\n"
        "If the answer is not in the context, reply exactly with: \"{fallback_response}\".\n"
        "Do NOT add new facts, dates, times, or opinions.\n"
        "Answer in ONE short sentence.\n"
        "Do NOT ask questions."
    )


# =========================
# MEMORY SCHEMA
# =========================

@dataclass
class MemoryItem:
    user_id: str
    text: str
    relationship: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[str] = None
    importance: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None


# =========================
# RAG SYSTEM
# =========================

class MemoryRAG:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.device = self._resolve_device(self.config.device)
        self._conversation_dir = Path(self.config.conversation_log_dir)
        self.client = None
        self.collection = None
        self.embedder = None
        self.tokenizer = None
        self.model = None
        self._collection_error = None
        self._embedder_error = None
        self._generation_error = None

    def _resolve_device(self, requested: str) -> str:
        requested = (requested or "cpu").lower()
        if requested == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "mps":
            return "mps" if torch.backends.mps.is_available() else "cpu"
        return "cpu"

    def _ensure_collection(self) -> None:
        if self.collection is not None:
            return
        if self._collection_error is not None:
            raise RuntimeError(f"Memory store unavailable: {self._collection_error}") from self._collection_error

        try:
            self.client = chromadb.PersistentClient(path=self.config.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as exc:
            self._collection_error = exc
            raise RuntimeError(f"Memory store unavailable: {exc}") from exc

    def _ensure_embedder(self) -> None:
        if self.embedder is not None:
            return
        if self._embedder_error is not None:
            raise RuntimeError(f"Embedding model unavailable: {self._embedder_error}") from self._embedder_error

        try:
            self.embedder = SentenceTransformer(self.config.embedding_model, device=self.device)
        except Exception as exc:
            self._embedder_error = exc
            raise RuntimeError(f"Embedding model unavailable: {exc}") from exc

    def _ensure_generation_models(self) -> None:
        if self.tokenizer is not None and self.model is not None:
            return
        if self._generation_error is not None:
            raise RuntimeError(f"Generation model unavailable: {self._generation_error}") from self._generation_error

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.llm_model, trust_remote_code=True)
            llm_dtype = torch.float16 if self.device == "cuda" else torch.float32
            llm_device_map = "auto" if self.device == "cuda" else None
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.llm_model,
                trust_remote_code=True,
                torch_dtype=llm_dtype,
                device_map=llm_device_map
            )
            if self.device in ("cpu", "mps"):
                self.model.to(self.device)
        except Exception as exc:
            self._generation_error = exc
            raise RuntimeError(f"Generation model unavailable: {exc}") from exc

    def _model_device(self):
        if self.model is None:
            return self.device
        return next(self.model.parameters()).device

    # =========================
    # MEMORY STORAGE
    # =========================
    def add_memories(self, memories: List[MemoryItem]) -> List[str]:
        if not memories:
            return []

        self._ensure_collection()
        self._ensure_embedder()
        texts = [m.text for m in memories]
        embeddings = self.embedder.encode(texts, normalize_embeddings=True)

        # Stable IDs to prevent duplicates
        ids = [f"{m.user_id}::{m.text}" for m in memories]
        metadatas = [self._memory_to_metadata(m) for m in memories]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        return ids

    def _memory_to_metadata(self, m: MemoryItem) -> Dict[str, Any]:
        data = asdict(m)

        # Ensure timestamp
        if data["timestamp"] is None:
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Chroma does not allow lists in metadata
        if data["tags"] is None:
            data["tags"] = ""
        elif isinstance(data["tags"], list):
            data["tags"] = ", ".join(data["tags"])

        # Remove None values (Chroma disallows None)
        clean = {k: v for k, v in data.items() if v is not None}

        return clean

    # =========================
    # RETRIEVAL
    # =========================
    def retrieve(self, query: str, user_id: Optional[str] = None) -> List[Dict]:
        self._ensure_collection()
        self._ensure_embedder()
        query_emb = self.embedder.encode([query], normalize_embeddings=True)[0]

        where = {"user_id": user_id} if user_id else None

        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=self.config.top_k,
            where=where
        )

        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            similarity = 1 - dist
            if similarity >= self.config.min_similarity:
                retrieved.append({
                    "text": doc,
                    "metadata": meta,
                    "similarity": similarity
                })

        return retrieved

    # =========================
    # CONTEXT BUILDER
    # =========================
    def build_context(self, retrieved: List[Dict]) -> str:
        if not retrieved:
            return ""

        blocks = []
        total_len = 0
        for item in retrieved:
            meta = item["metadata"]
            block = (
                f"[Memory]\n"
                f"Text: {item['text']}\n"
                f"Relationship: {meta.get('relationship')}\n"
                f"Event: {meta.get('event_type')}\n"
                f"Importance: {meta.get('importance')}\n"
            )
            if total_len + len(block) > self.config.max_context_chars:
                break
            blocks.append(block)
            total_len += len(block)

        return "\n".join(blocks)

    # =========================
    # RESPONSE GENERATION
    # =========================
    def generate_response(self, query: str, user_id: Optional[str] = None) -> Dict:
        try:
            retrieved = self.retrieve(query, user_id=user_id)
            context = self.build_context(retrieved)
        except Exception as exc:
            return {
                "response": self.config.fallback_response,
                "retrieved": [],
                "used_fallback": True,
                "error": str(exc)
            }

        if not context:
            return {
                "response": self.config.fallback_response,
                "retrieved": retrieved,
                "used_fallback": True
            }

        system_prompt = self.config.system_prompt.format(
            fallback_response=self.config.fallback_response
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"MEMORY CONTEXT:\n{context}\n\nQUESTION: {query}\n\nReturn ONE short sentence only."}
        ]

        try:
            self._ensure_generation_models()
            input_ids = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt",
                add_generation_prompt=True
            ).to(self._model_device())

            output = self.model.generate(
                input_ids=input_ids,
                max_new_tokens=40,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )

            new_tokens = output[0][input_ids.shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

            if not response:
                response = self.config.fallback_response
        except Exception as exc:
            return {
                "response": self.config.fallback_response,
                "retrieved": retrieved,
                "used_fallback": True,
                "error": str(exc)
            }

        used_fallback = response.strip() == self.config.fallback_response

        return {
            "response": response,
            "retrieved": retrieved,
            "used_fallback": used_fallback
        }

    def get_user_memory_count(self, user_id: str) -> int:
        self._ensure_collection()
        result = self.collection.get(where={"user_id": user_id}, include=[])
        return len(result.get("ids", []))

    def delete_memories_for_user(self, user_id: str) -> int:
        self._ensure_collection()
        result = self.collection.get(where={"user_id": user_id}, include=[])
        memory_ids = result.get("ids", [])
        if not memory_ids:
            return 0
        self.collection.delete(ids=memory_ids)
        return len(memory_ids)

    # =========================
    # CONVERSATION LOGGING (separate from memory retrieval)
    # =========================
    def _conversation_log_path(self, user_id: str) -> Path:
        safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in (user_id or "unknown"))
        safe = safe[:100] if safe else "unknown"
        return self._conversation_dir / f"{safe}.jsonl"

    def store_conversation(
        self,
        user_id: str,
        question: str,
        answer: str,
        *,
        used_fallback: bool,
        retrieved: Optional[List[Dict[str, Any]]] = None
    ) -> Path:
        record: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "used_fallback": used_fallback
        }
        if retrieved is not None:
            record["retrieved"] = [
                {
                    "text": r.get("text"),
                    "similarity": r.get("similarity"),
                    "metadata": r.get("metadata", {})
                }
                for r in retrieved
            ]

        path = self._conversation_log_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        path = self._conversation_log_path(user_id)
        if not path.exists() or limit <= 0:
            return []

        entries: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return entries[-limit:]

    def list_conversation_users(self) -> List[str]:
        if not self._conversation_dir.exists():
            return []
        return sorted(path.stem for path in self._conversation_dir.glob("*.jsonl"))

    def delete_conversation_history(self, user_id: str) -> bool:
        path = self._conversation_log_path(user_id)
        if not path.exists():
            return False
        path.unlink()
        return True


# =========================
# Example Usage
# =========================
if __name__ == "__main__":
    rag = MemoryRAG()

    # Add memory
    rag.add_memories([
        MemoryItem(
            user_id="patient_001",
            text="Your daughter Ananya visited you last Sunday.",
            relationship="daughter",
            event_type="family_visit",
            importance="high"
        )
    ])

    # Ask question
    result = rag.generate_response("Did my daughter visit me recently?", user_id="patient_001")
    print(json.dumps(result, indent=2))
