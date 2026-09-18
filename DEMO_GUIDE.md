# Guide Presentation & Demo Playbook: Repository Intelligence Assistant

This document is your **step-by-step presentation script and project breakdown** to show your academic guide in 4 days. It explains **current project status**, **what file does what**, **what commands to run**, and **what to say line-by-line**.

---

## 📌 1. Project Current Status

### What is Completed (Phases 1 & 2):
* **Phase 1 (AST Ingestion & Code Chunking)**: 100% Complete & Tested.
* **Phase 2 (Embeddings & FAISS Vector Search)**: 100% Complete & Tested.
* **Automated Unit Tests**: 9 / 9 Tests Passing (100% test coverage for core logic).
* **GitHub Repository**: Synced & up-to-date with clean, professional commit labels.

### Strict Academic Constraint Compliance:
* **Zero high-level frameworks used**: **No** LangChain, **No** LlamaIndex, **No** LangGraph.
* Built exclusively with low-level infrastructure: `tree-sitter-python` (parser), `faiss-cpu` (C++ vector index), `numpy` (matrix math), and pure Python.

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
│   └── search/
│       └── retriever.py
├── scripts/
│   ├── run_phase1_ingestion.py
│   └── run_phase2_search.py
└── tests/
    ├── sample_repo/
    │   ├── auth.py
    │   ├── database.py
    │   └── payment_gateway.py
    ├── test_ast_chunker.py
    └── test_vector_store.py
