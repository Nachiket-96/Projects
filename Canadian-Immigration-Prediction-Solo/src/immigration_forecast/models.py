"""Forecasting models behind one small interface.

Every model:
  fit(y)          y = monthly pd.Series with a "MS" DatetimeIndex and no gaps
  predict(h)      DataFrame indexed by the next h months, columns mean / lower / upper

Baselines come first on purpose: a model is only worth using if it beats them.
"""

import warnings
from abc import ABC, abstractmethod
from statistics import NormalDist

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .config import COVID_END, COVID_START, INTERVAL_ALPHA, SEASON_LENGTH


def check_series(y: pd.Series) -> None:
    if not isinstance(y.index, pd.DatetimeIndex) or y.index.freqstr != "MS":
        raise ValueError("Series needs a monthly ('MS') DatetimeIndex.")
    if y.isna().any():
        raise ValueError("Series contains missing values.")


def future_index(y: pd.Series, horizon: int) -> pd.DatetimeIndex:
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    return pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")


def _frame(index, mean, lower, upper) -> pd.DataFrame:
    out = pd.DataFrame({"mean": mean, "lower": lower, "upper": upper}, index=index)
    out.index.name = "date"
    return out.clip(lower=0)  # admissions cannot be negative


class Forecaster(ABC):
    name: str = "forecaster"

    def __init__(self, alpha: float = INTERVAL_ALPHA):
        self.alpha = alpha
        self._y = None

    @property
    def z(self) -> float:
        return NormalDist().inv_cdf(1 - self.alpha / 2)

    def fit(self, y: pd.Series) -> "Forecaster":
        check_series(y)
        self._y = y
        self._fit(y)
        return self

    def predict(self, horizon: int) -> pd.DataFrame:
        if self._y is None:
            raise RuntimeError(f"{self.name}: call fit() before predict().")
        return self._predict(horizon)

    def _fit(self, y: pd.Series) -> None:
        pass

    @abstractmethod
    def _predict(self, horizon: int) -> pd.DataFrame: ...


class NaiveForecaster(Forecaster):
    """Every future month = the last observed month."""

    name = "naive"

    def _fit(self, y):
        self._sigma = y.diff().std()

    def _predict(self, horizon):
        idx = future_index(self._y, horizon)
        mean = np.full(horizon, self._y.iloc[-1])
        spread = self.z * self._sigma * np.sqrt(np.arange(1, horizon + 1))
        return _frame(idx, mean, mean - spread, mean + spread)


class SeasonalNaiveForecaster(Forecaster):
    """Every future month = the same month one year earlier."""

    name = "seasonal_naive"

    def __init__(self, season_length: int = SEASON_LENGTH, **kwargs):
        super().__init__(**kwargs)
        self.season_length = season_length

    def _fit(self, y):
        if len(y) < self.season_length:
            raise ValueError(f"{self.name} needs at least {self.season_length} observations.")
        self._sigma = (y - y.shift(self.season_length)).std()

    def _predict(self, horizon):
        idx = future_index(self._y, horizon)
        last_season = self._y.iloc[-self.season_length :].to_numpy()
        steps = np.arange(horizon)
        mean = last_season[steps % self.season_length]
        spread = self.z * self._sigma * np.sqrt(steps // self.season_length + 1)
        return _frame(idx, mean, mean - spread, mean + spread)


class _LogModel(Forecaster):
    """Base for models fitted on log(y): keeps forecasts positive and turns
    multiplicative seasonality (bigger swings in bigger years) into additive."""

    def fit(self, y):
        check_series(y)
        if (y <= 0).any():
            raise ValueError(f"{self.name} needs strictly positive values (it models log(y)).")
        return super().fit(y)


class ETSForecaster(_LogModel):
    """Exponential smoothing: damped additive trend + additive yearly seasonality, on log(y)."""

    name = "ets"

    def _fit(self, y):
        model = ETSModel(
            np.log(y),
            error="add",
            trend="add",
            damped_trend=True,
            seasonal="add",
            seasonal_periods=SEASON_LENGTH,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self._result = model.fit(disp=False)

    def _predict(self, horizon):
        n = len(self._y)
        frame = self._result.get_prediction(start=n, end=n + horizon - 1).summary_frame(alpha=self.alpha)
        return _frame(
            future_index(self._y, horizon),
            np.exp(frame["mean"].to_numpy()),
            np.exp(frame["pi_lower"].to_numpy()),
            np.exp(frame["pi_upper"].to_numpy()),
        )


class SARIMAForecaster(_LogModel):
    """Seasonal ARIMA (1,1,1)(0,1,1)12 on log(y), with a COVID dummy so the
    2020-21 collapse is not read as a normal pattern."""

    name = "sarima"

    def __init__(self, order=(1, 1, 1), seasonal_order=(0, 1, 1, SEASON_LENGTH), **kwargs):
        super().__init__(**kwargs)
        self.order = order
        self.seasonal_order = seasonal_order

    @staticmethod
    def covid_dummy(index: pd.DatetimeIndex) -> pd.Series:
        return pd.Series(((index >= COVID_START) & (index <= COVID_END)).astype(float), index=index, name="covid")

    def _fit(self, y):
        exog = self.covid_dummy(y.index)
        self._use_exog = bool(exog.any())  # a column of zeros cannot be estimated
        model = SARIMAX(
            np.log(y),
            exog=exog if self._use_exog else None,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            warnings.simplefilter("ignore", UserWarning)
            self._result = model.fit(disp=False)

    def _predict(self, horizon):
        idx = future_index(self._y, horizon)
        exog = self.covid_dummy(idx) if self._use_exog else None
        frame = self._result.get_forecast(steps=horizon, exog=exog).summary_frame(alpha=self.alpha)
        return _frame(
            idx,
            np.exp(frame["mean"].to_numpy()),
            np.exp(frame["mean_ci_lower"].to_numpy()),
            np.exp(frame["mean_ci_upper"].to_numpy()),
        )


MODELS = {
    cls.name: cls
    for cls in (NaiveForecaster, SeasonalNaiveForecaster, ETSForecaster, SARIMAForecaster)
}

# Models whose libraries are optional extras: name -> (module, class, pip extra)
OPTIONAL_MODELS = {
    "lightgbm": ("models_ml", "LightGBMForecaster", "ml"),
    "timesfm": ("models_foundation", "TimesFMForecaster", "foundation"),
}
_OPTIONAL_IMPORTS = {"lightgbm": "lightgbm", "timesfm": "timesfm"}


def get_models(names: list[str]) -> dict:
    """Name -> model class for the requested models, with a clear error for missing extras."""
    import importlib

    selected = {}
    for name in names:
        if name in MODELS:
            selected[name] = MODELS[name]
        elif name in OPTIONAL_MODELS:
            module, cls, extra = OPTIONAL_MODELS[name]
            try:
                importlib.import_module(_OPTIONAL_IMPORTS[name])
            except ImportError as err:
                raise ImportError(f"Model {name!r} needs: pip install -e \".[{extra}]\"") from err
            selected[name] = getattr(importlib.import_module(f"{__package__}.{module}"), cls)
        else:
            raise ValueError(f"Unknown model {name!r}. Choose from {sorted(MODELS) + sorted(OPTIONAL_MODELS)}")
    return selected
