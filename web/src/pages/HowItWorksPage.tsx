import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader } from './ReposPage';

const STEPS = [
  {
    n: '01',
    title: 'Ingest a repo',
    body: 'Paste a GitHub URL or a local path. Heirloom clones it and mines git history, blame, code comments, merged PRs and docs.',
    detail: 'About 22 seconds for 2,000 commits, no LLM needed.',
  },
  {
    n: '02',
    title: 'Build the decision graph',
    body: 'Commits, comments and PRs become decisions with evidence links. DO NOT and HACK warnings are pulled out on their own.',
    detail: 'Heuristic extractor by default; IBM watsonx Granite when a key is set.',
  },
  {
    n: '03',
    title: 'Read the Why Card',
    body: 'One page per file: what it does, the decisions behind it, who still knows it, and what breaks if it changes.',
    detail: 'Copy it as Markdown or as compact agent context.',
  },
  {
    n: '04',
    title: 'Record new decisions',
    body: 'From the web form, the CLI, or an agent over MCP. Each one is saved as Markdown in the repo, so it lives in git.',
    detail: 'The PR guard comments on every pull request that conflicts.',
  },
];

const FEATURES = [
  { name: 'Why Card', to: 'why', color: 'bg-sun', text: 'text-[#1d1626]', body: 'History, decisions, owners and impact for one file.' },
  { name: 'Bus Factor Map', to: '', color: 'bg-coral', text: 'text-[#1d1626]', body: 'A treemap coloured by how many people still understand each file.' },
  { name: 'Onboarding Trails', to: 'trails', color: 'bg-mint', text: 'text-[#1d1626]', body: 'An ordered reading path that puts dependencies first.' },
  { name: 'Ask Heirloom', to: 'ask', color: 'bg-violet', text: 'text-[#f8f2ea]', body: 'Questions answered only from recorded decisions, with citations.' },
  { name: 'Decisions', to: 'decisions', color: 'bg-paper-light', text: 'text-ink', body: 'Every recorded decision, searchable, with its evidence.' },
  { name: 'People', to: 'people', color: 'bg-night', text: 'text-[#f8f2ea]', body: 'Who knows what, and what leaves with them.' },
];

/** How it works: the four-step pipeline, the feature set and the offline stack. */
export function HowItWorksPage() {
  return (
    <div className="space-y-16">
      <PageHeader
        kicker="How it works"
        title="From git log to a decision graph"
        blurb="Heirloom mines what is already in the repo. Nothing leaves your machine, and every step has a deterministic fallback when no LLM is configured."
      />

      <section>
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
            Four steps
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
                <span className="grid h-11 w-11 place-items-center border-[3px] border-ink bg-sun font-black text-[#1d1626] shadow-[3px_3px_0_var(--ink)]">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-4 text-base font-black uppercase tracking-wide">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{s.body}</p>
              <p className="mt-auto pt-4 text-[11px] font-black uppercase tracking-[0.12em]">
                {s.detail}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
            What you get
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-ink-soft">
            Six views on every ingested repo. All of them work without keys.
          </p>
        </div>
        <div className="grid border-[3px] border-ink shadow-[10px_10px_0_var(--ink)] sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <div
              key={f.name}
              className={`${f.color} ${f.text} border-ink p-6 transition-transform duration-300 hover:-translate-y-1 ${
                i < FEATURES.length - 1 ? 'border-b-[3px]' : ''
              } ${i % 3 !== 2 ? 'lg:border-r-[3px]' : ''} ${i % 2 === 0 ? 'sm:border-r-[3px] lg:border-r-[3px]' : ''} ${i >= FEATURES.length - 3 ? 'lg:border-b-0' : ''}`}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[10px] font-black tracking-[0.2em] opacity-70">
                  0{i + 1}
                </span>
                <span className="text-lg font-black uppercase tracking-[0.06em]">{f.name}</span>
              </div>
              <p className="mt-3 text-[12px] font-bold leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-8 lg:grid-cols-[1fr_1fr]">
        <div className="brutal-slab bg-night p-7 text-[#f8f2ea]" style={{ boxShadow: '10px 10px 0 var(--coral)' }}>
          <span className="brutal-sticker rotate-2 border-[#f8f2ea] bg-coral text-[#1d1626]">Stack</span>
          <h3 className="mt-5 text-3xl font-black uppercase leading-none tracking-[-0.05em]">
            No cloud required
          </h3>
          <ul className="mt-5 space-y-3 text-sm">
            {[
              ['SQLite', 'Every repo, decision and LLM cache in one file.'],
              ['FastAPI', 'Serves the API and this UI from one process.'],
              ['FastMCP', 'Seven tools for IBM Bob, Claude, Cursor and VS Code.'],
              ['watsonx Granite', 'Optional. Turns on richer extraction and Ask answers.'],
            ].map(([k, v]) => (
              <li key={k} className="flex gap-3 border-l-[3px] border-sun pl-3">
                <span className="w-36 shrink-0 font-mono text-[11px] font-black uppercase tracking-[0.12em] text-sun">
                  {k}
                </span>
                <span className="text-[#f8f2ea]/80">{v}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="brutal-slab bg-paper-light p-7" style={{ boxShadow: '10px 10px 0 var(--violet)' }}>
          <span className="brutal-sticker -rotate-2 bg-violet text-[#f8f2ea]">Try it</span>
          <h3 className="mt-5 text-3xl font-black uppercase leading-none tracking-[-0.05em]">
            Three commands
          </h3>
          <pre className="mt-5 overflow-x-auto border-[3px] border-ink bg-night p-4 font-mono text-[12px] leading-relaxed text-[#f8f2ea] shadow-[4px_4px_0_var(--ink)]">
            <span className="text-mint">$</span> heirloom ingest https://github.com/pallets/click{'\n'}
            <span className="text-mint">$</span> heirloom why src/click/core.py{'\n'}
            <span className="text-mint">$</span> heirloom serve
          </pre>
          <div className="mt-6 flex flex-wrap gap-4">
            <Link to="/repos" className="brutal-button px-6 py-3">
              Ingest a repo
            </Link>
            <Link to="/roles" className="btn px-6 py-3">
              Who it is for
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
