"""
Unit tests for the AST Chunker and Tree-sitter Parser.
Validates chunk boundaries, parent class tagging, docstring extraction,
and exact [file:line-line] line indices.
"""
import pytest
from pathlib import Path

from src.core.file_walker import RepoWalker
from src.chunking.ast_chunker import ASTChunker


SAMPLE_REPO_DIR = Path(__file__).parent / "sample_repo"


def test_repo_walker_discovers_python_files():
    walker = RepoWalker(SAMPLE_REPO_DIR)
    files = list(walker.walk())
    file_names = [f[0].name for f in files]

    assert "auth.py" in file_names
    assert "database.py" in file_names
    assert "payment_gateway.py" in file_names
    assert "__init__.py" in file_names


def test_ast_chunker_identifies_classes_and_methods():
    chunker = ASTChunker()
    auth_file = SAMPLE_REPO_DIR / "auth.py"
    chunks = chunker.chunk_file(str(auth_file))

    # We expect:
    # 1. hash_password (function)
    # 2. TokenService (class)
    # 3. TokenService.__init__ (method)
    # 4. TokenService.generate_token (method)
    # 5. TokenService.verify_token (method)
    # 6. TokenService.revoke_token (method)
    chunk_names = [c.name for c in chunks]
    assert "hash_password" in chunk_names
    assert "TokenService" in chunk_names
    assert "generate_token" in chunk_names
    assert "verify_token" in chunk_names
    assert "revoke_token" in chunk_names

    # Check method tagging with parent_class
    verify_chunk = next(c for c in chunks if c.name == "verify_token")
    assert verify_chunk.chunk_type == "method"
    assert verify_chunk.parent_class == "TokenService"
    assert "Class: TokenService" in verify_chunk.context_header
    assert verify_chunk.docstring is not None
    assert "Validates token signature" in verify_chunk.docstring

    # Check line numbers (start_line <= end_line and positive)
    assert verify_chunk.start_line > 0
    assert verify_chunk.end_line >= verify_chunk.start_line


def test_ast_chunker_top_level_function():
    chunker = ASTChunker()
    auth_file = SAMPLE_REPO_DIR / "auth.py"
    chunks = chunker.chunk_file(str(auth_file))

    hash_chunk = next(c for c in chunks if c.name == "hash_password")
    assert hash_chunk.chunk_type == "function"
    assert hash_chunk.parent_class is None
    assert "Hashes a plaintext password" in (hash_chunk.docstring or "")
    assert "auth.py" in hash_chunk.citation


def test_database_chunks_line_accuracy():
    chunker = ASTChunker()
    db_file = SAMPLE_REPO_DIR / "database.py"
    with open(db_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chunks = chunker.chunk_file(str(db_file))
    pool_chunk = next(c for c in chunks if c.name == "DatabasePool" and c.chunk_type == "class")
    
    # Check that code at start_line matches class definition
    start_idx = pool_chunk.start_line - 1
    assert "class DatabasePool" in lines[start_idx]
