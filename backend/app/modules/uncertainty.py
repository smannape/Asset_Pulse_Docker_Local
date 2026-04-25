"""
Uncertainty analysis: tornado sensitivities, scenario comparison, simple Monte Carlo.

Reference: Himalayan Journal of Economics and Business Management upstream NPV sensitivity example
https://www.himjournals.com/hjebm/936/1022/articleID=1380/
"""

from __future__ import annotations

import math
import random
from typing import Callable


def tornado_sensitivity(
    base_inputs: dict,
    npv_fn: Callable[[dict], float],
    variables: list[dict],
) -> list[dict]:
    """
    variables = [{ "name": "oil_price", "low_pct": -0.30, "high_pct": 0.30 }, ...]
    Returns rows sorted by absolute swing magnitude.
    """
    base_npv = npv_fn(base_inputs)
    rows = []
    for v in variables:
        name = v["name"]
        low_pct = v.get("low_pct", -0.20)
        high_pct = v.get("high_pct", 0.20)
        base_val = base_inputs.get(name, 0.0)

        low_inputs = dict(base_inputs)
        high_inputs = dict(base_inputs)
        low_inputs[name] = base_val * (1.0 + low_pct)
        high_inputs[name] = base_val * (1.0 + high_pct)

        low_npv = npv_fn(low_inputs)
        high_npv = npv_fn(high_inputs)

        swing = abs(high_npv - low_npv)
        rows.append({
            "variable": name,
            "low_value": round(low_inputs[name], 4),
            "base_value": round(base_val, 4),
            "high_value": round(high_inputs[name], 4),
            "low_npv": round(low_npv, 2),
            "base_npv": round(base_npv, 2),
            "high_npv": round(high_npv, 2),
            "swing": round(swing, 2),
            "delta_low": round(low_npv - base_npv, 2),
            "delta_high": round(high_npv - base_npv, 2),
        })

    rows.sort(key=lambda r: r["swing"], reverse=True)
    return rows


def scenario_compare(
    scenarios: list[dict],
    npv_fn: Callable[[dict], float],
) -> list[dict]:
    """
    scenarios = [{"name": "Base", "inputs": {...}}, ...]
    Returns each with computed npv plus delta vs base.
    """
    if not scenarios:
        return []
    base_npv = npv_fn(scenarios[0]["inputs"])
    out = []
    for s in scenarios:
        n = npv_fn(s["inputs"])
        out.append({
            "name": s["name"],
            "npv": round(n, 2),
            "delta_vs_base": round(n - base_npv, 2),
        })
    return out


def _triangular(low: float, mode: float, high: float) -> float:
    return random.triangular(low, high, mode)


def monte_carlo_npv(
    base_inputs: dict,
    distributions: dict,
    npv_fn: Callable[[dict], float],
    iterations: int = 1000,
    seed: int = 42,
) -> dict:
    """
    distributions = {
      "oil_price": {"type": "triangular", "low": 50, "mode": 70, "high": 90},
      "capex_multiplier": {"type": "triangular", "low": 0.9, "mode": 1.0, "high": 1.3},
      "production_rate_factor": {"type": "lognormal", "mu": 0.0, "sigma": 0.15},
    }
    Returns P10/P50/P90 plus mean and stdev.
    """
    random.seed(seed)
    samples: list[float] = []
    for _ in range(iterations):
        inputs = dict(base_inputs)
        for var, spec in distributions.items():
            t = spec.get("type", "triangular")
            if t == "triangular":
                val = _triangular(spec["low"], spec["mode"], spec["high"])
            elif t == "lognormal":
                val = random.lognormvariate(spec.get("mu", 0.0), spec.get("sigma", 0.1))
            elif t == "uniform":
                val = random.uniform(spec["low"], spec["high"])
            elif t == "normal":
                val = random.gauss(spec.get("mean", 0.0), spec.get("std", 1.0))
            else:
                val = base_inputs.get(var, 0.0)
            # If "multiplier" in name, multiply base; else replace.
            if "multiplier" in var or "factor" in var:
                inputs[var] = val
            else:
                inputs[var] = val
        samples.append(npv_fn(inputs))

    samples.sort()
    n = len(samples)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, int(round(p * (n - 1)))))
        return samples[idx]

    mean = sum(samples) / n
    var = sum((x - mean) ** 2 for x in samples) / n
    std = math.sqrt(var)
    return {
        "iterations": iterations,
        "mean": round(mean, 2),
        "stdev": round(std, 2),
        "p10": round(pct(0.10), 2),
        "p50": round(pct(0.50), 2),
        "p90": round(pct(0.90), 2),
        "min": round(samples[0], 2),
        "max": round(samples[-1], 2),
    }


__all__ = ["tornado_sensitivity", "scenario_compare", "monte_carlo_npv"]
