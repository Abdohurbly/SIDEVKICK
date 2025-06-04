from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import subprocess
from pathlib import Path
import logging
from diff_utils import DiffProcessor, ContextualDiffProcessor

from agent import (
    GeminiAgent,
    OpenAIAgent,
    AnthropicAgent,
    DEFAULT_GEMINI_MODEL_NAME,
    DEFAULT_OPENAI_MODEL_NAME,
    DEFAULT_ANTHROPIC_MODEL_NAME,
)
import utils

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State ---
global_agent: Optional[Union[GeminiAgent, OpenAIAgent, AnthropicAgent]] = None
current_ai_provider: Optional[str] = None
current_project_path: Optional[str] = None
chat_history: List[Dict[str, Any]] = []
use_rag: bool = True  # Flag to enable/disable RAG

PROVIDER_DEFAULT_MODELS = {
    "gemini": DEFAULT_GEMINI_MODEL_NAME,
    "openai": DEFAULT_OPENAI_MODEL_NAME,
    "anthropic": DEFAULT_ANTHROPIC_MODEL_NAME,
}


# --- Pydantic Models for Request/Response ---
class ApiKeyRequest(BaseModel):
    api_key: str
    provider: str
    initial_model_id: Optional[str] = None


class ProjectPathRequest(BaseModel):
    project_path: str


class FileContentRequest(BaseModel):
    relative_file_path: str
    content: str


class ChatRequest(BaseModel):
    user_prompt: str
    current_open_file_relative_path: Optional[str] = None
    model_id: Optional[str] = None  # For model selection per chat
    use_rag: Optional[bool] = None  # Override global RAG setting


class AIAction(BaseModel):
    type: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    folder_path: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    message: Optional[str] = None
    changes: Optional[List[Dict[str, Any]]] = None  # For partial edits


class AIResponse(BaseModel):
    explanation: str
    actions: List[AIAction]


class ApplyActionsRequest(BaseModel):
    actions: List[AIAction]


class CommandOutput(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: int
    command: str


class GitCommitRequest(BaseModel):
    message: str


class RAGSettings(BaseModel):
    enabled: bool
    max_tokens: Optional[int] = 20000


# --- Helper function for Git commands ---
def run_git_command(
    command_parts: List[str], project_path: Optional[str]
) -> CommandOutput:
    if not project_path:
        raise HTTPException(
            status_code=400, detail="No project loaded. Cannot run git command."
        )
    try:
        process = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            cwd=project_path,
            check=False,
            universal_newlines=True,
        )
        return CommandOutput(
            command=" ".join(command_parts),
            stdout=process.stdout.strip() if process.stdout else None,
            stderr=process.stderr.strip() if process.stderr else None,
            returncode=process.returncode,
        )
    except FileNotFoundError:
        logger.error(
            f"Git command not found when trying to execute: {' '.join(command_parts)}"
        )
        return CommandOutput(
            command=" ".join(command_parts),
            stdout=None,
            stderr="Error: git command not found. Is Git installed and in your PATH?",
            returncode=-1,
        )
    except Exception as e:
        logger.error(f"Error running git command {' '.join(command_parts)}: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing git command: {e}")


# --- API Endpoints ---


@app.post("/config/api-key")
async def configure_api_key(request: ApiKeyRequest):
    global global_agent, current_ai_provider
    try:
        logger.info(
            f"Configuring AI provider: {request.provider} with API key and model: {request.initial_model_id}"
        )

        default_model_for_provider = PROVIDER_DEFAULT_MODELS.get(request.provider)
        if not default_model_for_provider:
            # Fallback if provider is somehow unknown to our defaults, though UI should prevent this.
            default_model_for_provider = "default-model"
            logger.warning(
                f"Provider {request.provider} not in PROVIDER_DEFAULT_MODELS, using generic default."
            )

        initial_model = request.initial_model_id or default_model_for_provider

        if request.provider == "gemini":
            global_agent = GeminiAgent(
                api_key=request.api_key, initial_model_name=initial_model
            )
        elif request.provider == "openai":
            global_agent = OpenAIAgent(
                api_key=request.api_key, initial_model_name=initial_model
            )
        elif request.provider == "anthropic":
            global_agent = AnthropicAgent(
                api_key=request.api_key, initial_model_name=initial_model
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported AI provider: {request.provider}"
            )

        current_ai_provider = request.provider

        if global_agent and global_agent.is_ready():
            return {
                "message": f"{request.provider.capitalize()} Agent configured successfully with model {global_agent.get_current_model_name()}.".replace(
                    "Gemini Agent", "Gemini"
                )
            }
        else:
            # Agent-specific error should be logged by the agent's constructor/config method
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize {request.provider.capitalize()} Agent. Check API key or server logs.",
            )
    except (
        ValueError
    ) as ve:  # Catch specific errors like missing API key from agent constructors
        logger.error(f"Configuration ValueError for {request.provider}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error configuring API key for {request.provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/project/load")
