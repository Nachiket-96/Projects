"""Turn the wide IRCC report sheet into tidy monthly data.

The sheet is a report, not a table:
  - three header rows: year / quarter / month-or-total
  - quarter totals and year totals mixed in between the month columns
  - one row per country, then a "Total" row, then footnotes
  - counts stored as text ("2,630"), and values 0-5 shown as "--"

`load_workbook` keeps only the month columns and returns one row per
(country, month), plus IRCC's published national total.
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HEADER_LABEL = "Country of Citizenship"
TOTAL_LABEL = "Total"
SUPPRESSED = "--"
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}

_COUNT = re.compile(r"\d{1,3}(,\d{3})+|\d+(\.0+)?")


@dataclass(frozen=True)
class AdmissionsData:
    countries: pd.DataFrame  # columns: country, date, admissions, suppressed
    published_total: pd.Series  # index: month start date, IRCC's own national total


def parse_count(value) -> float:
    """Convert one cell to a number. "--" (suppressed, 0-5) becomes NaN."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("Blank cell where a count was expected.")
    text = str(value).strip()
    if text == SUPPRESSED:
        return math.nan
    if not _COUNT.fullmatch(text):
        raise ValueError(f"Unexpected cell value: {text!r}")
    return float(text.replace(",", ""))


def find_header_row(raw: pd.DataFrame) -> int:
    """Row index of the year header, found by its label instead of a hard-coded position."""
    rows = raw.index[raw[0].astype(str).str.strip() == HEADER_LABEL]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one {HEADER_LABEL!r} header row, found {len(rows)}.")
    return int(rows[0])


def month_columns(raw: pd.DataFrame, header_row: int) -> list[tuple[int, pd.Timestamp]]:
    """(column index, month start date) for every month column, skipping all total columns."""
    years = raw.iloc[header_row].ffill()  # a year label sits only above the first column of its block
    labels = raw.iloc[header_row + 2]
    columns = []
    for col in range(1, raw.shape[1]):
        label = labels[col]
        if isinstance(label, str) and label.strip() in MONTHS:
            year = str(years[col]).strip()
            if not re.fullmatch(r"\d{4}", year):
                raise ValueError(f"Column {col} has month {label!r} but no valid year (got {year!r}).")
            columns.append((col, pd.Timestamp(int(year), MONTHS[label.strip()], 1)))
    if not columns:
        raise ValueError("No month columns found.")
    return sorted(columns, key=lambda c: c[1])


def load_workbook(path: Path) -> AdmissionsData:
    raw = pd.read_excel(path, sheet_name=0, header=None, dtype=str)
    header_row = find_header_row(raw)
    columns = month_columns(raw, header_row)
    dates = [date for _, date in columns]

    total_rows = raw.index[(raw[0].astype(str).str.strip() == TOTAL_LABEL) & (raw.index > header_row)]
    if len(total_rows) != 1:
        raise ValueError(f"Expected exactly one {TOTAL_LABEL!r} row, found {len(total_rows)}.")
    total_row = int(total_rows[0])

    body = raw.iloc[header_row + 3 : total_row]
    body = body[body[0].notna()]

    records = []
    for _, row in body.iterrows():
        country = str(row[0]).strip()
        for col, date in columns:
            value = parse_count(row[col])
            records.append((country, date, value, math.isnan(value)))
    countries = pd.DataFrame(records, columns=["country", "date", "admissions", "suppressed"])

    published_total = pd.Series(
        [parse_count(raw.iat[total_row, col]) for col, _ in columns],
        index=pd.DatetimeIndex(dates, name="date"),
        name="admissions",
    )
    return AdmissionsData(countries=countries, published_total=published_total)
