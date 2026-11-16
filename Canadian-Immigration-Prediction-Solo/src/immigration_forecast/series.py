"""Pick the monthly series that get modelled."""

import pandas as pd

from .config import NOT_STATED
from .load import AdmissionsData


def _as_monthly(series: pd.Series, name: str) -> pd.Series:
    series = series.sort_index().asfreq("MS")
    series.name = name
    return series


def national_series(data: AdmissionsData) -> pd.Series:
    """IRCC's published national total. Used instead of summing countries,
    because each country value is rounded separately."""
    return _as_monthly(data.published_total.copy(), "Canada (total)")


def country_series(data: AdmissionsData, country: str) -> pd.Series:
    df = data.countries[data.countries["country"] == country]
    if df.empty:
        raise KeyError(f"Unknown country: {country!r}")
    if df["suppressed"].any():
        raise ValueError(
            f"{country!r} has {int(df['suppressed'].sum())} suppressed months; "
            "its exact values are unknown, so it is not modelled."
        )
    return _as_monthly(df.set_index("date")["admissions"], country)


def top_countries(data: AdmissionsData, n: int, recent_months: int = 12) -> list[str]:
    """The n largest source countries over the most recent `recent_months` months."""
    df = data.countries[data.countries["country"] != NOT_STATED]
    cutoff = df["date"].max() - pd.DateOffset(months=recent_months - 1)
    recent = df[df["date"] >= cutoff]
    totals = recent.groupby("country")["admissions"].sum()  # NaN (suppressed) counts as 0
    return totals.sort_values(ascending=False).head(n).index.tolist()
