import google.generativeai as genai
import json
import logging # Changed from streamlit

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model name. This can be overridden during agent initialization or by set_model.
DEFAULT_MODEL_NAME = "gemini-2.5-pro-preview-05-06"

SYSTEM_PROMPT = """
You are a Local AI Developer Agent. You are assisting a developer working on a local project.
Your goal is to help with tasks like editing files, refactoring code, generating new files/folders, and explaining or documenting code.

You will be provided with:
1. The user's request.
2. The project's file structure (a list of relative file paths).
3. The content of the currently open file and its relative path (if any file is open).
4. A dictionary of all file contents in the project (relative path -> content). Content may be truncated. This provides a snapshot of the entire project, so analyze it thoroughly to understand the context for the user's request.
5. Chat history for context.

When responding, you MUST use the following JSON format. Do NOT include any text outside the JSON block (e.g. no "```json" or "```" markers).

{
  "explanation": "A brief explanation of what you did, what the code does, or your analysis. This will always be displayed to the user. This field is mandatory.",
  "actions": [
    {
      "type": "EDIT_FILE",
      "file_path": "relative/path/to/file.py",
      "content": "The ENTIRE new content of the file. Be very careful to provide the complete file content, not just a diff or snippet."
    },
    {
      "type": "CREATE_FILE",
      "file_path": "relative/path/to/new_file.py",
      "content": "The content for the new file."
    },
    {
      "type": "CREATE_FOLDER",
      "folder_path": "relative/path/to/new_folder"
    },
    {
      "type": "EXECUTE_SHELL_COMMAND",
      "command": "The shell command to execute. e.g., 'pip install pandas'",
      "description": "A brief description of what this command does or why it's needed."
    },
    {
      "type": "GENERAL_MESSAGE",
      "message": "Use this for general explanations, documentation, or if no file operations are needed. The main answer can also be in the 'explanation' field."
    }
  ]
}

Guidelines:
- Base your understanding on the entire project context provided, especially `all_file_contents`.
- If the user asks for an explanation or documentation, use the "GENERAL_MESSAGE" action type in the `actions` array, and provide the core information in the "explanation" field.
- If you are editing a file, provide the *complete* new content for that file in the "content" field of the "EDIT_FILE" action.
- Ensure all file paths in "EDIT_FILE", "CREATE_FILE", and "CREATE_FOLDER" actions are relative to the project root.
- If you need to create a folder before creating a file within it, ensure the "CREATE_FOLDER" action for the parent directory is listed BEFORE the "CREATE_FILE" action in the `actions` array.
- If the user's request is unclear or you need more information, use the "GENERAL_MESSAGE" action to ask clarifying questions (primarily in the 'explanation' field).
- If no specific file operations are required by the user's request (e.g., "what does this function do?"), provide the answer in "explanation" and can use a "GENERAL_MESSAGE" action if further detail is needed in the message field.
- The "explanation" field should always provide a human-readable summary of your response or actions.
- If multiple actions are needed (e.g., edit multiple files, create a folder then a file inside it), include them all in the "actions" list in the correct order.
- If the request is to generate a new file, and its parent directory might not exist, include a "CREATE_FOLDER" action for the parent directory first.
- If you encounter an unrecoverable error or cannot fulfill the request, explain why in the "explanation" field and use a "GENERAL_MESSAGE" action.
- For `EXECUTE_SHELL_COMMAND`, ensure the command is safe and relevant to the user's local development environment.
"""


