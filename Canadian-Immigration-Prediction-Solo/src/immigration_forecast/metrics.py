"""Forecast error metrics. Lower is better for all of them."""

import numpy as np


def _arrays(actual, forecast):
    a = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)
    if a.shape != f.shape or a.size == 0:
        raise ValueError("actual and forecast must be non-empty and the same length")
    return a, f


def mae(actual, forecast) -> float:
    """Mean absolute error, in admissions per month."""
    a, f = _arrays(actual, forecast)
    return float(np.mean(np.abs(a - f)))


def rmse(actual, forecast) -> float:
    """Root mean squared error: like MAE but punishes big misses more."""
    a, f = _arrays(actual, forecast)
    return float(np.sqrt(np.mean((a - f) ** 2)))


def mape(actual, forecast) -> float:
    """Mean absolute percentage error, in %. Months with zero actuals are skipped."""
    a, f = _arrays(actual, forecast)
    nonzero = a != 0
    if not nonzero.any():
        raise ValueError("MAPE is undefined when every actual value is zero")
    return float(np.mean(np.abs((a[nonzero] - f[nonzero]) / a[nonzero])) * 100)


def coverage(actual, lower, upper) -> float:
    """Share of actuals that fell inside the prediction interval, in %."""
    a, lo = _arrays(actual, lower)
    _, hi = _arrays(actual, upper)
    return float(np.mean((a >= lo) & (a <= hi)) * 100)
