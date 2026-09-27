import type { WhyCard } from '../api';
import { DecisionItem } from './DecisionItem';

/**
 * The body sections of a Why Card (spec F5): summary, decisions, holders,
 * impact, warnings. Kept as a pure component so it is easy to test.
 */
export function WhyCardView({ card }: { card: WhyCard }) {
  return (
    <div className="space-y-4">
      <div className="card">
        <h2 className="text-sm font-semibold">
          What this file does{' '}
          <span className="font-normal text-gray-500">(source: {card.summary_source})</span>
        </h2>
        <p className="mt-1">{card.summary}</p>
      </div>

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

      <div className="card">
        <h2 className="text-sm font-semibold">Knowledge holders</h2>
        {card.holders.length === 0 ? (
          <p className="mt-1 text-gray-500">unknown (no blame data for this file)</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {card.holders.map((h) => (
              <li key={h.name} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">{h.name}</span>
                <span>{Math.round(h.ownership * 100)}%</span>
                <span className="text-gray-500">
                  last active {h.last_active ?? 'unknown'}
                </span>
                {h.inactive && (
                  <span className="rounded bg-gray-200 px-1.5 text-xs dark:bg-gray-700">
                    inactive
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold">Impact if changed</h2>
        {card.impact.length === 0 ? (
          <p className="mt-1 text-gray-500">No known dependents.</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {card.impact.map((i) => (
              <li key={i.path} className="text-sm">
                <span className="font-mono">{i.path}</span>{' '}
                <span className="text-gray-500">
                  (score {i.score.toFixed(2)}) — {i.reason}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

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
    </div>
  );
}
