import numpy as np
import pandas as pd
import pytest

from immigration_forecast.metrics import mae
from immigration_forecast.models import (
    MODELS,
    ETSForecaster,
    NaiveForecaster,
    SARIMAForecaster,
    SeasonalNaiveForecaster,
)


def test_naive_repeats_last_value(seasonal_series):
    fc = NaiveForecaster().fit(seasonal_series).predict(3)
    assert (fc["mean"] == seasonal_series.iloc[-1]).all()


def test_seasonal_naive_repeats_last_year(seasonal_series):
    fc = SeasonalNaiveForecaster().fit(seasonal_series).predict(15)
    last_year = seasonal_series.iloc[-12:].to_numpy()
    np.testing.assert_allclose(fc["mean"].iloc[:12], last_year)
    np.testing.assert_allclose(fc["mean"].iloc[12:], last_year[:3])


def test_baseline_intervals_widen_with_horizon(seasonal_series):
    fc = NaiveForecaster().fit(seasonal_series).predict(6)
    width = fc["upper"] - fc["lower"]
    assert width.is_monotonic_increasing and width.iloc[-1] > width.iloc[0]


@pytest.mark.parametrize("name", list(MODELS))
def test_every_model_output_shape(name, seasonal_series):
    fc = MODELS[name]().fit(seasonal_series).predict(12)
    assert list(fc.columns) == ["mean", "lower", "upper"]
    assert len(fc) == 12
    assert fc.index[0] == pd.Timestamp("2023-01-01") and fc.index.freqstr == "MS"
    assert not fc.isna().any().any()
    assert (fc["lower"] <= fc["mean"]).all() and (fc["mean"] <= fc["upper"]).all()
    assert (fc >= 0).all().all()


@pytest.mark.parametrize("model_cls", [ETSForecaster, SARIMAForecaster])
def test_statistical_models_beat_naive_on_seasonal_data(model_cls, seasonal_series):
    train, test = seasonal_series.iloc[:-12], seasonal_series.iloc[-12:]
    model_error = mae(test, model_cls().fit(train).predict(12)["mean"])
    naive_error = mae(test, NaiveForecaster().fit(train).predict(12)["mean"])
    assert model_error < naive_error


def test_predict_before_fit_fails():
    with pytest.raises(RuntimeError):
        NaiveForecaster().predict(3)


def test_series_must_be_monthly_without_gaps(seasonal_series):
    with pytest.raises(ValueError, match="monthly"):
        NaiveForecaster().fit(seasonal_series.reset_index(drop=True))
    gappy = seasonal_series.copy()
    gappy.iloc[5] = np.nan
    with pytest.raises(ValueError, match="missing"):
        NaiveForecaster().fit(gappy)


def test_log_models_need_positive_values(seasonal_series):
    y = seasonal_series.copy()
    y.iloc[10] = 0
    with pytest.raises(ValueError, match="positive"):
        ETSForecaster().fit(y)


def test_covid_dummy_window():
    idx = pd.date_range("2020-01-01", "2021-08-01", freq="MS")
    dummy = SARIMAForecaster.covid_dummy(idx)
    assert dummy["2020-02-01"] == 0 and dummy["2020-03-01"] == 1
    assert dummy["2021-05-01"] == 1 and dummy["2021-06-01"] == 0
