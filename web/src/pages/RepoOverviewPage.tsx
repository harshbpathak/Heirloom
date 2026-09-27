import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { BusFactorMap } from '../components/BusFactorMap';

/** Repo overview: stats strip, Bus Factor Map, author filter, search box. */
export function RepoOverviewPage() {
  const { repoId = '' } = useParams();
  const navigate = useNavigate();
  const [filterAuthor, setFilterAuthor] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const repos = useQuery({ queryKey: ['repos'], queryFn: api.repos });
  const tree = useQuery({ queryKey: ['tree', repoId], queryFn: () => api.tree(repoId) });
  const risk = useQuery({ queryKey: ['risk', repoId], queryFn: () => api.risk(repoId) });
  const people = useQuery({ queryKey: ['people', repoId], queryFn: () => api.people(repoId) });

  const repo = repos.data?.find((r) => r.id === repoId);
  const stats = repo?.stats;

  if (repos.isLoading) {
    return (
      <div className="space-y-6" aria-busy="true">
        <div className="skeleton h-7 w-48" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card py-3">
              <div className="skeleton mb-1 h-3 w-16" />
              <div className="skeleton h-6 w-12" />
            </div>
          ))}
        </div>
        <div className="card"><div className="skeleton h-64 w-full" /></div>
      </div>
    );
  }

  if (repos.error) {
    return (
      <div role="alert" className="card border-red-300 dark:border-red-800">
        <p className="font-medium text-red-700 dark:text-red-400">Failed to load repository</p>
        <p className="mt-1 text-sm text-red-600">{(repos.error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-bold">{repo?.name ?? repoId}</h1>
        <form
          className="ml-auto flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (search.trim())
              navigate(`/repo/${repoId}/decisions?q=${encodeURIComponent(search.trim())}`);
          }}
        >
          <label htmlFor="repo-search" className="sr-only">
            Search decisions
          </label>
          <input
            id="repo-search"
            className="input"
            placeholder="Search decisions…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn" type="submit">
            Search
          </button>
        </form>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5" role="group" aria-label="Repo statistics">
        <Stat label="Files" value={stats?.files} />
        <Stat label="Lines of code" value={stats?.loc} />
        <Stat label="Decisions found" value={stats?.decisions} />
        <Stat
          label="% LOC bus factor 1"
          value={stats?.bus_factor_1_loc_pct !== undefined ? `${stats.bus_factor_1_loc_pct}%` : undefined}
        />
        <Stat label="At-risk files" value={stats?.at_risk_files} />
      </div>

      {risk.data && risk.data.top_people.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold">Most concentrated people</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {risk.data.top_people.map((p) => (
              <span key={p.name} className="rounded-full bg-gray-100 px-3 py-0.5 text-sm dark:bg-gray-800">
                {p.name} — {p.files_over_40pct} files &gt;40%
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="font-semibold">Bus Factor Map</h2>
          <label htmlFor="author-filter" className="ml-auto text-sm text-gray-600 dark:text-gray-300">
            "If this person left":
          </label>
          <select
            id="author-filter"
            className="input"
            value={filterAuthor ?? ''}
            onChange={(e) => setFilterAuthor(e.target.value || null)}
          >
            <option value="">— everyone —</option>
            {people.data?.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        {tree.isLoading && (
          <div className="skeleton h-64 w-full" aria-label="Loading bus factor map…" />
        )}
        {tree.error && (
          <p role="alert" className="text-sm text-red-600">
            Could not load map: {(tree.error as Error).message}
          </p>
        )}
        {tree.data && (
          <BusFactorMap
            tree={tree.data}
            filterAuthor={filterAuthor}
            onSelectFile={(path) => navigate(`/repo/${repoId}/why?path=${encodeURIComponent(path)}`)}
          />
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string | undefined }) {
  return (
    <div className="card py-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold">{value ?? '—'}</div>
    </div>
  );
}
