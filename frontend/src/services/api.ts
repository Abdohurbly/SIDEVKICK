import axios from 'axios';
import {
  API_BASE_URL,
  ApiKeyConfigResponse,
  ProjectLoadResponse,
  ProjectStructureNode,
  FileContentResponse,
  SaveFileResponse,
  AIResponseData,
  AIAction,
  ApplyActionResponse,
  ChatMessage,
  GitCommitRequest,
  GitCommandResponse,
  AIModelId 
} from '../types';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    console.error('API Error:', message, error.response || error);
    return Promise.reject(new Error(message));
  }
);

export const configureApiKey = async (apiKey: string, initialModelId?: AIModelId): Promise<ApiKeyConfigResponse> => {
  const payload: { api_key: string; initial_model_id?: AIModelId } = { api_key: apiKey };
  if (initialModelId) {
    payload.initial_model_id = initialModelId;
  }
  const response = await apiClient.post('/config/api-key', payload);
  return response.data;
};

export const loadProject = async (projectPath: string): Promise<ProjectLoadResponse> => {
  const response = await apiClient.post('/project/load', { project_path: projectPath });
  return response.data;
};

export const getProjectStructure = async (): Promise<ProjectStructureNode> => {
  const response = await apiClient.get('/project/structure');
  return response.data;
};

export const getFileContent = async (relativeFilePath: string): Promise<FileContentResponse> => {
  const response = await apiClient.get('/file/content', { params: { relative_file_path: relativeFilePath } });
  return response.data;
};

export const saveFile = async (relativeFilePath: string, content: string): Promise<SaveFileResponse> => {
  const response = await apiClient.post('/file/save', { relative_file_path: relativeFilePath, content });
  return response.data;
};

export const chatWithAI = async (
  userPrompt: string,
  currentOpenFileRelativePath?: string | null,
  modelId?: AIModelId 
): Promise<AIResponseData> => {
  const payload: {
    user_prompt: string;
    current_open_file_relative_path?: string;
    model_id?: AIModelId; // Use AIModelId type
  } = { user_prompt: userPrompt };

  if (currentOpenFileRelativePath) {
    payload.current_open_file_relative_path = currentOpenFileRelativePath;
  }
  if (modelId) {
    payload.model_id = modelId;
  }

  const response = await apiClient.post('/chat', payload);
  return response.data;
};

export const applyAIActions = async (actions: AIAction[]): Promise<ApplyActionResponse> => {
  const response = await apiClient.post('/actions/apply', { actions });
  return response.data;
};

export const getChatHistory = async (): Promise<ChatMessage[]> => {
  const response = await apiClient.get('/chat/history');
  return response.data;
};

export const clearChatHistory = async (): Promise<{ message: string }> => {
  const response = await apiClient.delete('/chat/history');
  return response.data;
};

// Git API functions
export const getGitStatus = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.get('/git/status');
  return response.data;
};

export const gitAddAll = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post('/git/add_all');
  return response.data;
};

export const gitCommit = async (message: string): Promise<GitCommandResponse> => {
  const payload: GitCommitRequest = { message };
  const response = await apiClient.post('/git/commit', payload);
  return response.data;
};

export const gitPush = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post('/git/push');
  return response.data;
};

export const gitGetCurrentBranch = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.get('/git/branch');
  return response.data;
};

export const gitPull = async (): Promise<GitCommandResponse> => {
  const response = await apiClient.post('/git/pull');
  return response.data;
};

export { API_BASE_URL };
