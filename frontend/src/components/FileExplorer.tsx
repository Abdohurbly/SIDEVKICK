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
import FolderOpenIcon from "@mui/icons-material/FolderOpen";

interface FileExplorerProps {
  projectStructure: ProjectStructureNode | null;
  onFileSelect: (filePath: string) => void;
  selectedFilePath: string | null;
}

// Custom TreeItem to match VS Code's compact and subtle style
const StyledTreeItem = styled(
  (
    props: TreeItemProps & { selectedPath: string | null; currentPath: string }
  ) => {
    const { selectedPath, currentPath, ...other } = props;
    return <TreeItem {...other} />;
  }
)(({ theme, selectedPath, currentPath }) => ({
  [`& .${treeItemClasses.iconContainer}`]: {
    width: "auto",
    marginRight: theme.spacing(0.5), // Reduced space next to icon
    "& .close": {
      // Not sure what .close refers to here, kept for now
      opacity: 0.3,
    },
  },
  [`& .${treeItemClasses.group}`]: {
    marginLeft: theme.spacing(1.5), // 12px indent
    paddingLeft: theme.spacing(1.5), // 12px indent guide space
    borderLeft: `1px solid ${alpha(theme.palette.text.primary, 0.15)}`, // Subtler indent guide
  },
  [`& .${treeItemClasses.content}`]: {
    padding: theme.spacing(0.25, 1), // Compact padding (2px top/bottom, 8px left/right)
    borderRadius: theme.shape.borderRadius * 0.75, // Slightly less rounded
    minHeight: 28, // Ensure consistent item height
    "&:hover": {
      backgroundColor: theme.palette.action.hover,
    },
    "&.Mui-focused": {
      // Remove default focus ring if not desired, or style it
      backgroundColor: "transparent", // Or theme.palette.action.focus
    },
    "&.Mui-selected": {
      backgroundColor: alpha(
        theme.palette.primary.main,
        theme.palette.mode === "dark" ? 0.25 : 0.15
      ), // Selection color
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
        // Selected and focused
        backgroundColor: alpha(
          theme.palette.primary.main,
          theme.palette.mode === "dark" ? 0.3 : 0.2
        ),
      },
    },
  },
  [`& .${treeItemClasses.label}`]: {
    fontSize: "0.875rem", // VS Code like font size
    padding: 0,
    fontWeight: "inherit", // Handled by selected state
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
  level: number = 0
): React.ReactNode => {
  const isSelected =
    node.type === "file" && node.relative_path === selectedFilePath;

  return (
    <StyledTreeItem
      key={node.path}
      nodeId={node.relative_path} // Use relative_path for nodeId consistency with selection
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
              color: isSelected ? "inherit" : "text.secondary", // Icon color matches text or selection
            }}
          />
          <Typography
            variant="body2"
            sx={{
              fontSize: "0.875rem",
              fontWeight: isSelected ? 500 : 400,
              flexGrow: 1,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={node.name}
          >
            {node.name}
          </Typography>
        </Box>
      }
      onClick={(event) => {
        // Prevent toggle on label click if it's a directory, allow file selection
        if (node.type === "file") {
          onFileSelect(node.relative_path);
        } else {
          // Allow click on directory item to toggle, but not if clicking the expand icon area
          const target = event.target as HTMLElement;
          if (!target.closest(".MuiTreeItem-iconContainer")) {
            // Potentially toggle expand/collapse here if TreeView doesn't handle it for the whole content area.
            // Usually, TreeView handles this.
          }
        }
      }}
      selectedPath={selectedFilePath}
      currentPath={node.relative_path}
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
            return [...currentSearchPath, node.relative_path];
          }
          if (node.type === "directory" && node.children) {
            const found = findPathToNode(node.children, targetPath, [
              ...currentSearchPath,
              node.relative_path,
            ]);
            if (found) return found;
          }
        }
        return null;
      };

      const pathArray = findPathToNode(
        projectStructure.children || [],
        selectedFilePath
      );
      if (pathArray) {
        // We want to expand all parent directories, but not the file itself if it's a leaf.
        const directoriesToExpand = pathArray.slice(0, -1);
        setExpanded((prevExpanded) => {
          // Add to existing expanded nodes, don't replace, to keep user's manual expansions
          const newExpanded = new Set([
            ...prevExpanded,
            ...directoriesToExpand,
          ]);
          return Array.from(newExpanded);
        });
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
        overflowY: "hidden",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default",
      }}
    >
      <Typography
        variant="overline" // More subtle title like VS Code panels
        sx={{
          p: theme.spacing(1, 1.5, 0.5, 1.5),
          display: "block",
          color: "text.secondary",
          fontWeight: 500,
          fontSize: "0.7rem", // Smaller overline
          textTransform: "uppercase",
          borderBottom: `1px solid ${theme.palette.divider}`,
          mb: 0.5,
        }}
      >
        Project Explorer
      </Typography>
      {projectStructure.children && projectStructure.children.length > 0 ? (
        <TreeView
          aria-label="file system navigator"
          defaultCollapseIcon={<ExpandMoreIcon sx={{ fontSize: "1.2rem" }} />} // Adjusted icon size
          defaultExpandIcon={<ChevronRightIcon sx={{ fontSize: "1.2rem" }} />}
          expanded={expanded}
          selected={selectedFilePath || ""}
          onNodeToggle={handleToggle}
          sx={{
            flexGrow: 1,
            width: "100%",
            overflowY: "auto",
            p: theme.spacing(0, 0.5, 0.5, 0.5), // Padding around the tree
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
