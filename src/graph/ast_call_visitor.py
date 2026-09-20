"""
AST visitor for extracting imports, class inheritance, and function call-sites
using tree-sitter.
Zero framework abstractions.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from tree_sitter import Node

from src.chunking.parser import get_python_parser


@dataclass
class ImportRecord:
    """Represents an imported module or symbol extracted from the AST."""
    module: str
    name: str
    alias: Optional[str] = None
    line: int = 1
    is_from: bool = False


@dataclass
class CallRecord:
    """Represents a call-site within a function, method, or module body."""
    caller_scope: str          # e.g. "OrderService.process_order" or "format_order_summary"
    caller_class: Optional[str] # e.g. "OrderService" or None
    raw_expr: str              # Code snippet of the call
    callee_name: str           # Target function/method name (e.g. "charge", "verify_token")
    callee_attr: Optional[str] # Object prefix (e.g. "self.payment_gateway")
    line: int                  # 1-indexed line number where call occurs


@dataclass
class ClassInheritanceRecord:
    """Represents a class inheritance relationship extracted from AST."""
    class_name: str
    base_classes: List[str]
    line: int


@dataclass
class FileASTInfo:
    """Aggregated structural metadata for a single parsed Python file."""
    file_path: str
    imports: List[ImportRecord] = field(default_factory=list)
    inheritances: List[ClassInheritanceRecord] = field(default_factory=list)
    calls: List[CallRecord] = field(default_factory=list)


class ASTCallVisitor:
    """
    Parses a Python file using tree-sitter to extract:
    1. Import dependencies (standard, aliased, relative, from-imports).
    2. Class inheritance hierarchies.
    3. Function and method invocation call-sites with exact line citations.
    """
    def __init__(self):
        self.parser = get_python_parser()

    def parse_file(
        self,
        file_path: str | Path,
        rel_path: Optional[str] = None,
        source_code: Optional[str] = None,
    ) -> FileASTInfo:
        """
        Parses a file and returns its structural dependency information.
        """
        display_path = rel_path if rel_path is not None else str(file_path).replace("\\", "/")

        if source_code is None:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()

        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)
        root = tree.root_node

        info = FileASTInfo(file_path=display_path)

        self._extract_imports(root, source_bytes, info)
        self._extract_structure_and_calls(root, source_bytes, info, current_class=None, current_scope="<module>")

        return info

    def _extract_imports(self, root: Node, source_bytes: bytes, info: FileASTInfo) -> None:
        """Finds all import statements at module level."""
        for child in root.children:
            if child.type == "import_statement":
                line = child.start_point[0] + 1
                for c in child.children:
                    if c.type == "dotted_name":
                        mod_name = source_bytes[c.start_byte:c.end_byte].decode("utf-8")
                        info.imports.append(ImportRecord(module=mod_name, name=mod_name, line=line, is_from=False))
                    elif c.type == "aliased_import":
                        name_node = c.child_by_field_name("name")
                        alias_node = c.child_by_field_name("alias")
                        if name_node and alias_node:
                            mod_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                            alias_name = source_bytes[alias_node.start_byte:alias_node.end_byte].decode("utf-8")
                            info.imports.append(ImportRecord(module=mod_name, name=mod_name, alias=alias_name, line=line, is_from=False))

            elif child.type == "import_from_statement":
                line = child.start_point[0] + 1
                mod_node = child.child_by_field_name("module_name")
                mod_str = source_bytes[mod_node.start_byte:mod_node.end_byte].decode("utf-8") if mod_node else ""

                for c in child.children:
                    if c.type == "dotted_name" and c != mod_node:
                        sym_name = source_bytes[c.start_byte:c.end_byte].decode("utf-8")
                        info.imports.append(ImportRecord(module=mod_str, name=sym_name, line=line, is_from=True))
                    elif c.type == "aliased_import":
                        name_node = c.child_by_field_name("name")
                        alias_node = c.child_by_field_name("alias")
                        if name_node and alias_node:
                            sym_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                            alias_name = source_bytes[alias_node.start_byte:alias_node.end_byte].decode("utf-8")
                            info.imports.append(ImportRecord(module=mod_str, name=sym_name, alias=alias_name, line=line, is_from=True))

    def _extract_structure_and_calls(
        self,
        node: Node,
        source_bytes: bytes,
        info: FileASTInfo,
        current_class: Optional[str],
        current_scope: str,
    ) -> None:
        """
        Recursively extracts class definitions (with inheritance), function/method
        scopes, and function call-sites.
        """
        if node.type == "class_definition":
            c_name_node = node.child_by_field_name("name")
            class_name = source_bytes[c_name_node.start_byte:c_name_node.end_byte].decode("utf-8") if c_name_node else "<anon_class>"
            line = node.start_point[0] + 1

            # Extract superclasses
            superclasses_node = node.child_by_field_name("superclasses")
            base_classes = []
            if superclasses_node:
                for child in superclasses_node.children:
                    if child.type in ("identifier", "attribute"):
                        base_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                        base_classes.append(base_name)

            if base_classes:
                info.inheritances.append(ClassInheritanceRecord(class_name=class_name, base_classes=base_classes, line=line))

            # Traverse class body
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    self._extract_structure_and_calls(
                        node=child,
                        source_bytes=source_bytes,
                        info=info,
                        current_class=class_name,
                        current_scope=class_name,
                    )
            return

        elif node.type == "function_definition":
            fn_name_node = node.child_by_field_name("name")
            fn_name = source_bytes[fn_name_node.start_byte:fn_name_node.end_byte].decode("utf-8") if fn_name_node else "<anon_fn>"
            scope_name = f"{current_class}.{fn_name}" if current_class else fn_name

            body_node = node.child_by_field_name("body")
            if body_node:
                self._collect_calls_in_body(body_node, source_bytes, info, caller_scope=scope_name, caller_class=current_class)
            return

        # For statements outside classes and functions
        for child in node.children:
            self._extract_structure_and_calls(
                node=child,
                source_bytes=source_bytes,
                info=info,
                current_class=current_class,
                current_scope=current_scope,
            )

    def _collect_calls_in_body(
        self,
        node: Node,
        source_bytes: bytes,
        info: FileASTInfo,
        caller_scope: str,
        caller_class: Optional[str],
    ) -> None:
        """Finds all call expressions inside a function body, avoiding descending into nested functions."""
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                line = node.start_point[0] + 1
                raw_call = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").split("\n")[0].strip()

                if func_node.type == "identifier":
                    callee_name = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8")
                    info.calls.append(
                        CallRecord(
                            caller_scope=caller_scope,
                            caller_class=caller_class,
                            raw_expr=raw_call,
                            callee_name=callee_name,
                            callee_attr=None,
                            line=line,
                        )
                    )
                elif func_node.type == "attribute":
                    # e.g. self.payment_gateway.charge or db.acquire
                    attr_node = func_node.child_by_field_name("attribute")
                    obj_node = func_node.child_by_field_name("object")
                    if attr_node:
                        method_name = source_bytes[attr_node.start_byte:attr_node.end_byte].decode("utf-8")
                        obj_str = source_bytes[obj_node.start_byte:obj_node.end_byte].decode("utf-8") if obj_node else None
                        info.calls.append(
                            CallRecord(
                                caller_scope=caller_scope,
                                caller_class=caller_class,
                                raw_expr=raw_call,
                                callee_name=method_name,
                                callee_attr=obj_str,
                                line=line,
                            )
                        )

        # Do not descend into nested function or class definitions (they have their own scope)
        for child in node.children:
            if child.type not in ("function_definition", "class_definition"):
                self._collect_calls_in_body(child, source_bytes, info, caller_scope=caller_scope, caller_class=caller_class)
