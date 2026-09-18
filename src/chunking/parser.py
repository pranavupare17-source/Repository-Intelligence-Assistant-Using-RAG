"""
Tree-sitter Python parser initialization and wrapper.
Uses modern tree-sitter v0.24+ / v0.26+ syntax.
"""
from typing import Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Parser


_PARSER_INSTANCE: Optional[Parser] = None


def get_python_parser() -> Parser:
    """
    Returns a configured tree-sitter Parser instance for Python.
    Uses singleton caching to avoid reloading grammar C-bindings repeatedly.
    """
    global _PARSER_INSTANCE
    if _PARSER_INSTANCE is None:
        language = Language(tspython.language())
        _PARSER_INSTANCE = Parser(language)
    return _PARSER_INSTANCE
