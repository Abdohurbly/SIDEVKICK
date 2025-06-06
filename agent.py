import sys
import subprocess
import os
import google.generativeai as genai
import anthropic
import json
import logging

try:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "openai"], capture_output=True, text=True
    )
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                sys.path.insert(0, location)
                break
except:
    pass

import openai


# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model names. These can be overridden during agent initialization or by set_model.
DEFAULT_GEMINI_MODEL_NAME = "gemini-1.5-pro-latest"
DEFAULT_OPENAI_MODEL_NAME = "gpt-4-turbo-preview"
DEFAULT_ANTHROPIC_MODEL_NAME = "claude-3-opus-20240229"

SYSTEM_PROMPT = """
You are a Local AI Developer Agent assisting with code editing, refactoring, file generation, and code documentation.

You receive:
1. User's request
2. Project file structure (relative paths)
3. Current open file (if any)
4. Context: Either ALL files (traditional) or RELEVANT chunks (RAG)
5. Chat history

CONTEXT TYPES:
- RAG: Targeted chunks with metadata (chunk type, functions, classes, line numbers)
- Traditional: Complete or truncated file contents
- Files marked [FULL FILE - Ready for editing] can be edited
- Files marked [PARTIAL CONTEXT - Read-only] require user to open them first

When responding, output ONLY valid JSON (no markdown, no ```json markers):

{
  "explanation": "Clear explanation of what you did or found (REQUIRED)",
  "actions": [
    // Action objects here
  ]
}

🔴 CRITICAL: Each action type has EXACT required fields. Missing or wrong fields = failure.

=== ACTION TYPES ===

1. EDIT_FILE_CONTEXTUAL (Preferred - works with pattern matching):
   Always requires "operation" field! Choose based on what you need:

   REPLACE - Find and replace text:
   {
     "type": "EDIT_FILE_CONTEXTUAL",
     "file_path": "relative/path/to/file",
     "operation": "replace",
     "target_content": "exact text to find",
     "replacement_content": "new text",
     "before_context": "optional: unique text before target",
     "after_context": "optional: unique text after target",
     "description": "what this does"
   }

   INSERT_BEFORE - Add text before anchor:
   {
     "type": "EDIT_FILE_CONTEXTUAL",
     "file_path": "relative/path/to/file",
     "operation": "insert_before",
     "anchor_content": "exact text to insert before",
     "content": "text to insert",
     "description": "what this does"
   }

   INSERT_AFTER - Add text after anchor:
   {
     "type": "EDIT_FILE_CONTEXTUAL",
     "file_path": "relative/path/to/file",
     "operation": "insert_after",
     "anchor_content": "exact text to insert after",
     "content": "text to insert",
     "description": "what this does"
   }

   DELETE - Remove text:
   {
     "type": "EDIT_FILE_CONTEXTUAL",
     "file_path": "relative/path/to/file",
     "operation": "delete",
     "target_content": "exact text to delete",
     "before_context": "optional: unique text before",
     "after_context": "optional: unique text after",
     "description": "what this does"
   }

2. EDIT_FILE_CONTEXTUAL_BATCH (Multiple edits to same file):
   {
     "type": "EDIT_FILE_CONTEXTUAL_BATCH",
     "file_path": "relative/path/to/file",
     "changes": [
       {
         "operation": "replace",
         "target_content": "find this",
         "replacement_content": "replace with this",
         "description": "change 1"
       },
       {
         "operation": "insert_after",
         "anchor_content": "after this",
         "content": "insert this",
         "description": "change 2"
       }
     ],
     "description": "overall batch description"
   }

3. EDIT_FILE_COMPLETE (Replace entire file - use only for small files):
   {
     "type": "EDIT_FILE_COMPLETE",
     "file_path": "relative/path/to/file",
     "content": "entire new file content",
     "description": "what changed"
   }

4. CREATE_FILE:
   {
     "type": "CREATE_FILE",
     "file_path": "relative/path/to/newfile.ext",
     "content": "file content",
     "description": "what this file does"
   }

5. CREATE_FOLDER:
   {
     "type": "CREATE_FOLDER",
     "folder_path": "relative/path/to/folder",
     "description": "folder purpose"
   }

6. EXECUTE_SHELL_COMMAND:
   {
     "type": "EXECUTE_SHELL_COMMAND",
     "command": "command to run",
     "description": "what this does"
   }

7. GENERAL_MESSAGE (Info only, no action):
   {
     "type": "GENERAL_MESSAGE",
     "message": "informational message",
     "description": "brief description"
   }

=== CONTEXTUAL EDITING RULES ===

1. ALWAYS include "operation" field for EDIT_FILE_CONTEXTUAL
2. Use EXACT text matches - copy/paste from the file
3. Include enough context to make matches unique
4. Preserve original formatting (indentation, line breaks)
5. For ambiguous matches, use before_context/after_context
6. When adding to structures (switch/if/class/etc), find unique anchors

=== COMMON PATTERNS ===

Adding to a switch/match statement:
- Find unique anchor (like "default:" or closing brace)
- Use insert_before with proper indentation

Adding to a list/array:
- Find last item or closing bracket
- Use insert_before or insert_after

Adding to a class/struct:
- Find closing brace or last member
- Use insert_before with proper formatting

=== BEST PRACTICES ===

- Prefer EDIT_FILE_CONTEXTUAL - it's more reliable than line numbers
- Use EDIT_FILE_COMPLETE only for files <50 lines or complete rewrites
- Break complex changes into multiple operations
- Always verify target_content exists exactly as shown
- Include proper indentation in content/replacement_content
- Make descriptions clear and actionable
- Create folders before creating files inside them
- For UI changes, consider all related files (components, styles, etc.)

=== VALIDATION CHECKLIST ===

Before responding, verify:
✓ Valid JSON syntax (no trailing commas)
✓ Correct action type names (exact spelling)
✓ All required fields present for each action type
✓ "operation" field included for all EDIT_FILE_CONTEXTUAL
✓ No mixed fields from different action types
✓ File paths are relative to project root
✓ Descriptions explain the change clearly
"""


