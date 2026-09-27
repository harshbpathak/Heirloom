/** Small SVG bar chart: commits per month (Why Card timeline, F5.7). */
export function ActivityChart({ activity }: { activity: { month: string; commits: number }[] }) {
  const max = Math.max(...activity.map((a) => a.commits), 1);
  const barWidth = 18;
  const height = 60;
  const width = activity.length * (barWidth + 2);

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${width} ${height + 16}`}
      role="img"
      aria-label={`Commits per month from ${activity[0]?.month} to ${activity[activity.length - 1]?.month}`}
      className="max-w-full"
    >
      {activity.map((a, i) => {
        const h = Math.max((a.commits / max) * height, 2);
        return (
          <g key={a.month}>
            <rect
              x={i * (barWidth + 2)}
              y={height - h}
              width={barWidth}
              height={h}
              className="fill-blue-500"
            >
              <title>{`${a.month}: ${a.commits} commit${a.commits === 1 ? '' : 's'}`}</title>
            </rect>
            {(i === 0 || i === activity.length - 1) && (
              <text
                x={i * (barWidth + 2)}
                y={height + 12}
                className="fill-gray-500 text-[8px]"
              >
                {a.month}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
