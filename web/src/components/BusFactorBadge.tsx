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
      <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
        bus factor: unknown
      </span>
    );
  }
  const cls =
    busFactor === 1
      ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
      : busFactor === 2
        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
        : 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      bus factor: {busFactor}
      {atRisk && <strong aria-label="at risk">⚠ AT RISK</strong>}
    </span>
  );
}
