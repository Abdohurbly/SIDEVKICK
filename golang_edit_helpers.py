# golang_edit_helpers.py - New file for Go-specific editing
import re
from typing import Any, Dict, List, Tuple, Optional


class GolangEditHelper:
    """Helper class for creating precise Go code edits with context"""

    @staticmethod
    def create_function_edit(
        content: str,
        function_name: str,
        new_function_body: str,
        include_signature: bool = True,
    ) -> Dict[str, Any]:
        """Create a context-aware edit for a Go function"""

        lines = content.splitlines()

        # Find function definition
        func_pattern = (
            rf"func\s+(?:\(\w+\s+\*?\w+\)\s+)?{re.escape(function_name)}\s*\("
        )

        for i, line in enumerate(lines):
            if re.search(func_pattern, line):
                # Find function start
                func_start = i

                # Find function end (matching braces)
                brace_count = 0
                func_end = func_start

                for j in range(func_start, len(lines)):
                    for char in lines[j]:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                func_end = j
                                break
                    if brace_count == 0:
                        break

                # Extract contexts
                before_context = (
                    "\n".join(lines[max(0, func_start - 2) : func_start])
                    if func_start > 0
                    else ""
                )
                after_context = (
                    "\n".join(lines[func_end + 1 : min(len(lines), func_end + 3)])
                    if func_end < len(lines) - 1
                    else ""
                )

                # Target content (function to replace)
                target_content = "\n".join(lines[func_start : func_end + 1])

                # Replacement content
                if include_signature:
                    # Keep the original signature, replace body only
                    signature_line = lines[func_start]
                    replacement = f"{signature_line} {{\n{new_function_body}\n}}"
                else:
                    replacement = new_function_body

                return {
                    "operation": "replace",
                    "target_content": target_content,
                    "replacement_content": replacement,
                    "before_context": before_context,
                    "after_context": after_context,
                    "function_name": function_name,
                    "confidence": "high",
                }

        raise ValueError(f"Function '{function_name}' not found")

    @staticmethod
    def create_struct_field_edit(
        content: str, struct_name: str, field_name: str, new_field_definition: str
    ) -> Dict[str, Any]:
        """Add or modify a struct field with precise context"""

        lines = content.splitlines()

        # Find struct definition
        struct_pattern = rf"type\s+{re.escape(struct_name)}\s+struct\s*\{{"

        for i, line in enumerate(lines):
            if re.search(struct_pattern, line):
                struct_start = i

                # Find struct end
                brace_count = 0
                struct_end = struct_start

                for j in range(struct_start, len(lines)):
                    for char in lines[j]:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                struct_end = j
                                break
                    if brace_count == 0:
                        break

                # Look for existing field
                field_pattern = rf"\s*{re.escape(field_name)}\s+"
                field_found = False
                field_line = -1

                for j in range(struct_start + 1, struct_end):
                    if re.match(field_pattern, lines[j]):
                        field_found = True
                        field_line = j
                        break

                if field_found:
                    # Replace existing field
                    before_context = "\n".join(
                        lines[max(0, field_line - 1) : field_line]
                    )
                    after_context = "\n".join(
                        lines[field_line + 1 : min(len(lines), field_line + 2)]
                    )
                    target_content = lines[field_line]

                    return {
                        "operation": "replace",
                        "target_content": target_content,
                        "replacement_content": f"    {new_field_definition}",
                        "before_context": before_context,
                        "after_context": after_context,
                        "confidence": "high",
                    }
                else:
                    # Add new field before closing brace
                    before_context = "\n".join(
                        lines[max(0, struct_end - 2) : struct_end]
                    )
                    after_context = "\n".join(
                        lines[struct_end : min(len(lines), struct_end + 2)]
                    )

                    return {
                        "operation": "insert_before",
                        "anchor_content": lines[
                            struct_end
                        ].strip(),  # The closing brace
                        "content": f"    {new_field_definition}\n",
                        "before_context": before_context,
                        "confidence": "high",
                    }

        raise ValueError(f"Struct '{struct_name}' not found")

    @staticmethod
    def create_import_edit(content: str, import_path: str) -> Dict[str, Any]:
        """Add an import with proper context"""

        lines = content.splitlines()

        # Check if import already exists
        if f'"{import_path}"' in content or f"'{import_path}'" in content:
            return {"operation": "skip", "reason": "Import already exists"}

        # Find import block
        import_start = -1
        import_end = -1
        single_import = False

        for i, line in enumerate(lines):
            if line.strip().startswith("import ("):
                import_start = i
                # Find closing parenthesis
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == ")":
                        import_end = j
                        break
                break
            elif line.strip().startswith("import ") and '"' in line:
                # Single import line
                import_start = i
                import_end = i
                single_import = True
                break

        if import_start == -1:
            # No imports yet, add after package declaration
            for i, line in enumerate(lines):
                if line.strip().startswith("package "):
                    package_line = i
                    # Add import block after package
                    return {
                        "operation": "insert_after",
                        "anchor_content": line,
                        "content": f'\n\nimport "{import_path}"',
                        "confidence": "high",
                    }
        else:
            if single_import:
                # Convert single import to block
                existing_import = lines[import_start]
                before_context = (
                    "\n".join(lines[max(0, import_start - 1) : import_start])
                    if import_start > 0
                    else ""
                )
                after_context = (
                    "\n".join(
                        lines[import_start + 1 : min(len(lines), import_start + 2)]
                    )
                    if import_start < len(lines) - 1
                    else ""
                )

                new_import_block = f"""import (
    {existing_import.strip().replace('import ', '').strip()}
    "{import_path}"
)"""

                return {
                    "operation": "replace",
                    "target_content": existing_import,
                    "replacement_content": new_import_block,
                    "before_context": before_context,
                    "after_context": after_context,
                    "confidence": "high",
                }
            else:
                # Add to existing import block
                # Insert before closing parenthesis
                before_context = "\n".join(lines[max(0, import_end - 1) : import_end])
                after_context = "\n".join(
                    lines[import_end : min(len(lines), import_end + 2)]
                )

                return {
                    "operation": "insert_before",
                    "anchor_content": lines[import_end].strip(),  # The closing )
                    "content": f'    "{import_path}"\n',
                    "before_context": before_context,
                    "confidence": "high",
                }

        raise ValueError("Could not determine where to add import")