async def load_project(request: ProjectPathRequest):
    global current_project_path, chat_history
    path = Path(request.project_path)
    if not path.is_dir():
        raise HTTPException(
            status_code=400, detail="Invalid project path: Not a directory."
        )
    current_project_path = str(path.resolve())
    chat_history = []

    # Initialize RAG system for the project
    if use_rag:
        try:
            logger.info("Initializing RAG system for project...")
            utils.get_rag_system(current_project_path)
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")

    return {
        "message": f"Project '{path.name}' loaded successfully.",
        "project_path": current_project_path,
    }


@app.get("/project/structure")
async def get_project_structure_api():
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    structure = utils.get_project_structure(current_project_path)
    if not structure:
        raise HTTPException(status_code=500, detail="Failed to get project structure.")
    return structure


@app.get("/file/content")
async def get_file_content_api(relative_file_path: str):
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    abs_file_path = Path(current_project_path) / relative_file_path
    content = utils.read_file_content(str(abs_file_path))
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"File not found or unreadable: {relative_file_path}",
        )
    return {"relative_file_path": relative_file_path, "content": content}


@app.post("/file/save")
async def save_file_api(request: FileContentRequest):
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    abs_file_path = Path(current_project_path) / request.relative_file_path
    if utils.write_file_content(str(abs_file_path), request.content):
        return {"message": f"File '{request.relative_file_path}' saved successfully."}
    else:
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {request.relative_file_path}"
        )


@app.post("/chat", response_model=AIResponse)
async def chat_with_ai(request: ChatRequest):
    global chat_history, global_agent, current_ai_provider, use_rag

    if not global_agent or not global_agent.is_ready():
        # Attempt to re-initialize if necessary (e.g. if API key was set but an error occurred)
        # This part might need more robust handling depending on how API keys are stored/managed if they can be invalid
        if (
            global_agent
            and hasattr(global_agent, "api_key")
            and global_agent.api_key
            and current_ai_provider
        ):
            logger.warning(
                f"{current_ai_provider.capitalize()} Agent was not ready, attempting to re-initialize."
            )
            model_to_try = (
                global_agent.get_current_model_name()
                or PROVIDER_DEFAULT_MODELS.get(current_ai_provider, "default-model")
            )
            if not global_agent.set_model(model_to_try):
                raise HTTPException(
                    status_code=500,
                    detail=f"{current_ai_provider.capitalize()} Agent not configured or not ready after re-init attempt.",
                )
        else:
            raise HTTPException(
                status_code=500,
                detail="AI Agent not configured. Please configure API key and provider in settings.",
            )

    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")

    target_model_id = request.model_id or global_agent.get_current_model_name()
    if not global_agent.set_model(target_model_id):
        logger.warning(
            f"Failed to set AI model to '{target_model_id}' for {current_ai_provider}. Attempting to fall back to provider's default."
        )
        provider_default_model = PROVIDER_DEFAULT_MODELS.get(
            current_ai_provider, "default-model"
        )  # Fallback for safety
        if not global_agent.set_model(provider_default_model):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set AI model to '{target_model_id}' and fallback to provider's default '{provider_default_model}' also failed. Agent might be misconfigured or model unavailable.",
            )
        logger.info(
            f"Successfully fell back to using model: {global_agent.get_current_model_name()} for {current_ai_provider}"
        )
    else:
        logger.info(
            f"Using AI model: {global_agent.get_current_model_name()} for {current_ai_provider}"
        )

    # Choose context method: RAG or traditional
    should_use_rag = request.use_rag if request.use_rag is not None else use_rag

    if should_use_rag:
        try:
            logger.info("Using RAG for context retrieval...")
            project_files_context = utils.get_rag_context(
                user_query=request.user_prompt,
                project_path=current_project_path,
                current_file=request.current_open_file_relative_path,
                max_tokens=20000,
            )
            context_method = "RAG"
            # Add editing recommendation for RAG
            project_files_context["editing_recommendation"] = (
                "Use EDIT_FILE_COMPLETE - you have targeted chunks"
            )
        except Exception as e:
            logger.error(f"RAG failed, falling back to traditional method: {e}")
            project_files_context = utils.get_context_with_editing_hints(
                project_path=current_project_path,
                use_rag=False,
                current_file=request.current_open_file_relative_path,
                user_query=request.user_prompt,
            )
            context_method = "Traditional (RAG fallback)"
    else:
        logger.info("Using traditional context retrieval with editing hints...")
        project_files_context = utils.get_context_with_editing_hints(
            project_path=current_project_path,
            use_rag=False,
            current_file=request.current_open_file_relative_path,
            user_query=request.user_prompt,
        )
        context_method = "Traditional"

    current_file_content_for_ai: Optional[str] = None
    if request.current_open_file_relative_path:
        abs_current_file_path = (
            Path(current_project_path) / request.current_open_file_relative_path
        )
        current_file_content_for_ai = utils.read_file_content(
            str(abs_current_file_path)
        )

    ai_context = {
        "file_paths": project_files_context.get("file_paths", []),
        "current_file_path": request.current_open_file_relative_path,
        "current_file_content": current_file_content_for_ai,
        "all_file_contents": project_files_context.get("all_file_contents", {}),
        "context_method": context_method,
        "rag_metadata": project_files_context.get("rag_metadata", {}),
        "editing_recommendation": project_files_context.get(
            "editing_recommendation", ""
        ),
        "large_files": project_files_context.get("large_files", []),
    }

    chat_history.append({"role": "user", "content": request.user_prompt})

    ai_response_data = global_agent.get_ai_response(
        request.user_prompt, ai_context, chat_history[:-1]
    )

    # Add context metadata to response
    if "rag_metadata" in project_files_context:
        ai_response_data["context_info"] = {
            "method": context_method,
            "chunks_used": project_files_context["rag_metadata"].get("total_chunks", 0),
            "estimated_tokens": project_files_context["rag_metadata"].get(
                "estimated_tokens", 0
            ),
        }

    chat_history.append({"role": "assistant", "content": ai_response_data})
    return AIResponse(**ai_response_data)


