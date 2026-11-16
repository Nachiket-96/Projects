import pytest

from immigration_forecast.metrics import coverage, mae, mape, rmse


def test_mae():
    assert mae([100, 200], [110, 180]) == 15


def test_rmse_punishes_big_errors_more_than_mae():
    actual, forecast = [100, 100], [100, 140]
    assert mae(actual, forecast) == 20
    assert rmse(actual, forecast) == pytest.approx(28.2843, rel=1e-4)


def test_mape_skips_zero_actuals():
    assert mape([0, 100, 200], [5, 110, 180]) == pytest.approx(10.0)


def test_mape_all_zero_is_an_error():
    with pytest.raises(ValueError):
        mape([0, 0], [1, 1])


def test_coverage():
    assert coverage([10, 20, 30, 40], [0, 0, 0, 50], [15, 25, 25, 60]) == 50.0


@pytest.mark.parametrize("fn", [mae, rmse, mape])
def test_length_mismatch(fn):
    with pytest.raises(ValueError):
        fn([1, 2], [1])
