from dataclasses import dataclass
from typing import Dict, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class SummarizerConfig:
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    max_history_chars: int = 12000
    chunk_chars: int = 3500
    max_new_tokens: int = 180
    fallback_summary: str = (
        "I found earlier memories for this person, but I could not summarize them right now."
    )


class ConversationSummarizer:
    def __init__(self, config: Optional[SummarizerConfig] = None):
        self.config = config or SummarizerConfig()
        self.device = self._resolve_device(self.config.device)
        self.tokenizer = None
        self.model = None
        self._generation_error = None

    def _resolve_device(self, requested: str) -> str:
        requested = (requested or "cpu").lower()
        if requested == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "mps":
            return "mps" if torch.backends.mps.is_available() else "cpu"
        return "cpu"

    def _ensure_models(self) -> None:
        if self.tokenizer is not None and self.model is not None:
            return
        if self._generation_error is not None:
            raise RuntimeError(
                f"Summarization model unavailable: {self._generation_error}"
            ) from self._generation_error

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )
            model_dtype = torch.float16 if self.device == "cuda" else torch.float32
            device_map = "auto" if self.device == "cuda" else None
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                trust_remote_code=True,
                torch_dtype=model_dtype,
                device_map=device_map
            )
            if self.device in ("cpu", "mps"):
                self.model.to(self.device)
        except Exception as exc:
            self._generation_error = exc
            raise RuntimeError(
                f"Summarization model unavailable: {exc}"
            ) from exc

    def _model_device(self):
        if self.model is None:
            return self.device
        return next(self.model.parameters()).device

    def summarize(self, entries: List[Dict]) -> str:
        if not entries:
            return "No prior memories are stored for this user yet."

        chunks = self._chunk_entries(entries)
        if not chunks:
            return "No prior memories are stored for this user yet."

        if len(chunks) == 1:
            summary = self._generate_summary(
                chunks[0],
                detail_instruction=(
                    "Summarize the full conversation history in 3 to 5 natural sentences."
                ),
            )
            cleaned_summary = self._clean_summary(summary)
            return cleaned_summary or self.config.fallback_summary

        partial_summaries: List[str] = []
        for index, chunk in enumerate(chunks, start=1):
            partial_summary = self._generate_summary(
                chunk,
                detail_instruction=(
                    f"This is part {index} of {len(chunks)} from a longer history. "
                    "Summarize the important points from this part in 2 or 3 plain-English sentences."
                ),
            )
            cleaned_partial = self._clean_summary(partial_summary)
            if cleaned_partial:
                partial_summaries.append(
                    f"Part {index} summary: {cleaned_partial}"
                )

        if not partial_summaries:
            return self.config.fallback_summary

        final_summary = self._generate_summary(
            "\n".join(partial_summaries),
            detail_instruction=(
                "Combine these partial summaries into one warm, patient-friendly overview of the full history. "
                "Return 3 to 5 natural sentences."
            ),
        )
        cleaned_summary = self._clean_summary(final_summary)
        return cleaned_summary or self.config.fallback_summary

    def _generate_summary(self, history_text: str, detail_instruction: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You summarize remembered conversations for an Alzheimer's support app. "
                    "Write in plain, warm English for the patient. "
                    "Use only the stored conversation history provided by the user. "
                    "Do not invent facts, dates, names, or emotions that are not clearly present. "
                    "Avoid bullet points, keyword lists, fragments, or quoting raw lines. "
                    "Write natural prose only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Please summarize the conversation history below in a patient-friendly way. "
                    "Mention recurring themes, important recent updates, and anything that seems emotionally significant. "
                    f"{detail_instruction}\n\n"
                    f"CONVERSATION HISTORY:\n{history_text}"
                ),
            },
        ]

        try:
            self._ensure_models()
            input_ids = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt",
                add_generation_prompt=True
            ).to(self._model_device())

            output = self.model.generate(
                input_ids=input_ids,
                max_new_tokens=self.config.max_new_tokens,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )

            new_tokens = output[0][input_ids.shape[1]:]
            return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        except Exception:
            return ""

    def _chunk_entries(self, entries: List[Dict]) -> List[str]:
        lines: List[str] = []
        for index, entry in enumerate(entries, start=1):
            text = " ".join(str(entry.get("text", "")).split())
            if not text:
                continue
            timestamp = entry.get("timestamp", "unknown time")
            source = entry.get("source", "memory")
            lines.append(f"{index}. [{timestamp}] ({source}) {text}")

        if not lines:
            return []

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1
            if current_chunk and current_size + line_size > self.config.chunk_chars:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(line)
            current_size += line_size

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        if len(chunks) == 1 and len(chunks[0]) <= self.config.max_history_chars:
            return chunks

        merged_chunks: List[str] = []
        current_merged: List[str] = []
        current_merged_size = 0
        for chunk in chunks:
            chunk_size = len(chunk) + 2
            if current_merged and current_merged_size + chunk_size > self.config.max_history_chars:
                merged_chunks.append("\n\n".join(current_merged))
                current_merged = []
                current_merged_size = 0
            current_merged.append(chunk)
            current_merged_size += chunk_size
        if current_merged:
            merged_chunks.append("\n\n".join(current_merged))

        return merged_chunks

    def _clean_summary(self, text: str) -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return ""

        prefixes = (
            "Summary:",
            "summary:",
            "Assistant:",
            "assistant:",
            "[CONTEXT]",
        )
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned
