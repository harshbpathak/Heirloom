import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import type { CompactDecision } from '../api';
import { api } from '../api';

/** Filterable decisions table (spec §9.2 page 6) with a detail panel. */
export function DecisionsPage() {
  const { repoId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const idParam = params.get('id');
  const [picked, setSelected] = useState<CompactDecision | null>(null);

  const decisions = useQuery({
    queryKey: ['decisions', repoId, q],
    queryFn: () => api.decisions(repoId, { q: q || undefined }),
  });
  // A citation link (?id=N) preselects that decision until the user picks another.
  const selected =
    picked ?? decisions.data?.items.find((d) => d.id === idParam) ?? null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold">Decisions</h1>
        <span className="text-sm text-gray-500">{decisions.data?.total ?? '…'} total</span>
        <form
          className="ml-auto flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const value = new FormData(e.currentTarget).get('q') as string;
            setParams(value ? { q: value } : {});
          }}
        >
          <label htmlFor="q" className="sr-only">
            Filter decisions
          </label>
          <input id="q" name="q" className="input" placeholder="Filter…" defaultValue={q} />
          <button className="btn" type="submit">
            Filter
          </button>
        </form>
      </div>

      {decisions.isLoading && (
        <div className="card space-y-2 p-3" aria-busy="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-8 w-full" />
          ))}
        </div>
      )}
      {decisions.error && (
        <div role="alert" className="card border-red-300 dark:border-red-800">
          <p className="font-medium text-red-700 dark:text-red-400">Failed to load decisions</p>
          <p className="mt-1 text-sm text-red-600">{(decisions.error as Error).message}</p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left dark:border-gray-800">
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Confidence</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {decisions.data?.items.map((d) => (
                <tr
                  key={d.id}
                  className={`cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800 ${
                    selected?.id === d.id ? 'bg-brand-50 dark:bg-brand-500/10' : ''
                  }`}
                  onClick={() => setSelected(d)}
                >
                  <td className="px-3 py-2">
                    <button className="text-left hover:underline">{d.title}</button>
                  </td>
                  <td className="px-3 py-2">{d.confidence}</td>
                  <td className="px-3 py-2">{d.source ?? 'extracted'}</td>
                  <td className="px-3 py-2 text-gray-500">{d.date ?? 'unknown'}</td>
                </tr>
              ))}
              {decisions.data?.items.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-500">
                    No decisions match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <aside aria-label="Decision detail">
          {selected ? (
            <div className="card space-y-2">
              <h2 className="font-semibold">{selected.title}</h2>
              <p className="text-xs text-gray-500">
                confidence: {selected.confidence} · {selected.date ?? 'unknown date'} ·{' '}
                {selected.source ?? 'extracted'}
              </p>
              {selected.summary && <p className="text-sm">{selected.summary}</p>}
              {selected.reasoning && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-gray-500">Reasoning</h3>
                  <p className="text-sm">{selected.reasoning}</p>
                </div>
              )}
              {selected.alternatives && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-gray-500">Alternatives</h3>
                  <p className="text-sm">{selected.alternatives}</p>
                </div>
              )}
              {selected.files && selected.files.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-gray-500">Files</h3>
                  <ul className="text-sm">
                    {selected.files.map((f) => (
                      <li key={f}>
                        <Link
                          className="font-mono underline hover:text-brand-600"
                          to={`/repo/${repoId}/why?path=${encodeURIComponent(f)}`}
                        >
                          {f}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {selected.evidence.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase text-gray-500">Evidence</h3>
                  <ul className="text-sm">
                    {selected.evidence.map((e) => (
                      <li key={`${e.type}-${e.ref}`}>
                        {e.url ? (
                          <a className="underline" href={e.url} target="_blank" rel="noreferrer">
                            {e.type}: {e.ref}
                          </a>
                        ) : (
                          <span className="font-mono">
                            {e.type}: {e.ref}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Select a decision to see its evidence.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
