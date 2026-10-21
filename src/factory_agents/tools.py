"""File tools for agents, confined to the target repo root."""

from pathlib import Path

from langchain_core.tools import BaseTool, StructuredTool


class ToolError(Exception):
    """A tool call was rejected or failed."""


def resolve_safe(root: Path, rel: str) -> Path:
    """Resolve rel inside root, rejecting absolute paths, '..', .git and symlink escapes."""
    p = Path(rel)
    if p.is_absolute():
        raise ToolError(f"absolute paths are not allowed: {rel}")
    if ".." in p.parts:
        raise ToolError(f"'..' is not allowed: {rel}")
    if ".git" in p.parts:
        raise ToolError(f"access to .git is not allowed: {rel}")
    root = Path(root).resolve()
    resolved = (root / p).resolve()
    try:
        inner = resolved.relative_to(root)
    except ValueError:
        raise ToolError(f"path escapes the repository: {rel}") from None
    if ".git" in inner.parts:
        raise ToolError(f"access to .git is not allowed: {rel}")
    return resolved


class FileTools:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def read_file(self, path: str) -> str:
        p = resolve_safe(self.root, path)
        try:
            return p.read_text()
        except (OSError, UnicodeDecodeError) as e:
            raise ToolError(f"cannot read {path}: {e}") from e

    def write_file(self, path: str, content: str) -> str:
        p = resolve_safe(self.root, path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        except OSError as e:
            raise ToolError(f"cannot write {path}: {e}") from e
        return f"wrote {path}"

    def list_files(self, path: str = ".") -> str:
        base = resolve_safe(self.root, path)
        if not base.is_dir():
            raise ToolError(f"not a directory: {path}")
        files = sorted(
            f.relative_to(self.root).as_posix()
            for f in base.rglob("*")
            if f.is_file() and ".git" not in f.relative_to(self.root).parts
        )
        return "\n".join(files)


def _safe(fn):
    def wrapper(**kwargs) -> str:
        try:
            return fn(**kwargs)
        except ToolError as e:
            return f"Error: {e}"

    return wrapper


def build_tools(root: Path) -> list[BaseTool]:
    ft = FileTools(root)

    def read_file(path: str) -> str:
        """Read a text file at a path relative to the repo root."""
        return _safe(ft.read_file)(path=path)

    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file at a path relative to the repo root."""
        return _safe(ft.write_file)(path=path, content=content)

    def list_files(path: str = ".") -> str:
        """List files (recursively) under a directory relative to the repo root."""
        return _safe(ft.list_files)(path=path)

    return [StructuredTool.from_function(f) for f in (read_file, write_file, list_files)]
