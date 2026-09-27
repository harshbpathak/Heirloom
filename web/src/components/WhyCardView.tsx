import type { Holder, ImpactItem, WhyCard } from '../api';
import { ActivityChart } from './ActivityChart';
import { DecisionItem } from './DecisionItem';

/** Two-letter initials badge for a knowledge holder. */
function InitialsBadge({ name, inactive }: { name: string; inactive: boolean }) {
  const initials = name
    .split(' ')
    .map((p) => p[0]?.toUpperCase() ?? '')
    .slice(0, 2)
    .join('');
  return (
    <span
      className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
        inactive
          ? 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
          : 'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-400'
      }`}
      title={name}
      aria-label={name}
    >
      {initials}
    </span>
  );
}

/** Impact score bar (0–1 range). */
function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Impact score ${pct}%`}
        className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
      >
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-xs tabular-nums text-gray-500">{score.toFixed(2)}</span>
    </div>
  );
}

/**
 * The body sections of a Why Card (spec F5): summary, decisions, holders,
 * impact, warnings, activity. Two-column on desktop.
 */
export function WhyCardView({ card }: { card: WhyCard }) {
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="card">
        <h2 className="text-sm font-semibold">
          What this file does{' '}
          <span className="font-normal text-gray-500">(source: {card.summary_source})</span>
        </h2>
        <p className="mt-1">{card.summary}</p>
      </div>

      {/* Two-column grid on md+ */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Left column: decisions */}
        <div className="card">
          <h2 className="text-sm font-semibold">Why it is like this</h2>
          {card.decisions.length === 0 ? (
            <p className="mt-1 text-gray-500">No recorded decisions for this file.</p>
          ) : (
            <ul className="mt-2 space-y-3">
              {card.decisions.map((d) => (
                <DecisionItem key={d.id} decision={d} />
              ))}
            </ul>
          )}
        </div>

        {/* Right column: holders + impact */}
        <div className="space-y-4">
          <HoldersCard holders={card.holders} />
          <ImpactCard impact={card.impact} />
        </div>
      </div>

      {/* Warnings */}
      {card.warnings.length > 0 && (
        <div className="card border-amber-300 dark:border-amber-800">
          <h2 className="text-sm font-semibold text-amber-800 dark:text-amber-200">⚠ Warnings</h2>
          <ul className="mt-2 space-y-1">
            {card.warnings.map((w) => (
              <li key={`${w.line}-${w.text}`} className="text-sm">
                <span className="text-gray-500">line {w.line}:</span> {w.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Activity chart */}
      {card.activity.length > 0 && (
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold">Commits per month</h2>
          <ActivityChart activity={card.activity} />
        </div>
      )}
    </div>
  );
}

function HoldersCard({ holders }: { holders: Holder[] }) {
  return (
    <div className="card">
      <h2 className="text-sm font-semibold">Knowledge holders</h2>
      {holders.length === 0 ? (
        <p className="mt-1 text-gray-500">unknown (no blame data for this file)</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {holders.map((h) => (
            <li key={h.name} className="flex items-center gap-3">
              <InitialsBadge name={h.name} inactive={h.inactive} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2">
                  <span className="font-medium">{h.name}</span>
                  {h.inactive && (
                    <span className="rounded bg-gray-200 px-1.5 text-xs dark:bg-gray-700">
                      inactive
                    </span>
                  )}
                </div>
                <div className="mt-0.5 flex items-center gap-2">
                  <div
                    role="meter"
                    aria-valuenow={Math.round(h.ownership * 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${h.name} owns ${Math.round(h.ownership * 100)}%`}
                    className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
                  >
                    <div
                      className={`h-full rounded-full ${h.inactive ? 'bg-gray-400' : 'bg-brand-500'}`}
                      style={{ width: `${Math.round(h.ownership * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums text-gray-500">
                    {Math.round(h.ownership * 100)}%
                  </span>
                  <span className="text-xs text-gray-400">
                    · last active {h.last_active ?? 'unknown'}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ImpactCard({ impact }: { impact: ImpactItem[] }) {
  return (
    <div className="card">
      <h2 className="text-sm font-semibold">Impact if changed</h2>
      {impact.length === 0 ? (
        <p className="mt-1 text-gray-500">No known dependents.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {impact.map((i) => (
            <li key={i.path} className="text-sm">
              <div className="flex flex-wrap items-center justify-between gap-x-2">
                <span className="min-w-0 truncate font-mono text-xs">{i.path}</span>
                <ScoreBar score={i.score} />
              </div>
              <p className="mt-0.5 text-xs text-gray-500">{i.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
