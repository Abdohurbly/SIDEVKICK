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


# diff_utils.py - Enhanced version
class ContextualDiffProcessor:

    @staticmethod
    def create_smart_edit(
        content: str,
        target_content: str,
        replacement_content: str,
        context_lines: int = 2,
    ) -> Dict[str, Any]:
        """
        Automatically create before/after context for more precise edits
        """
        lines = content.splitlines()
        target_lines = target_content.splitlines()

        for i in range(len(lines) - len(target_lines) + 1):
            if lines[i : i + len(target_lines)] == target_lines:
                before_start = max(0, i - context_lines)
                before_context = "\n".join(lines[before_start:i]) if i > 0 else ""
                after_end = min(len(lines), i + len(target_lines) + context_lines)
                after_context = (
                    "\n".join(lines[i + len(target_lines) : after_end])
                    if i + len(target_lines) < len(lines)
                    else ""
                )
                return {
                    "operation": "replace",
                    "target_content": target_content,
                    "replacement_content": replacement_content,
                    "before_context": before_context,
                    "after_context": after_context,
                    "confidence": "high",
                }
        return {
            "operation": "replace",
            "target_content": target_content,
            "replacement_content": replacement_content,
            "confidence": "low",  # Fallback if exact match not found by this simple method
        }

    @staticmethod
    def _apply_replace(current_content: str, change: Dict[str, Any]) -> str:
        target = change.get("target_content", "")
        replacement = change.get("replacement_content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not target:  # Target cannot be empty for replace
            raise ValueError(
                "target_content is required and cannot be empty for replace operation"
            )

        target_escaped = re.escape(target)

        # Strategy 1: Full context match (most precise)
        if (
            before_ctx is not None and after_ctx is not None
        ):  # Contexts can be empty strings
            logger.info("Replace Strategy 1: Full context matching")
            before_escaped = re.escape(before_ctx)
            after_escaped = re.escape(after_ctx)
            # Pattern allows for flexible whitespace (e.g. \n, spaces) between contexts and target
            pattern = (
                f"({before_escaped})(\\s*)({target_escaped})(\\s*)({after_escaped})"
            )

            def replace_func_strat1(match_obj):
                return (
                    match_obj.group(1)
                    + match_obj.group(2)
                    + replacement
                    + match_obj.group(4)
                    + match_obj.group(5)
                )

            new_content, num_subs = re.subn(
                pattern,
                replace_func_strat1,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                logger.info("✅ Full context match successful for replace")
                return new_content

        # Strategy 2: Before context only
        if before_ctx is not None:
            logger.info("Replace Strategy 2: Before context matching")
            before_escaped = re.escape(before_ctx)
            pattern = f"({before_escaped})(\\s*)({target_escaped})"

            def replace_func_strat2(match_obj):
                return match_obj.group(1) + match_obj.group(2) + replacement

            new_content, num_subs = re.subn(
                pattern,
                replace_func_strat2,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                logger.info("✅ Before context match successful for replace")
                return new_content

        # Strategy 3: After context only
        if after_ctx is not None:
            logger.info("Replace Strategy 3: After context matching")
            after_escaped = re.escape(after_ctx)
            pattern = f"({target_escaped})(\\s*)({after_escaped})"

            def replace_func_strat3(match_obj):
                return replacement + match_obj.group(2) + match_obj.group(3)

            new_content, num_subs = re.subn(
                pattern,
                replace_func_strat3,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                logger.info("✅ After context match successful for replace")
                return new_content

        # Strategy 4: Direct target match (no context)
        logger.info("Replace Strategy 4: Direct target matching")
        pattern = f"({target_escaped})"  # Just the target

        def replace_func_strat4(match_obj):
            return replacement

        new_content, num_subs = re.subn(
            pattern,
            replace_func_strat4,
            current_content,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )
        if num_subs > 0:
            logger.info("✅ Direct target match successful for replace")
            return new_content

        # Strategy 5: Line-by-line fuzzy matching (from original, less preferred)
        logger.info(
            "Replace Strategy 5: Attempting line-by-line fuzzy matching (less precise)"
        )
        lines = current_content.splitlines()
        target_lines_list = target.splitlines()

        for i in range(len(lines) - len(target_lines_list) + 1):
            match = True
            for j, target_line_item in enumerate(target_lines_list):
                if lines[i + j].strip() != target_line_item.strip():
                    match = False
                    break
            if match:
                replacement_lines = replacement.splitlines()
                temp_lines = (
                    current_content.splitlines()
                )  # Use original splitlines for reconstruction
                temp_lines[i : i + len(target_lines_list)] = replacement_lines
                logger.info("✅ Line-by-line fuzzy match successful for replace")
                return "\n".join(temp_lines)

        raise ValueError(
            f"Could not find target content for replacement: '{target[:100]}...'. Ensure target and context (if provided) exactly match the file."
        )

    @staticmethod
    def _apply_insert_before(current_content: str, change: Dict[str, Any]) -> str:
        anchor = change.get("anchor_content")
        content_to_insert = change.get("content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not anchor:  # Anchor cannot be None or empty string
            raise ValueError(
                "anchor_content is required and cannot be empty for insert_before operation"
            )

        anchor_escaped = re.escape(anchor)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Insert_Before Strategy 1: Full context")
            pat = f"({re.escape(before_ctx)})(\\s*)({anchor_escaped})(\\s*)({re.escape(after_ctx)})"
            repl_func = (
                lambda m: m.group(1)
                + m.group(2)
                + content_to_insert
                + m.group(3)
                + m.group(4)
                + m.group(5)
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:
            logger.info("Insert_Before Strategy 2: Before context")
            pat = f"({re.escape(before_ctx)})(\\s*)({anchor_escaped})"
            repl_func = (
                lambda m: m.group(1) + m.group(2) + content_to_insert + m.group(3)
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:
            logger.info("Insert_Before Strategy 3: After context")
            pat = f"({anchor_escaped})(\\s*)({re.escape(after_ctx)})"
            repl_func = (
                lambda m: content_to_insert + m.group(1) + m.group(2) + m.group(3)
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        logger.info("Insert_Before Strategy 4: Direct anchor")
        pat = f"({anchor_escaped})"
        repl_func = lambda m: content_to_insert + m.group(1)
        new_content, num_subs = re.subn(
            pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find anchor_content for insert_before: '{anchor[:100]}...'. Ensure anchor and context (if provided) exactly match."
        )

    @staticmethod
    def _apply_insert_after(current_content: str, change: Dict[str, Any]) -> str:
        anchor = change.get("anchor_content")
        content_to_insert = change.get("content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not anchor:  # Anchor cannot be None or empty string
            raise ValueError(
                "anchor_content is required and cannot be empty for insert_after operation"
            )

        anchor_escaped = re.escape(anchor)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Insert_After Strategy 1: Full context")
            pat = f"({re.escape(before_ctx)})(\\s*)({anchor_escaped})(\\s*)({re.escape(after_ctx)})"
            repl_func = (
                lambda m: m.group(1)
                + m.group(2)
                + m.group(3)
                + content_to_insert
                + m.group(4)
                + m.group(5)
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:  # Match anchor when it's preceded by before_ctx
            logger.info("Insert_After Strategy 2: Before context (insert after anchor)")
            pat = f"({re.escape(before_ctx)})(\\s*)({anchor_escaped})"
            repl_func = (
                lambda m: m.group(1) + m.group(2) + m.group(3) + content_to_insert
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:  # Match anchor when it's followed by after_ctx
            logger.info("Insert_After Strategy 3: After context (insert after anchor)")
            pat = f"({anchor_escaped})(\\s*)({re.escape(after_ctx)})"
            # Insert content *after* the anchor, but *before* its own whitespace and after_ctx
            repl_func = (
                lambda m: m.group(1) + content_to_insert + m.group(2) + m.group(3)
            )
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        logger.info("Insert_After Strategy 4: Direct anchor")
        pat = f"({anchor_escaped})"
        repl_func = lambda m: m.group(1) + content_to_insert
        new_content, num_subs = re.subn(
            pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find anchor_content for insert_after: '{anchor[:100]}...'. Ensure anchor and context (if provided) exactly match."
        )

    @staticmethod
    def _apply_delete(current_content: str, change: Dict[str, Any]) -> str:
        target = change.get("target_content")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not target:  # Target cannot be None or empty string for delete
            raise ValueError(
                "target_content is required and cannot be empty for delete operation"
            )

        target_escaped = re.escape(target)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Delete Strategy 1: Full context")
            pat = f"({re.escape(before_ctx)})(\\s*)({target_escaped})(\\s*)({re.escape(after_ctx)})"
            repl_func = lambda m: m.group(1) + m.group(2) + m.group(4) + m.group(5)
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:
            logger.info("Delete Strategy 2: Before context")
            pat = f"({re.escape(before_ctx)})(\\s*)({target_escaped})"
            repl_func = lambda m: m.group(1) + m.group(2)
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:
            logger.info("Delete Strategy 3: After context")
            pat = f"({target_escaped})(\\s*)({re.escape(after_ctx)})"
            repl_func = lambda m: m.group(2) + m.group(3)
            new_content, num_subs = re.subn(
                pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
            )
            if num_subs > 0:
                return new_content

        logger.info("Delete Strategy 4: Direct target")
        pat = f"({target_escaped})"
        repl_func = lambda m: ""
        new_content, num_subs = re.subn(
            pat, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find target_content for delete: '{target[:100]}...'. Ensure target and context (if provided) exactly match."
        )

    @staticmethod
    def apply_contextual_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> str:
        modified_content = original_content
        for i, change_item in enumerate(changes):  # Renamed change to change_item
            # Ensure change_item is a dict, as Pydantic models might be passed in some contexts
            change_data = (
                change_item
                if isinstance(change_item, dict)
                else change_item.model_dump(exclude_none=True)
            )

            operation = change_data.get("operation")
            description = change_data.get("description", f"Change {i+1}")
            logger.info(
                f"Applying contextual change: operation='{operation}', description='{description}'"
            )

            if operation == "replace":
                modified_content = ContextualDiffProcessor._apply_replace(
                    modified_content, change_data
                )
            elif operation == "insert_before":
                modified_content = ContextualDiffProcessor._apply_insert_before(
                    modified_content, change_data
                )
            elif operation == "insert_after":
                modified_content = ContextualDiffProcessor._apply_insert_after(
                    modified_content, change_data
                )
            elif operation == "delete":
                modified_content = ContextualDiffProcessor._apply_delete(
                    modified_content, change_data
                )
            else:
                logger.error(
                    f"Unsupported contextual operation: {operation} for change: {change_data}"
                )
                raise ValueError(f"Unsupported contextual operation: {operation}")
        return modified_content

    @staticmethod
    def validate_contextual_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        for i, change_item in enumerate(changes):
            change_data = (
                change_item
                if isinstance(change_item, dict)
                else change_item.model_dump(exclude_none=True)
            )
            operation = change_data.get("operation")
            description = change_data.get("description", f"Change {i+1}")

            if not operation:
                return (
                    False,
                    f"Change {i+1} ('{description}') is missing 'operation' field.",
                )

            # Validate required fields based on operation
            if operation in ["replace", "delete"]:
                target_content_val = change_data.get("target_content")
                if target_content_val is None:  # Must be present
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) is missing 'target_content'.",
                    )
                if not target_content_val:  # Cannot be empty string
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) 'target_content' cannot be empty.",
                    )
                search_term_escaped = re.escape(target_content_val)
                term_type_for_error, term_value_for_error = (
                    "target_content",
                    target_content_val,
                )
            elif operation in ["insert_before", "insert_after"]:
                anchor_content_val = change_data.get("anchor_content")
                if anchor_content_val is None:  # Must be present
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) is missing 'anchor_content'.",
                    )
                if not anchor_content_val:  # Cannot be empty string
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) 'anchor_content' cannot be empty.",
                    )
                if (
                    change_data.get("content") is None
                ):  # Content to insert must be present (can be empty string)
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) is missing 'content' to insert.",
                    )
                search_term_escaped = re.escape(anchor_content_val)
                term_type_for_error, term_value_for_error = (
                    "anchor_content",
                    anchor_content_val,
                )
            else:
                return (
                    False,
                    f"Change {i+1} ('{description}') has unsupported operation: {operation}",
                )

            # Check if the search term (target or anchor) can be found with any context combination
            found_match = False
            before_ctx_val = change_data.get("before_context")
            after_ctx_val = change_data.get("after_context")

            # Strategy 1: Full context (if both provided)
            if before_ctx_val is not None and after_ctx_val is not None:
                pat = f"{re.escape(before_ctx_val)}\\s*{search_term_escaped}\\s*{re.escape(after_ctx_val)}"
                if re.search(pat, original_content, flags=re.DOTALL | re.MULTILINE):
                    found_match = True

            # Strategy 2: Before context only (if provided and full context didn't match or wasn't applicable)
            if not found_match and before_ctx_val is not None:
                pat = f"{re.escape(before_ctx_val)}\\s*{search_term_escaped}"
                if re.search(pat, original_content, flags=re.DOTALL | re.MULTILINE):
                    found_match = True

            # Strategy 3: After context only (if provided and previous didn't match)
            if not found_match and after_ctx_val is not None:
                pat = f"{search_term_escaped}\\s*{re.escape(after_ctx_val)}"
                if re.search(pat, original_content, flags=re.DOTALL | re.MULTILINE):
                    found_match = True

            # Strategy 4: Direct term match (if no context provided or context strategies failed)
            if not found_match:
                if re.search(
                    search_term_escaped,
                    original_content,
                    flags=re.DOTALL | re.MULTILINE,
                ):
                    found_match = True

            if not found_match:
                return False, (
                    f"Change {i+1} ('{description}', op: {operation}): "
                    f"Could not find {term_type_for_error} '{str(term_value_for_error)[:50]}...' "
                    f"with given context (Before: '{str(before_ctx_val)[:20]}...', After: '{str(after_ctx_val)[:20]}...'). "
                    f"Ensure target/anchor and context exactly match content in the file."
                )
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

        sorted_changes = sorted(
            changes, key=lambda x: x.get("start_line", x.get("line", 0)), reverse=True
        )

        for i, change in enumerate(sorted_changes):
            operation = change.get("operation")
            logger.info(
                f"Applying legacy partial change {i+1}/{len(sorted_changes)}: {operation}"
            )

            if operation == "replace":
                start_line = change["start_line"] - 1
                end_line = change["end_line"] - 1
                new_content = change.get(
                    "content", ""
                )  # Default to empty string if None

                if start_line < 0 or end_line >= total_lines or start_line > end_line:
                    logger.error(
                        f"Line numbers out of bounds or invalid range for replace: {start_line+1}-{end_line+1} (file has {total_lines} lines)"
                    )
                    continue

                lines[start_line : end_line + 1] = (
                    [new_content] if new_content or new_content == "" else []
                )
                total_lines = len(lines)

            elif operation == "insert":
                line_idx = change[
                    "line"
                ]  # 0-based index: insert *before* this line index.
                # So if line=0, inserts at beginning. if line=len(lines), appends.
                new_content = change.get("content", "")

                if line_idx < 0 or line_idx > total_lines:
                    logger.error(
                        f"Insert line index {line_idx} out of bounds (file has {total_lines} lines, insert valid 0 to {total_lines})"
                    )
                    continue
                lines.insert(line_idx, new_content)
                total_lines = len(lines)

            elif operation == "delete":
                start_line = change["start_line"] - 1
                end_line = change.get("end_line", change["start_line"]) - 1

                if start_line < 0 or end_line >= total_lines or start_line > end_line:
                    logger.error(
                        f"Delete line numbers out of bounds or invalid range: {start_line+1}-{end_line+1} (file has {total_lines} lines)"
                    )
                    continue

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
        lines = original_content.splitlines()
        max_line_num_for_replace_delete = len(
            lines
        )  # 1-based max line number for start/end
        max_line_idx_for_insert = len(
            lines
        )  # 0-based max line index for insert (append)

        for change_idx, change in enumerate(changes):
            operation = change.get("operation")

            if operation == "replace":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)

                if not (
                    1 <= start_line <= max_line_num_for_replace_delete
                    and 1 <= end_line <= max_line_num_for_replace_delete
                ):
                    return (
                        False,
                        f"Change {change_idx+1} (Replace): Line numbers {start_line}-{end_line} are out of range (file has {max_line_num_for_replace_delete} lines).",
                    )
                if start_line > end_line:
                    return (
                        False,
                        f"Change {change_idx+1} (Replace): start_line ({start_line}) > end_line ({end_line}).",
                    )
                if change.get("content") is None:
                    return (
                        False,
                        f"Change {change_idx+1} (Replace): 'content' field is missing.",
                    )

            elif operation == "insert":
                # 'line' is 0-based index, new content inserted *before* lines[line]
                # Valid range for 'line' is 0 to len(lines) inclusive.
                line_idx = change.get("line", -1)
                if not (0 <= line_idx <= max_line_idx_for_insert):
                    return (
                        False,
                        f"Change {change_idx+1} (Insert): Line index {line_idx} is out of range (file has {len(lines)} lines, valid 0 to {max_line_idx_for_insert}).",
                    )
                if change.get("content") is None:
                    return (
                        False,
                        f"Change {change_idx+1} (Insert): 'content' field is missing.",
                    )

            elif operation == "delete":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)

                if not (
                    1 <= start_line <= max_line_num_for_replace_delete
                    and 1 <= end_line <= max_line_num_for_replace_delete
                ):
                    return (
                        False,
                        f"Change {change_idx+1} (Delete): Line numbers {start_line}-{end_line} are out of range (file has {max_line_num_for_replace_delete} lines).",
                    )
                if start_line > end_line:
                    return (
                        False,
                        f"Change {change_idx+1} (Delete): start_line ({start_line}) > end_line ({end_line}).",
                    )

            elif not operation:
                return (False, f"Change {change_idx+1}: 'operation' field is missing.")
            else:
                return (
                    False,
                    f"Change {change_idx+1}: Unknown operation type '{operation}'.",
                )
        return True, ""