```

### Deep-Dive on Each File:

#### Root Files:
* **[requirements.txt](file:///p:/Projects/Repo%20Intelligence/requirements.txt)**: Declares exact pinned versions of low-level dependencies (`tree-sitter`, `tree-sitter-python`, `faiss-cpu`, `numpy`, `rich`, `pytest`).
* **[.gitignore](file:///p:/Projects/Repo%20Intelligence/.gitignore)**: Prevents cache files (`__pycache__`), virtual environments (`venv`), index dumps (`.faiss_data`), and sensitive `.env` files from cluttering Git.
* **[README.md](file:///p:/Projects/Repo%20Intelligence/README.md)**: Academic documentation with architectural diagrams, comparison tables against naive RAG, and mathematical derivations.

#### Core Layer (`src/core/`):
* **[src/core/models.py](file:///p:/Projects/Repo%20Intelligence/src/core/models.py)**:
  * Defines `CodeChunk`: Stores atomic code units with `{chunk_id, file_path, start_line, end_line, chunk_type, name, parent_class, docstring, code, context_header}`.
  * Property `citation`: Computes exact ground-truth academic citations `[file:start_line-end_line]`.
  * Method `get_embedding_text()`: Generates the context-enriched text payload for embedding.
  * Defines `SearchResult`: Encapsulates matched chunk, cosine similarity score, and rank.
* **[src/core/file_walker.py](file:///p:/Projects/Repo%20Intelligence/src/core/file_walker.py)**:
  * Implements `RepoWalker` and `GitIgnoreFilter`.
  * Crawls any codebase directory, respects `.gitignore` glob patterns, and filters out non-code directories (`node_modules`, `venv`, `build`, `.git`) and lockfiles (`package-lock.json`, `poetry.lock`).

#### AST Chunking Layer (`src/chunking/`):
* **[src/chunking/parser.py](file:///p:/Projects/Repo%20Intelligence/src/chunking/parser.py)**:
  * Singleton initializing the tree-sitter C-grammar parser for Python without reloading shared libraries repeatedly.
* **[src/chunking/ast_chunker.py](file:///p:/Projects/Repo%20Intelligence/src/chunking/ast_chunker.py)**:
  * The heart of Phase 1. Recursively walks the syntax tree.
  * Cuts chunks strictly at `class_definition` and `function_definition` boundaries.
  * Checks if a function is enclosed in a class; if so, tags it as `chunk_type="method"` and sets `parent_class`.
  * Extracts docstrings from the first block statement.
  * Synthesizes the `context_header`: `File: ... | Class: ... | Method: ... | Summary: ...`.

#### Vector Indexing Layer (`src/indexing/`):
* **[src/indexing/embedder.py](file:///p:/Projects/Repo%20Intelligence/src/indexing/embedder.py)**:
  * Implements `normalize_vectors()`: Normalizes vectors to unit length ($\|v\|_2 = 1$).
  * `MockEmbedder`: Deterministic token-hash embedder (384 dims) enabling 100% offline demonstration without API keys.
  * `GeminiEmbedder`: Google Gemini `text-embedding-004` (768 dims).
  * `OpenAIEmbedder`: OpenAI `text-embedding-3-small` (1536 dims).
* **[src/indexing/vector_store.py](file:///p:/Projects/Repo%20Intelligence/src/indexing/vector_store.py)**:
  * Direct wrapper around native `faiss.IndexFlatIP`.
  * Preserves a 1-to-1 index-to-chunk map.
  * Serializes FAISS binary index to `index.faiss` and chunk metadata to `chunks.json`.

#### Search & Retrieval Layer (`src/search/`):
* **[src/search/retriever.py](file:///p:/Projects/Repo%20Intelligence/src/search/retriever.py)**:
  * `semantic_search(query, k)`: Embeds query -> normalizes -> executes FAISS search -> applies AST symbol prioritization boost -> returns ranked hits.
  * `build_index_from_repo()`: End-to-end pipeline wiring walking, AST chunking, batch embedding, and FAISS store creation.

#### Benchmark Repository & Tests (`tests/`):
* **[tests/sample_repo/](file:///p:/Projects/Repo%20Intelligence/tests/sample_repo/)**: Realistic mini-backend with `auth.py` (JWT & password hashing), `database.py` (connection pool & retries), and `payment_gateway.py` (Stripe charges & refunds).
* **[tests/test_ast_chunker.py](file:///p:/Projects/Repo%20Intelligence/tests/test_ast_chunker.py)**: Unit tests for AST line boundaries, parent tagging, and file crawling.
* **[tests/test_vector_store.py](file:///p:/Projects/Repo%20Intelligence/tests/test_vector_store.py)**: Unit tests for vector normalization, mathematical cosine equivalence, FAISS search, and disk persistence.

#### Demonstration Scripts (`scripts/`):
* **[scripts/run_phase1_ingestion.py](file:///p:/Projects/Repo%20Intelligence/scripts/run_phase1_ingestion.py)**: Terminal UI showing AST parsing statistics, parent relationships, and spot-check line numbers.
* **[scripts/run_phase2_search.py](file:///p:/Projects/Repo%20Intelligence/scripts/run_phase2_search.py)**: Interactive search engine showing queries, ranked hits, cosine scores, citations, and highlighted code snippets.

---

## 🎬 3. How to Present to Your Guide (Step-by-Step Demo)

Follow this sequence during your meeting. Open your terminal in the project directory: `P:\Projects\Repo Intelligence`.

### Step 1: Prove System Correctness with Unit Tests
Run:
```bash
py -3.12 -m pytest tests/ -v
```
**What happens:**
All 9 tests pass in under 1 second.
**What to say to your guide:**
> *"Sir/Ma'am, before showing the features, here is our automated test suite. It verifies our custom tree-sitter AST parser, line boundary extraction, vector normalization, and FAISS IndexFlatIP retrieval mathematically from scratch."*

---

### Step 2: Demonstrate Phase 1 (AST Chunking & Ingestion)
Run:
```bash
py -3.12 scripts/run_phase1_ingestion.py --repo-path tests/sample_repo
```
**What happens:**
A terminal UI appears showing:
1. **Summary Box**: 4 files scanned, 18 semantic chunks produced (3 classes, 12 methods, 3 functions).
2. **Spot-Check Table**: Shows exact citations like `[auth.py:28-34]`, symbol `__init__`, and tagged `Parent Class: TokenService`.
3. **Sample Chunk Box**: Displays the exact code snippet for `TokenService.__init__` with line numbers 28–34.

**What to point out on screen:**
* Point to the **Parent Class** column: show how methods inside a class are automatically tagged with their parent class.
* Point to the **Citation column**: show that line numbers are exact (`[auth.py:45-68]`).
* **What to say:**
  > *"Existing RAG frameworks like LangChain cut code at arbitrary character lengths, splitting functions in half. Instead, our custom AST chunker uses tree-sitter to parse the Concrete Syntax Tree, guaranteeing that every chunk is a syntactically complete function or class with its enclosing class scope preserved."*

---

### Step 3: Demonstrate Phase 2 (FAISS Cosine Semantic Search)
Run:
```bash
py -3.12 scripts/run_phase2_search.py --repo-path tests/sample_repo --query "how is token expiration verified?"
```
**What happens:**
1. It ingests the repo and builds the FAISS `IndexFlatIP` vector index.
2. It executes the query and returns **Rank #1**:
   * **Citation**: `[auth.py:45-68]`
   * **Score**: Cosine score
   * **Code**: The exact `def verify_token(...)` implementation checking `int(time.time()) > int(expires_at_str)`.

**What to say:**
> *"Here, when queried with 'how is token expiration verified?', our FAISS vector index retrieves the exact `verify_token` method along with its line range `[auth.py:45-68]`. We don't just return raw code; we ground it in exact file-line citations."*

---

### Step 4: Run an Interactive Search Live with Your Guide
Run:
```bash
py -3.12 scripts/run_phase2_search.py --repo-path tests/sample_repo --interactive
```
**What to do:**
Invite your guide to type any question, or test these yourself in front of them:
1. Query: `where is database connection pool initialized?`
   * *Returns: `DatabasePool.initialize` and `class DatabasePool [database.py:9-49]`*
2. Query: `how are credit card charges handled?`
   * *Returns: `StripeGateway.charge [payment_gateway.py:16-36]`*
3. Query: `hash user password`
   * *Returns: `hash_password [auth.py:11-21]`*

Type `exit` to quit when done.

---

## 🧠 4. Expected Guide Questions & How to Answer (Viva Q&A)

### Q1: "Did you use LangChain, LlamaIndex, or any prebuilt RAG library?"
* **Answer**:
  > *"No, sir/ma'am. Our implementation is written 100% from scratch. We only used low-level infrastructure: tree-sitter for AST parsing, FAISS for index storage, and NumPy for matrix algebra. All chunking boundaries, vector normalization, and search ranking logic are custom Python functions that we wrote line-by-line."*

### Q2: "How does FAISS `IndexFlatIP` compute Cosine Similarity?"
* **Answer**:
  > *"Mathematically, cosine similarity is defined as $\frac{A \cdot B}{\|A\|_2 \|B\|_2}$. In our `embedder.py`, we apply $L_2$ normalization to every vector so that $\|A\|_2 = 1$ and $\|B\|_2 = 1$. Under this unit-norm constraint, the Inner Product $A \cdot B$ is mathematically identical to Cosine Similarity. By using FAISS `IndexFlatIP`, we compute exact cosine similarity at C++ SIMD speed without runtime division overhead."*

### Q3: "What is the purpose of the 'Context Header'?"
* **Answer**:
  > *"In code, function names are often repeated or brief (like `verify()`, `connect()`, or `charge()`). If embedded in isolation, the dense vector has no idea where it belongs. We construct a synthetic header: `File: auth.py | Class: TokenService | Method: verify_token(...)` and prepend it before embedding. This grounds the vector in its enclosing semantic scope."*

### Q4: "What will you build next in the upcoming phases?"
* **Answer**:
  > *"In Phase 3, we will construct a Code Dependency Knowledge Graph using NetworkX to map call graphs and import relationships. In Phase 4, we will build a hand-rolled ReAct agent loop from scratch that selects between vector search and graph traversal. In Phase 5, we will implement Reciprocal Rank Fusion (RRF) and grounded answer synthesis with mandatory `[file:line-line]` citations."*
