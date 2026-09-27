import { useQuery } from '@tanstack/react-query';
import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

const LINKS = [
  {
    to: '/how',
    n: '01',
    title: 'How it works',
    body: 'Four steps from git log to a decision graph, and the six views you get on every repo.',
    color: 'bg-sun',
  },
  {
    to: '/roles',
    n: '02',
    title: 'Roles',
    body: 'New engineers, tech leads, reviewers and coding agents. Same graph, different doors.',
    color: 'bg-mint',
  },
  {
    to: '/repos',
    n: '03',
    title: 'Repositories',
    body: 'Ingest a GitHub URL or a local path, then open the Why Card, the map, trails and Ask.',
    color: 'bg-coral',
  },
];

/** Landing page: hero, live stats and doors into the other pages. */
export function HomePage() {
  const repos = useQuery({ queryKey: ['repos'], queryFn: api.repos });
  const totalDecisions = repos.data?.reduce((n, r) => n + (r.stats.decisions ?? 0), 0);
  const atRisk = repos.data?.reduce((n, r) => n + (r.stats.at_risk_files ?? 0), 0);

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
            <Link
              to="/repos"
              className="brutal-button gap-2.5 px-7 py-4 text-[12px] shadow-[6px_6px_0_var(--ink)]"
            >
              Ingest a repo
            </Link>
            <Link to="/how" className="btn px-7 py-4 text-[12px] shadow-[6px_6px_0_var(--ink)]">
              How it works
            </Link>
            <Link
              to="/roles"
              className="text-[12px] font-black uppercase tracking-[0.16em] underline decoration-[3px] underline-offset-4 hover:text-violet"
            >
              Who it is for
            </Link>
          </div>
        </div>

        {/* Terminal screen */}
        <div
          className="reveal relative mx-auto w-full max-w-xl lg:max-w-none"
          style={{ '--reveal-delay': '120ms' } as CSSProperties}
        >
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
              <span className="text-mint">What it does</span>
              {'\n'}
              Tokenises option strings; the shell-split rules live here.{'\n'}
              {'\n'}
              <span className="text-mint">Decisions</span> (3){'\n'}
              <span className="text-coral">DO NOT</span> re-order flag parsing: #1237 relies on it
              {'\n'}
              Kept custom splitter over shlex: Windows paths (2019){'\n'}
              Added --strict after silent-failure bug (#884){'\n'}
              {'\n'}
              <span className="text-mint">Who knows it</span>
              {'\n'}
              j.rivera 71% · bus factor <span className="text-coral">1</span> · at risk{'\n'}
              {'\n'}
              <span className="text-mint">If this changes</span>
              {'\n'}
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
            <span className="text-5xl font-black leading-none tracking-tighter">{atRisk ?? '–'}</span>
            <span className="text-sm font-black uppercase tracking-[0.16em]">at-risk files</span>
          </div>
          <div className="mt-3 text-[11px] font-bold uppercase leading-relaxed tracking-[0.12em]">
            Understood by one person only
          </div>
        </div>
      </section>

      {/* Doors into the other pages */}
      <section>
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-4xl font-black uppercase leading-none tracking-[-0.05em] sm:text-5xl">
            Start
            <br />
            here
          </h2>
          <span className="brutal-sticker rotate-1 bg-paper-light">Three pages</span>
        </div>
        <div className="grid gap-8 md:grid-cols-3">
          {LINKS.map((l, i) => (
            <Link
              key={l.to}
              to={l.to}
              className="reveal brutal-card group flex h-full flex-col p-6 transition-transform duration-300 hover:-translate-y-1"
              style={{ '--reveal-delay': `${i * 90}ms` } as CSSProperties}
            >
              <div className="flex items-center justify-between">
                <span className="brutal-num font-mono text-5xl font-black leading-none">{l.n}</span>
                <span
                  className={`grid h-11 w-11 place-items-center border-[3px] border-ink ${l.color} text-[#1d1626] shadow-[3px_3px_0_var(--ink)] transition-transform group-hover:translate-x-1`}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12h13.5" />
                    <path d="M13 6s6 4.4 6 6-6 6-6 6" />
                  </svg>
                </span>
              </div>
              <h3 className="mt-4 text-xl font-black uppercase tracking-wide">{l.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{l.body}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
