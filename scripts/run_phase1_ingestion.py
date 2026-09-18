"""
Phase 1 Demonstration Script: Ingestion and AST Chunking.

Walks a local repository, parses Python code using tree-sitter,
cuts chunks strictly at AST boundaries (classes and functions), tags
methods with parent classes, and prints clean stats and line ranges
for manual spot-checking.
"""
import sys
import os
import argparse
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.core.file_walker import RepoWalker
from src.chunking.ast_chunker import ASTChunker
from src.core.models import CodeChunk

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


def run_ingestion(repo_path: str, spot_check_count: int = 10):
    console = Console(highlight=False)
    console.print(
        Panel.fit(
            "[bold cyan]Repository Intelligence Assistant[/bold cyan]\n"
            "[bold yellow]Phase 1 - Ingestion & AST-Driven Code Chunking[/bold yellow]\n"
            "[dim]Built strictly from scratch (Zero LangChain / LlamaIndex)[/dim]",
            border_style="cyan",
        )
    )

    path = Path(repo_path).resolve()
    if not path.exists():
        console.print(f"[bold red]Error: Path '{repo_path}' does not exist![/bold red]")
        sys.exit(1)

    console.print(f"\n[bold green][+] Crawling repository root:[/bold green] [underline]{path}[/underline]")
    
    walker = RepoWalker(path)
    chunker = ASTChunker()

    all_chunks: List[CodeChunk] = []
    scanned_files = 0

    for file_path, rel_path in walker.walk():
        scanned_files += 1
        chunks = chunker.chunk_file(file_path=file_path, rel_path=rel_path, source_code=None)
        all_chunks.extend(chunks)

    # Calculate statistics
    class_chunks = [c for c in all_chunks if c.chunk_type == "class"]
    method_chunks = [c for c in all_chunks if c.chunk_type == "method"]
    function_chunks = [c for c in all_chunks if c.chunk_type == "function"]
    docstring_count = sum(1 for c in all_chunks if c.docstring)
    total_lines = sum((c.end_line - c.start_line + 1) for c in all_chunks)
    avg_lines = (total_lines / len(all_chunks)) if all_chunks else 0

    # Summary Panel
    stats_text = (
        f"* [bold white]Total Python Files Ingested:[/bold white] [bold cyan]{scanned_files}[/bold cyan]\n"
        f"* [bold white]Total Semantic Chunks Produced:[/bold white] [bold green]{len(all_chunks)}[/bold green]\n"
        f"  - Classes: [bold magenta]{len(class_chunks)}[/bold magenta]\n"
        f"  - Methods (tagged with parent): [bold blue]{len(method_chunks)}[/bold blue]\n"
        f"  - Standalone Functions: [bold yellow]{len(function_chunks)}[/bold yellow]\n"
        f"* [bold white]Chunks with Extracted Docstrings:[/bold white] [bold cyan]{docstring_count}[/bold cyan] ({round(docstring_count/len(all_chunks)*100, 1) if all_chunks else 0}%)\n"
        f"* [bold white]Average Lines per Chunk:[/bold white] [bold cyan]{avg_lines:.1f}[/bold cyan] lines"
    )
    console.print(Panel(stats_text, title="[bold]AST Ingestion Summary[/bold]", border_style="green"))

    from rich.markup import escape

    # Display Spot-Check Table
    console.print(f"\n[bold cyan][*] Spot-Check Verification Table (Exact [{escape('file:start-end')}] Citations):[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Citation [file:start-end]", style="bold green", width=28)
    table.add_column("Type", style="cyan", width=10)
    table.add_column("Symbol Name", style="white", width=22)
    table.add_column("Parent Class", style="yellow", width=18)
    table.add_column("Docstring / Summary Preview", style="dim", overflow="ellipsis")

    for chunk in all_chunks[:spot_check_count]:
        doc_preview = chunk.docstring.split("\n")[0] if chunk.docstring else "-"
        table.add_row(
            escape(chunk.citation),
            chunk.chunk_type,
            chunk.name,
            chunk.parent_class or "-",
            escape(doc_preview),
        )

    console.print(table)

    # Detailed Sample Chunk Inspection
    if all_chunks:
        sample_chunk = next((c for c in all_chunks if c.chunk_type == "method" and c.docstring), all_chunks[0])
        console.print(f"\n[bold yellow][Inspection] Sample Chunk: {sample_chunk.name}[/bold yellow]")
        console.print(f"[bold white]Citation:[/bold white] [green]{escape(sample_chunk.citation)}[/green]")
        console.print(f"[bold white]Context Header:[/bold white] [italic dim]{escape(sample_chunk.context_header)}[/italic dim]")
        console.print("[bold white]Extracted Code Boundary:[/bold white]")
        syntax = Syntax(sample_chunk.code, "python", theme="monokai", line_numbers=True, start_line=sample_chunk.start_line)
        console.print(Panel(syntax, border_style="dim"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest repo and produce AST code chunks.")
    parser.add_argument(
        "--repo-path",
        type=str,
        default="tests/sample_repo",
        help="Path to repository directory to ingest (default: tests/sample_repo)",
    )
    parser.add_argument(
        "--spot-check",
        type=int,
        default=10,
        help="Number of chunks to display in spot-check table (default: 10)",
    )
    args = parser.parse_args()
    run_ingestion(args.repo_path, args.spot_check)
