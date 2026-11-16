import pandas as pd
import pytest

from immigration_forecast.cli import main
from immigration_forecast.pipeline import months_until, run_series

from conftest import write_ircc_workbook


def test_months_until(seasonal_series):  # last observed month: 2022-12
    assert months_until(seasonal_series, "2023-01") == 1
    assert months_until(seasonal_series, "2024-12") == 24
    with pytest.raises(ValueError):
        months_until(seasonal_series, "2022-12")


def test_run_series_picks_lowest_mae_and_forecasts(seasonal_series):
    result = run_series(seasonal_series, "2023-06", horizon=6, n_folds=3, step=3)
    assert result.best_model == result.metrics["mae"].idxmin()
    assert len(result.forecast) == 6
    assert result.forecast.index[-1] == pd.Timestamp("2023-06-01")


def test_cli_end_to_end(tmp_path, seasonal_series):
    """Full run on a fake workbook: load -> validate -> backtest -> forecast -> files."""
    n = len(seasonal_series)  # 96 months = 2015-2022
    values = [int(round(v / 5) * 5) for v in seasonal_series]
    countries = {
        "India": values,
        "Philippines": [int(round(v / 10 / 5) * 5) for v in seasonal_series],
        "Country not stated": [10] * n,
    }
    workbook = write_ircc_workbook(tmp_path / "in.xlsx", {y: 12 for y in range(2015, 2023)}, countries)

    main([
        "run", "--input", str(workbook),
        "--processed-dir", str(tmp_path / "processed"),
        "--reports-dir", str(tmp_path / "reports"),
        "--top", "2", "--forecast-end", "2023-06", "--horizon", "6", "--folds", "2",
    ])

    metrics = pd.read_csv(tmp_path / "reports" / "backtest_metrics.csv")
    assert set(metrics["series"]) == {"Canada (total)", "India", "Philippines"}
    assert set(metrics["model"]) == {"naive", "seasonal_naive", "ets", "sarima"}

    forecasts = pd.read_csv(tmp_path / "reports" / "forecasts.csv", parse_dates=["date"])
    assert len(forecasts) == 3 * 6
    assert (forecasts["lower"] <= forecasts["upper"]).all()

    assert (tmp_path / "processed" / "admissions_by_country_month.csv").exists()
    assert len(list((tmp_path / "reports" / "figures").glob("*.png"))) == 3
