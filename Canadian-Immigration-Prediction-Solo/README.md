# Canadian Immigration Prediction — Solo Rebuild

Forecasts **monthly permanent resident (PR) admissions to Canada**, nationally and for the
largest source countries, from official IRCC open data. Six models — from simple baselines to
Google's **TimesFM** foundation model — are compared with **rolling-origin backtesting**, and the
same forecasts can run inside **Google BigQuery**, with **Gemini** writing a plain-language briefing.

This is a solo rebuild of an earlier group capstone (`../Canadian immigration prediction/`,
left unchanged). See [What changed from the capstone](#what-changed-from-the-capstone).
For a non-technical explanation of every model and metric, read
**[docs/model-guide.md](docs/model-guide.md)**.

## Data

| | |
|---|---|
| Source | IRCC — *Permanent Residents – Monthly IRCC Updates*, [open.canada.ca dataset](https://open.canada.ca/data/en/dataset/f7e5498e-0ad8-4417-85c9-9b8aff9b9eda) |
| File | `EN_ODP-PR-Citz.xlsx` — admissions by country of citizenship |
| Coverage | Jan 2015 – Aug 2026 (140 months), 216 countries + "Country not stated" |
| Licence | Open Government Licence – Canada |

The workbook is a formatted report, not a table: three header rows (year / quarter / month),
quarter and year totals mixed between month columns, a `Total` row and footnotes, counts
stored as text (`"2,630"`), every value rounded to a multiple of 5, and values 0–5 hidden as
`--`. `load.py` reads only the month columns and keeps suppression as an explicit flag.

## Architecture

```
            IRCC open data (.xlsx)
                    │  download.py
                    ▼
   load.py ──► validate.py ──► series.py          tidy data, quality gate, series selection
                    │
        ┌───────────┴─────────────────────────────┐
        ▼  local (Python)                          ▼  Google Cloud
   models*.py  6 forecasters                  gcp/bigquery.py
   backtest.py rolling-origin scoring           BigQuery ML ARIMA_PLUS
   pipeline.py pick best → forecast             AI.FORECAST (TimesFM)
        │                                          │
        ▼                                          ▼
   reports/  metrics, forecasts, charts ──► gcp/gemini.py  plain-language briefing
```

```
Canadian-Immigration-Prediction-Solo/
├── pyproject.toml              package, optional extras [ml] [foundation] [gcp], pytest settings
├── requirements.txt            exact versions it was tested with
├── docs/model-guide.md         non-technical guide to the models, metrics and results
├── data/raw, data/processed    downloaded and generated data (git-ignored)
├── reports/                    backtest_metrics.csv, forecasts.csv, figures/
├── src/immigration_forecast/
│   ├── config.py               paths and constants (COVID window, interval level)
│   ├── download.py             fetch the workbook, verify it is a real .xlsx
│   ├── load.py                 wide report sheet -> tidy (country, month, admissions, suppressed)
│   ├── validate.py             quality gate: duplicates, gaps, negatives, rounding drift
│   ├── series.py               national series, per-country series, top-N countries
│   ├── models.py               interface + naive, seasonal naive, ETS, SARIMA; model registry
│   ├── models_ml.py            LightGBM on lag features (recursive)
│   ├── models_foundation.py    TimesFM 2.5 zero-shot
│   ├── metrics.py              MAE, RMSE, MAPE, interval coverage
│   ├── backtest.py             rolling-origin folds, no future data in training
│   ├── pipeline.py             backtest -> pick lowest MAE -> refit on all data -> forecast
│   ├── plotting.py             forecast chart
│   ├── gcp/bigquery.py         upload + ARIMA_PLUS + AI.FORECAST in BigQuery
│   ├── gcp/gemini.py           prompt with exact figures -> Gemini briefing
│   └── cli.py                  download / run / bq-forecast / summarize
└── tests/                      75 pytest tests
```

## How to run

```bash
cd Canadian-Immigration-Prediction-Solo
python -m venv .venv
.venv\Scripts\activate                       # macOS/Linux: source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch   # CPU build, for TimesFM
pip install -e ".[all]"

python -m immigration_forecast download
python -m immigration_forecast run --models naive,seasonal_naive,ets,sarima,lightgbm,timesfm
pytest                                       # RUN_SLOW=1 pytest also runs the real TimesFM test
```

`run` defaults to the four classical models, which need no extras. The first TimesFM run
downloads the model (~800 MB) from Hugging Face; later runs use the local cache.

### Google Cloud (optional)

Credentials come from the environment; nothing is stored in the project.

```bash
gcloud auth application-default login
python -m immigration_forecast bq-forecast --project YOUR_PROJECT_ID   # -> reports/bigquery_forecasts.csv

export GEMINI_API_KEY=...        # or Vertex AI: GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION
python -m immigration_forecast summarize                # -> reports/summary_gemini.md
python -m immigration_forecast summarize --print-prompt # see exactly what is sent, no API call
```

`bq-forecast` uploads the series to a BigQuery table, trains BigQuery ML `ARIMA_PLUS` models
(one per series) and calls `AI.FORECAST`, which runs TimesFM inside BigQuery without training.
`summarize` sends only the result tables to Gemini, with instructions to use those numbers only.

> **Verification status:** the BigQuery and Gemini code is covered by unit tests with fake
> clients (SQL text, call order, output shape). It has not yet been run against a real GCP
> project, because none was available while building this.

## Models

| Model | Family | Idea |
|---|---|---|
| `naive` | baseline | next months = last month |
| `seasonal_naive` | baseline | next months = same month last year |
| `ets` | statistical | exponential smoothing, damped trend + yearly seasonality, on log scale |
| `sarima` | statistical | seasonal ARIMA (1,1,1)(0,1,1)12 on log scale, with a COVID dummy |
| `lightgbm` | machine learning | gradient-boosted trees on lags (1, 2, 3, 6, 12 months), recent averages, month, COVID flag; forecasts recursively |
| `timesfm` | foundation model | Google TimesFM 2.5 (200M parameters), pre-trained, used zero-shot |

**Evaluation**: 8 folds, origins 3 months apart; each fold trains only on data up to its origin
and forecasts the next 12 months (latest fold: Sep 2025 – Aug 2026). 96 forecasts per model per
series. The lowest-MAE model is refitted on all data and forecasts Sep 2026 – Dec 2027.

## Results (data release of August 31, 2026)

Backtest error, 12-month-ahead monthly forecasts (`reports/backtest_metrics.csv`):

| Series | Best model | MAE / month | MAPE | Beats naive by | 80% interval coverage |
|---|---|---|---|---|---|
| **Canada (total)** | **timesfm** | 5,348 | **16.7%** | 15% | 92.7% |
| India | lightgbm | 2,053 | 25.3% | 19% | 99.0% |
| Philippines | sarima | 472 | 20.5% | 16% | 84.4% |
| Cameroon | lightgbm | 389 | 22.0% | 23% | 100% |
| China | ets | 480 | 25.6% | 8% | 93.8% |
| Nigeria | timesfm | 295 | 20.0% | 7% | 89.6% |

National forecast with TimesFM: about **150,000** admissions for Sep–Dec 2026 and about
**435,000** for 2027 (`reports/figures/forecast_canada_total.png`).

**Reading this honestly**

- No single model wins everywhere — that is why every series is backtested separately.
  TimesFM, with no training on this data, was best for the national total and Nigeria.
- The gain over the naive baseline is modest (7–23%). Admissions follow government targets
  and processing capacity, which a model of past values cannot see.
- Intervals are mostly conservative (coverage above 80%). TimesFM's are the best calibrated
  for the national series. LightGBM's intervals are a rough approximation and very wide.
- The model does not know the federal **Immigration Levels Plan**; compare forecasts with the
  published targets before using them.

## Limitations

- **Policy-driven series**: targets for 2025–2026 were cut; models trained on 2021–2024 growth
  can over-forecast. Adding Levels Plan targets as an input (e.g. `ARIMA_PLUS_XREG` or TimesFM
  covariates) is the next step.
- **Short history**: 140 months, with a COVID shock and a 2021 catch-up surge inside it.
- **Rounding and suppression**: values rounded to 5; 12.7% of country-months hidden as `--`.
  Countries with any suppressed month are not modelled.
- **Preliminary data**: IRCC revises recent months; a newer file can change results.

## What changed from the capstone

| Old capstone | This rebuild |
|---|---|
| Final "Ridge" and "Random Forest updated" results trained on **simulated random data** | Only official IRCC data |
| Random `train_test_split` on years (future leaked into training) | Rolling-origin backtest; a test checks no fold trains on future months |
| Random Forest on `year` → flat forecasts (trees cannot extrapolate) | LightGBM on lag features + time-series and foundation models |
| R² called "accuracy", 6–7 test points | MAE / RMSE / MAPE on 96 forecasts, plus interval coverage |
| Partial 2023 treated as a full year | Monthly data; incomplete periods are never summed as a year |
| No baseline | Every model must beat naive and seasonal naive |
| Upsampling before the split in LDA (leakage) | Classification dropped; the question is a forecast |

## Tests

`pytest` runs 74 tests (+1 slow test with the real TimesFM model):

- `test_load.py` — parsing a generated workbook with the real layout.
- `test_validate_and_series.py` — quality gate and series selection.
- `test_metrics.py` — metrics on hand-checked numbers.
- `test_models.py` — every classical model's output and intervals; bad input rejected.
- `test_models_ml_foundation.py` — LightGBM features use only the past, reproducibility;
  TimesFM quantile mapping with a fake model.
- `test_backtest.py` — fold layout and the **no-leakage check**.
- `test_pipeline_cli.py` — model selection and a full `run` on a fake workbook.
- `test_gcp.py` — BigQuery SQL, identifier validation, upload/forecast flow, Gemini prompt and
  client, all with fake clients.
- `test_real_data.py` — the real workbook's shape and published totals.