class GeminiAgent:
    def __init__(
        self, api_key: str, initial_model_name: str = DEFAULT_GEMINI_MODEL_NAME
    ):
        self.api_key = api_key
        self.current_model_name = initial_model_name
        self.model = None
        self._initialized_successfully = False
        self._configure_model()

    def _configure_model(self):
        try:
            genai.configure(api_key=self.api_key)
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7,
            )
            self.model = genai.GenerativeModel(
                self.current_model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config=generation_config,
            )
            self._initialized_successfully = True
            logger.info(
                f"Gemini Agent configured successfully with model: {self.current_model_name}."
            )
        except Exception as e:
            logger.error(
                f"Failed to configure Gemini with model {self.current_model_name}: {e}"
            )
            self._initialized_successfully = False
            self.model = None

    def set_model(self, new_model_name: str) -> bool:
        if new_model_name == self.current_model_name and self.is_ready():
            logger.info(f"Model {new_model_name} is already set and ready.")
            return True

        logger.info(f"Attempting to set Gemini model to: {new_model_name}")
        self.current_model_name = new_model_name
        self._configure_model()
        if self.is_ready():
            logger.info(f"Successfully set Gemini model to: {new_model_name}")
        else:
            logger.error(f"Failed to set Gemini model to: {new_model_name}")
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

        # Add context method information
        context_method = project_context.get("context_method", "Unknown")
        context_parts.append(f"Context Method: {context_method}")

        # Add RAG metadata if available
        if "rag_metadata" in project_context:
            rag_info = project_context["rag_metadata"]
            context_parts.append(
                f"RAG Info: {rag_info.get('total_chunks', 0)} relevant chunks, ~{rag_info.get('estimated_tokens', 0)} tokens"
            )

        context_parts.append("\nProject File Structure (relative paths):")
        if project_context.get("file_paths"):
            for p_path in project_context["file_paths"]:
                context_parts.append(f"- {p_path}")
        else:
            context_parts.append("No files in project or project not loaded.")
        context_parts.append("\n")
        if project_context.get("editing_recommendation"):
            context_parts.append(
                f"EDITING RECOMMENDATION: {project_context['editing_recommendation']}"
            )

        if project_context.get("large_files"):
            context_parts.append(
                f"LARGE FILES (consider EDIT_FILE_PARTIAL): {', '.join(project_context['large_files'])}"
            )

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

        # Enhanced context display for RAG vs Traditional
        if context_method == "RAG" or "RAG" in context_method:
            context_parts.append(
                "RELEVANT CODE CONTEXT (Selected via RAG - Most relevant to your query):"
            )
        else:
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
            logger.error(
                f"Error communicating with Gemini ({self.current_model_name}): {e}"
            )
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
            if "model" in err_str and (
                "not found" in err_str or "access" in err_str or "permission" in err_str
            ):
                return {
                    "explanation": f"Error with model '{self.current_model_name}': {str(e)}. It might be unavailable or you may not have access.",
                    "actions": [],
                }
            return {
                "explanation": f"An unexpected error occurred while interacting with the AI ({self.current_model_name}): {str(e)}",
                "actions": [],
            }


