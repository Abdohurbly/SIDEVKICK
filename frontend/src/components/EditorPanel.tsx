import React from "react";
import Editor, { OnChange } from "@monaco-editor/react";
import { Theme as AppThemeType } from "../types"; // Renamed to avoid conflict
import { Box, Button, Typography, Paper } from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";

interface EditorPanelProps {
  selectedFile: string | null;
  fileContent: string;
  setFileContent: (content: string) => void;
  onSaveFile: () => Promise<void>;
  isLoading: boolean;
  hasUnsavedChanges: boolean;
  theme: AppThemeType; // Use the renamed AppThemeType
}

const getLanguageForFile = (fileName: string | null): string => {
  if (!fileName) return "plaintext";
  const extension = fileName.split(".").pop()?.toLowerCase();
  switch (extension) {
    case "ts":
    case "tsx":
      return "typescript";
    case "js":
    case "jsx":
      return "javascript";
    case "py":
      return "python";
    case "json":
      return "json";
    case "html":
      return "html";
    case "css":
      return "css";
    case "md":
      return "markdown";
    case "java":
      return "java";
    case "c":
      return "c";
    case "cpp":
      return "cpp";
    case "cs":
      return "csharp";
    case "go":
      return "go";
    case "php":
      return "php";
    case "rb":
      return "ruby";
    case "rs":
      return "rust";
    case "sql":
      return "sql";
    case "yaml":
    case "yml":
      return "yaml";
    case "xml":
      return "xml";
    case "sh":
      return "shell";
    case "swift":
      return "swift";
    default:
      return "plaintext";
  }
};

const EditorPanel: React.FC<EditorPanelProps> = ({
  selectedFile,
  fileContent,
  setFileContent,
  onSaveFile,
  isLoading,
  hasUnsavedChanges,
  theme,
}) => {
  const handleEditorChange: OnChange = (value) => {
    setFileContent(value || "");
  };

  const monacoTheme = theme === "dark" ? "vs-dark" : "vs";

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        p: 0,
        m: 0,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h6" component="h2" sx={{ fontSize: "1.1rem" }}>
          Editor
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={onSaveFile}
          disabled={!selectedFile || isLoading || !hasUnsavedChanges}
          startIcon={<SaveIcon />}
          size="small"
        >
          Save File
        </Button>
      </Box>
      {selectedFile && (
        <Typography variant="caption" color="text.secondary" gutterBottom>
          Editing: {selectedFile} {hasUnsavedChanges && "(Unsaved Changes)"}
        </Typography>
      )}
      <Paper
        variant="outlined"
        sx={{
          flexGrow: 1, 
          minHeight: 0, // Changed for better flex behavior
          overflow: "hidden", // Monaco needs a bounded, non-scrolling container
          borderColor: "divider",
          mt: 1,
        }}
      >
        <Editor
          height="100%" // Editor fills the Paper
          language={getLanguageForFile(selectedFile)}
          value={fileContent}
          onChange={handleEditorChange}
          theme={monacoTheme}
          options={{
            minimap: { enabled: true },
            automaticLayout: true,
            readOnly: !selectedFile || isLoading,
            fontSize: 14,
            wordWrap: "on",
            scrollBeyondLastLine: false,
          }}
          aria-label={
            selectedFile ? `Content of ${selectedFile}` : "File content editor"
          }
        />
      </Paper>
    </Box>
  );
};

export default EditorPanel;
