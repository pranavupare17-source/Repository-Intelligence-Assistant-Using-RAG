# Guide Presentation & Demo Playbook: Repository Intelligence Assistant

This document is your **step-by-step presentation script and project breakdown** to show your academic guide in 4 days. It explains **current project status**, **what file does what**, **what commands to run**, and **what to say line-by-line**.

---

## 📌 1. Project Current Status### What is Completed (Phases 1, 2 & 3):
* **Phase 1 (AST Ingestion & Code Chunking)**: 100% Complete & Tested.
* **Phase 2 (Embeddings & FAISS Vector Search)**: 100% Complete & Tested.
* **Phase 3 (NetworkX Dependency Knowledge Graph)**: 100% Complete & Tested.
* **Web Demonstration Frontend**: 100% Complete & Interactive.
* **Automated Unit Tests**: 18 / 18 Tests Passing (100% test coverage across all three phases).
* **GitHub Repository**: Synced & up-to-date with clean, professional commit labels.

### Strict Academic Constraint Compliance:
* **Zero high-level frameworks used**: **No** LangChain, **No** LlamaIndex, **No** LangGraph.
* Built exclusively with low-level infrastructure: `tree-sitter-python` (parser), `faiss-cpu` (C++ vector index), `networkx` (graph algorithms), `numpy` (matrix math), and pure Python.

---

## 📂 2. File Map: What Every File Does

Here is a breakdown of every file in the codebase so you can explain any file if your guide asks:

```
Repo Intelligence/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── DEMO_GUIDE.md
├── src/
│   ├── core/
│   │   ├── models.py
│   │   └── file_walker.py
│   ├── chunking/
│   │   ├── parser.py
│   │   └── ast_chunker.py
│   ├── indexing/
│   │   ├── embedder.py
│   │   └── vector_store.py
│   ├── search/
│   │   └── retriever.py
│   ├── graph/
│   │   ├── graph_models.py
│   │   ├── ast_call_visitor.py
│   │   └── dependency_graph.py
│   └── web/
│       ├── server.py
│       └── static/
│           ├── index.html
│           ├── app.css
│           └── app.js
├── scripts/
│   ├── run_phase1_ingestion.py
│   ├── run_phase2_search.py
│   ├── run_phase3_graph.py
│   └── run_frontend.py
└── tests/
    ├── sample_repo/
    │   ├── auth.py
    │   ├── database.py
    │   ├── payment_gateway.py
    │   └── order_service.py
    ├── test_ast_chunker.py
    ├── test_vector_store.py
    └── test_dependency_graph.py
```

### Deep-Dive on Each File:

