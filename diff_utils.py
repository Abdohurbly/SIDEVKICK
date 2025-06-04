import difflib
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PatchOperation:
    """Represents a single patch operation"""

    def __init__(
        self,
        operation: str,
        start_line: int,
        end_line: Optional[int] = None,
        content: str = "",
    ):
        self.operation = operation  # 'replace', 'insert', 'delete'
        self.start_line = start_line
        self.end_line = end_line if end_line is not None else start_line
        self.content = content


class ContextualDiffProcessor:
    """Handles applying contextual file changes using pattern matching"""

    @staticmethod
    def apply_contextual_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> str:
        """Apply a list of contextual changes to the original content"""
        content = original_content

        # Process changes in order (no need to reverse for contextual changes)
        for i, change in enumerate(changes):
            operation = change.get("operation")
            logger.info(f"Applying contextual change {i+1}/{len(changes)}: {operation}")

            try:
                if operation == "replace":
                    content = ContextualDiffProcessor._apply_replace(content, change)
                elif operation == "insert_after":
                    content = ContextualDiffProcessor._apply_insert_after(
                        content, change
                    )
                elif operation == "insert_before":
                    content = ContextualDiffProcessor._apply_insert_before(
                        content, change
                    )
                elif operation == "delete":
                    content = ContextualDiffProcessor._apply_delete(content, change)
                else:
                    logger.warning(f"Unknown contextual operation: {operation}")

            except Exception as e:
                logger.error(f"Failed to apply contextual change {i+1}: {e}")
                raise Exception(f"Contextual change {i+1} failed: {str(e)}")

        return content

    @staticmethod
    def _apply_replace(content: str, change: Dict[str, Any]) -> str:
        """Apply a contextual replace operation"""
        target = change.get("target_content", "")
        replacement = change.get("replacement_content", "")
        before_ctx = change.get("before_context", "")
        after_ctx = change.get("after_context", "")

        if not target:
            raise ValueError("target_content is required for replace operation")

        # Try different matching strategies

        # Strategy 1: Full context match (most precise)
        if before_ctx and after_ctx:
            logger.info("Using full context matching")
            pattern = (
                re.escape(before_ctx)
                + r"\s*"
                + re.escape(target)
                + r"\s*"
                + re.escape(after_ctx)
            )
            replacement_full = before_ctx + replacement + after_ctx

            if re.search(pattern, content, re.DOTALL):
                content = re.sub(
                    pattern, replacement_full, content, count=1, flags=re.DOTALL
                )
                logger.info("Full context match successful")
                return content

        # Strategy 2: Target with partial context
        if before_ctx:
            logger.info("Using before context matching")
            pattern = re.escape(before_ctx) + r"\s*" + re.escape(target)
            replacement_full = before_ctx + replacement

            if re.search(pattern, content, re.DOTALL):
                content = re.sub(
                    pattern, replacement_full, content, count=1, flags=re.DOTALL
                )
                logger.info("Before context match successful")
                return content

        if after_ctx:
            logger.info("Using after context matching")
            pattern = re.escape(target) + r"\s*" + re.escape(after_ctx)
            replacement_full = replacement + after_ctx

            if re.search(pattern, content, re.DOTALL):
                content = re.sub(
                    pattern, replacement_full, content, count=1, flags=re.DOTALL
                )
                logger.info("After context match successful")
                return content

        # Strategy 3: Direct target match (least precise)
        if target in content:
            logger.info("Using direct target matching")
            content = content.replace(target, replacement, 1)
            logger.info("Direct target match successful")
            return content

        # Strategy 4: Fuzzy matching for slight variations
        logger.info("Attempting fuzzy matching")
        fuzzy_result = ContextualDiffProcessor._fuzzy_replace(
            content, target, replacement
        )
        if fuzzy_result != content:
            logger.info("Fuzzy match successful")
            return fuzzy_result

        raise ValueError(
            f"Could not find target content for replacement: {target[:100]}..."
        )

    @staticmethod
    def _apply_insert_after(content: str, change: Dict[str, Any]) -> str:
        """Insert content after an anchor"""
        anchor = change.get("anchor_content", "")
        new_content = change.get("content", "")

        if not anchor:
            raise ValueError("anchor_content is required for insert_after operation")

        if anchor in content:
            logger.info("Direct anchor match for insert_after")
            return content.replace(anchor, anchor + new_content, 1)

        # Try fuzzy matching
        fuzzy_result = ContextualDiffProcessor._fuzzy_insert_after(
            content, anchor, new_content
        )
        if fuzzy_result != content:
            logger.info("Fuzzy anchor match for insert_after")
            return fuzzy_result

        raise ValueError(
            f"Could not find anchor content for insertion: {anchor[:100]}..."
        )

    @staticmethod
    def _apply_insert_before(content: str, change: Dict[str, Any]) -> str:
        """Insert content before an anchor"""
        anchor = change.get("anchor_content", "")
        new_content = change.get("content", "")

        if not anchor:
            raise ValueError("anchor_content is required for insert_before operation")

        if anchor in content:
            logger.info("Direct anchor match for insert_before")
            return content.replace(anchor, new_content + anchor, 1)

        # Try fuzzy matching
        fuzzy_result = ContextualDiffProcessor._fuzzy_insert_before(
            content, anchor, new_content
        )
        if fuzzy_result != content:
            logger.info("Fuzzy anchor match for insert_before")
            return fuzzy_result

        raise ValueError(
            f"Could not find anchor content for insertion: {anchor[:100]}..."
        )

    @staticmethod
    def _apply_delete(content: str, change: Dict[str, Any]) -> str:
        """Delete content based on target or context"""
        target = change.get("target_content", "")
        before_ctx = change.get("before_context", "")
        after_ctx = change.get("after_context", "")

        if not target:
            raise ValueError("target_content is required for delete operation")

        # Similar to replace but with empty replacement
        if before_ctx and after_ctx:
            pattern = (
                re.escape(before_ctx)
                + r"\s*"
                + re.escape(target)
                + r"\s*"
                + re.escape(after_ctx)
            )
            replacement = before_ctx + after_ctx

            if re.search(pattern, content, re.DOTALL):
                return re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)

        if target in content:
            return content.replace(target, "", 1)

        raise ValueError(
            f"Could not find target content for deletion: {target[:100]}..."
        )

    @staticmethod
    def _fuzzy_replace(content: str, target: str, replacement: str) -> str:
        """Attempt fuzzy matching for replacement"""
        # Remove extra whitespace and try again
        normalized_target = " ".join(target.split())
        normalized_content = " ".join(content.split())

        if normalized_target in normalized_content:
            # Find the original whitespace-preserved version
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if normalized_target in " ".join(line.split()):
                    # Replace in this line
                    lines[i] = line.replace(target.strip(), replacement.strip())
                    return "\n".join(lines)

        return content  # No change if fuzzy match fails

    @staticmethod
    def _fuzzy_insert_after(content: str, anchor: str, new_content: str) -> str:
        """Attempt fuzzy matching for insert_after"""
        # Try with normalized whitespace
        normalized_anchor = " ".join(anchor.split())
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if normalized_anchor in " ".join(line.split()):
                # Insert after this line
                lines.insert(i + 1, new_content)
                return "\n".join(lines)

        return content

    @staticmethod
    def _fuzzy_insert_before(content: str, anchor: str, new_content: str) -> str:
        """Attempt fuzzy matching for insert_before"""
        # Try with normalized whitespace
        normalized_anchor = " ".join(anchor.split())
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if normalized_anchor in " ".join(line.split()):
                # Insert before this line
                lines.insert(i, new_content)
                return "\n".join(lines)

        return content

    @staticmethod
    def validate_contextual_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Validate that contextual changes can be applied"""
        for i, change in enumerate(changes):
            operation = change.get("operation")

            if operation == "replace":
                target = change.get("target_content", "")
                if not target:
                    return (
                        False,
                        f"Change {i+1}: target_content is required for replace operation",
                    )

                if target not in original_content:
                    # Try fuzzy matching
                    normalized_target = " ".join(target.split())
                    normalized_content = " ".join(original_content.split())
                    if normalized_target not in normalized_content:
                        return False, f"Change {i+1}: target_content not found in file"

            elif operation in ["insert_after", "insert_before"]:
                anchor = change.get("anchor_content", "")
                if not anchor:
                    return (
                        False,
                        f"Change {i+1}: anchor_content is required for {operation} operation",
                    )

                if anchor not in original_content:
                    # Try fuzzy matching
                    normalized_anchor = " ".join(anchor.split())
                    normalized_content = " ".join(original_content.split())
                    if normalized_anchor not in normalized_content:
                        return False, f"Change {i+1}: anchor_content not found in file"

            elif operation == "delete":
                target = change.get("target_content", "")
                if not target:
                    return (
                        False,
                        f"Change {i+1}: target_content is required for delete operation",
                    )

                if target not in original_content:
                    return False, f"Change {i+1}: target_content not found for deletion"

        return True, ""


class DiffProcessor:
    """Handles applying partial file changes (legacy line-based system)"""

    @staticmethod
    def apply_partial_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> str:
        """Apply a list of changes to the original content"""
        lines = original_content.splitlines(keepends=True)
        total_lines = len(lines)

        logger.info(f"Original content has {total_lines} lines")

        # Sort changes by line number in reverse order to avoid offset issues
        sorted_changes = sorted(
            changes, key=lambda x: x.get("start_line", x.get("line", 0)), reverse=True
        )

        for i, change in enumerate(sorted_changes):
            operation = change.get("operation")
            logger.info(f"Applying change {i+1}/{len(sorted_changes)}: {operation}")

            if operation == "replace":
                start_line = change["start_line"] - 1  # Convert to 0-based indexing
                end_line = change["end_line"] - 1
                new_content = change["content"]

                # Add bounds checking
                if start_line < 0 or end_line >= total_lines:
                    logger.error(
                        f"Line numbers out of bounds: {start_line+1}-{end_line+1} (file has {total_lines} lines)"
                    )
                    continue

                # Ensure new content ends with newline if original did
                if (
                    not new_content.endswith("\n")
                    and start_line < len(lines)
                    and lines[start_line].endswith("\n")
                ):
                    new_content += "\n"

                # Replace the lines
                lines[start_line : end_line + 1] = [new_content] if new_content else []
                total_lines = len(lines)

            elif operation == "insert":
                line = change["line"]  # This is after which line to insert
                new_content = change["content"]

                if line < 0 or line > total_lines:
                    logger.error(
                        f"Insert line {line} out of bounds (file has {total_lines} lines)"
                    )
                    continue

                if not new_content.endswith("\n"):
                    new_content += "\n"

                # Insert after the specified line
                lines.insert(line, new_content)
                total_lines = len(lines)

            elif operation == "delete":
                start_line = change["start_line"] - 1
                end_line = change.get("end_line", change["start_line"]) - 1

                if start_line < 0 or end_line >= total_lines:
                    logger.error(
                        f"Delete line numbers out of bounds: {start_line+1}-{end_line+1} (file has {total_lines} lines)"
                    )
                    continue

                # Delete the specified lines
                del lines[start_line : end_line + 1]
                total_lines = len(lines)

        return "".join(lines)

    @staticmethod
    def generate_unified_diff(
        original: str,
        modified: str,
        fromfile: str = "original",
        tofile: str = "modified",
    ) -> str:
        """Generate a unified diff between two strings"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )

        return "".join(diff)

    @staticmethod
    def validate_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Validate that changes can be applied to the original content"""
        lines = original_content.splitlines()
        max_line = len(lines)

        for change in changes:
            operation = change.get("operation")

            if operation == "replace":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)

                if (
                    start_line < 1
                    or end_line < 1
                    or start_line > max_line
                    or end_line > max_line
                ):
                    return (
                        False,
                        f"Replace operation line numbers {start_line}-{end_line} are out of range (file has {max_line} lines)",
                    )

                if start_line > end_line:
                    return (
                        False,
                        f"Replace operation start_line ({start_line}) > end_line ({end_line})",
                    )

            elif operation == "insert":
                line = change.get("line", 0)
                if line < 0 or line > max_line:
                    return (
                        False,
                        f"Insert operation line {line} is out of range (file has {max_line} lines)",
                    )

            elif operation == "delete":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)

                if (
                    start_line < 1
                    or end_line < 1
                    or start_line > max_line
                    or end_line > max_line
                ):
                    return (
                        False,
                        f"Delete operation line numbers {start_line}-{end_line} are out of range (file has {max_line} lines)",
                    )

                if start_line > end_line:
                    return (
                        False,
                        f"Delete operation start_line ({start_line}) > end_line ({end_line})",
                    )

        return True, ""


def create_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:
    """Create a preview of what changes will be applied"""
    lines = original_content.splitlines()
    preview_parts = []

    for change in sorted(changes, key=lambda x: x.get("start_line", x.get("line", 0))):
        operation = change.get("operation")

        if operation == "replace":
            start_line = change["start_line"]
            end_line = change["end_line"]
            new_content = change["content"].strip()

            preview_parts.append(f"Replace lines {start_line}-{end_line}:")
            preview_parts.append(
                f"  Old: {' '.join(lines[start_line-1:end_line])[:100]}..."
            )
            preview_parts.append(f"  New: {new_content[:100]}...")

        elif operation == "insert":
            line = change["line"]
            new_content = change["content"].strip()

            preview_parts.append(f"Insert after line {line}:")
            preview_parts.append(f"  Content: {new_content[:100]}...")

        elif operation == "delete":
            start_line = change["start_line"]
            end_line = change.get("end_line", start_line)

            preview_parts.append(f"Delete lines {start_line}-{end_line}:")
            preview_parts.append(
                f"  Content: {' '.join(lines[start_line-1:end_line])[:100]}..."
            )

    return "\n".join(preview_parts)


def create_contextual_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:
    """Create a preview of contextual changes"""
    preview_parts = []

    for i, change in enumerate(changes):
        operation = change.get("operation")
        preview_parts.append(f"Change {i+1}: {operation}")

        if operation == "replace":
            target = change.get("target_content", "")[:100]
            replacement = change.get("replacement_content", "")[:100]
            preview_parts.append(f"  Target: {target}...")
            preview_parts.append(f"  Replacement: {replacement}...")

        elif operation in ["insert_after", "insert_before"]:
            anchor = change.get("anchor_content", "")[:100]
            content = change.get("content", "")[:100]
            preview_parts.append(f"  Anchor: {anchor}...")
            preview_parts.append(f"  Content: {content}...")

        elif operation == "delete":
            target = change.get("target_content", "")[:100]
            preview_parts.append(f"  Target: {target}...")

        preview_parts.append("")  # Empty line between changes

    return "\n".join(preview_parts)
