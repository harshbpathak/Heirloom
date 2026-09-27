import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { api } from '../api';

/** Heirloom logo: pot glyph in a sun-coloured box, brutalist wordmark. */
function Wordmark() {
  return (
    <span className="flex items-center gap-2.5 text-sm font-black uppercase tracking-[0.14em]">
      <span className="grid h-9 w-9 place-items-center border-[3px] border-ink bg-sun shadow-[3px_3px_0_var(--ink)]">
        <svg width="18" height="16" viewBox="0 0 20 16" fill="none" aria-hidden="true">
          <path d="M4 4h12v2a6 6 0 0 1-12 0V4Z" fill="#1d1626" />
          <rect x="7" y="1" width="6" height="3.5" rx="0.5" fill="#1d1626" />
          <rect x="1" y="4" width="2" height="5" fill="#1d1626" />
          <rect x="17" y="4" width="2" height="5" fill="#1d1626" />
        </svg>
      </span>
      <span>
        Heir<span className="text-coral">loom</span>
      </span>
    </span>
  );
}

const TICKER = [
  'Why is this code the way it is',
  'Who still understands it',
  'What breaks if you change it',
  'Zero API keys required',
  'Runs offline',
  'Bus factor, decisions, trails',
];

/** Top navigation, ticker, theme toggle and demo-mode badge around every page. */
export function Layout() {
  const { repoId } = useParams();
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const health = useQuery({ queryKey: ['health'], queryFn: api.health });
  const { pathname } = useLocation();

  // Each route is its own page: start at the top when it changes.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    try {
      localStorage.setItem('heirloom-theme', dark ? 'dark' : 'light');
    } catch {
      /* private-mode storage failures are fine */
    }
  }, [dark]);

  const tabs = repoId
    ? [
        { to: `/repo/${repoId}`, label: 'Overview', end: true },
        { to: `/repo/${repoId}/why`, label: 'Why Card' },
        { to: `/repo/${repoId}/trails`, label: 'Trails' },
        { to: `/repo/${repoId}/ask`, label: 'Ask' },
        { to: `/repo/${repoId}/decisions`, label: 'Decisions' },
        { to: `/repo/${repoId}/people`, label: 'People' },
      ]
    : [
        { to: '/how', label: 'How it works' },
        { to: '/roles', label: 'Roles' },
        { to: '/repos', label: 'Repositories' },
      ];

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b-[3px] border-ink bg-paper">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3 sm:px-8">
          <Link to="/" aria-label="Heirloom home" className="mr-2">
            <Wordmark />
          </Link>
          <nav aria-label="Repo sections" className="flex min-w-0 flex-wrap items-center gap-4">
            {tabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  `text-[10px] font-black uppercase tracking-[0.16em] transition-colors ${
                    isActive
                      ? 'border-b-[3px] border-coral text-ink'
                      : 'text-ink-soft hover:text-ink'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex shrink-0 items-center gap-3">
            {health.data?.demo && (
              <span className="brutal-sticker -rotate-2 bg-sun text-[#1d1626]">demo</span>
            )}
            {health.data && (
              <span
                className="hidden text-[10px] font-black uppercase tracking-[0.16em] text-ink-soft md:inline"
                title="Active LLM backend"
              >
                {health.data.llm}
              </span>
            )}
            <button
              className="btn"
              onClick={() => setDark(!dark)}
              aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
            >
              {dark ? 'Light' : 'Dark'}
            </button>
            {repoId ? (
              <Link to={`/repo/${repoId}/ask`} className="brutal-button hidden sm:inline-flex">
                Ask Heirloom
                <ArrowIcon />
              </Link>
            ) : (
              <Link to="/repos" className="brutal-button hidden sm:inline-flex">
                Ingest a repo
                <ArrowIcon />
              </Link>
            )}
          </div>
        </div>
      </header>

      <div className="brutal-ticker" aria-hidden="true">
        <div className="brutal-ticker__track">
          {[0, 1].map((copy) => (
            <div key={copy} className="flex shrink-0 items-center">
              {TICKER.map((t) => (
                <span
                  key={t}
                  className="flex items-center gap-5 whitespace-nowrap px-5 py-2 text-[11px] font-black uppercase tracking-[0.2em]"
                >
                  {t}
                  <DiamondIcon />
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      <main className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <Outlet />
      </main>

      <footer className="mt-16 border-t-[3px] border-ink bg-night text-paper">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-5 py-6 text-[10px] font-black uppercase tracking-[0.2em] sm:px-8">
          <span className="text-[#f8f2ea]">Heirloom · knowledge that stays</span>
          <span className="text-[#f8f2ea]/60">Works offline · No API keys · MCP ready</span>
        </div>
      </footer>
    </div>
  );
}

function ArrowIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18.5 12L4.99997 12" />
      <path d="M13 18C13 18 19 13.5811 19 12C19 10.4188 13 6 13 6" />
    </svg>
  );
}

function DiamondIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--sun)"
      strokeWidth="2.8"
      aria-hidden="true"
    >
      <path d="M6.959 7.03438L8.04435 5.72804C10.1093 3.24268 11.1417 2 12.5 2C13.8583 2 14.8907 3.24268 16.9556 5.72803L18.041 7.03437C20.0137 9.4087 21 10.5959 21 12C21 13.4041 20.0137 14.5913 18.041 16.9656L16.9557 18.272C14.8907 20.7573 13.8583 22 12.5 22C11.1417 22 10.1093 20.7573 8.04435 18.272L6.95901 16.9656C4.98634 14.5913 4 13.4041 4 12C4 10.5959 4.98633 9.4087 6.959 7.03438Z" />
    </svg>
  );
}
