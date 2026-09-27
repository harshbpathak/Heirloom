import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useParams } from 'react-router-dom';
import { api } from '../api';

/** Top navigation, theme toggle and demo-mode banner around every page. */
export function Layout() {
  const { repoId } = useParams();
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const health = useQuery({ queryKey: ['health'], queryFn: api.health });

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
    : [];

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            🏺 Heirloom
          </Link>
          <nav aria-label="Repo sections" className="flex flex-wrap gap-1">
            {tabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  `rounded-md px-2.5 py-1 text-sm ${
                    isActive
                      ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                      : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            {health.data?.demo && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                demo mode
              </span>
            )}
            {health.data && (
              <span className="text-gray-500" title="Active LLM backend">
                LLM: {health.data.llm}
              </span>
            )}
            <button
              className="btn"
              onClick={() => setDark(!dark)}
              aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
            >
              {dark ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
