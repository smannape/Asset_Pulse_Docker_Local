"""
Weighted decision matrix for shut-in / restart / keep-online decisions.

References:
- SPE JPT shut-in nuance: https://jpt.spe.org/twa/shutting-wells-why-its-nuanced-process
- AOGR restart strategy: https://www.aogr.com/magazine/cover-story/fiscal-technical-issues-define-operator-strategies-in-restarting-shut-in-wells
"""

from __future__ import annotations


# Default criteria. Direction "higher_better" means a higher metric -> higher score.
# "lower_better" inverts. "higher_favors_shut_in" pushes shut-in score up when high.
DEFAULT_CRITERIA = [
    {"key": "monthly_margin",        "label": "Current monthly margin (USD)", "weight": 0.20, "direction": "higher_better"},
    {"key": "npv_keep_online",       "label": "NPV if kept online (USD)",     "weight": 0.15, "direction": "higher_better"},
    {"key": "avoidable_opex",        "label": "Avoidable OPEX if shut in",    "weight": 0.10, "direction": "higher_favors_shut_in"},
    {"key": "restart_payback_months","label": "Restart payback (months)",     "weight": 0.10, "direction": "lower_better"},
    {"key": "restart_risk",          "label": "Restart technical risk (0-1)", "weight": 0.15, "direction": "lower_better"},
    {"key": "hbp_risk",              "label": "HBP/lease/midstream risk (0-1)","weight": 0.10, "direction": "lower_better"},
    {"key": "water_burden",          "label": "Water-disposal burden (0-1)",  "weight": 0.10, "direction": "higher_favors_shut_in"},
    {"key": "strategic_value",       "label": "Strategic production value (0-1)","weight": 0.10, "direction": "higher_better"},
]


def _normalize(value: float, lo: float, hi: float, direction: str) -> float:
    if hi == lo:
        return 0.5
    raw = (value - lo) / (hi - lo)
    raw = max(0.0, min(1.0, raw))
    if direction in ("lower_better",):
        return 1.0 - raw
    if direction == "higher_favors_shut_in":
        # for "shut-in score" we want higher = higher score, so raw stays
        return raw
    return raw  # higher_better


def score_assets(
    assets: list[dict],
    criteria: list[dict] | None = None,
) -> list[dict]:
    """
    assets: each must have keys matching every criterion.key plus a 'name' or 'asset_id'.
    Returns each asset with normalized criterion scores, weighted total, and recommendation.
    """
    crits = criteria or DEFAULT_CRITERIA

    # Build min/max bounds across the asset population for normalization
    bounds = {}
    for c in crits:
        vals = [a.get(c["key"], 0.0) for a in assets]
        bounds[c["key"]] = (min(vals), max(vals))

    out = []
    for a in assets:
        breakdown = []
        weighted_total = 0.0
        shut_in_pressure = 0.0
        keep_online_pressure = 0.0
        for c in crits:
            v = a.get(c["key"], 0.0)
            lo, hi = bounds[c["key"]]
            ns = _normalize(v, lo, hi, c["direction"])
            contribution = ns * c["weight"]
            weighted_total += contribution
            breakdown.append({
                "key": c["key"],
                "label": c["label"],
                "value": v,
                "normalized": round(ns, 4),
                "weight": c["weight"],
                "contribution": round(contribution, 4),
                "direction": c["direction"],
            })
            if c["direction"] == "higher_favors_shut_in":
                shut_in_pressure += ns * c["weight"]
            elif c["direction"] == "higher_better":
                keep_online_pressure += ns * c["weight"]

        rec = _recommend(a, weighted_total, shut_in_pressure, keep_online_pressure)
        out.append({
            "asset_id": a.get("asset_id") or a.get("name"),
            "name": a.get("name", str(a.get("asset_id", ""))),
            "weighted_score": round(weighted_total, 4),
            "shut_in_pressure": round(shut_in_pressure, 4),
            "keep_online_pressure": round(keep_online_pressure, 4),
            "recommendation": rec,
            "breakdown": breakdown,
        })

    out.sort(key=lambda r: r["weighted_score"], reverse=True)
    return out


def _recommend(asset: dict, total: float, shut_in_p: float, keep_online_p: float) -> str:
    monthly_margin = asset.get("monthly_margin", 0.0)
    npv_keep = asset.get("npv_keep_online", 0.0)
    restart_risk = asset.get("restart_risk", 0.5)
    hbp_risk = asset.get("hbp_risk", 0.5)
    payback = asset.get("restart_payback_months", 999)

    if monthly_margin < 0 and restart_risk < 0.4 and hbp_risk < 0.4:
        return "Shut in / monitor restart trigger"
    if monthly_margin < 0 and restart_risk >= 0.6:
        return "Choke back / minimize cost / avoid full shut-in"
    if monthly_margin > 0 and npv_keep > 0:
        return "Keep online"
    if payback is not None and payback <= 12 and monthly_margin >= 0:
        return "Restart"
    return "Review manually"


def event_impact(
    base_npv: float,
    base_monthly_cf: float,
    event: dict,
) -> dict:
    """
    event: {"type": "capex_overrun"|"downtime"|"price_drop"|"opex_escalation"|"restart_cost", "magnitude": ...}
    Returns adjusted NPV and a short narrative.
    """
    t = event.get("type", "generic")
    mag = event.get("magnitude", 0.0)
    duration_months = event.get("duration_months", 0)
    narrative = ""
    delta_npv = 0.0

    if t == "capex_overrun":
        # mag is overrun amount in USD (one-time)
        delta_npv = -float(mag)
        narrative = f"CAPEX overrun of ${mag:,.0f} reduces NPV by the same amount at t=0."
    elif t == "downtime":
        # months of lost cash flow at base monthly cf
        delta_npv = -base_monthly_cf * duration_months
        narrative = f"{duration_months} months of downtime at ${base_monthly_cf:,.0f}/mo erodes NPV by ${-delta_npv:,.0f}."
    elif t == "price_drop":
        # mag is fractional drop in revenue, applied for duration_months
        delta_npv = -base_monthly_cf * mag * duration_months
        narrative = f"Price drop of {mag*100:.0f}% over {duration_months} months."
    elif t == "opex_escalation":
        delta_npv = -float(mag) * duration_months
        narrative = f"OPEX escalation of ${mag:,.0f}/mo over {duration_months} months."
    elif t == "restart_cost":
        delta_npv = -float(mag)
        narrative = f"Restart cost ${mag:,.0f} applied at t=0."
    else:
        narrative = "Unknown event type; no adjustment applied."

    return {
        "event_type": t,
        "delta_npv": round(delta_npv, 2),
        "adjusted_npv": round(base_npv + delta_npv, 2),
        "narrative": narrative,
    }


__all__ = ["DEFAULT_CRITERIA", "score_assets", "event_impact"]
