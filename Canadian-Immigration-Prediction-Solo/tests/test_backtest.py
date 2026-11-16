import pandas as pd
import pytest

from immigration_forecast.backtest import backtest, rolling_origin_folds, summarize
from immigration_forecast.models import NaiveForecaster, SeasonalNaiveForecaster


def test_folds_walk_forward_and_end_on_last_month():
    idx = pd.date_range("2015-01-01", periods=60, freq="MS")
    folds = rolling_origin_folds(idx, horizon=12, n_folds=3, step=3, min_train=24)
    assert len(folds) == 3
    assert folds[-1].test_end == idx[-1]
    assert [f.train_end for f in folds] == sorted(f.train_end for f in folds)
    for f in folds:
        assert f.train_end < f.test_start
        assert (f.test_end.year - f.test_start.year) * 12 + f.test_end.month - f.test_start.month == 11


def test_folds_respect_min_train():
    idx = pd.date_range("2015-01-01", periods=40, freq="MS")
    folds = rolling_origin_folds(idx, horizon=12, n_folds=10, step=3, min_train=24)
    assert all(len(idx[idx <= f.train_end]) >= 24 for f in folds)
    with pytest.raises(ValueError):
        rolling_origin_folds(idx, horizon=12, n_folds=1, step=1, min_train=39)


def test_no_future_data_leaks_into_training(seasonal_series):
    seen = []

    class Spy(NaiveForecaster):
        def _fit(self, y):
            seen.append(y.index[-1])
            super()._fit(y)

    results = backtest(seasonal_series, {"spy": Spy}, horizon=6, n_folds=4, step=3, min_train=24)
    assert (results["date"] > results["train_end"]).all()
    assert sorted(seen) == sorted(results["train_end"].unique())


def test_backtest_rows_and_summary(seasonal_series):
    models = {"naive": NaiveForecaster, "seasonal_naive": SeasonalNaiveForecaster}
    results = backtest(seasonal_series, models, horizon=12, n_folds=3, step=3, min_train=24)
    assert len(results) == 2 * 3 * 12
    assert set(results["step_ahead"]) == set(range(1, 13))

    table = summarize(results)
    assert list(table.columns) == ["mae", "rmse", "mape_pct", "interval_coverage_pct", "n_forecasts"]
    assert table.index[0] == "seasonal_naive"  # strongly seasonal data: seasonal naive should win
    assert table["mae"].is_monotonic_increasing
