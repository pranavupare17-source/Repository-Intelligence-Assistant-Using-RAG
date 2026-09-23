# Repository Intelligence Assistant (Using RAG)

A state-of-the-art codebase Question-Answering and Retrieval system built **completely from scratch in pure Python**. Combines Abstract Syntax Tree (AST) code parsing via Tree-sitter, parent-class context enrichment, exact ground-truth `[file:line-line]` citations, and an L2-normalized FAISS `IndexFlatIP` dense cosine similarity search engine.

> **Academic Hard Constraint**: Built with **ZERO** high-level agent or retrieval frameworks (No LangChain, No LlamaIndex, No LangGraph). Every step of ingestion, chunking, indexing, and retrieval is written in clean, explainable Python.

---

## 🌟 Architecture Overview

```
                        +-----------------------------------------+
                        |           Local Codebase Root           |
                        +-----------------------------------------+
                                             |
                               [ RepoWalker (.gitignore) ]
                                             |
                                             v
                        +-----------------------------------------+
                        |        Tree-Sitter Python CST           |
                        +-----------------------------------------+
                                             |
                              [ ASTChunker: class / method ]
                                             |
                                             v
                        +-----------------------------------------+
                        |      CodeChunk with Context Header      |
                        |      {file, start_line, end_line,       |
                        |       class, docstring, citation}       |
                        +-----------------------------------------+
                                             |
                           [ Embedder: Gemini / OpenAI / Mock ]
                                             |
                                 [ L2 Normalization ]
                                             |
                                             v
                        +-----------------------------------------+
                        |           FAISS IndexFlatIP             |
                        |      (Exhaustive Cosine Search)         |
                        +-----------------------------------------+
                                             |
                                   [ semantic_search() ]
                                             |
                                             v
                        +-----------------------------------------+
                        |       Ranked Hits + Exact Bounds        |
                        |            [file:start-end]             |
                        +-----------------------------------------+
```

---

## 🔬 Why is this Better than Existing Baseline Code RAG?

| Feature | Standard Naive RAG (LangChain/LlamaIndex) | Our Hand-Rolled Repository Intelligence |
| :--- | :--- | :--- |
| **Code Splitting** | Arbitrary token/char chunking (e.g. 500 chars). Slices functions in half, breaking syntax. | **AST-Driven Boundaries**: Cuts strictly at `class_definition` and `function_definition` using tree-sitter. |
| **Context Scope** | Isolated chunks lose enclosing class, file, and signature information. | **Synthetic Context Header Injection**: Tags methods with parent classes, parameters, and docstrings. |
| **Mathematical Cosine Search** | Uses generic $L_2$ distance or unnormalized inner product with framework overhead. | **Normalized FAISS `IndexFlatIP`**: Strict unit $L_2$ vectors where $A \cdot B \equiv \cos(\theta)$ at raw C++ SIMD speed. |
| **Citation Precision** | Coarse file-level or character offsets. | **Exact 1-Indexed Academic Citations**: `[file_path:start_line-end_line]`. |
| **Explainability** | Black-box chains and opaque abstractions. | **100% Transparent Python**: Zero framework dependencies; every line is defensible in an academic review. |

---

## 🚀 Quickstart & Demonstration

### 1. Environment Setup
```bash
# Python 3.11+ recommended
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` if you want to use Google Gemini or OpenAI:
```bash
cp .env.example .env
# Edit .env with GEMINI_API_KEY or OPENAI_API_KEY
```
*(By default, the system includes a deterministic offline `MockEmbedder` so you can demonstrate the entire pipeline to your guide without internet or API keys!)*

### Phase 2: FAISS Vector Indexing & Semantic Search
Run semantic retrieval queries against the codebase with colorized code display and ground-truth citations:
```bash
# Single Query
python scripts/run_phase2_search.py --repo-path tests/sample_repo --query "how is token expiration verified?"

# Interactive Mode
python scripts/run_phase2_search.py --repo-path tests/sample_repo --interactive
```

### Phase 3: Code Dependency Knowledge Graph
Analyze symbol call-sites, cross-module imports, class inheritance, and transitive blast radius using NetworkX:
```bash
# Symbol Impact & Caller/Callee Analysis
python scripts/run_phase3_graph.py --repo-path tests/sample_repo --symbol verify_token

# Shortest Call-Chain Path Finding
python scripts/run_phase3_graph.py --repo-path tests/sample_repo --path process_order verify_token

# Interactive Terminal Graph Explorer
python scripts/run_phase3_graph.py --repo-path tests/sample_repo --interactive
```

