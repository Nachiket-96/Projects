"""Rolling-origin backtesting: the honest way to score a time-series model.

For each fold the model sees ONLY the months up to the fold's origin, then
forecasts the next `horizon` months, which are compared with what happened.
A random train/test split would let the model peek at the future (leakage).

    fold 1: train [=========]  test [-----]
    fold 2: train [===========]  test [-----]
    fold 3: train [=============]  test [-----]
"""

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .metrics import coverage, mae, mape, rmse
from .models import Forecaster, check_series


@dataclass(frozen=True)
class Fold:
    train_end: pd.Timestamp  # last month the model is allowed to see
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def rolling_origin_folds(
    index: pd.DatetimeIndex, horizon: int, n_folds: int, step: int, min_train: int
) -> list[Fold]:
    """Folds ordered oldest to newest. The newest fold's test window ends on the last month."""
    if horizon < 1 or n_folds < 1 or step < 1:
        raise ValueError("horizon, n_folds and step must be at least 1")
    folds = []
    for k in range(n_folds):
        test_end_pos = len(index) - 1 - k * step
        train_end_pos = test_end_pos - horizon
        if train_end_pos + 1 < min_train:
            break
        folds.append(Fold(index[train_end_pos], index[train_end_pos + 1], index[test_end_pos]))
    if not folds:
        raise ValueError("Series is too short for even one fold with these settings.")
    return folds[::-1]


def backtest(
    y: pd.Series,
    models: dict[str, Callable[[], Forecaster]],
    horizon: int = 12,
    n_folds: int = 8,
    step: int = 3,
    min_train: int = 48,
) -> pd.DataFrame:
    """One row per (model, fold, forecast month) with the actual and forecast values."""
    check_series(y)
    rows = []
    for fold in rolling_origin_folds(y.index, horizon, n_folds, step, min_train):
        train = y.loc[: fold.train_end]
        actual = y.loc[fold.test_start : fold.test_end]
        for name, make_model in models.items():
            forecast = make_model().fit(train).predict(len(actual))
            for step_ahead, (date, row) in enumerate(forecast.iterrows(), start=1):
                rows.append(
                    {
                        "model": name,
                        "train_end": fold.train_end,
                        "date": date,
                        "step_ahead": step_ahead,
                        "actual": actual.loc[date],
                        "forecast": row["mean"],
                        "lower": row["lower"],
                        "upper": row["upper"],
                    }
                )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    """Error metrics per model, best (lowest MAE) first."""

    def score(g):
        return pd.Series(
            {
                "mae": mae(g["actual"], g["forecast"]),
                "rmse": rmse(g["actual"], g["forecast"]),
                "mape_pct": mape(g["actual"], g["forecast"]),
                "interval_coverage_pct": coverage(g["actual"], g["lower"], g["upper"]),
                "n_forecasts": len(g),
            }
        )

    table = results.groupby("model")[["actual", "forecast", "lower", "upper"]].apply(score)
    return table.sort_values("mae")
