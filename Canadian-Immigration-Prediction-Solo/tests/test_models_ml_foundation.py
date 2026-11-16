import os

import numpy as np
import pandas as pd
import pytest

from immigration_forecast.metrics import mae
from immigration_forecast.models import MODELS, NaiveForecaster, get_models


def test_get_models_classical_and_unknown():
    assert get_models(["naive", "ets"]) == {"naive": MODELS["naive"], "ets": MODELS["ets"]}
    with pytest.raises(ValueError, match="Unknown model"):
        get_models(["prophet"])


# ---------- LightGBM ----------

lightgbm = pytest.importorskip("lightgbm", reason="optional extra [ml] not installed")
from immigration_forecast.models_ml import LightGBMForecaster, make_features  # noqa: E402


def test_features_use_only_the_past():
    history = np.arange(1.0, 25.0)  # values for 24 months
    f = make_features(history, pd.Timestamp("2020-04-01"))
    assert f["lag_1"] == 24 and f["lag_12"] == 13
    assert f["mean_3"] == pytest.approx(23)
    assert f["month"] == 4 and f["covid"] == 1.0


def test_lightgbm_output_and_beats_naive(seasonal_series):
    train, test = seasonal_series.iloc[:-12], seasonal_series.iloc[-12:]
    fc = LightGBMForecaster().fit(train).predict(12)
    assert list(fc.columns) == ["mean", "lower", "upper"] and len(fc) == 12
    assert (fc["lower"] <= fc["mean"]).all() and (fc["mean"] <= fc["upper"]).all()
    assert mae(test, fc["mean"]) < mae(test, NaiveForecaster().fit(train).predict(12)["mean"])


def test_lightgbm_needs_enough_history(seasonal_series):
    with pytest.raises(ValueError, match="needs more than"):
        LightGBMForecaster().fit(seasonal_series.iloc[:20])


def test_lightgbm_is_reproducible(seasonal_series):
    a = LightGBMForecaster().fit(seasonal_series).predict(6)
    b = LightGBMForecaster().fit(seasonal_series).predict(6)
    pd.testing.assert_frame_equal(a, b)


# ---------- TimesFM (logic tested with a fake model; real model only with RUN_SLOW=1) ----------


class FakeTimesFM:
    def __init__(self):
        self.calls = []

    def forecast(self, horizon, inputs):
        self.calls.append((horizon, inputs))
        last = inputs[0][-1]
        point = np.full((1, horizon), last)
        quantiles = np.stack([last + np.arange(-5, 5) * 10.0] * horizon)[None]  # col 0 = mean, 1..9 = q0.1..q0.9
        return point, quantiles


def test_timesfm_maps_deciles_to_80pct_interval(monkeypatch, seasonal_series):
    from immigration_forecast import models_foundation

    fake = FakeTimesFM()
    monkeypatch.setattr(models_foundation, "load_model", lambda: fake)
    fc = models_foundation.TimesFMForecaster().fit(seasonal_series).predict(3)
    last = seasonal_series.iloc[-1]
    assert np.allclose(fc["mean"], last)
    assert np.allclose(fc["lower"], last - 40)  # q0.1 -> column 1
    assert np.allclose(fc["upper"], last + 40)  # q0.9 -> column 9
    assert len(fake.calls[0][1][0]) == len(seasonal_series)  # whole history passed, nothing trained


def test_timesfm_rejects_unsupported_interval(seasonal_series):
    from immigration_forecast.models_foundation import TimesFMForecaster

    with pytest.raises(ValueError, match="deciles"):
        TimesFMForecaster(alpha=0.05).fit(seasonal_series)


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="downloads ~800MB model; set RUN_SLOW=1")
def test_real_timesfm_beats_naive(seasonal_series):
    pytest.importorskip("timesfm")
    from immigration_forecast.models_foundation import TimesFMForecaster

    train, test = seasonal_series.iloc[:-12], seasonal_series.iloc[-12:]
    fc = TimesFMForecaster().fit(train).predict(12)
    assert mae(test, fc["mean"]) < mae(test, NaiveForecaster().fit(train).predict(12)["mean"])
