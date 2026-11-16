"""Command line entry point.

    python -m immigration_forecast download
    python -m immigration_forecast run --top 5 --forecast-end 2027-12
"""

import argparse
import re
from pathlib import Path

import pandas as pd

from . import config
from .download import download_workbook
from .load import load_workbook
from .pipeline import run_series
from .plotting import plot_forecast
from .series import country_series, national_series, top_countries
from .validate import validate


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def cmd_download(args) -> None:
    path = download_workbook(dest=Path(args.output))
    print(f"Saved {path} ({path.stat().st_size:,} bytes)")


def cmd_run(args) -> None:
    data = load_workbook(Path(args.input))
    report = validate(data)
    print(
        f"Loaded {report.n_countries} countries, {report.n_months} months "
        f"({report.first_month:%Y-%m} to {report.last_month:%Y-%m}); "
        f"{report.suppressed_share:.1%} of country-months suppressed; "
        f"max monthly gap vs published total = {report.max_total_gap:,.0f}"
    )
    for warning in report.warnings:
        print(f"WARNING: {warning}")

    processed = Path(args.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    data.countries.to_csv(processed / "admissions_by_country_month.csv", index=False)

    series = [national_series(data)]
    for country in top_countries(data, args.top):
        try:
            series.append(country_series(data, country))
        except ValueError as err:
            print(f"Skipping: {err}")

    reports = Path(args.reports_dir)
    all_metrics, all_forecasts = [], []
    for y in series:
        result = run_series(y, args.forecast_end, horizon=args.horizon, n_folds=args.folds, step=args.step)
        print(f"\n{result.series}: best model = {result.best_model}")
        print(result.metrics.round(1).to_string())

        all_metrics.append(result.metrics.reset_index().assign(series=result.series))
        all_forecasts.append(result.forecast.reset_index().assign(series=result.series, model=result.best_model))
        plot_forecast(
            y,
            result.forecast,
            f"{result.series}: monthly PR admissions, forecast with {result.best_model}",
            reports / "figures" / f"forecast_{_slug(result.series)}.png",
        )

    reports.mkdir(parents=True, exist_ok=True)
    metrics = pd.concat(all_metrics)[["series", "model", "mae", "rmse", "mape_pct", "interval_coverage_pct", "n_forecasts"]]
    metrics.round(2).to_csv(reports / "backtest_metrics.csv", index=False)
    forecasts = pd.concat(all_forecasts)[["series", "model", "date", "mean", "lower", "upper"]]
    forecasts.round(0).to_csv(reports / "forecasts.csv", index=False)
    print(f"\nWrote {reports / 'backtest_metrics.csv'}, {reports / 'forecasts.csv'} and figures.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="immigration_forecast", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download", help="download the IRCC workbook")
    p.add_argument("--output", default=str(config.RAW_FILE))
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("run", help="validate, backtest, forecast and write reports")
    p.add_argument("--input", default=str(config.RAW_FILE))
    p.add_argument("--processed-dir", default=str(config.PROCESSED_DIR))
    p.add_argument("--reports-dir", default=str(config.REPORTS_DIR))
    p.add_argument("--top", type=int, default=5, help="also model the N largest source countries")
    p.add_argument("--forecast-end", default="2027-12", help="last month to forecast (YYYY-MM)")
    p.add_argument("--horizon", type=int, default=12, help="months ahead scored in each backtest fold")
    p.add_argument("--folds", type=int, default=8)
    p.add_argument("--step", type=int, default=3, help="months between backtest origins")
    p.set_defaults(func=cmd_run)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)
