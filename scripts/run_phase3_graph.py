"""
Phase 3 Demonstration Script: Code Dependency Knowledge Graph.

Extracts Concrete Syntax Tree (CST) call-sites, import statements,
and class inheritance hierarchies using tree-sitter, constructs a
NetworkX directed knowledge graph, and performs impact/blast-radius
and call-chain path analysis.

Built strictly from scratch (Zero LangChain / LlamaIndex).
"""
import sys
import os
import argparse
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markup import escape
from rich.tree import Tree

from src.graph.dependency_graph import CodeKnowledgeGraph
from src.graph.graph_models import NodeType, EdgeType


def print_graph_summary(console: Console, kg: CodeKnowledgeGraph, repo_path: str):
    stats = kg.get_stats()

    table = Table(title="[bold green]Knowledge Graph Architectural Metrics[/bold green]", border_style="green")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white", justify="right")
    table.add_column("Description", style="dim")

    table.add_row("Total Graph Nodes", str(stats.total_nodes), "Files, classes, methods, and modules")
    table.add_row("Total Graph Edges", str(stats.total_edges), "Contains, imports, calls, inherits")
    table.add_row("Source Files", str(stats.files_count), "Parsed Python source files")
    table.add_row("Classes", str(stats.classes_count), "Discovered class definitions")
    table.add_row("Methods & Functions", f"{stats.methods_count + stats.functions_count} ({stats.methods_count}m / {stats.functions_count}f)", "Atomic execution units")
    table.add_row("AST Call Sites", str(stats.calls_count), "Resolved function invocation edges")
    table.add_row("Module Imports", str(stats.imports_count), "Inter-module dependency edges")
    table.add_row("Class Inheritances", str(stats.inherits_count), "Object-oriented subclassing links")
    table.add_row("Graph Density", f"{stats.density:.4f}", "Network connectivity density (|E| / |V|(|V|-1))")

    console.print(table)


def display_symbol_analysis(console: Console, kg: CodeKnowledgeGraph, symbol_query: str):
    node_id = kg.resolve_node_id(symbol_query)
    if not node_id:
        console.print(f"[bold red][!] Symbol '{symbol_query}' not found in the Knowledge Graph.[/bold red]")
        return

    node = kg.get_node(node_id)
    console.print(
        Panel(
            f"[bold white]Entity:[/bold white] [bold yellow]{escape(node.name)}[/bold yellow] ({node.node_type})\n"
            f"[bold white]Citation:[/bold white] [bold cyan]{escape(node.citation)}[/bold cyan]\n"
            f"[bold white]Docstring:[/bold white] [dim]{escape(node.docstring.strip() if node.docstring else 'N/A')}[/dim]",
            title=f"[bold cyan]Symbol Detail: {escape(node.name)}[/bold cyan]",
            border_style="cyan",
        )
    )

    # 1. Callers (Upstream Invocations)
    callers = kg.get_callers(node_id)
    caller_table = Table(title=f"[bold]Upstream Callers ({len(callers)} found)[/bold]", border_style="blue")
    caller_table.add_column("Caller Symbol", style="bold white")
    caller_table.add_column("Caller Citation", style="bold cyan")
    caller_table.add_column("Call Site Code", style="yellow")
    caller_table.add_column("Line", style="dim", justify="right")

    for caller_node, edge in callers:
        caller_table.add_row(
            caller_node.name,
            escape(caller_node.citation),
            escape(edge.call_expr or ""),
            str(edge.line or "-"),
        )
    console.print(caller_table)

    # 2. Callees (Downstream Invocations)
    callees = kg.get_callees(node_id)
    callee_table = Table(title=f"[bold]Downstream Callees ({len(callees)} found)[/bold]", border_style="magenta")
    callee_table.add_column("Callee Symbol", style="bold white")
    callee_table.add_column("Type", style="dim")
    callee_table.add_column("Call Site Code", style="yellow")
    callee_table.add_column("Line", style="dim", justify="right")

    for callee_node, edge in callees:
        callee_table.add_row(
            callee_node.name,
            callee_node.node_type,
            escape(edge.call_expr or ""),
            str(edge.line or "-"),
        )
    console.print(callee_table)

    # 3. Blast Radius & Impact Analysis
    blast = kg.get_blast_radius(node_id)
    console.print(
        f"\n[bold red][*] Blast Radius / Transitive Impact Analysis:[/bold red] "
        f"[bold white]{blast['total_affected']} component(s) potentially impacted if '{node.name}' changes.[/bold white]"
    )

    if blast["impact_levels"]:
        tree = Tree(f"[bold red]💥 Impact Root: {escape(node.name)} ({escape(node.citation)})[/bold red]")
        for depth, items in blast["impact_levels"].items():
            depth_branch = tree.add(f"[bold yellow]Depth {depth} ({len(items)} affected)[/bold yellow]")
            for item in items:
                n = item["node"]
                rel = item["relationship"]
                depth_branch.add(f"[{rel}] [bold white]{escape(n['name'])}[/bold white] [dim]{escape(n.get('citation', ''))}[/dim]")
        console.print(tree)
    console.print()


