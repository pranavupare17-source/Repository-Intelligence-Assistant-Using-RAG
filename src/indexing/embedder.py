"""
Embedding provider layer built from scratch.
Supports Google Gemini, OpenAI, and a deterministic offline MockEmbedder.
Enforces L2 vector normalization so that FAISS IndexFlatIP computes exact cosine similarity.
"""
import os
import re
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from dotenv import load_dotenv

load_dotenv()


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """
    Applies L2 normalization to vectors along the last dimension.
    
    Academic Rationale:
    Cosine similarity between vectors A and B is defined as:
        cos(theta) = (A . B) / (||A||_2 * ||B||_2)
    When vectors are pre-normalized such that ||A||_2 = 1 and ||B||_2 = 1,
    the inner product A . B is mathematically identical to cosine similarity:
        A . B = cos(theta)
    This allows FAISS IndexFlatIP (Inner Product) to run at raw C++ SIMD speed
    without per-query division or magnitude calculations.
    """
    if vectors.ndim == 1:
        norm = np.linalg.norm(vectors)
        return (vectors / (norm if norm > 0 else 1.0)).astype(np.float32)
    
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32)


class BaseEmbedder(ABC):
    """Abstract base class for all embedding providers."""
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Embeds a single string and returns an L2-normalized float32 vector."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of strings and returns an L2-normalized (N, D) float32 matrix."""
        pass


class MockEmbedder(BaseEmbedder):
    """
    Deterministic offline embedder for local benchmarking, tests, and defense.
    Constructs bag-of-words / token-hashed vectors in 384 dimensions.
    Requires no API keys or internet connection.
    """
    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_token(self, token: str) -> np.ndarray:
        """Maps a token to a deterministic pseudo-random projection."""
        seed = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        return rng.standard_normal(self._dim).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        tokens = re.findall(r"\b[a-zA-Z_0-9]+\b", text.lower())
        if not tokens:
            vec = np.ones(self._dim, dtype=np.float32)
            return normalize_vectors(vec)

        vec = np.zeros(self._dim, dtype=np.float32)
        for token in tokens:
            vec += self._hash_token(token)

        return normalize_vectors(vec)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        matrix = np.vstack([self.embed_text(t) for t in texts])
        return normalize_vectors(matrix)


class GeminiEmbedder(BaseEmbedder):
    """
    Google Gemini Embeddings provider using the official google-genai SDK.
    Default model: 'text-embedding-004' (768 dimensions).
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-004"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment.")
        self.model = model
        self._dim = 768

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install google-genai: pip install google-genai")

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            response = self.client.models.embed_content(
                model=self.model,
                contents=chunk,
            )
            for emb in response.embeddings:
                all_embeddings.append(emb.values)

        matrix = np.array(all_embeddings, dtype=np.float32)
        if matrix.shape[1] != self._dim:
            self._dim = matrix.shape[1]
        return normalize_vectors(matrix)


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI Embeddings provider.
    Default model: 'text-embedding-3-small' (1536 dimensions).
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be provided or set in environment.")
        self.model = model
        self._dim = 1536

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install openai: pip install openai")

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=chunk,
            )
            for item in response.data:
                all_embeddings.append(item.embedding)

        matrix = np.array(all_embeddings, dtype=np.float32)
        if matrix.shape[1] != self._dim:
            self._dim = matrix.shape[1]
        return normalize_vectors(matrix)


def get_embedder(provider: Optional[str] = None) -> BaseEmbedder:
    """
    Factory function returning the configured embedder.
    Order of preference:
    1. Explicit provider argument ('gemini', 'openai', 'mock')
    2. EMBEDDING_PROVIDER in environment
    3. Auto-detected GEMINI_API_KEY -> GeminiEmbedder
    4. Auto-detected OPENAI_API_KEY -> OpenAIEmbedder
    5. Fallback -> MockEmbedder (deterministic local mode)
    """
    chosen = provider or os.getenv("EMBEDDING_PROVIDER")
    
    if chosen == "gemini":
        return GeminiEmbedder()
    elif chosen == "openai":
        return OpenAIEmbedder()
    elif chosen == "mock":
        return MockEmbedder()

    # Auto-detection
    if os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiEmbedder()
        except Exception:
            pass

    if os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAIEmbedder()
        except Exception:
            pass

    # Default to MockEmbedder for offline/defense safety
    return MockEmbedder()
