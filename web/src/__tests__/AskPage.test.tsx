import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { AskPage } from '../pages/AskPage';

function renderAsk() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/repo/demo/ask']}>
        <Routes>
          <Route path="/repo/:repoId/ask" element={<AskPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AskPage', () => {
  it('shows the answer with citation links', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        answer: 'Redis keeps sessions across restarts [12].',
        citations: ['12'],
        route: 'decisions',
      }),
    }) as unknown as typeof fetch;

    renderAsk();
    fireEvent.change(screen.getByLabelText('Your question'), {
      target: { value: 'Why Redis?' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    await waitFor(() =>
      expect(screen.getByText(/Redis keeps sessions across restarts/)).toBeInTheDocument(),
    );
    expect(screen.getByRole('link', { name: '[12]' })).toBeInTheDocument();
  });

  it('surfaces API errors instead of inventing an answer', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: { code: 'repo_not_found', message: 'Repo missing' } }),
    }) as unknown as typeof fetch;

    renderAsk();
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Repo missing'));
  });
});
