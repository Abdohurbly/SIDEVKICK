import React, { useState, useMemo, useEffect } from "react";
import { AIAction, PartialEditChange } from "../types";
import { getFileContentForDiff } from "../services/api"; // Import API call
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
  CircularProgress,
  Tooltip,
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
import BuildIcon from "@mui/icons-material/Build"; // For EDIT_FILE_PARTIAL (legacy)
import CompareArrowsIcon from "@mui/icons-material/CompareArrows"; // For EDIT_FILE_CONTEXTUAL
import PlaylistAddCheckIcon from "@mui/icons-material/PlaylistAddCheck"; // For EDIT_FILE_CONTEXTUAL_BATCH
import DeleteIcon from "@mui/icons-material/Delete"; // For delete operations
import AddIcon from "@mui/icons-material/Add"; // For insert operations

interface AISuggestionsPanelProps {
  explanation?: string;
  aiActions: AIAction[];
  onApplyActions: (actionsToApply: AIAction[]) => Promise<void>; // Modified to accept actions
  isLoading: boolean;
}

const ContextualChangeViewer: React.FC<{ change: PartialEditChange }> = ({
  change,
}) => {
  const renderContent = (content: string | undefined, label: string) => {
    if (!content) return null;
    return (
      <Box sx={{ mt: 0.5 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontWeight: "bold" }}
        >
          {label}:
        </Typography>
        <Typography
          component="pre"
          sx={{
            fontFamily: "monospace",
            fontSize: "0.75rem",
            whiteSpace: "pre-wrap",
            maxHeight: 100,
            overflow: "auto",
            bgcolor: "background.paper",
            p: 0.5,
            borderRadius: 0.5,
            border: "1px solid",
            borderColor: "divider",
            mt: 0.25,
          }}
        >
          {content.slice(0, 300)}
          {content.length > 300 && "..."}
        </Typography>
      </Box>
    );
  };

  return (
    <Box sx={{ mb: 1, p: 1, bgcolor: "action.hover", borderRadius: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 0.5, gap: 1 }}>
        <Chip
          label={(change.operation || "N/A").toUpperCase()}
          size="small"
          color={
            change.operation?.includes("insert")
              ? "success"
              : change.operation?.includes("delete")
              ? "error"
              : change.operation?.includes("replace")
              ? "warning"
              : "default"
          }
          sx={{ minWidth: 80, fontWeight: "medium" }}
        />
        {change.description && (
          <Typography variant="caption" color="text.secondary">
            {change.description}
          </Typography>
        )}
      </Box>
      {renderContent(change.before_context, "Context Before")}
      {change.operation === "replace" &&
        renderContent(change.target_content, "Target Content (to be replaced)")}
      {change.operation === "replace" &&
        renderContent(change.replacement_content, "Replacement Content")}

      {change.operation?.includes("insert") &&
        renderContent(change.anchor_content, "Anchor Content")}
      {change.operation?.includes("insert") &&
        renderContent(change.content, `Content to ${change.operation}`)}

      {change.operation === "delete" &&
        renderContent(change.target_content, "Target Content (to be deleted)")}
      {renderContent(change.after_context, "Context After")}
    </Box>
  );
};

