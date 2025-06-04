import React, { useState, useMemo } from "react";
import { AIAction, PartialEditChange } from "../types";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
  IconButton,
  Paper,
  Chip,
  Divider,
  Tabs,
  Tab,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import TerminalIcon from "@mui/icons-material/Terminal";
import MessageIcon from "@mui/icons-material/Message";
import CodeIcon from "@mui/icons-material/Code";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import DifferenceIcon from "@mui/icons-material/Difference";
import BuildIcon from "@mui/icons-material/Build";

interface AISuggestionsPanelProps {
  explanation?: string;
  aiActions: AIAction[];
  onApplyActions: () => Promise<void>;
  isLoading: boolean;
}

const DiffViewer: React.FC<{
  originalContent: string;
  newContent?: string;
  changes?: PartialEditChange[];
  filePath: string;
}> = ({ originalContent, newContent, changes, filePath }) => {
  const [viewMode, setViewMode] = useState(0); // 0 = unified diff, 1 = side by side

  const generateUnifiedDiff = useMemo(() => {
    if (!originalContent) return "No original content available";

    if (newContent) {
      // For complete file replacement
      const originalLines = originalContent.split("\n");
      const newLines = newContent.split("\n");

      // Simple unified diff representation
      const diff: string[] = [];
      diff.push(`--- a/${filePath}`);
      diff.push(`+++ b/${filePath}`);
      diff.push(`@@ -1,${originalLines.length} +1,${newLines.length} @@`);

      // Add context and changes (simplified)
      newLines.forEach((line, i) => {
        if (i < originalLines.length && originalLines[i] !== line) {
          diff.push(`-${originalLines[i]}`);
          diff.push(`+${line}`);
        } else if (i >= originalLines.length) {
          diff.push(`+${line}`);
        } else {
          diff.push(` ${line}`);
        }
      });

      return diff.join("\n");
    } else if (changes) {
      // For partial changes
      const diff: string[] = [];
      diff.push(`--- a/${filePath}`);
      diff.push(`+++ b/${filePath}`);

      changes.forEach((change, i) => {
        switch (change.operation) {
          case "replace":
            diff.push(
              `@@ -${change.start_line},${
                (change.end_line || change.start_line!) - change.start_line! + 1
              } +${change.start_line},1 @@`
            );
            diff.push(
              `-Lines ${change.start_line}-${
                change.end_line || change.start_line
              } (original)`
            );
            diff.push(`+${change.content || ""}`);
            break;
          case "insert":
            diff.push(`@@ -${change.line},0 +${change.line},1 @@`);
            diff.push(`+${change.content || ""}`);
            break;
          case "delete":
            diff.push(
              `@@ -${change.start_line},${
                (change.end_line || change.start_line!) - change.start_line! + 1
              } +${change.start_line},0 @@`
            );
            diff.push(
              `-Lines ${change.start_line}-${
                change.end_line || change.start_line
              } (deleted)`
            );
            break;
        }
        if (i < changes.length - 1) diff.push("");
      });

      return diff.join("\n");
    }

    return "No changes to display";
  }, [originalContent, newContent, changes, filePath]);

  const generateChangesSummary = useMemo(() => {
    if (!changes) return null;

    return changes.map((change, i) => (
      <Box
        key={i}
        sx={{ mb: 1, p: 1, bgcolor: "action.hover", borderRadius: 1 }}
      >
        <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
          <Chip
            label={change.operation.toUpperCase()}
            size="small"
            color={
              change.operation === "insert"
                ? "success"
                : change.operation === "delete"
                ? "error"
                : "warning"
            }
            sx={{ mr: 1, minWidth: 60 }}
          />
          <Typography variant="caption" color="text.secondary">
            {change.operation === "replace" &&
              `Lines ${change.start_line}-${change.end_line}`}
            {change.operation === "insert" && `After line ${change.line}`}
            {change.operation === "delete" &&
              `Lines ${change.start_line}-${
                change.end_line || change.start_line
              }`}
          </Typography>
        </Box>
        {change.content && (
          <Typography
            variant="body2"
            component="pre"
            sx={{
              fontFamily: "monospace",
              fontSize: "0.75rem",
              whiteSpace: "pre-wrap",
              maxHeight: 100,
              overflow: "auto",
              bgcolor: "background.paper",
              p: 1,
              borderRadius: 0.5,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            {change.content.slice(0, 500)}
            {change.content.length > 500 ? "..." : ""}
          </Typography>
        )}
      </Box>
    ));
  }, [changes]);

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs
          value={viewMode}
          onChange={(e, v) => setViewMode(v)}
          aria-label="diff view mode"
        >
          <Tab label="Unified Diff" />
          {changes && <Tab label="Changes Summary" />}
        </Tabs>
      </Box>

      {viewMode === 0 && (
        <Typography
          component="pre"
          sx={{
            fontFamily: "monospace",
            fontSize: "0.75rem",
            whiteSpace: "pre-wrap",
            maxHeight: 300,
            overflow: "auto",
            bgcolor: "background.paper",
            p: 1.5,
            borderRadius: 1,
            border: "1px solid",
            borderColor: "divider",
            "& .diff-add": {
              bgcolor: "success.light",
              color: "success.contrastText",
            },
            "& .diff-remove": {
              bgcolor: "error.light",
              color: "error.contrastText",
            },
          }}
        >
          {generateUnifiedDiff}
        </Typography>
      )}

      {viewMode === 1 && changes && (
        <Box sx={{ maxHeight: 300, overflow: "auto" }}>
          {generateChangesSummary}
        </Box>
      )}
    </Box>
  );
};

const ActionItem: React.FC<{ action: AIAction; index: number }> = ({
  action,
  index,
}) => {
  const [open, setOpen] = React.useState(false);
  const [originalContent, setOriginalContent] = React.useState<string>("");

  // Fetch original content for diff when expanded
  React.useEffect(() => {
    if (
      open &&
      (action.type === "EDIT_FILE_COMPLETE" ||
        action.type === "EDIT_FILE_PARTIAL") &&
      action.file_path
    ) {
      // You'll need to implement this API call to get file content
      // For now, we'll use a placeholder
      setOriginalContent("// Original file content would be fetched here");
    }
  }, [open, action]);

  const handleToggle = () => {
    if (
      action.content ||
      action.changes ||
      (action.type === "EXECUTE_SHELL_COMMAND" && action.command) ||
      (action.type === "GENERAL_MESSAGE" && action.message)
    ) {
      setOpen(!open);
    }
  };

  let icon;
  let primaryText = "";
  let secondaryText = action.description || "";
  let contentToDisplay = action.content;
  let showDiff = false;

  switch (action.type) {
    case "EDIT_FILE_COMPLETE":
      icon = <EditIcon fontSize="small" />;
      primaryText = `Edit Complete: ${action.file_path}`;
      secondaryText = action.description || "Complete file replacement";
      showDiff = true;
      break;
    case "EDIT_FILE_PARTIAL":
      icon = <BuildIcon fontSize="small" />;
      primaryText = `Edit Partial: ${action.file_path}`;
      const changesCount = action.changes?.length || 0;
      secondaryText = action.description || `${changesCount} targeted changes`;
      showDiff = true;
      break;
    case "EDIT_FILE":
      icon = <EditIcon fontSize="small" />;
      primaryText = `Edit: ${action.file_path}`;
      secondaryText = action.description || "Legacy edit format";
      showDiff = true;
      break;
    case "CREATE_FILE":
      icon = <AddCircleOutlineIcon fontSize="small" />;
      primaryText = `Create: ${action.file_path}`;
      secondaryText =
        action.description || (action.content ? "View content below" : "");
      break;
    case "CREATE_FOLDER":
      icon = <CreateNewFolderIcon fontSize="small" />;
      primaryText = `Create Folder: ${action.folder_path}`;
      contentToDisplay = undefined;
      break;
    case "EXECUTE_SHELL_COMMAND":
      icon = <TerminalIcon fontSize="small" />;
      primaryText = `Execute: ${action.command}`;
      secondaryText = action.description || "Shell command to execute";
      contentToDisplay = action.command;
      break;
    case "GENERAL_MESSAGE":
      icon = <MessageIcon fontSize="small" />;
      primaryText = action.message || "General Message";
      secondaryText = action.description || "";
      contentToDisplay = action.message;
      break;
    default:
      icon = <CodeIcon fontSize="small" />;
      primaryText = `Unknown Action: ${action.type}`;
      contentToDisplay = JSON.stringify(action, null, 2);
  }

  const canExpand = !!(contentToDisplay || showDiff);

  return (
    <ListItem
      key={action.file_path || action.folder_path || action.command || index}
      divider
      secondaryAction={
        canExpand ? (
          <IconButton
            edge="end"
            onClick={handleToggle}
            size="small"
            aria-label={open ? "Collapse" : "Expand"}
          >
            {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        ) : null
      }
      onClick={canExpand ? handleToggle : undefined}
      sx={{
        cursor: canExpand ? "pointer" : "default",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        py: 1.25,
        pr: canExpand ? 5 : 2,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", width: "100%" }}>
        <ListItemIcon sx={{ minWidth: 36, mr: 0.5 }}>{icon}</ListItemIcon>
        <ListItemText
          primary={
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Typography
                variant="body1"
                sx={{ fontWeight: 500, fontSize: "0.95rem" }}
              >
                {primaryText}
              </Typography>
              {action.type === "EDIT_FILE_PARTIAL" && action.changes && (
                <Chip
                  size="small"
                  label={`${action.changes.length} changes`}
                  color="primary"
                  variant="outlined"
                />
              )}
              {showDiff && <DifferenceIcon fontSize="small" color="action" />}
            </Box>
          }
          secondary={
            secondaryText && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontSize: "0.85rem" }}
              >
                {secondaryText}
              </Typography>
            )
          }
          sx={{ flexGrow: 1, my: 0 }}
        />
      </Box>
      {canExpand && (
        <Collapse
          in={open}
          timeout="auto"
          unmountOnExit
          sx={{
            width: "100%",
            pl: "40px",
            pt: open ? 1 : 0,
          }}
        >
          <Box
            sx={{
              p: 1.5,
              bgcolor: (theme) =>
                theme.palette.mode === "dark"
                  ? "rgba(255,255,255,0.05)"
                  : "rgba(0,0,0,0.03)",
              borderRadius: 1,
              maxHeight: 400,
              overflowY: "auto",
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            {showDiff ? (
              <DiffViewer
                originalContent={originalContent}
                newContent={
                  action.type === "EDIT_FILE_COMPLETE" ||
                  action.type === "EDIT_FILE"
                    ? action.content
                    : undefined
                }
                changes={
                  action.type === "EDIT_FILE_PARTIAL"
                    ? action.changes
                    : undefined
                }
                filePath={action.file_path || "unknown"}
              />
            ) : (
              <Typography
                variant="caption"
                component="pre"
                sx={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  fontFamily: "monospace",
                  fontSize: "0.8rem",
                  lineHeight: 1.6,
                }}
              >
                {contentToDisplay}
              </Typography>
            )}
          </Box>
        </Collapse>
      )}
    </ListItem>
  );
};

// Rest of AISuggestionsPanel component remains the same...
const AISuggestionsPanel: React.FC<AISuggestionsPanelProps> = ({
  explanation,
  aiActions,
  onApplyActions,
  isLoading,
}) => {
  const actionableItems = aiActions.filter(
    (action) =>
      action.type !== "GENERAL_MESSAGE" ||
      (action.type === "GENERAL_MESSAGE" &&
        action.message &&
        action.message !== explanation)
  );

  if (actionableItems.length === 0 && !explanation) {
    return null;
  }

  const hasActualActions = actionableItems.some(
    (action) => action.type !== "GENERAL_MESSAGE"
  );

  return (
    <Card
      sx={{
        mt: 1,
        mb: 1,
        flexGrow: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
      elevation={2}
    >
      <CardContent
        sx={{
          pb: actionableItems.length > 0 ? 1 : 2,
          overflowY: "auto",
          flexGrow: 1,
        }}
      >
        <Typography variant="h6" component="h2" gutterBottom>
          AI Suggestions
        </Typography>
        {explanation && (
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mb: actionableItems.length > 0 ? 2 : 0,
              bgcolor: (theme) =>
                theme.palette.mode === "dark"
                  ? "rgba(255,255,255,0.03)"
                  : "rgba(0,0,0,0.02)",
              borderColor: "divider",
            }}
          >
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontStyle: "italic", whiteSpace: "pre-wrap" }}
            >
              {explanation}
            </Typography>
          </Paper>
        )}
        {actionableItems.length > 0 && (
          <List
            dense
            sx={{
              bgcolor: "background.paper",
              p: 0,
              borderRadius: 1,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            {actionableItems.map((action, index) => (
              <ActionItem key={index} action={action} index={index} />
            ))}
          </List>
        )}
      </CardContent>
      {hasActualActions && (
        <CardActions
          sx={{
            justifyContent: "flex-end",
            p: 1.5,
            borderTop: 1,
            borderColor: "divider",
            flexShrink: 0,
          }}
        >
          <Button
            variant="contained"
            color="primary"
            onClick={onApplyActions}
            disabled={isLoading}
            aria-busy={isLoading}
          >
            Apply Changes
          </Button>
        </CardActions>
      )}
    </Card>
  );
};

export default AISuggestionsPanel;
