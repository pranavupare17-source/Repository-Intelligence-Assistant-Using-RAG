"""
Hand-rolled FAISS Vector Store using IndexFlatIP.
Stores L2-normalized embeddings for exact Cosine Similarity search.
Maintains a 1-to-1 mapping with CodeChunk metadata and handles serialization.

Zero LangChain/LlamaIndex dependencies.
"""
import json
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import faiss

from src.core.models import CodeChunk
from src.indexing.embedder import normalize_vectors


class FAISSVectorStore:
    """
    Direct wrapper around FAISS IndexFlatIP.
    
    Academic Rationale:
    Instead of using high-level vector database abstractions (e.g. LangChain's FAISS wrapper),
    this class exposes raw FAISS operations:
    - Direct instantiation of faiss.IndexFlatIP(d)
    - Manual matrix alignment and validation
    - Direct chunk-ID-to-vector pointer tracking
    - Serialization via native faiss.write_index and JSON metadata
    """
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: List[CodeChunk] = []

    @property
    def total_vectors(self) -> int:
        """Returns the number of indexed code chunks."""
        return self.index.ntotal

    def add_chunks(self, chunks: List[CodeChunk], embeddings: np.ndarray) -> None:
        """
        Adds code chunks and their corresponding embedding vectors to the FAISS index.
        
        Args:
            chunks: List of CodeChunk objects.
            embeddings: (N, D) numpy array of embedding vectors.
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks provided but embeddings has {embeddings.shape[0]} rows."
            )

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} does not match index dimension {self.dimension}."
            )

        # Enforce L2 normalization so that Inner Product = Cosine Similarity
        normalized_embs = normalize_vectors(embeddings.astype(np.float32))

        # Add to FAISS index
        self.index.add(normalized_embs)
        self.chunks.extend(chunks)

    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[CodeChunk, float]]:
        """
        Performs exact nearest-neighbor cosine similarity search.
        
        Args:
            query_vector: (D,) or (1, D) numpy array.
            k: Number of nearest chunks to retrieve.
            
        Returns:
            List of (CodeChunk, cosine_similarity_score) sorted in descending order of relevance.
        """
        if self.total_vectors == 0:
            return []

        # Ensure (1, D) shape and float32 type
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        query_normalized = normalize_vectors(query_vector.astype(np.float32))

        # FAISS search: returns top-k scores (cosine similarities) and vector indices
        actual_k = min(k, self.total_vectors)
        scores, indices = self.index.search(query_normalized, actual_k)

        results: List[Tuple[CodeChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx]
            results.append((chunk, float(score)))

        return results

    def save(self, directory: str | Path) -> None:
        """Serializes the FAISS index binary and chunk metadata to disk."""
        dir_path = Path(directory).resolve()
        dir_path.mkdir(parents=True, exist_ok=True)

        index_file = dir_path / "index.faiss"
        metadata_file = dir_path / "chunks.json"

        # Write native FAISS binary index
        faiss.write_index(self.index, str(index_file))

        # Write chunk metadata as structured JSON
        chunks_data = {
            "dimension": self.dimension,
            "total_chunks": len(self.chunks),
            "chunks": [c.to_dict() for c in self.chunks],
        }
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

    @classmethod
    def load(cls, directory: str | Path) -> "FAISSVectorStore":
        """Loads a persisted FAISS index and chunk metadata from disk."""
        dir_path = Path(directory).resolve()
        index_file = dir_path / "index.faiss"
        metadata_file = dir_path / "chunks.json"

        if not index_file.exists() or not metadata_file.exists():
            raise FileNotFoundError(f"FAISS index files not found in {dir_path}")

        with open(metadata_file, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        dimension = chunks_data["dimension"]
        instance = cls(dimension=dimension)

        # Read native FAISS index
        instance.index = faiss.read_index(str(index_file))

        # Rebuild CodeChunk objects
        instance.chunks = [CodeChunk.from_dict(c) for c in chunks_data["chunks"]]

        return instance
