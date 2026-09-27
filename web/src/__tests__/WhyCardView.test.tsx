import { render, screen } from '@testing-library/react';
import type { WhyCard } from '../api';
import { WhyCardView } from '../components/WhyCardView';

const card: WhyCard = {
  path: 'src/auth/session.ts',
  language: 'typescript',
  loc: 214,
  is_entry_point: false,
  summary: 'Stores sessions in Redis.',
  summary_source: 'comment',
  decisions: [
    {
      id: '7',
      title: 'Use Redis for session storage',
      reasoning: 'Sessions must survive restarts.',
      confidence: 'high',
      date: '2026-09-27',
      evidence: [{ type: 'commit', ref: 'abc123', url: 'https://example.com/c/abc123' }],
    },
  ],
  holders: [{ name: 'Alice Chen', ownership: 0.62, last_active: '2026-08-01', inactive: false }],
  bus_factor: 1,
  at_risk: true,
  impact: [{ path: 'src/app.ts', score: 0.8, reason: 'imports this file directly' }],
  warnings: [{ line: 42, text: 'DO NOT switch to in-memory sessions' }],
  activity: [{ month: '2026-01', commits: 3 }],
};

describe('WhyCardView', () => {
  it('renders every section of the Why Card', () => {
    render(<WhyCardView card={card} />);
    expect(screen.getByText(/What this file does/)).toBeInTheDocument();
    expect(screen.getByText('Stores sessions in Redis.')).toBeInTheDocument();
    expect(screen.getByText('Why it is like this')).toBeInTheDocument();
    expect(screen.getByText('Use Redis for session storage')).toBeInTheDocument();
    expect(screen.getByText('Knowledge holders')).toBeInTheDocument();
    expect(screen.getByText('Alice Chen')).toBeInTheDocument();
    expect(screen.getByText('Impact if changed')).toBeInTheDocument();
    expect(screen.getByText('src/app.ts')).toBeInTheDocument();
    expect(screen.getByText(/DO NOT switch/)).toBeInTheDocument();
  });

  it('shows evidence as a clickable link', () => {
    render(<WhyCardView card={card} />);
    const link = screen.getByRole('link', { name: /commit:abc123/ });
    expect(link).toHaveAttribute('href', 'https://example.com/c/abc123');
  });

  it('labels confidence with text, not color alone', () => {
    render(<WhyCardView card={card} />);
    expect(screen.getByText('confidence: high')).toBeInTheDocument();
  });

  it('says unknown instead of inventing holders', () => {
    render(<WhyCardView card={{ ...card, holders: [] }} />);
    expect(screen.getByText(/unknown \(no blame data/)).toBeInTheDocument();
  });

  it('shows initials badge for each holder', () => {
    render(<WhyCardView card={card} />);
    // InitialsBadge renders "AC" for "Alice Chen"
    expect(screen.getByLabelText('Alice Chen')).toBeInTheDocument();
    expect(screen.getByLabelText('Alice Chen').textContent).toBe('AC');
  });

  it('renders score bar for each impact item', () => {
    render(<WhyCardView card={card} />);
    // role="meter" for the score bar
    const meters = screen.getAllByRole('meter');
    // At least one meter for impact score
    const impactMeter = meters.find((m) => m.getAttribute('aria-label')?.startsWith('Impact score'));
    expect(impactMeter).toBeTruthy();
  });

  it('renders activity chart when activity data is present', () => {
    render(<WhyCardView card={card} />);
    expect(screen.getByRole('img', { name: /Commits per month/ })).toBeInTheDocument();
  });

  it('omits activity chart when activity is empty', () => {
    render(<WhyCardView card={{ ...card, activity: [] }} />);
    expect(screen.queryByRole('img', { name: /Commits per month/ })).not.toBeInTheDocument();
  });
});