@app.post("/actions/apply")
async def apply_ai_actions(request: ApplyActionsRequest):
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")

    project_root_abs_path = Path(current_project_path)
    results = []
    sorted_actions = sorted(
        request.actions,
        key=lambda x: 0 if x.type == "CREATE_FOLDER" else 1,
    )

    for action_item_model in sorted_actions:
        action_item = action_item_model.model_dump(exclude_none=True)
        action_type = action_item["type"]
        try:
            if action_type == "CREATE_FOLDER":
                folder_path = action_item.get("folder_path")
                if not folder_path:
                    raise ValueError("folder_path missing")
                folder_to_create_abs = (project_root_abs_path / folder_path).resolve()
                if not utils.create_folder_if_not_exists(str(folder_to_create_abs)):
                    raise Exception(f"Failed to create folder: {folder_path}")
                results.append(
                    {"type": action_type, "path_info": folder_path, "status": "success"}
                )

            elif action_type == "EDIT_FILE_COMPLETE" or action_type == "EDIT_FILE":
                file_path = action_item.get("file_path")
                content = action_item.get("content")
                if not file_path or content is None:
                    raise ValueError("file_path or content missing")
                file_to_edit_abs = (project_root_abs_path / file_path).resolve()
                if not utils.write_file_content(str(file_to_edit_abs), content):
                    raise Exception(f"Failed to edit file: {file_path}")
                results.append(
                    {"type": action_type, "path_info": file_path, "status": "success"}
                )

            elif action_type == "EDIT_FILE_PARTIAL":
                file_path = action_item.get("file_path")
                changes = action_item.get("changes", [])

                if not file_path or not changes:
                    raise ValueError("file_path or changes missing")

                file_to_edit_abs = (project_root_abs_path / file_path).resolve()

                if not file_to_edit_abs.exists():
                    raise Exception(f"File does not exist: {file_path}")

                # Read original content
                original_content = file_to_edit_abs.read_text(
                    encoding="utf-8", errors="ignore"
                )

                # Validate and apply changes
                valid, error_msg = DiffProcessor.validate_changes(
                    original_content, changes
                )
                if not valid:
                    raise Exception(f"Invalid changes: {error_msg}")

                modified_content = DiffProcessor.apply_partial_changes(
                    original_content, changes
                )

                if not utils.write_file_content(
                    str(file_to_edit_abs), modified_content
                ):
                    raise Exception(
                        f"Failed to write partial changes to file: {file_path}"
                    )

                results.append(
                    {
                        "type": action_type,
                        "path_info": file_path,
                        "status": "success",
                        "changes_applied": len(changes),
                    }
                )

            elif action_type == "CREATE_FILE":
                file_path = action_item.get("file_path")
                content = action_item.get("content")
                if not file_path or content is None:
                    raise ValueError("file_path or content missing")
                file_to_create_abs = (project_root_abs_path / file_path).resolve()
                if not utils.create_folder_if_not_exists(
                    str(file_to_create_abs.parent)
                ):
                    raise Exception(f"Failed to create parent dir for: {file_path}")
                if not utils.write_file_content(str(file_to_create_abs), content):
                    raise Exception(f"Failed to create file: {file_path}")
                results.append(
                    {"type": action_type, "path_info": file_path, "status": "success"}
                )

            elif action_type == "EDIT_FILE_CONTEXTUAL":
                file_path = action_item.get("file_path")

                if not file_path:
                    raise ValueError("file_path is required for contextual edit")

                file_to_edit_abs = (project_root_abs_path / file_path).resolve()

                if not file_to_edit_abs.exists():
                    raise Exception(f"File does not exist: {file_path}")

                # Read original content
                original_content = file_to_edit_abs.read_text(
                    encoding="utf-8", errors="ignore"
                )

                logger.info(f"Applying contextual edit to {file_path}")

                # Create a single change from the action
                contextual_change = {
                    "operation": action_item.get("operation"),
                    "target_content": action_item.get("target_content"),
                    "replacement_content": action_item.get("replacement_content"),
                    "anchor_content": action_item.get("anchor_content"),
                    "before_context": action_item.get("before_context"),
                    "after_context": action_item.get("after_context"),
                    "content": action_item.get("content"),  # For insert operations
                }

                # Validate the contextual change
                valid, error_msg = ContextualDiffProcessor.validate_contextual_changes(
                    original_content, [contextual_change]
                )
                if not valid:
                    logger.error(f"Contextual validation failed: {error_msg}")
                    raise Exception(f"Invalid contextual change: {error_msg}")

                try:
                    modified_content = ContextualDiffProcessor.apply_contextual_changes(
                        original_content, [contextual_change]
                    )
                except Exception as e:
                    logger.error(f"Failed to apply contextual change: {e}")
                    raise Exception(f"Failed to apply contextual change: {str(e)}")

                if not utils.write_file_content(
                    str(file_to_edit_abs), modified_content
                ):
                    raise Exception(
                        f"Failed to write contextual changes to file: {file_path}"
                    )

                results.append(
                    {
                        "type": action_type,
                        "path_info": file_path,
                        "status": "success",
                        "operation": action_item.get("operation"),
                    }
                )

            # Also add support for multiple contextual changes in one action
            elif action_type == "EDIT_FILE_CONTEXTUAL_BATCH":
                file_path = action_item.get("file_path")
                contextual_changes = action_item.get("changes", [])

                if not file_path or not contextual_changes:
                    raise ValueError(
                        "file_path and changes are required for contextual batch edit"
                    )

                file_to_edit_abs = (project_root_abs_path / file_path).resolve()

                if not file_to_edit_abs.exists():
                    raise Exception(f"File does not exist: {file_path}")

                # Read original content
                original_content = file_to_edit_abs.read_text(
                    encoding="utf-8", errors="ignore"
                )

                logger.info(
                    f"Applying {len(contextual_changes)} contextual changes to {file_path}"
                )

                # Validate all contextual changes
                valid, error_msg = ContextualDiffProcessor.validate_contextual_changes(
                    original_content, contextual_changes
                )
                if not valid:
                    logger.error(f"Contextual validation failed: {error_msg}")
                    raise Exception(f"Invalid contextual changes: {error_msg}")

                try:
                    modified_content = ContextualDiffProcessor.apply_contextual_changes(
                        original_content, contextual_changes
                    )
                except Exception as e:
                    logger.error(f"Failed to apply contextual changes: {e}")
                    raise Exception(f"Failed to apply contextual changes: {str(e)}")

                if not utils.write_file_content(
                    str(file_to_edit_abs), modified_content
                ):
                    raise Exception(
                        f"Failed to write contextual changes to file: {file_path}"
                    )

                results.append(
                    {
                        "type": action_type,
                        "path_info": file_path,
                        "status": "success",
                        "changes_applied": len(contextual_changes),
                    }
                )

            elif action_type == "EXECUTE_SHELL_COMMAND":
                command = action_item.get("command")
                if not command:
                    raise ValueError("command missing")
                process = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=current_project_path,
                    check=False,
                    universal_newlines=True,
                )
                cmd_output = CommandOutput(
                    command=command,
                    stdout=process.stdout.strip() if process.stdout else None,
                    stderr=process.stderr.strip() if process.stderr else None,
                    returncode=process.returncode,
                )
                status = "success" if process.returncode == 0 else "error"
                results.append(
                    {
                        "type": action_type,
                        "command": command,
                        "status": status,
                        "output": cmd_output.model_dump(),
                    }
                )
            elif action_type == "GENERAL_MESSAGE":
                results.append(
                    {
                        "type": action_type,
                        "status": "skipped",
                        "detail": "General message, no operation.",
                    }
                )
            else:
                results.append(
                    {
                        "type": action_type,
                        "status": "skipped",
                        "detail": "Unknown action type",
                    }
                )
        except Exception as e:
            path_info = (
                action_item.get("file_path")
                or action_item.get("folder_path")
                or action_item.get("command")
            )
            results.append(
                {
                    "type": action_type,
                    "path_info": path_info,
                    "status": "error",
                    "detail": str(e),
                }
            )

    return {"results": results}


