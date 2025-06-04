import { PaletteMode } from '@mui/material';

export const API_BASE_URL = '/api'; // Proxied by Vite dev server

export type Theme = PaletteMode;

// AI Provider Types
export type AIProvider = 'gemini' | 'openai' | 'anthropic';

// AI Model Types
export type AIModelId =
  // Gemini Models
  | 'gemini-2.0-flash-exp'
  | 'gemini-1.5-pro'
  | 'gemini-1.5-flash'
  | 'gemini-1.5-flash-8b'
  | 'gemini-2.5-pro-preview-05-06'
  | 'gemini-2.5-flash-preview-05-20'
  | 'gemini-2.5-flash-preview-native-audio-dialog'
  // OpenAI Models
  | 'gpt-4o'
  | 'gpt-4o-mini'
  | 'gpt-4-turbo'
  | 'gpt-3.5-turbo'
  // Anthropic Models
  | 'claude-3.5-sonnet'
  | 'claude-3-opus'
  | 'claude-3-haiku';

export interface AIModelInfo {
  id: AIModelId;
  name: string;
  provider: AIProvider;
  description?: string;
  contextWindow?: number;
  pricing?: {
    input: number;  // per 1M tokens
    output: number; // per 1M tokens
  };
}

export const availableAiModels: AIModelInfo[] = [
  // Gemini Models
  {
    id: 'gemini-2.0-flash-exp',
    name: 'Gemini 2.0 Flash (Experimental)',
    provider: 'gemini',
    description: 'Latest experimental Gemini model with enhanced capabilities',
    contextWindow: 1000000,
    pricing: { input: 0.075, output: 0.30 }
  },
  {
    id: 'gemini-1.5-pro',
    name: 'Gemini 1.5 Pro',
    provider: 'gemini',
    description: 'Most capable Gemini model for complex reasoning',
    contextWindow: 2000000,
    pricing: { input: 1.25, output: 5.00 }
  },
  {
    id: 'gemini-1.5-flash',
    name: 'Gemini 1.5 Flash',
    provider: 'gemini',
    description: 'Fast and efficient for most tasks',
    contextWindow: 1000000,
    pricing: { input: 0.075, output: 0.30 }
  },
  {
    id: 'gemini-1.5-flash-8b',
    name: 'Gemini 1.5 Flash 8B',
    provider: 'gemini',
    description: 'Smaller, faster model for simple tasks',
    contextWindow: 1000000,
    pricing: { input: 0.0375, output: 0.15 }
  },
  {
    id: 'gemini-2.5-pro-preview-05-06',
    name: 'Gemini 2.5 Pro (05-06)',
    provider: 'gemini',
    description: 'Preview version with advanced capabilities',
    contextWindow: 2000000
  },
  {
    id: 'gemini-2.5-flash-preview-05-20',
    name: 'Gemini 2.5 Flash (05-20)',
    provider: 'gemini',
    description: 'Preview version optimized for speed',
    contextWindow: 1000000
  },
  {
    id: 'gemini-2.5-flash-preview-native-audio-dialog',
    name: 'Gemini 2.5 Flash (Native Audio/Dialog)',
    provider: 'gemini',
    description: 'Preview with native audio and dialog support',
    contextWindow: 1000000
  },
  // OpenAI Models
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most advanced OpenAI model with multimodal capabilities',
    contextWindow: 128000,
    pricing: { input: 2.50, output: 10.00 }
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Affordable and intelligent small model',
    contextWindow: 128000,
    pricing: { input: 0.15, output: 0.60 }
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    provider: 'openai',
    description: 'Previous generation flagship model',
    contextWindow: 128000,
    pricing: { input: 10.00, output: 30.00 }
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'openai',
    description: 'Fast and cost-effective for simple tasks',
    contextWindow: 16385,
    pricing: { input: 0.50, output: 1.50 }
  },
  // Anthropic Models
  {
    id: 'claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'anthropic',
    description: 'Most intelligent Claude model for complex tasks',
    contextWindow: 200000,
    pricing: { input: 3.00, output: 15.00 }
  },
  {
    id: 'claude-3-opus',
    name: 'Claude 3 Opus',
    provider: 'anthropic',
    description: 'Powerful model for highly complex tasks',
    contextWindow: 200000,
    pricing: { input: 15.00, output: 75.00 }
  },
  {
    id: 'claude-3-haiku',
    name: 'Claude 3 Haiku',
    provider: 'anthropic',
    description: 'Fastest and most compact model',
    contextWindow: 200000,
    pricing: { input: 0.25, output: 1.25 }
  }
];

export const DEFAULT_AI_MODEL_ID: AIModelId = 'gemini-1.5-flash';

// Helper functions
export const getModelsByProvider = (provider: AIProvider): AIModelInfo[] => {
  return availableAiModels.filter(model => model.provider === provider);
};

