import os
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional, Set
import streamlit as st
from rag_system import RAGSystem

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMMON_IGNORE_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".vscode",
    ".idea",
    "node_modules",
    "venv",
    ".env",
    "build",
    "dist",
    "target",  # For Java/Rust
    "*.egg-info",  # Python packaging
}
COMMON_IGNORE_FILES: Set[str] = {".DS_Store", "*.pyc", "*.log", "*.swp", "*.swo"}
MAX_PROJECT_CONTEXT_CHARS: int = (
    1000000  # Max characters for all_file_contents to send to AI
)

# Global RAG system instance
_rag_systems: Dict[str, RAGSystem] = {}


def get_rag_system(project_path: str) -> RAGSystem:
    """Get or create RAG system for project"""
    global _rag_systems

    if project_path not in _rag_systems:
        _rag_systems[project_path] = RAGSystem(project_path)
        # Index project if not already cached
        if not _rag_systems[project_path].chunks:
            logger.info("Indexing project for RAG...")
            _rag_systems[project_path].index_project()

    return _rag_systems[project_path]


def get_rag_context(
    user_query: str,
    project_path: str,
    current_file: Optional[str] = None,
    max_tokens: int = 20000,
) -> Dict[str, Any]:
    """Enhanced RAG-based context that includes full files when needed"""
    try:
        rag_system = get_rag_system(project_path)

        # Use the new smart context retrieval
        context = rag_system.get_relevant_context_smart(
            user_query, current_file, max_tokens, include_full_files=True
        )

        # Format for AI agent
        file_paths = context.get("file_paths", [])
        all_file_contents = context.get("all_file_contents", {})
        rag_metadata = context.get("rag_metadata", {})

        # Add instructions for the AI about file handling
        if rag_metadata.get("full_files"):
            instructions = "\n[CONTEXT INSTRUCTIONS]\n"
            instructions += "The following files are provided with FULL CONTENT and can be edited:\n"
            for file in rag_metadata["full_files"]:
                instructions += f"- {file}\n"
            instructions += "\nFiles marked as [PARTIAL CONTEXT] are read-only. "
            instructions += (
                "If you need to edit them, ask the user to open the file first.\n"
            )

            # Prepend instructions to the context
            if all_file_contents:
                first_file = list(all_file_contents.keys())[0]
                all_file_contents = {"_instructions": instructions, **all_file_contents}

        return {
            "file_paths": file_paths,
            "all_file_contents": all_file_contents,
            "rag_metadata": rag_metadata,
        }

    except Exception as e:
        logger.error(f"RAG context retrieval failed: {e}")
        # Fallback to original method
        return get_all_project_files_context(project_path)


def invalidate_rag_cache(project_path: str):
    """Invalidate RAG cache for project (call when files change)"""
    global _rag_systems

    if project_path in _rag_systems:
        _rag_systems[project_path].invalidate_cache()
        del _rag_systems[project_path]


def display_file_tree_sidebar(
    node: Dict[str, Any],
    on_file_click,
    selected_file_path: Optional[str] = None,
    indent_level: int = 0,
):
    """
    Recursively renders a collapsible file tree in the Streamlit sidebar.
    - node: dict representing the current folder/file node.
    - on_file_click: function to call with absolute path when a file is clicked.
    - selected_file_path: the currently selected file's absolute path.
    - indent_level: depth level for nested display indentation.
    """
    indent = " " * indent_level * 2  # Visual indent using spaces

    if node["type"] == "directory":
        with st.sidebar.expander(f"{indent}📁 {node['name']}", expanded=False):
            for child in node.get("children", []):
                display_file_tree_sidebar(
                    child,
                    on_file_click,
                    selected_file_path,
                    indent_level + 1,
                )
    else:
        # Highlight selected file
        is_selected = selected_file_path == node["path"]
        if st.sidebar.button(f"{indent}📄 {node['name']}", key=node["path"]):
            on_file_click(node["path"])


