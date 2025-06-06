import React, { useEffect } from "react";
import { ProjectStructureNode } from "../types";
import {
  Box,
  Typography,
  CircularProgress,
  useTheme,
  alpha,
} from "@mui/material";
import TreeView from "@mui/lab/TreeView";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import TreeItem, { TreeItemProps, treeItemClasses } from "@mui/lab/TreeItem";
import { styled } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined"; // Outlined version for cleaner look
// import FolderOpenIcon from "@mui/icons-material/FolderOpen"; // Not directly used, TreeView handles open/close icons

interface FileExplorerProps {
  projectStructure: ProjectStructureNode | null;
  onFileSelect: (filePath: string) => void;
  selectedFilePath: string | null;
}

// Custom TreeItem to match VS Code's compact and subtle style
const StyledTreeItem = styled(
  (
    props: TreeItemProps & { isItemSelected: boolean } // Added isItemSelected
  ) => {
    const { isItemSelected, ...other } = props; // Destructure isItemSelected
    return <TreeItem {...other} />;
  }
)(({ theme, isItemSelected }) => ({
  // Use isItemSelected here
  [`& .${treeItemClasses.iconContainer}`]: {
    width: "auto",
    marginRight: theme.spacing(0.5),
    "& .close": {
      opacity: 0.3,
    },
  },
  [`& .${treeItemClasses.group}`]: {
    marginLeft: theme.spacing(1.5),
    paddingLeft: theme.spacing(1.5),
    borderLeft: `1px solid ${alpha(theme.palette.text.primary, 0.15)}`,
  },
  [`& .${treeItemClasses.content}`]: {
    padding: theme.spacing(0.25, 1),
    borderRadius: theme.shape.borderRadius * 0.75,
    minHeight: 28, // Ensure consistent item height
    color: isItemSelected // Apply selected color to content text
      ? theme.palette.mode === "dark"
        ? theme.palette.primary.light
        : theme.palette.primary.dark
      : "inherit",
    "&:hover": {
      backgroundColor: theme.palette.action.hover,
    },
    "&.Mui-focused": {
      backgroundColor: "transparent",
    },
    "&.Mui-selected": {
      backgroundColor: alpha(
        theme.palette.primary.main,
        theme.palette.mode === "dark" ? 0.25 : 0.15
      ),
      // This ensures the text inside the selected item is contrasted
      color:
        theme.palette.mode === "dark"
          ? theme.palette.primary.light
          : theme.palette.primary.dark,
      "&:hover": {
        backgroundColor: alpha(
          theme.palette.primary.main,
          theme.palette.mode === "dark" ? 0.35 : 0.25
        ),
      },
      "&.Mui-focused": {
        backgroundColor: alpha(
          theme.palette.primary.main,
          theme.palette.mode === "dark" ? 0.3 : 0.2
        ),
      },
    },
  },
  [`& .${treeItemClasses.label}`]: {
    fontSize: "0.875rem",
    padding: 0,
    fontWeight: "inherit",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    display: "flex",
    alignItems: "center",
  },
}));

const renderTree = (
  node: ProjectStructureNode,
  onFileSelect: (filePath: string) => void,
  selectedFilePath: string | null,
  level: number = 0 // level can be used for aria attributes if needed
): React.ReactNode => {
  const isSelected =
    node.type === "file" && node.relative_path === selectedFilePath;

  return (
    <StyledTreeItem
      key={node.path} // Use absolute path for key as it's guaranteed unique
      nodeId={node.relative_path} // Use relative_path for nodeId for selection logic
      isItemSelected={isSelected} // Pass selection state to StyledTreeItem
      label={
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            width: "100%",
            overflow: "hidden",
          }}
        >
          <Box
            component={
              node.type === "directory"
                ? FolderIcon
                : InsertDriveFileOutlinedIcon
            }
            sx={{
              fontSize: "1.1rem",
              mr: 0.75,
              // Icon color should also change when selected
              color: isSelected
                ? "inherit" // Inherits from StyledTreeItem's content color
                : "text.secondary",
            }}
          />
          <Typography
            variant="body2"
            sx={{
              fontSize: "0.875rem",
              fontWeight: isSelected ? 500 : 400, // Emphasize selected file name
              flexGrow: 1,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              // Text color is handled by StyledTreeItem's content color on selection
            }}
            title={node.name} // Show full name on hover
          >
            {node.name}
          </Typography>
        </Box>
      }
      onClick={(event: React.MouseEvent) => {
        if (node.type === "file") {
          onFileSelect(node.relative_path);
        } else {
          // For directories, MUI TreeView handles expand/collapse on the entire content area by default.
          // No explicit toggle needed here unless specific behavior is desired.
        }
      }}
    >
      {Array.isArray(node.children)
        ? node.children.map((childNode) =>
            renderTree(childNode, onFileSelect, selectedFilePath, level + 1)
          )
        : null}
    </StyledTreeItem>
  );
};