const DiffViewer: React.FC<{
  originalContent: string;
  action: AIAction;
  isLoadingOriginal: boolean;
}> = ({ originalContent, action, isLoadingOriginal }) => {
  const [viewMode, setViewMode] = useState(0); // 0 = unified diff, 1 = changes summary

  const filePath = action.file_path || "unknown_file";

  const generateUnifiedDiff = useMemo(() => {
    if (isLoadingOriginal) return "Loading original content for diff...";
    if (!originalContent && action.type !== "CREATE_FILE")
      return "Original content not available for diff.";

    let newContentPreview = "";

    if (action.type === "EDIT_FILE_COMPLETE" || action.type === "EDIT_FILE") {
      newContentPreview = action.content || "";
    } else if (action.type === "CREATE_FILE") {
      newContentPreview = action.content || "";
      // For create file, original is empty
      const originalLines: string[] = [];
      const newLines = newContentPreview.split("\n");
      const diff: string[] = [];
      diff.push(`--- a/ (new file)`);
      diff.push(`+++ b/${filePath}`);
      diff.push(`@@ -0,0 +1,${newLines.length} @@`);
      newLines.forEach((line) => diff.push(`+${line}`));
      return diff.join("\n");
    }
    // For partial/contextual, we'd need to apply changes to original to get newContent
    // This is complex for a simple preview. For now, we'll show summary.

    const originalLines = originalContent.split("\n");
    const newLines = newContentPreview.split("\n");

    const diff: string[] = [];
    diff.push(`--- a/${filePath}`);
    diff.push(`+++ b/${filePath}`);

    // Basic line-by-line diff (very simplified)
    const maxLength = Math.max(originalLines.length, newLines.length);
    diff.push(`@@ -1,${originalLines.length} +1,${newLines.length} @@`);

    for (let i = 0; i < maxLength; i++) {
      const oldLine = originalLines[i];
      const newLine = newLines[i];
      if (oldLine !== undefined && newLine !== undefined) {
        if (oldLine === newLine) {
          diff.push(` ${oldLine}`);
        } else {
          diff.push(`-${oldLine}`);
          diff.push(`+${newLine}`);
        }
      } else if (newLine !== undefined) {
        diff.push(`+${newLine}`);
      } else if (oldLine !== undefined) {
        diff.push(`-${oldLine}`);
      }
    }
    return diff.join("\n");
  }, [originalContent, action, filePath, isLoadingOriginal]);

  const renderChangesSummary = () => {
    if (action.type === "EDIT_FILE_PARTIAL" && action.changes) {
      return action.changes.map((change, i) => (
        <ContextualChangeViewer key={`partial-${i}`} change={change} />
      ));
    }
    if (action.type === "EDIT_FILE_CONTEXTUAL") {
      // Create a single change object to pass to ContextualChangeViewer
      const contextualChange: PartialEditChange = {
        operation: action.operation!, // Should be present
        target_content: action.target_content,
        replacement_content: action.replacement_content,
        anchor_content: action.anchor_content,
        content: action.content, // For inserts
        before_context: action.before_context,
        after_context: action.after_context,
        description: action.description,
      };
      return <ContextualChangeViewer change={contextualChange} />;
    }
    if (action.type === "EDIT_FILE_CONTEXTUAL_BATCH" && action.changes) {
      return action.changes.map((change, i) => (
        <ContextualChangeViewer key={`contextual-batch-${i}`} change={change} />
      ));
    }
    return (
      <Typography variant="caption">
        No detailed changes summary for this action type.
      </Typography>
    );
  };

  const showSummaryTab =
    action.type === "EDIT_FILE_PARTIAL" ||
    action.type === "EDIT_FILE_CONTEXTUAL" ||
    action.type === "EDIT_FILE_CONTEXTUAL_BATCH";

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 1 }}>
        <Tabs
          value={viewMode}
          onChange={(e, v) => setViewMode(v)}
          aria-label="diff view mode"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab
            label="Unified Diff / Content"
            sx={{ minWidth: 100, fontSize: "0.8rem" }}
          />
          {showSummaryTab && (
            <Tab
              label="Changes Summary"
              sx={{ minWidth: 100, fontSize: "0.8rem" }}
            />
          )}
        </Tabs>
      </Box>

      {isLoadingOriginal && viewMode === 0 && (
        <Box sx={{ display: "flex", alignItems: "center", p: 2 }}>
          <CircularProgress size={20} sx={{ mr: 1 }} />
          <Typography variant="caption">
            Loading original file for diff...
          </Typography>
        </Box>
      )}

      {viewMode === 0 && !isLoadingOriginal && (
        <Typography
          component="pre"
          sx={{
            fontFamily: "monospace",
            fontSize: "0.75rem",
            whiteSpace: "pre-wrap",
            maxHeight: 300,
            overflow: "auto",
            bgcolor: "background.paper",
            p: 1,
            borderRadius: 0.5,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          {generateUnifiedDiff}
        </Typography>
      )}

      {viewMode === 1 && showSummaryTab && (
        <Box sx={{ maxHeight: 300, overflow: "auto", p: 0.5 }}>
          {renderChangesSummary()}
        </Box>
      )}
      {viewMode === 1 && !showSummaryTab && (
        <Typography variant="caption" sx={{ p: 1 }}>
          No summary view for this action type.
        </Typography>
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
  const [isLoadingOriginal, setIsLoadingOriginal] =
    React.useState<boolean>(false);

  const isDiffableAction = [
    "EDIT_FILE_COMPLETE",
    "EDIT_FILE_PARTIAL",
    "EDIT_FILE", // Legacy
    "EDIT_FILE_CONTEXTUAL",
    "EDIT_FILE_CONTEXTUAL_BATCH",
    "CREATE_FILE", // Diff against empty
  ].includes(action.type);

  useEffect(() => {
    if (
      open &&
      isDiffableAction &&
      action.file_path &&
      action.type !== "CREATE_FILE"
    ) {
      setIsLoadingOriginal(true);
      getFileContentForDiff(action.file_path)
        .then((content) => {
          setOriginalContent(content);
          setIsLoadingOriginal(false);
        })
        .catch((err) => {
          console.error("Error fetching original content:", err);
          setOriginalContent(
            `// Failed to fetch original content: ${err.message}`
          );
          setIsLoadingOriginal(false);
        });
    } else if (action.type === "CREATE_FILE") {
      setOriginalContent(""); // For CREATE_FILE, original is empty
      setIsLoadingOriginal(false);
    }
  }, [open, action.type, action.file_path, isDiffableAction]);

  const handleToggle = () => {
    // Expand if there's content/changes to show, or if it's a diffable action
    if (
      action.content ||
      action.changes ||
      (action.type === "EXECUTE_SHELL_COMMAND" && action.command) ||
      (action.type === "GENERAL_MESSAGE" && action.message) ||
      isDiffableAction
    ) {
      setOpen(!open);
    }
  };

  let icon;
  let primaryText = "";
  let secondaryText = action.description || "";
  let contentToDisplay = action.content; // Default content to show if not diff
  let showDiffViewer = false;

  switch (action.type) {
    case "EDIT_FILE_COMPLETE":
    case "EDIT_FILE": // Legacy
      icon = <EditIcon fontSize="small" />;
      primaryText = `Edit Complete: ${action.file_path}`;
      secondaryText = action.description || "Replace entire file content";
      showDiffViewer = true;
      contentToDisplay = undefined; // DiffViewer will handle content
      break;
    case "EDIT_FILE_PARTIAL": // Legacy line-based
      icon = <BuildIcon fontSize="small" />;
      primaryText = `Edit Partial (Line-based): ${action.file_path}`;
      secondaryText =
        action.description || `${action.changes?.length || 0} line changes`;
      showDiffViewer = true;
      contentToDisplay = undefined;
      break;
    case "EDIT_FILE_CONTEXTUAL":
      icon = <CompareArrowsIcon fontSize="small" />;
      primaryText = `Edit Contextual: ${action.file_path}`;
      secondaryText =
        action.description || `Contextual ${action.operation || "edit"}`;
      showDiffViewer = true;
      contentToDisplay = undefined;
      break;
    case "EDIT_FILE_CONTEXTUAL_BATCH":
      icon = <PlaylistAddCheckIcon fontSize="small" />;
      primaryText = `Batch Edit Contextual: ${action.file_path}`;
      secondaryText =
        action.description ||
        `${action.changes?.length || 0} contextual changes`;
      showDiffViewer = true;
      contentToDisplay = undefined;
      break;
    case "CREATE_FILE":
      icon = <AddCircleOutlineIcon fontSize="small" />;
      primaryText = `Create File: ${action.file_path}`;
      secondaryText =
        action.description ||
        (action.content ? "View content below" : "Empty file");
      showDiffViewer = true; // Diff against empty
      contentToDisplay = undefined;
      break;
    case "CREATE_FOLDER":
      icon = <CreateNewFolderIcon fontSize="small" />;
      primaryText = `Create Folder: ${action.folder_path}`;
      contentToDisplay = undefined;
      break;
    case "EXECUTE_SHELL_COMMAND":
      icon = <TerminalIcon fontSize="small" />;
      primaryText = `Execute: ${action.command}`;
      contentToDisplay = action.command;
      break;
    case "GENERAL_MESSAGE":
      icon = <MessageIcon fontSize="small" />;
      primaryText = action.message || "General Message";
      contentToDisplay = action.message;
      break;
    default:
      icon = <CodeIcon fontSize="small" />;
      primaryText = `Unknown Action: ${action.type}`;
      contentToDisplay = JSON.stringify(action, null, 2);
  }

  const canExpand = !!(contentToDisplay || showDiffViewer);

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
        py: 1,
        pr: canExpand ? 5 : 1.5,
        pl: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", width: "100%" }}>
        <ListItemIcon sx={{ minWidth: 32, mr: 0.75 }}>{icon}</ListItemIcon>
        <ListItemText
          primary={
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                flexWrap: "wrap",
              }}
            >
              <Typography
                variant="body1"
                sx={{
                  fontWeight: 500,
                  fontSize: "0.9rem",
                  wordBreak: "break-all",
                }}
              >
                {primaryText}
              </Typography>
              {(action.type === "EDIT_FILE_PARTIAL" ||
                action.type === "EDIT_FILE_CONTEXTUAL_BATCH") &&
                action.changes && (
                  <Chip
                    size="small"
                    label={`${action.changes.length} changes`}
                    color="primary"
                    variant="outlined"
                    sx={{ height: 18, fontSize: "0.7rem" }}
                  />
                )}
              {showDiffViewer && (
                <DifferenceIcon fontSize="small" color="action" />
              )}
            </Box>
          }
          secondary={
            secondaryText && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontSize: "0.8rem", mt: 0.25 }}
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
            pl: "36px", // Align with ListItemText approximately
            pt: open ? 0.5 : 0, // Reduced top padding when open
            mt: 0.5,
          }}
        >
          <Box
            sx={{
              p: 1, // Reduced padding inside content box
              bgcolor: (theme) =>
                theme.palette.mode === "dark"
                  ? "rgba(255,255,255,0.04)"
                  : "rgba(0,0,0,0.025)",
              borderRadius: 1,
              maxHeight: 350, // Increased max height
              overflowY: "auto",
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            {showDiffViewer ? (
              <DiffViewer
                originalContent={originalContent}
                action={action}
                isLoadingOriginal={isLoadingOriginal}
              />
            ) : (
              <Typography
                variant="caption"
                component="pre"
                sx={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  fontFamily: "monospace",
                  fontSize: "0.75rem", // Slightly smaller for dense info
                  lineHeight: 1.5,
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
        action.message !== explanation) // Avoid showing explanation as an action if it's the same
  );

  if (actionableItems.length === 0 && !explanation) {
    return null;
  }

  const hasActualFileOperations = actionableItems.some(
    (action) =>
      action.type !== "GENERAL_MESSAGE" &&
      action.type !== "EXECUTE_SHELL_COMMAND"
  );
  const hasShellCommands = actionableItems.some(
    (action) => action.type === "EXECUTE_SHELL_COMMAND"
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
      elevation={1} // Reduced elevation for a flatter look
    >
      <CardContent
        sx={{
          pb: actionableItems.length > 0 ? 1 : 2,
          overflowY: "auto",
          flexGrow: 1,
          p: 1.5, // Uniform padding
        }}
      >
        <Typography
          variant="h6"
          component="h2"
          gutterBottom
          sx={{ fontSize: "1.1rem", mb: 1 }}
        >
          AI Suggestions
        </Typography>
        {explanation && (
          <Paper
            variant="outlined"
            sx={{
              p: 1, // Reduced padding
              mb: actionableItems.length > 0 ? 1.5 : 0,
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
              sx={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}
            >
              {explanation}
            </Typography>
          </Paper>
        )}
        {actionableItems.length > 0 && (
          <List
            dense
            sx={{
              bgcolor: "transparent", // Let CardContent handle background
              p: 0,
              borderRadius: 1,
              // border: "1px solid", // Removed border, relies on Card border
              // borderColor: "divider",
            }}
          >
            {actionableItems.map((action, index) => (
              <ActionItem key={index} action={action} index={index} />
            ))}
          </List>
        )}
      </CardContent>
      {(hasActualFileOperations || hasShellCommands) && (
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
            onClick={() => onApplyActions(actionableItems)} // Pass current actionableItems
            disabled={isLoading}
            aria-busy={isLoading}
            size="small"
          >
            Apply {actionableItems.length} Suggestion
            {actionableItems.length === 1 ? "" : "s"}
          </Button>
        </CardActions>
      )}
    </Card>
  );
};

export default AISuggestionsPanel;
