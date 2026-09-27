import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

/** Repositories page: ingest form and the list of ingested repos. */
export function ReposPage() {
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
    <div className="space-y-14">
      <PageHeader
        kicker="Repositories"
        title={health.data?.demo ? 'Demo repositories' : 'Your repositories'}
        blurb="Every repo Heirloom has mined. Open one to read Why Cards, the bus factor map, trails and decisions."
      />

      {!health.data?.demo && (
        <section id="ingest" className="scroll-mt-24">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
              Ingest a repository
            </h2>
            <span className="brutal-sticker rotate-1 bg-paper-light">2,000 commits in 22 s</span>
          </div>
          <div className="brutal-card p-6">
            <form
              className="flex flex-col gap-3 sm:flex-row"
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
                className="brutal-input flex-1"
                placeholder="https://github.com/owner/name or a local path"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
              <button
                className="brutal-button px-6"
                type="submit"
                disabled={ingest.isPending || !!jobId}
              >
                Ingest
              </button>
            </form>
            <p className="mt-3 text-xs font-medium text-ink-soft">
              No API keys needed. Git history, blame, comments, PRs and docs are mined locally.
            </p>
            {ingest.error && (
              <p role="alert" className="mt-3 text-sm font-bold text-danger">
                {(ingest.error as Error).message}
              </p>
            )}
            {jobId && job.data && (
              <div className="mt-4">
                <div className="flex justify-between text-[11px] font-black uppercase tracking-[0.16em]">
                  <span>{job.data.message}</span>
                  <span>{job.data.progress}%</span>
                </div>
                <div
                  role="progressbar"
                  aria-valuenow={job.data.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  className="mt-2 h-4 overflow-hidden border-[3px] border-ink bg-paper"
                >
                  <div
                    className="h-full bg-sun transition-all"
                    style={{ width: `${job.data.progress}%` }}
                  />
                </div>
                {job.data.status === 'failed' && (
                  <p role="alert" className="mt-2 text-sm font-bold text-danger">
                    Ingestion failed: {job.data.message}
                  </p>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      <section id="repos" className="scroll-mt-24">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
            Ingested
          </h2>
          {repos.data && (
            <span className="brutal-tag bg-sun text-[#1d1626]">{repos.data.length} repos</span>
          )}
        </div>
        {repos.isLoading && <p className="font-bold uppercase tracking-[0.16em]">Loading…</p>}
        {repos.data?.length === 0 && (
          <div className="brutal-card p-8 text-center">
            <p className="text-lg font-black uppercase">Nothing ingested yet</p>
            <p className="mt-2 text-sm text-ink-soft">
              Paste a GitHub URL above, or run <code className="font-mono">heirloom ingest .</code>{' '}
              in your project.
            </p>
          </div>
        )}
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {repos.data?.map((r, i) => (
            <Link
              key={r.id}
              to={`/repo/${r.id}`}
              className="reveal brutal-card block p-6 transition-transform duration-300 hover:-translate-y-1"
              style={{ '--reveal-delay': `${i * 90}ms` } as CSSProperties}
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-xl font-black uppercase tracking-wide">{r.name}</h3>
                <span
                  className={`brutal-tag shrink-0 ${
                    (r.stats.at_risk_files ?? 0) > 0
                      ? 'bg-coral text-[#1d1626]'
                      : 'bg-mint text-[#1d1626]'
                  }`}
                >
                  {(r.stats.at_risk_files ?? 0) > 0 ? 'at risk' : 'healthy'}
                </span>
              </div>
              <p className="mt-1 truncate font-mono text-xs text-ink-soft">{r.source}</p>
              <dl className="mt-4 grid grid-cols-2 gap-3">
                <Stat label="Files" value={r.stats.files ?? 'unknown'} />
                <Stat label="Decisions" value={r.stats.decisions ?? 'unknown'} />
                <Stat
                  label="LOC bus factor 1"
                  value={
                    r.stats.bus_factor_1_loc_pct != null
                      ? `${r.stats.bus_factor_1_loc_pct}%`
                      : 'unknown'
                  }
                />
                <Stat label="At-risk files" value={r.stats.at_risk_files ?? 'unknown'} />
              </dl>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export function PageHeader({
  kicker,
  title,
  blurb,
}: {
  kicker: string;
  title: string;
  blurb: string;
}) {
  return (
    <header className="reveal border-b-[3px] border-ink pb-8">
      <span className="brutal-sticker -rotate-2 bg-ink text-sun">{kicker}</span>
      <h1 className="mt-5 text-[clamp(2.4rem,6vw,4.5rem)] font-black uppercase leading-[0.9] tracking-[-0.05em]">
        {title}
      </h1>
      <p className="mt-4 max-w-2xl text-base font-medium leading-relaxed text-ink-soft">{blurb}</p>
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border-l-[3px] border-ink pl-3">
      <dt className="text-[10px] font-black uppercase tracking-[0.16em] text-ink-soft">{label}</dt>
      <dd className="text-lg font-black leading-tight">{value}</dd>
    </div>
  );
}
