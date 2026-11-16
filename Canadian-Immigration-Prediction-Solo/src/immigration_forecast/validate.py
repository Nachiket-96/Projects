"""Data-quality checks run before any modelling.

Hard problems (duplicates, gaps, negative counts) raise DataValidationError.
Soft problems (rounding drift beyond what IRCC's rules allow) are returned as warnings.
"""

from dataclasses import dataclass, field

import pandas as pd

from .load import AdmissionsData

ROUNDING_BASE = 5  # IRCC rounds every value to a multiple of 5
MAX_ROUNDING_ERROR = 2.5  # rounding to the nearest 5 moves a value by at most 2.5
MAX_SUPPRESSED_VALUE = 5  # "--" hides a value between 0 and 5


class DataValidationError(ValueError):
    pass


@dataclass
class ValidationReport:
    n_countries: int
    first_month: pd.Timestamp
    last_month: pd.Timestamp
    n_months: int
    suppressed_share: float
    max_total_gap: float  # largest |sum of countries - published total| in any month
    warnings: list[str] = field(default_factory=list)


def validate(data: AdmissionsData) -> ValidationReport:
    df = data.countries
    if df.empty:
        raise DataValidationError("No country rows were loaded.")

    dupes = df.duplicated(["country", "date"])
    if dupes.any():
        raise DataValidationError(f"{int(dupes.sum())} duplicate (country, month) rows.")

    if (df["admissions"] < 0).any() or (data.published_total < 0).any():
        raise DataValidationError("Negative admission counts found.")

    if data.published_total.isna().any():
        raise DataValidationError("The published national total has suppressed or missing months.")

    months = pd.DatetimeIndex(sorted(df["date"].unique()))
    expected = pd.date_range(months[0], months[-1], freq="MS")
    if len(months) != len(expected):
        missing = expected.difference(months)
        raise DataValidationError(f"Missing months: {[d.strftime('%Y-%m') for d in missing]}")

    per_country = df.groupby("country")["date"].count()
    if (per_country != len(months)).any():
        raise DataValidationError("Some countries do not have a value for every month.")

    warnings = []
    reported = df["admissions"].dropna()
    off_grid = reported[reported % ROUNDING_BASE != 0]
    if len(off_grid):
        warnings.append(f"{len(off_grid)} values are not multiples of {ROUNDING_BASE}.")

    # Each month: the sum of rounded country values may differ from the published total, but
    # never by more than the worst case allowed by rounding and suppression.
    monthly = df.groupby("date").agg(
        summed=("admissions", "sum"),
        n_reported=("admissions", "count"),
        n_suppressed=("suppressed", "sum"),
    )
    gap = (monthly["summed"] - data.published_total.reindex(monthly.index)).abs()
    allowed = (monthly["n_reported"] + 1) * MAX_ROUNDING_ERROR + monthly["n_suppressed"] * MAX_SUPPRESSED_VALUE
    too_far = gap[gap > allowed]
    if len(too_far):
        warnings.append(
            "Country sums differ from the published total by more than rounding allows in "
            f"{len(too_far)} month(s): {[d.strftime('%Y-%m') for d in too_far.index]}"
        )

    return ValidationReport(
        n_countries=int(df["country"].nunique()),
        first_month=months[0],
        last_month=months[-1],
        n_months=len(months),
        suppressed_share=float(df["suppressed"].mean()),
        max_total_gap=float(gap.max()),
        warnings=warnings,
    )