class GeminiAgent:
    def __init__(self, api_key: str, initial_model_name: str = DEFAULT_MODEL_NAME):
        self.api_key = api_key
        self.current_model_name = initial_model_name
        self.model = None
        self._initialized_successfully = False
        self._configure_model()

    def _configure_model(self):
        try:
            genai.configure(api_key=self.api_key)
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",  # Enforce JSON output
                temperature=0.7,  # Adjust for creativity vs. precision
                # max_output_tokens=8192, # Ensure this is adequate for your needs
            )
            self.model = genai.GenerativeModel(
                self.current_model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config=generation_config,
            )
            self._initialized_successfully = True
            logger.info(f"Gemini Agent configured successfully with model: {self.current_model_name}.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini with model {self.current_model_name}: {e}")
            self._initialized_successfully = False
            self.model = None

    def set_model(self, new_model_name: str) -> bool:
        if new_model_name == self.current_model_name and self.is_ready():
            logger.info(f"Model {new_model_name} is already set and ready.")
            return True
        
        logger.info(f"Attempting to set model to: {new_model_name}")
        self.current_model_name = new_model_name
        self._configure_model()
        if self.is_ready():
            logger.info(f"Successfully set model to: {new_model_name}")
        else:
            logger.error(f"Failed to set model to: {new_model_name}")
        return self.is_ready()
    
    def get_current_model_name(self) -> str:
        return self.current_model_name

    def is_ready(self) -> bool:
        return self.model is not None and self._initialized_successfully

    def get_ai_response(
        self, user_prompt: str, project_context: dict, chat_history: list
    ) -> dict:
        if not self.is_ready():
            return {
                "explanation": f"Gemini model ({self.current_model_name}) not initialized. Please check API key and configuration.",
                "actions": [],
            }

        gemini_chat_history = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            if role == "model" and isinstance(content, dict):
                try:
                    gemini_chat_history.append(
                        {"role": role, "parts": [json.dumps(content)]}
                    )
                except TypeError as e:
                    gemini_chat_history.append(
                        {
                            "role": role,
                            "parts": [
                                f"Error serializing previous model response: {e}"
                            ],
                        }
                    )
            elif isinstance(content, str):
                gemini_chat_history.append({"role": role, "parts": [content]})
            else:
                gemini_chat_history.append({"role": role, "parts": [str(content)]})

        context_parts = [f"User Request: {user_prompt}\n"]
        context_parts.append("Project File Structure (relative paths):")
        if project_context.get("file_paths"):
            for p_path in project_context["file_paths"]:
                context_parts.append(f"- {p_path}")
        else:
            context_parts.append("No files in project or project not loaded.")
        context_parts.append("\n")

        if (
            project_context.get("current_file_path")
            and project_context.get("current_file_content") is not None
        ):
            context_parts.append(
                f"Currently Open File Relative Path: {project_context['current_file_path']}"
            )
            context_parts.append("Current Open File Content:")
            context_parts.append("```")
            context_parts.append(project_context["current_file_content"])
            context_parts.append("```\n")
        else:
            context_parts.append("No file is currently open in the editor.\n")

        context_parts.append(
            "All Project File Contents (relative_path -> content, content may be truncated):"
        )
        if project_context.get("all_file_contents"):
            for rel_path, content_text in project_context["all_file_contents"].items():
                context_parts.append(f"\n--- File: {rel_path} ---")
                context_parts.append(content_text)
                context_parts.append("--- End File ---")
        else:
            context_parts.append("No file contents available for the project.")

        full_user_content_for_gemini = "\n".join(context_parts)

        try:
            if gemini_chat_history:
                chat = self.model.start_chat(history=gemini_chat_history)
                response = chat.send_message(full_user_content_for_gemini)
            else:
                response = self.model.generate_content(full_user_content_for_gemini)

            raw_response_text = response.text.strip()

            # Remove potential markdown code block fences
            if raw_response_text.startswith("```json"):
                raw_response_text = raw_response_text[7:-3].strip()
            elif raw_response_text.startswith("```") and raw_response_text.endswith(
                "```"
            ):
                raw_response_text = raw_response_text[3:-3].strip()

            try:
                parsed_response = json.loads(raw_response_text)
                if not isinstance(parsed_response, dict):
                    logger.warning(
                        f"AI response was valid JSON but not a dictionary. Raw: {raw_response_text}"
                    )
                    return {
                        "explanation": f"AI response format error: Expected a JSON object. Raw: {raw_response_text}",
                        "actions": [
                            {"type": "GENERAL_MESSAGE", "message": raw_response_text}
                        ],
                    }

                if (
                    "explanation" not in parsed_response
                    or "actions" not in parsed_response
                ):
                    logger.warning(
                        f"AI response JSON was valid but missed 'explanation' or 'actions'. Raw response: {raw_response_text}"
                    )
                    return {
                        "explanation": f"AI response JSON structure error: Missing 'explanation' or 'actions' keys. The AI did not follow the required output format. Raw response from AI: {raw_response_text}",
                        "actions": [
                            {
                                "type": "GENERAL_MESSAGE",
                                "message": f"AI response format error. Raw response: {raw_response_text}",
                            }
                        ],
                    }
                if not isinstance(parsed_response.get("actions"), list):
                    logger.warning(
                        f"AI response 'actions' field was not a list. Raw: {raw_response_text}"
                    )
                    parsed_response["actions"] = [
                        {
                            "type": "GENERAL_MESSAGE",
                            "message": f"AI 'actions' field was malformed (not a list). Raw content: {raw_response_text}",
                        }
                    ]
                return parsed_response

            except json.JSONDecodeError:
                logger.warning(
                    f"AI response was not valid JSON. Raw response:\n{raw_response_text}"
                )
                return {
                    "explanation": "AI response was not in the expected JSON format. Displaying raw response.",
                    "actions": [
                        {"type": "GENERAL_MESSAGE", "message": raw_response_text}
                    ],
                }

        except Exception as e:
            logger.error(f"Error communicating with Gemini ({self.current_model_name}): {e}")
            err_str = str(e).lower()
            if (
                "api key not valid" in err_str
                or "api_key_invalid" in err_str
                or "permission_denied" in err_str
                and "api key" in err_str
            ):
                return {
                    "explanation": "Gemini API key is not valid or lacks permissions. Please check and re-enter.",
                    "actions": [],
                }
            if "resource_exhausted" in err_str or "quota" in err_str:
                return {
                    "explanation": "Gemini API quota exceeded. Please check your quota or try again later.",
                    "actions": [],
                }
            # Handle model specific errors, e.g., model not found or access denied
            if "model" in err_str and ("not found" in err_str or "access" in err_str or "permission" in err_str):
                return {
                    "explanation": f"Error with model '{self.current_model_name}': {str(e)}. It might be unavailable or you may not have access.",
                    "actions": [],
                }
            return {
                "explanation": f"An unexpected error occurred while interacting with the AI ({self.current_model_name}): {str(e)}",
                "actions": [],
            }
