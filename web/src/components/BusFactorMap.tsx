import * as d3 from 'd3';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TreeNode } from '../api';

/** Colors match the tailwind bus-factor scale; labels are always shown too. */
const COLORS: Record<string, string> = {
  bf1: '#dc2626',
  bf2: '#d97706',
  bf3: '#16a34a',
  na: '#6b7280',
  highlight: '#2563eb',
};

interface FileLeaf {
  name: string;
  path: string;
  loc: number;
  bus_factor?: number | null;
  at_risk?: boolean;
  holders?: { name: string; ownership: number }[];
}

function colorFor(node: FileLeaf, filterAuthor: string | null): string {
  if (filterAuthor) {
    const owns = node.holders?.some((h) => h.name === filterAuthor && h.ownership > 0.4);
    return owns ? COLORS.highlight : COLORS.na;
  }
  const bf = node.bus_factor;
  if (bf === null || bf === undefined || bf === 0) return COLORS.na;
  return bf === 1 ? COLORS.bf1 : bf === 2 ? COLORS.bf2 : COLORS.bf3;
}

/**
 * Zoomable bus-factor treemap (spec F6), canvas-rendered so large repos stay
 * smooth. Click a rectangle to open its Why Card; hover shows details.
 */
export function BusFactorMap({
  tree,
  filterAuthor,
  onSelectFile,
}: {
  tree: TreeNode;
  filterAuthor: string | null;
  onSelectFile: (path: string) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<FileLeaf | null>(null);
  const [zoomRoot, setZoomRoot] = useState<string | null>(null);
  const width = 900;
  const height = 520;

  const layout = useMemo(() => {
    let source: TreeNode = tree;
    if (zoomRoot) {
      const find = (n: TreeNode): TreeNode | null => {
        if (n.type === 'dir' && n.name === zoomRoot) return n;
        for (const c of n.children ?? []) {
          const hit = find(c);
          if (hit) return hit;
        }
        return null;
      };
      source = find(tree) ?? tree;
    }
    const hierarchy = d3
      .hierarchy(source, (d) => d.children)
      .sum((d) => (d.type === 'file' ? Math.max(d.loc, 1) : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    return d3.treemap<TreeNode>().size([width, height]).paddingInner(1).paddingTop(14)(hierarchy);
  }, [tree, zoomRoot]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    for (const node of layout.descendants()) {
      const d = node.data;
      const w = node.x1 - node.x0;
      const h = node.y1 - node.y0;
      if (d.type === 'dir' && node.depth > 0) {
        ctx.strokeStyle = '#9ca3af';
        ctx.strokeRect(node.x0, node.y0, w, h);
        if (w > 40 && h > 14) {
          ctx.fillStyle = '#6b7280';
          ctx.font = '10px sans-serif';
          ctx.fillText(d.name, node.x0 + 3, node.y0 + 10, w - 6);
        }
      }
      if (d.type !== 'file') continue;
      const leaf = d as unknown as FileLeaf;
      ctx.fillStyle = colorFor(leaf, filterAuthor);
      ctx.fillRect(node.x0, node.y0, w, h);
      if (leaf.at_risk && !filterAuthor && w > 6 && h > 6) {
        // Striped overlay marks "at risk" (pattern, not color alone).
        ctx.save();
        ctx.beginPath();
        ctx.rect(node.x0, node.y0, w, h);
        ctx.clip();
        ctx.strokeStyle = 'rgba(255,255,255,0.65)';
        ctx.lineWidth = 2;
        for (let x = node.x0 - h; x < node.x1; x += 7) {
          ctx.beginPath();
          ctx.moveTo(x, node.y1);
          ctx.lineTo(x + h, node.y0);
          ctx.stroke();
        }
        ctx.restore();
      }
      if (w > 60 && h > 16) {
        ctx.fillStyle = 'white';
        ctx.font = '10px sans-serif';
        ctx.fillText(leaf.name, node.x0 + 3, node.y0 + 12, w - 6);
      }
    }
  }, [layout, filterAuthor]);

  useEffect(() => draw(), [draw]);

  const leafAt = (evt: React.MouseEvent): FileLeaf | null => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = ((evt.clientX - rect.left) / rect.width) * width;
    const y = ((evt.clientY - rect.top) / rect.height) * height;
    for (const node of layout.leaves()) {
      if (x >= node.x0 && x <= node.x1 && y >= node.y0 && y <= node.y1) {
        return node.data.type === 'file' ? (node.data as unknown as FileLeaf) : null;
      }
    }
    return null;
  };

  const exportPng = () => {
    const url = canvasRef.current?.toDataURL('image/png');
    if (!url) return;
    const a = document.createElement('a');
    a.href = url;
    a.download = 'bus-factor-map.png';
    a.click();
  };

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-3 text-xs" aria-label="Legend">
        <Legend color={COLORS.bf1} label="bus factor 1 (red)" />
        <Legend color={COLORS.bf2} label="bus factor 2 (amber)" />
        <Legend color={COLORS.bf3} label="bus factor 3+ (green)" />
        <Legend color={COLORS.na} label="not analyzed (grey)" />
        <span className="text-gray-500">striped = at risk</span>
        {filterAuthor && (
          <span className="font-medium text-blue-600 dark:text-blue-400">
            “If {filterAuthor} left”: blue = they own &gt;40%
          </span>
        )}
        <span className="ml-auto flex gap-2">
          {zoomRoot && (
            <button className="btn" onClick={() => setZoomRoot(null)}>
              ⤴ Zoom out
            </button>
          )}
          <button className="btn" onClick={exportPng}>
            Export PNG
          </button>
        </span>
      </div>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        role="img"
        aria-label="Treemap of files sized by lines of code and colored by bus factor"
        className="w-full cursor-pointer rounded border border-gray-200 dark:border-gray-800"
        onMouseMove={(e) => setHover(leafAt(e))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const leaf = leafAt(e);
          if (leaf) onSelectFile(leaf.path);
        }}
        onDoubleClick={(e) => {
          const leaf = leafAt(e);
          if (leaf) setZoomRoot(leaf.path.split('/')[0] ?? null);
        }}
      />
      <div className="mt-1 min-h-[1.5rem] text-xs text-gray-600 dark:text-gray-300" aria-live="polite">
        {hover ? (
          <>
            <strong>{hover.path}</strong> · {hover.loc} LOC · bus factor{' '}
            {hover.bus_factor ?? 'unknown'}
            {hover.at_risk ? ' · AT RISK' : ''}
            {hover.holders?.[0] &&
              ` · top owner ${hover.holders[0].name} (${Math.round(hover.holders[0].ownership * 100)}%)`}
          </>
        ) : (
          'Hover a rectangle for details; click to open its Why Card; double-click to zoom into a top-level folder.'
        )}
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: color }} aria-hidden />
      {label}
    </span>
  );
}