def create_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:
    lines = original_content.splitlines()
    preview_parts = []
    sorted_changes_for_preview = sorted(
        changes, key=lambda x: x.get("start_line", x.get("line", 0))
    )

    for change in sorted_changes_for_preview:
        operation = change.get("operation")

        if operation == "replace":
            start_line = change["start_line"]
            end_line = change["end_line"]
            new_content = change.get("content", "").strip()
            preview_parts.append(f"Replace lines {start_line}-{end_line}:")
            old_lines_preview = " ".join(
                lines[max(0, start_line - 1) : min(len(lines), end_line)]
            )[:100]
            preview_parts.append(
                f"  Old: {old_lines_preview}..."
                if len(old_lines_preview) >= 100
                else f"  Old: {old_lines_preview}"
            )
            preview_parts.append(
                f"  New: {new_content[:100]}..."
                if len(new_content) >= 100
                else f"  New: {new_content}"
            )

        elif operation == "insert":
            line_idx = change["line"]
            new_content = change.get("content", "").strip()
            preview_parts.append(
                f"Insert before line index {line_idx} (physical line {line_idx+1}):"
            )
            preview_parts.append(
                f"  Content: {new_content[:100]}..."
                if len(new_content) >= 100
                else f"  Content: {new_content}"
            )

        elif operation == "delete":
            start_line = change["start_line"]
            end_line = change.get("end_line", start_line)
            preview_parts.append(f"Delete lines {start_line}-{end_line}:")
            deleted_lines_preview = " ".join(
                lines[max(0, start_line - 1) : min(len(lines), end_line)]
            )[:100]
            preview_parts.append(
                f"  Content: {deleted_lines_preview}..."
                if len(deleted_lines_preview) >= 100
                else f"  Content: {deleted_lines_preview}"
            )
        preview_parts.append("")
    return "\n".join(preview_parts)


