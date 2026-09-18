"""
Plain Python semantic retrieval engine.
Combines L2-normalized FAISS IndexFlatIP dense cosine retrieval with
AST symbol boosting for superior code search performance over standard RAG.

Zero framework abstractions (No LangChain, LlamaIndex, or Haystack).
"""
import re
from pathlib import Path
from typing import List, Optional
import numpy as np

from src.core.models import CodeChunk, SearchResult
from src.core.file_walker import RepoWalker
from src.chunking.ast_chunker import ASTChunker
from src.indexing.embedder import BaseEmbedder, get_embedder
from src.indexing.vector_store import FAISSVectorStore


def semantic_search(
    query: str,
    vector_store: FAISSVectorStore,
    embedder: BaseEmbedder,
    k: int = 5,
    boost_ast_symbols: bool = True,
    symbol_boost_weight: float = 0.15,
) -> List[SearchResult]:
    """
    Executes a query-adaptive semantic search over the codebase.
    
    Academic Rationale & Algorithmic Advantages:
    1. Vector Cosine Matching:
       The natural language query is mapped into embedding space and normalized.
       FAISS computes the dense inner product (cosine similarity) against all
       pre-normalized chunk vectors (context header + docstring + source code).
       
    2. AST Symbol Prioritization (Advancement over naive RAG):
       Standard text RAG treats all tokens uniformly. In codebases, developers
       frequently query using symbol names (e.g. "how does verify_token handle expiry?").
       When a query explicitly contains an AST symbol or parent class name, we apply
       a principled lexical-semantic boost. This solves the classic 'vocabulary mismatch'
       problem without requiring complex external sparse engines.
    """
    if vector_store.total_vectors == 0:
        return []

    # 1. Embed query
    query_vector = embedder.embed_text(query)

    # 2. Retrieve top candidates via FAISS cosine similarity
    candidate_k = min(k * 2 if boost_ast_symbols else k, vector_store.total_vectors)
    raw_hits = vector_store.search(query_vector=query_vector, k=candidate_k)

    if not raw_hits:
        return []

    # 3. Optional AST Symbol Alignment Boosting
    query_tokens = set(re.findall(r"\b[a-zA-Z_0-9]+\b", query.lower()))
    
    ranked_candidates = []
    for chunk, cosine_score in raw_hits:
        final_score = cosine_score
        
        if boost_ast_symbols:
            symbol_matched = False
            # Check symbol name match
            if chunk.name.lower() in query_tokens:
                symbol_matched = True
            # Check parent class match
            if chunk.parent_class and chunk.parent_class.lower() in query_tokens:
                symbol_matched = True

            if symbol_matched:
                final_score += symbol_boost_weight

        ranked_candidates.append((chunk, final_score))

    # Re-sort if boosting changed ranks
    ranked_candidates.sort(key=lambda x: x[1], reverse=True)

    # 4. Construct SearchResult objects
    results: List[SearchResult] = []
    for rank, (chunk, score) in enumerate(ranked_candidates[:k], start=1):
        results.append(
            SearchResult(
                chunk=chunk,
                score=round(float(score), 4),
                rank=rank,
            )
        )

    return results


def build_index_from_repo(
    repo_path: str | Path,
    embedder: Optional[BaseEmbedder] = None,
    save_dir: Optional[str | Path] = None,
) -> tuple[FAISSVectorStore, List[CodeChunk]]:
    """
    End-to-end ingestion and indexing pipeline:
    1. Walks repository respecting .gitignore.
    2. Chunks Python files using tree-sitter AST.
    3. Generates embedding text (Context Header + Docstring + Source).
    4. Computes normalized embeddings in batches.
    5. Builds and populates FAISS IndexFlatIP.
    6. Optionally saves index and metadata to disk.
    """
    embedder = embedder or get_embedder()
    walker = RepoWalker(repo_path)
    chunker = ASTChunker()

    all_chunks: List[CodeChunk] = []
    for file_path, rel_path in walker.walk():
        chunks = chunker.chunk_file(file_path=file_path, rel_path=rel_path)
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError(f"No valid code chunks found in repository: {repo_path}")

    # Prepare embedding text payloads
    embedding_texts = [c.get_embedding_text() for c in all_chunks]

    # Compute batch embeddings
    embeddings = embedder.embed_batch(embedding_texts)

    # Initialize FAISS store with matching dimension
    store = FAISSVectorStore(dimension=embedder.dimension)
    store.add_chunks(chunks=all_chunks, embeddings=embeddings)

    if save_dir:
        store.save(save_dir)

    return store, all_chunks
