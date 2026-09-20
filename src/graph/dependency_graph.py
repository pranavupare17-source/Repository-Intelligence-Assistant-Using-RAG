"""
Code Dependency Knowledge Graph Engine.
Constructs, queries, and analyzes software architecture graphs using NetworkX.
Built strictly from scratch with zero framework abstractions.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import networkx as nx

from src.core.file_walker import RepoWalker
from src.chunking.ast_chunker import ASTChunker
from src.core.models import CodeChunk
from src.graph.graph_models import (
    GraphNode,
    GraphEdge,
    GraphStats,
    NodeType,
    EdgeType,
)
from src.graph.ast_call_visitor import ASTCallVisitor, FileASTInfo, CallRecord


class CodeKnowledgeGraph:
    """
    Knowledge Graph representing repository architecture, symbol definitions,
    call-sites, inheritance, and module dependencies.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._symbol_index: Dict[str, List[str]] = {}  # symbol_name -> list of node_ids

    @property
    def total_nodes(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def total_edges(self) -> int:
        return self.graph.number_of_edges()

    def add_node(self, node: GraphNode) -> None:
        """Adds a GraphNode to the graph and indexes its name."""
        self._nodes[node.id] = node
        self.graph.add_node(
            node.id,
            name=node.name,
            node_type=node.node_type,
            file_path=node.file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            parent_class=node.parent_class,
            docstring=node.docstring,
            citation=node.citation,
            chunk_id=node.chunk_id,
            metadata=node.metadata,
        )
        # Index symbol name for fast resolution
        self._symbol_index.setdefault(node.name, []).append(node.id)
        if node.parent_class:
            composite_name = f"{node.parent_class}.{node.name}"
            self._symbol_index.setdefault(composite_name, []).append(node.id)

    def add_edge(self, edge: GraphEdge) -> None:
        """Adds a directed relationship between two nodes."""
        self._edges.append(edge)
        self.graph.add_edge(
            edge.source,
            edge.target,
            edge_type=edge.edge_type,
            line=edge.line,
            call_expr=edge.call_expr,
            resolved=edge.resolved,
            metadata=edge.metadata,
        )

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Fetches a GraphNode by its identifier."""
        return self._nodes.get(node_id)

    def resolve_node_id(self, symbol_or_id: str) -> Optional[str]:
        """Resolves a query string (either full ID or bare symbol name) to a node ID."""
        if symbol_or_id in self._nodes:
            return symbol_or_id
        if symbol_or_id in self._symbol_index:
            return self._symbol_index[symbol_or_id][0]
        # Partial match on symbol ending
        for nid in self._nodes:
            if nid.endswith(f"::{symbol_or_id}") or nid.endswith(f".{symbol_or_id}"):
                return nid
        return None

    def build_from_repository(
        self,
        repo_path: str | Path,
        chunks: Optional[List[CodeChunk]] = None,
    ) -> "CodeKnowledgeGraph":
        """
        Scans a repository directory, extracts AST chunks, calls, inheritances,
        and imports, and builds the complete knowledge graph.
        """
        repo_path = Path(repo_path).resolve()
        walker = RepoWalker(repo_path)
        ast_chunker = ASTChunker()
        call_visitor = ASTCallVisitor()

        # Step 1: Discover all files and parse AST chunks
        file_chunks: Dict[str, List[CodeChunk]] = {}
        if chunks is None:
            for file_path, rel_path in walker.walk():
                c_list = ast_chunker.chunk_file(file_path=file_path, rel_path=rel_path)
                file_chunks[rel_path] = c_list
        else:
            for c in chunks:
                file_chunks.setdefault(c.file_path, []).append(c)

        # Step 2: Extract imports, inheritances, and calls for each file
        file_ast_data: Dict[str, FileASTInfo] = {}
        for file_path, rel_path in walker.walk():
            ast_info = call_visitor.parse_file(file_path=file_path, rel_path=rel_path)
            file_ast_data[rel_path] = ast_info

        # Step 3: Register File Nodes
        for rel_path in file_ast_data:
            file_node_id = rel_path
            f_node = GraphNode(
                id=file_node_id,
                name=Path(rel_path).name,
                node_type=NodeType.FILE,
                file_path=rel_path,
                start_line=1,
                end_line=sum(1 for _ in open(repo_path / rel_path, "r", encoding="utf-8", errors="ignore")),
            )
            self.add_node(f_node)

        # Step 4: Register Class and Function/Method Nodes & 'contains' Edges
        chunk_map: Dict[str, CodeChunk] = {}
        for rel_path, c_list in file_chunks.items():
            file_node_id = rel_path

            for c in c_list:
                chunk_map[c.chunk_id] = c
                if c.chunk_type == "class":
                    node_id = f"{rel_path}::{c.name}"
                    node = GraphNode(
                        id=node_id,
                        name=c.name,
                        node_type=NodeType.CLASS,
                        file_path=rel_path,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        parent_class=None,
                        docstring=c.docstring,
                        chunk_id=c.chunk_id,
                    )
                    self.add_node(node)
                    # File contains class
                    self.add_edge(GraphEdge(source=file_node_id, target=node_id, edge_type=EdgeType.CONTAINS))

                elif c.chunk_type in ("method", "function"):
                    scope = f"{c.parent_class}.{c.name}" if c.parent_class else c.name
                    node_id = f"{rel_path}::{scope}"
                    node = GraphNode(
                        id=node_id,
                        name=c.name,
                        node_type=NodeType.METHOD if c.parent_class else NodeType.FUNCTION,
                        file_path=rel_path,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        parent_class=c.parent_class,
                        docstring=c.docstring,
                        chunk_id=c.chunk_id,
                    )
                    self.add_node(node)

                    # Class contains method or File contains top-level function
                    if c.parent_class:
                        parent_class_id = f"{rel_path}::{c.parent_class}"
                        self.add_edge(GraphEdge(source=parent_class_id, target=node_id, edge_type=EdgeType.CONTAINS))
                    else:
                        self.add_edge(GraphEdge(source=file_node_id, target=node_id, edge_type=EdgeType.CONTAINS))

        # Step 5: Wire Import Edges
        for rel_path, ast_info in file_ast_data.items():
            file_node_id = rel_path
            for imp in ast_info.imports:
                target_node_id = self._resolve_import_target(rel_path, imp.module, imp.name)
                self.add_edge(
                    GraphEdge(
                        source=file_node_id,
                        target=target_node_id,
                        edge_type=EdgeType.IMPORTS,
                        line=imp.line,
                        metadata={"module": imp.module, "symbol": imp.name, "alias": imp.alias},
                    )
                )

        # Step 6: Wire Inheritance Edges
        for rel_path, ast_info in file_ast_data.items():
            for inh in ast_info.inheritances:
                subclass_id = f"{rel_path}::{inh.class_name}"
                for base in inh.base_classes:
                    base_id = self.resolve_node_id(base)
                    if not base_id:
                        # Register external/unresolved base class
                        base_id = f"ext::{base}"
                        if base_id not in self._nodes:
                            self.add_node(GraphNode(id=base_id, name=base, node_type=NodeType.CLASS))
                    self.add_edge(
                        GraphEdge(
                            source=subclass_id,
                            target=base_id,
                            edge_type=EdgeType.INHERITS,
                            line=inh.line,
                        )
                    )

        # Step 7: Wire Call Edges
        for rel_path, ast_info in file_ast_data.items():
            for call in ast_info.calls:
                caller_id = f"{rel_path}::{call.caller_scope}"
                if caller_id not in self._nodes:
                    continue

                target_id = self._resolve_call_target(rel_path, call, ast_info)
                self.add_edge(
                    GraphEdge(
                        source=caller_id,
                        target=target_id,
                        edge_type=EdgeType.CALLS,
                        line=call.line,
                        call_expr=call.raw_expr,
                        resolved=not target_id.startswith("ext::"),
                        metadata={"callee_name": call.callee_name, "callee_attr": call.callee_attr},
                    )
                )

        return self

    def _resolve_import_target(self, current_file: str, module_path: str, symbol_name: str) -> str:
        """Resolves an import to an internal file/symbol node or creates an external module node."""
        # 1. Check if symbol exists internally
        if symbol_name:
            resolved = self.resolve_node_id(symbol_name)
            if resolved:
                return resolved

        # 2. Check if module maps to a local file
        clean_mod = module_path.lstrip(".")
        for nid, node in self._nodes.items():
            if node.node_type == NodeType.FILE:
                if clean_mod and (clean_mod in node.file_path or node.file_path.endswith(f"{clean_mod}.py")):
                    return nid

        # 3. External module fallback
        ext_name = f"{module_path}.{symbol_name}" if module_path and symbol_name else (module_path or symbol_name)
        ext_id = f"ext::{ext_name}"
        if ext_id not in self._nodes:
            self.add_node(GraphNode(id=ext_id, name=ext_name, node_type=NodeType.MODULE))
        return ext_id

    def _resolve_call_target(self, current_file: str, call: CallRecord, ast_info: FileASTInfo) -> str:
        """Resolves a call expression to an exact function/method or external symbol."""
        callee = call.callee_name

        # 1. Intra-class calls: self.method(...)
        if call.callee_attr and call.callee_attr.startswith("self") and call.caller_class:
            method_id = f"{current_file}::{call.caller_class}.{callee}"
            if method_id in self._nodes:
                return method_id

        # 2. Intra-file calls
        same_file_id = f"{current_file}::{callee}"
        if same_file_id in self._nodes:
            return same_file_id

        # 3. Imported symbols in current file
        for imp in ast_info.imports:
            if imp.name == callee or imp.alias == callee:
                resolved = self.resolve_node_id(imp.name)
                if resolved:
                    return resolved

        # 4. Global match in repository symbols
        if callee in self._symbol_index:
            candidates = self._symbol_index[callee]
            # Prefer candidate matching imported modules
            return candidates[0]

        # 5. External symbol fallback
        target_name = f"{call.callee_attr}.{callee}" if call.callee_attr else callee
        ext_id = f"ext::{target_name}"
        if ext_id not in self._nodes:
            self.add_node(GraphNode(id=ext_id, name=target_name, node_type=NodeType.MODULE))
        return ext_id

    # ---------------- Traversal and Query API ----------------

    def get_callers(self, symbol_or_id: str) -> List[Tuple[GraphNode, GraphEdge]]:
        """Finds all functions/methods that call the specified symbol."""
        node_id = self.resolve_node_id(symbol_or_id)
        if not node_id:
            return []

        callers = []
        for src, _, data in self.graph.in_edges(node_id, data=True):
            if data.get("edge_type") == EdgeType.CALLS:
                src_node = self._nodes.get(src)
                if src_node:
                    edge = GraphEdge(source=src, target=node_id, **data)
                    callers.append((src_node, edge))
        return callers

    def get_callees(self, symbol_or_id: str) -> List[Tuple[GraphNode, GraphEdge]]:
        """Finds all functions/methods called by the specified symbol."""
        node_id = self.resolve_node_id(symbol_or_id)
        if not node_id:
            return []

        callees = []
        for _, tgt, data in self.graph.out_edges(node_id, data=True):
            if data.get("edge_type") == EdgeType.CALLS:
                tgt_node = self._nodes.get(tgt)
                if tgt_node:
                    edge = GraphEdge(source=node_id, target=tgt, **data)
                    callees.append((tgt_node, edge))
        return callees

    def get_blast_radius(self, symbol_or_id: str) -> Dict[str, Any]:
        """
        Computes the transitive impact / blast radius if this symbol is modified or breaks.
        Traverses upstream incoming call edges and inheritances using reverse BFS.
        """
        node_id = self.resolve_node_id(symbol_or_id)
        if not node_id:
            return {"target": symbol_or_id, "total_affected": 0, "affected_nodes": [], "impact_levels": {}}

        # Target node
        target_node = self._nodes[node_id]

        # Reverse traversal for callers and dependents
        visited: Set[str] = {node_id}
        levels: Dict[int, List[Dict[str, Any]]] = {}
        current_level = {node_id}
        depth = 1

        while current_level and depth <= 5:
            next_level = set()
            level_nodes = []
            for curr in current_level:
                # Check who calls curr or inherits from curr
                for pred in self.graph.predecessors(curr):
                    edge_data = self.graph.get_edge_data(pred, curr) or {}
                    etype = edge_data.get("edge_type")
                    if etype in (EdgeType.CALLS, EdgeType.INHERITS, EdgeType.CONTAINS):
                        if pred not in visited:
                            visited.add(pred)
                            next_level.add(pred)
                            pred_node = self._nodes.get(pred)
                            if pred_node and pred_node.node_type != NodeType.FILE:
                                level_nodes.append({
                                    "node": pred_node.to_dict(),
                                    "relationship": etype,
                                    "via": curr,
                                })

            if level_nodes:
                levels[depth] = level_nodes
            current_level = next_level
            depth += 1

        total_affected = sum(len(n_list) for n_list in levels.values())

        return {
            "target": target_node.to_dict(),
            "total_affected": total_affected,
            "impact_levels": levels,
        }

    def get_shortest_path(self, source_symbol: str, target_symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Finds the shortest directed path between two entities in the knowledge graph."""
        src_id = self.resolve_node_id(source_symbol)
        tgt_id = self.resolve_node_id(target_symbol)
        if not src_id or not tgt_id:
            return None

        try:
            path_ids = nx.shortest_path(self.graph, source=src_id, target=tgt_id)
            path_nodes = []
            for i, nid in enumerate(path_ids):
                node = self._nodes.get(nid)
                edge_info = None
                if i < len(path_ids) - 1:
                    next_nid = path_ids[i + 1]
                    edge_info = self.graph.get_edge_data(nid, next_nid)
                path_nodes.append({
                    "node": node.to_dict() if node else {"id": nid, "name": nid},
                    "outgoing_edge": edge_info,
                })
            return path_nodes
        except nx.NetworkXNoPath:
            return None

    def get_subgraph(self, symbol_or_id: str, depth: int = 1) -> Dict[str, Any]:
        """Extracts ego-subgraph centered around a symbol for focused frontend display."""
        node_id = self.resolve_node_id(symbol_or_id)
        if not node_id:
            return {"nodes": [], "edges": []}

        subgraph_nodes = set([node_id])
        frontier = set([node_id])

        for _ in range(depth):
            next_frontier = set()
            for curr in frontier:
                # Add successors and predecessors
                succ = set(self.graph.successors(curr))
                pred = set(self.graph.predecessors(curr))
                next_frontier.update(succ - subgraph_nodes)
                next_frontier.update(pred - subgraph_nodes)
            subgraph_nodes.update(next_frontier)
            frontier = next_frontier

        nodes_data = [self._nodes[nid].to_dict() for nid in subgraph_nodes if nid in self._nodes]
        edges_data = []
        for u, v, d in self.graph.subgraph(subgraph_nodes).edges(data=True):
            edges_data.append({
                "source": u,
                "target": v,
                "edge_type": d.get("edge_type"),
                "line": d.get("line"),
                "call_expr": d.get("call_expr"),
            })

        return {"nodes": nodes_data, "edges": edges_data}

    def get_stats(self) -> GraphStats:
        """Computes summary architectural statistics."""
        node_type_counts: Dict[str, int] = {}
        for n in self._nodes.values():
            node_type_counts[n.node_type] = node_type_counts.get(n.node_type, 0) + 1

        edge_type_counts: Dict[str, int] = {}
        for _, _, d in self.graph.edges(data=True):
            etype = d.get("edge_type", "unknown")
            edge_type_counts[etype] = edge_type_counts.get(etype, 0) + 1

        n_count = self.graph.number_of_nodes()
        density = round(float(nx.density(self.graph)), 4) if n_count > 1 else 0.0

        return GraphStats(
            total_nodes=n_count,
            total_edges=self.graph.number_of_edges(),
            files_count=node_type_counts.get(NodeType.FILE, 0),
            classes_count=node_type_counts.get(NodeType.CLASS, 0),
            functions_count=node_type_counts.get(NodeType.FUNCTION, 0),
            methods_count=node_type_counts.get(NodeType.METHOD, 0),
            modules_count=node_type_counts.get(NodeType.MODULE, 0),
            calls_count=edge_type_counts.get(EdgeType.CALLS, 0),
            imports_count=edge_type_counts.get(EdgeType.IMPORTS, 0),
            inherits_count=edge_type_counts.get(EdgeType.INHERITS, 0),
            contains_count=edge_type_counts.get(EdgeType.CONTAINS, 0),
            density=density,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entire graph for frontend visualization and JSON export."""
        nodes_list = [node.to_dict() for node in self._nodes.values()]
        edges_list = []
        for u, v, d in self.graph.edges(data=True):
            edges_list.append({
                "source": u,
                "target": v,
                "edge_type": d.get("edge_type"),
                "line": d.get("line"),
                "call_expr": d.get("call_expr"),
                "resolved": d.get("resolved", True),
            })
        return {
            "stats": self.get_stats().to_dict(),
            "nodes": nodes_list,
            "edges": edges_list,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes graph to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, save_dir: str | Path) -> None:
        """Persists graph structure and metadata to disk."""
        out_path = Path(save_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_path / "graph.json", "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, load_dir: str | Path) -> "CodeKnowledgeGraph":
        """Loads a persisted graph from disk."""
        in_file = Path(load_dir) / "graph.json"
        with open(in_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        kg = cls()
        for nd in data.get("nodes", []):
            kg.add_node(GraphNode.from_dict(nd))
        for ed in data.get("edges", []):
            kg.add_edge(GraphEdge.from_dict(ed))
        return kg
