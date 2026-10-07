"""Heading-aware deterministic Markdown chunking."""

import hashlib
import re

from geoops_api.knowledge.models import IndexedKnowledgeChunk, SourceDocument


class MarkdownChunker:
    """Keep related paragraphs and their nearest heading together."""

    _HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(self, *, maximum_characters: int = 900, overlap_characters: int = 120) -> None:
        if maximum_characters < 200:
            raise ValueError("maximum_characters must be at least 200")
        if overlap_characters >= maximum_characters:
            raise ValueError("overlap_characters must be smaller than maximum_characters")
        self._maximum_characters = maximum_characters
        self._overlap_characters = overlap_characters

    def chunk(self, document: SourceDocument) -> list[IndexedKnowledgeChunk]:
        chunks: list[IndexedKnowledgeChunk] = []
        section = "Document"
        paragraphs: list[str] = []
        for block in re.split(r"\n\s*\n", document.content):
            cleaned = block.strip()
            heading = self._HEADING_PATTERN.match(cleaned)
            if heading:
                chunks.extend(self._flush(document, section, paragraphs, len(chunks)))
                paragraphs = []
                section = heading.group(2).strip()
            elif cleaned:
                paragraphs.append(cleaned)
        chunks.extend(self._flush(document, section, paragraphs, len(chunks)))
        return chunks

    def _flush(
        self,
        document: SourceDocument,
        section: str,
        paragraphs: list[str],
        starting_index: int,
    ) -> list[IndexedKnowledgeChunk]:
        if not paragraphs:
            return []
        groups: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > self._maximum_characters:
                groups.append(current)
                overlap = current[-self._overlap_characters :].lstrip()
                current = f"{overlap}\n\n{paragraph}" if overlap else paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current:
            groups.append(current)

        output: list[IndexedKnowledgeChunk] = []
        for offset, text in enumerate(groups):
            identity = f"{document.document_id}:{starting_index + offset}:{section}:{text}"
            suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
            output.append(
                IndexedKnowledgeChunk(
                    chunk_id=f"{document.document_id}:{suffix}",
                    document_id=document.document_id,
                    title=document.title,
                    document_type=document.document_type,
                    version=document.version,
                    effective_date=document.effective_date,
                    customer_id=document.customer_id,
                    equipment_type=document.equipment_type,
                    storage_uri=document.storage_uri,
                    section=section,
                    text=text,
                    embedding=[],
                    metadata=document.metadata,
                )
            )
        return output