### 🌐 Interactive Web Demonstration Dashboard
Launch the zero-dependency interactive single-page application with real-time force-directed physics graph, live semantic search console, and AST code inspector:
```bash
python scripts/run_frontend.py --repo-path tests/sample_repo --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 🎓 Academic Defense / Viva Cheatsheet

If your guide asks:

### 1. "Why didn't you use LangChain or LlamaIndex?"
> *"Frameworks like LangChain wrap retrieval in monolithic abstractions (`RetrievalQA`, `RecursiveCharacterTextSplitter`) that treat code like prose. They slice arbitrarily across token limits, breaking control flow and AST structure. By building from scratch, we have full mathematical and structural control over AST node boundary detection, parent scope injection, and vector normalization."*

### 2. "How does FAISS `IndexFlatIP` compute Cosine Similarity?"
> *"Cosine similarity is defined as $\frac{A \cdot B}{\|A\|_2 \|B\|_2}$. In our `embedder.py` and `vector_store.py`, we apply $L_2$ normalization such that $\|A\|_2 = 1$ and $\|B\|_2 = 1$. Consequently, the Inner Product $A \cdot B$ is mathematically identical to Cosine Similarity. Using FAISS `IndexFlatIP` allows us to perform exhaustive cosine searches using optimized BLAS matrix multiplications without needing to divide by magnitudes during query time."*

### 3. "What is the role of the Context Header?"
> *"Code exhibits high lexical sparsity. An isolated method like `def verify_token(self, token)` lacks its module and class identity. We synthesize a structured context header (`File: auth.py | Class: TokenService | Method: verify_token(...) | Summary: ...`) and prepend it prior to embedding. This grounds the dense vector in its semantic hierarchy."*

### 4. "What is the Purpose of the Phase 3 Dependency Knowledge Graph?"
> *"Dense vector embeddings capture conceptual and lexical semantics, but are blind to deterministic execution and control flow. Our Phase 3 Knowledge Graph parses call expressions, imports, and inheritance from the tree-sitter Concrete Syntax Tree into a directed NetworkX graph. This allows our system to perform transitive blast-radius analysis (e.g. if `verify_token` breaks, what callers across the system are affected) and find shortest invocation chains between components."*

---

## 📂 Project Structure

```
├── .env.example                  # Environment configuration
├── .gitignore                    # Git exclusions
├── README.md                     # Academic documentation & guide
├── DEMO_GUIDE.md                 # Complete guide presentation playbook
├── requirements.txt              # Pinned low-level dependencies
├── src/
│   ├── core/
│   │   ├── models.py             # CodeChunk and SearchResult dataclasses
│   │   └── file_walker.py        # Crawler respecting .gitignore and exclusions
│   ├── chunking/
│   │   ├── parser.py             # Tree-sitter Python parser singleton
│   │   └── ast_chunker.py        # Recursive CST walker for classes & methods
│   ├── indexing/
│   │   ├── embedder.py           # Gemini, OpenAI & Mock embedders with L2 normalization
│   │   └── vector_store.py       # FAISS IndexFlatIP wrapper with persistence
│   ├── search/
│   │   └── retriever.py          # Semantic search engine with AST symbol boosting
│   ├── graph/                    # Phase 3: Code Dependency Knowledge Graph
│   │   ├── graph_models.py       # GraphNode, GraphEdge, GraphStats schemas
│   │   ├── ast_call_visitor.py   # Tree-Sitter visitor for calls, imports, inheritance
│   │   └── dependency_graph.py   # NetworkX DiGraph engine & blast-radius traversals
│   └── web/                      # Interactive Web Demonstration Dashboard
│       ├── server.py             # Native Python HTTP REST API server
│       └── static/               # Single-page glassmorphic UI (HTML, CSS, JS Canvas)
├── scripts/
│   ├── run_phase1_ingestion.py   # Phase 1 CLI demo
│   ├── run_phase2_search.py      # Phase 2 CLI demo with interactive mode
│   ├── run_phase3_graph.py       # Phase 3 CLI demo with blast-radius & call paths
│   └── run_frontend.py           # Web frontend launcher (http://localhost:8000)
└── tests/
    ├── sample_repo/              # Benchmark codebase (auth, db, payments, order_service)
    ├── test_ast_chunker.py       # Phase 1 test suite
    ├── test_vector_store.py      # Phase 2 test suite
    └── test_dependency_graph.py  # Phase 3 test suite
```

---

## 🔮 Upcoming Phases
- **Phase 4**: Hand-rolled ReAct Loop (Pure while-loop LLM agent with tool dispatch).
- **Phase 5**: Reciprocal Rank Fusion (RRF) & Grounded Synthesis with strict `[file:line-line]` attribution.

