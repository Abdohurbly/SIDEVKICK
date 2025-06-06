import axios, { AxiosError } from 'axios';
import {
  API_BASE_URL,
  AIProvider,
  AIModelId,
  ApiKeyConfigRequest,
  ApiKeyConfigResponse,
  ProjectLoadRequest,
  ProjectLoadResponse,
  ProjectStructureNode,
  FileContentResponse,
  SaveFileRequest,
  SaveFileResponse,
  ChatRequest,
  AIResponseData,
  AIAction,
  ApplyActionsRequest,
  ApplyActionResponse,
  ChatMessage,
  GitCommitRequest,
  GitCommandResponse,
  RAGSettings,
  RAGStatus,
  ReindexResponse,
  getProviderFromModelId,
} from '../types';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },

});

// Enhanced error handling interceptor
apiClient.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    let message = 'An unexpected error occurred';

    if (error.response?.data) {
      const errorData = error.response.data as any;
      message = errorData.detail || errorData.message || message;
    } else if (error.message) {
      message = error.message;
    }

    console.error('API Error:', {
      message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      url: error.config?.url,
      method: error.config?.method,
    });

    return Promise.reject(new Error(message));
  }
);

// API Key Configuration
export const configureApiKey = async (
  apiKey: string,
  modelId: AIModelId
): Promise<ApiKeyConfigResponse> => {
  const provider = getProviderFromModelId(modelId);

  const payload: ApiKeyConfigRequest = {
    api_key: apiKey,
    provider,
    initial_model_id: modelId,
  };

  const response = await apiClient.post<ApiKeyConfigResponse>('/config/api-key', payload);
  return response.data;
};

// Project Management
export const loadProject = async (projectPath: string): Promise<ProjectLoadResponse> => {
  const payload: ProjectLoadRequest = { project_path: projectPath };
  const response = await apiClient.post<ProjectLoadResponse>('/project/load', payload);
  return response.data;
};

export const getProjectStructure = async (): Promise<ProjectStructureNode> => {
  const response = await apiClient.get<ProjectStructureNode>('/project/structure');
  return response.data;
};

// File Operations
export const getFileContent = async (relativeFilePath: string): Promise<FileContentResponse> => {
  const response = await apiClient.get<FileContentResponse>('/file/content', {
    params: { relative_file_path: relativeFilePath }
  });
  return response.data;
};

// Specifically for fetching original content for diff views
export const getFileContentForDiff = async (relativePath: string): Promise<string> => {
  try {
    const response = await getFileContent(relativePath);
    return response.content;
  } catch (error: any) {
    console.warn(`Could not fetch content for diff of ${relativePath}:`, error.message);
    return `// Error fetching original content for ${relativePath}: ${error.message}`;
  }
};

export const saveFile = async (
  relativeFilePath: string,
  content: string
): Promise<SaveFileResponse> => {
  const payload: SaveFileRequest = {
    relative_file_path: relativeFilePath,
    content
  };
  const response = await apiClient.post<SaveFileResponse>('/file/save', payload);
  return response.data;
};

// Chat Operations
export const chatWithAI = async (
  userPrompt: string,
  currentOpenFileRelativePath?: string | null,
  modelId?: AIModelId,
  useRag?: boolean
): Promise<AIResponseData> => {
  const payload: ChatRequest = {
    user_prompt: userPrompt,
  };

  if (currentOpenFileRelativePath) {
    payload.current_open_file_relative_path = currentOpenFileRelativePath;
  }

  if (modelId) {
    payload.model_id = modelId;
  }

  if (useRag !== undefined) {
    payload.use_rag = useRag;
  }

  const response = await apiClient.post<AIResponseData>('/chat', payload);
  return response.data;
};

export const getChatHistory = async (): Promise<ChatMessage[]> => {
  const response = await apiClient.get<ChatMessage[]>('/chat/history');
  return response.data;
};

export const clearChatHistory = async (): Promise<{ message: string }> => {
  const response = await apiClient.delete<{ message: string }>('/chat/history');
  return response.data;
};

// Action Management
export const applyAIActions = async (actions: AIAction[]): Promise<ApplyActionResponse> => {
  const payload: ApplyActionsRequest = { actions };
  const response = await apiClient.post<ApplyActionResponse>('/actions/apply', payload);
  return response.data;
};

// RAG Management
export const getRagSettings = async (): Promise<RAGSettings> => {
  const response = await apiClient.get<RAGSettings>('/rag/settings');
  return response.data;
};

export const updateRagSettings = async (
  settings: RAGSettings
): Promise<{ message: string; settings: RAGSettings }> => {
  const response = await apiClient.post<{ message: string; settings: RAGSettings }>(
    '/rag/settings',
    settings
  );
  return response.data;
};

export const reindexProject = async (): Promise<ReindexResponse> => {
  const response = await apiClient.post<ReindexResponse>('/rag/reindex');
  return response.data;
};

export const getRagStatus = async (): Promise<RAGStatus> => {
  const response = await apiClient.get<RAGStatus>('/rag/status');
  return response.data;
};

// Git Operations
export const getGitStatus = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.get<GitCommandResponse>('/git/status');
  return response.data;
};

export const gitAddAll = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post<GitCommandResponse>('/git/add_all');
  return response.data;
};

export const gitCommit = async (message: string): Promise<GitCommandResponse> => {
  const payload: GitCommitRequest = { message };
  const response = await apiClient.post<GitCommandResponse>('/git/commit', payload);
  return response.data;
};

export const gitPush = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post<GitCommandResponse>('/git/push');
  return response.data;
};

export const gitGetCurrentBranch = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.get<GitCommandResponse>('/git/branch');
  return response.data;
};

export const gitPull = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post<GitCommandResponse>('/git/pull');
  return response.data;
};

// Helper functions for better error handling
export const isNetworkError = (error: unknown): boolean => {
  return error instanceof Error && (
    error.message.includes('Network Error') ||
    error.message.includes('timeout') ||
    error.message.includes('ECONNREFUSED')
  );
};

export const isAuthError = (error: unknown): boolean => {
  return error instanceof Error && (
    error.message.includes('401') ||
    error.message.includes('Unauthorized') ||
    error.message.includes('Invalid API key')
  );
};

export const isServerError = (error: unknown): boolean => {
  return error instanceof Error && (
    error.message.includes('500') ||
    error.message.includes('Internal Server Error') ||
    error.message.includes('503') ||
    error.message.includes('Service Unavailable')
  );
};

// Export the API base URL for external use
export { API_BASE_URL };

// Export apiClient for advanced usage if needed
export { apiClient };