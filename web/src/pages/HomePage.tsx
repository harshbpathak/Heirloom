import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

const STEPS = [
  {
    n: '01',
    title: 'Ingest a repo',
    body: 'Paste a GitHub URL or a local path. Heirloom mines git history, blame, comments, PRs and docs.',
  },
  {
    n: '02',
    title: 'Read the Why Card',
    body: 'One page per file: what it does, the decisions behind it, who knows it, what breaks if it changes.',
  },
  {
    n: '03',
    title: 'See the bus factor',
    body: 'A treemap of the repo coloured by how many people still understand each file. At-risk files are striped.',
  },
  {
    n: '04',
    title: 'Record decisions',
    body: 'From the web, the CLI, or an agent over MCP. Each one is saved as Markdown, so it lives in git.',
  },
];

const ROLES = [
  {
    tag: 'For people',
    title: 'The engineer',
    body: 'You just joined, or the person who wrote this left. Follow an onboarding trail, ask why, and see who to talk to.',
    tools: ['Why Card', 'Trails', 'Ask', 'People'],
    dark: false,
  },
  {
    tag: 'For agents',
    title: 'The agent',
    body: 'IBM Bob or any MCP client reads a file’s history before it edits, and records a decision after. Seven tools, under 2000 tokens each.',
    tools: ['ask_why', 'who_knows', 'impact_if_changed', 'record_decision'],
    dark: true,
  },
];