export const getModelInfo = (modelId: AIModelId): AIModelInfo | undefined => {
  return availableAiModels.find(model => model.id === modelId);
};

export const getProviderFromModelId = (modelId: AIModelId): AIProvider => {
  const model = getModelInfo(modelId);
  return model?.provider || 'gemini';
};

export const getProviderDisplayName = (provider: AIProvider): string => {
  switch (provider) {
    case 'gemini': return 'Google Gemini';
    case 'openai': return 'OpenAI';
    case 'anthropic': return 'Anthropic';
    default: return provider;
  }
};

// Validation helpers
export const validateApiKey = (apiKey: string, provider: AIProvider): string | null => {
  if (!apiKey.trim()) {
    return 'API key is required';
  }

  switch (provider) {
    case 'openai':
      if (!apiKey.startsWith('sk-')) {
        return 'OpenAI API key should start with "sk-"';
      }
      break;
    case 'anthropic':
      if (!apiKey.startsWith('sk-ant-')) {
        return 'Anthropic API key should start with "sk-ant-"';
      }
      break;
    case 'gemini':
      if (apiKey.length < 20) {
        return 'Gemini API key appears to be too short';
      }
      break;
  }

  return null;
};

// API Configuration Types
export interface APIConfiguration {
  provider: AIProvider;
  apiKey: string;
  selectedModel: AIModelId;
}

// API Response Types
export interface ApiKeyConfigRequest {
  api_key: string;
  provider: AIProvider;
  initial_model_id?: AIModelId;
}

export interface ApiKeyConfigResponse {
  message: string;
}

export interface ProjectLoadRequest {
  project_path: string;
}

export interface ProjectLoadResponse {
  message: string;
  project_path: string;
}

export interface ProjectStructureNode {
  name: string;
  path: string;
  relative_path: string;
  type: 'file' | 'directory';
  children?: ProjectStructureNode[];
}

export interface FileContentRequest {
  relative_file_path: string;
}

export interface FileContentResponse {
  relative_file_path: string;
  content: string;
}

export interface SaveFileRequest {
  relative_file_path: string;
  content: string;
}

export interface SaveFileResponse {
  message: string;
}

// Chat Types
export interface ChatRequest {
  user_prompt: string;
  current_open_file_relative_path?: string;
  model_id?: AIModelId;
  use_rag?: boolean;
}

export interface AIAction {
  type: string;
  file_path?: string;
  content?: string;
  folder_path?: string;
  command?: string;
  description?: string;
  message?: string;
  changes?: PartialEditChange[]; // New field for partial edits
}

export interface PartialEditChange {
  operation: 'replace' | 'insert' | 'delete';
  start_line?: number;
  end_line?: number;
  line?: number;
  content?: string;
}


export interface AIResponseData {
  explanation: string;
  actions: AIAction[];
  context_info?: {
    method: string;
    chunks_used: number;
    estimated_tokens: number;
  };
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string | AIResponseData;
}

export interface CommandOutput {
  stdout?: string;
  stderr?: string;
  returncode: number;
  command: string;
}

export interface ApplyActionDetail {
  type: string;
  path_info?: string;
  command?: string;
  status: 'success' | 'error' | 'skipped';
  detail?: string;
  output?: CommandOutput;
}

export interface ApplyActionsRequest {
  actions: AIAction[];
}

export interface ApplyActionResponse {
  results: ApplyActionDetail[];
}

// Git Types
export interface GitCommitRequest {
  message: string;
}

export type GitCommandResponse = CommandOutput;

// RAG Types
export interface RAGSettings {
  enabled: boolean;
  max_tokens?: number;
}

export interface RAGStatus {
  indexed: boolean;
  total_chunks: number;
  cache_exists: boolean;
  error?: string;
}

export interface ReindexResponse {
  message: string;
  chunks_indexed: number;
}

// UI Types
export type ViewMode = 'editor' | 'preview';
export type PreviewDevice = 'desktop' | 'tablet' | 'mobile';

// Storage helpers
export const STORAGE_KEYS = {
  THEME: 'app_theme',
  SELECTED_MODEL: 'selected_ai_model',
  API_CONFIGS: 'api_configurations',
  PROJECT_PATH: 'project_path',
  PREVIEW_URL: 'preview_url',
  AUTO_SAVE: 'auto_save_enabled',
  RAG_ENABLED: 'rag_enabled',
} as const;

// App Settings
export interface AppSettings {
  theme: Theme;
  selectedModel: AIModelId;
  apiConfigurations: Partial<Record<AIProvider, { apiKey: string; lastUsedModel: AIModelId }>>;
  projectPath: string;
  previewUrl: string;
  autoSave: boolean;
  ragEnabled: boolean;
}