def create_contextual_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:
    preview_parts = []
    for i, change_item in enumerate(changes):
        change_data = (
            change_item
            if isinstance(change_item, dict)
            else change_item.model_dump(exclude_none=True)
        )
        operation = change_data.get("operation", "Unknown operation")
        desc = change_data.get("description", f"Change {i+1}")
        preview_parts.append(f"--- Change: {desc} (Operation: {operation}) ---")

        before_ctx_val = change_data.get("before_context", "")[:50]
        after_ctx_val = change_data.get("after_context", "")[:50]

        if operation == "replace":
            target = change_data.get("target_content", "")[:100]
            replacement = change_data.get("replacement_content", "")[:100]
            preview_parts.append(f"  Target: '{target}'...")
            if before_ctx_val:
                preview_parts.append(
                    f"    (Context Before Target: '{before_ctx_val}'...)"
                )
            if after_ctx_val:
                preview_parts.append(
                    f"    (Context After Target: '{after_ctx_val}'...)"
                )
            preview_parts.append(f"  Replacement: '{replacement}'...")

        elif operation in ["insert_after", "insert_before"]:
            anchor = change_data.get("anchor_content", "")[:100]
            content = change_data.get("content", "")[:100]
            preview_parts.append(f"  Anchor: '{anchor}'...")
            if before_ctx_val:
                preview_parts.append(
                    f"    (Context Before Anchor: '{before_ctx_val}'...)"
                )
            if after_ctx_val:
                preview_parts.append(
                    f"    (Context After Anchor: '{after_ctx_val}'...)"
                )
            preview_parts.append(f"  Content to insert: '{content}'...")

        elif operation == "delete":
            target = change_data.get("target_content", "")[:100]
            preview_parts.append(f"  Target to delete: '{target}'...")
            if before_ctx_val:
                preview_parts.append(f"    (Context Before: '{before_ctx_val}'...)")
            if after_ctx_val:
                preview_parts.append(f"    (Context After: '{after_ctx_val}'...)")

        preview_parts.append("")
    return "\n".join(preview_parts)
