import dataclasses

import pandas as pd
import pytest

from immigration_forecast.load import load_workbook
from immigration_forecast.series import country_series, national_series, top_countries
from immigration_forecast.validate import DataValidationError, validate


def _with_countries(data, df):
    return dataclasses.replace(data, countries=df)


def test_clean_workbook_passes(small_workbook):
    report = validate(load_workbook(small_workbook))
    assert report.n_countries == 3
    assert report.n_months == 14
    assert report.first_month == pd.Timestamp("2023-01-01")
    assert report.last_month == pd.Timestamp("2024-02-01")
    assert report.suppressed_share == pytest.approx(9 / 42)
    assert report.warnings == []


def test_duplicates_are_rejected(small_workbook):
    data = load_workbook(small_workbook)
    df = pd.concat([data.countries, data.countries.head(1)])
    with pytest.raises(DataValidationError, match="duplicate"):
        validate(_with_countries(data, df))


def test_missing_month_is_rejected(small_workbook):
    data = load_workbook(small_workbook)
    df = data.countries[data.countries["date"] != "2023-06-01"]
    with pytest.raises(DataValidationError, match="Missing months"):
        validate(_with_countries(data, df))


def test_negative_counts_are_rejected(small_workbook):
    data = load_workbook(small_workbook)
    df = data.countries.copy()
    df.loc[0, "admissions"] = -5
    with pytest.raises(DataValidationError, match="Negative"):
        validate(_with_countries(data, df))


def test_total_far_from_country_sum_is_flagged(small_workbook):
    data = load_workbook(small_workbook)
    total = data.published_total.copy()
    total.iloc[3] += 10_000
    report = validate(dataclasses.replace(data, published_total=total))
    assert any("2023-04" in w for w in report.warnings)


def test_off_grid_values_are_flagged(small_workbook):
    data = load_workbook(small_workbook)
    df = data.countries.copy()
    df.loc[0, "admissions"] = 1001
    assert any("multiples of 5" in w for w in validate(_with_countries(data, df)).warnings)


def test_national_series_is_monthly(small_workbook):
    y = national_series(load_workbook(small_workbook))
    assert y.index.freqstr == "MS"
    assert len(y) == 14 and not y.isna().any()


def test_country_series(small_workbook):
    y = country_series(load_workbook(small_workbook), "India")
    assert y.name == "India" and y.index.freqstr == "MS" and y.iloc[0] == 1000


def test_country_with_suppressed_months_is_not_modelled(small_workbook):
    with pytest.raises(ValueError, match="suppressed"):
        country_series(load_workbook(small_workbook), "Tuvalu")


def test_unknown_country(small_workbook):
    with pytest.raises(KeyError):
        country_series(load_workbook(small_workbook), "Atlantis")


def test_top_countries_excludes_not_stated(small_workbook):
    assert top_countries(load_workbook(small_workbook), n=2) == ["India", "Tuvalu"]
