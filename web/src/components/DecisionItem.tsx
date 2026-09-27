import type { CompactDecision } from '../api';

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-200',
  medium: 'bg-blue-100 text-blue-900 dark:bg-blue-950 dark:text-blue-200',
  low: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
};

/** One decision with its confidence badge and clickable evidence links. */
export function DecisionItem({ decision }: { decision: CompactDecision }) {
  return (
    <li className="border-l-2 border-gray-300 pl-3 dark:border-gray-700">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{decision.title}</span>
        <span
          className={`rounded px-1.5 py-0.5 text-xs font-medium ${CONFIDENCE_STYLES[decision.confidence]}`}
        >
          confidence: {decision.confidence}
        </span>
        <span className="text-xs text-gray-500">{decision.date ?? 'unknown date'}</span>
      </div>
      {decision.reasoning && <p className="mt-0.5 text-sm">{decision.reasoning}</p>}
      {decision.evidence.length > 0 && (
        <p className="mt-0.5 text-xs text-gray-500">
          Evidence:{' '}
          {decision.evidence.map((e, i) => (
            <span key={`${e.type}-${e.ref}`}>
              {i > 0 && ', '}
              {e.url ? (
                <a
                  className="underline hover:text-blue-600"
                  href={e.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {e.type}:{e.ref.slice(0, 24)}
                </a>
              ) : (
                <span className="font-mono">
                  {e.type}:{e.ref.slice(0, 40)}
                </span>
              )}
            </span>
          ))}
        </p>
      )}
    </li>
  );
}
