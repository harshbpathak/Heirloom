/**
 * Bus-factor badge. Color AND text label together (never color alone),
 * per the accessibility requirement in spec §9.2.
 */
export function BusFactorBadge({
  busFactor,
  atRisk,
}: {
  busFactor: number | null | undefined;
  atRisk?: boolean;
}) {
  if (busFactor === null || busFactor === undefined || busFactor === 0) {
    return (
      <span className="inline-flex items-center rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-700 dark:text-gray-200">
        bus factor: unknown (not analyzed)
      </span>
    );
  }
  const cls =
    busFactor === 1
      ? 'bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200'
      : busFactor === 2
        ? 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200'
        : 'bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-200';
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      bus factor: {busFactor}
      {atRisk && <strong aria-label="at risk">⚠ AT RISK</strong>}
    </span>
  );
}
