import streamlit as st
from pathlib import Path
import difflib
import json
from typing import Any, Dict, Optional
import subprocess  # Added for shell command execution

import utils
from agent import GeminiAgent

st.set_page_config(layout="wide", page_title="Local AI Developer Agent")


# --- Session State Initialization ---
def init_session_state():
    defaults: Dict[str, Any] = {
        "api_key": None,
        "gemini_initialized": False,
        "project_path": None,  # Will store absolute path
        "project_name": "No Project Loaded",
        "project_files_structure": None,  # For sidebar tree display (nodes with absolute paths)
        "project_files_context": {  # For AI context (relative paths)
            "file_paths": [],
            "all_file_contents": {},
        },
        "selected_file_path": None,  # Will store absolute path
        "current_file_content": "",
        "chat_history": [],
        "ai_actions_to_apply": None,
        "unsaved_changes": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# --- Helper Functions ---
def load_project(path_str: str):
    if not path_str:
        st.sidebar.warning("Project path cannot be empty.")
        return
    try:
        resolved_path = Path(path_str).resolve()
    except (
        Exception
    ) as e:  # Catches potential errors during path resolution (e.g. invalid characters)
        st.error(f"Error resolving project path '{path_str}': {e}")
        st.session_state.project_path = None  # Clear previous path if any
        st.session_state.project_name = "No Project Loaded"
        return

    if resolved_path.is_dir():
        st.session_state.project_path = str(resolved_path)
        st.session_state.project_name = resolved_path.name
        refresh_project_data()  # This populates structure and context

        # Reset file-specific states
        st.session_state.selected_file_path = None
        st.session_state.current_file_content = ""
        st.session_state.unsaved_changes = False
        st.session_state.ai_actions_to_apply = None
        st.session_state.chat_history = []  # Clear chat for a new project context

        st.sidebar.success(f"Project '{st.session_state.project_name}' loaded!")
        st.rerun()  # Refresh UI
    else:
        st.error(f"Invalid project path: '{resolved_path}' is not a directory.")
        # Clear states if path was invalid after being set previously
        st.session_state.project_path = None
        st.session_state.project_name = "No Project Loaded"
        st.session_state.project_files_structure = None
        st.session_state.project_files_context = {
            "file_paths": [],
            "all_file_contents": {},
        }


def refresh_project_data():
    if st.session_state.project_path:
        st.session_state.project_files_structure = utils.get_project_structure(
            st.session_state.project_path
        )
        st.session_state.project_files_context = utils.get_all_project_files_context(
            st.session_state.project_path,
            max_total_chars=utils.MAX_PROJECT_CONTEXT_CHARS,
        )
        # If selected file no longer exists (e.g., deleted externally or by AI)
        if (
            st.session_state.selected_file_path
            and not Path(st.session_state.selected_file_path).exists()
        ):
            st.session_state.selected_file_path = None
            st.session_state.current_file_content = ""
            st.session_state.unsaved_changes = False
            st.info("Previously selected file no longer exists.")  # Inform user


def select_file(file_abs_path_str: str):  # Expects an absolute path string
    abs_file_path = Path(file_abs_path_str)  # Already resolved by utils

    if st.session_state.unsaved_changes and st.session_state.selected_file_path != str(
        abs_file_path
    ):
        st.warning(
            "Unsaved changes in the current file will be lost if you switch. Save the file first or proceed."
        )
        # For a production app, a modal confirmation (st.dialog) would be better here.
        # For now, the warning is sufficient.

    content = utils.read_file_content(str(abs_file_path))
    if content is not None:
        st.session_state.selected_file_path = str(abs_file_path)
        st.session_state.current_file_content = content
        st.session_state.unsaved_changes = False
        st.session_state.ai_actions_to_apply = (
            None  # Clear AI suggestions for previous file
        )
        st.rerun()  # Update editor and clear AI suggestions
    else:
        st.error(f"Could not read file: {abs_file_path.name}")


def save_current_file():
    if st.session_state.selected_file_path and st.session_state.unsaved_changes:
        file_name = Path(st.session_state.selected_file_path).name
        if utils.write_file_content(
            st.session_state.selected_file_path, st.session_state.current_file_content
        ):
            st.success(f"File '{file_name}' saved successfully.")
            st.session_state.unsaved_changes = False
            refresh_project_data()  # Update AI context with saved changes
            # No st.rerun() needed immediately, success message shown.
            # User can continue editing or AI will pick up new content on next interaction.
        else:
            st.error(f"Failed to save file '{file_name}'.")
    elif not st.session_state.selected_file_path:
        st.warning("No file selected to save.")
    elif not st.session_state.unsaved_changes:
        st.info("No unsaved changes to save.")


# --- UI Rendering ---

# Sidebar: API Key Configuration
st.sidebar.title("⚙️ Configuration")
api_key_input = st.sidebar.text_input(
    "Gemini API Key:",
    type="password",
    key="api_key_input_val",  # Ensure key is different from session_state key if needed
    value=st.session_state.api_key or "",  # Pre-fill from session state
)
if st.sidebar.button("Configure Gemini Agent", key="configure_gemini_button"):
    if api_key_input:
        st.session_state.api_key = api_key_input  # Store in session state
        # Attempt to initialize agent
        if "agent" in st.session_state:
            del st.session_state.agent  # Clear old agent
        st.session_state.agent = GeminiAgent(st.session_state.api_key)

        if st.session_state.agent.is_ready():
            st.sidebar.success("Gemini Agent configured successfully!")
            st.session_state.gemini_initialized = True
            st.rerun()  # Rerun to reflect initialized state
        else:
            # Agent's _configure_model should have set an error in st.error
            st.sidebar.error(
                "Agent configuration failed. Check error messages above or in console."
            )
            st.session_state.gemini_initialized = False
    else:
        st.sidebar.warning("Please enter an API key.")

if not st.session_state.gemini_initialized:
    st.info("👋 Welcome! Please configure your Gemini API Key in the sidebar to start.")
    st.stop()  # Halt further execution until API key is configured

# Sidebar: Project Loader & File Tree
st.sidebar.title("📁 Project Explorer")
project_path_from_session = st.session_state.project_path or ""
project_path_input = st.sidebar.text_input(
    "Project Folder Path:",
    value=project_path_from_session,  # Pre-fill from session state
    key="project_path_input_field",
    help="Enter the absolute or relative path to your project folder.",
)
if st.sidebar.button("Load Project", key="load_project_button"):
    if project_path_input:
        load_project(project_path_input)  # load_project handles rerun
    else:
        st.sidebar.warning("Please enter a project path.")

if st.session_state.project_path:
    st.sidebar.markdown(f"**Project:** `{st.session_state.project_name}`")
    st.sidebar.caption(f"`{st.session_state.project_path}`")  # Display absolute path
    if st.sidebar.button("Refresh File Tree", key="refresh_tree_button"):
        refresh_project_data()
        st.rerun()  # Rerun to redraw tree

    if st.session_state.project_files_structure:
        utils.display_file_tree_sidebar(
            st.session_state.project_files_structure,
            on_file_click=select_file,
            selected_file_path=st.session_state.selected_file_path,
        )
    else:
        st.sidebar.info("Project empty or structure not loaded. Try 'Refresh'.")
else:
    st.info(
        "👈 Load a project using the sidebar to explore files and chat with the AI."
    )
    st.stop()  # Halt if no project is loaded

# Main Area: Code Editor and Chat Panel
col_editor, col_chat = st.columns([2, 1])  # Editor takes 2/3, Chat 1/3

with col_editor:
    st.subheader("📝 Code Editor")
    if st.session_state.selected_file_path:
        selected_file_abs = Path(st.session_state.selected_file_path)
        project_root_abs = Path(st.session_state.project_path)
        try:
            # Display relative path for user-friendliness
            display_rel_path = selected_file_abs.relative_to(project_root_abs)
        except ValueError:  # Should not happen if selection is from tree
            display_rel_path = selected_file_abs.name

        st.markdown(f"**Editing:** `{str(display_rel_path)}`")

        edited_content = st.text_area(
            "File Content:",
            value=st.session_state.current_file_content,
            height=650,  # Increased height
            key=f"editor_{st.session_state.selected_file_path}",  # Force re-render on file switch
            help="Edit file content here. Save changes using the button below.",
        )
        if edited_content != st.session_state.current_file_content:
            st.session_state.current_file_content = edited_content
            st.session_state.unsaved_changes = True

        if st.button(
            "💾 Save File",
            key="save_file_button",
            disabled=not st.session_state.unsaved_changes,
            type="primary" if st.session_state.unsaved_changes else "secondary",
        ):
            save_current_file()
    else:
        st.info(
            "No file selected. Click a file in the Project Explorer to view or edit."
        )

    # Display AI suggested changes and diff
    if st.session_state.ai_actions_to_apply:
        st.subheader("🤖 AI Suggested Changes")
        ai_response_data = st.session_state.ai_actions_to_apply

        if ai_response_data.get("explanation"):
            with st.container(border=True):  # Visually group explanation
                st.markdown("**AI Explanation:**")
                st.markdown(ai_response_data["explanation"])

        actionable_items = [
            a
            for a in ai_response_data.get("actions", [])
            if a["type"]
            in ["EDIT_FILE", "CREATE_FILE", "CREATE_FOLDER", "EXECUTE_SHELL_COMMAND"]
        ]

        if not actionable_items:
            if not any(
                a["type"] == "GENERAL_MESSAGE"
                for a in ai_response_data.get("actions", [])
            ):  # Avoid double message if GENERAL_MESSAGE handled by chat
                st.markdown(
                    "No file modifications, creations, or shell commands were suggested by the AI for this response."
                )

        for idx, action in enumerate(ai_response_data.get("actions", [])):
            action_key_prefix = f"action_{idx}_{action.get('file_path', action.get('folder_path', action.get('command', 'general')))}"

            if action["type"] == "EDIT_FILE":
                with st.expander(f"✏️ Edit: `{action['file_path']}`", expanded=True):
                    target_file_abs = (
                        Path(st.session_state.project_path) / action["file_path"]
                    ).resolve()
                    original_content = ""
                    if target_file_abs.exists():
                        original_content = target_file_abs.read_text(
                            encoding="utf-8", errors="ignore"
                        )
                    else:  # File might be newly created by a previous action in same batch
                        original_content = (
                            "[File does not exist yet or is new in this set of actions]"
                        )

                    proposed_content = action["content"]
                    diff = list(
                        difflib.unified_diff(
                            original_content.splitlines(keepends=True),
                            proposed_content.splitlines(keepends=True),
                            fromfile=f"a/{action['file_path']}",
                            tofile=f"b/{action['file_path']}",
                            lineterm="",
                        )
                    )
                    if diff:
                        st.code("".join(diff), language="diff")
                    else:
                        st.markdown(
                            "_No textual changes, or this is the proposed content for a new/empty file._"
                        )
                        st.code(
                            proposed_content,
                            language=Path(action["file_path"]).suffix[1:].lower()
                            or "plaintext",
                        )

            elif action["type"] == "CREATE_FILE":
                with st.expander(
                    f"📄 Create New File: `{action['file_path']}`", expanded=True
                ):
                    st.code(
                        action["content"],
                        language=Path(action["file_path"]).suffix[1:].lower()
                        or "plaintext",
                    )

            elif action["type"] == "CREATE_FOLDER":
                st.markdown(f"➕ Create New Folder: `{action['folder_path']}`")

            elif action["type"] == "EXECUTE_SHELL_COMMAND":
                with st.expander(
                    f"⚙️ Execute Shell Command: `{action.get('command', 'N/A')}`",
                    expanded=True,
                ):
                    st.markdown(f"**Command:**")
                    st.code(
                        action.get("command", "No command provided."), language="shell"
                    )
                    if action.get("description"):
                        st.markdown(f"**Description:** {action['description']}")
                    st.warning(
                        "⚠️ Executing shell commands can have unintended consequences. Review carefully before applying.",
                        icon="❗",
                    )

        if actionable_items and st.button(
            "✅ Apply AI Changes", key="apply_ai_changes_button", type="primary"
        ):
            applied_all_successfully = True
            application_errors_for_ai_feedback = (
                []
            )  # Store detailed errors for AI feedback
            original_ai_response_that_failed = (
                st.session_state.ai_actions_to_apply
            )  # Keep a reference

            project_root_abs_path = Path(st.session_state.project_path)
            sorted_actions = sorted(
                ai_response_data["actions"],
                key=lambda x: 0 if x["type"] == "CREATE_FOLDER" else 1,
            )

            for action_idx, action_item in enumerate(sorted_actions):
                action_key_prefix_apply = f"apply_action_{action_idx}_{action_item.get('type')}_{action_item.get('file_path', action_item.get('folder_path', action_item.get('command', '')))}"

                if action_item["type"] == "CREATE_FOLDER":
                    folder_path = action_item.get("folder_path")
                    if folder_path:
                        folder_to_create_abs = (
                            project_root_abs_path / folder_path
                        ).resolve()
                        if not utils.create_folder_if_not_exists(
                            str(folder_to_create_abs)
                        ):
                            applied_all_successfully = False
                            err_msg = f"Failed to create folder: {folder_path}"
                            st.error(err_msg)
                            application_errors_for_ai_feedback.append(
                                {
                                    "type": "FILE_OPERATION_ERROR",
                                    "operation": "CREATE_FOLDER",
                                    "path": folder_path,
                                    "error": "Failed to create.",
                                }
                            )
                    else:
                        st.warning("CREATE_FOLDER action missing 'folder_path'.")
                        application_errors_for_ai_feedback.append(
                            {
                                "type": "MALFORMED_ACTION",
                                "action_type": "CREATE_FOLDER",
                                "error": "Missing 'folder_path'",
                            }
                        )

                elif action_item["type"] == "EDIT_FILE":
                    file_path = action_item.get("file_path")
                    content = action_item.get("content")
                    if file_path and content is not None:
                        file_to_edit_abs = (project_root_abs_path / file_path).resolve()
                        if not utils.write_file_content(str(file_to_edit_abs), content):
                            applied_all_successfully = False
                            err_msg = f"Failed to edit file: {file_path}"
                            st.error(err_msg)
                            application_errors_for_ai_feedback.append(
                                {
                                    "type": "FILE_OPERATION_ERROR",
                                    "operation": "EDIT_FILE",
                                    "path": file_path,
                                    "error": "Failed to write content.",
                                }
                            )
                        elif (
                            str(file_to_edit_abs) == st.session_state.selected_file_path
                        ):
                            st.session_state.current_file_content = content
                            st.session_state.unsaved_changes = False
                    else:
                        st.warning("EDIT_FILE action missing 'file_path' or 'content'.")
                        err_detail = []
                        if not file_path:
                            err_detail.append("Missing 'file_path'")
                        if content is None:
                            err_detail.append("Missing 'content'")
                        application_errors_for_ai_feedback.append(
                            {
                                "type": "MALFORMED_ACTION",
                                "action_type": "EDIT_FILE",
                                "error": ", ".join(err_detail),
                            }
                        )

                elif action_item["type"] == "CREATE_FILE":
                    file_path = action_item.get("file_path")
                    content = action_item.get("content")
                    if file_path and content is not None:
                        file_to_create_abs = (
                            project_root_abs_path / file_path
                        ).resolve()
                        if not utils.create_folder_if_not_exists(
                            str(file_to_create_abs.parent)
                        ):
                            applied_all_successfully = False
                            err_msg = f"Failed to create parent dir for: {file_path}"
                            st.error(err_msg)
                            application_errors_for_ai_feedback.append(
                                {
                                    "type": "FILE_OPERATION_ERROR",
                                    "operation": "CREATE_FILE_PARENT_DIR",
                                    "path": str(file_to_create_abs.parent),
                                    "error": "Failed to create parent directory.",
                                }
                            )
                        elif not utils.write_file_content(
                            str(file_to_create_abs), content
                        ):
                            applied_all_successfully = False
                            err_msg = f"Failed to create file: {file_path}"
                            st.error(err_msg)
                            application_errors_for_ai_feedback.append(
                                {
                                    "type": "FILE_OPERATION_ERROR",
                                    "operation": "CREATE_FILE",
                                    "path": file_path,
                                    "error": "Failed to write content.",
                                }
                            )
                    else:
                        st.warning(
                            "CREATE_FILE action missing 'file_path' or 'content'."
                        )
                        err_detail = []
                        if not file_path:
                            err_detail.append("Missing 'file_path'")
                        if content is None:
                            err_detail.append("Missing 'content'")
                        application_errors_for_ai_feedback.append(
                            {
                                "type": "MALFORMED_ACTION",
                                "action_type": "CREATE_FILE",
                                "error": ", ".join(err_detail),
                            }
                        )

                elif action_item["type"] == "EXECUTE_SHELL_COMMAND":
                    command_to_run = action_item.get("command")
                    if command_to_run:
                        st.info(f"Executing: `{command_to_run}`")
                        try:
                            process = subprocess.run(
                                command_to_run,
                                shell=True,
                                capture_output=True,
                                text=True,
                                cwd=st.session_state.project_path,
                                check=False,
                                universal_newlines=True,
                            )
                            st.markdown(f"**Output for `{command_to_run}`:**")
                            if process.stdout:
                                st.text_area(
                                    "Stdout:",
                                    process.stdout.strip(),
                                    height=100,
                                    key=f"stdout_{action_key_prefix_apply}_{action_idx}",
                                )
                            if process.stderr:
                                st.text_area(
                                    "Stderr:",
                                    process.stderr.strip(),
                                    height=100,
                                    key=f"stderr_{action_key_prefix_apply}_{action_idx}",
                                )

                            if process.returncode != 0:
                                st.error(
                                    f"Command exited with error code {process.returncode}."
                                )
                                applied_all_successfully = False
                                application_errors_for_ai_feedback.append(
                                    {
                                        "type": "SHELL_COMMAND_ERROR",
                                        "command": command_to_run,
                                        "returncode": process.returncode,
                                        "stdout": (
                                            process.stdout.strip()
                                            if process.stdout
                                            else ""
                                        ),
                                        "stderr": (
                                            process.stderr.strip()
                                            if process.stderr
                                            else ""
                                        ),
                                        "description": action_item.get("description"),
                                    }
                                )
                            else:
                                st.success("Command executed successfully.")
                        except Exception as e:
                            st.error(
                                f"Failed to execute command `{command_to_run}`: {e}"
                            )
                            applied_all_successfully = False
                            application_errors_for_ai_feedback.append(
                                {
                                    "type": "SHELL_COMMAND_ERROR",
                                    "command": command_to_run,
                                    "error_message": str(e),
                                    "description": action_item.get("description"),
                                }
                            )
                    else:
                        st.warning(
                            "No command provided for EXECUTE_SHELL_COMMAND action."
                        )
                        application_errors_for_ai_feedback.append(
                            {
                                "type": "MALFORMED_ACTION",
                                "action_type": "EXECUTE_SHELL_COMMAND",
                                "error": "Missing 'command'",
                            }
                        )

            # --- Automatic Error Feedback to AI ---
            if application_errors_for_ai_feedback:
                st.warning("Errors occurred. Preparing feedback for AI...")
                error_details_formatted = []
                for error_item in application_errors_for_ai_feedback:
                    if error_item["type"] == "SHELL_COMMAND_ERROR":
                        detail = f"- Shell Command Failed:\n  Command: {error_item['command']}\n"
                        if "returncode" in error_item:
                            detail += f"  Return Code: {error_item['returncode']}\n"
                        if error_item.get("stdout"):
                            detail += f"  Stdout:\n```\n{error_item['stdout']}\n```\n"
                        if error_item.get("stderr"):
                            detail += f"  Stderr:\n```\n{error_item['stderr']}\n```\n"
                        if error_item.get("error_message"):
                            detail += (
                                f"  Execution Error: {error_item['error_message']}\n"
                            )
                        error_details_formatted.append(detail)
                    elif error_item["type"] == "FILE_OPERATION_ERROR":
                        detail = f"- File Operation Failed:\n  Operation: {error_item['operation']}\n  Path: {error_item['path']}\n  Error: {error_item['error']}\n"
                        error_details_formatted.append(detail)
                    elif error_item["type"] == "MALFORMED_ACTION":
                        detail = f"- Malformed Action from AI:\n  Action Type: {error_item['action_type']}\n  Error: {error_item['error']}\n"
                        error_details_formatted.append(detail)
                formatted_errors_string = "\n".join(error_details_formatted)

                original_ai_actions_str = json.dumps(
                    original_ai_response_that_failed.get("actions", []), indent=2
                )

                history_copy = st.session_state.chat_history[:]
                last_user_prompt_for_failed_actions = "Unknown original prompt."
                if (
                    history_copy
                    and history_copy[-1]["role"] == "assistant"
                    and history_copy[-1]["content"] == original_ai_response_that_failed
                ):
                    if len(history_copy) > 1 and history_copy[-2]["role"] == "user":
                        last_user_prompt_for_failed_actions = history_copy[-2][
                            "content"
                        ]

                feedback_prompt = (
                    f"The following issues occurred when I tried to apply your previous suggestions.\n\n"
                    f"Original user request that led to these suggestions:\n'''\n{last_user_prompt_for_failed_actions}\n'''\n\n"
                    f"Your suggestions that were attempted (actions part only):\n'''json\n{original_ai_actions_str}\n'''\n\n"
                    f"Observed errors/issues:\n'''\n{formatted_errors_string}\n'''\n\n"
                    f"Please analyze these errors and the original context. Provide a new set of actions to fix these issues and achieve the original goal. "
                    f"If a shell command failed, explain why and provide a corrected command. "
                    f"If a file operation failed, consider if the path, content, or order of operations was problematic."
                )

                st.session_state.chat_history.append(
                    {"role": "user", "content": feedback_prompt}
                )

                relative_current_file_path_fb: Optional[str] = None
                if st.session_state.selected_file_path:
                    try:
                        selected_abs_fb = Path(st.session_state.selected_file_path)
                        project_abs_fb = Path(st.session_state.project_path)
                        if (
                            selected_abs_fb.is_absolute()
                            and project_abs_fb.is_absolute()
                            and selected_abs_fb.is_relative_to(project_abs_fb)
                        ):
                            relative_current_file_path_fb = selected_abs_fb.relative_to(
                                project_abs_fb
                            ).as_posix()
                        elif str(selected_abs_fb).startswith(str(project_abs_fb)):
                            relative_current_file_path_fb = str(
                                selected_abs_fb.relative_to(project_abs_fb)
                            ).replace("\\", "/")
                        else:
                            relative_current_file_path_fb = selected_abs_fb.name
                    except (ValueError, TypeError):
                        relative_current_file_path_fb = (
                            Path(st.session_state.selected_file_path).name
                            if st.session_state.selected_file_path
                            else None
                        )

                ai_context_for_feedback = {
                    "file_paths": st.session_state.project_files_context.get(
                        "file_paths", []
                    ),
                    "current_file_path": relative_current_file_path_fb,
                    "current_file_content": (
                        st.session_state.current_file_content
                        if st.session_state.selected_file_path
                        else None
                    ),
                    "all_file_contents": st.session_state.project_files_context.get(
                        "all_file_contents", {}
                    ),
                }

                agent_instance: GeminiAgent = st.session_state.agent
                history_for_ai_call = st.session_state.chat_history[:-1]

                with st.spinner("AI is reviewing the errors..."):
                    new_ai_response_data = agent_instance.get_ai_response(
                        user_prompt=feedback_prompt,
                        project_context=ai_context_for_feedback,
                        chat_history=history_for_ai_call,
                    )

                st.session_state.chat_history.append(
                    {"role": "assistant", "content": new_ai_response_data}
                )

                if any(
                    action["type"]
                    in [
                        "EDIT_FILE",
                        "CREATE_FILE",
                        "CREATE_FOLDER",
                        "EXECUTE_SHELL_COMMAND",
                    ]
                    for action in new_ai_response_data.get("actions", [])
                ):
                    st.session_state.ai_actions_to_apply = new_ai_response_data
                else:
                    st.session_state.ai_actions_to_apply = None

            elif applied_all_successfully:
                st.success("AI changes applied successfully!")
                st.session_state.ai_actions_to_apply = None
            else:
                st.error("Some AI changes could not be applied. Review messages above.")
                # Do not clear ai_actions_to_apply if it failed and no feedback was sent, so user can see them.

            refresh_project_data()
            st.rerun()

with col_chat:
    st.subheader("💬 AI Chat")
    chat_display_container = st.container(height=650)

    with chat_display_container:
        for msg_idx, message in enumerate(st.session_state.chat_history):
            with st.chat_message(message["role"]):
                content = message["content"]
                if (
                    isinstance(content, dict) and "explanation" in content
                ):  # AI's structured response
                    st.markdown(content["explanation"])
                    action_summary_parts = []
                    for action_data in content.get("actions", []):
                        if action_data["type"] == "EDIT_FILE":
                            action_summary_parts.append(
                                f"Edited `{action_data.get('file_path','N/A')}`"
                            )
                        elif action_data["type"] == "CREATE_FILE":
                            action_summary_parts.append(
                                f"Created `{action_data.get('file_path','N/A')}`"
                            )
                        elif action_data["type"] == "CREATE_FOLDER":
                            action_summary_parts.append(
                                f"Created folder `{action_data.get('folder_path','N/A')}`"
                            )
                        elif action_data["type"] == "EXECUTE_SHELL_COMMAND":
                            action_summary_parts.append(
                                f"Executed shell: `{action_data.get('command','N/A')}`"
                            )
                        elif (
                            action_data["type"] == "GENERAL_MESSAGE"
                            and action_data.get("message")
                            and action_data["message"] != content["explanation"]
                        ):
                            st.markdown(
                                f"*Additional Message: {action_data['message']}*"
                            )
                    if action_summary_parts:
                        st.caption("Actions: " + "; ".join(action_summary_parts))
                elif isinstance(content, str):
                    st.markdown(content)
                else:
                    st.text(str(content))

    user_prompt = st.chat_input(
        "Ask the AI to help with your project...",
        key="chat_input_field",
        disabled=(not st.session_state.agent or not st.session_state.agent.is_ready()),
    )

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        relative_current_file_path: Optional[str] = None
        if st.session_state.selected_file_path:
            try:
                selected_abs = Path(st.session_state.selected_file_path)
                project_abs = Path(st.session_state.project_path)
                if (
                    selected_abs.is_absolute()
                    and project_abs.is_absolute()
                    and selected_abs.is_relative_to(project_abs)
                ):
                    relative_current_file_path = selected_abs.relative_to(
                        project_abs
                    ).as_posix()
                else:
                    if str(selected_abs).startswith(str(project_abs)):
                        relative_current_file_path = str(
                            selected_abs.relative_to(project_abs)
                        ).replace("\\", "/")
                    else:
                        relative_current_file_path = selected_abs.name
            except (ValueError, TypeError):
                relative_current_file_path = (
                    Path(st.session_state.selected_file_path).name
                    if st.session_state.selected_file_path
                    else None
                )

        ai_context = {
            "file_paths": st.session_state.project_files_context.get("file_paths", []),
            "current_file_path": relative_current_file_path,
            "current_file_content": (
                st.session_state.current_file_content
                if st.session_state.selected_file_path
                else None
            ),
            "all_file_contents": st.session_state.project_files_context.get(
                "all_file_contents", {}
            ),
        }

        agent: GeminiAgent = st.session_state.agent
        with st.spinner("AI is thinking..."):
            ai_response_data = agent.get_ai_response(
                user_prompt, ai_context, st.session_state.chat_history[:-1]
            )

        st.session_state.chat_history.append(
            {"role": "assistant", "content": ai_response_data}
        )

        if any(
            action["type"]
            in ["EDIT_FILE", "CREATE_FILE", "CREATE_FOLDER", "EXECUTE_SHELL_COMMAND"]
            for action in ai_response_data.get("actions", [])
        ):
            st.session_state.ai_actions_to_apply = ai_response_data
        else:
            st.session_state.ai_actions_to_apply = None

        st.rerun()

    if st.button("Clear Chat History", key="clear_chat_button"):
        st.session_state.chat_history = []
        st.session_state.ai_actions_to_apply = None
        st.rerun()
