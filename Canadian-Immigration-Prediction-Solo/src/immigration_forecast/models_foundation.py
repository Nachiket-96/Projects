"""Foundation-model forecaster: Google's TimesFM 2.5.

TimesFM is a 200M-parameter transformer that Google pre-trained on a very large
collection of real and synthetic time series. It is used "zero-shot": nothing is
trained on our data. fit() only remembers the history; predict() hands that history
to the pre-trained model, which returns a median forecast and quantiles.

The same model family powers BigQuery's AI.FORECAST function (see gcp/bigquery.py).
"""

import numpy as np

from .models import Forecaster, _frame, future_index

REPO_ID = "google/timesfm-2.5-200m-pytorch"
MAX_CONTEXT = 512  # months of history the model may look at (multiple of its 32-step patch)
MAX_HORIZON = 128
# TimesFM returns [mean, q0.1, q0.2, ..., q0.9] in its quantile output
QUANTILE_COLUMNS = {0.1: 1, 0.2: 2, 0.3: 3, 0.4: 4, 0.5: 5, 0.6: 6, 0.7: 7, 0.8: 8, 0.9: 9}

_MODEL = None  # loaded once per process; loading takes seconds, forecasting milliseconds


def load_model():
    global _MODEL
    if _MODEL is None:
        import timesfm

        model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(REPO_ID)
        model.compile(
            timesfm.ForecastConfig(
                max_context=MAX_CONTEXT,
                max_horizon=MAX_HORIZON,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                fix_quantile_crossing=True,
            )
        )
        _MODEL = model
    return _MODEL


class TimesFMForecaster(Forecaster):
    name = "timesfm"

    def _fit(self, y):
        lower_q = round(self.alpha / 2, 2)
        if lower_q not in QUANTILE_COLUMNS or round(1 - lower_q, 2) not in QUANTILE_COLUMNS:
            raise ValueError(f"TimesFM only provides deciles; alpha={self.alpha} is not supported.")
        self._lower_col = QUANTILE_COLUMNS[lower_q]
        self._upper_col = QUANTILE_COLUMNS[round(1 - lower_q, 2)]

    def _predict(self, horizon):
        if horizon > MAX_HORIZON:
            raise ValueError(f"horizon must be at most {MAX_HORIZON}")
        point, quantiles = load_model().forecast(horizon=horizon, inputs=[self._y.to_numpy(dtype=float)])
        return _frame(
            future_index(self._y, horizon),
            np.asarray(point[0]),
            np.asarray(quantiles[0, :, self._lower_col]),
            np.asarray(quantiles[0, :, self._upper_col]),
        )
