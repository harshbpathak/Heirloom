/** Small SVG bar chart: commits per month (Why Card timeline, F5.7). */
export function ActivityChart({ activity }: { activity: { month: string; commits: number }[] }) {
  if (activity.length === 0) return null;

  const max = Math.max(...activity.map((a) => a.commits), 1);
  const barW = 18;
  const gap = 2;
  const chartH = 60;
  const axisH = 16; // space for x-axis labels
  const labelW = 28; // space for y-axis labels
  const totalW = labelW + activity.length * (barW + gap);
  const totalH = chartH + axisH;

  // Y-axis: 0 and max
  const yLabels = [
    { y: 0, label: String(max) },
    { y: chartH, label: '0' },
  ];

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${totalW} ${totalH}`}
      role="img"
      aria-label={`Commits per month from ${activity[0].month} to ${activity[activity.length - 1].month}`}
      className="max-w-full overflow-visible"
    >
      {/* Y-axis labels */}
      {yLabels.map(({ y, label }) => (
        <text
          key={label}
          x={labelW - 4}
          y={y + (y === 0 ? 8 : 0)}
          textAnchor="end"
          fontSize="8"
          className="fill-gray-400"
        >
          {label}
        </text>
      ))}

      {/* Y-axis line */}
      <line x1={labelW} y1={0} x2={labelW} y2={chartH} className="stroke-gray-200 dark:stroke-gray-700" strokeWidth="1" />

      {/* Bars */}
      {activity.map((a, i) => {
        const h = Math.max((a.commits / max) * chartH, 2);
        const x = labelW + i * (barW + gap);
        const showLabel = i === 0 || i === activity.length - 1 || (activity.length > 12 && i % 6 === 0);
        return (
          <g key={a.month}>
            <rect
              x={x}
              y={chartH - h}
              width={barW}
              height={h}
              className="fill-brand-500"
              rx={2}
            >
              <title>{`${a.month}: ${a.commits} commit${a.commits === 1 ? '' : 's'}`}</title>
            </rect>
            {showLabel && (
              <text
                x={x + barW / 2}
                y={totalH}
                textAnchor="middle"
                fontSize="7"
                className="fill-gray-400"
              >
                {a.month.slice(0, 7)}
              </text>
            )}
          </g>
        );
      })}

      {/* X-axis line */}
      <line x1={labelW} y1={chartH} x2={totalW} y2={chartH} className="stroke-gray-200 dark:stroke-gray-700" strokeWidth="1" />
    </svg>
  );
}
