from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import subprocess
from pathlib import Path
import logging

from agent import GeminiAgent, DEFAULT_MODEL_NAME
import utils

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware for frontend communication (adjust origins as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State (simplified for this example) ---
# In a production app, consider more robust state management or dependency injection patterns.
global_agent: Optional[GeminiAgent] = None
current_project_path: Optional[str] = None
chat_history: List[Dict[str, Any]] = []

# --- Pydantic Models for Request/Response ---
class ApiKeyRequest(BaseModel):
    api_key: str
    initial_model_id: Optional[str] = None # For setting preferred model on config

class ProjectPathRequest(BaseModel):
    project_path: str

class FileContentRequest(BaseModel):
    relative_file_path: str
    content: str

class ChatRequest(BaseModel):
    user_prompt: str
    current_open_file_relative_path: Optional[str] = None
    model_id: Optional[str] = None # For model selection per chat

class AIAction(BaseModel):
    type: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    folder_path: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    message: Optional[str] = None # For GENERAL_MESSAGE type

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

# --- Helper function for Git commands ---
def run_git_command(command_parts: List[str], project_path: Optional[str]) -> CommandOutput:
    if not project_path:
        raise HTTPException(status_code=400, detail="No project loaded. Cannot run git command.")
    try:
        process = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            cwd=project_path,
            check=False,
            universal_newlines=True # Ensures text mode for stdout/stderr
        )
        return CommandOutput(
            command=" ".join(command_parts),
            stdout=process.stdout.strip() if process.stdout else None,
            stderr=process.stderr.strip() if process.stderr else None,
            returncode=process.returncode
        )
    except FileNotFoundError:
        # Git command itself not found
        logger.error(f"Git command not found when trying to execute: {' '.join(command_parts)}")
        return CommandOutput(
            command=" ".join(command_parts),
            stdout=None,
            stderr="Error: git command not found. Is Git installed and in your PATH?",
            returncode=-1 # Use a distinct return code for this case
        )
    except Exception as e:
        logger.error(f"Error running git command {' '.join(command_parts)}: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing git command: {e}")


# --- API Endpoints ---

@app.post("/config/api-key")
async def configure_api_key(request: ApiKeyRequest):
    global global_agent
    try:
        initial_model = request.initial_model_id or DEFAULT_MODEL_NAME
        logger.info(f"Configuring agent with API key and initial model: {initial_model}")
        global_agent = GeminiAgent(api_key=request.api_key, initial_model_name=initial_model)
        if global_agent.is_ready():
            return {"message": f"Gemini Agent configured successfully with model {global_agent.get_current_model_name()}."}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize Gemini Agent. Check API key or server logs.")
    except Exception as e:
        logger.error(f"Error configuring API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/load")
async def load_project(request: ProjectPathRequest):
    global current_project_path, chat_history
    path = Path(request.project_path)
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid project path: Not a directory.")
    current_project_path = str(path.resolve())
    chat_history = [] # Reset chat history for new project
    return {"message": f"Project '{path.name}' loaded successfully.", "project_path": current_project_path}

@app.get("/project/structure")
async def get_project_structure_api():
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    structure = utils.get_project_structure(current_project_path)
    if not structure:
        raise HTTPException(status_code=500, detail="Failed to get project structure.")
    return structure

@app.get("/file/content")
async def get_file_content_api(relative_file_path: str): # Query parameter
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    abs_file_path = Path(current_project_path) / relative_file_path
    content = utils.read_file_content(str(abs_file_path))
    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found or unreadable: {relative_file_path}")
    return {"relative_file_path": relative_file_path, "content": content}

@app.post("/file/save")
async def save_file_api(request: FileContentRequest):
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")
    abs_file_path = Path(current_project_path) / request.relative_file_path
    if utils.write_file_content(str(abs_file_path), request.content):
        return {"message": f"File '{request.relative_file_path}' saved successfully."}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {request.relative_file_path}")

