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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import SettingsIcon from "@mui/icons-material/Settings";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import EditIcon from '@mui/icons-material/Edit';

import { getAppTheme } from "./theme";

import FileExplorer from "./components/FileExplorer";
import EditorPanel from "./components/EditorPanel";
import PreviewPanel from "./components/PreviewPanel"; // Import PreviewPanel
import ChatPanel from "./components/ChatPanel";
import AISuggestionsPanel from "./components/AISuggestionsPanel";
import SettingsPage from "./pages/SettingsPage";

const drawerWidth = 280;

const modalStyle = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 'clamp(300px, 80vw, 700px)',
  bgcolor: 'background.paper',
  border: (theme: any) => `1px solid ${theme.palette.divider}`,
  borderRadius: 2,
  boxShadow: 24,
  p: { xs: 2, sm: 3, md: 4 },
  maxHeight: '90vh',
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
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
  const [showSuggestionsModal, setShowSuggestionsModal] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
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
    const storedModel = localStorage.getItem("selectedAiModel") as AIModelId | null;
    if (storedModel && availableAiModels.some(model => model.id === storedModel)) {
      return storedModel;
    }
    return DEFAULT_AI_MODEL_ID;
  });

  const muiTheme = useMemo(() => getAppTheme(themeMode), [themeMode]);

  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // New states for Editor/Preview toggle
  const [viewMode, setViewMode] = useState<ViewMode>('editor');
  const [previewUrl, setPreviewUrl] = useState<string>('http://localhost:8080');
  const [previewDevice, setPreviewDevice] = useState<PreviewDevice>('desktop');


  useEffect(() => {
    localStorage.setItem("themeMode", themeMode);
  }, [themeMode]);

  useEffect(() => {
    localStorage.setItem("selectedAiModel", selectedAiModel);
  }, [selectedAiModel]);

  const toggleTheme = () => {
    setThemeMode((prevMode) => (prevMode === "light" ? "dark" : "light"));
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
      try {
        const response = await configureApiKey(apiKey, selectedAiModel); // Pass selectedAiModel
        if (showAlert) showSnackbar(response.message, "success");
        setIsApiConfigured(true);
      } catch (err: any) {
        showSnackbar(err.message || "Failed to configure API Key.", "error");
        setIsApiConfigured(false);
      }
      setIsLoading(false);
    },
    [apiKey, selectedAiModel, showSnackbar] // Added selectedAiModel to dependencies
  );

  const fetchProjectStructure = useCallback(async () => {
    if (!isProjectLoaded) return;
    setIsLoading(true);
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
      } catch (err: any) {
        showSnackbar(err.message || "Failed to load project.", "error");
        setIsProjectLoaded(false);
        setProjectStructure(null);
      }
      setIsLoading(false);
    },
    [projectPath, isApiConfigured, showSnackbar]
  );

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
      fetchChatHistoryInternal();
    }
  }, [isProjectLoaded, fetchProjectStructure, fetchChatHistoryInternal]);

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
  };

  const handleSaveFile = async () => {
    if (!selectedFile) {
      showSnackbar("No file selected to save.", "warning");
      return;
    }
    setIsLoading(true);
    setActionResults(null);
    try {
      await saveFile(selectedFile, fileContent);
      showSnackbar("File saved successfully!", "success");
      setOriginalFileContent(fileContent);
    } catch (err: any) {
      showSnackbar(err.message || "Failed to save file.", "error");
    }
    setIsLoading(false);
  };

  const handleChatSubmit = async () => {
    if (!userInput.trim()) return;
    if (!isProjectLoaded && !showSettings) {
      showSnackbar("Please load a project before chatting.", "warning");
      return;
    }
    setIsLoading(true);
    setActionResults(null);
    const newUserMessage: ChatMessage = { role: "user", content: userInput };
    setChatMessages((prev) => [...prev, newUserMessage]);
    const currentPrompt: string = userInput;
    setUserInput("");

    try {
      const aiResponse = await chatWithAI(currentPrompt, selectedFile, selectedAiModel);
      const newAiMessage: ChatMessage = {
        role: "assistant",
        content: aiResponse,
      };
      setChatMessages((prev) => [...prev, newAiMessage]);
      if (
        aiResponse.actions &&
        aiResponse.actions.some(
          (a) =>
            a.type !== "GENERAL_MESSAGE" ||
            (a.type === "GENERAL_MESSAGE" &&
              a.message &&
              a.message !== aiResponse.explanation)
        )
      ) {
        setAiSuggestions(aiResponse);
        setShowSuggestionsModal(true); // Open modal when suggestions are available
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
  };

  const handleApplyActions = async () => {
    if (
      !aiSuggestions ||
      !aiSuggestions.actions ||
      aiSuggestions.actions.length === 0
    ) {
      showSnackbar("No AI actions to apply.", "warning");
      return;
    }
    setIsLoading(true);
    setActionResults(null);
    try {
      const actionsToApply = aiSuggestions.actions.filter(
        (action) =>
          action.type !== "GENERAL_MESSAGE" ||
          (action.message && action.message !== aiSuggestions.explanation)
      );

      if (actionsToApply.length === 0) {
        showSnackbar(
          "No actionable changes to apply from AI suggestions.",
          "info"
        );
        setAiSuggestions(null);
        setShowSuggestionsModal(false);
        setIsLoading(false);
        return;
      }

      const response = await applyAIActions(actionsToApply);
      setActionResults(response.results);
      showSnackbar("AI actions processed. Review results if any.", "success");

      setAiSuggestions(null);
      setShowSuggestionsModal(false);
      fetchProjectStructure(); 
      if (selectedFile) {
        const editedCurrentFileAction = actionsToApply.find(
          (a) => a.type === "EDIT_FILE" && a.file_path === selectedFile
        );
        if (
          editedCurrentFileAction &&
          typeof editedCurrentFileAction.content === "string"
        ) {
          setFileContent(editedCurrentFileAction.content);
          setOriginalFileContent(editedCurrentFileAction.content);
        }
      }
    } catch (err: any) {
      showSnackbar(err.message || "Failed to apply AI actions.", "error");
    }
    setIsLoading(false);
  };

  const handleClearChat = async () => {
    setIsLoading(true);
    setActionResults(null);
    try {
      await clearChatHistory();
      setChatMessages([]);
      setAiSuggestions(null);
      setShowSuggestionsModal(false);
      showSnackbar("Chat history cleared.", "success");
    } catch (err: any) {
      showSnackbar(err.message || "Failed to clear chat history.", "error");
    }
    setIsLoading(false);
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

  const drawerContent = (
    <FileExplorer
      projectStructure={projectStructure}
      onFileSelect={handleFileSelect}
      selectedFilePath={selectedFile}
    />
  );

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <Box
        sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
      >
        <AppBar
          position="fixed"
          sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: "none" } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography
              variant="h6"
              noWrap
              component="div"
              sx={{ flexGrow: 1 }}
            >
              Local AI Developer Agent
            </Typography>
            <IconButton
              color="inherit"
              onClick={toggleTheme}
              title={
                themeMode === "light"
                  ? "Switch to Dark Mode"
                  : "Switch to Light Mode"
              }
            >
              {themeMode === "dark" ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
            <IconButton
              color="inherit"
              onClick={() => setShowSettings(!showSettings)}
              title="Settings"
            >
              <SettingsIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        {isLoading && (
          <Box
            sx={{
              position: "fixed",
              top: 10,
              right: 10,
              zIndex: 1301, // Above modal zIndex (typically 1300)
              display: "flex",
              alignItems: "center",
              bgcolor: "background.paper",
              p: 1,
              borderRadius: 1,
              boxShadow: 1,
            }}
          >
            <CircularProgress size={20} />{" "}
            <Typography variant="caption" sx={{ ml: 1 }}>
              Loading...
            </Typography>
          </Box>
        )}

        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={() => setSnackbarOpen(false)}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
        >
          <MuiAlert
            onClose={() => setSnackbarOpen(false)}
            severity={snackbarSeverity}
            sx={{ width: "100%" }}
            variant="filled"
          >
            {snackbarMessage}
          </MuiAlert>
        </Snackbar>

        <Modal
          open={showSuggestionsModal}
          onClose={() => {
            setShowSuggestionsModal(false);
            // Do not clear aiSuggestions here, allow panel to manage or apply to clear
          }}
          aria-labelledby="ai-suggestions-modal-title"
          aria-describedby="ai-suggestions-modal-description"
        >
          <Box sx={modalStyle}>
            {aiSuggestions && (
              <AISuggestionsPanel
                explanation={aiSuggestions.explanation}
                aiActions={aiSuggestions.actions}
                onApplyActions={handleApplyActions} // Will also close modal
                isLoading={isLoading}
              />
            )}
            <MuiButton 
              onClick={() => {
                setShowSuggestionsModal(false);
                setAiSuggestions(null); // Clear suggestions on explicit dismiss
              }}
              sx={{ mt: 2, alignSelf: 'flex-end' }}
              variant="outlined"
            >
              Dismiss
            </MuiButton>
          </Box>
        </Modal>

        <Box
          component="main"
          sx={{
            display: "flex",
            flexGrow: 1,
            pt: "64px",
          }}
        >
          {showSettings ? (
            <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
              <SettingsPage
                apiKey={apiKey}
                setApiKey={setApiKey}
                projectPath={projectPath}
                setProjectPath={setProjectPath}
                onConfigure={handleConfigure} // Pass handleConfigure here
                onLoadProject={handleLoadProject}
                isLoading={isLoading}
                isApiConfigured={isApiConfigured}
                isProjectLoaded={isProjectLoaded}
                selectedAiModel={selectedAiModel}
                setSelectedAiModel={setSelectedAiModel}
                availableAiModels={availableAiModels}
                onClose={() => setShowSettings(false)}
              />
            </Container>
          ) : isApiConfigured && isProjectLoaded ? (
            <>
              <Drawer
                variant="temporary"
                open={mobileOpen}
                onClose={handleDrawerToggle}
                ModalProps={{
                  keepMounted: true,
                }}
                sx={{
                  display: { xs: "block", sm: "none" },
                  "& .MuiDrawer-paper": {
                    boxSizing: "border-box",
                    width: drawerWidth,
                  },
                }}
              >
                {drawerContent}
              </Drawer>
              <Drawer
                variant="permanent"
                sx={{
                  display: { xs: "none", sm: "block" },
                  "& .MuiDrawer-paper": {
                    boxSizing: "border-box",
                    width: drawerWidth,
                    position: "relative",
                    height: "calc(100vh - 64px)",
                  },
                }}
                open
              >
                {drawerContent}
              </Drawer>

              <Box
                component="div"
                sx={{
                  flexGrow: 1,
                  p: 1,
                  display: "flex",
                  flexDirection: { xs: "column", md: "row" },
                  overflow: "hidden", // Added to contain children
                }}
              >
                <Box // Editor Area Box
                  sx={{
                    flex: 2,
                    display: "flex",
                    flexDirection: "column",
                    // overflowY: "auto", // Removed for better child scroll management
                    p: { xs: 1, md: 2 },
                    minHeight: 0, // Ensure flex child can shrink
                  }}
                >
                  <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
                    <ToggleButtonGroup
                      value={viewMode}
                      exclusive
                      onChange={handleViewModeChange}
                      aria-label="View mode"
                    >
                      <ToggleButton value="editor" aria-label="Editor mode">
                        <EditIcon sx={{ mr: 1 }} />
                        Editor
                      </ToggleButton>
                      <ToggleButton value="preview" aria-label="Preview mode">
                        <Brightness7Icon sx={{ mr: 1 }} />
                        Preview
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Box>

                  {viewMode === 'editor' ? (
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
                      {actionResults && (
                        <Box
                          sx={{
                            mt: 2,
                            p: 2,
                            border: "1px solid",
                            borderColor: "divider",
                            borderRadius: 1,
                            maxHeight: 200, 
                            overflowY: 'auto'
                          }}
                          className="action-results-panel"
                        >
                          <Typography variant="h6" gutterBottom>
                            Action Results
                          </Typography>
                          <ul>
                            {actionResults.map((result, index) => (
                              <li
                                key={index}
                                className={`action-result ${result.status}`}
                              >
                                <Typography variant="body2">
                                  <strong>{result.type}</strong>{" "}
                                  {result.path_info || result.command}:{" "}
                                  {result.status}
                                  {result.detail && (
                                    <Typography variant="caption" component="small">
                                      {" "}
                                      - {result.detail}
                                    </Typography>
                                  )}
                                  {result.output && (
                                    <pre style={{ fontSize: '0.8em', margin: '4px 0', padding: '4px', backgroundColor: muiTheme.palette.action.hover, borderRadius: '4px', overflowX: 'auto' }}>
                                      <strong>Stdout:</strong>{" "}
                                      {result.output.stdout || "(empty)"}\n
                                      <strong>Stderr:</strong>{" "}
                                      {result.output.stderr || "(empty)"} 
                                    </pre>
                                  )}
                                </Typography>
                              </li>
                            ))}
                          </ul>
                        </Box>
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

                <Box // Chat Area Box
                  sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    overflow: "hidden", // Keep this for ChatPanel to manage its height
                    borderLeft: { md: "1px solid" },
                    borderColor: { md: "divider" },
                    p: { xs: 1, md: 2 },
                    minHeight: 0, // Ensure flex child can shrink
                  }}
                >
                  <Box
                    sx={{
                      flexGrow: 1,
                      display: "flex",
                      flexDirection: "column",
                      minHeight: 0, 
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
              </Box>
            </>
          ) : (
            <Container maxWidth="sm" sx={{ textAlign: "center", mt: 8 }}>
              <Typography variant="h5" gutterBottom>
                {!isApiConfigured
                  ? "Welcome! Please configure your API Key."
                  : "Project not loaded. Please load a project."}
              </Typography>
              <Typography variant="body1" color="textSecondary" paragraph>
                {!isApiConfigured
                  ? "Go to Settings to enter your API Key and enable project features."
                  : "Go to Settings to specify the path to your project folder."}
              </Typography>
              <MuiButton
                variant="contained"
                color="primary"
                onClick={() => setShowSettings(true)}
                sx={{ mt: 2 }}
              >
                Go to Settings
              </MuiButton>
            </Container>
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
