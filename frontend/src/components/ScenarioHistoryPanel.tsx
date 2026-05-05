import type { SavedScenario } from "../lib/api";
import { fmtMonths, fmtUSD } from "../lib/format";

// Compact "last N runs" panel shown in the Scenario tab left column.
// Clicking an item loads its inputs AND reconstructs the stored result so
// all charts populate instantly without an extra API call.

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const m = Math.floor(diff / 60_000);
    if (m < 1) return "just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const days = Math.floor(h / 24);
    return `${days}d ago`;
  } catch {
    return "";
  }
}

export function ScenarioHistoryPanel({
  scenarios,
  activeId,
  onSelect,
}: {
  scenarios: SavedScenario[];
  activeId: number | null;
  onSelect: (sc: SavedScenario) => void;
}) {
  if (scenarios.length === 0) {
    return (
      <div className="muted" style={{ fontSize: 11, padding: "4px 0" }}>
        No saved runs yet. Run a scenario to begin.
      </div>
    );
  }

  return (
    <div className="sc-history-panel">
      {scenarios.map((sc) => {
        const r = sc.result;
        const npv = r?.npv;
        const npvCls = npv == null ? "" : npv >= 0 ? "good" : "bad";
        const isActive = sc.id === activeId;

        return (
          <div
            key={sc.id}
            className={`sc-history-item${isActive ? " active" : ""}`}
            onClick={() => onSelect(sc)}
            title={`Load "${sc.name}"`}
          >
            <div className="sc-history-name">{sc.name}</div>
            <div className="sc-history-meta">
              {npv != null && (
                <span className={`sc-history-npv ${npvCls}`}>{fmtUSD(npv)}</span>
              )}
              {r?.payback_months != null && (
                <span className="sc-history-pay">{fmtMonths(r.payback_months)}</span>
              )}
              <span className="sc-history-ts">{relativeTime(sc.created_at)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
