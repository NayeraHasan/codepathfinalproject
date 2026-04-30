"""Keyword-based Retrieval-Augmented Generation system using local pet care documents."""

import os
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Loads pet care markdown docs and retrieves relevant chunks by keyword overlap."""

    def __init__(self, knowledge_dir: str = "knowledge_base"):
        self.knowledge_dir = knowledge_dir
        self.documents: List[dict] = []
        self._load_documents()

    def _load_documents(self) -> None:
        """Load all .md and .txt files from the knowledge base directory."""
        if not os.path.exists(self.knowledge_dir):
            logger.warning("Knowledge base directory '%s' not found.", self.knowledge_dir)
            return
        for filename in sorted(os.listdir(self.knowledge_dir)):
            if not filename.endswith((".md", ".txt")):
                continue
            path = os.path.join(self.knowledge_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.documents.append({
                    "filename": filename,
                    "content": content,
                    "chunks": self._chunk_text(content),
                })
                logger.info("Loaded knowledge base file: %s", filename)
            except OSError as e:
                logger.error("Could not load %s: %s", filename, e)

    def _chunk_text(self, text: str, max_chars: int = 600) -> List[str]:
        """Split text into paragraph-sized chunks, merging short ones."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_chars:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, str, float]]:
        """Return top_k (source, chunk, score) tuples ranked by keyword overlap."""
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        scored: List[Tuple[str, str, float]] = []
        for doc in self.documents:
            for chunk in doc["chunks"]:
                chunk_words = set(re.findall(r"\b\w+\b", chunk.lower()))
                overlap = len(query_words & chunk_words)
                if overlap:
                    score = overlap / (len(query_words) + 1)
                    scored.append((doc["filename"], chunk, score))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def format_context(self, query: str) -> str:
        """Retrieve and concatenate relevant chunks as a formatted context string."""
        results = self.retrieve(query)
        if not results:
            return ""
        parts = [f"[Source: {src}]\n{chunk}" for src, chunk, _ in results]
        return "\n\n---\n\n".join(parts)