def display_path(console: Console, kg: CodeKnowledgeGraph, src_query: str, tgt_query: str):
    console.print(f"\n[bold cyan][*] Computing Call-Chain Path:[/bold cyan] [yellow]{src_query}[/yellow] ──> [yellow]{tgt_query}[/yellow]")
    path = kg.get_shortest_path(src_query, tgt_query)
    if not path:
        console.print("[bold red][!] No directed call path found between these symbols.[/bold red]\n")
        return

    tree = Tree(f"[bold green]Path Found ({len(path)} hops):[/bold green]")
    curr_branch = tree
    for i, step in enumerate(path):
        n = step["node"]
        edge = step["outgoing_edge"]
        lbl = f"[bold white]{escape(n.get('name', ''))}[/bold white] [dim]{escape(n.get('citation', ''))}[/dim]"
        if edge:
            call_txt = edge.get("call_expr", "")
            lbl += f" ──([bold yellow]{edge.get('edge_type', '')}[/bold yellow] line {edge.get('line', '-')}: [italic]{escape(call_txt)}[/italic])──>"
        curr_branch = curr_branch.add(lbl)
    console.print(tree)
    console.print()


def main():
    console = Console(highlight=False)
    console.print(
        Panel.fit(
            "[bold cyan]Repository Intelligence Assistant[/bold cyan]\n"
            "[bold yellow]Phase 3 - Code Dependency Knowledge Graph via NetworkX[/bold yellow]\n"
            "[dim]AST call-site extraction, cross-file imports, blast radius & path finding[/dim]\n"
            "[dim italic]Built strictly from scratch (Zero LangChain / LlamaIndex)[/dim italic]",
            border_style="cyan",
        )
    )

    parser = argparse.ArgumentParser(description="Phase 3 Dependency Knowledge Graph Demo")
    parser.add_argument(
        "--repo-path",
        type=str,
        default="tests/sample_repo",
        help="Repository path to analyze (default: tests/sample_repo)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="verify_token",
        help="Symbol to inspect callers, callees, and blast radius (default: verify_token)",
    )
    parser.add_argument(
        "--path",
        nargs=2,
        metavar=("SRC", "TGT"),
        help="Find directed call-chain path between two symbols (e.g. --path process_order verify_token)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive terminal graph explorer",
    )

    args = parser.parse_args()

    repo_dir = Path(args.repo_path).resolve()
    if not repo_dir.exists():
        console.print(f"[bold red]Error: Repository directory '{repo_dir}' does not exist.[/bold red]")
        sys.exit(1)

    console.print(f"[dim][*] Building Code Dependency Knowledge Graph from: {repo_dir}...[/dim]")
    kg = CodeKnowledgeGraph()
    kg.build_from_repository(repo_dir)

    print_graph_summary(console, kg, str(repo_dir))

    if args.path:
        display_path(console, kg, args.path[0], args.path[1])
        return

    if args.interactive:
        console.print("\n[bold cyan]Interactive Graph Explorer[/bold cyan]")
        console.print("[dim]Commands: '<symbol_name>', 'path <src> <tgt>', 'stats', or 'exit'[/dim]\n")
        while True:
            try:
                user_in = console.input("[bold green]graph-query > [/bold green]").strip()
                if not user_in:
                    continue
                if user_in.lower() in ("exit", "quit", "q"):
                    break
                if user_in.lower() == "stats":
                    print_graph_summary(console, kg, str(repo_dir))
                    continue
                if user_in.startswith("path "):
                    parts = user_in.split()
                    if len(parts) >= 3:
                        display_path(console, kg, parts[1], parts[2])
                    else:
                        console.print("[yellow]Usage: path <source_symbol> <target_symbol>[/yellow]")
                    continue

                display_symbol_analysis(console, kg, user_in)
            except (KeyboardInterrupt, EOFError):
                break
        console.print("\n[bold green][+] Exiting Interactive Graph Explorer.[/bold green]")
        return

    # Default demonstration
    display_symbol_analysis(console, kg, args.symbol)

    # Also demo path finding
    display_path(console, kg, "process_order", "verify_token")


if __name__ == "__main__":
    main()
