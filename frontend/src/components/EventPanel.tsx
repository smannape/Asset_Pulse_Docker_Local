import { useState } from "react";
import { apiPost, type EventInput } from "../lib/api";
import { fmtUSD } from "../lib/format";

const EVENT_TYPES = [
  { value: "capex_overrun", label: "CAPEX overrun (one-time)" },
  { value: "downtime", label: "Downtime (months)" },
  { value: "price_drop", label: "Price drop (% × months)" },
  { value: "opex_escalation", label: "OPEX escalation ($/mo × months)" },
  { value: "restart_cost", label: "Restart cost (one-time)" },
];

export function EventPanel({
  baseNpv,
  baseMonthlyCf,
}: {
  baseNpv: number | null;
  baseMonthlyCf: number | null;
}) {
  const [events, setEvents] = useState<EventInput[]>([
    { type: "capex_overrun", magnitude: 1_500_000, duration_months: 0 },
    { type: "downtime", magnitude: 0, duration_months: 3 },
  ]);
  const [result, setResult] = useState<{
    final_npv: number;
    impacts: Array<{ event_type: string; delta_npv: number; adjusted_npv: number; narrative: string }>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const update = (i: number, patch: Partial<EventInput>) => {
    setEvents((arr) => arr.map((e, j) => (i === j ? { ...e, ...patch } : e)));
  };
  const addEvent = () =>
    setEvents((arr) => [...arr, { type: "capex_overrun", magnitude: 0, duration_months: 0 }]);
  const removeEvent = (i: number) =>
    setEvents((arr) => arr.filter((_, j) => j !== i));

  const run = async () => {
    if (baseNpv == null || baseMonthlyCf == null) return;
    setLoading(true);
    setErr(null);
    try {
      const r = await apiPost<typeof result>("/api/events/impact", {
        base_npv: baseNpv,
        base_monthly_cf: baseMonthlyCf,
        events,
      });
      setResult(r);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {baseNpv == null && (
        <div className="muted">Run a scenario first — events stack on top of base NPV.</div>
      )}
      {baseNpv != null && (
        <>
          <div className="muted" style={{ marginBottom: 6 }}>
            Base NPV: <span className="mono-num accent-text">{fmtUSD(baseNpv)}</span> · Avg
            monthly FCF: <span className="mono-num">{fmtUSD(baseMonthlyCf ?? 0)}</span>
          </div>
          <table className="tbl" style={{ marginBottom: 8 }}>
            <thead>
              <tr>
                <th className="l">Event</th>
                <th>Magnitude</th>
                <th>Duration (mo)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={i}>
                  <td className="l">
                    <select value={e.type} onChange={(ev) => update(i, { type: ev.target.value })}>
                      {EVENT_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={e.magnitude}
                      onChange={(ev) => update(i, { magnitude: Number(ev.target.value) })}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="1"
                      value={e.duration_months}
                      onChange={(ev) => update(i, { duration_months: Number(ev.target.value) })}
                    />
                  </td>
                  <td>
                    <button onClick={() => removeEvent(i)} className="ghost">
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row" style={{ marginBottom: 8 }}>
            <button onClick={addEvent} className="ghost">
              + add event
            </button>
            <button onClick={run} className="primary" disabled={loading}>
              {loading ? "Computing..." : "Compute impact"}
            </button>
          </div>
          {err && <div className="ln bad">! {err}</div>}
          {result && (
            <div className="console" style={{ minHeight: 80 }}>
              <span className="ln pre">// Event impact stack</span>
              {result.impacts.map((im, i) => (
                <span key={i} className={`ln ${im.delta_npv < 0 ? "bad" : "good"}`}>
                  [{i + 1}] {im.event_type}: ΔNPV {fmtUSD(im.delta_npv)} → {fmtUSD(im.adjusted_npv)}{" "}
                  — {im.narrative}
                </span>
              ))}
              <span className="ln h">Final NPV after all events: {fmtUSD(result.final_npv)}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
