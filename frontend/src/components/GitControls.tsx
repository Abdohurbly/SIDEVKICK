import React, { useState, useEffect, useCallback } from "react";
import {
  getGitStatus,
  gitAddAll,
  gitCommit,
  gitPush,
  gitGetCurrentBranch,
  gitPull,
} from "../services/api";
import { GitCommandResponse } from "../types";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  Divider,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import AddIcon from "@mui/icons-material/Add";
import CommitIcon from "@mui/icons-material/Commit";
import PushPinIcon from "@mui/icons-material/PushPin"; // Using PushPin as a placeholder for Push
import CloudDownloadIcon from "@mui/icons-material/CloudDownload"; // For Pull

const GitControls: React.FC = () => {
  const [branch, setBranch] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [commitMessage, setCommitMessage] = useState<string>("");
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<string | null>(null); // string to identify which button is loading

  const handleResponse = (operation: string, res: GitCommandResponse) => {
    let message = `Command: ${res.command}\nReturn Code: ${res.returncode}\n`;
    if (res.stdout) message += `Stdout:\n${res.stdout}\n`;
    if (res.stderr) message += `Stderr:\n${res.stderr}\n`;
    setOutput(message.trim());

    if (res.returncode !== 0) {
      let errorMessage = `Error during ${operation}: ${res.stderr || "Unknown error"}`;
      if (res.returncode === -1 && res.stderr && res.stderr.toLowerCase().includes("git command not found")) {
        errorMessage = "Error: Git command not found. Is Git installed and in your system's PATH?";
      }
      setError(errorMessage);
    } else {
      setError(null);
      if (operation === "commit") setCommitMessage("");
      // Refresh status and branch after successful operations that change state
      if (["add", "commit", "push", "pull"].includes(operation)) {
        fetchBranch();
        fetchStatus();
      }
    }
  };

  const runGitCommand = async (
    commandFn: () => Promise<GitCommandResponse>,
    operation: string
  ) => {
    setIsLoading(operation);
    setError(null);
    setOutput(null);
    try {
      const res = await commandFn();
      handleResponse(operation, res);
      if (operation === "branch" && res.stdout && res.returncode === 0)
        setBranch(res.stdout);
      if (operation === "status" && res.returncode === 0) {
        setStatus(res.stdout || "No changes detected or repository is clean.");
      } else if (operation === "status" && res.returncode !== 0) {
        setStatus(res.stderr || "Failed to get status");
      }
    } catch (err: any) {
      setError(`Failed to execute ${operation}: ${err.message}`);
      setOutput(`Error: ${err.message}`);
    }
    setIsLoading(null);
  };

  const fetchBranch = useCallback(
    () => runGitCommand(gitGetCurrentBranch, "branch"),
    []
  );
  const fetchStatus = useCallback(
    () => runGitCommand(getGitStatus, "status"),
    []
  );

  useEffect(() => {
    fetchBranch();
    fetchStatus();
  }, [fetchBranch, fetchStatus]);

  return (
    <Paper elevation={2} sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom component="h3">
        Git Controls
      </Typography>
      {branch && (
        <Chip label={`Branch: ${branch}`} color="info" sx={{ mb: 1 }} />
      )}

      <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
        <Button
          variant="outlined"
          size="small"
          onClick={fetchStatus}
          disabled={!!isLoading}
          startIcon={<RefreshIcon />}
        >
          {isLoading === "status" ? (
            <CircularProgress size={20} />
          ) : (
            "Refresh Status"
          )}
        </Button>
        <Button
          variant="outlined"
          size="small"
          onClick={() => runGitCommand(gitAddAll, "add")}
          disabled={!!isLoading}
          startIcon={<AddIcon />}
        >
          {isLoading === "add" ? <CircularProgress size={20} /> : "Stage All"}
        </Button>
        <Button
          variant="outlined"
          size="small"
          onClick={() => runGitCommand(gitPull, "pull")}
          disabled={!!isLoading}
          startIcon={<CloudDownloadIcon />}
        >
          {isLoading === "pull" ? <CircularProgress size={20} /> : "Pull"}
        </Button>
      </Box>

      {status && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Status:</Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 1,
              maxHeight: 150,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: "0.8rem",
              bgcolor: 'background.default'
            }}
          >
            {status || "No changes or unable to fetch status."}
          </Paper>
        </Box>
      )}

      <TextField
        fullWidth
        label="Commit Message"
        variant="outlined"
        size="small"
        value={commitMessage}
        onChange={(e) => setCommitMessage(e.target.value)}
        disabled={!!isLoading}
        sx={{ mb: 1 }}
      />
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() =>
            runGitCommand(() => gitCommit(commitMessage), "commit")
          }
          disabled={!!isLoading || !commitMessage.trim()}
          startIcon={<CommitIcon />}
        >
          {isLoading === "commit" ? (
            <CircularProgress size={20} color="inherit" />
          ) : (
            "Commit"
          )}
        </Button>
        <Button
          variant="contained"
          color="secondary"
          onClick={() => runGitCommand(gitPush, "push")}
          disabled={!!isLoading}
          startIcon={<PushPinIcon />}
        >
          {isLoading === "push" ? (
            <CircularProgress size={20} color="inherit" />
          ) : (
            "Push"
          )}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
          {error}
        </Alert>
      )}
      {output && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Last Command Output:</Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 1,
              maxHeight: 200,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: "0.8rem",
              bgcolor: 'background.default'
            }}
          >
            {output}
          </Paper>
        </Box>
      )}
    </Paper>
  );
};

export default GitControls;
