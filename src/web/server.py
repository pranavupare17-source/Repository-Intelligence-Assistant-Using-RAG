"""
Lightweight REST API backend and static web server.
Uses Python's standard library http.server for zero external runtime dependencies.
Exposes FAISS semantic search, AST chunk inspection, and NetworkX Knowledge Graph.
"""
import json
import urllib.parse
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.core.models import CodeChunk, SearchResult
from src.indexing.embedder import BaseEmbedder, get_embedder
from src.indexing.vector_store import FAISSVectorStore
from src.search.retriever import build_index_from_repo, semantic_search
from src.graph.dependency_graph import CodeKnowledgeGraph


class AppState:
    """Holds shared backend state: vector store, embedder, and knowledge graph."""
    def __init__(self, repo_path: str | Path, provider: str = "mock"):
        self.repo_path = Path(repo_path).resolve()
        self.embedder: BaseEmbedder = get_embedder(provider=provider)
        
        # Build FAISS vector store and AST chunks
        self.vector_store, self.chunks = build_index_from_repo(
            repo_path=self.repo_path,
            embedder=self.embedder,
        )
        self.chunk_by_id: Dict[str, CodeChunk] = {c.chunk_id: c for c in self.chunks}

        # Build Dependency Knowledge Graph
        self.kg = CodeKnowledgeGraph()
        self.kg.build_from_repository(repo_path=self.repo_path, chunks=self.chunks)


class RepositoryRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler serving REST API endpoints and static frontend assets."""
    state: Optional[AppState] = None
    static_dir: Path = Path(__file__).resolve().parent / "static"

    def __init__(self, *args, **kwargs):
        # Serve static assets from our designated static directory
        super().__init__(*args, directory=str(self.static_dir), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/status":
            self._handle_status()
        elif path == "/api/graph":
            self._handle_graph()
        elif path == "/api/node":
            self._handle_node(query)
        elif path == "/api/path":
            self._handle_path(query)
        elif path == "/api/chunks":
            self._handle_chunks()
        else:
            # Fall back to static file serving
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/search":
            self._handle_search()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    # ----------------- API Handlers -----------------

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_status(self):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return

        stats = self.state.kg.get_stats()
        resp = {
            "status": "ready",
            "repo_path": str(self.state.repo_path),
            "vector_store": {
                "total_vectors": self.state.vector_store.total_vectors,
                "dimension": self.state.vector_store.dimension,
                "index_type": "IndexFlatIP (Cosine)",
                "normalized": True,
            },
            "ast_chunks": {
                "total_chunks": len(self.state.chunks),
            },
            "knowledge_graph": stats.to_dict(),
        }
        self._send_json(resp)

    def _handle_graph(self):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return
        self._send_json(self.state.kg.to_dict())

    def _handle_node(self, query: Dict[str, List[str]]):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return

        node_id_param = query.get("id", [None])[0]
        if not node_id_param:
            self._send_json({"error": "Missing 'id' query parameter"}, 400)
            return

        node_id = self.state.kg.resolve_node_id(node_id_param)
        if not node_id:
            self._send_json({"error": f"Node '{node_id_param}' not found"}, 404)
            return

        node = self.state.kg.get_node(node_id)
        callers = self.state.kg.get_callers(node_id)
        callees = self.state.kg.get_callees(node_id)
        blast = self.state.kg.get_blast_radius(node_id)

        code_snippet = ""
        chunk = None
        if node.chunk_id and node.chunk_id in self.state.chunk_by_id:
            chunk = self.state.chunk_by_id[node.chunk_id]
            code_snippet = chunk.code
        elif node.file_path and node.start_line > 0:
            try:
                full_path = self.state.repo_path / node.file_path
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    code_snippet = "".join(lines[node.start_line - 1 : node.end_line])
            except Exception:
                code_snippet = ""

        resp = {
            "node": node.to_dict(),
            "code": code_snippet,
            "callers": [
                {
                    "node": c[0].to_dict(),
                    "edge": c[1].to_dict(),
                }
                for c in callers
            ],
            "callees": [
                {
                    "node": c[0].to_dict(),
                    "edge": c[1].to_dict(),
                }
                for c in callees
            ],
            "blast_radius": blast,
        }
        self._send_json(resp)

    def _handle_path(self, query: Dict[str, List[str]]):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return

        src = query.get("src", [None])[0]
        tgt = query.get("tgt", [None])[0]
        if not src or not tgt:
            self._send_json({"error": "Both 'src' and 'tgt' query parameters are required"}, 400)
            return

        path = self.state.kg.get_shortest_path(src, tgt)
        self._send_json({"source": src, "target": tgt, "path": path})

    def _handle_chunks(self):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return

        chunks_data = [
            {
                "chunk_id": c.chunk_id,
                "name": c.name,
                "chunk_type": c.chunk_type,
                "file_path": c.file_path,
                "citation": c.citation,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "parent_class": c.parent_class,
                "docstring": c.docstring,
                "context_header": c.context_header,
                "code": c.code,
            }
            for c in self.state.chunks
        ]
        self._send_json({"chunks": chunks_data})

    def _handle_search(self):
        if not self.state:
            self._send_json({"error": "State uninitialized"}, 500)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        query = req_data.get("query", "").strip()
        if not query:
            self._send_json({"error": "Empty search query"}, 400)
            return

        k = int(req_data.get("k", 5))

        search_hits = semantic_search(
            query=query,
            vector_store=self.state.vector_store,
            embedder=self.state.embedder,
            k=k,
        )

        results = []
        for hit in search_hits:
            c = hit.chunk
            results.append({
                "rank": hit.rank,
                "score": hit.score,
                "citation": hit.citation,
                "name": c.name,
                "chunk_type": c.chunk_type,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "parent_class": c.parent_class,
                "docstring": c.docstring,
                "context_header": c.context_header,
                "code": c.code,
            })

        self._send_json({"query": query, "count": len(results), "results": results})


def create_server(
    repo_path: str | Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    provider: str = "mock",
) -> HTTPServer:
    """Factory function creating configured HTTP server."""
    state = AppState(repo_path=repo_path, provider=provider)
    RepositoryRequestHandler.state = state
    server = HTTPServer((host, port), RepositoryRequestHandler)
    return server
