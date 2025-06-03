import React from "react";
import { AIAction } from "../types";
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
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import TerminalIcon from "@mui/icons-material/Terminal";
import MessageIcon from "@mui/icons-material/Message";
import CodeIcon from "@mui/icons-material/Code";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";

interface AISuggestionsPanelProps {
  explanation?: string;
  aiActions: AIAction[];
  onApplyActions: () => Promise<void>;
  isLoading: boolean;
}

const ActionItem: React.FC<{ action: AIAction; index: number }> = ({
  action,
  index,
}) => {
  const [open, setOpen] = React.useState(false);

  const handleToggle = () => {
    if (
      action.content ||
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

  switch (action.type) {
    case "EDIT_FILE":
      icon = <EditIcon fontSize="small" />;
      primaryText = `Edit: ${action.file_path}`;
      if (action.description && action.description !== action.file_path) {
        secondaryText = action.description;
      } else if (!action.description && action.content) {
        secondaryText = "View content changes below";
      }
      break;
    case "CREATE_FILE":
      icon = <AddCircleOutlineIcon fontSize="small" />;
      primaryText = `Create: ${action.file_path}`;
      secondaryText = action.description || (action.content ? "View content below" : "");
      break;
    case "CREATE_FOLDER":
      icon = <CreateNewFolderIcon fontSize="small" />;
      primaryText = `Create Folder: ${action.folder_path}`;
      contentToDisplay = undefined; // No content for folder creation
      break;
    case "EXECUTE_SHELL_COMMAND":
      icon = <TerminalIcon fontSize="small" />;
      primaryText = `Execute: ${action.command}`;
      secondaryText = action.description || "Shell command to execute";
      contentToDisplay = action.command; // Display command in detail
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

  const canExpand = !!contentToDisplay;

  return (
    <ListItem
      key={action.file_path || action.folder_path || action.command || index}
      divider
      secondaryAction={
        canExpand ? (
          <IconButton edge="end" onClick={handleToggle} size="small" aria-label={open ? 'Collapse' : 'Expand'}>
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
        pr: canExpand ? 5 : 2, // Ensure space for IconButton if it's there
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", width: "100%" }}>
        <ListItemIcon sx={{ minWidth: 36, mr: 0.5 }}>{icon}</ListItemIcon>
        <ListItemText
          primary={
            <Typography variant="body1" sx={{ fontWeight: 500, fontSize: '0.95rem' }}>
              {primaryText}
            </Typography>
          }
          secondary={
            secondaryText && (
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
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
            pl: "40px" /* Align with ListItemText after icon (36px icon + 4px approx margin) */,
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
              maxHeight: 250,
              overflowY: "auto",
              border: '1px solid',
              borderColor: 'divider'
            }}
          >
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
        action.message !== explanation) 
  );

  if (actionableItems.length === 0 && !explanation) {
    return null;
  }

  const hasActualActions = actionableItems.some(action => action.type !== "GENERAL_MESSAGE");

  return (
    <Card sx={{ 
      mt: 1, 
      mb: 1,
      flexGrow: 1,         // For when it's a flex item in the Modal's Box
      minHeight: 0,          // Allow it to shrink and enable internal scrolling
      display: 'flex',       // Make the Card a flex container
      flexDirection: 'column', // Stack CardContent and CardActions vertically
      // overflow: 'hidden' // Optional: prevent card itself from scrolling if content is misconfigured
    }} elevation={2}>
      <CardContent sx={{ 
        pb: actionableItems.length > 0 ? 1 : 2, 
        overflowY: 'auto',   // This is the key for scrolling CardContent
        flexGrow: 1,          // Allow CardContent to take up available vertical space
      }}>
        <Typography variant="h6" component="h2" gutterBottom>
          AI Suggestions
        </Typography>
        {explanation && (
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1.5, 
              mb: actionableItems.length > 0 ? 2 : 0, 
              bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
              borderColor: 'divider'
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
          <List dense sx={{ 
            bgcolor: "background.paper", 
            p: 0, 
            borderRadius: 1, 
            border: '1px solid', 
            borderColor: 'divider' 
          }}>
            {actionableItems.map((action, index) => (
              <ActionItem key={index} action={action} index={index} />
            ))}
          </List>
        )}
      </CardContent>
      {hasActualActions && (
        <CardActions sx={{ 
          justifyContent: "flex-end", 
          p: 1.5, // Adjusted padding
          borderTop: 1, 
          borderColor: 'divider',
          flexShrink: 0, // Prevent CardActions from shrinking
        }}>
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
