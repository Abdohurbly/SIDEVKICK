import React from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Container,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Divider
} from '@mui/material';
import GitControls from '../components/GitControls'; // Import GitControls
import { AIModelId, AIModelInfo } from '../types'; // Import AIModel types

interface SettingsPageProps {
  apiKey: string;
  setApiKey: (key: string) => void;
  projectPath: string;
  setProjectPath: (path: string) => void;
  onConfigure: () => Promise<void>; // This will now also set the preferred model
  onLoadProject: () => Promise<void>;
  isLoading: boolean;
  isApiConfigured: boolean;
  isProjectLoaded: boolean;
  selectedAiModel: AIModelId;
  setSelectedAiModel: (modelId: AIModelId) => void;
  availableAiModels: AIModelInfo[];
  onClose: () => void;
}

const SettingsPage: React.FC<SettingsPageProps> = ({
  apiKey,
  setApiKey,
  projectPath,
  setProjectPath,
  onConfigure,
  onLoadProject,
  isLoading,
  isApiConfigured,
  isProjectLoaded,
  selectedAiModel,
  setSelectedAiModel,
  availableAiModels,
  onClose,
}) => {
  const handleModelChange = (event: SelectChangeEvent<AIModelId>) => {
    setSelectedAiModel(event.target.value as AIModelId);
  };

  return (
    <Container maxWidth="sm">
      <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 }, mt: { xs: 2, sm: 4 } }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Settings
        </Typography>

        <Box component="form" noValidate autoComplete="off" sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>API Configuration</Typography>
          <TextField
            fullWidth
            type="password"
            label="Gemini API Key (or other provider's key)"
            variant="outlined"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={isLoading}
            sx={{ mb: 2 }}
          />
          <Button
            fullWidth
            variant="contained"
            color="primary"
            onClick={onConfigure} // This button now also considers the selected model
            disabled={isLoading || !apiKey}
            sx={{ mb: 3 }}
          >
            {isApiConfigured ? 'Update API Key / Apply Settings' : 'Set API Key & Settings'}
          </Button>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>AI Model Selection</Typography>
          <FormControl fullWidth sx={{ mb: 1 }} disabled={isLoading || availableAiModels.length === 0}>
            <InputLabel id="ai-model-select-label">AI Model</InputLabel>
            <Select
              labelId="ai-model-select-label"
              id="ai-model-select"
              value={selectedAiModel}
              label="AI Model"
              onChange={handleModelChange}
            >
              {availableAiModels.map((model) => (
                <MenuItem key={model.id} value={model.id}>
                  {model.name} ({model.provider})
                </MenuItem>
              ))}
            </Select>
            {availableAiModels.length === 0 && <Typography variant="caption" color="error">No AI models available.</Typography>}
          </FormControl>
          <Button
            fullWidth
            variant="outlined"
            color="primary"
            onClick={onConfigure} // Re-uses onConfigure to apply model with current API key
            disabled={isLoading || !isApiConfigured} // Enabled if API key is already set
            sx={{ mb: 3 }}
          >
            Apply Model Preference
          </Button>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>Project Configuration</Typography>
          <TextField
            fullWidth
            label="Project Folder Path"
            variant="outlined"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            disabled={isLoading || !isApiConfigured}
            helperText={!isApiConfigured ? "API Key must be set first." : ""}
            sx={{ mb: 2 }}
          />
          <Button
            fullWidth
            variant="contained"
            color="secondary"
            onClick={onLoadProject}
            disabled={isLoading || !projectPath || !isApiConfigured}
            sx={{ mb: 3 }}
          >
            Load Project
          </Button>
        </Box>

        {isProjectLoaded && ( // Conditionally render GitControls
          <Box sx={{ mt: 3, mb: 3 }}>
            <Divider sx={{ mb: 3 }} />
            <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>Git Management</Typography>
            <GitControls />
          </Box>
        )}

        <Button fullWidth variant="outlined" onClick={onClose} disabled={isLoading} sx={{ mt: 2 }}>
          Back to App
        </Button>
      </Paper>
    </Container>
  );
};

export default SettingsPage;
