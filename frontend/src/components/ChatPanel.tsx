import React, { useRef, useEffect } from "react";
import { ChatMessage, AIResponseData } from "../types";
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Collapse,
  IconButton,
  CircularProgress,
  useTheme,
  alpha,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ClearAllIcon from "@mui/icons-material/ClearAll";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import CodeIcon from "@mui/icons-material/Code";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";

interface ChatPanelProps {
  chatMessages: ChatMessage[];
  userInput: string;
  setUserInput: (input: string) => void;
  onChatSubmit: () => Promise<void>;
  onClearChat: () => Promise<void>;
  isLoading: boolean;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  chatMessages,
  userInput,
  setUserInput,
  onChatSubmit,
  onClearChat,
  isLoading,
}) => {
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const [openActionDetails, setOpenActionDetails] = React.useState<{
    [key: number]: boolean;
  }>({});
  const theme = useTheme();

  useEffect(() => {
    const chatNode = chatMessagesRef.current;
    if (chatNode) {
      // Scroll to bottom only if the user is already near the bottom or for new messages
      // This prevents auto-scrolling if the user has scrolled up to read past messages
      const scrollThreshold = 150; // If user is within 150px from bottom, auto-scroll
      const isScrolledToBottom =
        chatNode.scrollHeight - chatNode.clientHeight <=
        chatNode.scrollTop + scrollThreshold;

      if (isScrolledToBottom || chatMessages.length === 1) {
        // also scroll for the very first message
        chatNode.scrollTop = chatNode.scrollHeight;
      }
    }
  }, [chatMessages]);

  const handleKeyPress = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !isLoading &&
      userInput.trim()
    ) {
      event.preventDefault();
      onChatSubmit();
    }
  };

  const toggleActionDetails = (index: number) => {
    setOpenActionDetails((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        p: 0,
        m: 0,
        bgcolor: "transparent", // Inherit from parent, usually background.default
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
          px: 0.5,
        }}
      >
        <Typography
          variant="subtitle1" // Changed from h6
          component="h2"
          sx={{ fontWeight: 500, color: "text.secondary" }}
        >
          AI Assistant
        </Typography>
        <Button
          variant="outlined"
          size="small"
          onClick={onClearChat}
          disabled={isLoading || chatMessages.length === 0}
          startIcon={<ClearAllIcon fontSize="small" />}
          title="Clear chat history"
          sx={{ textTransform: "none", fontSize: "0.8rem" }}
        >
          Clear
        </Button>
      </Box>
      <Box
        ref={chatMessagesRef}
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          mb: 1,
          p: 1, // Reduced padding for tighter feel
          bgcolor: "background.paper", // Explicit background for chat area
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1, // theme.shape.borderRadius
        }}
      >
        {chatMessages.map((msg, index) => (
          <Box
            key={index}
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "flex-start",
              mb: 1.5,
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            {msg.role === "assistant" && (
              <SmartToyIcon
                sx={{
                  mr: 1,
                  mt: 0.5,
                  color: "primary.main",
                  fontSize: "1.25rem",
                }}
              />
            )}
            <Paper
              elevation={0} // Flatter look
              variant={msg.role === "user" ? "elevation" : "outlined"} // User messages elevated slightly, AI outlined
              sx={{
                p: theme.spacing(0.75, 1.25), // Adjusted padding
                maxWidth: "85%",
                bgcolor:
                  msg.role === "user"
                    ? alpha(theme.palette.primary.light, 0.25) // Softer user bubble
                    : theme.palette.background.default, // AI more integrated
                color: "text.primary",
                borderRadius:
                  msg.role === "user"
                    ? "10px 10px 2px 10px"
                    : "2px 10px 10px 10px",
                wordBreak: "break-word",
                border:
                  msg.role === "assistant"
                    ? `1px solid ${theme.palette.divider}`
                    : "none",
              }}
            >
              <Typography
                variant="body2" // Main content
                sx={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}
              >
                {typeof msg.content === "string"
                  ? msg.content
                  : (msg.content as AIResponseData).explanation}
              </Typography>
              {typeof msg.content !== "string" &&
                (msg.content as AIResponseData).actions &&
                (msg.content as AIResponseData).actions.length > 0 && (
                  <Box
                    sx={{
                      mt: 1,
                      pt: 0.5,
                      borderTop: `1px dashed ${theme.palette.divider}`,
                    }}
                  >
                    <Button
                      size="small"
                      onClick={() => toggleActionDetails(index)}
                      startIcon={<CodeIcon fontSize="inherit" />}
                      endIcon={
                        openActionDetails[index] ? (
                          <ExpandLessIcon fontSize="inherit" />
                        ) : (
                          <ExpandMoreIcon fontSize="inherit" />
                        )
                      }
                      variant="text"
                      sx={{
                        textTransform: "none",
                        color: "text.secondary",
                        fontSize: "0.75rem",
                        p: theme.spacing(0.25, 0.5),
                        "&:hover": {
                          bgcolor: alpha(theme.palette.action.active, 0.05),
                        },
                      }}
                    >
                      Show Raw Actions (
                      {(msg.content as AIResponseData).actions.length})
                    </Button>
                    <Collapse
                      in={openActionDetails[index]}
                      timeout="auto"
                      unmountOnExit
                    >
                      <Paper
                        elevation={0}
                        variant="outlined" // Consistent outlined style
                        sx={{
                          p: 1,
                          mt: 0.5,
                          bgcolor: alpha(
                            theme.palette.common.black,
                            theme.palette.mode === "dark" ? 0.2 : 0.03
                          ),
                          maxHeight: 180,
                          overflowY: "auto",
                          borderColor: "divider",
                          borderRadius: theme.shape.borderRadius * 0.5,
                        }}
                      >
                        <Typography
                          component="pre"
                          variant="caption"
                          sx={{
                            margin: 0,
                            fontSize: "0.7rem", // Smaller for dense JSON
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-all",
                            fontFamily: "monospace",
                            lineHeight: 1.4,
                            color: "text.secondary",
                          }}
                        >
                          {JSON.stringify(
                            (msg.content as AIResponseData).actions,
                            null,
                            2
                          )}
                        </Typography>
                      </Paper>
                    </Collapse>
                  </Box>
                )}
            </Paper>
            {msg.role === "user" && (
              <AccountCircleIcon
                sx={{
                  ml: 1,
                  mt: 0.5,
                  color: "text.secondary",
                  fontSize: "1.25rem",
                }}
              />
            )}
          </Box>
        ))}
        {isLoading &&
          chatMessages.length > 0 && ( // Show typing indicator if loading after some messages
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                p: 1,
                justifyContent: "flex-start",
              }}
            >
              <SmartToyIcon
                sx={{ mr: 1, color: "primary.main", fontSize: "1.25rem" }}
              />
              <CircularProgress size={18} color="primary" />
              <Typography
                variant="caption"
                sx={{ ml: 1, color: "text.secondary" }}
              >
                AI is thinking...
              </Typography>
            </Box>
          )}
      </Box>
      <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
        <TextField
          fullWidth
          multiline
          maxRows={5}
          variant="outlined"
          size="small"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Ask AI... (Shift+Enter for newline)"
          disabled={isLoading}
          aria-label="Chat input with AI"
          sx={{
            bgcolor: "background.paper",
            "& .MuiOutlinedInput-root": {
              paddingRight: "8px", // Make space for button if needed
            },
          }}
        />
        <Button
          variant="contained"
          onClick={onChatSubmit}
          disabled={isLoading || !userInput.trim()}
          aria-busy={isLoading && !!userInput.trim()}
          sx={{
            height: "40px", // Match TextField small size height
            minWidth: "40px", // More square for icon only
            p: "0 10px", // Padding for text or icon
          }}
          title="Send message"
        >
          {isLoading && userInput.trim() ? (
            <CircularProgress size={20} color="inherit" />
          ) : (
            <SendIcon fontSize="small" />
          )}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatPanel;
