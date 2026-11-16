"""Paths and constants shared by the whole project."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

DATASET_PAGE = "https://open.canada.ca/data/en/dataset/f7e5498e-0ad8-4417-85c9-9b8aff9b9eda"
SOURCE_URL = "https://www.ircc.canada.ca/opendata-donneesouvertes/data/EN_ODP-PR-Citz.xlsx"
RAW_FILE = RAW_DIR / "EN_ODP-PR-Citz.xlsx"

SEASON_LENGTH = 12  # monthly data, yearly seasonality

# Months when COVID-19 border restrictions pushed admissions far below normal.
COVID_START = "2020-03-01"
COVID_END = "2021-05-01"

# Prediction intervals are 80% (alpha = 0.2), a common choice for planning forecasts.
INTERVAL_ALPHA = 0.2

# "Country not stated" is a data-entry bucket, not a country, so it is never ranked or modelled.
NOT_STATED = "Country not stated"
