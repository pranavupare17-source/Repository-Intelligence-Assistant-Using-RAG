"""
AST-based Code Chunker using tree-sitter.
Parses Python source code into a Concrete Syntax Tree (CST),
recursively discovers class and function boundaries, tags methods
with enclosing classes, extracts docstrings, and builds enriched
context headers.
"""
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from tree_sitter import Node

from src.core.models import CodeChunk
from src.chunking.parser import get_python_parser


class ASTChunker:
    """
    Analyzes Python source files using tree-sitter AST nodes to produce
    semantically meaningful, syntactically whole code chunks.
    """
    def __init__(self):
        self.parser = get_python_parser()

    def chunk_file(
        self,
        file_path: str | Path,
        rel_path: Optional[str] = None,
        source_code: Optional[str] = None,
    ) -> List[CodeChunk]:
        """
        Parses a single Python file and returns extracted CodeChunk objects.
        
        Args:
            file_path: Path to the file on disk.
            rel_path: Optional relative path for clean citation metadata.
                      Defaults to str(file_path).
            source_code: Optional string containing source code. If None,
                         the file is read from disk.
        """
        display_path = rel_path if rel_path is not None else str(file_path).replace("\\", "/")
        
        if source_code is None:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()

        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)
        root_node = tree.root_node

        chunks: List[CodeChunk] = []
        self._traverse_node(
            node=root_node,
            source_bytes=source_bytes,
            file_path=display_path,
            parent_class=None,
            chunks=chunks,
        )
        return chunks

    def _traverse_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: str,
        parent_class: Optional[str],
        chunks: List[CodeChunk],
    ) -> None:
        """
        Recursively walks AST nodes, cutting chunks at class and function definitions.
        """
        if node.type == "class_definition":
            class_name = self._get_node_name(node, source_bytes)
            docstring = self._extract_docstring(node, source_bytes)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            code = self._get_node_text(node, source_bytes)
            decorators = self._extract_decorators(node, source_bytes)

            # Record the class-level chunk (useful for structural architectural queries)
            class_chunk = CodeChunk.create(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                chunk_type="class",
                name=class_name,
                parent_class=None,
                docstring=docstring,
                code=code,
                metadata={
                    "decorators": decorators,
                    "is_class_level": True,
                },
            )
            chunks.append(class_chunk)

            # Now visit the body of the class to extract its individual methods
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    self._traverse_node(
                        node=child,
                        source_bytes=source_bytes,
                        file_path=file_path,
                        parent_class=class_name,
                        chunks=chunks,
                    )
            return

        elif node.type == "function_definition":
            fn_name = self._get_node_name(node, source_bytes)
            docstring = self._extract_docstring(node, source_bytes)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            code = self._get_node_text(node, source_bytes)
            decorators = self._extract_decorators(node, source_bytes)
            params = self._extract_parameters(node, source_bytes)

            chunk_type = "method" if parent_class else "function"

            # Synthetic context header incorporating parent class & signature
            header_parts = [f"File: {file_path}"]
            if parent_class:
                header_parts.append(f"Class: {parent_class}")
            header_parts.append(f"{chunk_type.capitalize()}: {fn_name}({', '.join(params)})")
            if decorators:
                header_parts.append(f"Decorators: [{', '.join(decorators)}]")
            if docstring:
                header_parts.append(f"Summary: {docstring.strip()}")
            context_header = " | ".join(header_parts)

            chunk = CodeChunk.create(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                chunk_type=chunk_type,
                name=fn_name,
                parent_class=parent_class,
                docstring=docstring,
                code=code,
                context_header=context_header,
                metadata={
                    "parameters": params,
                    "decorators": decorators,
                },
            )
            chunks.append(chunk)

            # Note: Do not return early if there are nested functions inside this function
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    if child.type == "function_definition":
                        nested_parent = f"{parent_class}.{fn_name}" if parent_class else fn_name
                        self._traverse_node(
                            node=child,
                            source_bytes=source_bytes,
                            file_path=file_path,
                            parent_class=nested_parent,
                            chunks=chunks,
                        )
            return

        # For general statements, continue recursive descent to locate any nested functions/classes
        for child in node.children:
            self._traverse_node(
                node=child,
                source_bytes=source_bytes,
                file_path=file_path,
                parent_class=parent_class,
                chunks=chunks,
            )

    def _get_node_name(self, node: Node, source_bytes: bytes) -> str:
        """Extracts the identifier name from a function or class definition node."""
        name_node = node.child_by_field_name("name")
        if name_node:
            return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        return "<anonymous>"

    def _get_node_text(self, node: Node, source_bytes: bytes) -> str:
        """Extracts exact UTF-8 decoded source code for a node."""
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _extract_docstring(self, node: Node, source_bytes: bytes) -> Optional[str]:
        """
        Extracts the docstring from the body of a class or function definition.
        In Python AST, docstrings appear as the first expression_statement in the block.
        """
        body_node = node.child_by_field_name("body")
        if not body_node:
            return None

        for child in body_node.children:
            # First statement in the block
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "string":
                        raw_str = source_bytes[subchild.start_byte:subchild.end_byte].decode("utf-8", errors="replace")
                        return self._clean_docstring(raw_str)
                break
            elif child.type not in ("comment",):
                # If first non-comment statement is not an expression_statement, no docstring exists
                break
        return None

    def _clean_docstring(self, raw_str: str) -> str:
        """Strips quotes and formatting from raw docstring literals."""
        cleaned = raw_str.strip()
        for quote in ('"""', "'''", '"', "'"):
            if cleaned.startswith(quote) and cleaned.endswith(quote) and len(cleaned) >= 2 * len(quote):
                cleaned = cleaned[len(quote):-len(quote)]
                break
        return cleaned.strip()

    def _extract_decorators(self, node: Node, source_bytes: bytes) -> List[str]:
        """Extracts any decorators applied to the function or class."""
        decorators: List[str] = []
        # Check preceding siblings or parent decorated_definition
        parent = node.parent
        if parent and parent.type == "decorated_definition":
            for child in parent.children:
                if child.type == "decorator":
                    dec_text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                    decorators.append(dec_text.strip())
        return decorators

    def _extract_parameters(self, node: Node, source_bytes: bytes) -> List[str]:
        """Extracts parameter names from a function_definition node."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return []

        params: List[str] = []
        for child in params_node.children:
            if child.type in ("identifier", "typed_parameter", "default_parameter", "typed_default_parameter"):
                param_text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                params.append(param_text.strip())
        return params
