"""Cloud-Storage-compatible document boundary with a local filesystem adapter."""

from datetime import date
from pathlib import Path
from typing import Any

from geoops_api.knowledge.models import DocumentType, SourceDocument


class DocumentFormatError(ValueError):
    """Raised when a source document has invalid or incomplete front matter."""


class FilesystemDocumentStorage:
    """Read UTF-8 Markdown originals from a bounded local directory."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def list_documents(self) -> list[SourceDocument]:
        if not self._root.is_dir():
            raise FileNotFoundError(f"Knowledge document directory not found: {self._root}")
        documents = [self._read_document(path) for path in sorted(self._root.rglob("*.md"))]
        identifiers = [document.document_id for document in documents]
        if len(identifiers) != len(set(identifiers)):
            raise DocumentFormatError("Knowledge document IDs must be unique")
        return documents

    def _read_document(self, path: Path) -> SourceDocument:
        resolved = path.resolve()
        if self._root not in resolved.parents:
            raise DocumentFormatError(f"Document escapes configured root: {path}")
        metadata, content = self._parse_front_matter(resolved.read_text(encoding="utf-8"), path)
        required = {"document_id", "title", "document_type", "version"}
        missing = sorted(required - metadata.keys())
        if missing:
            raise DocumentFormatError(f"{path} is missing required metadata: {', '.join(missing)}")
        known = required | {"effective_date", "customer_id", "equipment_type"}
        extra: dict[str, Any] = {key: value for key, value in metadata.items() if key not in known}
        effective_date = metadata.get("effective_date")
        try:
            return SourceDocument(
                document_id=metadata["document_id"],
                title=metadata["title"],
                document_type=DocumentType(metadata["document_type"]),
                version=metadata["version"],
                effective_date=(date.fromisoformat(effective_date) if effective_date else None),
                customer_id=metadata.get("customer_id"),
                equipment_type=metadata.get("equipment_type"),
                storage_uri=resolved.relative_to(self._root).as_posix(),
                content=content,
                metadata=extra,
            )
        except ValueError as error:
            raise DocumentFormatError(f"Invalid metadata in {path}: {error}") from error

    @staticmethod
    def _parse_front_matter(text: str, path: Path) -> tuple[dict[str, str], str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise DocumentFormatError(f"{path} must start with Markdown front matter")
        try:
            closing_index = lines[1:].index("---") + 1
        except ValueError as error:
            raise DocumentFormatError(f"{path} has unterminated front matter") from error
        metadata: dict[str, str] = {}
        for line in lines[1:closing_index]:
            key, separator, value = line.partition(":")
            if not separator or not key.strip() or not value.strip():
                raise DocumentFormatError(f"Invalid front-matter line in {path}: {line!r}")
            metadata[key.strip()] = value.strip()
        content = "\n".join(lines[closing_index + 1 :]).strip()
        if not content:
            raise DocumentFormatError(f"{path} does not contain document text")
        return metadata, content
