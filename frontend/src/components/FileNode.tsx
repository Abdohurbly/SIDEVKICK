import React from "react";
import { ProjectStructureNode } from "../types";

interface FileNodeProps {
  node: ProjectStructureNode;
  onFileSelect: (filePath: string) => void;
  level?: number;
}

const FileNode: React.FC<FileNodeProps> = ({
  node,
  onFileSelect,
  level = 0,
}) => {
  const [isOpen, setIsOpen] = React.useState(false);

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent file selection if clicking on folder toggle
    if (node.type === "directory") {
      setIsOpen(!isOpen);
    }
  };

  const handleFileClick = () => {
    if (node.type === "file") {
      onFileSelect(node.relative_path);
    }
  };

  const indentStyle = { paddingLeft: `${level * 20}px` };

  return (
    <li>
      <div
        onClick={node.type === "file" ? handleFileClick : handleToggle}
        style={{ ...indentStyle, cursor: "pointer" }}
        className={`file-node ${node.type}`}
        title={node.relative_path}
      >
        {node.type === "directory" && (isOpen ? "📂 " : "📁 ")}
        {node.type === "file" && "📄 "}
        {node.name}
      </div>
      {node.type === "directory" &&
        isOpen &&
        node.children &&
        node.children.length > 0 && (
          <ul>
            {node.children.map((child) => (
              <FileNode
                key={child.path}
                node={child}
                onFileSelect={onFileSelect}
                level={level + 1}
              />
            ))}
          </ul>
        )}
    </li>
  );
};

export default FileNode;
