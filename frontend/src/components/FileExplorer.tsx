import React from "react";
import { ProjectStructureNode } from "../types";
import { Box, Typography, CircularProgress } from "@mui/material";
import TreeView from "@mui/lab/TreeView";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import TreeItem, { TreeItemProps, treeItemClasses } from "@mui/lab/TreeItem";
import { styled, alpha } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";

interface FileExplorerProps {
  projectStructure: ProjectStructureNode | null;
  onFileSelect: (filePath: string) => void;
  selectedFilePath: string | null;
}

const StyledTreeItem = styled((props: TreeItemProps) => (
  <TreeItem {...props} />
))(({ theme }) => ({
  [`& .${treeItemClasses.iconContainer}`]: {
    "& .close": {
      opacity: 0.3,
    },
  },
  [`& .${treeItemClasses.group}`]: {
    marginLeft: 15,
    paddingLeft: 10,
    borderLeft: `1px dashed ${alpha(theme.palette.text.primary, 0.2)}`,
  },
  [`& .${treeItemClasses.label}`]: {
    fontSize: "0.95rem",
    padding: theme.spacing(0.5, 0),
  },
  [`& .${treeItemClasses.root}.${treeItemClasses.selected} > .${treeItemClasses.content}`]:
    {
      backgroundColor: alpha(theme.palette.primary.main, 0.2),
      color: theme.palette.primary.main,
      fontWeight: theme.typography.fontWeightMedium,
      "&:hover": {
        backgroundColor: alpha(theme.palette.primary.main, 0.3),
      },
    },
  [`& .${treeItemClasses.content}`]: {
    padding: theme.spacing(0.5, 1),
    borderRadius: theme.shape.borderRadius,
    "&:hover": {
      backgroundColor: theme.palette.action.hover,
    },
  },
}));

const renderTree = (
  node: ProjectStructureNode,
  onFileSelect: (filePath: string) => void,
  selectedFilePath: string | null
): React.ReactNode => {
  const isSelected =
    node.type === "file" && node.relative_path === selectedFilePath;
  return (
    <StyledTreeItem
      key={node.path}
      nodeId={node.path} // Use absolute path as nodeId for uniqueness
      label={node.name}
      onClick={() => {
        if (node.type === "file") {
          onFileSelect(node.relative_path);
        }
      }}
      icon={
        node.type === "directory" ? (
          <FolderIcon sx={{ fontSize: "1.2rem" }} />
        ) : (
          <InsertDriveFileIcon sx={{ fontSize: "1.1rem" }} />
        )
      }
      sx={{
        color: isSelected ? "primary.main" : "text.primary",
        fontWeight: isSelected ? "fontWeightBold" : "fontWeightRegular",
        backgroundColor: isSelected
          ? (theme) => alpha(theme.palette.primary.main, 0.12)
          : "transparent",
        "&:hover > .MuiTreeItem-content": {
          backgroundColor: (theme) => theme.palette.action.hover,
        },
        ".MuiTreeItem-label": {
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        },
      }}
    >
      {Array.isArray(node.children)
        ? node.children.map((childNode) =>
            renderTree(childNode, onFileSelect, selectedFilePath)
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
  if (!projectStructure) {
    return (
      <Box sx={{ p: 2, textAlign: "center" }}>
        <Typography variant="h6" gutterBottom>
          File Explorer
        </Typography>
        <CircularProgress size={24} sx={{ mr: 1 }} />
        <Typography variant="body2" color="text.secondary">
          Loading structure...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 1, height: "100%", overflowY: "auto" }}>
      <Typography
        variant="h6"
        gutterBottom
        sx={{ pl: 1, pt: 1, fontSize: "1.1rem" }}
      >
        Project Explorer
      </Typography>
      {projectStructure.children && projectStructure.children.length > 0 ? (
        <TreeView
          aria-label="file system navigator"
          defaultCollapseIcon={<ExpandMoreIcon />}
          defaultExpandIcon={<ChevronRightIcon />}
          sx={{ flexGrow: 1, width: "100%", overflowY: "auto" }}
          selected={
            selectedFilePath
              ? projectStructure.children.find(
                  (c) => c.relative_path === selectedFilePath
                )?.path
              : ""
          }
        >
          {projectStructure.children.map((node) =>
            renderTree(node, onFileSelect, selectedFilePath)
          )}
        </TreeView>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
          Project is empty or contains no viewable files/folders.
        </Typography>
      )}
    </Box>
  );
};

export default FileExplorer;
