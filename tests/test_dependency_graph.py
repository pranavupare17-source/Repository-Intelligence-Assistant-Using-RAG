"""
Unit and Integration Tests for Phase 3: Code Dependency Knowledge Graph.
Validates AST call-site extraction, cross-module imports, inheritance hierarchy,
caller/callee resolution, blast-radius analysis, and serialization.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.graph.ast_call_visitor import ASTCallVisitor
from src.graph.dependency_graph import CodeKnowledgeGraph
from src.graph.graph_models import NodeType, EdgeType


SAMPLE_REPO_DIR = Path(__file__).parent / "sample_repo"


def test_ast_call_visitor_extracts_imports():
    visitor = ASTCallVisitor()
    order_svc_file = SAMPLE_REPO_DIR / "order_service.py"
    info = visitor.parse_file(order_svc_file)

    imported_names = [imp.name for imp in info.imports]
    assert "TokenService" in imported_names
    assert "DatabasePool" in imported_names
    assert "StripeGateway" in imported_names
    assert "execute_query_with_retry" in imported_names

    # Check from-import flag
    token_imp = next(imp for imp in info.imports if imp.name == "TokenService")
    assert token_imp.is_from is True
    assert token_imp.module == ".auth"


def test_ast_call_visitor_extracts_inheritance():
    visitor = ASTCallVisitor()
    order_svc_file = SAMPLE_REPO_DIR / "order_service.py"
    info = visitor.parse_file(order_svc_file)

    assert len(info.inheritances) >= 1
    order_inh = next(inh for inh in info.inheritances if inh.class_name == "OrderService")
    assert "BaseService" in order_inh.base_classes


def test_ast_call_visitor_extracts_call_sites():
    visitor = ASTCallVisitor()
    order_svc_file = SAMPLE_REPO_DIR / "order_service.py"
    info = visitor.parse_file(order_svc_file)

    callee_names = [call.callee_name for call in info.calls]
    # Check key methods are extracted as call sites
    assert "verify_token" in callee_names
    assert "charge" in callee_names
    assert "execute_query_with_retry" in callee_names
    assert "calculate_processing_fee" in callee_names
    assert "validate_checkout" in callee_names

    # Verify line numbers are positive
    for call in info.calls:
        assert call.line > 0


def test_knowledge_graph_build_and_stats():
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(SAMPLE_REPO_DIR)

    stats = kg.get_stats()
    assert stats.total_nodes > 10
    assert stats.total_edges > 10
    assert stats.files_count >= 4
    assert stats.classes_count >= 4
    assert stats.methods_count >= 10
    assert stats.calls_count >= 10
    assert stats.imports_count >= 5
    assert stats.density > 0.0


def test_knowledge_graph_caller_callee_resolution():
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(SAMPLE_REPO_DIR)

    # verify_token should be called by validate_checkout
    callers = kg.get_callers("verify_token")
    caller_names = [c[0].name for c in callers]
    assert "validate_checkout" in caller_names

    # process_order should call charge and execute_query_with_retry
    callees = kg.get_callees("process_order")
    callee_names = [c[0].name for c in callees]
    assert "charge" in callee_names
    assert "execute_query_with_retry" in callee_names
    assert "validate_checkout" in callee_names


def test_knowledge_graph_blast_radius():
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(SAMPLE_REPO_DIR)

    blast = kg.get_blast_radius("verify_token")
    assert blast["total_affected"] > 0
    # validate_checkout and OrderService should be in blast radius
    level1_names = [item["node"]["name"] for item in blast["impact_levels"].get(1, [])]
    assert "validate_checkout" in level1_names or "TokenService" in level1_names


def test_knowledge_graph_shortest_path():
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(SAMPLE_REPO_DIR)

    path = kg.get_shortest_path("process_order", "verify_token")
    assert path is not None
    assert len(path) == 3
    node_names = [p["node"]["name"] for p in path]
    assert node_names == ["process_order", "validate_checkout", "verify_token"]


def test_knowledge_graph_subgraph_extraction():
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(SAMPLE_REPO_DIR)

    sub = kg.get_subgraph("OrderService", depth=1)
    assert len(sub["nodes"]) > 1
    assert any(n["name"] == "OrderService" for n in sub["nodes"])


def test_knowledge_graph_serialization_cycle():
    temp_dir = tempfile.mkdtemp()
    try:
        kg = CodeKnowledgeGraph()
        kg.build_from_repository(SAMPLE_REPO_DIR)
        kg.save(temp_dir)

        loaded_kg = CodeKnowledgeGraph.load(temp_dir)
        assert loaded_kg.total_nodes == kg.total_nodes
        assert loaded_kg.total_edges == kg.total_edges

        # Check queries work on loaded graph
        callers = loaded_kg.get_callers("verify_token")
        caller_names = [c[0].name for c in callers]
        assert "validate_checkout" in caller_names
    finally:
        shutil.rmtree(temp_dir)
