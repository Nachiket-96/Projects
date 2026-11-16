"""Run the forecasts inside Google BigQuery, the way a GCP data team would in production.

Two in-database methods, both driven by plain SQL:
  - BigQuery ML ARIMA_PLUS: trains one auto-ARIMA model per series (ML.FORECAST)
  - AI.FORECAST: Google's pre-trained TimesFM model, no training at all

Results come back in the same columns as the local models (date, mean, lower, upper).
"""

import re

import pandas as pd

_IDENTIFIER = re.compile(r"[A-Za-z0-9_\-]+")

OUTPUT_COLUMNS = {
    "forecast_timestamp": "date",
    "forecast_value": "mean",
    "prediction_interval_lower_bound": "lower",
    "prediction_interval_upper_bound": "upper",
}


def table_ref(project: str, dataset: str, name: str) -> str:
    """`project.dataset.name`, rejecting anything that could break out of the identifier."""
    for part in (project, dataset, name):
        if not _IDENTIFIER.fullmatch(part or ""):
            raise ValueError(f"Invalid BigQuery identifier: {part!r}")
    return f"`{project}.{dataset}.{name}`"


def to_bigquery_frame(series: list[pd.Series]) -> pd.DataFrame:
    """Long table (series, date, admissions) with one row per series and month."""
    frames = [
        pd.DataFrame({"series": y.name, "date": y.index.date, "admissions": y.to_numpy(dtype=float)})
        for y in series
    ]
    return pd.concat(frames, ignore_index=True)


def arima_plus_sql(source: str, model: str, horizon: int, confidence: float) -> tuple[str, str]:
    create = f"""
CREATE OR REPLACE MODEL {model}
OPTIONS (
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'date',
  time_series_data_col = 'admissions',
  time_series_id_col = 'series',
  data_frequency = 'MONTHLY',
  auto_arima = TRUE
) AS
SELECT series, date, admissions FROM {source}
""".strip()
    forecast = f"""
SELECT series, forecast_timestamp, forecast_value,
       prediction_interval_lower_bound, prediction_interval_upper_bound
FROM ML.FORECAST(MODEL {model}, STRUCT({int(horizon)} AS horizon, {float(confidence)} AS confidence_level))
""".strip()
    return create, forecast


def ai_forecast_sql(source: str, horizon: int, confidence: float, model_name: str | None = None) -> str:
    model_arg = f",\n  model => '{model_name}'" if model_name else ""
    if model_name and not re.fullmatch(r"[A-Za-z0-9 .]+", model_name):
        raise ValueError(f"Invalid model name: {model_name!r}")
    return f"""
SELECT series, forecast_timestamp, forecast_value,
       prediction_interval_lower_bound, prediction_interval_upper_bound
FROM AI.FORECAST(
  TABLE {source},
  data_col => 'admissions',
  timestamp_col => 'date',
  id_cols => ['series'],
  horizon => {int(horizon)},
  confidence_level => {float(confidence)}{model_arg}
)
""".strip()


def standardize(df: pd.DataFrame, method: str) -> pd.DataFrame:
    out = df.rename(columns=OUTPUT_COLUMNS)[["series", "date", "mean", "lower", "upper"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    out.insert(1, "model", method)
    return out.sort_values(["series", "date"]).reset_index(drop=True)


def _load_job_config():
    from google.cloud import bigquery

    return bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")


def run_bigquery_forecasts(
    client,
    project: str,
    dataset: str,
    frame: pd.DataFrame,
    horizon: int,
    confidence: float = 0.8,
    timesfm_model: str | None = None,
) -> pd.DataFrame:
    """Upload the series, forecast with ARIMA_PLUS and AI.FORECAST, return both."""
    source = table_ref(project, dataset, "pr_admissions")
    model = table_ref(project, dataset, "pr_admissions_arima_plus")

    client.create_dataset(f"{project}.{dataset}", exists_ok=True)
    client.load_table_from_dataframe(frame, source.strip("`"), job_config=_load_job_config()).result()

    create, forecast = arima_plus_sql(source, model, horizon, confidence)
    client.query(create).result()
    arima = standardize(client.query(forecast).to_dataframe(), "bqml_arima_plus")
    timesfm = standardize(
        client.query(ai_forecast_sql(source, horizon, confidence, timesfm_model)).to_dataframe(),
        "bq_ai_forecast_timesfm",
    )
    return pd.concat([arima, timesfm], ignore_index=True)
