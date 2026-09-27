import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { BusFactorBadge } from '../components/BusFactorBadge';
import { FileTree } from '../components/FileTree';
import { WhyCardView } from '../components/WhyCardView';

/** The main screen: one file, fully explained (spec F5), with a tree sidebar. */
export function WhyCardPage() {
  const { repoId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const path = params.get('path');

  const tree = useQuery({ queryKey: ['tree', repoId], queryFn: () => api.tree(repoId) });
  const card = useQuery({
    queryKey: ['why', repoId, path],
    queryFn: () => api.why(repoId, path!),
    enabled: !!path,
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      <aside className="card max-h-[75vh] overflow-y-auto" aria-label="File tree">
        {tree.isLoading && (
          <div className="space-y-1.5 p-1">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton h-4" style={{ width: `${55 + (i % 4) * 10}%` }} />
            ))}
          </div>
        )}
        {tree.error && (
          <p className="text-sm text-red-600" role="alert">
            Could not load file tree: {(tree.error as Error).message}
          </p>
        )}
        {tree.data && (
          <FileTree
            node={tree.data}
            selected={path}
            onSelect={(p) => setParams({ path: p })}
          />
        )}
      </aside>
      <section>
        {!path && (
          <p className="text-gray-500">Pick a file from the tree to see its Why Card.</p>
        )}
        {card.isLoading && path && (
          <div className="space-y-4">
            <div className="skeleton h-6 w-2/3" />
            <div className="card space-y-2">
              <div className="skeleton h-4 w-1/3" />
              <div className="skeleton h-16 w-full" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="card"><div className="skeleton h-32 w-full" /></div>
              <div className="card"><div className="skeleton h-32 w-full" /></div>
            </div>
          </div>
        )}
        {card.error && (
          <div role="alert" className="card border-red-300 dark:border-red-800">
            <p className="font-medium text-red-700 dark:text-red-400">Failed to load Why Card</p>
            <p className="mt-1 text-sm text-red-600 dark:text-red-300">
              {(card.error as Error).message}
            </p>
          </div>
        )}
        {card.data && <WhyCardBody repoId={repoId} card={card.data} />}
      </section>
    </div>
  );
}

function WhyCardBody({ repoId, card }: { repoId: string; card: import('../api').WhyCard }) {
  const [copied, setCopied] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const copy = async (kind: 'markdown' | 'agent') => {
    const data =
      kind === 'markdown'
        ? (await api.whyMarkdown(repoId, card.path)).markdown
        : JSON.stringify(await api.whyAgent(repoId, card.path), null, 1);
    await navigator.clipboard.writeText(data);
    setCopied(kind);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <h1 className="break-all font-mono text-lg font-bold">{card.path}</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            {card.language ?? 'unknown language'} · {card.loc} LOC
            {card.is_entry_point && (
              <span className="ml-2 rounded bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-500/20 dark:text-brand-400">
                entry point
              </span>
            )}
          </p>
        </div>
        <BusFactorBadge busFactor={card.bus_factor} atRisk={card.at_risk} />
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="btn" onClick={() => copy('markdown')}>
          {copied === 'markdown' ? '✓ Copied' : 'Copy as Markdown'}
        </button>
        <button className="btn" onClick={() => copy('agent')}>
          {copied === 'agent' ? '✓ Copied' : 'Copy as agent context'}
        </button>
        <button className="btn" onClick={() => setShowForm(!showForm)} aria-expanded={showForm}>
          Add decision
        </button>
        <Link className="btn" to={`/repo/${repoId}/ask`}>
          Ask about this repo
        </Link>
      </div>

      {showForm && <AddDecisionForm repoId={repoId} path={card.path} onDone={() => setShowForm(false)} />}

      <WhyCardView card={card} />
    </div>
  );
}

function AddDecisionForm({
  repoId,
  path,
  onDone,
}: {
  repoId: string;
  path: string;
  onDone: () => void;
}) {
  const [title, setTitle] = useState('');
  const [reasoning, setReasoning] = useState('');
  const [alternatives, setAlternatives] = useState('');
  const queryClient = useQueryClient();

  const save = useMutation({
    mutationFn: () =>
      api.addDecision(repoId, {
        title,
        files: [path],
        reasoning,
        alternatives: alternatives || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['why', repoId, path] });
      onDone();
    },
  });

  return (
    <form
      className="card space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <h2 className="font-semibold">Record a decision for {path}</h2>
      <label className="block text-sm">
        Title (max 80 chars)
        <input
          className="input mt-1 w-full"
          maxLength={80}
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label className="block text-sm">
        Why (the reasoning)
        <textarea
          className="input mt-1 w-full"
          rows={3}
          required
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
        />
      </label>
      <label className="block text-sm">
        Alternatives considered (optional)
        <textarea
          className="input mt-1 w-full"
          rows={2}
          value={alternatives}
          onChange={(e) => setAlternatives(e.target.value)}
        />
      </label>
      <div className="flex gap-2">
        <button className="btn" type="submit" disabled={save.isPending}>
          Save decision
        </button>
        <button className="btn" type="button" onClick={onDone}>
          Cancel
        </button>
      </div>
      {save.error && (
        <p role="alert" className="text-sm text-red-600">
          {(save.error as Error).message}
        </p>
      )}
    </form>
  );
}