#### Root Files:
* **[requirements.txt](file:///p:/Projects/Repo%20Intelligence/requirements.txt)**: Declares exact pinned versions of low-level dependencies (`tree-sitter`, `tree-sitter-python`, `faiss-cpu`, `networkx`, `numpy`, `rich`, `pytest`).
* **[.gitignore](file:///p:/Projects/Repo%20Intelligence/.gitignore)**: Prevents cache files (`__pycache__`), virtual environments (`venv`), index dumps (`.faiss_data`), and sensitive `.env` files from cluttering Git.
* **[README.md](file:///p:/Projects/Repo%20Intelligence/README.md)**: Academic documentation with architectural diagrams, comparison tables against naive RAG, and mathematical derivations.

#### Core Layer (`src/core/`):
* **[src/core/models.py](file:///p:/Projects/Repo%20Intelligence/src/core/models.py)**: Defines `CodeChunk` and `SearchResult` with exact `[file:start-end]` citations.
* **[src/core/file_walker.py](file:///p:/Projects/Repo%20Intelligence/src/core/file_walker.py)**: Crawls codebases respecting `.gitignore` patterns and excluding binaries/lockfiles.

#### AST Chunking Layer (`src/chunking/`):
* **[src/chunking/parser.py](file:///p:/Projects/Repo%20Intelligence/src/chunking/parser.py)**: Singleton initializing the tree-sitter C-grammar parser for Python.
* **[src/chunking/ast_chunker.py](file:///p:/Projects/Repo%20Intelligence/src/chunking/ast_chunker.py)**: Cuts chunks strictly at `class_definition` and `function_definition` boundaries; synthesizes context headers.

#### Vector Indexing Layer (`src/indexing/`):
* **[src/indexing/embedder.py](file:///p:/Projects/Repo%20Intelligence/src/indexing/embedder.py)**: Implements $L_2$ unit normalization and deterministic `MockEmbedder` (offline) + Gemini/OpenAI embedders.
* **[src/indexing/vector_store.py](file:///p:/Projects/Repo%20Intelligence/src/indexing/vector_store.py)**: Direct wrapper around native `faiss.IndexFlatIP` with index persistence.

#### Search & Retrieval Layer (`src/search/`):
* **[src/search/retriever.py](file:///p:/Projects/Repo%20Intelligence/src/search/retriever.py)**: Semantic cosine search engine with AST symbol boosting.

#### Phase 3 Knowledge Graph Layer (`src/graph/`):
* **[src/graph/graph_models.py](file:///p:/Projects/Repo%20Intelligence/src/graph/graph_models.py)**: Data structures for `GraphNode`, `GraphEdge`, and `GraphStats`.
* **[src/graph/ast_call_visitor.py](file:///p:/Projects/Repo%20Intelligence/src/graph/ast_call_visitor.py)**: Tree-sitter visitor extracting function call expressions, imports (aliased & relative), and class inheritance.
* **[src/graph/dependency_graph.py](file:///p:/Projects/Repo%20Intelligence/src/graph/dependency_graph.py)**: `CodeKnowledgeGraph` powered by NetworkX; supports caller/callee resolution, transitive blast radius calculations, shortest path search, and JSON serialization.

#### Web Demonstration Layer (`src/web/`):
* **[src/web/server.py](file:///p:/Projects/Repo%20Intelligence/src/web/server.py)**: Standard library Python HTTP REST server with zero node/npm overhead (`/api/status`, `/api/search`, `/api/graph`, `/api/node`, `/api/path`, `/api/chunks`).
* **[src/web/static/](file:///p:/Projects/Repo%20Intelligence/src/web/static/)**: Glassmorphic single-page app with HTML5 Canvas force-directed graph physics, live FAISS search console, AST code inspector, and academic defense matrix.

---

## 🎬 3. How to Present to Your Guide (Step-by-Step Demo)

Follow this sequence during your meeting. Open your terminal in the project directory: `P:\Projects\Repo Intelligence`.

### Step 1: Prove System Correctness with Unit Tests
Run:
```bash
py -3.12 -m pytest tests/ -v
```
**What happens:**
All 18 tests pass in under 1 second.
**What to say to your guide:**
> *"Sir/Ma'am, before showing the features, here is our automated test suite. All 18 tests verify our custom tree-sitter AST parser, line boundary extraction, vector normalization, FAISS IndexFlatIP retrieval, and NetworkX dependency graph mathematically from scratch."*

---

### Step 2: Demonstrate Phase 1 (AST Chunking & Ingestion)
Run:
```bash
py -3.12 scripts/run_phase1_ingestion.py --repo-path tests/sample_repo
```
**What happens:**
A terminal UI appears showing files scanned, semantic chunks produced, exact citations like `[auth.py:28-34]`, and tagged parent classes.
**What to say:**
> *"Existing RAG frameworks like LangChain cut code at arbitrary character lengths, splitting functions in half. Instead, our custom AST chunker uses tree-sitter to parse the Concrete Syntax Tree, guaranteeing that every chunk is a syntactically complete function or class with its enclosing class scope preserved."*

---

### Step 3: Demonstrate Phase 2 (FAISS Cosine Semantic Search)
Run:
```bash
py -3.12 scripts/run_phase2_search.py --repo-path tests/sample_repo --query "how is token expiration verified?"
```
**What happens:**
Retrieves Rank #1 `verify_token` with exact citation `[auth.py:45-68]` and highlighted code snippet.
**What to say:**
> *"Here, when queried with 'how is token expiration verified?', our FAISS vector index retrieves the exact `verify_token` method along with its line range `[auth.py:45-68]`. We don't just return raw code; we ground it in exact file-line citations."*

---

### Step 4: Demonstrate Phase 3 (NetworkX Code Dependency Knowledge Graph)
Run:
```bash
py -3.12 scripts/run_phase3_graph.py --repo-path tests/sample_repo --symbol verify_token
```
**What happens:**
1. Prints architectural metrics: 66 nodes, 104 edges, 5 source files, 5 classes, 22 functions/methods, 50 call-sites, 26 imports.
2. Displays Upstream Callers: shows `validate_checkout` in `order_service.py` calling `self.token_service.verify_token(token)` on line 52.
3. Displays Downstream Callees: shows `hmac.compare_digest`, `time.time()`, etc.
4. **Calculates Blast Radius**: Computes that modifying `verify_token` transitively impacts `validate_checkout`, `TokenService`, `OrderService`, and `process_order`.
5. Shows the shortest invocation chain: `process_order` ──> `validate_checkout` ──> `verify_token`.

**What to say:**
> *"Dense vector embeddings are great for keyword and semantic matching, but blind to code execution flow. Our Phase 3 Dependency Graph parses the AST Concrete Syntax Tree to map exact call-sites and cross-file imports into a directed NetworkX graph. If a developer asks 'What breaks if I change verify_token?', our blast-radius traversal answers with exact mathematical certainty."*

---

### Step 5: Demonstrate the Web Frontend Dashboard Live
Run:
```bash
py -3.12 scripts/run_frontend.py --repo-path tests/sample_repo --port 8000
```
Open **`http://localhost:8000`** in your browser.
**What to demonstrate:**
1. **Interactive Knowledge Graph**:
   * Drag nodes around to show the force-directed physics engine.
   * Click `verify_token` to open the side inspector drawer.
   * Click **"Calculate Blast Radius"**: watch the impacted nodes glow in animated red!
   * Click **"Call-Chain Path"**: type `process_order` to `verify_token` and watch the path highlight in vivid green!
2. **FAISS Semantic Search Console**:
   * Click benchmark chip: *"how is token expiration verified?"*
   * Show cosine score, citation badge `[auth.py:45-68]`, and click **"Show in Knowledge Graph"** to zoom to the node.
3. **AST Chunker Explorer**:
   * Click through source files to view atomic class/function chunks and synthetic context headers.
4. **Academic Defense & Viva Tab**:
   * Show the side-by-side comparison matrix against LangChain.

---

## 🧠 4. Expected Guide Questions & How to Answer (Viva Q&A)

### Q1: "Did you use LangChain, LlamaIndex, or any prebuilt RAG library?"
* **Answer**:
  > *"No, sir/ma'am. Our implementation is written 100% from scratch. We only used low-level infrastructure: tree-sitter for AST parsing, FAISS for index storage, NetworkX for graph traversals, and NumPy for matrix algebra. All chunking boundaries, vector normalization, and search ranking logic are custom Python functions that we wrote line-by-line."*

### Q2: "How does FAISS `IndexFlatIP` compute Cosine Similarity?"
* **Answer**:
  > *"Mathematically, cosine similarity is defined as $\frac{A \cdot B}{\|A\|_2 \|B\|_2}$. In our `embedder.py`, we apply $L_2$ normalization to every vector so that $\|A\|_2 = 1$ and $\|B\|_2 = 1$. Under this unit-norm constraint, the Inner Product $A \cdot B$ is mathematically identical to Cosine Similarity. By using FAISS `IndexFlatIP`, we compute exact cosine similarity at C++ SIMD speed without runtime division overhead."*

### Q3: "What is the purpose of the 'Context Header'?"
* **Answer**:
  > *"In code, function names are often repeated or brief (like `verify()`, `connect()`, or `charge()`). If embedded in isolation, the dense vector has no idea where it belongs. We construct a synthetic header: `File: auth.py | Class: TokenService | Method: verify_token(...)` and prepend it before embedding. This grounds the vector in its enclosing semantic scope."*

### Q4: "How does Phase 3 differ from existing RAG systems?"
* **Answer**:
  > *"Standard RAG systems treat code like disconnected text documents. When you modify code, naive RAG cannot tell you downstream impact. Our Phase 3 parses call expressions and imports from the concrete syntax tree into a NetworkX directed graph. This enables architectural analysis: caller/callee tracing, shortest call chains, and transitive blast-radius computation, bridging the gap between semantic search and software architecture."*

