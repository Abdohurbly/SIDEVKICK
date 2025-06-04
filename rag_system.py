import os
import json
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import ast
import re
import networkx as nx
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata"""

    content: str
    file_path: str
    chunk_id: str
    start_line: int
    end_line: int
    chunk_type: str  # function, class, module, config, etc.
    language: str
    description: str
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    embedding: Optional[np.ndarray] = None
    # New fields for enhanced retrieval
    exported_symbols: List[str] = field(default_factory=list)
    imported_from: Dict[str, List[str]] = field(default_factory=dict)
    ui_components: List[str] = field(default_factory=list)
    css_classes: List[str] = field(default_factory=list)
    dom_ids: List[str] = field(default_factory=list)


class FileDependencyAnalyzer:
    """Analyzes file dependencies and relationships"""

    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.file_to_symbols = defaultdict(set)  # file -> exported symbols
        self.symbol_to_file = {}  # symbol -> file
        self.ui_dependencies = defaultdict(set)  # component -> files

    def analyze_project(self, chunks: Dict[str, CodeChunk]) -> None:
        """Build dependency graph from chunks"""
        # First pass: collect all exports and definitions
        for chunk in chunks.values():
            file_path = chunk.file_path

            # Collect exported symbols
            if chunk.language in ["javascript", "typescript"]:
                self._extract_js_exports(chunk, file_path)
            elif chunk.language == "python":
                self._extract_python_exports(chunk, file_path)

            # Collect UI components
            if chunk.ui_components:
                for component in chunk.ui_components:
                    self.ui_dependencies[component].add(file_path)

        # Second pass: build dependency graph
        for chunk in chunks.values():
            file_path = chunk.file_path

            # Add file node if not exists
            if not self.dependency_graph.has_node(file_path):
                self.dependency_graph.add_node(file_path, type="file")

            # Add import dependencies
            for imp in chunk.imports:
                if imp in self.symbol_to_file:
                    dep_file = self.symbol_to_file[imp]
                    if dep_file != file_path:
                        self.dependency_graph.add_edge(
                            file_path, dep_file, type="import", symbol=imp
                        )

            # Add imported_from dependencies
            for source, symbols in chunk.imported_from.items():
                # Resolve relative imports
                resolved_path = self._resolve_import_path(source, file_path)
                if resolved_path and resolved_path != file_path:
                    self.dependency_graph.add_edge(
                        file_path, resolved_path, type="import", symbols=symbols
                    )

    def _extract_js_exports(self, chunk: CodeChunk, file_path: str):
        """Extract JavaScript/TypeScript exports"""
        content = chunk.content

        # Default exports
        if re.search(r"export\s+default", content):
            self.file_to_symbols[file_path].add(f"{file_path}:default")
            self.symbol_to_file[f"{file_path}:default"] = file_path

        # Named exports
        exports = re.findall(
            r"export\s+(?:const|let|var|function|class)\s+(\w+)", content
        )
        for export in exports:
            self.file_to_symbols[file_path].add(export)
            self.symbol_to_file[export] = file_path
            chunk.exported_symbols.append(export)

        # Export statements
        export_statements = re.findall(r"export\s*\{([^}]+)\}", content)
        for statement in export_statements:
            symbols = [s.strip() for s in statement.split(",")]
            for symbol in symbols:
                if " as " in symbol:
                    _, alias = symbol.split(" as ")
                    symbol = alias.strip()
                else:
                    symbol = symbol.strip()
                self.file_to_symbols[file_path].add(symbol)
                self.symbol_to_file[symbol] = file_path
                chunk.exported_symbols.append(symbol)

    def _extract_python_exports(self, chunk: CodeChunk, file_path: str):
        """Extract Python exports (public symbols)"""
        # In Python, all top-level definitions are "exported"
        for func in chunk.functions:
            if not func.startswith("_"):  # Public function
                self.file_to_symbols[file_path].add(func)
                self.symbol_to_file[func] = file_path
                chunk.exported_symbols.append(func)

        for cls in chunk.classes:
            if not cls.startswith("_"):  # Public class
                self.file_to_symbols[file_path].add(cls)
                self.symbol_to_file[cls] = file_path
                chunk.exported_symbols.append(cls)

    def _resolve_import_path(
        self, import_path: str, current_file: str
    ) -> Optional[str]:
        """Resolve relative import paths"""
        if import_path.startswith("."):
            # Relative import
            current_dir = Path(current_file).parent
            resolved = current_dir / import_path

            # Try different extensions
            for ext in [".js", ".jsx", ".ts", ".tsx", ".py", ""]:
                test_path = str(resolved) + ext
                if test_path in self.file_to_symbols:
                    return test_path

            # Try index files
            for index in [
                "index.js",
                "index.jsx",
                "index.ts",
                "index.tsx",
                "__init__.py",
            ]:
                test_path = str(resolved / index)
                if test_path in self.file_to_symbols:
                    return test_path

        return None

    def get_related_files(self, file_path: str, depth: int = 2) -> Set[str]:
        """Get files related to the given file up to certain depth"""
        related = set()

        if file_path not in self.dependency_graph:
            return related

        # Get direct dependencies and dependents
        for neighbor in nx.all_neighbors(self.dependency_graph, file_path):
            related.add(neighbor)

        # Get indirect dependencies up to depth
        if depth > 1:
            paths = nx.single_source_shortest_path(
                self.dependency_graph, file_path, cutoff=depth
            )
            for target, path in paths.items():
                if len(path) <= depth:
                    related.add(target)

        # Get reverse dependencies (files that depend on this file)
        reverse_graph = self.dependency_graph.reverse()
        if file_path in reverse_graph:
            paths = nx.single_source_shortest_path(
                reverse_graph, file_path, cutoff=depth
            )
            for target, path in paths.items():
                if len(path) <= depth:
                    related.add(target)

        return related

    def get_ui_related_files(self, query: str) -> Set[str]:
        """Get files related to UI components mentioned in query"""
        related = set()

        # Extract potential component names from query
        # Look for PascalCase words (typical React components)
        potential_components = re.findall(r"\b[A-Z][a-zA-Z]+\b", query)

        # Look for specific UI terms
        ui_terms = [
            "button",
            "modal",
            "dialog",
            "form",
            "input",
            "navbar",
            "header",
            "footer",
            "sidebar",
            "menu",
            "dropdown",
            "table",
            "card",
            "list",
            "grid",
            "layout",
            "container",
            "wrapper",
        ]

        query_lower = query.lower()
        for term in ui_terms:
            if term in query_lower:
                # Find components containing this term
                for component, files in self.ui_dependencies.items():
                    if term in component.lower():
                        related.update(files)

        # Check exact component matches
        for component in potential_components:
            if component in self.ui_dependencies:
                related.update(self.ui_dependencies[component])

        return related


class CodeAnalyzer:
    """Enhanced code analyzer with dependency extraction"""

    @staticmethod
    def extract_javascript_imports(content: str) -> Dict[str, List[str]]:
        """Extract JavaScript/TypeScript imports with their sources"""
        imports = {}

        # ES6 imports
        # import { x, y } from 'module'
        es6_imports = re.findall(
            r'import\s*\{([^}]+)\}\s*from\s*[\'"]([^\'"]+)[\'"]', content
        )
        for symbols, source in es6_imports:
            symbol_list = [s.strip() for s in symbols.split(",")]
            imports[source] = symbol_list

        # import x from 'module'
        default_imports = re.findall(
            r'import\s+(\w+)\s+from\s*[\'"]([^\'"]+)[\'"]', content
        )
        for symbol, source in default_imports:
            if source in imports:
                imports[source].append(symbol)
            else:
                imports[source] = [symbol]

        # import * as x from 'module'
        namespace_imports = re.findall(
            r'import\s*\*\s*as\s+(\w+)\s+from\s*[\'"]([^\'"]+)[\'"]', content
        )
        for symbol, source in namespace_imports:
            if source in imports:
                imports[source].append(f"* as {symbol}")
            else:
                imports[source] = [f"* as {symbol}"]

        return imports

    @staticmethod
    def extract_ui_components(content: str, language: str) -> List[str]:
        """Extract UI component references"""
        components = []

        if language in ["javascript", "typescript"]:
            # JSX components
            jsx_components = re.findall(r"<([A-Z]\w+)", content)
            components.extend(jsx_components)

            # React class components
            class_components = re.findall(
                r"class\s+(\w+)\s+extends\s+(?:React\.)?Component", content
            )
            components.extend(class_components)

            # Function components (heuristic: PascalCase functions returning JSX)
            func_components = re.findall(
                r"(?:function|const)\s+([A-Z]\w+)\s*(?:=|\()", content
            )
            components.extend(func_components)

        elif language == "html":
            # Custom elements
            custom_elements = re.findall(r"<([a-z]+-[a-z]+)", content)
            components.extend(custom_elements)

        return list(set(components))  # Remove duplicates

    @classmethod
    def analyze_code(cls, content: str, file_path: str) -> Dict[str, Any]:
        """Enhanced code analysis with dependency information"""
        language = cls.detect_language(file_path)
        base_analysis = cls.analyze_code_original(content, file_path)

        # Add enhanced analysis
        if language in ["javascript", "typescript"]:
            base_analysis["imported_from"] = cls.extract_javascript_imports(content)

        base_analysis["ui_components"] = cls.extract_ui_components(content, language)

        # Extract CSS classes and IDs for style dependencies
        css_classes = re.findall(r'className\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        css_classes.extend(re.findall(r'class\s*=\s*[\'"]([^\'"]+)[\'"]', content))
        base_analysis["css_classes"] = list(set(css_classes))

        dom_ids = re.findall(r'id\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        base_analysis["dom_ids"] = list(set(dom_ids))

        return base_analysis

    @classmethod
    def analyze_code_original(cls, content: str, file_path: str) -> Dict[str, Any]:
        """Original analyze_code method renamed"""
        # Original implementation from your code
        language = cls.detect_language(file_path)

        if language == "python":
            functions, classes, imports = cls.extract_python_elements(content)
        elif language in ["javascript", "typescript"]:
            functions, classes, imports = cls.extract_javascript_elements(content)
        elif language == "golang":
            functions, classes, imports = cls.extract_golang_elements(content)
        elif language == "html":
            functions, classes, imports = cls.extract_html_elements(content)
        elif language == "css":
            functions, classes, imports = cls.extract_css_elements(content)
        else:
            # Generic extraction for other languages
            functions = re.findall(
                r"(?:function|def|func)\s+(\w+)", content, re.IGNORECASE
            )
            classes = re.findall(r"class\s+(\w+)", content, re.IGNORECASE)
            imports = re.findall(
                r'(?:import|include|require)\s+[\'"]*([^\s\'"]+)',
                content,
                re.IGNORECASE,
            )

        # Calculate complexity (language-specific keywords)
        if language == "python":
            complexity_keywords = [
                "if",
                "elif",
                "else",
                "for",
                "while",
                "try",
                "except",
                "with",
            ]
        elif language in ["javascript", "typescript"]:
            complexity_keywords = [
                "if",
                "else",
                "for",
                "while",
                "try",
                "catch",
                "switch",
                "case",
            ]
        elif language == "golang":
            complexity_keywords = ["if", "else", "for", "switch", "case", "defer", "go"]
        elif language == "html":
            complexity_keywords = ["script", "style", "form", "table"]
        elif language == "css":
            complexity_keywords = [
                "@media",
                "@keyframes",
                "@supports",
                "hover",
                "active",
            ]
        else:
            complexity_keywords = ["if", "else", "for", "while", "try", "catch"]

        complexity_score = sum(
            len(re.findall(rf"\b{keyword}\b", content, re.IGNORECASE))
            for keyword in complexity_keywords
        )

        return {
            "language": language,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "complexity_score": float(complexity_score),
        }

    # Keep all the original extract_* methods from your implementation
    @staticmethod
    def detect_language(file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "golang",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "css",
            ".sass": "css",
            ".less": "css",
            ".sql": "sql",
            ".md": "markdown",
            ".txt": "text",
        }
        return language_map.get(ext, "unknown")

    @staticmethod
    def extract_python_elements(content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract functions, classes, and imports from Python code"""
        functions = []
        classes = []
        imports = []

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            # If parsing fails, use regex fallback
            functions.extend(re.findall(r"def\s+(\w+)", content))
            classes.extend(re.findall(r"class\s+(\w+)", content))
            imports.extend(re.findall(r"import\s+(\w+)", content))
            imports.extend(re.findall(r"from\s+(\w+)", content))

        return functions, classes, imports

    @staticmethod
    def extract_javascript_elements(
        content: str,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Extract functions, classes, and imports from JavaScript/TypeScript"""
        functions = []
        classes = []
        imports = []

        # Function patterns
        functions.extend(re.findall(r"function\s+(\w+)", content))
        functions.extend(re.findall(r"const\s+(\w+)\s*=\s*(?:async\s+)?\(", content))
        functions.extend(re.findall(r"(\w+)\s*:\s*(?:async\s+)?function", content))
        functions.extend(re.findall(r"(\w+)\s*=\s*(?:async\s+)?\(.*?\)\s*=>", content))
        functions.extend(re.findall(r"export\s+(?:async\s+)?function\s+(\w+)", content))

        # Class patterns
        classes.extend(re.findall(r"class\s+(\w+)", content))
        classes.extend(re.findall(r"export\s+class\s+(\w+)", content))

        # Import patterns
        imports.extend(re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', content))
        imports.extend(re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content))
        imports.extend(re.findall(r'import\s+[\'"]([^\'"]+)[\'"]', content))

        return functions, classes, imports

    @staticmethod
    def extract_golang_elements(content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract functions, structs, and imports from Go code"""
        functions = []
        classes = []  # Structs in Go
        imports = []

        # Function patterns
        functions.extend(re.findall(r"func\s+(\w+)", content))
        functions.extend(
            re.findall(r"func\s+\(\w+\s+\*?\w+\)\s+(\w+)", content)
        )  # Methods

        # Struct patterns (classes equivalent in Go)
        classes.extend(re.findall(r"type\s+(\w+)\s+struct", content))
        classes.extend(re.findall(r"type\s+(\w+)\s+interface", content))

        # Import patterns
        imports.extend(re.findall(r'import\s+"([^"]+)"', content))
        imports.extend(re.findall(r'import\s+\(\s*"([^"]+)"', content))
        imports.extend(re.findall(r'"([^"]+)"\s*$', content, re.MULTILINE))

        return functions, classes, imports

    @staticmethod
    def extract_html_elements(content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract components, IDs, and classes from HTML"""
        functions = []  # Custom elements/components
        classes = []  # CSS classes
        imports = []  # Scripts and stylesheets

        # Custom elements and components
        functions.extend(re.findall(r"<(\w+-\w+)", content))  # Custom elements
        functions.extend(re.findall(r"<([A-Z]\w+)", content))  # React components

        # CSS classes
        classes.extend(re.findall(r'class\s*=\s*[\'"]([^\'"]+)[\'"]', content))

        # Scripts and stylesheets
        imports.extend(re.findall(r'<script.*?src\s*=\s*[\'"]([^\'"]+)[\'"]', content))
        imports.extend(re.findall(r'<link.*?href\s*=\s*[\'"]([^\'"]+)[\'"]', content))

        return functions, classes, imports

    @staticmethod
    def extract_css_elements(content: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract selectors, classes, and imports from CSS"""
        functions = []  # Mixins, functions
        classes = []  # CSS classes and IDs
        imports = []  # @import statements

        # CSS classes and IDs
        classes.extend(re.findall(r"\.([a-zA-Z_-][\w-]*)", content))
        classes.extend(re.findall(r"#([a-zA-Z_-][\w-]*)", content))

        # CSS functions and mixins (SCSS/SASS)
        functions.extend(re.findall(r"@mixin\s+([a-zA-Z_-][\w-]*)", content))
        functions.extend(re.findall(r"@function\s+([a-zA-Z_-][\w-]*)", content))

        # Imports
        imports.extend(re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', content))
        imports.extend(re.findall(r'@import\s+url\([\'"]?([^\'"]+)[\'"]?\)', content))

        return functions, classes, imports


class CodeChunker:
    """Enhanced chunker with UI-aware chunking"""

    def __init__(self, max_chunk_size: int = 2000):
        self.max_chunk_size = max_chunk_size

    def _create_chunk(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
    ) -> Dict[str, Any]:
        """Enhanced chunk creation with dependency information"""
        analysis = CodeAnalyzer.analyze_code(content, file_path)

        # Generate description
        description = self._generate_description(
            content, file_path, chunk_type, analysis
        )

        # Create unique chunk ID
        chunk_id = hashlib.md5(
            f"{file_path}:{start_line}:{end_line}:{content[:100]}".encode()
        ).hexdigest()

        return {
            "content": content,
            "file_path": file_path,
            "chunk_id": chunk_id,
            "start_line": start_line,
            "end_line": end_line,
            "chunk_type": chunk_type,
            "description": description,
            "imported_from": analysis.get("imported_from", {}),
            "ui_components": analysis.get("ui_components", []),
            "css_classes": analysis.get("css_classes", []),
            "dom_ids": analysis.get("dom_ids", []),
            **analysis,
        }

    # Keep all the original chunking methods from your implementation
    def chunk_by_functions(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk code by functions and classes"""
        language = CodeAnalyzer.detect_language(file_path)

        if language == "python":
            return self._chunk_python(content, file_path)
        elif language in ["javascript", "typescript"]:
            return self._chunk_javascript(content, file_path)
        elif language == "golang":
            return self._chunk_golang(content, file_path)
        elif language == "html":
            return self._chunk_html(content, file_path)
        elif language == "css":
            return self._chunk_css(content, file_path)
        else:
            return self._chunk_generic(content, file_path)

    def _chunk_python(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk Python code by functions and classes"""
        chunks = []
        lines = content.split("\n")

        try:
            tree = ast.parse(content)

            # Get all function and class definitions with their line numbers
            nodes = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    nodes.append(
                        {
                            "node": node,
                            "start": node.lineno - 1,
                            "type": (
                                "function"
                                if isinstance(node, ast.FunctionDef)
                                else "class"
                            ),
                            "name": node.name,
                        }
                    )

            # Sort by line number
            nodes.sort(key=lambda x: x["start"])

            # Create chunks
            last_end = 0
            for i, node_info in enumerate(nodes):
                start_line = node_info["start"]

                # Add module-level code before this function/class
                if start_line > last_end:
                    module_content = "\n".join(lines[last_end:start_line])
                    if module_content.strip():
                        chunks.append(
                            self._create_chunk(
                                content=module_content,
                                file_path=file_path,
                                start_line=last_end,
                                end_line=start_line - 1,
                                chunk_type="module",
                            )
                        )

                # Find end of this function/class
                end_line = self._find_python_block_end(lines, start_line)

                # Create chunk for this function/class
                chunk_content = "\n".join(lines[start_line : end_line + 1])
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        chunk_type=node_info["type"],
                    )
                )

                last_end = end_line + 1

            # Add remaining module-level code
            if last_end < len(lines):
                module_content = "\n".join(lines[last_end:])
                if module_content.strip():
                    chunks.append(
                        self._create_chunk(
                            content=module_content,
                            file_path=file_path,
                            start_line=last_end,
                            end_line=len(lines) - 1,
                            chunk_type="module",
                        )
                    )

        except SyntaxError:
            # Fallback to generic chunking
            chunks = self._chunk_generic(content, file_path)

        return chunks

    def _find_python_block_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a Python function or class block"""
        if start_line >= len(lines):
            return len(lines) - 1

        # Get initial indentation
        start_indent = len(lines[start_line]) - len(lines[start_line].lstrip())

        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= start_indent:
                    return i - 1

        return len(lines) - 1

    def _chunk_javascript(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk JavaScript/TypeScript code"""
        chunks = []
        lines = content.split("\n")

        # Find function boundaries
        function_starts = []
        for i, line in enumerate(lines):
            if re.match(
                r"^\s*(?:export\s+)?(?:async\s+)?(?:function|const\s+\w+\s*=|class|interface)",
                line,
            ):
                function_starts.append(i)

        last_end = 0
        for start in function_starts:
            # Add code before this function
            if start > last_end:
                module_content = "\n".join(lines[last_end:start])
                if module_content.strip():
                    chunks.append(
                        self._create_chunk(
                            content=module_content,
                            file_path=file_path,
                            start_line=last_end,
                            end_line=start - 1,
                            chunk_type="module",
                        )
                    )

            # Find end of function (simple b
            # Find end of function (simple brace counting)
            end = self._find_js_block_end(lines, start)
            chunk_content = "\n".join(lines[start : end + 1])

            # Determine chunk type
            chunk_type = "function"
            if "class" in lines[start] or "interface" in lines[start]:
                chunk_type = "class"

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    chunk_type=chunk_type,
                )
            )

            last_end = end + 1

        # Add remaining code
        if last_end < len(lines):
            module_content = "\n".join(lines[last_end:])
            if module_content.strip():
                chunks.append(
                    self._create_chunk(
                        content=module_content,
                        file_path=file_path,
                        start_line=last_end,
                        end_line=len(lines) - 1,
                        chunk_type="module",
                    )
                )

        return chunks if chunks else self._chunk_generic(content, file_path)

    def _find_js_block_end(self, lines: List[str], start_line: int) -> int:
        """Find end of JavaScript block using brace counting"""
        brace_count = 0
        in_block = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == "{":
                    brace_count += 1
                    in_block = True
                elif char == "}":
                    brace_count -= 1
                    if in_block and brace_count == 0:
                        return i

        return len(lines) - 1

    def _chunk_golang(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk Go code by functions and structs"""
        chunks = []
        lines = content.split("\n")

        # Find function and struct boundaries
        boundaries = []
        for i, line in enumerate(lines):
            if re.match(r"^\s*func\s+", line) or re.match(
                r"^\s*type\s+\w+\s+(?:struct|interface)", line
            ):
                boundaries.append(i)

        last_end = 0
        for start in boundaries:
            # Add code before this function/struct
            if start > last_end:
                module_content = "\n".join(lines[last_end:start])
                if module_content.strip():
                    chunks.append(
                        self._create_chunk(
                            content=module_content,
                            file_path=file_path,
                            start_line=last_end,
                            end_line=start - 1,
                            chunk_type="module",
                        )
                    )

            # Find end of function/struct
            end = self._find_go_block_end(lines, start)
            chunk_content = "\n".join(lines[start : end + 1])

            # Determine chunk type
            chunk_type = "function"
            if "type" in lines[start] and (
                "struct" in lines[start] or "interface" in lines[start]
            ):
                chunk_type = "type"

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    chunk_type=chunk_type,
                )
            )

            last_end = end + 1

        # Add remaining code
        if last_end < len(lines):
            module_content = "\n".join(lines[last_end:])
            if module_content.strip():
                chunks.append(
                    self._create_chunk(
                        content=module_content,
                        file_path=file_path,
                        start_line=last_end,
                        end_line=len(lines) - 1,
                        chunk_type="module",
                    )
                )

        return chunks if chunks else self._chunk_generic(content, file_path)

    def _find_go_block_end(self, lines: List[str], start_line: int) -> int:
        """Find end of Go function or struct block"""
        brace_count = 0
        in_block = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == "{":
                    brace_count += 1
                    in_block = True
                elif char == "}":
                    brace_count -= 1
                    if in_block and brace_count == 0:
                        return i

        return len(lines) - 1

    def _chunk_html(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk HTML by components and sections"""
        chunks = []
        lines = content.split("\n")

        # Find major HTML sections
        section_patterns = [
            r"<(head|body|header|nav|main|section|article|aside|footer|div\s+(?:class|id))",
            r"<script",
            r"<style",
        ]

        boundaries = []
        for i, line in enumerate(lines):
            for pattern in section_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    boundaries.append(i)
                    break

        # If no major sections found, chunk by size
        if not boundaries:
            return self._chunk_generic(content, file_path)

        last_end = 0
        for start in boundaries:
            if start > last_end:
                # Add content before this section
                section_content = "\n".join(lines[last_end:start])
                if section_content.strip():
                    chunks.append(
                        self._create_chunk(
                            content=section_content,
                            file_path=file_path,
                            start_line=last_end,
                            end_line=start - 1,
                            chunk_type="html_section",
                        )
                    )

            # Find end of this section
            end = self._find_html_section_end(lines, start)
            chunk_content = "\n".join(lines[start : end + 1])

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    chunk_type="html_section",
                )
            )

            last_end = end + 1

        # Add remaining content
        if last_end < len(lines):
            remaining_content = "\n".join(lines[last_end:])
            if remaining_content.strip():
                chunks.append(
                    self._create_chunk(
                        content=remaining_content,
                        file_path=file_path,
                        start_line=last_end,
                        end_line=len(lines) - 1,
                        chunk_type="html_section",
                    )
                )

        return chunks

    def _find_html_section_end(self, lines: List[str], start_line: int) -> int:
        """Find end of HTML section"""
        # Simple approach: look for closing tag or next major section
        start_line_content = lines[start_line]

        # Extract tag name
        tag_match = re.search(r"<(\w+)", start_line_content)
        if tag_match:
            tag_name = tag_match.group(1)
            closing_tag = f"</{tag_name}>"

            for i in range(start_line + 1, len(lines)):
                if closing_tag in lines[i]:
                    return i

        # Fallback: next 20 lines or next major section
        for i in range(start_line + 1, min(start_line + 21, len(lines))):
            if re.search(
                r"<(?:head|body|header|nav|main|section|article|aside|footer)",
                lines[i],
                re.IGNORECASE,
            ):
                return i - 1

        return min(start_line + 20, len(lines) - 1)

    def _chunk_css(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk CSS by selectors and rules"""
        chunks = []
        lines = content.split("\n")

        # Find CSS rules and blocks
        rule_starts = []
        for i, line in enumerate(lines):
            # Look for CSS selectors
            if re.match(r"^\s*[.#]?[\w-]+(?:\s*[,.:]|\s*\{)", line.strip()) or re.match(
                r"^\s*@", line.strip()
            ):
                rule_starts.append(i)

        if not rule_starts:
            return self._chunk_generic(content, file_path)

        last_end = 0
        for start in rule_starts:
            if start > last_end:
                # Add content before this rule
                section_content = "\n".join(lines[last_end:start])
                if section_content.strip():
                    chunks.append(
                        self._create_chunk(
                            content=section_content,
                            file_path=file_path,
                            start_line=last_end,
                            end_line=start - 1,
                            chunk_type="css_block",
                        )
                    )

            # Find end of this CSS rule
            end = self._find_css_rule_end(lines, start)
            chunk_content = "\n".join(lines[start : end + 1])

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    chunk_type="css_rule",
                )
            )

            last_end = end + 1

        # Add remaining content
        if last_end < len(lines):
            remaining_content = "\n".join(lines[last_end:])
            if remaining_content.strip():
                chunks.append(
                    self._create_chunk(
                        content=remaining_content,
                        file_path=file_path,
                        start_line=last_end,
                        end_line=len(lines) - 1,
                        chunk_type="css_block",
                    )
                )

        return chunks

    def _find_css_rule_end(self, lines: List[str], start_line: int) -> int:
        """Find end of CSS rule"""
        brace_count = 0

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return len(lines) - 1

    def _chunk_generic(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Generic chunking for any file type"""
        chunks = []
        lines = content.split("\n")

        # Simple sliding window approach
        chunk_size = min(50, len(lines))  # 50 lines per chunk
        overlap = 5  # 5 lines overlap

        for i in range(0, len(lines), chunk_size - overlap):
            end = min(i + chunk_size, len(lines))
            chunk_content = "\n".join(lines[i:end])

            if chunk_content.strip():
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=i,
                        end_line=end - 1,
                        chunk_type="block",
                    )
                )

        return chunks

    def _generate_description(
        self, content: str, file_path: str, chunk_type: str, analysis: Dict[str, Any]
    ) -> str:
        """Generate natural language description of code chunk"""
        descriptions = []

        # File context
        filename = Path(file_path).name
        descriptions.append(f"Code from {filename}")

        # Type and functions
        if chunk_type == "function" and analysis["functions"]:
            descriptions.append(
                f"containing function(s): {', '.join(analysis['functions'][:3])}"
            )
        elif chunk_type == "class" and analysis["classes"]:
            descriptions.append(
                f"containing class(es): {', '.join(analysis['classes'][:3])}"
            )
        elif chunk_type == "type" and analysis["classes"]:
            descriptions.append(
                f"containing type(s): {', '.join(analysis['classes'][:3])}"
            )
        elif chunk_type == "module":
            descriptions.append("module-level code")
        elif chunk_type == "html_section":
            descriptions.append("HTML section")
        elif chunk_type == "css_rule":
            descriptions.append("CSS rule")

        # UI components
        if analysis.get("ui_components"):
            descriptions.append(
                f"UI components: {', '.join(analysis['ui_components'][:3])}"
            )

        # Imports
        if analysis["imports"]:
            descriptions.append(f"imports: {', '.join(analysis['imports'][:3])}")

        # Language
        descriptions.append(f"in {analysis['language']}")

        # Content preview
        content_preview = content.strip()[:100].replace("\n", " ")
        if len(content.strip()) > 100:
            content_preview += "..."
        descriptions.append(f"Content: {content_preview}")

        return ". ".join(descriptions)