const FileExplorer: React.FC<FileExplorerProps> = ({
  projectStructure,
  onFileSelect,
  selectedFilePath,
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = React.useState<string[]>([]);

  const handleToggle = (event: React.SyntheticEvent, nodeIds: string[]) => {
    setExpanded(nodeIds);
  };

  // Expand parent directories of the selected file
  useEffect(() => {
    if (selectedFilePath && projectStructure) {
      const findPathToNode = (
        nodes: ProjectStructureNode[],
        targetPath: string,
        currentSearchPath: string[] = []
      ): string[] | null => {
        for (const node of nodes) {
          if (node.relative_path === targetPath) {
            // Path to file itself, parents are currentSearchPath
            return currentSearchPath;
          }
          if (node.type === "directory" && node.children) {
            const found = findPathToNode(node.children, targetPath, [
              ...currentSearchPath,
              node.relative_path, // Add current directory to path
            ]);
            if (found) return found;
          }
        }
        return null;
      };

      // Find path to the *parent* of the selected file, then expand those
      const pathArray = projectStructure.children
        ? findPathToNode(projectStructure.children, selectedFilePath)
        : null;

      if (pathArray && pathArray.length > 0) {
        setExpanded((prevExpanded) => {
          const newExpanded = new Set([...prevExpanded, ...pathArray]);
          return Array.from(newExpanded);
        });
      } else if (pathArray && pathArray.length === 0 && selectedFilePath) {
        // This means the selected file is at the root of the children list.
        // No parents to expand other than possibly the root project node (if it were expandable).
        // If projectStructure itself represents the root, then no expansion needed here for root files.
      }
    }
  }, [selectedFilePath, projectStructure]);

  if (!projectStructure) {
    return (
      <Box
        sx={{
          p: 2,
          textAlign: "center",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <CircularProgress size={24} sx={{ mb: 1 }} />
        <Typography variant="caption" color="text.secondary">
          Loading project...
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: "100%",
        overflowY: "hidden", // Outer box manages flex, TreeView handles its own scroll
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default", // Use theme default background
      }}
    >
      <Typography
        variant="overline"
        sx={{
          p: theme.spacing(1, 1.5, 0.5, 1.5), // Consistent padding
          display: "block",
          color: "text.secondary",
          fontWeight: 500,
          fontSize: "0.7rem",
          textTransform: "uppercase",
          borderBottom: `1px solid ${theme.palette.divider}`,
          mb: 0.5, // Space before TreeView
        }}
      >
        Project Explorer
      </Typography>
      {projectStructure.children && projectStructure.children.length > 0 ? (
        <TreeView
          aria-label="file system navigator"
          defaultCollapseIcon={<ExpandMoreIcon sx={{ fontSize: "1.1rem" }} />} // Slightly smaller icons
          defaultExpandIcon={<ChevronRightIcon sx={{ fontSize: "1.1rem" }} />}
          expanded={expanded}
          selected={selectedFilePath || ""} // Ensure selected prop is managed
          onNodeToggle={handleToggle}
          // onNodeSelect is not needed if onClick on TreeItem handles file selection.
          // If you want TreeView to manage selection state based on nodeId, use onNodeSelect.
          // For direct file selection, onClick on TreeItem is fine.
          sx={{
            flexGrow: 1,
            width: "100%",
            overflowY: "auto", // Allow TreeView to scroll its content
            p: theme.spacing(0, 0.5, 0.5, 0.5),
          }}
        >
          {projectStructure.children.map((node) =>
            renderTree(node, onFileSelect, selectedFilePath)
          )}
        </TreeView>
      ) : (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ p: 2, textAlign: "center", mt: 2 }}
        >
          Project is empty or no viewable files.
        </Typography>
      )}
    </Box>
  );
};

export default FileExplorer;
