import math

import pandas as pd
import pytest

from immigration_forecast.load import load_workbook, parse_count

from conftest import write_ircc_workbook


@pytest.mark.parametrize("text, expected", [("90", 90.0), ("2,630", 2630.0), ("1,234,565", 1234565.0), (" 15 ", 15.0)])
def test_parse_count_numbers(text, expected):
    assert parse_count(text) == expected


def test_parse_count_suppressed_is_nan():
    assert math.isnan(parse_count("--"))


@pytest.mark.parametrize("bad", ["n/a", "12,34", "-5", "", None, float("nan")])
def test_parse_count_rejects_unexpected_values(bad):
    with pytest.raises(ValueError):
        parse_count(bad)


def test_only_month_columns_are_kept(small_workbook):
    data = load_workbook(small_workbook)
    dates = sorted(data.countries["date"].unique())
    assert len(dates) == 14  # 12 + 2 months; quarter and year totals are dropped
    assert pd.Timestamp(dates[0]) == pd.Timestamp("2023-01-01")
    assert pd.Timestamp(dates[-1]) == pd.Timestamp("2024-02-01")


def test_one_row_per_country_and_month(small_workbook):
    data = load_workbook(small_workbook)
    assert len(data.countries) == 3 * 14
    assert set(data.countries["country"]) == {"India", "Tuvalu", "Country not stated"}
    assert "Total" not in set(data.countries["country"])


def test_values_and_suppression_flags(small_workbook):
    df = load_workbook(small_workbook).countries
    india = df[df["country"] == "India"].set_index("date")["admissions"]
    assert india.iloc[0] == 1000 and india.iloc[-1] == 1065
    tuvalu = df[df["country"] == "Tuvalu"]
    assert tuvalu["suppressed"].sum() == 9
    assert tuvalu.loc[tuvalu["suppressed"], "admissions"].isna().all()
    assert not tuvalu.loc[~tuvalu["suppressed"], "admissions"].isna().any()


def test_published_total_is_separate(small_workbook):
    total = load_workbook(small_workbook).published_total
    assert len(total) == 14
    assert total.iloc[0] == 1000 + 0 + 10  # Tuvalu's suppressed month counts as 0 in the fake total


def test_header_found_even_if_rows_shift(tmp_path):
    path = write_ircc_workbook(tmp_path / "w.xlsx", {2023: 12}, {"India": list(range(5, 65, 5))})
    from openpyxl import load_workbook as open_xlsx

    wb = open_xlsx(path)
    wb.active.insert_rows(1, amount=2)  # extra title lines above the header
    wb.save(path)
    assert len(load_workbook(path).countries) == 12


def test_unexpected_text_in_data_fails_loudly(tmp_path):
    path = write_ircc_workbook(tmp_path / "w.xlsx", {2023: 12}, {"India": list(range(5, 65, 5))})
    from openpyxl import load_workbook as open_xlsx

    wb = open_xlsx(path)
    wb.active.cell(row=6, column=2, value="unknown")
    wb.save(path)
    with pytest.raises(ValueError, match="Unexpected cell value"):
        load_workbook(path)
