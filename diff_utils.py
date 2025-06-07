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
    def _normalize_whitespace_for_search(text: str) -> str:
        """Normalizes whitespace in a string for more robust regex searching.
        Converts multiple whitespace characters (including newlines) to a single space,
        and trims leading/trailing whitespace.
        This is for FINDING text, not for REPLACING text.
        """
        if not text:
            return ""
        # Replace multiple whitespace chars (including newlines if they are part of the logical search block)
        # with a single space. This helps if AI has slight variations in spacing/newlines.
        # Be careful with this, as it can make matches too broad.
        # A less aggressive approach is to make regex patterns more flexible with \s* or \s+.
        # For now, we'll primarily rely on flexible regex.
        return text  # For now, return as is, and rely on regex flexibility.

    @staticmethod
    def _build_search_pattern(
        term_to_find_escaped: str,
        before_ctx: Optional[str],
        after_ctx: Optional[str],
        strategy_name: str,
    ) -> Optional[str]:
        """Helper to build regex patterns for different strategies."""
        if before_ctx is not None and after_ctx is not None:
            # Strategy: Full context
            # logger.debug(f"{strategy_name}: Full context pattern")
            return f"({re.escape(before_ctx)})(\\s*)({term_to_find_escaped})(\\s*)({re.escape(after_ctx)})"

        if before_ctx is not None:
            # Strategy: Before context only
            # logger.debug(f"{strategy_name}: Before context pattern")
            return f"({re.escape(before_ctx)})(\\s*)({term_to_find_escaped})"

        if after_ctx is not None:
            # Strategy: After context only
            # logger.debug(f"{strategy_name}: After context pattern")
            return f"({term_to_find_escaped})(\\s*)({re.escape(after_ctx)})"

        # Strategy: Direct term match (no context)
        # logger.debug(f"{strategy_name}: Direct term pattern")
        return f"({term_to_find_escaped})"

    @staticmethod
    def _find_match_for_validation(
        original_content: str,
        term_to_find: str,  # This is the target_content or anchor_content
        before_ctx: Optional[str],
        after_ctx: Optional[str],
    ) -> bool:
        """
        Tries to find the term_to_find with various context strategies for validation.
        Returns True if found, False otherwise.
        """
        if not term_to_find:  # term_to_find itself cannot be empty
            return False

        term_to_find_escaped = re.escape(term_to_find)

        # Try with full context if available
        if before_ctx is not None and after_ctx is not None:
            pattern = ContextualDiffProcessor._build_search_pattern(
                term_to_find_escaped, before_ctx, after_ctx, "Validation Full"
            )
            if pattern and re.search(
                pattern, original_content, flags=re.DOTALL | re.MULTILINE
            ):
                return True

        # Try with before context if available
        if before_ctx is not None:
            pattern = ContextualDiffProcessor._build_search_pattern(
                term_to_find_escaped, before_ctx, None, "Validation Before"
            )
            if pattern and re.search(
                pattern, original_content, flags=re.DOTALL | re.MULTILINE
            ):
                return True

        # Try with after context if available
        if after_ctx is not None:
            pattern = ContextualDiffProcessor._build_search_pattern(
                term_to_find_escaped, None, after_ctx, "Validation After"
            )
            if pattern and re.search(
                pattern, original_content, flags=re.DOTALL | re.MULTILINE
            ):
                return True

        # Try direct match of the term_to_find
        pattern = ContextualDiffProcessor._build_search_pattern(
            term_to_find_escaped, None, None, "Validation Direct"
        )
        if pattern and re.search(
            pattern, original_content, flags=re.DOTALL | re.MULTILINE
        ):
            return True

        return False

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
            "confidence": "low",
        }

    @staticmethod
    def _apply_replace(current_content: str, change: Dict[str, Any]) -> str:
        target = change.get("target_content", "")
        replacement = change.get("replacement_content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not target:
            raise ValueError(
                "target_content is required and cannot be empty for replace operation"
            )

        target_escaped = re.escape(target)

        # Strategy 1: Full context match
        if before_ctx is not None and after_ctx is not None:
            logger.info("Replace Strategy 1: Full context matching")
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, before_ctx, after_ctx, "ApplyReplace Full"
            )
            repl_func = (
                lambda m: m.group(1)
                + m.group(2)
                + replacement
                + m.group(4)
                + m.group(5)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
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
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, before_ctx, None, "ApplyReplace Before"
            )
            repl_func = lambda m: m.group(1) + m.group(2) + replacement
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
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
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, None, after_ctx, "ApplyReplace After"
            )
            repl_func = lambda m: replacement + m.group(2) + m.group(3)
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                logger.info("✅ After context match successful for replace")
                return new_content

        # Strategy 4: Direct target match (no context)
        logger.info("Replace Strategy 4: Direct target matching")
        pattern = ContextualDiffProcessor._build_search_pattern(
            target_escaped, None, None, "ApplyReplace Direct"
        )
        repl_func = lambda m: replacement
        new_content, num_subs = re.subn(
            pattern, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            logger.info("✅ Direct target match successful for replace")
            return new_content

        # Fallback to line-by-line if regex fails (less precise, from previous implementation)
        logger.warning(
            f"Regex replace failed for target '{target[:50]}...'. Attempting line-by-line fuzzy match as last resort."
        )
        lines = current_content.splitlines()
        target_lines_list = target.splitlines()
        if not target_lines_list:  # Cannot replace with empty target lines list
            raise ValueError(
                f"Cannot perform line-by-line replace: target content '{target[:100]}...' is empty or only whitespace after splitlines."
            )

        for i in range(len(lines) - len(target_lines_list) + 1):
            match = True
            for j, target_line_item in enumerate(target_lines_list):
                if (
                    lines[i + j].strip() != target_line_item.strip()
                ):  # Compare stripped lines
                    match = False
                    break
            if match:
                # Preserve original line endings of the file as much as possible by splitting replacement by \n
                # and then joining with the detected line ending or \n as default.
                # This is a simplified approach. True preservation is complex.
                replacement_lines_for_join = replacement.splitlines()

                # Reconstruct: original lines before match + replacement lines + original lines after match
                # This assumes AI provides `replacement` with its own correct internal newlines.
                # The overall structure is preserved by joining with `\n` which is common.
                temp_lines_original_split = (
                    current_content.splitlines()
                )  # split without keepends for this reconstruction
                temp_lines_original_split[i : i + len(target_lines_list)] = (
                    replacement_lines_for_join
                )

                logger.info(
                    "✅ Line-by-line fuzzy match successful for replace (last resort)"
                )
                return "\n".join(temp_lines_original_split)

        raise ValueError(
            f"Could not find target content for replacement: '{target[:100]}...'. All strategies failed. Ensure target and context (if provided) exactly match the file."
        )

    @staticmethod
    def _apply_insert_before(current_content: str, change: Dict[str, Any]) -> str:
        anchor = change.get("anchor_content")
        content_to_insert = change.get("content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not anchor:
            raise ValueError(
                "anchor_content is required and cannot be empty for insert_before operation"
            )

        anchor_escaped = re.escape(anchor)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Insert_Before Strategy 1: Full context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, before_ctx, after_ctx, "ApplyInsertBefore Full"
            )
            repl_func = (
                lambda m: m.group(1)
                + m.group(2)
                + content_to_insert
                + m.group(3)
                + m.group(4)
                + m.group(5)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:
            logger.info("Insert_Before Strategy 2: Before context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, before_ctx, None, "ApplyInsertBefore Before"
            )
            repl_func = (
                lambda m: m.group(1) + m.group(2) + content_to_insert + m.group(3)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:
            logger.info("Insert_Before Strategy 3: After context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, None, after_ctx, "ApplyInsertBefore After"
            )
            repl_func = (
                lambda m: content_to_insert + m.group(1) + m.group(2) + m.group(3)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        logger.info("Insert_Before Strategy 4: Direct anchor")
        pattern = ContextualDiffProcessor._build_search_pattern(
            anchor_escaped, None, None, "ApplyInsertBefore Direct"
        )
        repl_func = lambda m: content_to_insert + m.group(1)
        new_content, num_subs = re.subn(
            pattern, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find anchor_content for insert_before: '{anchor[:100]}...'. All strategies failed. Ensure anchor and context (if provided) exactly match."
        )

    @staticmethod
    def _apply_insert_after(current_content: str, change: Dict[str, Any]) -> str:
        anchor = change.get("anchor_content")
        content_to_insert = change.get("content", "")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not anchor:
            raise ValueError(
                "anchor_content is required and cannot be empty for insert_after operation"
            )

        anchor_escaped = re.escape(anchor)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Insert_After Strategy 1: Full context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, before_ctx, after_ctx, "ApplyInsertAfter Full"
            )
            repl_func = (
                lambda m: m.group(1)
                + m.group(2)
                + m.group(3)
                + content_to_insert
                + m.group(4)
                + m.group(5)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:
            logger.info("Insert_After Strategy 2: Before context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, before_ctx, None, "ApplyInsertAfter Before"
            )
            repl_func = (
                lambda m: m.group(1) + m.group(2) + m.group(3) + content_to_insert
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:
            logger.info("Insert_After Strategy 3: After context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                anchor_escaped, None, after_ctx, "ApplyInsertAfter After"
            )
            repl_func = (
                lambda m: m.group(1) + content_to_insert + m.group(2) + m.group(3)
            )
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        logger.info("Insert_After Strategy 4: Direct anchor")
        pattern = ContextualDiffProcessor._build_search_pattern(
            anchor_escaped, None, None, "ApplyInsertAfter Direct"
        )
        repl_func = lambda m: m.group(1) + content_to_insert
        new_content, num_subs = re.subn(
            pattern, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find anchor_content for insert_after: '{anchor[:100]}...'. All strategies failed. Ensure anchor and context (if provided) exactly match."
        )

    @staticmethod
    def _apply_delete(current_content: str, change: Dict[str, Any]) -> str:
        target = change.get("target_content")
        before_ctx = change.get("before_context")
        after_ctx = change.get("after_context")

        if not target:
            raise ValueError(
                "target_content is required and cannot be empty for delete operation"
            )

        target_escaped = re.escape(target)

        if before_ctx is not None and after_ctx is not None:
            logger.info("Delete Strategy 1: Full context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, before_ctx, after_ctx, "ApplyDelete Full"
            )
            repl_func = lambda m: m.group(1) + m.group(2) + m.group(4) + m.group(5)
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if before_ctx is not None:
            logger.info("Delete Strategy 2: Before context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, before_ctx, None, "ApplyDelete Before"
            )
            repl_func = lambda m: m.group(1) + m.group(2)
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        if after_ctx is not None:
            logger.info("Delete Strategy 3: After context")
            pattern = ContextualDiffProcessor._build_search_pattern(
                target_escaped, None, after_ctx, "ApplyDelete After"
            )
            repl_func = lambda m: m.group(2) + m.group(3)
            new_content, num_subs = re.subn(
                pattern,
                repl_func,
                current_content,
                count=1,
                flags=re.DOTALL | re.MULTILINE,
            )
            if num_subs > 0:
                return new_content

        logger.info("Delete Strategy 4: Direct target")
        pattern = ContextualDiffProcessor._build_search_pattern(
            target_escaped, None, None, "ApplyDelete Direct"
        )
        repl_func = lambda m: ""
        new_content, num_subs = re.subn(
            pattern, repl_func, current_content, count=1, flags=re.DOTALL | re.MULTILINE
        )
        if num_subs > 0:
            return new_content

        raise ValueError(
            f"Could not find target_content for delete: '{target[:100]}...'. All strategies failed. Ensure target and context (if provided) exactly match."
        )

    @staticmethod
    def apply_contextual_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> str:
        modified_content = original_content
        for i, change_item in enumerate(changes):
            change_data = (
                change_item
                if isinstance(change_item, dict)
                else change_item.model_dump(exclude_none=True)
            )
            operation = change_data.get("operation")
            description = change_data.get("description", f"Change {i+1} ({operation})")
            logger.info(f"Applying contextual change: {description}")

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
                err_msg = f"Unsupported contextual operation: '{operation}' for change: {description}"
                logger.error(err_msg)
                raise ValueError(err_msg)
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

            term_to_find = ""
            term_type_for_error = ""

            if operation in ["replace", "delete"]:
                target_content_val = change_data.get("target_content")
                if target_content_val is None:
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) is missing 'target_content'.",
                    )
                if not target_content_val:  # Cannot be empty string for these ops
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) 'target_content' cannot be empty.",
                    )
                term_to_find = target_content_val
                term_type_for_error = "target_content"
            elif operation in ["insert_before", "insert_after"]:
                anchor_content_val = change_data.get("anchor_content")
                if anchor_content_val is None:
                    return (
                        False,
                        f"Change {i+1} ('{description}', op: {operation}) is missing 'anchor_content'.",
                    )
                if not anchor_content_val:  # Cannot be empty string for these ops
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
                term_to_find = anchor_content_val
                term_type_for_error = "anchor_content"
            else:
                return (
                    False,
                    f"Change {i+1} ('{description}') has unsupported operation: {operation}",
                )

            before_ctx_val = change_data.get("before_context")
            after_ctx_val = change_data.get("after_context")

            if not ContextualDiffProcessor._find_match_for_validation(
                original_content, term_to_find, before_ctx_val, after_ctx_val
            ):
                error_detail = (
                    f"Could not find {term_type_for_error} '{str(term_to_find)[:100]}...' "
                    f"with given context. "
                    f"Before context searched: '{str(before_ctx_val)[:50]}...'. "
                    f"After context searched: '{str(after_ctx_val)[:50]}...'. "
                    f"Ensure target/anchor and context exactly match content in the file, including whitespace and newlines. "
                    f"The system tries multiple matching strategies (full context, partial context, direct match)."
                )
                logger.warning(
                    f"Validation failed for change {i+1} ('{description}', op: {operation}): {error_detail}"
                )
                return (
                    False,
                    f"Change {i+1} ('{description}', op: {operation}): {error_detail}",
                )
        return True, ""


class DiffProcessor:  # Legacy line-based
    @staticmethod
    def apply_partial_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> str:
        lines = original_content.splitlines(keepends=True)
        total_lines = len(lines)
        logger.info(f"Legacy partial: Original content has {total_lines} lines")
        sorted_changes = sorted(
            changes, key=lambda x: x.get("start_line", x.get("line", 0)), reverse=True
        )
        for i, change in enumerate(sorted_changes):
            operation = change.get("operation")
            logger.info(
                f"Legacy partial: Applying change {i+1}/{len(sorted_changes)}: {operation}"
            )
            if operation == "replace":
                start_line = change["start_line"] - 1
                end_line = change["end_line"] - 1
                new_content = change.get("content", "")
                if not (0 <= start_line <= end_line < total_lines):
                    logger.error(
                        f"Legacy partial: Line numbers out of bounds for replace: {start_line+1}-{end_line+1}"
                    )
                    continue
                lines[start_line : end_line + 1] = (
                    [new_content] if new_content or new_content == "" else []
                )
                total_lines = len(lines)
            elif operation == "insert":
                line_idx = change["line"]
                new_content = change.get("content", "")
                if not (0 <= line_idx <= total_lines):
                    logger.error(
                        f"Legacy partial: Insert line index {line_idx} out of bounds"
                    )
                    continue
                lines.insert(line_idx, new_content)
                total_lines = len(lines)
            elif operation == "delete":
                start_line = change["start_line"] - 1
                end_line = change.get("end_line", change["start_line"]) - 1
                if not (0 <= start_line <= end_line < total_lines):
                    logger.error(
                        f"Legacy partial: Delete line numbers out of bounds: {start_line+1}-{end_line+1}"
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
        return "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=fromfile,
                tofile=tofile,
                lineterm="",
            )
        )

    @staticmethod
    def validate_changes(
        original_content: str, changes: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        lines = original_content.splitlines()
        max_line_num = len(lines)
        max_line_idx_insert = len(lines)

        for idx, change in enumerate(changes):
            op = change.get("operation")
            if op == "replace":
                s, e = change.get("start_line", 0), change.get("end_line", 0)
                if not (1 <= s <= e <= max_line_num):
                    return (
                        False,
                        f"L-Replace {idx+1}: Lines {s}-{e} out of range (1-{max_line_num})",
                    )
                if change.get("content") is None:
                    return False, f"L-Replace {idx+1}: Missing content"
            elif op == "insert":
                l = change.get("line", -1)
                if not (0 <= l <= max_line_idx_insert):
                    return (
                        False,
                        f"L-Insert {idx+1}: Line {l} out of range (0-{max_line_idx_insert})",
                    )
                if change.get("content") is None:
                    return False, f"L-Insert {idx+1}: Missing content"
            elif op == "delete":
                s, e = change.get("start_line", 0), change.get(
                    "end_line", change.get("start_line", 0)
                )
                if not (1 <= s <= e <= max_line_num):
                    return (
                        False,
                        f"L-Delete {idx+1}: Lines {s}-{e} out of range (1-{max_line_num})",
                    )
            elif not op:
                return False, f"L-Change {idx+1}: Missing operation"
            else:
                return False, f"L-Change {idx+1}: Unknown op '{op}'"
        return True, ""


def create_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:  # Legacy preview
    lines = original_content.splitlines()
    preview_parts = [f"Preview of legacy line-based changes for: {file_path}"]
    sorted_changes = sorted(
        changes, key=lambda x: x.get("start_line", x.get("line", 0))
    )
    for chg in sorted_changes:
        op = chg.get("operation")
        if op == "replace":
            s, e = chg["start_line"], chg["end_line"]
            nc = chg.get("content", "").strip()[:100]
            preview_parts.append(f"Replace lines {s}-{e} with: '{nc}...'")
        elif op == "insert":
            lidx = chg["line"]
            nc = chg.get("content", "").strip()[:100]
            preview_parts.append(
                f"Insert before line index {lidx} (physical line {lidx+1}): '{nc}...'"
            )
        elif op == "delete":
            s, e = chg["start_line"], chg.get("end_line", chg["start_line"])
            preview_parts.append(f"Delete lines {s}-{e}")
    return "\n".join(preview_parts)


def create_contextual_change_preview(
    original_content: str, changes: List[Dict[str, Any]], file_path: str
) -> str:
    preview_parts = [f"Preview of contextual changes for: {file_path}"]
    for i, change_item in enumerate(changes):
        chg = (
            change_item
            if isinstance(change_item, dict)
            else change_item.model_dump(exclude_none=True)
        )
        op = chg.get("operation", "Unknown")
        desc = chg.get("description", f"Ctx Change {i+1}")
        preview_parts.append(f"\n--- {desc} (Op: {op}) ---")
        if op == "replace":
            preview_parts.append(f"  Target: '{chg.get('target_content','')[:50]}...'")
            if chg.get("before_context"):
                preview_parts.append(
                    f"    CtxBefore: '{chg.get('before_context')[:30]}...'"
                )
            if chg.get("after_context"):
                preview_parts.append(
                    f"    CtxAfter: '{chg.get('after_context')[:30]}...'"
                )
            preview_parts.append(
                f"  ReplaceWith: '{chg.get('replacement_content','')[:50]}...'"
            )
        elif op in ["insert_after", "insert_before"]:
            preview_parts.append(f"  Anchor: '{chg.get('anchor_content','')[:50]}...'")
            if chg.get("before_context"):
                preview_parts.append(
                    f"    CtxBeforeAnchor: '{chg.get('before_context')[:30]}...'"
                )
            if chg.get("after_context"):
                preview_parts.append(
                    f"    CtxAfterAnchor: '{chg.get('after_context')[:30]}...'"
                )
            preview_parts.append(f"  InsertContent: '{chg.get('content','')[:50]}...'")
        elif op == "delete":
            preview_parts.append(
                f"  TargetToDelete: '{chg.get('target_content','')[:50]}...'"
            )
            if chg.get("before_context"):
                preview_parts.append(
                    f"    CtxBefore: '{chg.get('before_context')[:30]}...'"
                )
            if chg.get("after_context"):
                preview_parts.append(
                    f"    CtxAfter: '{chg.get('after_context')[:30]}...'"
                )
    return "\n".join(preview_parts)
