"""Transparent weighted score conversion."""

from __future__ import annotations

from app.config.settings import SignalWeights


def weighted(value: float, maximum: int) -> int:
    return round(max(0.0, min(1.0, value)) * maximum)


def breakdown(weights: SignalWeights, macro: float, entry: float, momentum: float, structure: float, volatility: float, candle: float, sr: float) -> dict[str, int]:
    return {"trend_score": weighted(macro, weights.macro_trend), "entry_trend_score": weighted(entry, weights.entry_trend), "momentum_score": weighted(momentum, weights.momentum), "structure_score": weighted(structure, weights.structure), "volatility_score": weighted(volatility, weights.volatility), "candle_score": weighted(candle, weights.candle), "sr_score": weighted(sr, weights.support_resistance)}
