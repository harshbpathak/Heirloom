import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader } from './ReposPage';

const ROLES = [
  {
    tag: 'Role 01',
    title: 'The new engineer',
    body: 'You just joined, or the person who wrote this left last month. Follow an onboarding trail, read the Why Card before you touch a file, and see who to ask.',
    uses: ['Onboarding trail puts dependencies first', 'Why Card shows DO NOT warnings inline', 'People page names who still knows it'],
    dark: false,
    shadow: 'var(--violet)',
  },
  {
    tag: 'Role 02',
    title: 'The tech lead',
    body: 'You need to know what breaks when someone leaves. The bus factor map shows the footprint of one person, and the risk report lists the files nobody else understands.',
    uses: ['Treemap coloured by bus factor', '"If this person left" filter', 'Repo-wide at-risk report'],
    dark: false,
    shadow: 'var(--sun)',
  },
  {
    tag: 'Role 03',
    title: 'The coding agent',
    body: 'IBM Bob, Claude, Cursor or any MCP client. It reads a file’s history before it edits and records a decision after. Every response stays under 2,000 tokens.',
    uses: ['ask_why · who_knows · impact_if_changed', 'onboarding_trail · search_decisions', 'record_decision · repo_risk_report'],
    dark: true,
    shadow: 'var(--coral)',
  },
  {
    tag: 'Role 04',
    title: 'The reviewer',
    body: 'A GitHub Action comments on every pull request with the decisions it may conflict with, the bus factor of touched files and impacted files outside the PR.',
    uses: ['One comment, updated in place', 'Works on forks with no secrets', 'DO NOT comments near changed lines'],
    dark: false,
    shadow: 'var(--mint)',
  },
];

const TOOLS = [
  ['ask_why', 'Why a file is the way it is, with evidence.'],
  ['who_knows', 'Knowledge holders and bus factor for a path.'],
  ['impact_if_changed', 'What breaks, and why, if a file changes.'],
  ['onboarding_trail', 'An ordered reading path, general or by topic.'],
  ['search_decisions', 'Full-text search over recorded decisions.'],
  ['record_decision', 'Save a new decision as Markdown in git.'],
  ['repo_risk_report', 'Repo-wide list of at-risk files.'],
];

/** Roles: who Heirloom is for, and the MCP tool list for agents. */
export function RolesPage() {
  return (
    <div className="space-y-16">
      <PageHeader
        kicker="Roles"
        title="Four people. One graph."
        blurb="Engineers, leads and reviewers use the web UI and the CLI. Agents use the MCP server. All of them read the same decision graph."
      />

      <section className="grid gap-8 lg:grid-cols-2">
        {ROLES.map((role, i) => (
          <div
            key={role.title}
            className={`reveal brutal-slab flex h-full flex-col p-7 ${
              role.dark ? 'bg-night text-[#f8f2ea]' : 'bg-paper-light'
            }`}
            style={
              {
                '--reveal-delay': `${i * 100}ms`,
                boxShadow: `10px 10px 0 ${role.shadow}`,
              } as CSSProperties
            }
          >
            <span
              className={`brutal-sticker self-start ${
                role.dark
                  ? 'rotate-2 border-[#f8f2ea] bg-coral text-[#1d1626]'
                  : '-rotate-2 bg-violet text-[#f8f2ea]'
              }`}
            >
              {role.tag}
            </span>
            <h2 className="mt-5 text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
              {role.title}
            </h2>
            <p
              className={`mt-4 text-sm leading-relaxed ${
                role.dark ? 'text-[#f8f2ea]/75' : 'text-ink-soft'
              }`}
            >
              {role.body}
            </p>
            <ul className="mt-6 space-y-2">
              {role.uses.map((u) => (
                <li
                  key={u}
                  className={`flex items-center gap-3 text-[12px] font-black uppercase tracking-wide ${
                    role.dark ? 'text-[#f8f2ea]' : ''
                  }`}
                >
                  <span
                    className={`h-3 w-3 shrink-0 border-[3px] ${
                      role.dark ? 'border-[#f8f2ea] bg-coral' : 'border-ink bg-sun'
                    }`}
                  />
                  {u}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="border-t-[3px] border-ink pt-16">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-3xl font-black uppercase leading-none tracking-[-0.05em] sm:text-4xl">
            Seven MCP tools
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-ink-soft">
            One line of config and any agent can read history before it edits.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {TOOLS.map(([name, body], i) => (
            <div
              key={name}
              className="reveal flex items-center gap-4 border-[3px] border-ink bg-paper-light p-4 shadow-[4px_4px_0_var(--ink)]"
              style={{ '--reveal-delay': `${i * 60}ms` } as CSSProperties}
            >
              <span
                className={`grid h-11 w-11 shrink-0 place-items-center border-[3px] border-ink font-mono text-[10px] font-black ${
                  ['bg-violet text-[#f8f2ea]', 'bg-sun', 'bg-danger text-[#f8f2ea]', 'bg-coral', 'bg-mint', 'bg-night text-[#f8f2ea]', 'bg-paper-light'][i]
                }`}
              >
                0{i + 1}
              </span>
              <span>
                <span className="block font-mono text-[12px] font-black tracking-wide">{name}</span>
                <span className="block text-[11px] text-ink-soft">{body}</span>
              </span>
            </div>
          ))}
        </div>
        <pre className="mt-8 overflow-x-auto border-[3px] border-ink bg-night p-4 font-mono text-[12px] leading-relaxed text-[#f8f2ea] shadow-[6px_6px_0_var(--ink)]">
          {'{ "mcpServers": { "heirloom": { "command": "heirloom", "args": ["mcp"] } } }'}
        </pre>
        <div className="mt-8 flex flex-wrap gap-4">
          <Link to="/repos" className="brutal-button px-6 py-3">
            Ingest a repo
          </Link>
          <Link to="/how" className="btn px-6 py-3">
            How it works
          </Link>
        </div>
      </section>
    </div>
  );
}
