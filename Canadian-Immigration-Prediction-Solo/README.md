# Canadian Immigration Prediction — Solo Rebuild

Forecasts **monthly permanent resident (PR) admissions to Canada**, nationally and for the
largest source countries, from official IRCC open data. Every model is scored with
**rolling-origin backtesting** against simple baselines before it is trusted.

This is a solo rebuild of an earlier group capstone (`../Canadian immigration prediction/`,
left unchanged). See [What changed from the capstone](#what-changed-from-the-capstone).

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

## Project layout

```
Canadian-Immigration-Prediction-Solo/
├── pyproject.toml            package metadata, dependencies, pytest settings
├── requirements.txt          exact versions it was tested with
├── data/
│   ├── raw/                  downloaded workbook (git-ignored)
│   └── processed/            tidy country-month CSV (git-ignored)
├── reports/
│   ├── backtest_metrics.csv  error of every model on every series
│   ├── forecasts.csv         chosen model's forecast with 80% interval
│   └── figures/              one chart per series
├── src/immigration_forecast/
│   ├── config.py             paths and constants (COVID window, interval level)
│   ├── download.py           fetch the workbook, verify it is a real .xlsx
│   ├── load.py               wide report sheet -> tidy (country, month, admissions, suppressed)
│   ├── validate.py           data-quality gate: duplicates, gaps, negatives, rounding drift
│   ├── series.py             national series, per-country series, top-N countries
│   ├── models.py             naive, seasonal naive, ETS, SARIMA behind one fit/predict interface
│   ├── metrics.py            MAE, RMSE, MAPE, interval coverage
│   ├── backtest.py           rolling-origin folds, no future data in training
│   ├── pipeline.py           backtest -> pick lowest MAE -> refit on all data -> forecast
│   ├── plotting.py           forecast chart
│   └── cli.py                `download` and `run` commands
└── tests/                    58 pytest tests (unit, integration, real-data)
```

Data flows one way: **download → load → validate → series → backtest → forecast → reports**.
Each step is a small module that can be tested on its own.

## How to run

```bash
cd Canadian-Immigration-Prediction-Solo
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

python -m immigration_forecast download     # saves data/raw/EN_ODP-PR-Citz.xlsx
python -m immigration_forecast run          # validate, backtest, forecast, write reports/
pytest                                      # run the test suite
```

Options for `run`: `--top 5` (number of source countries), `--forecast-end 2027-12`,
`--horizon 12` (months scored per backtest fold), `--folds 8`, `--step 3`.

Without installing, `PYTHONPATH=src python -m immigration_forecast run` also works.

## Method

**Models** (`models.py`), all fitted per series:

| Model | Idea |
|---|---|
| `naive` | next months = last month |
| `seasonal_naive` | next months = same month last year |
| `ets` | exponential smoothing, damped additive trend + yearly seasonality, on log(admissions) |
| `sarima` | seasonal ARIMA (1,1,1)(0,1,1)12 on log(admissions), with a COVID dummy (Mar 2020 – May 2021) |

Log transform keeps forecasts positive and makes seasonal swings proportional to the level.

**Evaluation** (`backtest.py`): 8 folds, origins 3 months apart; each fold trains only on
data up to its origin and forecasts the next 12 months. The latest fold tests Sep 2025 –
Aug 2026. 96 forecasts per model per series. The model with the lowest MAE is refitted on
all data and forecasts Sep 2026 – Dec 2027.

## Results (data release of August 31, 2026)

Backtest error, 12-month-ahead forecasts (`reports/backtest_metrics.csv`):

| Series | Best model | MAE (per month) | MAPE | Naive MAE | Improvement vs naive |
|---|---|---|---|---|---|
| Canada (total) | ets | 5,759 | 17.0% | 6,326 | 9% |
| India | ets | 2,151 | 26.4% | 2,546 | 16% |
| Philippines | sarima | 472 | 20.5% | 565 | 16% |
| Cameroon | ets | 412 | 22.9% | 504 | 18% |
| China | ets | 480 | 25.6% | 523 | 8% |
| Nigeria | naive | 318 | 20.6% | 318 | — |

National forecast (`reports/figures/forecast_canada_total.png`): about **145,000** admissions
for Sep–Dec 2026 and about **464,000** for 2027, with a wide 80% interval
(roughly 260,000 – 836,000 for 2027).

**How to read this honestly**

- The best models beat the naive baseline by only **8–18%**, and for Nigeria nothing beats it.
  Monthly admissions are driven mostly by government targets and processing capacity,
  which a model of past values alone cannot see.
- The 80% intervals contained **more than 80%** of actuals in backtests (up to 100% for ETS),
  so they are conservative — wide rather than over-confident.
- The model does not know the federal **Immigration Levels Plan**. Compare forecasts with the
  published targets before using them; a target change moves the real numbers far more
  than any seasonal pattern.

## Limitations

- **Policy-driven series**: targets for 2025–2026 were cut; a model trained on 2021–2024
  growth can over-forecast. Adding the Levels Plan targets as an input is the next step.
- **Short history**: 140 months, with a COVID shock and a 2021 catch-up surge inside it.
- **Rounding and suppression**: every value is rounded to 5, and 12.7% of country-months are
  hidden as `--`. Countries with any suppressed month are not modelled.
- **Preliminary data**: IRCC revises recent months; re-running on a newer file can change results.
- **Country names** are IRCC's own (e.g. "China, People's Republic of").

## What changed from the capstone

| Old capstone | This rebuild |
|---|---|
| Final "Ridge" and "Random Forest updated" results trained on **simulated random data** | Only official IRCC data |
| Random `train_test_split` on years (future leaked into training) | Rolling-origin backtest; a test checks no fold trains on future months |
| Random Forest on `year` → flat forecasts (cannot extrapolate) | Time-series models built for trend + seasonality |
| R² called "accuracy", 6–7 test points | MAE / RMSE / MAPE on 96 forecasts, plus interval coverage |
| Partial 2023 treated as a full year | Monthly data; incomplete periods are never summed as a year |
| No baseline | Every model must beat naive and seasonal naive |
| Upsampling before the split in LDA (leakage) | Classification dropped; the question is a forecast |

## Tests

`pytest` runs 58 tests:

- `test_load.py` — parsing on a generated workbook with the real layout: totals dropped,
  `--` flagged, partial final year, shifted header rows, unexpected text rejected.
- `test_validate_and_series.py` — duplicates, missing months, negatives, rounding drift,
  suppressed countries refused, top-N ranking.
- `test_metrics.py` — metric values on hand-checked numbers.
- `test_models.py` — output shape and intervals for every model; ETS and SARIMA beat naive on
  seasonal data; bad input rejected.
- `test_backtest.py` — fold layout, **no-leakage check**, summary ranking.
- `test_pipeline_cli.py` — model selection, and a full `run` end to end on a fake workbook.
- `test_real_data.py` — real workbook shape and published yearly totals (skipped if not downloaded).
