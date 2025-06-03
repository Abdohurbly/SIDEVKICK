import React from "react";

interface ConfigPanelProps {
  apiKey: string;
  setApiKey: (key: string) => void;
  projectPath: string;
  setProjectPath: (path: string) => void;
  onConfigure: () => Promise<void>;
  onLoadProject: () => Promise<void>;
  isLoading: boolean;
  isApiConfigured: boolean;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({
  apiKey,
  setApiKey,
  projectPath,
  setProjectPath,
  onConfigure,
  onLoadProject,
  isLoading,
  isApiConfigured,
}) => {
  return (
    <div className="config-panel">
      <h2>Configuration</h2>
      <input
        type="password"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="Gemini API Key"
        disabled={isLoading}
        aria-label="Gemini API Key"
      />
      <button
        onClick={onConfigure}
        disabled={isLoading || !apiKey}
        aria-busy={isLoading && !!apiKey}
      >
        {isApiConfigured ? "API Key Set" : "Set API Key"}
      </button>

      <input
        type="text"
        value={projectPath}
        onChange={(e) => setProjectPath(e.target.value)}
        placeholder="/path/to/your/project"
        disabled={isLoading || !isApiConfigured} // Disable if API not configured
        aria-label="Project Path"
      />
      <button
        onClick={onLoadProject}
        disabled={isLoading || !projectPath || !isApiConfigured}
        aria-busy={isLoading && !!projectPath && isApiConfigured}
      >
        Load Project
      </button>
    </div>
  );
};

export default ConfigPanel;
