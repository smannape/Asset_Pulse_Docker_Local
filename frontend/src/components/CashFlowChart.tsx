import type { ScenarioResult } from "../lib/api";

// Minimalist SVG cash-flow chart. Bars = monthly FCF; line = cumulative FCF.

export function CashFlowChart({ result }: { result: ScenarioResult | null }) {
  if (!result) return <div className="muted">No scenario run yet.</div>;
  const months = result.monthly.months;
  const fcf = result.monthly.free_cash_flow;

  const w = 800;
  const h = 220;
  const pad = { l: 50, r: 16, t: 8, b: 26 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const cum: number[] = [];
  let running = 0;
  for (const v of fcf) {
    running += v;
    cum.push(running);
  }

  const minFCF = Math.min(0, ...fcf);
  const maxFCF = Math.max(0, ...fcf);
  const minCum = Math.min(0, ...cum);
  const maxCum = Math.max(0, ...cum);

  const barX = (i: number) => pad.l + (i / Math.max(months.length - 1, 1)) * innerW;
  const barW = innerW / Math.max(months.length, 1) * 0.85;
  const yFCF = (v: number) =>
    pad.t + innerH - ((v - minFCF) / (maxFCF - minFCF || 1)) * innerH;
  const yCum = (v: number) =>
    pad.t + innerH - ((v - minCum) / (maxCum - minCum || 1)) * innerH;

  const zeroY = yFCF(0);

  const cumPath = cum
    .map((v, i) => `${i === 0 ? "M" : "L"} ${barX(i)} ${yCum(v)}`)
    .join(" ");

  return (
    <div className="cf-chart">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {/* axes */}
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="var(--border)" />
        <line x1={pad.l} y1={zeroY} x2={pad.l + innerW} y2={zeroY} stroke="var(--border)" strokeDasharray="2 3" />

        {/* monthly FCF bars */}
        {fcf.map((v, i) => {
          const x = barX(i) - barW / 2;
          const y = v >= 0 ? yFCF(v) : zeroY;
          const height = Math.abs(yFCF(v) - zeroY);
          const fill = v >= 0 ? "var(--accent)" : "var(--bad)";
          return <rect key={i} x={x} y={y} width={barW} height={height} fill={fill} fillOpacity={0.55} />;
        })}

        {/* cumulative line */}
        <path d={cumPath} fill="none" stroke="var(--text)" strokeWidth={1.4} />

        {/* labels */}
        <text x={pad.l + 4} y={pad.t + 12} fill="var(--text-muted)" fontSize={10}>
          monthly FCF (bars) + cumulative FCF (line)
        </text>
        <text x={pad.l - 4} y={zeroY + 3} textAnchor="end" fill="var(--text-faint)" fontSize={10}>
          0
        </text>
        <text x={pad.l + innerW} y={pad.t + innerH + 18} textAnchor="end" fill="var(--text-faint)" fontSize={10}>
          month {months[months.length - 1]}
        </text>
        <text x={pad.l} y={pad.t + innerH + 18} fill="var(--text-faint)" fontSize={10}>
          month 0
        </text>
      </svg>
    </div>
  );
}
