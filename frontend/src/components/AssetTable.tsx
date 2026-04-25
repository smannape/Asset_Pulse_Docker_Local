import type { Asset } from "../lib/api";
import { fmtNum, fmtUSD } from "../lib/format";

export function AssetTable({
  assets,
  onSelect,
}: {
  assets: Asset[];
  onSelect: (a: Asset) => void;
}) {
  if (assets.length === 0) {
    return <div className="muted">No assets seeded yet.</div>;
  }

  return (
    <div className="scrollbox">
      <table className="tbl">
        <thead>
          <tr>
            <th className="l">Asset</th>
            <th className="l">Type</th>
            <th className="l">Region</th>
            <th>Initial oil (bopd)</th>
            <th>Decline</th>
            <th>Fixed OPEX/mo</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => {
            const cp = a.cost_profile;
            const decl = cp?.decline_inputs;
            const opx = cp?.opex_inputs;
            return (
              <tr key={a.id}>
                <td className="l">{a.name}</td>
                <td className="l">{a.asset_type}</td>
                <td className="l">{a.region ?? "—"}</td>
                <td className="mono-num">{decl?.initial_oil_bopd ? fmtNum(decl.initial_oil_bopd) : "—"}</td>
                <td className="mono-num">
                  {decl?.annual_decline ? `${(decl.annual_decline * 100).toFixed(0)}%` : "—"}
                </td>
                <td className="mono-num">
                  {opx?.fixed_opex_per_month ? fmtUSD(opx.fixed_opex_per_month) : "—"}
                </td>
                <td>
                  <button onClick={() => onSelect(a)}>load</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
