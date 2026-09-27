import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import type { TreeNode } from '../api';
import { BusFactorMap } from '../components/BusFactorMap';

// jsdom has no canvas; stub the 2D context so drawing calls are no-ops.
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    fillText: vi.fn(),
    beginPath: vi.fn(),
    rect: vi.fn(),
    clip: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
  }) as unknown as typeof HTMLCanvasElement.prototype.getContext;
});

const tree: TreeNode = {
  name: '',
  type: 'dir',
  loc: 200,
  children: [
    {
      name: 'a.py',
      type: 'file',
      path: 'a.py',
      loc: 100,
      bus_factor: 1,
      at_risk: true,
      children: [],
    },
    {
      name: 'b.py',
      type: 'file',
      path: 'b.py',
      loc: 100,
      bus_factor: 1,
      at_risk: false,
      children: [],
    },
  ],
};

describe('BusFactorMap', () => {
  it('legend carries text labels for every color (not color alone)', () => {
    render(<BusFactorMap tree={tree} filterAuthor={null} onSelectFile={() => {}} />);
    expect(screen.getByText(/bus factor 1 \(red\)/)).toBeInTheDocument();
    expect(screen.getByText(/bus factor 2 \(amber\)/)).toBeInTheDocument();
    expect(screen.getByText(/bus factor 3\+ \(green\)/)).toBeInTheDocument();
    expect(screen.getByText(/not analyzed \(grey\)/)).toBeInTheDocument();
    expect(screen.getByText(/striped = at risk/)).toBeInTheDocument();
  });

  it('canvas has an accessible name', () => {
    render(<BusFactorMap tree={tree} filterAuthor={null} onSelectFile={() => {}} />);
    expect(screen.getByRole('img', { name: /Treemap of files/ })).toBeInTheDocument();
  });

  it('shows the "if this person left" note when filtering', () => {
    render(<BusFactorMap tree={tree} filterAuthor="Alice" onSelectFile={() => {}} />);
    expect(screen.getByText(/If Alice left/)).toBeInTheDocument();
  });

  it('renders a riskiest-files table with keyboard-accessible rows', () => {
    render(<BusFactorMap tree={tree} filterAuthor={null} onSelectFile={() => {}} />);
    // The details summary should be visible
    expect(screen.getByText(/Riskiest files/)).toBeInTheDocument();
    // Table rows have tabIndex 0
    const rows = screen.getAllByRole('row');
    const dataRows = rows.filter((r) => r.getAttribute('tabIndex') === '0');
    expect(dataRows.length).toBeGreaterThan(0);
  });

  it('calls onSelectFile when a riskiest-file table row is activated with Enter', () => {
    const onSelect = vi.fn();
    render(<BusFactorMap tree={tree} filterAuthor={null} onSelectFile={onSelect} />);
    // Open the details element so rows are accessible
    const summary = screen.getByText(/Riskiest files/);
    summary.click();
    const rows = screen.getAllByRole('row');
    const dataRow = rows.find((r) => r.getAttribute('tabIndex') === '0');
    if (dataRow) {
      dataRow.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    }
    expect(onSelect).toHaveBeenCalled();
  });
});
