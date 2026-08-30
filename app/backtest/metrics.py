"""Deterministic analytical metrics for fixed-horizon signal returns."""
from __future__ import annotations
import statistics
from collections import defaultdict
from typing import Iterable
from app.backtest.models import SignalRecord

def _summary(records: Iterable[SignalRecord], horizon: int) -> dict[str, object]:
    items = [record for record in records if record.returns.get(horizon) is not None]
    values = [float(record.returns[horizon]) for record in items]
    if not values: return {"count": 0, "win_rate": None, "loss_rate": None, "average_return": None, "median_return": None, "best_return": None, "worst_return": None, "average_mfe": None, "average_mae": None, "max_mfe": None, "max_mae": None, "profit_factor": None, "expectancy": None}
    positive, negative = sum(value for value in values if value > 0), -sum(value for value in values if value < 0)
    return {"count": len(values), "win_rate": sum(value > 0 for value in values) / len(values), "loss_rate": sum(value <= 0 for value in values) / len(values), "average_return": statistics.mean(values), "median_return": statistics.median(values), "best_return": max(values), "worst_return": min(values), "average_mfe": statistics.mean(float(record.mfe[horizon]) for record in items), "average_mae": statistics.mean(float(record.mae[horizon]) for record in items), "max_mfe": max(float(record.mfe[horizon]) for record in items), "max_mae": min(float(record.mae[horizon]) for record in items), "profit_factor": positive / negative if negative else None, "expectancy": statistics.mean(values)}

def calculate(records: tuple[SignalRecord, ...], horizons: list[int], selected: int) -> tuple[dict[str, object], tuple[tuple[str, float], ...]]:
    actionable = tuple(record for record in records if record.direction != "WAIT")
    metrics: dict[str, object] = {"horizons": {h: _summary(actionable, h) for h in horizons}, "buy": _summary((r for r in actionable if r.direction == "BUY"), selected), "sell": _summary((r for r in actionable if r.direction == "SELL"), selected)}
    def groups(key):
        grouped = defaultdict(list)
        for r in actionable: grouped[key(r)].append(r)
        return {name: _summary(group, selected) for name, group in grouped.items()}
    metrics["strength"] = groups(lambda r: r.strength)
    metrics["score_buckets"] = groups(lambda r: f"{min(90, (r.score // 10) * 10)}-{min(100, (r.score // 10) * 10 + 9)}")
    metrics["directional_edge"] = groups(lambda r: "50+" if abs(r.directional_edge) >= 50 else f"{max(20, (abs(r.directional_edge)//10)*10)}-{max(20, (abs(r.directional_edge)//10)*10+9)}")
    metrics["mtf"] = groups(lambda r: f"M15_{r.m15_bias}_M5_{r.m5_bias}")
    metrics["regime"] = groups(lambda r: r.regime); metrics["session"] = groups(lambda r: r.session)
    equity = 1.0; peak = 1.0; max_drawdown = 0.0; curve = []
    streak = win_streak = loss_streak = max_wins = max_losses = 0
    for r in actionable:
        value = r.returns.get(selected)
        if value is None: continue
        equity *= 1 + float(value); peak = max(peak, equity); max_drawdown = max(max_drawdown, (peak - equity) / peak); curve.append((r.timestamp, equity))
        if value > 0: win_streak += 1; loss_streak = 0
        else: loss_streak += 1; win_streak = 0
        max_wins, max_losses = max(max_wins, win_streak), max(max_losses, loss_streak)
    metrics["maximum_drawdown"] = max_drawdown; metrics["maximum_consecutive_wins"] = max_wins; metrics["maximum_consecutive_losses"] = max_losses
    return metrics, tuple(curve)
