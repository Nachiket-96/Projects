"""Forecast chart: recent history, the forecast, and its prediction interval."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # write files only; no window needed
import matplotlib.pyplot as plt
import pandas as pd


def plot_forecast(y: pd.Series, forecast: pd.DataFrame, title: str, path: Path, history_years: int = 6) -> Path:
    history = y.loc[y.index[-1] - pd.DateOffset(years=history_years) :]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(history.index, history.values, color="#1f4e79", label="Actual")
    ax.plot(forecast.index, forecast["mean"], color="#c0504d", label="Forecast")
    ax.fill_between(forecast.index, forecast["lower"], forecast["upper"], color="#c0504d", alpha=0.2, label="80% interval")
    ax.set_title(title)
    ax.set_ylabel("Admissions per month")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
