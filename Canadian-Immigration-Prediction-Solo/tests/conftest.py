"""Shared fixtures: a small fake workbook laid out exactly like the IRCC sheet,
and synthetic monthly series with a known trend and seasonality."""

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook

MONTH_NAMES = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _fmt(value):
    return "--" if value is None else f"{value:,}"


def write_ircc_workbook(path, months_per_year: dict[int, int], countries: dict[str, list]):
    """Write a workbook with the IRCC layout.

    months_per_year: {2023: 12, 2024: 2} -> all of 2023, Jan-Feb 2024
    countries: {name: [monthly values in order]}; None means suppressed ("--")
    """
    ws = Workbook().active
    ws.title = "PR - CITZ"
    ws.append(["Canada - Admissions of Permanent Residents by Country of Citizenship (test)"])
    ws.append([])

    year_row, quarter_row, month_row = ["Country of Citizenship"], [None], [None]
    layout = []  # ("month", i) or ("total", [month positions])
    pos = 0
    for year, n_months in months_per_year.items():
        year_cols = []
        for q in range(4):
            q_months = [m for m in range(q * 3, q * 3 + 3) if m < n_months]
            if not q_months:
                break
            for k, m in enumerate(q_months):
                year_row.append(str(year) if (q == 0 and k == 0) else None)
                quarter_row.append(f"Q{q + 1}" if k == 0 else None)
                month_row.append(MONTH_NAMES[m])
                layout.append(("month", pos))
                year_cols.append(pos)
                pos += 1
            year_row.append(None)
            quarter_row.append(None)
            month_row.append(f"Q{q + 1} Total")
            layout.append(("total", list(range(pos - len(q_months), pos))))
        year_row.append(None)
        quarter_row.append(f"{year} Total")
        month_row.append(None)
        layout.append(("total", year_cols))
    ws.append(year_row)
    ws.append(quarter_row)
    ws.append(month_row)

    def row_cells(values):
        cells = []
        for kind, ref in layout:
            if kind == "month":
                cells.append(_fmt(values[ref]))
            else:
                cells.append(_fmt(sum(v for i in ref if (v := values[i]) is not None)))
        return cells

    for name, values in countries.items():
        ws.append([name] + row_cells(values))
    totals = [sum(v for v in col if v is not None) for col in zip(*countries.values())]
    ws.append(["Total"] + row_cells(totals))
    ws.append([])
    ws.append(["Notes: values between 0 and 5 are shown as --"])
    ws.append([])
    ws.append(["Source: test"])
    ws.parent.save(path)
    return path


@pytest.fixture
def small_workbook(tmp_path):
    """14 months: all of 2023 and Jan-Feb 2024 (a partial final year, like the real file)."""
    countries = {
        "India": [1000 + 5 * i for i in range(14)],
        "Tuvalu": [None, 5, None, 10, None, None, 5, None, None, None, 5, None, None, 5],
        "Country not stated": [10] * 14,
    }
    return write_ircc_workbook(tmp_path / "test.xlsx", {2023: 12, 2024: 2}, countries)


@pytest.fixture
def seasonal_series():
    """8 years of monthly data: upward trend + yearly seasonality + small noise."""
    idx = pd.date_range("2015-01-01", periods=96, freq="MS")
    t = np.arange(96)
    rng = np.random.default_rng(0)
    values = 20000 + 100 * t + 3000 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 300, 96)
    return pd.Series(values, index=idx, name="synthetic")
