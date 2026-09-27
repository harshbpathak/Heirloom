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
  loc: 100,
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
});
