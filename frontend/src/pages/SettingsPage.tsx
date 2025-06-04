import React, { useState, useEffect, useMemo } from "react";
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
  Divider,
  Chip,
  Alert,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  Grid,
  Tooltip,
  IconButton,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";

import GitControls from "../components/GitControls";
import {
  AIModelId,
  AIModelInfo,
  AIProvider,
  availableAiModels,
  getModelsByProvider,
  getProviderFromModelId,
  RAGSettings,
  validateApiKey,
} from "../types";
import {
  getRagSettings,
  updateRagSettings,
  reindexProject,
  getRagStatus,
} from "../services/api";

interface SettingsPageProps {
  apiKey: string;
  setApiKey: (key: string) => void;
  projectPath: string;
  setProjectPath: (path: string) => void;
  onConfigure: () => Promise<void>;
  onLoadProject: () => Promise<void>;
  isLoading: boolean;
  isApiConfigured: boolean;
  isProjectLoaded: boolean;
  selectedAiModel: AIModelId;
  setSelectedAiModel: (modelId: AIModelId) => void;
  availableAiModels: AIModelInfo[];
  autoApplyAiSuggestions: boolean;
  setAutoApplyAiSuggestions: (enabled: boolean) => void;
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
  autoApplyAiSuggestions,
  setAutoApplyAiSuggestions,
  onClose,
}) => {
  const [ragSettings, setRagSettings] = useState<RAGSettings>({
    enabled: true,
  });
  const [ragStatus, setRagStatus] = useState<any>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const currentProvider = useMemo(
    () => getProviderFromModelId(selectedAiModel),
    [selectedAiModel]
  );
  const modelsByProvider = useMemo(() => {
    const grouped: Record<AIProvider, AIModelInfo[]> = {
      gemini: getModelsByProvider("gemini"),
      openai: getModelsByProvider("openai"),
      anthropic: getModelsByProvider("anthropic"),
    };
    return grouped;
  }, []);

  const selectedModelInfo = useMemo(
    () => availableAiModels.find((model) => model.id === selectedAiModel),
    [selectedAiModel]
  );

  useEffect(() => {
    if (isProjectLoaded) {
      loadRagSettings();
      loadRagStatus();
    }
  }, [isProjectLoaded]);

  useEffect(() => {
    const error = validateApiKey(apiKey, currentProvider);
    setValidationError(error);
  }, [apiKey, currentProvider]);

  const loadRagSettings = async () => {
    try {
      const settings = await getRagSettings();
      setRagSettings(settings);
    } catch (error) {
      console.warn("Failed to load RAG settings:", error);
    }
  };

  const loadRagStatus = async () => {
    try {
      const status = await getRagStatus();
      setRagStatus(status);
    } catch (error) {
      console.warn("Failed to load RAG status:", error);
    }
  };

  const handleModelChange = (event: SelectChangeEvent<AIModelId>) => {
    const newModel = event.target.value as AIModelId;
    setSelectedAiModel(newModel);
  };

  const handleRagToggle = async (enabled: boolean) => {
    try {
      const newSettings = { ...ragSettings, enabled };
      await updateRagSettings(newSettings);
      setRagSettings(newSettings);
    } catch (error) {
      console.error("Failed to update RAG settings:", error);
    }
  };

  const handleReindex = async () => {
    try {
      await reindexProject();
      await loadRagStatus();
    } catch (error) {
      console.error("Failed to reindex project:", error);
    }
  };

  const getProviderDisplayName = (provider: AIProvider): string => {
    switch (provider) {
      case "gemini":
        return "Google Gemini";
      case "openai":
        return "OpenAI";
      case "anthropic":
        return "Anthropic";
      default:
        return provider;
    }
  };

  const getApiKeyPlaceholder = (provider: AIProvider): string => {
    switch (provider) {
      case "gemini":
        return "Enter your Google AI Studio API key...";
      case "openai":
        return "Enter your OpenAI API key (sk-...)";
      case "anthropic":
        return "Enter your Anthropic API key (sk-ant-...)";
      default:
        return "Enter your API key...";
    }
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 }, mt: { xs: 2, sm: 4 } }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Settings
        </Typography>

        {/* API Configuration Section */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              API Configuration
              {isApiConfigured && (
                <Chip
                  label="Configured"
                  color="success"
                  size="small"
                  sx={{ ml: 2 }}
                />
              )}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ mb: 3 }}>
              <Alert severity="info" sx={{ mb: 2 }}>
                Current provider:{" "}
                <strong>{getProviderDisplayName(currentProvider)}</strong>
                {selectedModelInfo && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Selected model: {selectedModelInfo.name}
                    {selectedModelInfo.description &&
                      ` - ${selectedModelInfo.description}`}
                  </Typography>
                )}
              </Alert>

              <TextField
                fullWidth
                type="password"
                label={`${getProviderDisplayName(currentProvider)} API Key`}
                placeholder={getApiKeyPlaceholder(currentProvider)}
                variant="outlined"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={isLoading}
                error={!!validationError}
                helperText={
                  validationError ||
                  `This will be used for ${getProviderDisplayName(
                    currentProvider
                  )} requests`
                }
                sx={{ mb: 2 }}
              />

              <Button
                fullWidth
                variant="contained"
                color="primary"
                onClick={onConfigure}
                disabled={isLoading || !apiKey || !!validationError}
                sx={{ mb: 2 }}
              >
                {isApiConfigured ? "Update API Configuration" : "Configure API"}
              </Button>
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* AI Model Selection */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">AI Model Selection</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {Object.entries(modelsByProvider).map(([provider, models]) => (
                <Grid item xs={12} md={4} key={provider}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {getProviderDisplayName(provider as AIProvider)}
                      </Typography>
                      {models.map((model) => (
                        <Box
                          key={model.id}
                          sx={{
                            p: 1,
                            mb: 1,
                            border: selectedAiModel === model.id ? 2 : 1,
                            borderColor:
                              selectedAiModel === model.id
                                ? "primary.main"
                                : "divider",
                            borderRadius: 1,
                            cursor: "pointer",
                            "&:hover": { bgcolor: "action.hover" },
                          }}
                          onClick={() => setSelectedAiModel(model.id)}
                        >
                          <Typography variant="body2" fontWeight="medium">
                            {model.name}
                          </Typography>
                          {model.description && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                            >
                              {model.description}
                            </Typography>
                          )}
                          {model.pricing && (
                            <Typography
                              variant="caption"
                              display="block"
                              color="text.secondary"
                            >
                              ${model.pricing.input}/M input • $
                              {model.pricing.output}/M output
                            </Typography>
                          )}
                        </Box>
                      ))}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            <FormControl fullWidth sx={{ mt: 2 }} disabled={isLoading}>
              <InputLabel>Select AI Model</InputLabel>
              <Select
                value={selectedAiModel}
                label="Select AI Model"
                onChange={handleModelChange}
              >
                {Object.entries(modelsByProvider).map(([provider, models]) => [
                  <MenuItem key={`${provider}-header`} disabled>
                    <Typography variant="overline" color="primary">
                      {getProviderDisplayName(provider as AIProvider)}
                    </Typography>
                  </MenuItem>,
                  ...models.map((model) => (
                    <MenuItem key={model.id} value={model.id}>
                      <Box>
                        <Typography variant="body2">{model.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {model.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  )),
                ])}
              </Select>
            </FormControl>

            <Button
              fullWidth
              variant="outlined"
              color="primary"
              onClick={onConfigure}
              disabled={isLoading || !isApiConfigured}
              sx={{ mt: 2 }}
            >
              Apply Model Settings
            </Button>
          </AccordionDetails>
        </Accordion>

        {/* Project Configuration */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Project Configuration
              {isProjectLoaded && (
                <Chip
                  label="Loaded"
                  color="success"
                  size="small"
                  sx={{ ml: 2 }}
                />
              )}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              fullWidth
              label="Project Folder Path"
              variant="outlined"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              disabled={isLoading || !isApiConfigured}
              helperText={
                !isApiConfigured
                  ? "API Key must be configured first."
                  : "Absolute path to your project directory"
              }
              sx={{ mb: 2 }}
            />
            <Button
              fullWidth
              variant="contained"
              color="secondary"
              onClick={onLoadProject}
              disabled={isLoading || !projectPath || !isApiConfigured}
              sx={{ mb: 2 }}
            >
              Load Project
            </Button>
          </AccordionDetails>
        </Accordion>


        {/* General App Settings */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">General Preferences</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <FormControlLabel
              control={
                <Switch
                  checked={autoApplyAiSuggestions}
                  onChange={(e) => setAutoApplyAiSuggestions(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label="Automatically apply AI recommendations"
            />
            <Typography variant="caption" display="block" color="text.secondary" sx={{mt:0.5}}>
              When enabled, AI-suggested code changes will be applied directly without requiring manual confirmation from the suggestions panel.
            </Typography>
          </AccordionDetails>
        </Accordion>

        {/* RAG Settings */}
        {isProjectLoaded && (
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">
                RAG (Retrieval-Augmented Generation)
                <Tooltip title="RAG helps provide better context by indexing your codebase">
                  <IconButton size="small">
                    <InfoIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <FormControlLabel
                control={
                  <Switch
                    checked={ragSettings.enabled}
                    onChange={(e) => handleRagToggle(e.target.checked)}
                    disabled={isLoading}
                  />
                }
                label="Enable RAG for better context understanding"
              />

              {ragStatus && (
                <Alert
                  severity={ragStatus.indexed ? "success" : "warning"}
                  sx={{ mt: 2, mb: 2 }}
                >
                  <Typography variant="body2">
                    Status: {ragStatus.indexed ? "Indexed" : "Not indexed"}
                    {ragStatus.total_chunks > 0 &&
                      ` • ${ragStatus.total_chunks} chunks`}
                  </Typography>
                </Alert>
              )}

              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={handleReindex}
                disabled={isLoading}
                sx={{ mt: 1 }}
              >
                Reindex Project
              </Button>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Git Controls */}
        {isProjectLoaded && (
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Git Management</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <GitControls />
            </AccordionDetails>
          </Accordion>
        )}

        <Box sx={{ mt: 3, display: "flex", gap: 2 }}>
          <Button
            fullWidth
            variant="outlined"
            onClick={onClose}
            disabled={isLoading}
          >
            Back to App
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default SettingsPage;