@app.post("/chat", response_model=AIResponse)
async def chat_with_ai(request: ChatRequest):
    global chat_history, global_agent
    if not global_agent or not global_agent.is_ready():
        # Try to re-initialize if not ready, could be a startup race or previous error
        if global_agent and hasattr(global_agent, 'api_key') and global_agent.api_key:
            logger.warning("AI Agent was not ready, attempting to re-initialize.")
            # Re-initialize with its current_model_name or default if current is not set
            model_to_try = global_agent.get_current_model_name() or DEFAULT_MODEL_NAME
            if not global_agent.set_model(model_to_try):
                 raise HTTPException(status_code=500, detail="AI Agent not configured or not ready after re-init attempt.")
        else:
            raise HTTPException(status_code=500, detail="AI Agent not configured. Please configure API key in settings.")
            
    if not current_project_path:
        raise HTTPException(status_code=400, detail="No project loaded.")

    # Handle model switching based on request's model_id or agent's current model
    target_model_id = request.model_id or global_agent.get_current_model_name()
    if not global_agent.set_model(target_model_id):
        # If setting the target model fails, try to fall back to the absolute default
        logger.warning(f"Failed to set AI model to '{target_model_id}'. Attempting to fall back to default model {DEFAULT_MODEL_NAME}.")
        if not global_agent.set_model(DEFAULT_MODEL_NAME):
            raise HTTPException(status_code=500, detail=f"Failed to set AI model to '{target_model_id}' and fallback to default also failed. Agent might be misconfigured or model unavailable.")
        logger.info(f"Successfully fell back to using model: {global_agent.get_current_model_name()}")
    else:
        logger.info(f"Using AI model: {global_agent.get_current_model_name()}")


    project_files_context = utils.get_all_project_files_context(current_project_path)
    
    current_file_content_for_ai: Optional[str] = None
    if request.current_open_file_relative_path:
        abs_current_file_path = Path(current_project_path) / request.current_open_file_relative_path
        current_file_content_for_ai = utils.read_file_content(str(abs_current_file_path))

    ai_context = {
        "file_paths": project_files_context.get("file_paths", []),
        "current_file_path": request.current_open_file_relative_path,
        "current_file_content": current_file_content_for_ai,
        "all_file_contents": project_files_context.get("all_file_contents", {}),
    }

    chat_history.append({"role": "user", "content": request.user_prompt})
    
    ai_response_data = global_agent.get_ai_response(request.user_prompt, ai_context, chat_history[:-1])
    
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
                folder_path = action_item.get('folder_path')
                if not folder_path: raise ValueError("folder_path missing")
                folder_to_create_abs = (project_root_abs_path / folder_path).resolve()
                if not utils.create_folder_if_not_exists(str(folder_to_create_abs)):
                    raise Exception(f"Failed to create folder: {folder_path}")
                results.append({"type": action_type, "path_info": folder_path, "status": "success"})
            
            elif action_type == "EDIT_FILE":
                file_path = action_item.get('file_path')
                content = action_item.get('content')
                if not file_path or content is None: raise ValueError("file_path or content missing")
                file_to_edit_abs = (project_root_abs_path / file_path).resolve()
                if not utils.write_file_content(str(file_to_edit_abs), content):
                    raise Exception(f"Failed to edit file: {file_path}")
                results.append({"type": action_type, "path_info": file_path, "status": "success"})

            elif action_type == "CREATE_FILE":
                file_path = action_item.get('file_path')
                content = action_item.get('content')
                if not file_path or content is None: raise ValueError("file_path or content missing")
                file_to_create_abs = (project_root_abs_path / file_path).resolve()
                if not utils.create_folder_if_not_exists(str(file_to_create_abs.parent)):
                     raise Exception(f"Failed to create parent dir for: {file_path}")
                if not utils.write_file_content(str(file_to_create_abs), content):
                    raise Exception(f"Failed to create file: {file_path}")
                results.append({"type": action_type, "path_info": file_path, "status": "success"})
            
            elif action_type == "EXECUTE_SHELL_COMMAND":
                command = action_item.get('command')
                if not command: raise ValueError("command missing")
                process = subprocess.run(
                    command,
                    shell=True, 
                    capture_output=True,
                    text=True,
                    cwd=current_project_path,
                    check=False,
                    universal_newlines=True
                )
                cmd_output = CommandOutput(
                    command=command,
                    stdout=process.stdout.strip() if process.stdout else None,
                    stderr=process.stderr.strip() if process.stderr else None,
                    returncode=process.returncode
                )
                status = "success" if process.returncode == 0 else "error"
                results.append({"type": action_type, "command": command, "status": status, "output": cmd_output.model_dump()})
            elif action_type == "GENERAL_MESSAGE":
                # GENERAL_MESSAGE is not typically an "applied" action, but log it if passed
                results.append({"type": action_type, "status": "skipped", "detail": "General message, no operation."})
            else:
                results.append({"type": action_type, "status": "skipped", "detail": "Unknown action type"})
        except Exception as e:
            path_info = action_item.get('file_path') or action_item.get('folder_path') or action_item.get('command')
            results.append({"type": action_type, "path_info": path_info, "status": "error", "detail": str(e)})
    
    return {"results": results}


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
    return run_git_command(["git", "commit", "-m", request.message], current_project_path)

@app.post("/git/push", response_model=CommandOutput)
async def git_push():
    return run_git_command(["git", "push"], current_project_path)

@app.get("/git/branch", response_model=CommandOutput)
async def git_current_branch():
    return run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], current_project_path)

@app.post("/git/pull", response_model=CommandOutput)
async def git_pull():
    return run_git_command(["git", "pull"], current_project_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
