import { useState } from 'react';
import type { TreeNode } from '../api';

/** Collapsible file-tree sidebar used on the Why Card page. */
export function FileTree({
  node,
  selected,
  onSelect,
  depth = 0,
}: {
  node: TreeNode;
  selected: string | null;
  onSelect: (path: string) => void;
  depth?: number;
}) {
  if (node.type === 'file') {
    const isSelected = node.path === selected;
    return (
      <button
        onClick={() => node.path && onSelect(node.path)}
        className={`block w-full truncate rounded px-2 py-0.5 text-left text-sm ${
          isSelected
            ? 'bg-blue-100 font-medium dark:bg-blue-950'
            : 'hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        title={node.path}
      >
        {node.at_risk ? '⚠ ' : ''}
        {node.name}
      </button>
    );
  }
  return <DirNode node={node} selected={selected} onSelect={onSelect} depth={depth} />;
}

function DirNode({
  node,
  selected,
  onSelect,
  depth,
}: {
  node: TreeNode;
  selected: string | null;
  onSelect: (path: string) => void;
  depth: number;
}) {
  const [open, setOpen] = useState(depth < 2);
  const isRoot = node.name === '';
  return (
    <div>
      {!isRoot && (
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="block w-full truncate rounded px-2 py-0.5 text-left text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {open ? '▾' : '▸'} {node.name}/
        </button>
      )}
      {(open || isRoot) &&
        node.children?.map((c) => (
          <FileTree
            key={c.path ?? c.name}
            node={c}
            selected={selected}
            onSelect={onSelect}
            depth={isRoot ? depth : depth + 1}
          />
        ))}
    </div>
  );
}
