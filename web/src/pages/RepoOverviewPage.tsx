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
              <span key={p.name} className="rounded bg-gray-100 px-2 py-0.5 text-sm dark:bg-gray-800">
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
            “If this person left”:
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
        {tree.isLoading && <p>Loading map…</p>}
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
      <div className="text-lg font-semibold">{value ?? 'unknown'}</div>
    </div>
  );
}
