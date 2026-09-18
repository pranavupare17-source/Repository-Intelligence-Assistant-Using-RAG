"""
Unit tests for Phase 2: Vector Store, Normalization, FAISS IndexFlatIP, and Semantic Search.
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil

from src.core.models import CodeChunk
from src.indexing.embedder import normalize_vectors, MockEmbedder
from src.indexing.vector_store import FAISSVectorStore
from src.search.retriever import semantic_search, build_index_from_repo


SAMPLE_REPO_DIR = Path(__file__).parent / "sample_repo"


def test_vector_normalization_produces_unit_length():
    random_vectors = np.random.randn(10, 128).astype(np.float32)
    normalized = normalize_vectors(random_vectors)
    
    # Compute L2 norms
    norms = np.linalg.norm(normalized, axis=1)
    for norm in norms:
        assert np.isclose(norm, 1.0, atol=1e-5)


def test_inner_product_equals_cosine_similarity():
    v1 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    v2 = np.array([2.0, 3.0, 4.0], dtype=np.float32)

    # Standard mathematical cosine similarity formula
    expected_cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    # Normalized vectors inner product
    n1 = normalize_vectors(v1)
    n2 = normalize_vectors(v2)
    inner_product = np.dot(n1, n2)

    assert np.isclose(inner_product, expected_cosine, atol=1e-5)


def test_faiss_vector_store_add_and_search():
    dim = 64
    store = FAISSVectorStore(dimension=dim)
    
    c1 = CodeChunk.create("auth.py", 1, 10, "function", "hash_pw", code="def hash_pw(): pass")
    c2 = CodeChunk.create("db.py", 1, 15, "function", "connect_db", code="def connect_db(): pass")

    # Construct two distinct vectors
    v1 = np.zeros((1, dim), dtype=np.float32)
    v1[0, 0] = 1.0  # Feature at index 0
    v2 = np.zeros((1, dim), dtype=np.float32)
    v2[0, 1] = 1.0  # Feature at index 1

    embeddings = np.vstack([v1, v2])
    store.add_chunks([c1, c2], embeddings)

    assert store.total_vectors == 2

    # Query with vector aligned with v1
    query = np.zeros(dim, dtype=np.float32)
    query[0] = 1.0

    results = store.search(query, k=1)
    assert len(results) == 1
    hit_chunk, score = results[0]
    assert hit_chunk.name == "hash_pw"
    assert np.isclose(score, 1.0, atol=1e-4)


def test_faiss_store_save_and_load():
    temp_dir = tempfile.mkdtemp()
    try:
        dim = 32
        store = FAISSVectorStore(dimension=dim)
        chunk = CodeChunk.create("sample.py", 10, 25, "class", "PaymentManager", code="class PaymentManager: pass")
        embs = np.random.randn(1, dim).astype(np.float32)
        store.add_chunks([chunk], embs)

        store.save(temp_dir)

        # Load back
        loaded = FAISSVectorStore.load(temp_dir)
        assert loaded.total_vectors == 1
        assert loaded.dimension == dim
        assert loaded.chunks[0].name == "PaymentManager"
        assert loaded.chunks[0].start_line == 10
        assert loaded.chunks[0].end_line == 25
    finally:
        shutil.rmtree(temp_dir)


def test_end_to_end_build_and_semantic_search():
    embedder = MockEmbedder(dimension=128)
    store, chunks = build_index_from_repo(SAMPLE_REPO_DIR, embedder=embedder)

    assert store.total_vectors > 0

    # Search for token verification
    results = semantic_search("verify token expiration", vector_store=store, embedder=embedder, k=3)
    assert len(results) > 0

    top_chunk = results[0].chunk
    assert top_chunk.citation.startswith("[")
    assert top_chunk.citation.endswith("]")
    assert top_chunk.start_line > 0
