"""
Pure-Python repository file crawler.
Walks the codebase tree, parses and respects .gitignore rules,
and filters out non-code, virtualenvs, dependencies, and lockfiles.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Set, Iterator


# Default directory names that should ALWAYS be excluded
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".git",
    "build",
    "dist",
    ".eggs",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".faiss_data",
}

# Default file patterns to exclude (lockfiles, minified files, binary extensions)
DEFAULT_EXCLUDED_PATTERNS: Set[str] = {
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "*.min.js",
    "*.min.css",
    "*.min.py",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.zip",
    "*.tar.gz",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
}


class GitIgnoreFilter:
    """
    Parses .gitignore syntax and matches file paths against patterns.
    Implements standard gitignore semantics without external library dependencies.
    """
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.rules: List[tuple[str, bool]] = []  # (pattern, is_negation)
        self._load_gitignore()

    def _load_gitignore(self) -> None:
        gitignore_path = self.repo_root / ".gitignore"
        if not gitignore_path.is_file():
            return

        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    # Skip blank lines and comments
                    if not line or line.startswith("#"):
                        continue
                    
                    is_negation = line.startswith("!")
                    if is_negation:
                        line = line[1:].strip()
                    
                    # Strip leading and trailing slashes for standard glob matching
                    rule = line.strip("/")
                    self.rules.append((rule, is_negation))
        except Exception:
            pass

    def is_ignored(self, rel_path: str) -> bool:
        """Determines if a path relative to repo_root is ignored by .gitignore."""
        normalized_path = rel_path.replace("\\", "/")
        path_parts = normalized_path.split("/")
        
        ignored = False
        for pattern, is_negation in self.rules:
            # Check matching against full path or individual filename / dir name
            matches = (
                fnmatch.fnmatch(normalized_path, pattern)
                or fnmatch.fnmatch(normalized_path, f"*{pattern}*")
                or any(fnmatch.fnmatch(part, pattern) for part in path_parts)
            )
            if matches:
                ignored = not is_negation
        return ignored


class RepoWalker:
    """
    Crawls a repository directory tree, filtering files based on gitignore
    rules and file-type configurations.
    """
    def __init__(
        self,
        repo_path: str | Path,
        allowed_extensions: Set[str] | None = None,
        custom_excludes: Set[str] | None = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.allowed_extensions = allowed_extensions or {".py"}
        self.excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
        if custom_excludes:
            self.excluded_dirs.update(custom_excludes)
        self.gitignore = GitIgnoreFilter(self.repo_path)

    def walk(self) -> Iterator[tuple[Path, str]]:
        """
        Yields tuples of (absolute_path, relative_path) for all valid code files.
        """
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Target repository path does not exist: {self.repo_path}")

        for root, dirs, files in os.walk(self.repo_path, topdown=True):
            current_path = Path(root)
            
            # Prune excluded directories in-place so os.walk does not descend into them
            dirs[:] = [
                d for d in dirs
                if d not in self.excluded_dirs
                and not d.endswith(".egg-info")
                and not self.gitignore.is_ignored(
                    str((current_path / d).relative_to(self.repo_path))
                )
            ]

            for file_name in files:
                file_path = current_path / file_name
                try:
                    rel_path = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
                except ValueError:
                    continue

                # Check default file patterns (lockfiles, minified, etc.)
                if any(fnmatch.fnmatch(file_name, pat) for pat in DEFAULT_EXCLUDED_PATTERNS):
                    continue

                # Check .gitignore
                if self.gitignore.is_ignored(rel_path):
                    continue

                # Check file extension
                if file_path.suffix.lower() not in self.allowed_extensions:
                    continue

                yield file_path, rel_path
