interface Segment {
  label: string;
  value: number;
  color: string;
}

// Lightweight SVG donut — no chart library needed.
export function DonutChart({
  segments,
  centerLabel,
  centerSub,
}: {
  segments: Segment[];
  centerLabel: string;
  centerSub: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="donut-wrap">
      <svg width="150" height="150" viewBox="0 0 150 150">
        <circle
          cx="75"
          cy="75"
          r={radius}
          fill="none"
          stroke="var(--surface-hover)"
          strokeWidth="16"
        />
        {total > 0 &&
          segments
            .filter((s) => s.value > 0)
            .map((s) => {
              const fraction = s.value / total;
              const dash = fraction * circumference;
              const el = (
                <circle
                  key={s.label}
                  cx="75"
                  cy="75"
                  r={radius}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="16"
                  strokeLinecap="butt"
                  strokeDasharray={`${dash} ${circumference - dash}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 75 75)"
                  style={{ transition: "stroke-dasharray 0.6s ease" }}
                />
              );
              offset += dash;
              return el;
            })}
        <text x="75" y="73" textAnchor="middle" className="donut-center-label">
          {centerLabel}
        </text>
        <text x="75" y="90" textAnchor="middle" className="donut-center-sub">
          {centerSub}
        </text>
      </svg>
      <div className="donut-legend">
        {segments.map((s) => (
          <div key={s.label} className="legend-item">
            <span className="legend-swatch" style={{ background: s.color }} />
            {s.label}
            <span className="legend-count">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
