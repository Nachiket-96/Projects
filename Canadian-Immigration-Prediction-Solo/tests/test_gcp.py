"""BigQuery and Gemini code, tested with fake clients: no GCP project or network needed."""

import pandas as pd
import pytest

from immigration_forecast.cli import main
from immigration_forecast.gcp import bigquery as bq
from immigration_forecast.gcp.gemini import build_prompt, summarize_with_gemini

# ---------- BigQuery ----------


def test_table_ref_quotes_and_validates():
    assert bq.table_ref("my-proj", "ds_1", "t") == "`my-proj.ds_1.t`"
    for bad in ["proj; DROP TABLE x", "a`b", "", "p.q"]:
        with pytest.raises(ValueError):
            bq.table_ref(bad, "ds", "t")


def test_arima_plus_sql():
    create, forecast = bq.arima_plus_sql("`p.d.src`", "`p.d.m`", 16, 0.8)
    assert "model_type = 'ARIMA_PLUS'" in create and "time_series_id_col = 'series'" in create
    assert "FROM `p.d.src`" in create
    assert "ML.FORECAST(MODEL `p.d.m`, STRUCT(16 AS horizon, 0.8 AS confidence_level))" in forecast


def test_ai_forecast_sql():
    sql = bq.ai_forecast_sql("`p.d.src`", 16, 0.8)
    assert "AI.FORECAST(" in sql and "TABLE `p.d.src`" in sql
    assert "horizon => 16" in sql and "id_cols => ['series']" in sql and "model =>" not in sql
    assert "model => 'TimesFM 2.5'" in bq.ai_forecast_sql("`p.d.src`", 16, 0.8, "TimesFM 2.5")
    with pytest.raises(ValueError):
        bq.ai_forecast_sql("`p.d.src`", 16, 0.8, "x'); DROP")


def test_to_bigquery_frame(seasonal_series):
    frame = bq.to_bigquery_frame([seasonal_series, seasonal_series.rename("India")])
    assert list(frame.columns) == ["series", "date", "admissions"]
    assert len(frame) == 2 * len(seasonal_series)
    assert set(frame["series"]) == {"synthetic", "India"}


class FakeJob:
    def __init__(self, df=None):
        self.df = df

    def result(self):
        return self

    def to_dataframe(self):
        return self.df


class FakeBigQuery:
    def __init__(self):
        self.queries, self.datasets, self.loaded = [], [], None

    def create_dataset(self, dataset, exists_ok):
        self.datasets.append(dataset)

    def load_table_from_dataframe(self, df, table, job_config):
        self.loaded = (df, table)
        return FakeJob()

    def query(self, sql):
        self.queries.append(sql)
        if sql.startswith("CREATE"):
            return FakeJob()
        return FakeJob(
            pd.DataFrame(
                {
                    "series": ["Canada (total)"] * 2,
                    "forecast_timestamp": pd.to_datetime(["2026-09-01", "2026-10-01"], utc=True),
                    "forecast_value": [100.0, 110.0],
                    "prediction_interval_lower_bound": [90.0, 95.0],
                    "prediction_interval_upper_bound": [110.0, 125.0],
                }
            )
        )


def test_run_bigquery_forecasts_flow(monkeypatch, seasonal_series):
    monkeypatch.setattr(bq, "_load_job_config", lambda: None)
    client = FakeBigQuery()
    frame = bq.to_bigquery_frame([seasonal_series])
    out = bq.run_bigquery_forecasts(client, "proj", "ds", frame, horizon=2)

    assert client.datasets == ["proj.ds"]
    assert client.loaded[1] == "proj.ds.pr_admissions"
    assert [q.split()[0] for q in client.queries] == ["CREATE", "SELECT", "SELECT"]
    assert "ML.FORECAST" in client.queries[1] and "AI.FORECAST" in client.queries[2]

    assert list(out.columns) == ["series", "model", "date", "mean", "lower", "upper"]
    assert set(out["model"]) == {"bqml_arima_plus", "bq_ai_forecast_timesfm"}
    assert out["date"].dt.tz is None and out["date"].iloc[0] == pd.Timestamp("2026-09-01")


# ---------- Gemini ----------


@pytest.fixture
def reports():
    metrics = pd.DataFrame(
        {
            "series": ["Canada (total)", "Canada (total)"],
            "model": ["ets", "naive"],
            "mae": [5758.8, 6326.4],
            "rmse": [6883.5, 7773.5],
            "mape_pct": [17.0, 19.0],
            "interval_coverage_pct": [100.0, 97.9],
            "n_forecasts": [96, 96],
        }
    )
    forecasts = pd.DataFrame(
        {
            "series": ["Canada (total)"] * 3,
            "model": ["ets"] * 3,
            "date": pd.to_datetime(["2026-12-01", "2027-01-01", "2027-02-01"]),
            "mean": [33000.0, 39000.0, 40000.0],
            "lower": [22000.0, 25000.0, 25000.0],
            "upper": [49000.0, 60000.0, 64000.0],
        }
    )
    return metrics, forecasts


def test_prompt_contains_facts_and_rules(reports):
    prompt = build_prompt(*reports, "November 2026")
    assert "Canada (total),ets,5758.8,17.0,6326.4" in prompt  # best model row with naive MAE
    assert "Canada (total),2027,79000.0" in prompt  # yearly sum, rounded to hundreds
    assert "do not invent" in prompt and "Immigration Levels Plan" in prompt


class FakeGemini:
    def __init__(self, text):
        self.text, self.calls = text, []
        self.models = self

    def generate_content(self, model, contents):
        self.calls.append((model, contents))
        return type("Response", (), {"text": self.text})()


def test_summarize_with_gemini_uses_given_model():
    client = FakeGemini("Summary text")
    assert summarize_with_gemini("prompt", model="gemini-test", client=client) == "Summary text"
    assert client.calls == [("gemini-test", "prompt")]


def test_empty_gemini_response_is_an_error():
    with pytest.raises(RuntimeError):
        summarize_with_gemini("prompt", model="m", client=FakeGemini(""))


def test_cli_summarize_print_prompt(tmp_path, reports, capsys):
    metrics, forecasts = reports
    metrics.to_csv(tmp_path / "backtest_metrics.csv", index=False)
    forecasts.to_csv(tmp_path / "forecasts.csv", index=False)
    main(["summarize", "--reports-dir", str(tmp_path), "--print-prompt"])
    out = capsys.readouterr().out
    assert "November 2026" in out and "Canada (total)" in out