def get_project_structure(
    root_path_str: str,
    ignore_dirs: Optional[Set[str]] = None,
    ignore_files: Optional[Set[str]] = None,
) -> Optional[Dict[str, Any]]:
    effective_ignore_dirs = (
        ignore_dirs if ignore_dirs is not None else COMMON_IGNORE_DIRS
    )
    effective_ignore_files = (
        ignore_files if ignore_files is not None else COMMON_IGNORE_FILES
    )

    root_path = Path(root_path_str).resolve()
    if not root_path.is_dir():
        logger.error(f"Project path not found or is not a directory: {root_path}")
        return None

    def _is_ignored(item: Path, project_root: Path) -> bool:
        if item.name in effective_ignore_dirs or item.name in effective_ignore_files:
            return True
        # Check wildcard patterns for ignored dirs/files (simple glob for now)
        for pattern in effective_ignore_dirs:  # e.g. "*.egg-info"
            if "*" in pattern and item.is_dir() and item.match(pattern):
                return True
        for pattern in effective_ignore_files:  # e.g. "*.pyc"
            if "*" in pattern and item.is_file() and item.match(pattern):
                return True

        try:
            relative_to_root = item.relative_to(project_root)
            for part in relative_to_root.parts[:-1]:
                if part in effective_ignore_dirs:
                    return True
        except ValueError:
            pass
        return False

    def _build_tree(current_path: Path, project_root: Path) -> Dict[str, Any]:
        tree_node: Dict[str, Any] = {
            "name": current_path.name,
            "path": str(
                current_path.resolve()
            ),  # Keep absolute path for server-side reference
            "relative_path": str(
                current_path.relative_to(project_root).as_posix()
            ),  # Add relative path for client
            "type": "directory" if current_path.is_dir() else "file",
            "children": [],
        }
        if current_path.is_dir():
            sorted_items = sorted(
                current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())
            )
            for item in sorted_items:
                if _is_ignored(item, project_root):
                    continue
                tree_node["children"].append(_build_tree(item, project_root))
        return tree_node

    return _build_tree(root_path, root_path)


def get_all_project_files_context(
    project_path_str: str, max_total_chars: int = MAX_PROJECT_CONTEXT_CHARS
) -> Dict[str, Any]:
    """Original method - kept as fallback"""
    project_path = Path(project_path_str).resolve()
    if not project_path.is_dir():
        return {"file_paths": [], "all_file_contents": {}}

    all_relative_files: List[str] = []
    file_contents_map: Dict[str, str] = {}
    current_total_chars: int = 0
    all_items_in_project = sorted(
        list(project_path.rglob("*")), key=lambda p: p.as_posix()
    )

    def _is_path_ignored(item_path: Path, root_path: Path) -> bool:
        if (
            item_path.name in COMMON_IGNORE_DIRS
            or item_path.name in COMMON_IGNORE_FILES
        ):
            return True
        for pattern in COMMON_IGNORE_DIRS:
            if "*" in pattern and item_path.is_dir() and item_path.match(pattern):
                return True
        for pattern in COMMON_IGNORE_FILES:
            if "*" in pattern and item_path.is_file() and item_path.match(pattern):
                return True
        try:
            relative_path_to_root = item_path.relative_to(root_path)
            for part in relative_path_to_root.parts[:-1]:
                if part in COMMON_IGNORE_DIRS:
                    return True
        except ValueError:
            return False
        return False

    for item in all_items_in_project:
        if _is_path_ignored(item, project_path):
            continue
        if item.is_file():
            try:
                relative_path_str = str(item.relative_to(project_path).as_posix())
            except ValueError:
                continue
            all_relative_files.append(relative_path_str)
            try:
                if current_total_chars < max_total_chars:
                    content = item.read_text(encoding="utf-8", errors="ignore")
                    chars_to_add = len(content)
                    if chars_to_add + current_total_chars > max_total_chars:
                        can_add_chars = max_total_chars - current_total_chars
                        if can_add_chars <= 0:
                            file_contents_map[relative_path_str] = (
                                "... [CONTENT SKIPPED - TOTAL SIZE LIMIT REACHED]"
                            )
                            continue
                        content = (
                            content[:can_add_chars]
                            + f"\n... [TRUNCATED - {chars_to_add - can_add_chars} of {chars_to_add} chars omitted]"
                        )
                        current_total_chars += can_add_chars
                    else:
                        current_total_chars += chars_to_add
                    file_contents_map[relative_path_str] = content
                else:
                    file_contents_map[relative_path_str] = (
                        "... [CONTENT SKIPPED - TOTAL SIZE LIMIT REACHED PRIOR TO THIS FILE]"
                    )
            except UnicodeDecodeError:
                file_contents_map[relative_path_str] = (
                    "[Error: Could not decode file as UTF-8. Likely a binary file.]"
                )
            except Exception as e:
                file_contents_map[relative_path_str] = f"[Error reading file: {str(e)}]"
    return {
        "file_paths": sorted(all_relative_files),
        "all_file_contents": file_contents_map,
    }


def read_file_content(file_path_str: str) -> Optional[str]:
    try:
        return Path(file_path_str).resolve().read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading file {file_path_str}: {e}")
        return None


def write_file_content(file_path_str: str, content: str) -> bool:
    try:
        path = Path(file_path_str).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        # Invalidate RAG cache for the project when files are modified
        project_path = None
        for parent in path.parents:
            if (
                (parent / ".git").exists()
                or (parent / "requirements.txt").exists()
                or (parent / "package.json").exists()
            ):
                project_path = str(parent)
                break

        if project_path:
            invalidate_rag_cache(project_path)

        return True
    except Exception as e:
        logger.error(f"Error writing file {file_path_str}: {e}")
        return False


def create_folder_if_not_exists(folder_path_str: str) -> bool:
    try:
        Path(folder_path_str).resolve().mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating folder {folder_path_str}: {e}")
        return False