# --- RAG Management Endpoints ---


@app.get("/rag/settings")
async def get_rag_settings():
    """Get current RAG settings"""
    global use_rag
    return {"enabled": use_rag, "max_tokens": 20000}


@app.post("/rag/settings")
async def update_rag_settings(settings: RAGSettings):
    """Update RAG settings"""
    global use_rag
    use_rag = settings.enabled
    return {
        "message": f"RAG {'enabled' if use_rag else 'disabled'}",
        "settings": settings,
    }


@app.post("/rag/reindex")
async def reindex_project():
    """Force reindexing of the current project"""
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")

    try:
        # Clear existing cache
        utils.invalidate_rag_cache(current_project_path)

        # Reindex
        rag_system = utils.get_rag_system(current_project_path)
        chunk_count = rag_system.index_project()

        return {
            "message": "Project reindexed successfully",
            "chunks_indexed": chunk_count,
        }
    except Exception as e:
        logger.error(f"Failed to reindex project: {e}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


@app.get("/rag/status")
async def get_rag_status():
    """Get RAG system status for current project"""
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")

    try:
        rag_system = utils.get_rag_system(current_project_path)
        return {
            "indexed": len(rag_system.chunks) > 0,
            "total_chunks": len(rag_system.chunks),
            "cache_exists": rag_system.chunks_cache_file.exists(),
        }
    except Exception as e:
        return {
            "indexed": False,
            "total_chunks": 0,
            "cache_exists": False,
            "error": str(e),
        }


@app.get("/chat/history")
async def get_chat_history():
    return chat_history


@app.delete("/chat/history")
async def clear_chat_history_api():
    global chat_history
    chat_history = []
    return {"message": "Chat history cleared."}


# --- Git Endpoints ---
@app.get("/git/status", response_model=CommandOutput)
async def git_status():
    return run_git_command(["git", "status", "--porcelain"], current_project_path)


@app.post("/git/add_all", response_model=CommandOutput)
async def git_add_all():
    return run_git_command(["git", "add", "."], current_project_path)


@app.post("/git/commit", response_model=CommandOutput)
async def git_commit(request: GitCommitRequest):
    if not request.message:
        raise HTTPException(status_code=400, detail="Commit message cannot be empty.")
    return run_git_command(
        ["git", "commit", "-m", request.message], current_project_path
    )


@app.post("/git/push", response_model=CommandOutput)
async def git_push():
    return run_git_command(["git", "push"], current_project_path)


@app.get("/git/branch", response_model=CommandOutput)
async def git_current_branch():
    return run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], current_project_path
    )


@app.post("/git/pull", response_model=CommandOutput)
async def git_pull():
    return run_git_command(["git", "pull"], current_project_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
