"""Machine-learning forecaster: LightGBM on lag features.

A tree model cannot use "year" to extrapolate (that is why the old capstone's Random
Forest gave flat forecasts). Instead each month is described by what came before it:
last month, 2 and 3 months ago, 6 months ago, the same month last year, recent
averages, the calendar month and a COVID flag. The model learns how next month
relates to those, and forecasts several months ahead one step at a time, feeding
each prediction back in as the newest "last month" (recursive forecasting).
"""

import numpy as np
import pandas as pd

from .config import COVID_END, COVID_START
from .models import _LogModel, _frame, future_index

LAGS = (1, 2, 3, 6, 12)
MIN_HISTORY = max(LAGS)


def make_features(history: np.ndarray, date: pd.Timestamp) -> dict:
    """Features for the month `date`, using only `history` (values strictly before it).

    The same function builds training rows and forecast rows, so the model sees
    identical features in both places.
    """
    features = {f"lag_{k}": history[-k] for k in LAGS}
    features["mean_3"] = history[-3:].mean()
    features["mean_12"] = history[-12:].mean()
    features["month"] = date.month
    features["covid"] = float(pd.Timestamp(COVID_START) <= date <= pd.Timestamp(COVID_END))
    return features


class LightGBMForecaster(_LogModel):
    name = "lightgbm"

    def __init__(self, n_estimators: int = 300, learning_rate: float = 0.05, **kwargs):
        super().__init__(**kwargs)
        self.params = dict(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            num_leaves=7,  # small trees: only ~100 training rows
            min_child_samples=5,
            subsample=0.8,
            subsample_freq=1,
            random_state=42,
            verbose=-1,
        )

    def _fit(self, y):
        from lightgbm import LGBMRegressor

        if len(y) <= MIN_HISTORY + 12:
            raise ValueError(f"{self.name} needs more than {MIN_HISTORY + 12} months.")
        log_y = np.log(y.to_numpy())
        rows = [make_features(log_y[:t], y.index[t]) for t in range(MIN_HISTORY, len(y))]
        self._columns = list(rows[0])
        X = pd.DataFrame(rows, columns=self._columns)
        self._model = LGBMRegressor(**self.params).fit(X, log_y[MIN_HISTORY:])
        self._log_y = log_y
        # spread of month-to-month changes, used for an approximate interval
        self._sigma = np.diff(log_y).std()

    def _predict(self, horizon):
        idx = future_index(self._y, horizon)
        history = self._log_y.copy()
        preds = []
        for date in idx:
            X = pd.DataFrame([make_features(history, date)], columns=self._columns)
            next_value = float(self._model.predict(X)[0])
            preds.append(next_value)
            history = np.append(history, next_value)
        preds = np.array(preds)
        spread = self.z * self._sigma * np.sqrt(np.arange(1, horizon + 1))
        return _frame(idx, np.exp(preds), np.exp(preds - spread), np.exp(preds + spread))