# OpenAI and Anthropic classes remain the same as your original implementation
class OpenAIAgent:
    def __init__(
        self, api_key: str, initial_model_name: str = DEFAULT_OPENAI_MODEL_NAME
    ):
        self.api_key = api_key
        self.current_model_name = initial_model_name
        self.client = None
        self._initialized_successfully = False
        self._configure_model()

    def _configure_model(self):
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key is missing.")
            self.client = openai.OpenAI(api_key=self.api_key)
            self._initialized_successfully = True
            logger.info(
                f"OpenAI Agent configured successfully with model: {self.current_model_name}."
            )
        except Exception as e:
            logger.error(
                f"Failed to configure OpenAI with model {self.current_model_name}: {e}"
            )
            self._initialized_successfully = False
            self.client = None
        ai = 0

    def set_model(self, new_model_name: str) -> bool:
        if new_model_name == self.current_model_name and self.is_ready():
            logger.info(f"OpenAI Model {new_model_name} is already set and ready.")
            return True

        logger.info(f"Attempting to set OpenAI model to: {new_model_name}")
        self.current_model_name = new_model_name
        if not self.client:
            self._configure_model()

        if self.is_ready():
            logger.info(f"Successfully set OpenAI model to: {new_model_name}")
        else:
            logger.error(
                f"OpenAI client not ready after attempting to set model to: {new_model_name}"
            )
        return self.is_ready()

    def get_current_model_name(self) -> str:
        return self.current_model_name

    def is_ready(self) -> bool:
        return self.client is not None and self._initialized_successfully

    def get_ai_response(
        self, user_prompt: str, project_context: dict, chat_history: list
    ) -> dict:
        if not self.is_ready():
            return {
                "explanation": f"OpenAI model ({self.current_model_name}) not initialized. Please check API key and configuration.",
                "actions": [],
            }

        logger.warning("OpenAI get_ai_response is not fully implemented yet.")
        return {
            "explanation": f"OpenAI integration for model {self.current_model_name} is a stub. Full response generation not implemented.",
            "actions": [
                {
                    "type": "GENERAL_MESSAGE",
                    "message": "OpenAI response generation is a stub.",
                }
            ],
        }


