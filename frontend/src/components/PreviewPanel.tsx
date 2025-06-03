import React from "react";
import {
  Box,
  Paper,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  IconButton,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { PreviewDevice } from "../types";

interface PreviewPanelProps {
  previewUrl: string;
  setPreviewUrl: (url: string) => void;
  previewDevice: PreviewDevice;
  setPreviewDevice: (device: PreviewDevice) => void;
  isLoading: boolean;
}

const deviceDimensions: Record<
  PreviewDevice,
  { width: string; height: string }
> = {
  desktop: { width: "100%", height: "100%" },
  tablet: { width: "768px", height: "1024px" },
  mobile: { width: "375px", height: "812px" }, // iPhone X/XS/11 Pro dimensions
};

const PreviewPanel: React.FC<PreviewPanelProps> = ({
  previewUrl,
  setPreviewUrl,
  previewDevice,
  setPreviewDevice,
  isLoading,
}) => {
  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  const handleDeviceChange = (
    event: React.MouseEvent<HTMLElement>,
    newDevice: PreviewDevice | null
  ) => {
    if (newDevice) {
      setPreviewDevice(newDevice);
    }
  };

  const handleRefresh = () => {
    if (iframeRef.current) {
      iframeRef.current.src = previewUrl; // Re-assigning src to refresh
    }
  };

  const currentDimensions = deviceDimensions[previewDevice];

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
          alignItems: "center",
          gap: 2,
          mb: 1,
          flexWrap: "wrap",
        }}
      >
        <TextField
          label="Preview URL"
          variant="outlined"
          size="small"
          value={previewUrl}
          onChange={(e) => setPreviewUrl(e.target.value)}
          disabled={isLoading}
          sx={{ flexGrow: 1, minWidth: "250px" }}
        />
        <IconButton
          onClick={handleRefresh}
          disabled={isLoading}
          title="Refresh Preview"
        >
          <RefreshIcon />
        </IconButton>
        <ToggleButtonGroup
          value={previewDevice}
          exclusive
          onChange={handleDeviceChange}
          aria-label="Preview device type"
          size="small"
          disabled={isLoading}
        >
          <ToggleButton
            value="desktop"
            aria-label="Desktop view"
            title="Desktop View"
          >
            <RefreshIcon />
          </ToggleButton>
          <ToggleButton
            value="tablet"
            aria-label="Tablet view"
            title="Tablet View"
          >
            <RefreshIcon />
          </ToggleButton>
          <ToggleButton
            value="mobile"
            aria-label="Mobile view"
            title="Mobile View"
          >
            <RefreshIcon />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Paper
        variant="outlined"
        sx={{
          flexGrow: 1,
          overflow: "hidden",
          borderColor: "divider",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          p: previewDevice === "desktop" ? 0 : 2,
          bgcolor: previewDevice === "desktop" ? "transparent" : "action.hover",
        }}
      >
        <Box
          component="iframe"
          ref={iframeRef}
          src={previewUrl}
          title="Website Preview"
          sx={{
            width: currentDimensions.width,
            height: currentDimensions.height,
            border:
              previewDevice === "desktop"
                ? "none"
                : (theme) => `1px solid ${theme.palette.divider}`,
            boxShadow: previewDevice === "desktop" ? "none" : 3,
            bgcolor: "background.paper",
            transition: "width 0.3s ease-in-out, height 0.3s ease-in-out",
          }}
        />
      </Paper>
    </Box>
  );
};

export default PreviewPanel;
