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
  CircularProgress
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ClearAllIcon from "@mui/icons-material/ClearAll";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import CodeIcon from '@mui/icons-material/Code';

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

  useEffect(() => {
    const chatNode = chatMessagesRef.current;
    if (chatNode) {
      const scrollThreshold = 100;
      const isScrolledToBottom =
        chatNode.scrollHeight - chatNode.clientHeight <=
        chatNode.scrollTop + scrollThreshold;

      if (isScrolledToBottom) {
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
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography
          variant="h6"
          component="h2"
          sx={{ fontSize: "1.1rem" }}
        >
          AI Chat
        </Typography>
        <Button
          variant="outlined"
          size="small"
          onClick={onClearChat}
          disabled={isLoading || chatMessages.length === 0}
          startIcon={<ClearAllIcon />}
          title="Clear chat history"
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
          p: 1.5,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          bgcolor: "background.default",
        }}
      >
        {chatMessages.map((msg, index) => (
          <Paper
            key={index}
            elevation={1}
            sx={{
              p: 1.5,
              mb: 1.5,
              maxWidth: "90%",
              ml: msg.role === "user" ? "auto" : 0,
              mr: msg.role === "assistant" ? "auto" : 0,
              bgcolor:
                msg.role === "user"
                  ? "primary.main"
                  : "background.paper",
              color:
                msg.role === "user"
                  ? "primary.contrastText"
                  : "text.primary",
              borderRadius:
                msg.role === "user"
                  ? "12px 12px 2px 12px"
                  : "2px 12px 12px 12px",
              wordBreak: "break-word",
            }}
          >
            <Typography
              variant="caption"
              display="block"
              sx={{ fontWeight: "bold", mb: 0.5, opacity: 0.9 }}
            >
              {msg.role === "assistant" ? "AI" : "You"}:
            </Typography>
            {typeof msg.content === "string" ? (
              <Typography
                variant="body2"
                sx={{ whiteSpace: "pre-wrap" }}
              >
                {msg.content}
              </Typography>
            ) : (
              <Box>
                <Typography
                  variant="body2"
                  sx={{ whiteSpace: "pre-wrap" }}
                >
                  {(msg.content as AIResponseData).explanation}
                </Typography>
                {(msg.content as AIResponseData).actions &&
                  (msg.content as AIResponseData).actions.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Button
                        size="small"
                        onClick={() => toggleActionDetails(index)}
                        startIcon={<CodeIcon />}
                        endIcon={
                          openActionDetails[index] ? (
                            <ExpandLessIcon />
                          ) : (
                            <ExpandMoreIcon />
                          )
                        }
                        variant="text"
                        sx={{
                          textTransform: "none",
                          color:
                            msg.role === "user"
                              ? "primary.contrastText"
                              : "primary.main",
                          opacity: 0.85,
                          fontSize: '0.8rem',
                          p: '2px 8px'
                        }}
                      >
                        Show Actions ({(msg.content as AIResponseData).actions.length})
                      </Button>
                      <Collapse
                        in={openActionDetails[index]}
                        timeout="auto"
                        unmountOnExit
                      >
                        <Paper
                          elevation={0}
                          variant="outlined"
                          sx={{
                            p: 1,
                            mt: 0.5,
                            bgcolor: (theme) => theme.palette.mode === 'dark' ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
                            maxHeight: 180,
                            overflowY: "auto",
                            borderColor: 'divider',
                            borderRadius: 1
                          }}
                        >
                          <Typography
                            component="pre"
                            variant="caption"
                            sx={{
                              margin: 0,
                              fontSize: "0.75rem",
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-all",
                              fontFamily: 'monospace',
                              lineHeight: 1.5
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
              </Box>
            )}
          </Paper>
        ))}
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
          sx={{ bgcolor: "background.paper" }}
        />
        <Button
          variant="contained"
          onClick={onChatSubmit}
          disabled={isLoading || !userInput.trim()}
          aria-busy={isLoading && !!userInput.trim()}
          sx={{ height: "40px", minWidth: 'auto', p: '0 12px' }}
          title="Send message"
        >
          {isLoading && userInput.trim() ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatPanel;
