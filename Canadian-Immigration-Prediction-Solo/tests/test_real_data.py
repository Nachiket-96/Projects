"""Checks against the real IRCC workbook. Skipped when it has not been downloaded.

The expected numbers come from the August 31, 2026 release. IRCC revises
preliminary data, so a newer download may need these values updated.
"""

import pandas as pd
import pytest

from immigration_forecast.config import RAW_FILE
from immigration_forecast.load import load_workbook
from immigration_forecast.series import national_series
from immigration_forecast.validate import validate

pytestmark = pytest.mark.skipif(not RAW_FILE.exists(), reason="real workbook not downloaded")


@pytest.fixture(scope="module")
def data():
    return load_workbook(RAW_FILE)


def test_shape(data):
    report = validate(data)
    assert report.n_countries == 217  # 216 countries + "Country not stated"
    assert report.first_month == pd.Timestamp("2015-01-01")
    assert report.n_months == (report.last_month.year - 2015) * 12 + report.last_month.month
    assert report.warnings == []


def test_yearly_totals_match_published_months(data):
    yearly = national_series(data).groupby(lambda d: d.year).sum()
    assert yearly[2015] == 271_830
    assert yearly[2024] == 483_655
