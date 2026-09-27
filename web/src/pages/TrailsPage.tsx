import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';

/** Onboarding trails (spec F7): topic input, ordered steps, local progress. */
export function TrailsPage() {
  const { repoId = '' } = useParams();
  const [topic, setTopic] = useState('');
  const [activeTopic, setActiveTopic] = useState<string | undefined>(undefined);
  const [done, setDone] = useState<Record<string, boolean>>({});

  const storageKey = `heirloom-trail-${repoId}-${activeTopic ?? 'general'}`;

  const trail = useQuery({
    queryKey: ['trail', repoId, activeTopic],
    queryFn: () => api.trail(repoId, activeTopic),
  });

  useEffect(() => {
    try {
      setDone(JSON.parse(localStorage.getItem(storageKey) ?? '{}'));
    } catch {
      setDone({});
    }
  }, [storageKey]);

  const toggle = (path: string) => {
    const next = { ...done, [path]: !done[path] };
    setDone(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      /* storage may be unavailable */
    }
  };

  const exportMarkdown = () => {
    if (!trail.data) return;
    const lines = [
      `# Onboarding trail${activeTopic ? `: ${activeTopic}` : ''}`,
      '',
      ...trail.data.steps.map(
        (s, i) => `${i + 1}. **${s.path}** (~${s.reading_minutes} min) — ${s.reason}`,
      ),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'onboarding-trail.md';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const doneCount = trail.data?.steps.filter((s) => done[s.path]).length ?? 0;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-bold">Onboarding trail</h1>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setActiveTopic(topic.trim() || undefined);
        }}
      >
        <label htmlFor="topic" className="sr-only">
          Topic
        </label>
        <input
          id="topic"
          className="input flex-1"
          placeholder='Topic, e.g. "authentication" (empty for a general trail)'
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button className="btn" type="submit">
          Build trail
        </button>
        <button className="btn" type="button" onClick={exportMarkdown} disabled={!trail.data?.steps.length}>
          Export Markdown
        </button>
      </form>

      {trail.isLoading && <p>Building trail…</p>}
      {trail.data && trail.data.steps.length === 0 && (
        <p className="text-gray-500">
          No relevant files found{activeTopic ? ` for "${activeTopic}"` : ''}.
        </p>
      )}
      {trail.data && trail.data.steps.length > 0 && (
        <>
          <p className="text-sm text-gray-500">
            {doneCount} of {trail.data.steps.length} steps done
          </p>
          <ol className="space-y-3">
            {trail.data.steps.map((s, i) => (
              <li key={s.path} className={`card ${done[s.path] ? 'opacity-60' : ''}`}>
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    id={`step-${i}`}
                    className="mt-1 h-4 w-4"
                    checked={!!done[s.path]}
                    onChange={() => toggle(s.path)}
                    aria-label={`Mark ${s.path} as read`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{i + 1}.</span>
                      <Link
                        to={`/repo/${repoId}/why?path=${encodeURIComponent(s.path)}`}
                        className="break-all font-mono text-sm underline hover:text-blue-600"
                      >
                        {s.path}
                      </Link>
                      <span className="text-xs text-gray-500">~{s.reading_minutes} min</span>
                    </div>
                    <p className="mt-1 text-sm">{s.reason}</p>
                    {s.decisions.length > 0 && (
                      <ul className="mt-1 text-xs text-gray-500">
                        {s.decisions.map((d) => (
                          <li key={d.id}>decision: {d.title}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
