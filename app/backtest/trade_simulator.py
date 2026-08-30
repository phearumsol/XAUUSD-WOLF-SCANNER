"""Fixed-horizon directional outcome measurements, not order simulation."""
from __future__ import annotations
import pandas as pd

def outcomes(data: pd.DataFrame, index: int, direction: str, entry: float, horizons: list[int], costs: float) -> tuple[dict[int, float | None], dict[int, float | None], dict[int, float | None]]:
    returns: dict[int, float | None] = {}; mfe: dict[int, float | None] = {}; mae: dict[int, float | None] = {}
    for horizon in horizons:
        future = data.iloc[index + 1:index + 1 + horizon]
        if len(future) < horizon: returns[horizon] = mfe[horizon] = mae[horizon] = None; continue
        sign = 1 if direction == "BUY" else -1
        returns[horizon] = sign * (float(future.iloc[-1].close) / entry - 1) - costs
        favorable = (float(future.high.max()) / entry - 1) if sign == 1 else (1 - float(future.low.min()) / entry)
        adverse = (float(future.low.min()) / entry - 1) if sign == 1 else (1 - float(future.high.max()) / entry)
        mfe[horizon], mae[horizon] = favorable, adverse
    return returns, mfe, mae