/** Landing page: hero, how-it-works, roles, ingest form and ingested repo list. */
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

  const totalDecisions = repos.data?.reduce((n, r) => n + (r.stats.decisions ?? 0), 0);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="grid items-center gap-12 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:py-10">
        <div className="reveal flex flex-col items-start">
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <span className="brutal-sticker -rotate-2 bg-ink text-sun">Knowledge graph</span>
            <span className="brutal-sticker rotate-1 bg-paper-light">Zero API keys</span>
          </div>
          <h1 className="text-[clamp(2.8rem,8vw,6.5rem)] font-black uppercase leading-[0.85] tracking-[-0.06em]">
            Why is
            <br />
            this code
            <br />
            <span className="text-coral">the way</span>
            <br />
            <span className="inline-block border-[3px] border-ink bg-sun px-3 text-[#1d1626] shadow-[8px_8px_0_var(--ink)]">
              it is?
            </span>
          </h1>
          <p className="mt-9 max-w-lg text-base font-medium leading-relaxed">
            Heirloom mines a repo&apos;s git history, comments and docs into a decision graph, so
            knowledge doesn&apos;t leave when an engineer does. Who still understands it. What breaks
            if you change it.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="#ingest"
              className="brutal-button gap-2.5 px-7 py-4 text-[12px] shadow-[6px_6px_0_var(--ink)]"
            >
              Ingest a repo
            </a>
            <a href="#repos" className="btn px-7 py-4 text-[12px] shadow-[6px_6px_0_var(--ink)]">
              Browse repos
            </a>
            <a
              href="#how"
              className="text-[12px] font-black uppercase tracking-[0.16em] underline decoration-[3px] underline-offset-4 hover:text-violet"
            >
              How it works
            </a>
          </div>
        </div>

        {/* Terminal screen */}
        <div className="reveal relative mx-auto w-full max-w-xl lg:max-w-none" style={{ '--reveal-delay': '120ms' } as CSSProperties}>
          <div className="brutal-screen">
            <div className="flex items-center justify-between border-b-[3px] border-ink bg-[#1d1626] px-3 py-2 text-[9px] font-black uppercase tracking-[0.2em] text-[#f8f2ea]">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 bg-coral" />
                <span className="h-2.5 w-2.5 bg-sun" />
                <span className="h-2.5 w-2.5 bg-mint" />
                <span className="ml-2">heirloom why src/core/parser.py</span>
              </span>
              <span className="flex items-center gap-1.5 text-mint">
                <span className="signal-pulse h-1.5 w-1.5 rounded-full bg-mint" />
                live
              </span>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[12px] leading-relaxed text-[#f8f2ea]">
              <span className="text-sun">WHY CARD</span> src/core/parser.py{'\n'}
              {'\n'}
              <span className="text-mint">What it does</span>{'\n'}
              Tokenises option strings; the shell-split rules live here.{'\n'}
              {'\n'}
              <span className="text-mint">Decisions</span> (3){'\n'}
              <span className="text-coral">DO NOT</span> re-order flag parsing: #1237 relies on it{'\n'}
              Kept custom splitter over shlex: Windows paths (2019){'\n'}
              Added --strict after silent-failure bug (#884){'\n'}
              {'\n'}
              <span className="text-mint">Who knows it</span>{'\n'}
              davidism 71%  ·  bus factor <span className="text-coral">1</span>  ·  at risk{'\n'}
              {'\n'}
              <span className="text-mint">If this changes</span>{'\n'}
              core/context.py · cli/main.py · 14 tests
            </pre>
          </div>
          <span className="brutal-sticker absolute -bottom-4 left-4 rotate-[-3deg] bg-sun text-[#1d1626] sm:left-8">
            Bus factor 1 = one person away from lost
          </span>
        </div>
      </section>

      {/* Stat slabs */}
      <section className="grid border-[3px] border-ink shadow-[10px_10px_0_var(--ink)] sm:grid-cols-3">
        <div className="border-b-[3px] border-ink bg-sun p-6 text-[#1d1626] transition-transform duration-300 hover:-translate-y-1 sm:border-b-0 sm:border-r-[3px]">
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black leading-none tracking-tighter">
              {repos.data?.length ?? '–'}
            </span>
            <span className="text-sm font-black uppercase tracking-[0.16em]">repos</span>
          </div>
          <div className="mt-3 text-[11px] font-bold uppercase leading-relaxed tracking-[0.12em]">
            Ingested and ready to ask
          </div>
        </div>
        <div className="border-b-[3px] border-ink bg-mint p-6 text-[#1d1626] transition-transform duration-300 hover:-translate-y-1 sm:border-b-0 sm:border-r-[3px]">
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black leading-none tracking-tighter">
              {totalDecisions ?? '–'}
            </span>
            <span className="text-sm font-black uppercase tracking-[0.16em]">decisions</span>
          </div>
          <div className="mt-3 text-[11px] font-bold uppercase leading-relaxed tracking-[0.12em]">
            Mined from history, with evidence
          </div>
        </div>
        <div className="bg-violet p-6 text-[#f8f2ea] transition-transform duration-300 hover:-translate-y-1">
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black leading-none tracking-tighter">7</span>
            <span className="text-sm font-black uppercase tracking-[0.16em]">MCP tools</span>
          </div>
          <div className="mt-3 text-[11px] font-bold uppercase leading-relaxed tracking-[0.12em]">
            For IBM Bob and any agent
          </div>
        </div>
      </section>

      {/* Ingest */}
      {!health.data?.demo && (
        <section id="ingest" className="scroll-mt-24">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-4xl font-black uppercase leading-none tracking-[-0.05em] sm:text-5xl">
              Ingest a<br />
              repository
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

      {/* Repos */}
      <section id="repos" className="scroll-mt-24">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-4xl font-black uppercase leading-none tracking-[-0.05em] sm:text-5xl">
            {health.data?.demo ? 'Demo' : 'Ingested'}
            <br />
            repositories
          </h2>
        </div>
        {repos.isLoading && <p className="font-bold uppercase tracking-[0.16em]">Loading…</p>}
        {repos.data?.length === 0 && (
          <p className="text-ink-soft">Nothing ingested yet. Paste a GitHub URL above.</p>
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
                    (r.stats.at_risk_files ?? 0) > 0 ? 'bg-coral text-[#1d1626]' : 'bg-mint text-[#1d1626]'
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
                  value={r.stats.bus_factor_1_loc_pct != null ? `${r.stats.bus_factor_1_loc_pct}%` : 'unknown'}
                />
                <Stat label="At-risk files" value={r.stats.at_risk_files ?? 'unknown'} />
              </dl>
            </Link>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-24">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-4xl font-black uppercase leading-none tracking-[-0.05em] sm:text-5xl">
            How Heirloom
            <br />
            works
          </h2>
          <span className="brutal-sticker rotate-1 bg-paper-light">Offline by default</span>
        </div>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <div
              key={s.n}
              className="reveal brutal-card flex h-full flex-col p-6"
              style={{ '--reveal-delay': `${i * 90}ms` } as CSSProperties}
            >
              <div className="flex items-center justify-between">
                <span className="brutal-num font-mono text-5xl font-black leading-none">{s.n}</span>
                <span className="grid h-11 w-11 place-items-center border-[3px] border-ink bg-sun text-[#1d1626] shadow-[3px_3px_0_var(--ink)] font-black">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-4 text-base font-black uppercase tracking-wide">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Roles */}
      <section id="roles" className="grid gap-8 lg:grid-cols-2">
        {ROLES.map((role, i) => (
          <div
            key={role.title}
            className={`reveal brutal-slab h-full p-7 ${
              role.dark ? 'bg-night text-[#f8f2ea]' : 'bg-paper-light'
            }`}
            style={
              {
                '--reveal-delay': `${i * 120}ms`,
                boxShadow: role.dark ? '10px 10px 0 var(--coral)' : '10px 10px 0 var(--violet)',
              } as CSSProperties
            }
          >
            <span
              className={`brutal-sticker ${
                role.dark ? 'rotate-2 border-[#f8f2ea] bg-coral text-[#1d1626]' : '-rotate-2 bg-violet text-[#f8f2ea]'
              }`}
            >
              {role.tag}
            </span>
            <h3 className="mt-5 text-4xl font-black uppercase leading-none tracking-[-0.05em]">
              {role.title}
            </h3>
            <p className={`mt-4 text-sm leading-relaxed ${role.dark ? 'text-[#f8f2ea]/75' : 'text-ink-soft'}`}>
              {role.body}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {role.tools.map((t) => (
                <span
                  key={t}
                  className={`brutal-tag font-mono ${
                    role.dark ? 'border-[#f8f2ea] bg-[#1d1626] text-[#f8f2ea] shadow-[3px_3px_0_var(--coral)]' : 'bg-sun text-[#1d1626]'
                  }`}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
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
