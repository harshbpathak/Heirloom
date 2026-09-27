import * as d3 from 'd3';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TreeNode } from '../api';

/** Colors match the tailwind bus-factor scale; labels are always shown too. */
const COLORS: Record<string, string> = {
  bf1: '#c92a2a',
  bf2: '#e67700',
  bf3: '#2f9e44',
  na: '#868e96',
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
  const containerRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<FileLeaf | null>(null);
  // tooltip position in pixels relative to container
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
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

  /** Collect riskiest files for the accessible table. */
  const riskiestFiles = useMemo(() => {
    return layout
      .leaves()
      .filter((n) => n.data.type === 'file')
      .map((n) => n.data as unknown as FileLeaf)
      .filter((f) => f.bus_factor === 1 || f.at_risk)
      .sort((a, b) => {
        const riskA = a.at_risk ? 0 : 1;
        const riskB = b.at_risk ? 0 : 1;
        if (riskA !== riskB) return riskA - riskB;
        return (b.loc ?? 0) - (a.loc ?? 0);
      })
      .slice(0, 10);
  }, [layout]);

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
          ctx.font = '10px Inter, sans-serif';
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
        ctx.font = '10px Inter, sans-serif';
        ctx.fillText(leaf.name, node.x0 + 3, node.y0 + 12, w - 6);
      }
    }
  }, [layout, filterAuthor]);

  useEffect(() => draw(), [draw]);

  const leafAt = (evt: React.MouseEvent): { leaf: FileLeaf; canvasX: number; canvasY: number } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const x = (evt.clientX - rect.left) * scaleX;
    const y = (evt.clientY - rect.top) * scaleY;
    for (const node of layout.leaves()) {
      if (x >= node.x0 && x <= node.x1 && y >= node.y0 && y <= node.y1) {
        if (node.data.type !== 'file') return null;
        return {
          leaf: node.data as unknown as FileLeaf,
          // position relative to container div in CSS pixels
          canvasX: evt.clientX - rect.left,
          canvasY: evt.clientY - rect.top,
        };
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
          <span className="font-medium text-brand-600 dark:text-brand-500">
            If {filterAuthor} left: blue = they own &gt;40%
          </span>
        )}
        <span className="ml-auto flex gap-2">
          {zoomRoot && (
            <button className="btn" onClick={() => setZoomRoot(null)}>
              ↩ Zoom out
            </button>
          )}
          <button className="btn" onClick={exportPng}>
            Export PNG
          </button>
        </span>
      </div>

      {/* Canvas wrapped in a relative container so the tooltip can be positioned */}
      <div ref={containerRef} className="relative">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          role="img"
          aria-label="Treemap of files sized by lines of code and colored by bus factor"
          className="w-full cursor-pointer rounded-lg border border-gray-200 dark:border-gray-800"
          onMouseMove={(e) => {
            const hit = leafAt(e);
            if (hit) {
              setHover(hit.leaf);
              setTooltipPos({ x: hit.canvasX, y: hit.canvasY });
            } else {
              setHover(null);
              setTooltipPos(null);
            }
          }}
          onMouseLeave={() => {
            setHover(null);
            setTooltipPos(null);
          }}
          onClick={(e) => {
            const hit = leafAt(e);
            if (hit) onSelectFile(hit.leaf.path);
          }}
          onDoubleClick={(e) => {
            const hit = leafAt(e);
            if (hit) setZoomRoot(hit.leaf.path.split('/')[0] ?? null);
          }}
        />

        {/* Floating cursor tooltip */}
        {hover && tooltipPos && (
          <div
            role="tooltip"
            className="pointer-events-none absolute z-10 max-w-[260px] rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs shadow-lg dark:border-gray-700 dark:bg-gray-900"
            style={{
              left: Math.min(tooltipPos.x + 12, (containerRef.current?.offsetWidth ?? 900) - 270),
              top: Math.max(tooltipPos.y - 48, 4),
            }}
          >
            <p className="font-mono font-medium">{hover.path}</p>
            <p className="mt-0.5 text-gray-500">
              {hover.loc} LOC · bus factor {hover.bus_factor ?? 'unknown'}
              {hover.at_risk ? ' · AT RISK' : ''}
            </p>
            {hover.holders?.[0] && (
              <p className="text-gray-500">
                top owner {hover.holders[0].name} ({Math.round(hover.holders[0].ownership * 100)}%)
              </p>
            )}
          </div>
        )}
      </div>

      {/* Keyboard-accessible table of the riskiest files */}
      {riskiestFiles.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200">
            Riskiest files ({riskiestFiles.length} shown)
          </summary>
          <div className="mt-2 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200 text-left dark:border-gray-800">
                  <th className="px-3 py-1.5 font-medium">File</th>
                  <th className="px-3 py-1.5 font-medium">LOC</th>
                  <th className="px-3 py-1.5 font-medium">Bus factor</th>
                  <th className="px-3 py-1.5 font-medium">Status</th>
                  <th className="px-3 py-1.5 font-medium">Top owner</th>
                </tr>
              </thead>
              <tbody>
                {riskiestFiles.map((f) => (
                  <tr
                    key={f.path}
                    tabIndex={0}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 focus-visible:bg-brand-50 dark:border-gray-800 dark:hover:bg-gray-800 dark:focus-visible:bg-brand-500/10"
                    onClick={() => onSelectFile(f.path)}
                    onKeyDown={(e) => e.key === 'Enter' && onSelectFile(f.path)}
                  >
                    <td className="px-3 py-1.5 font-mono">{f.path}</td>
                    <td className="px-3 py-1.5">{f.loc}</td>
                    <td className="px-3 py-1.5">
                      <span
                        className="rounded px-1.5 py-0.5 text-white"
                        style={{ backgroundColor: colorFor(f, null) }}
                      >
                        {f.bus_factor ?? '?'}
                      </span>
                    </td>
                    <td className="px-3 py-1.5">
                      {f.at_risk ? (
                        <span className="font-semibold text-bf1">AT RISK</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-gray-500">
                      {f.holders?.[0]
                        ? `${f.holders[0].name} (${Math.round(f.holders[0].ownership * 100)}%)`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
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