class AnthropicAgent:
    def __init__(
        self, api_key: str, initial_model_name: str = DEFAULT_ANTHROPIC_MODEL_NAME
    ):
        self.api_key = api_key
        self.current_model_name = initial_model_name
        self.client = None
        self._initialized_successfully = False
        self._configure_model()

    def _configure_model(self):
        try:
            if not self.api_key:
                raise ValueError("Anthropic API key is missing.")
            # Initialize without any extra parameters that might be causing issues
            self.client = anthropic.Anthropic(api_key=self.api_key)

            self._initialized_successfully = True
            logger.info(
                f"Anthropic Agent configured successfully with model: {self.current_model_name}."
            )
        except Exception as e:
            logger.error(
                f"Failed to configure Anthropic with model {self.current_model_name}: {e}"
            )
            self._initialized_successfully = False
            self.client = None

    def set_model(self, new_model_name: str) -> bool:
        if new_model_name == self.current_model_name and self.is_ready():
            logger.info(f"Anthropic Model {new_model_name} is already set and ready.")
            return True

        logger.info(f"Attempting to set Anthropic model to: {new_model_name}")
        self.current_model_name = new_model_name
        if not self.client:
            self._configure_model()

        if self.is_ready():
            logger.info(f"Successfully set Anthropic model to: {new_model_name}")
        else:
            logger.error(
                f"Anthropic client not ready after attempting to set model to: {new_model_name}"
            )
        return self.is_ready()

    def get_current_model_name(self) -> str:
        return self.current_model_name

    def is_ready(self) -> bool:
        return self.client is not None and self._initialized_successfully

    def get_ai_response(
        self, user_prompt: str, project_context: dict, chat_history: list
    ) -> dict:
        if not self.is_ready():
            return {
                "explanation": f"Anthropic model ({self.current_model_name}) not initialized. Please check API key and configuration.",
                "actions": [],
            }

        # Build context
        context_parts = [f"User Request: {user_prompt}\n"]

        # Add context method information
        context_method = project_context.get("context_method", "Unknown")
        context_parts.append(f"Context Method: {context_method}")

        # Add RAG metadata if available
        if "rag_metadata" in project_context:
            rag_info = project_context["rag_metadata"]
            context_parts.append(
                f"RAG Info: {rag_info.get('total_chunks', 0)} relevant chunks, ~{rag_info.get('estimated_tokens', 0)} tokens"
            )

        context_parts.append("\nProject File Structure (relative paths):")
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

        # Enhanced context display for RAG vs Traditional
        if context_method == "RAG" or "RAG" in context_method:
            context_parts.append(
                "RELEVANT CODE CONTEXT (Selected via RAG - Most relevant to your query):"
            )
        else:
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

        full_user_content = "\n".join(context_parts)

        # Build messages for Anthropic
        messages = []

        # Add chat history
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "assistant"
            content = msg["content"]

            if isinstance(content, dict):
                # Previous AI response - convert to string
                content = json.dumps(content)

            messages.append({"role": role, "content": content})

        # Add current request
        messages.append({"role": "user", "content": full_user_content})

        try:
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.current_model_name,
                max_tokens=8000,
                temperature=0.7,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            raw_response_text = response.content[0].text.strip()

            # Clean up response if wrapped in code blocks
            if raw_response_text.startswith("```json"):
                raw_response_text = raw_response_text[7:]
                if raw_response_text.endswith("```"):
                    raw_response_text = raw_response_text[:-3]
                raw_response_text = raw_response_text.strip()
            elif raw_response_text.startswith("```") and raw_response_text.endswith(
                "```"
            ):
                raw_response_text = raw_response_text[3:-3].strip()

            # Parse JSON response
            try:
                parsed_response = json.loads(raw_response_text)

                if not isinstance(parsed_response, dict):
                    logger.warning(f"AI response was valid JSON but not a dictionary.")
                    return {
                        "explanation": "AI response format error: Expected a JSON object.",
                        "actions": [
                            {"type": "GENERAL_MESSAGE", "message": raw_response_text}
                        ],
                    }

                if (
                    "explanation" not in parsed_response
                    or "actions" not in parsed_response
                ):
                    logger.warning(
                        "AI response JSON was valid but missed 'explanation' or 'actions'."
                    )
                    return {
                        "explanation": "AI response JSON structure error: Missing required fields.",
                        "actions": [
                            {"type": "GENERAL_MESSAGE", "message": raw_response_text}
                        ],
                    }

                if not isinstance(parsed_response.get("actions"), list):
                    parsed_response["actions"] = []

                return parsed_response

            except json.JSONDecodeError:
                logger.warning(f"AI response was not valid JSON: {raw_response_text}")
                return {
                    "explanation": "AI response was not in the expected JSON format.",
                    "actions": [
                        {"type": "GENERAL_MESSAGE", "message": raw_response_text}
                    ],
                }

        except Exception as e:
            logger.error(f"Error communicating with Anthropic: {e}")
            err_str = str(e).lower()

            if "api" in err_str and "key" in err_str:
                return {
                    "explanation": "Anthropic API key is not valid. Please check and re-enter.",
                    "actions": [],
                }
            elif "rate" in err_str and "limit" in err_str:
                return {
                    "explanation": "Rate limit exceeded. Please wait a moment and try again.",
                    "actions": [],
                }
            elif "model" in err_str:
                return {
                    "explanation": f"Error with model '{self.current_model_name}'. It might not be available.",
                    "actions": [],
                }
            else:
                return {
                    "explanation": f"Error communicating with Anthropic: {str(e)}",
                    "actions": [],
                }
