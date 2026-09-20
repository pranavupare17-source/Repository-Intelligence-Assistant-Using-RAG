"""
Web Frontend Demonstration Launcher.
Starts the native Python HTTP REST server and launches the interactive
Repository Intelligence Dashboard in your web browser.

Usage:
    py -3.12 scripts/run_frontend.py --repo-path tests/sample_repo --port 8000
"""
import sys
import os
import argparse
import webbrowser
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
from rich.panel import Panel
from rich.table import Table

from src.web.server import create_server


def main():
    console = Console(highlight=False)

    parser = argparse.ArgumentParser(description="Repository Intelligence Web Demonstration Launcher")
    parser.add_argument(
        "--repo-path",
        type=str,
        default="tests/sample_repo",
        help="Repository path to analyze (default: tests/sample_repo)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Local HTTP port to bind (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="mock",
        choices=["mock", "gemini", "openai"],
        help="Embedding provider (default: mock for offline demo)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open web browser",
    )

    args = parser.parse_args()

    repo_dir = Path(args.repo_path).resolve()
    if not repo_dir.exists():
        console.print(f"[bold red]Error: Repository directory '{repo_dir}' does not exist.[/bold red]")
        sys.exit(1)

    url = f"http://{args.host}:{args.port}"

    console.print(
        Panel.fit(
            "[bold cyan]Repository Intelligence Assistant[/bold cyan]\n"
            "[bold yellow]Interactive Web Demonstration Dashboard[/bold yellow]\n"
            "[dim]AST Code RAG + FAISS IndexFlatIP + NetworkX Knowledge Graph[/dim]\n"
            f"[bold green]URL: [underline]{url}[/underline][/bold green]",
            border_style="cyan",
        )
    )

    table = Table(title="[bold]Demonstration Highlights[/bold]", border_style="dim")
    table.add_column("Phase", style="bold cyan")
    table.add_column("Capability", style="bold white")
    table.add_column("How to Demo Live", style="dim")

    table.add_row(
        "Phase 3: Graph",
        "Interactive Force-Directed Knowledge Graph",
        "Drag nodes, click to inspect callers/callees, compute transitive blast radius",
    )
    table.add_row(
        "Phase 2: Search",
        "Dense FAISS IndexFlatIP Cosine Retrieval",
        "Click benchmark chips for instant semantic code retrieval with [file:line-line] citations",
    )
    table.add_row(
        "Phase 1: Ingestion",
        "Tree-Sitter Concrete Syntax Tree Chunker",
        "Browse file tree and view AST boundaries, docstrings, and synthetic context headers",
    )
    table.add_row(
        "Academic Viva",
        "Mathematical Proofs & Architecture Matrix",
        "Review rigorous viva answers defending zero-framework engineering vs LangChain",
    )
    console.print(table)
    console.print(f"\n[bold green][*] Initializing AST Ingestion, FAISS Index, and Knowledge Graph from: [dim]{repo_dir}[/dim][/bold green]")

    server = create_server(
        repo_path=repo_dir,
        host=args.host,
        port=args.port,
        provider=args.provider,
    )

    console.print(f"[bold green][✓] Server active at: [underline]{url}[/underline][/bold green]")
    console.print("[dim]Press Ctrl+C in this terminal to stop the server.[/dim]\n")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[bold yellow][!] Shutting down server...[/bold yellow]")
        server.server_close()
        console.print("[bold green][✓] Server closed cleanly.[/bold green]")


if __name__ == "__main__":
    main()
