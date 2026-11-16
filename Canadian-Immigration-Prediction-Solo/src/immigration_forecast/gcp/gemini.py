"""Turn the forecast numbers into a plain-language briefing with Gemini.

Gemini does not forecast here. The numbers come from the backtested models; Gemini
only explains them for a non-technical reader. The prompt passes the exact figures
and tells the model not to invent any.

Credentials come from the environment, never from code:
  - Gemini API:  GEMINI_API_KEY
  - Vertex AI:   GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION
"""

import os

import pandas as pd

DEFAULT_MODEL = "gemini-2.5-flash"


def build_prompt(metrics: pd.DataFrame, forecasts: pd.DataFrame, last_month: str) -> str:
    best = metrics.sort_values("mae").groupby("series").head(1)
    naive = metrics[metrics["model"] == "naive"].set_index("series")["mae"]
    best = best.assign(naive_mae=best["series"].map(naive))

    f = forecasts.copy()
    f["year"] = pd.to_datetime(f["date"]).dt.year
    yearly = f.groupby(["series", "year"])[["mean", "lower", "upper"]].sum().round(-2).reset_index()

    return f"""You are writing a short briefing for a non-technical manager about forecasts of
monthly permanent resident admissions to Canada, made from official IRCC open data
(last month of actual data: {last_month}).

FACTS - use only these numbers, do not invent or recalculate others:

Backtest error of the chosen model per series (MAE = average miss in admissions per month,
MAPE = average miss in percent, naive_mae = error of simply repeating last month):
{best[["series", "model", "mae", "mape_pct", "naive_mae"]].round(1).to_csv(index=False)}
Forecast totals per year (mean = expected total; lower/upper = sums of the monthly 80% bounds,
a rough outer range that is wider than a true yearly range; partial years cover only the forecast months):
{yearly.to_csv(index=False)}
WRITE:
- 4 short sections with headings: Summary, What we expect, How reliable this is, Cautions.
- Plain English, no jargon; explain MAPE and the range in everyday words.
- Say clearly that the models only learn from past numbers and do not know the government's
  Immigration Levels Plan targets, which drive admissions most.
- Under 300 words.
"""


def summarize_with_gemini(prompt: str, model: str | None = None, client=None) -> str:
    if client is None:
        from google import genai

        client = genai.Client()  # reads credentials from the environment
    model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    response = client.models.generate_content(model=model, contents=prompt)
    if not getattr(response, "text", None):
        raise RuntimeError("Gemini returned an empty response.")
    return response.text
