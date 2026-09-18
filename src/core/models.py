"""
Core data structures for code chunking and retrieval.
Built strictly from scratch with zero framework abstractions.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import hashlib


@dataclass
class CodeChunk:
    """
    Represents an atomic semantic code unit extracted via AST analysis.
    
    Attributes:
        chunk_id: Deterministic SHA-256 hash identifying this chunk.
        file_path: Relative path to the source file from the repository root.
        start_line: 1-indexed starting line in the source file.
        end_line: 1-indexed ending line in the source file.
        chunk_type: 'function', 'method', or 'class'.
        name: Name of the symbol (e.g. 'generate_token' or 'AuthManager').
        parent_class: Name of enclosing class if chunk is a method, else None.
        docstring: Extracted docstring if present in the AST, else None.
        code: The exact raw source code of the chunk.
        context_header: Synthetic header embedding context (file path, class, signature).
        metadata: Extensible dictionary for decorators, arguments, dependencies, etc.
    """
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: str
    parent_class: Optional[str] = None
    docstring: Optional[str] = None
    code: str = ""
    context_header: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        file_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
        name: str,
        parent_class: Optional[str] = None,
        docstring: Optional[str] = None,
        code: str = "",
        context_header: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CodeChunk":
        """Factory method computing a deterministic chunk_id from attributes."""
        hash_input = f"{file_path}:{start_line}:{end_line}:{parent_class or ''}:{name}"
        chunk_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
        
        # Build synthetic context header if not provided
        if not context_header:
            header_parts = [f"File: {file_path}"]
            if parent_class:
                header_parts.append(f"Class: {parent_class}")
            header_parts.append(f"{chunk_type.capitalize()}: {name}")
            if docstring:
                header_parts.append(f"Docstring: {docstring.strip()}")
            context_header = " | ".join(header_parts)

        return cls(
            chunk_id=chunk_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            chunk_type=chunk_type,
            name=name,
            parent_class=parent_class,
            docstring=docstring,
            code=code,
            context_header=context_header,
            metadata=metadata or {},
        )

    @property
    def citation(self) -> str:
        """Returns academic ground-truth citation in exact [file:start-end] format."""
        return f"[{self.file_path}:{self.start_line}-{self.end_line}]"

    def get_embedding_text(self) -> str:
        """
        Constructs the text payload for vector embedding.
        
        Academic rationale:
        Embedding source code alone often fails because functions have isolated names
        without module or class context. Prepending the structured context header
        and docstring provides rich semantic grounding for cosine retrieval.
        """
        parts = [
            f"### Context: {self.context_header}",
        ]
        if self.docstring:
            parts.append(f"### Documentation: {self.docstring.strip()}")
        parts.append(f"### Source Code ({self.file_path}):\n{self.code.strip()}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes chunk to dictionary for index persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeChunk":
        """Deserializes dictionary back into a CodeChunk instance."""
        return cls(**data)


@dataclass
class SearchResult:
    """Represents a ranked semantic search hit."""
    chunk: CodeChunk
    score: float
    rank: int

    @property
    def citation(self) -> str:
        return self.chunk.citation
