"""
Phase 2 Demonstration Script: Embeddings, FAISS IndexFlatIP, and Semantic Search.

Ingests a codebase, generates L2-normalized embeddings, builds a FAISS IndexFlatIP,
and executes semantic code retrieval with exact [file:start-end] citations.

Built strictly from scratch (Zero LangChain / LlamaIndex).
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

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markup import escape

from src.indexing.embedder import get_embedder, BaseEmbedder
from src.indexing.vector_store import FAISSVectorStore
from src.search.retriever import build_index_from_repo, semantic_search


def display_results(console: Console, query: str, results, top_k: int = 3):
    console.print(f"\n[bold cyan][*] Query:[/bold cyan] [italic yellow]\"{escape(query)}\"[/italic yellow]")
    console.print(f"[bold green][*] Top {len(results)} Semantic Search Hits (FAISS IndexFlatIP Cosine Retrieval):[/bold green]\n")

    for res in results:
        chunk = res.chunk
        score_color = "green" if res.score >= 0.5 else "yellow"
        
        header_text = (
            f"[bold white]Rank #{res.rank}[/bold white] | "
            f"[{score_color}]Cosine Score: {res.score:.4f}[/{score_color}] | "
            f"[bold cyan]Citation: {escape(chunk.citation)}[/bold cyan]\n"
            f"[dim]Context: {escape(chunk.context_header)}[/dim]"
        )
        if chunk.docstring:
            header_text += f"\n[dim italic]Docstring: {escape(chunk.docstring.strip())}[/dim italic]"

        syntax = Syntax(
            chunk.code,
            "python",
            theme="monokai",
            line_numbers=True,
            start_line=chunk.start_line,
        )

        panel = Panel(
            syntax,
            title=header_text,
            title_align="left",
            border_style="cyan" if res.rank == 1 else "dim",
        )
        console.print(panel)


def main():
    console = Console(highlight=False)
    console.print(
        Panel.fit(
            "[bold cyan]Repository Intelligence Assistant[/bold cyan]\n"
            "[bold yellow]Phase 2 - FAISS IndexFlatIP Vector Store & Semantic Search[/bold yellow]\n"
            "[dim]Built strictly from scratch (Zero LangChain / LlamaIndex)[/dim]",
            border_style="cyan",
        )
    )

    parser = argparse.ArgumentParser(description="FAISS Code Semantic Search Demo")
    parser.add_argument(
        "--repo-path",
        type=str,
        default="tests/sample_repo",
        help="Repository path to index (default: tests/sample_repo)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="mock",
        choices=["mock", "gemini", "openai"],
        help="Embedding provider (default: mock for offline demo)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="how is token expiration verified?",
        help="Search query to run",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of nearest chunks to retrieve (default: 3)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter interactive CLI search prompt after indexing",
    )
    args = parser.parse_args()

    repo_dir = Path(args.repo_path).resolve()
    if not repo_dir.exists():
        console.print(f"[bold red]Error: Repo path '{args.repo_path}' does not exist![/bold red]")
        sys.exit(1)

    console.print(f"\n[bold green][+] Initializing Embedder:[/bold green] provider=[bold magenta]{args.provider}[/bold magenta]")
    embedder = get_embedder(provider=args.provider)
    console.print(f"    Vector dimension: [bold cyan]{embedder.dimension}[/bold cyan]")

    console.print(f"[bold green][+] Ingesting & Building FAISS Vector Index from:[/bold green] [underline]{repo_dir}[/underline]")
    index_cache_dir = project_root / ".faiss_data"
    
    vector_store, all_chunks = build_index_from_repo(
        repo_path=repo_dir,
        embedder=embedder,
        save_dir=index_cache_dir,
    )

    console.print(f"    Successfully indexed [bold green]{vector_store.total_vectors}[/bold green] code chunks into FAISS IndexFlatIP.")
    console.print(f"    Index serialized to: [dim]{index_cache_dir}[/dim]")

    # Run default or specified query
    results = semantic_search(query=args.query, vector_store=vector_store, embedder=embedder, k=args.top_k)
    display_results(console, args.query, results, top_k=args.top_k)

    # Interactive Loop if requested
    if args.interactive:
        console.print("\n[bold cyan]=== Interactive Code Retrieval Mode (type 'exit' to quit) ===[/bold cyan]")
        while True:
            try:
                user_q = input("\nEnter code query > ").strip()
                if not user_q or user_q.lower() in ("exit", "quit", "q"):
                    break
                hits = semantic_search(query=user_q, vector_store=vector_store, embedder=embedder, k=args.top_k)
                display_results(console, user_q, hits, top_k=args.top_k)
            except (KeyboardInterrupt, EOFError):
                break
        console.print("\n[dim]Interactive session ended.[/dim]")


if __name__ == "__main__":
    main()