class RAGSystem:
    """Enhanced RAG system with smart multi-file context retrieval"""

    def __init__(self, project_path: str, cache_dir: str = ".rag_cache"):
        self.project_path = Path(project_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize components
        self.chunker = CodeChunker()
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.chunks: Dict[str, CodeChunk] = {}
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunk_ids: List[str] = []

        # New: dependency analyzer
        self.dependency_analyzer = FileDependencyAnalyzer()

        # Cache files
        self.chunks_cache_file = self.cache_dir / "chunks.pkl"
        self.index_cache_file = self.cache_dir / "index.faiss"
        self.metadata_cache_file = self.cache_dir / "metadata.json"
        self.dependency_cache_file = self.cache_dir / "dependencies.pkl"

        # Load existing cache if available
        self._load_cache()

    def _load_cache(self) -> bool:
        """Load cached index and chunks"""
        try:
            if (
                self.chunks_cache_file.exists()
                and self.index_cache_file.exists()
                and self.metadata_cache_file.exists()
            ):

                # Load metadata to check if cache is still valid
                with open(self.metadata_cache_file, "r") as f:
                    metadata = json.load(f)

                # Simple cache invalidation based on project modification time
                project_mtime = max(
                    os.path.getmtime(f)
                    for f in self.project_path.rglob("*")
                    if f.is_file() and not self._should_ignore_file(f)
                )

                if metadata.get("project_mtime", 0) >= project_mtime:
                    # Load chunks
                    with open(self.chunks_cache_file, "rb") as f:
                        self.chunks = pickle.load(f)

                    # Load index
                    self.index = faiss.read_index(str(self.index_cache_file))
                    self.chunk_ids = metadata["chunk_ids"]

                    # Load dependency analyzer
                    if self.dependency_cache_file.exists():
                        with open(self.dependency_cache_file, "rb") as f:
                            self.dependency_analyzer = pickle.load(f)

                    logger.info(f"Loaded RAG cache with {len(self.chunks)} chunks")
                    return True
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

        return False

    def _save_cache(self):
        """Save index and chunks to cache"""
        try:
            # Save chunks
            with open(self.chunks_cache_file, "wb") as f:
                pickle.dump(self.chunks, f)

            # Save index
            if self.index:
                faiss.write_index(self.index, str(self.index_cache_file))

            # Save dependency analyzer
            with open(self.dependency_cache_file, "wb") as f:
                pickle.dump(self.dependency_analyzer, f)

            # Save metadata
            project_mtime = max(
                os.path.getmtime(f)
                for f in self.project_path.rglob("*")
                if f.is_file() and not self._should_ignore_file(f)
            )

            metadata = {
                "project_mtime": project_mtime,
                "chunk_ids": self.chunk_ids,
                "created_at": datetime.now().isoformat(),
            }

            with open(self.metadata_cache_file, "w") as f:
                json.dump(metadata, f)

            logger.info("Saved RAG cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored"""
        ignore_dirs = {
            ".git",
            "__pycache__",
            ".vscode",
            ".idea",
            "node_modules",
            "venv",
            ".env",
            "build",
            "dist",
            ".rag_cache",
            "vendor",  # Go vendor directory
            "target",  # Rust target directory
            ".next",  # Next.js build directory
            "coverage",  # Test coverage directories
        }
        ignore_files = {
            ".DS_Store",
            ".gitignore",
            "package-lock.json",
            "yarn.lock",
            "go.sum",
        }
        ignore_extensions = {
            ".pyc",
            ".log",
            ".swp",
            ".swo",
            ".tmp",
            ".bak",
            ".min.js",
            ".min.css",  # Minified files
            ".map",  # Source maps
            ".lock",  # Lock files
        }

        # Check if any parent directory is in ignore list
        for parent in file_path.parents:
            if parent.name in ignore_dirs:
                return True

        # Check filename and extension
        if (
            file_path.name in ignore_files
            or file_path.suffix in ignore_extensions
            or file_path.name.startswith(".")
            or file_path.stat().st_size > 1024 * 1024  # Skip files larger than 1MB
        ):
            return True

        return False

    def index_project(self) -> int:
        """Index the entire project"""
        logger.info(f"Indexing project: {self.project_path}")

        all_chunks = []

        # Supported file extensions
        supported_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".html",
            ".htm",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".json",
            ".yaml",
            ".yml",
            ".md",
            ".txt",
        }

        # Process all files
        for file_path in self.project_path.rglob("*"):
            if (
                file_path.is_file()
                and not self._should_ignore_file(file_path)
                and file_path.suffix.lower() in supported_extensions
            ):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():  # Skip empty files
                        relative_path = str(file_path.relative_to(self.project_path))
                        chunks = self.chunker.chunk_by_functions(content, relative_path)
                        all_chunks.extend(chunks)
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")

        # Create CodeChunk objects and generate embeddings
        self.chunks = {}
        embeddings = []
        self.chunk_ids = []

        logger.info(f"Generating embeddings for {len(all_chunks)} chunks...")

        for chunk_data in all_chunks:
            try:
                # Create CodeChunk object with proper dependencies initialization
                chunk = CodeChunk(
                    content=chunk_data["content"],
                    file_path=chunk_data["file_path"],
                    chunk_id=chunk_data["chunk_id"],
                    start_line=chunk_data["start_line"],
                    end_line=chunk_data["end_line"],
                    chunk_type=chunk_data["chunk_type"],
                    language=chunk_data["language"],
                    description=chunk_data["description"],
                    functions=chunk_data.get("functions", []),
                    classes=chunk_data.get("classes", []),
                    imports=chunk_data.get("imports", []),
                    dependencies=chunk_data.get("dependencies", []),
                    complexity_score=chunk_data.get("complexity_score", 0.0),
                    exported_symbols=chunk_data.get("exported_symbols", []),
                    imported_from=chunk_data.get("imported_from", {}),
                    ui_components=chunk_data.get("ui_components", []),
                    css_classes=chunk_data.get("css_classes", []),
                    dom_ids=chunk_data.get("dom_ids", []),
                )

                # Generate embedding for content + description
                text_to_embed = f"{chunk.description}\n\n{chunk.content}"
                embedding = self.embedder.encode(text_to_embed, convert_to_numpy=True)
                chunk.embedding = embedding

                # Store
                self.chunks[chunk.chunk_id] = chunk
                embeddings.append(embedding)
                self.chunk_ids.append(chunk.chunk_id)

            except Exception as e:
                logger.warning(f"Failed to create chunk: {e}")
                continue

        # Create FAISS index
        if embeddings:
            embeddings_matrix = np.vstack(embeddings).astype("float32")
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings_matrix)

            # Create index
            dimension = embeddings_matrix.shape[1]
            self.index = faiss.IndexFlatIP(
                dimension
            )  # Inner product for cosine similarity
            self.index.add(embeddings_matrix)

            logger.info(f"Created FAISS index with {len(embeddings)} chunks")

        # Analyze dependencies
        logger.info("Analyzing file dependencies...")
        self.dependency_analyzer.analyze_project(self.chunks)

        # Save to cache
        self._save_cache()

        return len(all_chunks)

    def search(
        self, query: str, k: int = 10, current_file: Optional[str] = None
    ) -> List[CodeChunk]:
        """Search for relevant code chunks"""
        if not self.index or not self.chunks:
            logger.warning("No index available. Please index the project first.")
            return []

        # Generate query embedding
        query_embedding = self.embedder.encode(query, convert_to_numpy=True).astype(
            "float32"
        )
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(
            query_embedding,
            min(k * 3, len(self.chunk_ids)),  # Get more results for filtering
        )

        results = []
        seen_files = set()
        file_chunk_count = {}

        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunk_ids):
                chunk_id = self.chunk_ids[idx]
                chunk = self.chunks[chunk_id]

                # Boost score if from current file
                adjusted_score = score
                if current_file and chunk.file_path == current_file:
                    adjusted_score *= 1.5

                # Limit chunks per file to avoid overwhelming from single file
                file_count = file_chunk_count.get(chunk.file_path, 0)
                if file_count < 3:  # Max 3 chunks per file initially
                    results.append((chunk, adjusted_score))
                    file_chunk_count[chunk.file_path] = file_count + 1
                    seen_files.add(chunk.file_path)

                if len(results) >= k:
                    break

        # Sort by adjusted score and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in results[:k]]

    def get_relevant_context_smart(
        self,
        user_query: str,
        current_file: Optional[str] = None,
        max_tokens: int = 20000,
        include_full_files: bool = True,
    ) -> Dict[str, Any]:
        """Enhanced context retrieval with smart file detection"""

        # Analyze query to determine if UI changes are involved
        is_ui_query = any(
            term in user_query.lower()
            for term in [
                "ui",
                "interface",
                "button",
                "component",
                "style",
                "css",
                "layout",
                "design",
                "visual",
                "appearance",
                "top bar",
                "appbar",
                "navbar",
                "header",
                "footer",
                "sidebar",
                "modal",
                "dialog",
            ]
        )

        # Get relevant chunks from search
        relevant_chunks = self.search(user_query, k=15, current_file=current_file)

        # Collect files that need full content
        files_for_full_content = set()
        files_for_chunks = set()

        # Determine which files need editing based on query
        for chunk in relevant_chunks:
            file_path = chunk.file_path

            # If the query mentions editing/changing/improving, include full file
            if any(
                action in user_query.lower()
                for action in [
                    "edit",
                    "change",
                    "modify",
                    "update",
                    "improve",
                    "fix",
                    "refactor",
                    "rewrite",
                    "adjust",
                    "make",
                    "set",
                ]
            ):
                # This file likely needs editing
                files_for_full_content.add(file_path)
            else:
                files_for_chunks.add(file_path)

        # If UI query, find related files through dependencies
        if is_ui_query:
            ui_related_files = self.dependency_analyzer.get_ui_related_files(user_query)

            # Add main UI files for full content
            for file in ui_related_files:
                if any(file.endswith(ext) for ext in [".tsx", ".jsx", ".js", ".ts"]):
                    files_for_full_content.add(file)
                else:
                    files_for_chunks.add(file)

            # Get CSS/style files related to the components
            for chunk in relevant_chunks:
                if chunk.css_classes:
                    # Find CSS files that might contain these classes
                    for other_chunk in self.chunks.values():
                        if other_chunk.language == "css" and any(
                            cls in other_chunk.content for cls in chunk.css_classes
                        ):
                            files_for_chunks.add(other_chunk.file_path)

        # Add dependency files
        for file_path in list(files_for_full_content):
            related = self.dependency_analyzer.get_related_files(file_path, depth=1)
            files_for_chunks.update(related - files_for_full_content)

        # Build context
        context_parts = []
        full_file_contents = {}
        chunk_contents = {}
        total_chars = 0

        # First, add full files (these are priority)
        if include_full_files:
            for file_path in files_for_full_content:
                try:
                    full_path = self.project_path / file_path
                    if full_path.exists():
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                        file_chars = len(content)

                        if total_chars + file_chars <= max_tokens * 4:
                            full_file_contents[file_path] = content
                            total_chars += file_chars

                            context_parts.append(
                                {
                                    "type": "full_file",
                                    "file_path": file_path,
                                    "content": content,
                                    "reason": "File requires editing based on query",
                                }
                            )
                except Exception as e:
                    logger.warning(f"Failed to read file {file_path}: {e}")

        # Then add relevant chunks from other files
        for chunk in relevant_chunks:
            if chunk.file_path not in files_for_full_content:
                chunk_chars = len(chunk.content) + len(chunk.description)
                if total_chars + chunk_chars > max_tokens * 4:
                    break

                if chunk.file_path not in chunk_contents:
                    chunk_contents[chunk.file_path] = []

                chunk_contents[chunk.file_path].append(
                    {
                        "chunk_type": chunk.chunk_type,
                        "description": chunk.description,
                        "content": chunk.content,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "functions": chunk.functions,
                        "classes": chunk.classes,
                        "language": chunk.language,
                        "ui_components": chunk.ui_components,
                    }
                )

                total_chars += chunk_chars

        # Format the context for the AI
        all_file_contents = {}

        # Add full files
        for file_path, content in full_file_contents.items():
            all_file_contents[file_path] = f"[FULL FILE - Ready for editing]\n{content}"

        # Add chunked files
        for file_path, chunks in chunk_contents.items():
            content_parts = [
                f"[PARTIAL CONTEXT - Read-only, request full file to edit]"
            ]
            for chunk_info in chunks:
                header = f"\n# {chunk_info['chunk_type'].upper()} ({chunk_info['start_line']}-{chunk_info['end_line']}): {chunk_info['description']}\n"
                content_parts.append(header + chunk_info["content"])
            all_file_contents[file_path] = "\n".join(content_parts)

        return {
            "file_paths": list(full_file_contents.keys()) + list(chunk_contents.keys()),
            "all_file_contents": all_file_contents,
            "rag_metadata": {
                "total_chunks": len(relevant_chunks),
                "full_files": list(full_file_contents.keys()),
                "partial_files": list(chunk_contents.keys()),
                "estimated_tokens": total_chars // 4,
                "search_query": user_query,
                "is_ui_query": is_ui_query,
                "retrieval_strategy": "smart_multi_file",
            },
        }

    def get_relevant_context(
        self,
        user_query: str,
        current_file: Optional[str] = None,
        max_tokens: int = 20000,
    ) -> Dict[str, Any]:
        """Original get_relevant_context method for backward compatibility"""
        return self.get_relevant_context_smart(
            user_query=user_query,
            current_file=current_file,
            max_tokens=max_tokens,
            include_full_files=True,
        )

    def invalidate_cache(self):
        """Clear all cached data"""
        try:
            if self.chunks_cache_file.exists():
                self.chunks_cache_file.unlink()
            if self.index_cache_file.exists():
                self.index_cache_file.unlink()
            if self.metadata_cache_file.exists():
                self.metadata_cache_file.unlink()
            if self.dependency_cache_file.exists():
                self.dependency_cache_file.unlink()

            self.chunks = {}
            self.index = None
            self.chunk_ids = []
            self.dependency_analyzer = FileDependencyAnalyzer()

            logger.info("Cleared RAG cache")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
