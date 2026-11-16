"""Backtest every model on a series, pick the best one, refit it on all data, forecast."""

from dataclasses import dataclass

import pandas as pd

from .backtest import backtest, summarize
from .models import MODELS


@dataclass
class SeriesResult:
    series: str
    metrics: pd.DataFrame  # one row per model, best first
    best_model: str
    forecast: pd.DataFrame  # mean / lower / upper for the future months


def months_until(y: pd.Series, end: str) -> int:
    """Number of months from the month after the last observation up to and including `end`."""
    end = pd.Timestamp(end)
    last = y.index[-1]
    months = (end.year - last.year) * 12 + (end.month - last.month)
    if months < 1:
        raise ValueError(f"Forecast end {end:%Y-%m} is not after the last observed month {last:%Y-%m}.")
    return months


def run_series(
    y: pd.Series,
    forecast_end: str,
    horizon: int = 12,
    n_folds: int = 8,
    step: int = 3,
    models: dict | None = None,
) -> SeriesResult:
    models = models or MODELS
    results = backtest(y, models, horizon=horizon, n_folds=n_folds, step=step)
    metrics = summarize(results)
    best = metrics.index[0]
    forecast = models[best]().fit(y).predict(months_until(y, forecast_end))
    return SeriesResult(series=str(y.name), metrics=metrics, best_model=best, forecast=forecast)
