import React, { useState, useEffect, useCallback, useMemo } from "react";
import "./App.css";
import {
  configureApiKey,
  loadProject,
  getProjectStructure,
  getFileContent,
  saveFile,
  chatWithAI,
  applyAIActions,
  getChatHistory,
  clearChatHistory,
  getRagSettings,
  updateRagSettings,
  reindexProject,
  getRagStatus,
} from "./services/api";
import {
  ProjectStructureNode,
  ChatMessage,
  AIResponseData,
  ApplyActionDetail,
  Theme as AppThemeType,
  AIModelId,
  availableAiModels,
  DEFAULT_AI_MODEL_ID,
  ViewMode,
  PreviewDevice,
  RAGSettings,
  RAGStatus,
  AIAction,
} from "./types";

// MUI Imports
import {
  ThemeProvider,
  CssBaseline,
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  Container,
  CircularProgress,
  Alert as MuiAlert,
  Button as MuiButton,
  PaletteMode,
  Snackbar,
  Modal,
  ToggleButtonGroup,
  ToggleButton,
  Menu,
  MenuItem,
  Chip,
  Tooltip,
  LinearProgress,
  Paper,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import SettingsIcon from "@mui/icons-material/Settings";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import EditIcon from "@mui/icons-material/Edit";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import InfoIcon from "@mui/icons-material/Info";
// import StorageIcon from "@mui/icons-material/Storage"; // Not directly used, but kept
import VisibilityIcon from "@mui/icons-material/Visibility"; // For Preview toggle

import { getAppTheme } from "./theme";

import FileExplorer from "./components/FileExplorer";
import EditorPanel from "./components/EditorPanel";
import PreviewPanel from "./components/PreviewPanel";
import ChatPanel from "./components/ChatPanel";
import AISuggestionsPanel from "./components/AISuggestionsPanel";
import SettingsPage from "./pages/SettingsPage";

const drawerWidth = 280;

const modalStyle = {
  position: "absolute" as "absolute",
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%)",
  width: "clamp(300px, 80vw, 700px)",
  bgcolor: "background.paper",
  border: (theme: any) => `1px solid ${theme.palette.divider}`,
  borderRadius: 2, // theme.shape.borderRadius * 2
  boxShadow: 24,
  p: { xs: 2, sm: 3, md: 4 },
  maxHeight: "90vh",
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
};

