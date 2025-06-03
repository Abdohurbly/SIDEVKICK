import { PaletteMode } from '@mui/material'; // Import PaletteMode

export const API_BASE_URL = '/api'; // Proxied by Vite dev server

export type Theme = PaletteMode; // Use MUI's PaletteMode for theme type

// AI Model Types
export type AIModelId =
  | 'gemini-2.5-pro-preview-05-06'
  | 'gemini-2.5-flash-preview-05-20'
  | 'gemini-2.5-flash-preview-native-audio-dialog';

export interface AIModelInfo {
  id: AIModelId;
  name: string;
  provider: string;
}

export const availableAiModels: AIModelInfo[] = [
  { id: 'gemini-2.5-pro-preview-05-06', name: 'Gemini 2.5 Pro (05-06)', provider: 'Google' },
  { id: 'gemini-2.5-flash-preview-05-20', name: 'Gemini 2.5 Flash (05-20)', provider: 'Google' },
  { id: 'gemini-2.5-flash-preview-native-audio-dialog', name: 'Gemini 2.5 Flash (Native Audio/Dialog)', provider: 'Google' },
];

export const DEFAULT_AI_MODEL_ID: AIModelId = 'gemini-2.5-pro-preview-05-06';

export interface ApiKeyConfigResponse {
  message: string;
}

export interface ProjectLoadResponse {
  message: string;
  project_path: string;
}

export interface ProjectStructureNode {
  name: string; // Absolute path on server, for reference
  path: string;
  relative_path: string; // Relative path, used for client-side display and API calls
  type: 'file' | 'directory';
  children?: ProjectStructureNode[];
}

export interface FileContentResponse {
  relative_file_path: string;
  content: string;
}

export interface SaveFileResponse {
  message: string;
}

// Matches backend_api.py AIAction Pydantic model
export interface AIAction {
  type: string;
  file_path?: string;
  content?: string;
  folder_path?: string;
  command?: string;
  description?: string;
  message?: string; // Added as it was in the original type, though might be for GENERAL_MESSAGE only
}

// Matches backend_api.py AIResponse Pydantic model
export interface AIResponseData {
  explanation: string;
  actions: AIAction[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string | AIResponseData; // AI responses can be complex objects
}

export interface CommandOutput {
  stdout?: string;
  stderr?: string;
  returncode: number;
  command: string;
}

export interface ApplyActionDetail {
  type: string;
  path_info?: string; // file_path, folder_path, or command
  command?: string;
  status: 'success' | 'error' | 'skipped';
  detail?: string;
  output?: CommandOutput;
}

export interface ApplyActionResponse {
  results: ApplyActionDetail[];
}

// Git specific types
export interface GitCommitRequest {
  message: string;
}

// GitCommandResponse can reuse CommandOutput as the backend returns this structure
export type GitCommandResponse = CommandOutput;

// New types for Editor/Preview toggle and device view
export type ViewMode = 'editor' | 'preview';
export type PreviewDevice = 'desktop' | 'tablet' | 'mobile';
