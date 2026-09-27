import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';

/** People page: concentration stats and a link to the "if they left" view. */
export function PeoplePage() {
  const { repoId = '' } = useParams();
  const people = useQuery({ queryKey: ['people', repoId], queryFn: () => api.people(repoId) });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">People</h1>
      <p className="text-sm text-gray-500">
        Names only — Heirloom never shows email addresses. Use the Overview page's "If this person
        left" filter to see each person's footprint on the map.
      </p>

      {people.isLoading && (
        <div className="card space-y-2 p-3" aria-busy="true">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-8 w-full" />
          ))}
        </div>
      )}
      {people.error && (
        <div role="alert" className="card border-red-300 dark:border-red-800">
          <p className="font-medium text-red-700 dark:text-red-400">Failed to load people</p>
          <p className="mt-1 text-sm text-red-600">{(people.error as Error).message}</p>
        </div>
      )}
      {people.data && people.data.length === 0 && (
        <p className="text-gray-500">No ownership data yet — ingest the repo first.</p>
      )}
      {people.data && people.data.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left dark:border-gray-800">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Owned LOC (weighted)</th>
                <th className="px-3 py-2">Files owned &gt;40%</th>
                <th className="px-3 py-2">Last active</th>
                <th className="px-3 py-2">Map</th>
              </tr>
            </thead>
            <tbody>
              {people.data.map((p) => (
                <tr key={p.name} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="px-3 py-2 font-medium">
                    {p.name}
                    {p.inactive && (
                      <span className="ml-2 rounded bg-gray-200 px-1.5 text-xs dark:bg-gray-700">
                        inactive
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{p.owned_loc.toLocaleString()}</td>
                  <td className="px-3 py-2 tabular-nums">{p.files_over_40pct}</td>
                  <td className="px-3 py-2 text-gray-500">{p.last_active ?? 'unknown'}</td>
                  <td className="px-3 py-2">
                    <Link className="underline hover:text-brand-600" to={`/repo/${repoId}`}>
                      If {p.name} left →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
