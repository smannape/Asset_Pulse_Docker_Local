import type { ScenarioResult } from "../lib/api";

// Decline curve: Oil Rate (bopd, solid line + area) + Water Cut % (dashed line).
// Uses the same SVG approach as CashFlowChart — no external charting library.

export function DeclineCurveChart({ result }: { result: ScenarioResult | null }) {
  if (!result) return <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>No scenario run yet.</div>;

  const months   = result.monthly.months;
  const oilBbl   = result.monthly.oil_bbl ?? [];
  const waterBbl = result.monthly.water_bbl ?? [];

  if (oilBbl.length === 0) {
    return <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>No production data available.</div>;
  }

  const DAYS_PER_MONTH = 30.44;
  const oilBopd     = oilBbl.map((b) => b / DAYS_PER_MONTH);
  const waterCutPct = oilBbl.map((oil, i) => {
    const water = waterBbl[i] ?? 0;
    const total = oil + water;
    return total > 0 ? (water / total) * 100 : 0;
  });

  const w = 800;
  const h = 220;
  const pad = { l: 54, r: 46, t: 12, b: 26 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const n = months.length;
  const xScale = (i: number) => pad.l + (i / Math.max(n - 1, 1)) * innerW;

  // Oil: left axis, 0 → maxOil
  const maxOil = Math.max(...oilBopd, 1);
  const yOil = (v: number) => pad.t + innerH - (v / maxOil) * innerH;

  // Water cut: right axis, 0 → 100 %
  const yWater = (v: number) => pad.t + innerH - (v / 100) * innerH;

  // SVG paths
  const oilLinePath = oilBopd
    .map((v, i) => `${i === 0 ? "M" : "L"} ${xScale(i).toFixed(1)} ${yOil(v).toFixed(1)}`)
    .join(" ");
  const oilAreaPath =
    `${oilLinePath} L ${xScale(n - 1).toFixed(1)} ${(pad.t + innerH).toFixed(1)}` +
    ` L ${xScale(0).toFixed(1)} ${(pad.t + innerH).toFixed(1)} Z`;
  const waterPath = waterCutPct
    .map((v, i) => `${i === 0 ? "M" : "L"} ${xScale(i).toFixed(1)} ${yWater(v).toFixed(1)}`)
    .join(" ");

  // Y-axis tick marks
  const oilTickValues = [0, 0.25, 0.5, 0.75, 1.0].map((t) => ({
    y: pad.t + innerH * (1 - t),
    label: Math.round(maxOil * t).toLocaleString(),
  }));
  const waterTickPcts = [0, 25, 50, 75, 100];

  return (
    <div className="cf-chart">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {/* Axes */}
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="var(--border)" />
        <line
          x1={pad.l + innerW} y1={pad.t}
          x2={pad.l + innerW} y2={pad.t + innerH}
          stroke="var(--border)" strokeDasharray="2 3"
        />
        <line
          x1={pad.l} y1={pad.t + innerH}
          x2={pad.l + innerW} y2={pad.t + innerH}
          stroke="var(--border)"
        />

        {/* Horizontal grid lines (oil ticks) */}
        {oilTickValues.map((t) => (
          <line
            key={t.label}
            x1={pad.l} y1={t.y} x2={pad.l + innerW} y2={t.y}
            stroke="var(--border)" strokeDasharray="2 4" opacity={0.4}
          />
        ))}

        {/* Oil area fill */}
        <path d={oilAreaPath} fill="var(--accent)" fillOpacity={0.12} />

        {/* Oil decline line */}
        <path d={oilLinePath} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinejoin="round" />

        {/* Water cut dashed line */}
        <path d={waterPath} fill="none" stroke="var(--warn)" strokeWidth={1.6} strokeDasharray="5 3" strokeLinejoin="round" />

        {/* Left axis labels — oil bopd */}
        {oilTickValues.map((t) => (
          <text
            key={t.label}
            x={pad.l - 4} y={t.y + 3}
            textAnchor="end" fill="var(--accent)" fontSize={9}
          >
            {t.label}
          </text>
        ))}

        {/* Right axis labels — water cut % */}
        {waterTickPcts.map((pct) => (
          <text
            key={pct}
            x={pad.l + innerW + 4} y={yWater(pct) + 3}
            textAnchor="start" fill="var(--warn)" fontSize={9}
          >
            {pct}%
          </text>
        ))}

        {/* X-axis labels */}
        <text x={pad.l} y={pad.t + innerH + 18} fill="var(--text-faint)" fontSize={10}>
          month 0
        </text>
        <text
          x={pad.l + innerW} y={pad.t + innerH + 18}
          textAnchor="end" fill="var(--text-faint)" fontSize={10}
        >
          month {months[months.length - 1]}
        </text>

        {/* Legend — bottom-left */}
        <line
          x1={pad.l + 4} y1={pad.t + innerH - 20}
          x2={pad.l + 22} y2={pad.t + innerH - 20}
          stroke="var(--accent)" strokeWidth={2}
        />
        <text x={pad.l + 26} y={pad.t + innerH - 17} fill="var(--accent)" fontSize={9}>
          oil rate (bopd)
        </text>
        <line
          x1={pad.l + 4} y1={pad.t + innerH - 8}
          x2={pad.l + 22} y2={pad.t + innerH - 8}
          stroke="var(--warn)" strokeWidth={1.6} strokeDasharray="5 3"
        />
        <text x={pad.l + 26} y={pad.t + innerH - 5} fill="var(--warn)" fontSize={9}>
          water cut %
        </text>
      </svg>
    </div>
  );
}