function App() {
  const [apiKey, setApiKey] = useState<string>(
    localStorage.getItem("geminiApiKey") || ""
  );
  const [projectPath, setProjectPath] = useState<string>(
    localStorage.getItem("projectPath") || ""
  );
  const [isApiConfigured, setIsApiConfigured] = useState<boolean>(false);
  const [isProjectLoaded, setIsProjectLoaded] = useState<boolean>(false);

  const [projectStructure, setProjectStructure] =
    useState<ProjectStructureNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [originalFileContent, setOriginalFileContent] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [userInput, setUserInput] = useState<string>("");
  const [aiSuggestions, setAiSuggestions] = useState<AIResponseData | null>(
    null
  );
  const [showSuggestionsModal, setShowSuggestionsModal] =
    useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>("Loading...");
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState("");
  const [snackbarSeverity, setSnackbarSeverity] = useState<
    "success" | "error" | "info" | "warning"
  >("info");

  const [actionResults, setActionResults] = useState<
    ApplyActionDetail[] | null
  >(null);

  const [themeMode, setThemeMode] = useState<PaletteMode>(() => {
    return (localStorage.getItem("themeMode") as PaletteMode) || "dark";
  });

  const [selectedAiModel, setSelectedAiModel] = useState<AIModelId>(() => {
    const storedModel = localStorage.getItem(
      "selectedAiModel"
    ) as AIModelId | null;
    if (
      storedModel &&
      availableAiModels.some((model) => model.id === storedModel)
    ) {
      return storedModel;
    }
    return DEFAULT_AI_MODEL_ID;
  });

  // RAG-related states
  const [ragSettings, setRagSettings] = useState<RAGSettings>({
    enabled: true,
    max_tokens: 20000,
  });
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);
  const [lastAiResponseMeta, setLastAiResponseMeta] = useState<any>(null);

  const [autoApplyAiSuggestions, setAutoApplyAiSuggestions] = useState<boolean>(
    () => {
      const storedValue = localStorage.getItem("autoApplyAiSuggestions");
      return storedValue === "true";
    }
  );

  const muiTheme = useMemo(() => getAppTheme(themeMode), [themeMode]);

  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // New states for Editor/Preview toggle
  const [viewMode, setViewMode] = useState<ViewMode>("editor");
  const [previewUrl, setPreviewUrl] = useState<string>("http://localhost:8080");
  const [previewDevice, setPreviewDevice] = useState<PreviewDevice>("desktop");

  // States for top bar menus
  const [fileMenuAnchorEl, setFileMenuAnchorEl] = useState<null | HTMLElement>(
    null
  );
  const [editMenuAnchorEl, setEditMenuAnchorEl] = useState<null | HTMLElement>(
    null
  );
  const [sectionMenuAnchorEl, setSectionMenuAnchorEl] =
    useState<null | HTMLElement>(null);
  const [goMenuAnchorEl, setGoMenuAnchorEl] = useState<null | HTMLElement>(
    null
  );
  const [helpMenuAnchorEl, setHelpMenuAnchorEl] = useState<null | HTMLElement>(
    null
  );
  const [aboutDevMenuAnchorEl, setAboutDevMenuAnchorEl] =
    useState<null | HTMLElement>(null);

  useEffect(() => {
    localStorage.setItem("themeMode", themeMode);
  }, [themeMode]);

  useEffect(() => {
    localStorage.setItem("selectedAiModel", selectedAiModel);
  }, [selectedAiModel]);

  useEffect(() => {
    localStorage.setItem(
      "autoApplyAiSuggestions",
      String(autoApplyAiSuggestions)
    );
  }, [autoApplyAiSuggestions]);

  const toggleTheme = () => {
    setThemeMode((prevMode) => (prevMode === "light" ? "dark" : "light"));
    setAboutDevMenuAnchorEl(null);
  };

  const hasUnsavedChanges: boolean =
    fileContent !== originalFileContent && selectedFile !== null;

  useEffect(() => {
    if (apiKey) localStorage.setItem("geminiApiKey", apiKey);
    else localStorage.removeItem("geminiApiKey");
  }, [apiKey]);

  useEffect(() => {
    if (projectPath) localStorage.setItem("projectPath", projectPath);
    else localStorage.removeItem("projectPath");
  }, [projectPath]);

  const showSnackbar = useCallback(
    (
      message: string,
      severity: "success" | "error" | "info" | "warning" = "info"
    ) => {
      setSnackbarMessage(message);
      setSnackbarSeverity(severity);
      setSnackbarOpen(true);
    },
    []
  );

  const handleConfigure = useCallback(
    async (showAlert = true) => {
      if (!apiKey) {
        showSnackbar("API Key is required.", "error");
        return;
      }
      setIsLoading(true);
      setLoadingMessage("Configuring API...");
      try {
        const response = await configureApiKey(apiKey, selectedAiModel);
        if (showAlert) showSnackbar(response.message, "success");
        setIsApiConfigured(true);
      } catch (err: any) {
        showSnackbar(err.message || "Failed to configure API Key.", "error");
        setIsApiConfigured(false);
      }
      setIsLoading(false);
      setLoadingMessage("Loading...");
    },
    [apiKey, selectedAiModel, showSnackbar]
  );

  const fetchProjectStructure = useCallback(async () => {
    if (!isProjectLoaded) return;
    setIsLoading(true);
    setLoadingMessage("Loading project structure...");
    try {
      const structure = await getProjectStructure();
      setProjectStructure(structure);
    } catch (err: any) {
      showSnackbar(
        err.message || "Failed to fetch project structure.",
        "error"
      );
      setProjectStructure(null);
    }
    setIsLoading(false);
    setLoadingMessage("Loading...");
  }, [isProjectLoaded, showSnackbar]);

  const fetchChatHistoryInternal = useCallback(async () => {
    if (!isProjectLoaded) return;
    try {
      const history = await getChatHistory();
      setChatMessages(history);
    } catch (err: any) {
      console.warn(
        "Failed to fetch chat history, could be a new session:",
        err.message
      );
      setChatMessages([]);
    }
  }, [isProjectLoaded]);

  const fetchRagSettings = useCallback(async () => {
    if (!isProjectLoaded) return;
    try {
      const settings = await getRagSettings();
      setRagSettings(settings);
    } catch (err: any) {
      console.warn("Failed to fetch RAG settings:", err.message);
    }
  }, [isProjectLoaded]);

  const fetchRagStatus = useCallback(async () => {
    if (!isProjectLoaded) return;
    try {
      const status = await getRagStatus();
      setRagStatus(status);
    } catch (err: any) {
      console.warn("Failed to fetch RAG status:", err.message);
    }
  }, [isProjectLoaded]);

  const handleLoadProject = useCallback(
    async (showAlert = true) => {
      if (!projectPath) {
        showSnackbar("Project Path is required.", "error");
        return;
      }
      if (!isApiConfigured) {
        showSnackbar(
          "API Key must be configured before loading a project.",
          "error"
        );
        return;
      }
      setIsLoading(true);
      setLoadingMessage("Loading project...");
      setActionResults(null);
      try {
        const response = await loadProject(projectPath);
        if (showAlert) showSnackbar(response.message, "success");
        setIsProjectLoaded(true);
        setChatMessages([]);
        setSelectedFile(null);
        setFileContent("");
        setOriginalFileContent("");
        setAiSuggestions(null);

        setLoadingMessage("Initializing RAG system...");
        await fetchRagSettings();
        await fetchRagStatus();
      } catch (err: any) {
        showSnackbar(err.message || "Failed to load project.", "error");
        setIsProjectLoaded(false);
        setProjectStructure(null);
      }
      setIsLoading(false);
      setLoadingMessage("Loading...");
    },
    [
      projectPath,
      isApiConfigured,
      showSnackbar,
      fetchRagSettings,
      fetchRagStatus,
    ]
  );

  const handleReindexProject = useCallback(async () => {
    if (!isProjectLoaded) {
      showSnackbar("No project loaded to reindex.", "warning");
      return;
    }
    setIsIndexing(true);
    setLoadingMessage("Reindexing project for RAG...");
    try {
      const response = await reindexProject();
      showSnackbar(
        `Project reindexed successfully. ${response.chunks_indexed} chunks indexed.`,
        "success"
      );
      await fetchRagStatus();
    } catch (err: any) {
      showSnackbar(err.message || "Failed to reindex project.", "error");
    }
    setIsIndexing(false);
    setLoadingMessage("Loading...");
  }, [isProjectLoaded, showSnackbar, fetchRagStatus]);

  const handleToggleRag = useCallback(async () => {
    const newSettings = { ...ragSettings, enabled: !ragSettings.enabled };
    try {
      await updateRagSettings(newSettings);
      setRagSettings(newSettings);
      showSnackbar(
        `RAG ${newSettings.enabled ? "enabled" : "disabled"}`,
        "success"
      );
    } catch (err: any) {
      showSnackbar(err.message || "Failed to update RAG settings.", "error");
    }
  }, [ragSettings, showSnackbar]);

  useEffect(() => {
    if (apiKey && !isApiConfigured) {
      handleConfigure(false);
    }
  }, [apiKey, isApiConfigured, handleConfigure]);

  useEffect(() => {
    if (projectPath && isApiConfigured && !isProjectLoaded) {
      handleLoadProject(false);
    }
  }, [projectPath, isApiConfigured, isProjectLoaded, handleLoadProject]);

  useEffect(() => {
    if (isProjectLoaded) {
      fetchProjectStructure();
      fetchRagSettings();
      fetchRagStatus();
    }
  }, [
    isProjectLoaded,
    fetchProjectStructure,
    fetchRagSettings,
    fetchRagStatus,
  ]);

  // New useEffect specifically for fetching chat history when a project is loaded
  useEffect(() => {
    if (isProjectLoaded) {
      fetchChatHistoryInternal();
    }
    // Note: We don't need to explicitly clear chatMessages if isProjectLoaded becomes false,
    // because handleLoadProject (which sets isProjectLoaded) already clears chatMessages.
  }, [isProjectLoaded, fetchChatHistoryInternal]);

  const handleFileSelect = async (filePath: string) => {
    if (hasUnsavedChanges) {
      if (
        !window.confirm(
          "You have unsaved changes. Are you sure you want to switch files? Changes will be lost."
        )
      ) {
        return;
      }
    }
    setIsLoading(true);
    setLoadingMessage(`Loading ${filePath}...`);
    setActionResults(null);
    try {
      const data = await getFileContent(filePath);
      setSelectedFile(filePath);
      setFileContent(data.content);
      setOriginalFileContent(data.content);
      setAiSuggestions(null);
      if (mobileOpen) setMobileOpen(false);
    } catch (err: any) {
      showSnackbar(err.message || `Failed to load file: ${filePath}`, "error");
      setSelectedFile(null);
      setFileContent("");
      setOriginalFileContent("");
    }
    setIsLoading(false);
    setLoadingMessage("Loading...");
  };

  const handleSaveFile = async () => {
    if (!selectedFile) {
      showSnackbar("No file selected to save.", "warning");
      return;
    }
    setIsLoading(true);
    setLoadingMessage("Saving file...");
    setActionResults(null);
    try {
      await saveFile(selectedFile, fileContent);
      showSnackbar("File saved successfully!", "success");
      setOriginalFileContent(fileContent);
      if (ragSettings.enabled) {
        setLoadingMessage("Updating RAG index...");
        await fetchRagStatus();
      }
    } catch (err: any) {
      showSnackbar(err.message || "Failed to save file.", "error");
    }
    setIsLoading(false);
    setLoadingMessage("Loading...");
  };

  const handleChatSubmit = async () => {
    if (!userInput.trim()) return;
    if (!isProjectLoaded && !showSettings) {
      showSnackbar("Please load a project before chatting.", "warning");
      return;
    }
    setIsLoading(true);
    setLoadingMessage(
      ragSettings.enabled
        ? "Searching relevant context..."
        : "Processing request..."
    );
    setActionResults(null);
    const newUserMessage: ChatMessage = { role: "user", content: userInput };
    setChatMessages((prev) => [...prev, newUserMessage]);
    const currentPrompt: string = userInput;
    setUserInput("");

    try {
      const aiResponse = await chatWithAI(
        currentPrompt,
        selectedFile,
        selectedAiModel
      );

      if (aiResponse.context_info) {
        setLastAiResponseMeta(aiResponse.context_info);
      }

      const newAiMessage: ChatMessage = {
        role: "assistant",
        content: aiResponse,
      };
      setChatMessages((prev) => [...prev, newAiMessage]);

      const hasActionableItems =
        aiResponse.actions &&
        aiResponse.actions.some(
          (a) =>
            a.type !== "GENERAL_MESSAGE" ||
            (a.type === "GENERAL_MESSAGE" &&
              a.message &&
              a.message !== aiResponse.explanation)
        );

      if (hasActionableItems) {
        setAiSuggestions(aiResponse); // Store suggestions for potential review or if auto-apply fails
        if (autoApplyAiSuggestions) {
          showSnackbar("Auto-applying AI suggestions...", "info");
          await handleApplyActions(aiResponse.actions); // Pass actions directly
          setShowSuggestionsModal(false); // Ensure modal is closed
        } else {
          setShowSuggestionsModal(true); // Show modal for manual application
        }
      } else {
        setAiSuggestions(null);
        setShowSuggestionsModal(false);
      }
    } catch (err: any) {
      showSnackbar(err.message || "Failed to get AI response.", "error");
      const errorAiMessageContent: AIResponseData = {
        explanation: `Error: ${err.message || "Failed to get AI response."}`,
        actions: [],
      };
      const errorAiMessage: ChatMessage = {
        role: "assistant",
        content: errorAiMessageContent,
      };
      setChatMessages((prev) => [...prev, errorAiMessage]);
      setAiSuggestions(null);
      setShowSuggestionsModal(false);
    }
    setIsLoading(false);
    setLoadingMessage("Loading...");
  };

  const handleApplyActions = async (actionsOverride?: AIAction[]) => {
    const actionsToProcess =
      actionsOverride || (aiSuggestions ? aiSuggestions.actions : null);
    const explanationToUse = aiSuggestions
      ? aiSuggestions.explanation
      : actionsOverride
      ? "AI actions auto-applied."
      : "AI actions applied.";

    if (!actionsToProcess || actionsToProcess.length === 0) {
      showSnackbar("No AI actions to apply.", "warning");
      return;
    }

    setIsLoading(true);
    setLoadingMessage("Applying AI actions...");
    setActionResults(null);

    try {
      const actionsToApply = actionsToProcess.filter(
        (action) =>
          action.type !== "GENERAL_MESSAGE" ||
          (action.type === "GENERAL_MESSAGE" &&
            action.message &&
            action.message !== explanationToUse)
      );

      if (actionsToApply.length === 0) {
        showSnackbar(
          "No actionable changes to apply from AI suggestions.",
          "info"
        );
        if (!actionsOverride) {
          // Only clear modal/state if not auto-applying (i.e., called from modal)
          setAiSuggestions(null);
          setShowSuggestionsModal(false);
        }
        setIsLoading(false); // ensure loading is stopped
        setLoadingMessage("Loading..."); // reset message
        return;
      }

      const response = await applyAIActions(actionsToApply);
      setActionResults(response.results);
      showSnackbar("AI actions processed. Review results.", "success");

      if (!actionsOverride) {
        // If called from modal
        setAiSuggestions(null);
        setShowSuggestionsModal(false);
      }

      fetchProjectStructure();

      const currentFileEditResult = response.results.find(
        (result) =>
          (result.type === "EDIT_FILE_COMPLETE" ||
            result.type === "EDIT_FILE_PARTIAL" ||
            result.type === "EDIT_FILE") &&
          result.path_info === selectedFile &&
          result.status === "success"
      );

      if (currentFileEditResult && selectedFile) {
        const updatedContentData = await getFileContent(selectedFile);
        setFileContent(updatedContentData.content);
        setOriginalFileContent(updatedContentData.content);
      }

      if (ragSettings.enabled) {
        setLoadingMessage("Updating RAG index after applying actions...");
        await fetchRagStatus();
      }
    } catch (err: any) {
      const errorMessage = err.message || "Failed to apply AI actions.";
      showSnackbar(errorMessage, "error");
      setActionResults([
        {
          // Provide feedback on error
          type: "GENERAL_ERROR", // Custom type for UI
          status: "error",
          detail: errorMessage,
        },
      ]);
    } finally {
      setIsLoading(false);
      setLoadingMessage("Loading...");
    }
  };

  const handleClearChat = async () => {
    setIsLoading(true);
    setLoadingMessage("Clearing chat history...");
    setActionResults(null);
    try {
      await clearChatHistory();
      setChatMessages([]);
      setAiSuggestions(null);
      setShowSuggestionsModal(false);
      setLastAiResponseMeta(null);
      showSnackbar("Chat history cleared.", "success");
    } catch (err: any) {
      showSnackbar(err.message || "Failed to clear chat history.", "error");
    }
    setIsLoading(false);
    setLoadingMessage("Loading...");
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleViewModeChange = (
    event: React.MouseEvent<HTMLElement>,
    newMode: ViewMode | null
  ) => {
    if (newMode) {
      setViewMode(newMode);
    }
  };

  const handleMenuOpen =
    (setter: React.Dispatch<React.SetStateAction<HTMLElement | null>>) =>
    (event: React.MouseEvent<HTMLElement>) => {
      setter(event.currentTarget);
    };

  const handleMenuClose = () => {
    setFileMenuAnchorEl(null);
    setEditMenuAnchorEl(null);
    setSectionMenuAnchorEl(null);
    setGoMenuAnchorEl(null);
    setHelpMenuAnchorEl(null);
  };

  // Placeholder for non-File menu items
  const handleMenuItemClick = (menuName: string) => {
    showSnackbar(`${menuName} - Coming Soon!`, "info");
    handleMenuClose();
  };

  const handleOpenTerminalClick = () => {
    showSnackbar("Open Terminal - Feature coming soon!", "info");
    handleMenuClose();
  };

  // Specific handlers for File menu items
  const handleCreateFile = () => {
    showSnackbar("Create File - Not implemented yet.", "info");
    handleMenuClose();
  };

  const handleDeleteFile = () => {
    if (!selectedFile) {
      showSnackbar("No file selected to delete.", "warning");
      handleMenuClose();
      return;
    }
    showSnackbar(`Delete File: ${selectedFile} - Not implemented yet.`, "info");
    handleMenuClose();
  };

  const drawerContent = (
    <FileExplorer
      projectStructure={projectStructure}
      onFileSelect={handleFileSelect}
      selectedFilePath={selectedFile}
    />
  );

  const generateAppBarTitle = () => {
    const appBaseTitle = "Local AI Developer Agent";
    if (showSettings) {
      return `Settings — ${appBaseTitle}`;
    }

    if (isProjectLoaded && projectPath) {
      const projectName = projectPath.split(/[\/]/).pop() || "Project";
      if (selectedFile) {
        const unsavedIndicator = hasUnsavedChanges ? " ●" : "";
        return `${selectedFile}${unsavedIndicator} — ${projectName} — ${appBaseTitle}`;
      }
      return `${projectName} — ${appBaseTitle}`;
    }
    return appBaseTitle;
  };

  const renderRagStatusChip = () => {
    if (!isProjectLoaded || !ragStatus) return null;

    const isIndexed = ragStatus.indexed && ragStatus.total_chunks > 0;
    const chipColor = ragSettings.enabled
      ? isIndexed
        ? "success"
        : "warning"
      : "default";
    const chipIcon = ragSettings.enabled ? (
      isIndexed ? (
        <CheckCircleIcon fontSize="small" />
      ) : (
        <ErrorIcon fontSize="small" />
      )
    ) : (
      <InfoIcon fontSize="small" />
    );
    const chipLabel = ragSettings.enabled
      ? isIndexed
        ? `RAG: ${ragStatus.total_chunks} chunks`
        : "RAG: Not indexed"
      : "RAG: Disabled";

    return (
      <Tooltip
        title={
          <Box sx={{ p: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: "bold" }}>
              RAG Status
            </Typography>
            <Typography variant="caption" display="block">
              Enabled: {ragSettings.enabled ? "Yes" : "No"}
            </Typography>
            <Typography variant="caption" display="block">
              Indexed: {isIndexed ? "Yes" : "No"}
            </Typography>
            {isIndexed && (
              <Typography variant="caption" display="block">
                Total chunks: {ragStatus.total_chunks}
              </Typography>
            )}
            {lastAiResponseMeta && (
              <Box
                sx={{
                  mt: 1,
                  pt: 1,
                  borderTop: `1px solid ${muiTheme.palette.divider}`,
                }}
              >
                <Typography
                  variant="caption"
                  display="block"
                  sx={{ fontWeight: "bold" }}
                >
                  Last query:
                </Typography>
                <Typography variant="caption" display="block">
                  Method: {lastAiResponseMeta.method}
                </Typography>
                <Typography variant="caption" display="block">
                  Chunks used: {lastAiResponseMeta.chunks_used}
                </Typography>
              </Box>
            )}
          </Box>
        }
        arrow
      >
        <Chip
          icon={chipIcon}
          label={chipLabel}
          size="small"
          color={chipColor}
          onClick={handleToggleRag}
          sx={{ mr: 1, cursor: "pointer" }}
        />
      </Tooltip>
    );
  };

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <Box
        sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
      >
        <AppBar
          position="fixed"
          elevation={1}
          sx={{
            zIndex: (theme) => theme.zIndex.drawer + 1,
            bgcolor: "background.paper",
            borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
            color: "text.primary",
          }}
        >
          <Toolbar variant="dense">
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: { xs: 1, sm: 1.5 }, display: { sm: "none" } }}
            >
              <MenuIcon />
            </IconButton>
            <Box
              sx={{
                display: { xs: "none", sm: "flex" },
                alignItems: "center",
                mr: 1,
              }}
            >
              {[
                {
                  label: "File",
                  anchor: fileMenuAnchorEl,
                  setter: setFileMenuAnchorEl,
                },
                {
                  label: "Edit",
                  anchor: editMenuAnchorEl,
                  setter: setEditMenuAnchorEl,
                },
                {
                  label: "Section",
                  anchor: sectionMenuAnchorEl,
                  setter: setSectionMenuAnchorEl,
                },
                {
                  label: "Go",
                  anchor: goMenuAnchorEl,
                  setter: setGoMenuAnchorEl,
                },
                {
                  label: "Help",
                  anchor: helpMenuAnchorEl,
                  setter: setHelpMenuAnchorEl,
                },
               
              ].map((item) => (
                <React.Fragment key={item.label}>
                  <MuiButton
                    onClick={handleMenuOpen(item.setter)}
                    sx={{
                      padding: (theme) => theme.spacing(0.5, 1.5),
                      color: "text.secondary",
                      fontSize: "0.875rem",
                      textTransform: "none",
                      "&:hover": {
                        bgcolor: "action.hover",
                      },
                    }}
                  >
                    {item.label}
                  </MuiButton>
                  <Menu
                    anchorEl={item.anchor}
                    open={Boolean(item.anchor)}
                    onClose={handleMenuClose}
                    MenuListProps={{ dense: true }}
                  >
                    {item.label === "File"
                      ? [
                          <MenuItem
                            key="create-file"
                            onClick={handleCreateFile}
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Create File
                          </MenuItem>,
                          <MenuItem
                            key="save-file"
                            onClick={() => {
                              handleSaveFile();
                              handleMenuClose();
                            }}
                            disabled={!selectedFile || !hasUnsavedChanges}
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Save File
                          </MenuItem>,
                          <MenuItem
                            key="delete-file"
                            onClick={handleDeleteFile}
                            disabled={!selectedFile}
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Delete File
                          </MenuItem>,
                        ]
                      : item.label === "Go"
                      ? [
                          <MenuItem
                            key="go-open-terminal"
                            onClick={handleOpenTerminalClick}
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Open Terminal
                          </MenuItem>,
                        ]
                      : [
                          // For "Edit", "Section", "Help"
                          <MenuItem
                            key={`${item.label}-coming-soon-1`}
                            onClick={() =>
                              handleMenuItemClick(`${item.label} Menu Item 1`)
                            }
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Coming Soon 1
                          </MenuItem>,
                          <MenuItem
                            key={`${item.label}-coming-soon-2`}
                            onClick={() =>
                              handleMenuItemClick(`${item.label} Menu Item 2`)
                            }
                            sx={{ fontSize: "0.875rem" }}
                          >
                            Coming Soon 2
                          </MenuItem>,
                        ]}
                  </Menu>
                </React.Fragment>
              ))}
            </Box>
            <Typography
              variant="body2"
              noWrap
              component="div"
              sx={{
                flexGrow: 1,
                fontWeight: 400,
                fontSize: { xs: "0.8rem", sm: "0.875rem" },
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                textAlign: "center",
                color: "text.secondary",
              }}
              title={generateAppBarTitle()}
            >
              {generateAppBarTitle()}
            </Typography>
            {renderRagStatusChip()}
            {isProjectLoaded && ragSettings.enabled && (
              <Tooltip title="Reindex project for RAG" arrow>
                <IconButton
                  color="inherit"
                  onClick={handleReindexProject}
                  disabled={isIndexing}
                  size="small"
                  sx={{ mr: 0.5 }}
                >
                  {isIndexing ? (
                    <CircularProgress size={18} color="inherit" />
                  ) : (
                    <RefreshIcon fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>
            )}
            <Tooltip
              title={
                themeMode === "light"
                  ? "Switch to Dark Mode"
                  : "Switch to Light Mode"
              }
              arrow
            >
              <IconButton
                color="inherit"
                onClick={toggleTheme}
                size="small"
                sx={{ mr: 0.5 }}
              >
                {themeMode === "dark" ? (
                  <Brightness7Icon fontSize="small" />
                ) : (
                  <Brightness4Icon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
            <Tooltip title="Settings" arrow>
              <IconButton
                color="inherit"
                onClick={() => setShowSettings(!showSettings)}
                size="small"
              >
                <SettingsIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Toolbar>
          {isLoading && (
            <LinearProgress
              sx={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: 2,
              }}
            />
          )}
        </AppBar>

        <Toolbar variant="dense" />

        {isLoading && !showSettings && (
          <Box
            sx={{
              position: "fixed",
              top: (theme) =>
                `calc(${theme.mixins.toolbar.minHeight}px + ${theme.spacing(
                  1
                )})`,
              right: (theme) => theme.spacing(2),
              zIndex: 1301,
              display: "flex",
              alignItems: "center",
              bgcolor: "background.paper",
              p: (theme) => theme.spacing(0.5, 1),
              borderRadius: 1,
              boxShadow: (theme) => theme.shadows[3],
            }}
          >
            <CircularProgress size={16} sx={{ mr: 1 }} />
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {loadingMessage}
            </Typography>
          </Box>
        )}

        <Snackbar
          open={snackbarOpen}
          autoHideDuration={4000}
          onClose={() => setSnackbarOpen(false)}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          <MuiAlert
            onClose={() => setSnackbarOpen(false)}
            severity={snackbarSeverity}
            sx={{ width: "100%" }}
            variant="filled"
            elevation={6}
          >
            {snackbarMessage}
          </MuiAlert>
        </Snackbar>

        <Modal
          open={showSuggestionsModal}
          onClose={() => {
            setShowSuggestionsModal(false);
          }}
          aria-labelledby="ai-suggestions-modal-title"
          aria-describedby="ai-suggestions-modal-description"
        >
          <Box sx={modalStyle}>
            {aiSuggestions && (
              <AISuggestionsPanel
                explanation={aiSuggestions.explanation}
                aiActions={aiSuggestions.actions}
                onApplyActions={handleApplyActions}
                isLoading={isLoading}
              />
            )}
            <MuiButton
              onClick={() => {
                setShowSuggestionsModal(false);
                setAiSuggestions(null);
              }}
              sx={{ mt: 2, alignSelf: "flex-end" }}
              variant="outlined"
              size="small"
            >
              Dismiss
            </MuiButton>
          </Box>
        </Modal>

        <Box
          component="main"
          sx={{
            display: "flex", // Parent flex container
            flexGrow: 1,
            overflow: "hidden",
          }}
        >
          {showSettings ? (
            <Container
              maxWidth="md"
              sx={{ mt: 4, mb: 4, flexGrow: 1, overflowY: "auto" }}
            >
              <SettingsPage
                apiKey={apiKey}
                setApiKey={setApiKey}
                projectPath={projectPath}
                setProjectPath={setProjectPath}
                onConfigure={handleConfigure}
                onLoadProject={handleLoadProject}
                isLoading={isLoading}
                isApiConfigured={isApiConfigured}
                isProjectLoaded={isProjectLoaded}
                selectedAiModel={selectedAiModel}
                setSelectedAiModel={setSelectedAiModel}
                availableAiModels={availableAiModels}
                autoApplyAiSuggestions={autoApplyAiSuggestions}
                setAutoApplyAiSuggestions={setAutoApplyAiSuggestions}
                onClose={() => setShowSettings(false)}
              />
            </Container>
          ) : isApiConfigured && isProjectLoaded ? (
            <>
              <Drawer // Temporary Mobile Drawer
                variant="temporary"
                open={mobileOpen}
                onClose={handleDrawerToggle}
                ModalProps={{ keepMounted: true }}
                sx={{
                  display: { xs: "block", sm: "none" },
                  "& .MuiDrawer-paper": {
                    boxSizing: "border-box",
                    width: drawerWidth,
                    top: (theme) => `${theme.mixins.toolbar.minHeight}px`,
                    height: (theme) =>
                      `calc(100% - ${theme.mixins.toolbar.minHeight}px)`,
                    borderRight: (theme) =>
                      `1px solid ${theme.palette.divider}`,
                  },
                }}
              >
                {drawerContent}
              </Drawer>
              <Drawer // Permanent Desktop Drawer
                variant="permanent"
                sx={{
                  display: { xs: "none", sm: "block" },
                  width: drawerWidth, // Define width for the Drawer component
                  flexShrink: 0, // Prevent Drawer from shrinking
                  "& .MuiDrawer-paper": {
                    boxSizing: "border-box",
                    width: drawerWidth, // Also set width for the paper
                    top: (theme) => `${theme.mixins.toolbar.minHeight}px`,
                    height: (theme) =>
                      `calc(100% - ${theme.mixins.toolbar.minHeight}px)`,
                    borderRight: (theme) =>
                      `1px solid ${theme.palette.divider}`,
                    bgcolor: "background.default",
                  },
                }}
                open
              >
                {drawerContent}
              </Drawer>

              <Box // Main Content Area (Editor + Chat)
                sx={{
                  flexGrow: 1, // This Box will take up remaining space
                  display: "flex",
                  flexDirection: { xs: "column", md: "row" },
                  overflow: "hidden",
                  height: (theme) =>
                    `calc(100vh - ${theme.mixins.toolbar.minHeight}px)`,
                }}
              >
                <Box // Editor/Preview Container
                  sx={{
                    flex: 2,
                    display: "flex",
                    flexDirection: "column",
                    p: 1,
                    minHeight: 0,
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      mb: 1,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", ml: 0.5 }}
                    >
                      {selectedFile
                        ? `Editing: ${selectedFile.split(/[\/]/).pop()}`
                        : "No file selected"}
                      {hasUnsavedChanges && (
                        <Box
                          component="span"
                          sx={{ color: "warning.main", ml: 0.5 }}
                        >
                          ●
                        </Box>
                      )}
                    </Typography>
                    <ToggleButtonGroup
                      value={viewMode}
                      exclusive
                      onChange={handleViewModeChange}
                      aria-label="View mode"
                      size="small"
                    >
                      <ToggleButton
                        value="editor"
                        aria-label="Editor mode"
                        sx={{ px: 1, py: 0.5, fontSize: "0.75rem" }}
                      >
                        <EditIcon sx={{ mr: 0.5 }} fontSize="inherit" />
                        Editor
                      </ToggleButton>
                      <ToggleButton
                        value="preview"
                        aria-label="Preview mode"
                        sx={{ px: 1, py: 0.5, fontSize: "0.75rem" }}
                      >
                        <VisibilityIcon sx={{ mr: 0.5 }} fontSize="inherit" />
                        Preview
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Box>

                  {viewMode === "editor" ? (
                    <>
                      <EditorPanel
                        selectedFile={selectedFile}
                        fileContent={fileContent}
                        setFileContent={setFileContent}
                        onSaveFile={handleSaveFile}
                        isLoading={isLoading}
                        hasUnsavedChanges={hasUnsavedChanges}
                        theme={themeMode as AppThemeType}
                      />
                      {actionResults && actionResults.length > 0 && (
                        <Paper
                          variant="outlined"
                          sx={{
                            mt: 1,
                            p: 1,
                            maxHeight: { xs: 100, sm: 150 },
                            overflowY: "auto",
                            borderColor: "divider",
                            fontSize: "0.8rem",
                          }}
                        >
                          <Typography
                            variant="caption"
                            display="block"
                            sx={{
                              fontWeight: "bold",
                              mb: 0.5,
                              color: "text.secondary",
                            }}
                          >
                            Action Results:
                          </Typography>
                          <ul style={{ margin: 0, paddingLeft: "18px" }}>
                            {actionResults.map(
                              (result: ApplyActionDetail, index) => (
                                <li key={index}>
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      fontSize: "0.8rem",
                                      display: "flex",
                                      alignItems: "center",
                                    }}
                                  >
                                    {result.status === "success" ? (
                                      <CheckCircleIcon
                                        color="success"
                                        sx={{ fontSize: "1rem", mr: 0.5 }}
                                      />
                                    ) : (
                                      <ErrorIcon
                                        color="error"
                                        sx={{ fontSize: "1rem", mr: 0.5 }}
                                      />
                                    )}
                                    <strong>
                                      {result.type === "EDIT_FILE_COMPLETE"
                                        ? "Edit Complete"
                                        : result.type === "EDIT_FILE_PARTIAL"
                                        ? "Edit Partial"
                                        : result.type}
                                    </strong>{" "}
                                    <Tooltip
                                      title={
                                        result.path_info || result.command || ""
                                      }
                                      arrow
                                    >
                                      <Box
                                        component="span"
                                        sx={{
                                          textOverflow: "ellipsis",
                                          overflow: "hidden",
                                          whiteSpace: "nowrap",
                                          maxWidth: "150px",
                                          mx: 0.5,
                                        }}
                                      >
                                        {result.path_info
                                          ?.split(/[\/]/)
                                          .pop() || result.command}
                                      </Box>
                                    </Tooltip>
                                    : {result.status}
                                    {result.detail && (
                                      <Tooltip title={result.detail} arrow>
                                        <InfoIcon
                                          sx={{
                                            fontSize: "0.8rem",
                                            ml: 0.5,
                                            color: "text.secondary",
                                            cursor: "help",
                                          }}
                                        />
                                      </Tooltip>
                                    )}
                                    {/* Show additional info for partial edits */}
                                    {result.type === "EDIT_FILE_PARTIAL" &&
                                      (result as any).changes_applied && (
                                        <Chip
                                          size="small"
                                          label={`${
                                            (result as any).changes_applied
                                          } changes`}
                                          sx={{
                                            ml: 0.5,
                                            height: 16,
                                            fontSize: "0.7rem",
                                          }}
                                        />
                                      )}
                                  </Typography>
                                  {result.output &&
                                    (result.output.stdout ||
                                      result.output.stderr) && (
                                      <pre
                                        style={{
                                          fontSize: "0.7em",
                                          margin: "2px 0 4px 18px",
                                          padding: "2px 4px",
                                          backgroundColor:
                                            muiTheme.palette.action
                                              .disabledBackground,
                                          borderRadius: "4px",
                                          overflowX: "auto",
                                          maxHeight: "60px",
                                        }}
                                      >
                                        {result.output.stdout && (
                                          <>
                                            <strong>Stdout:</strong>{" "}
                                            {result.output.stdout}
                                            <br />
                                          </>
                                        )}
                                        {result.output.stderr && (
                                          <>
                                            <strong>Stderr:</strong>{" "}
                                            {result.output.stderr}
                                          </>
                                        )}
                                      </pre>
                                    )}
                                </li>
                              )
                            )}
                          </ul>
                        </Paper>
                      )}
                    </>
                  ) : (
                    <PreviewPanel
                      previewUrl={previewUrl}
                      setPreviewUrl={setPreviewUrl}
                      previewDevice={previewDevice}
                      setPreviewDevice={setPreviewDevice}
                      isLoading={isLoading}
                    />
                  )}
                </Box>

                <Box // Chat Panel Container
                  sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    overflow: "hidden",
                    borderLeft: { md: `1px solid ${muiTheme.palette.divider}` },
                    borderColor: { md: "divider" },
                    p: 1,
                    minHeight: 0,
                    bgcolor: "background.default",
                  }}
                >
                  <ChatPanel
                    chatMessages={chatMessages}
                    userInput={userInput}
                    setUserInput={setUserInput}
                    onChatSubmit={handleChatSubmit}
                    onClearChat={handleClearChat}
                    isLoading={isLoading}
                  />
                </Box>
              </Box>
            </>
          ) : (
            <Container
              maxWidth="sm"
              sx={{ textAlign: "center", mt: 8, flexGrow: 1 }}
            >
              <Paper
                elevation={0}
                sx={{
                  p: 4,
                  border: (theme) => `1px dashed ${theme.palette.divider}`,
                }}
              >
                <Typography variant="h5" component="h1" gutterBottom>
                  {!isApiConfigured
                    ? "Welcome! Configure API Key"
                    : "Project Not Loaded"}
                </Typography>
                <Typography variant="body1" color="textSecondary" paragraph>
                  {!isApiConfigured
                    ? "To get started, please go to Settings and enter your API Key."
                    : "Please specify the path to your project folder in Settings to load it."}
                </Typography>
                <MuiButton
                  variant="contained"
                  color="primary"
                  onClick={() => setShowSettings(true)}
                  startIcon={<SettingsIcon />}
                  sx={{ mt: 2 }}
                >
                  Go to Settings
                </MuiButton>
              </Paper>
            </Container>
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
