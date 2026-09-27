import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

/** Landing page: demo repo cards, GitHub URL input, ingested repo list. */
export function HomePage() {
  const repos = useQuery({ queryKey: ['repos'], queryFn: api.repos });
  const health = useQuery({ queryKey: ['health'], queryFn: api.health });
  const [source, setSource] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const ingest = useMutation({
    mutationFn: api.ingest,
    onSuccess: (data) => setJobId(data.job_id),
  });

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.job(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) =>
      query.state.data?.status === 'done' || query.state.data?.status === 'failed' ? false : 800,
  });

  useEffect(() => {
    if (job.data?.status === 'done') {
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      const repoId = job.data.repo_id;
      setJobId(null);
      navigate(`/repo/${repoId}`);
    }
  }, [job.data?.status, job.data?.repo_id, navigate, queryClient]);

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">Why is this code the way it is?</h1>
        <p className="mt-1 max-w-2xl text-gray-600 dark:text-gray-300">
          Heirloom mines a repo's git history, comments and docs into a decision graph — so
          knowledge doesn't leave when an engineer does.
        </p>
      </section>

      {!health.data?.demo && (
        <section className="card max-w-2xl">
          <h2 className="font-semibold">Ingest a repository</h2>
          <form
            className="mt-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (source.trim()) ingest.mutate(source.trim());
            }}
          >
            <label htmlFor="source" className="sr-only">
              Local path or public GitHub URL
            </label>
            <input
              id="source"
              className="input flex-1"
              placeholder="https://github.com/owner/name or a local path"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
            <button className="btn" type="submit" disabled={ingest.isPending || !!jobId}>
              Ingest
            </button>
          </form>
          {ingest.error && (
            <p role="alert" className="mt-2 text-sm text-red-600">
              {(ingest.error as Error).message}
            </p>
          )}
          {jobId && job.data && (
            <div className="mt-3">
              <div className="flex justify-between text-sm">
                <span>{job.data.message}</span>
                <span>{job.data.progress}%</span>
              </div>
              <div
                role="progressbar"
                aria-valuenow={job.data.progress}
                aria-valuemin={0}
                aria-valuemax={100}
                className="mt-1 h-2 overflow-hidden rounded bg-gray-200 dark:bg-gray-800"
              >
                <div
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${job.data.progress}%` }}
                />
              </div>
              {job.data.status === 'failed' && (
                <p role="alert" className="mt-2 text-sm text-red-600">
                  Ingestion failed: {job.data.message}
                </p>
              )}
            </div>
          )}
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">
          {health.data?.demo ? 'Demo repositories' : 'Ingested repositories'}
        </h2>
        {repos.isLoading && <p>Loading…</p>}
        {repos.data?.length === 0 && (
          <p className="text-gray-500">Nothing ingested yet — paste a GitHub URL above.</p>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {repos.data?.map((r) => (
            <Link key={r.id} to={`/repo/${r.id}`} className="card block hover:border-blue-400">
              <h3 className="font-semibold">{r.name}</h3>
              <p className="truncate text-xs text-gray-500">{r.source}</p>
              <dl className="mt-2 grid grid-cols-2 gap-1 text-sm">
                <div>
                  <dt className="text-gray-500">Files</dt>
                  <dd>{r.stats.files ?? 'unknown'}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Decisions</dt>
                  <dd>{r.stats.decisions ?? 'unknown'}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">LOC w/ bus factor 1</dt>
                  <dd>{r.stats.bus_factor_1_loc_pct ?? 'unknown'}%</dd>
                </div>
                <div>
                  <dt className="text-gray-500">At-risk files</dt>
                  <dd>{r.stats.at_risk_files ?? 'unknown'}</dd>
                </div>
              </dl>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
