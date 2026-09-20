"""
Data models for the Code Dependency Knowledge Graph.
Defines nodes, edges, graph metrics, and serialization schemas.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


class NodeType:
    """Standardized node types in the knowledge graph."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    MODULE = "module"


class EdgeType:
    """Standardized semantic relationship types in the knowledge graph."""
    IMPORTS = "imports"
    CONTAINS = "contains"
    INHERITS = "inherits"
    CALLS = "calls"


@dataclass
class GraphNode:
    """
    Represents an entity in the repository knowledge graph (file, class, method, function, module).
    """
    id: str
    name: str
    node_type: str
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    parent_class: Optional[str] = None
    docstring: Optional[str] = None
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        """Ground-truth citation for academic verification."""
        if self.file_path and self.start_line > 0 and self.end_line >= self.start_line:
            return f"[{self.file_path}:{self.start_line}-{self.end_line}]"
        elif self.file_path:
            return f"[{self.file_path}]"
        return f"[{self.name}]"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes node to dictionary for JSON/frontend consumption."""
        data = asdict(self)
        data["citation"] = self.citation
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        """Deserializes dictionary to GraphNode."""
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass
class GraphEdge:
    """
    Represents a directed relationship between two nodes in the knowledge graph.
    """
    source: str
    target: str
    edge_type: str
    line: Optional[int] = None
    call_expr: Optional[str] = None
    resolved: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes edge to dictionary for JSON/frontend consumption."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        """Deserializes dictionary to GraphEdge."""
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass
class GraphStats:
    """Summary metrics of the knowledge graph."""
    total_nodes: int
    total_edges: int
    files_count: int
    classes_count: int
    functions_count: int
    methods_count: int
    modules_count: int
    calls_count: int
    imports_count: int
    inherits_count: int
    contains_count: int
    density: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
