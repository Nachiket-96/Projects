# Model Guide — explained without jargon

This guide explains what the project does, how each model works, how we know which one to
trust, and what the results mean. No maths or coding background is needed.

---

## 1. The question

> *How many people will Canada admit as permanent residents each month over the next year or so?*

Governments, settlement agencies, schools and housing planners all need a rough answer. We
answer it for Canada as a whole and for the five countries that send the most people.

## 2. The data

The data comes from **IRCC** (Immigration, Refugees and Citizenship Canada), published on the
Government of Canada's open data portal. It counts new permanent residents **per month, per
country of citizenship**, from January 2015 to August 2026.

Three quirks matter:

| Quirk | What it means for us |
|---|---|
| Every number is **rounded to the nearest 5** | Small differences (±5) are noise, not information. |
| Numbers from 0 to 5 are shown as **"--"** | Hidden to protect privacy. We never treat "--" as zero, and we don't forecast countries that have them. |
| The newest months are **preliminary** | IRCC may revise them later, so results can shift slightly with a newer file. |

The history also contains two shocks: **COVID-19** (spring 2020 to spring 2021, when admissions
collapsed) and a **catch-up surge** in late 2021. More recently, the government **lowered its
targets** for 2025–2026.

## 3. What a forecast is

A forecast is an **educated guess plus a range**. We always give both:

- **Point forecast** — the single most likely number, e.g. "about 38,000 in March".
- **80% range** — "we expect the real number to land between 25,000 and 60,000 about 8 times out of 10".

A wide range is not a failure. It is honest about how uncertain the future is.

## 4. The six models

Think of each model as a different person trying to predict next month's number.

### 4.1 Naive — *"Same as last month"*
Next month will look like this month. It sounds too simple, but it is surprisingly hard to beat
over short periods. **Its job is to be the bar every other model must clear.**

### 4.2 Seasonal naive — *"Same as this month last year"*
March next year will look like March this year. Good when the calendar matters a lot
(holidays, fiscal years, school terms). Also a bar to clear.

### 4.3 ETS (Exponential Smoothing) — *"Recent months matter most"*
Keeps a running estimate of three things: the current **level**, the **trend** (going up or
down) and the **seasonal pattern** (which months are usually busy). Each new month updates
those estimates, with recent months counting more than old ones. The trend is **damped** — it
is assumed to flatten out over time instead of growing forever, which is realistic for
government-capped numbers.

### 4.4 SARIMA (Seasonal ARIMA) — *"Learn from your own past mistakes"*
Looks at how each month's number relates to the previous months and to the same month a year
earlier, and also at how wrong its own recent guesses were. We add a **COVID flag** so the 2020
collapse is understood as a one-off event, not a normal pattern.

### 4.5 LightGBM (Machine learning) — *"Hundreds of small yes/no rules"*
Builds many small decision trees, each a set of questions like *"Was last month above 35,000?
Is it December?"*. Every tree corrects the mistakes of the ones before it (this is called
**gradient boosting**).

The model is described by **lag features** — what happened 1, 2, 3, 6 and 12 months ago, recent
averages, the calendar month, and the COVID flag — not by the year number. This matters: tree
models cannot extend a line into the future, which is why the old capstone's Random Forest,
which only knew the year, predicted the same number for every future year.

To forecast 12 months ahead it predicts one month, treats that guess as the newest "last
month", and repeats.

### 4.6 TimesFM (Foundation model by Google) — *"Has seen millions of charts before"*
A large AI model (200 million parameters) that Google trained on a huge collection of real
and synthetic time series — retail sales, web traffic, weather, energy and more. Like a
language model has read a lot of text, TimesFM has "read" a lot of charts.

We use it **zero-shot**: we do **not** train it on immigration data. We just show it our
history and ask what comes next. It is the same technology behind BigQuery's `AI.FORECAST`
function on Google Cloud.

## 5. How we decide which model to trust: backtesting

You can't judge a forecaster by how well it explains the past. You have to check how well it
**predicted things it had not seen yet**.

So we **replay history**. We pretend it is the end of November 2023, give each model only the
data up to then, ask it to forecast the next 12 months, and compare with what actually
happened. Then we move forward 3 months and repeat — 8 times in total, the last replay
forecasting September 2025 to August 2026.

```
replay 1:  [ data the model may see ][ next 12 months: scored ]
replay 2:  [ data the model may see ...... ][ next 12 months: scored ]
replay 3:  [ data the model may see ............ ][ next 12 months: scored ]
```

That gives 96 real "exam answers" per model per series. An automated test checks that no
model ever sees a month it is being scored on.

**Why not just shuffle the years randomly into training and testing?** That is what the old
capstone did. If 2019 and 2021 are in training and 2020 is in the test, the model is filling a
gap, not predicting the future. It looks great on paper and fails in real use. This mistake is
called **data leakage**.

## 6. How we measure error

| Measure | Plain meaning | Example |
|---|---|---|
| **MAE** (mean absolute error) | On average, how many people the forecast was off by per month | MAE 5,348 = off by about 5,300 people a month |
| **MAPE** (mean absolute percentage error) | The same, as a percentage | MAPE 16.7% = off by about 17% on average |
| **"Accuracy"** (informal) | 100% − MAPE | about 83% |
| **Interval coverage** | How often the real number fell inside the 80% range | 92.7% = the range was, if anything, a bit too cautious |
| **Beats naive by** | How much smaller the error is than "same as last month" | 15% = a real but modest improvement |

## 7. What we found

| Series | Best model | Typical miss | Better than "same as last month" by |
|---|---|---|---|
| Canada (total) | TimesFM | ~17% | 15% |
| India | LightGBM | ~25% | 19% |
| Philippines | SARIMA | ~21% | 16% |
| Cameroon | LightGBM | ~22% | 23% |
| China | ETS | ~26% | 8% |
| Nigeria | TimesFM | ~20% | 7% |

Key takeaways:

1. **No model wins everywhere.** That is why we test each series separately instead of picking
   a favourite.
2. **Google's TimesFM did best nationally without any training on this data** — strong
   evidence that foundation models are useful even for small, messy datasets.
3. **The improvements are real but modest.** Immigration numbers are set mainly by government
   targets and processing capacity. A model that only looks at past numbers can't know about
   a policy decision announced next month.

The national forecast is about **150,000** admissions for September–December 2026 and about
**435,000** for 2027, with a wide range.

## 8. Cautions

- The models **do not know the Immigration Levels Plan**. If the government changes its
  targets, trust the targets over the model.
- The 2027 range is wide on purpose. Planning should consider both ends, not just the middle.
- Rounded and hidden ("--") values make small countries unreliable to forecast.

## 9. The Google Cloud version

A company on Google Cloud would run this inside its data warehouse:

| Step | Google Cloud tool | What it does |
|---|---|---|
| Store the data | **BigQuery** table | The monthly numbers for every series |
| Classical forecast | **BigQuery ML `ARIMA_PLUS`** | Trains an automatic ARIMA model per series, written in SQL |
| Foundation-model forecast | **BigQuery `AI.FORECAST`** | Runs TimesFM inside BigQuery, no training, one SQL query |
| Explain the results | **Gemini** | Writes a short plain-English briefing from the result tables |

**Gemini does not do the forecasting.** It is a language model: excellent at explaining, not at
precise numeric prediction. We give it the exact numbers and tell it not to invent any. TimesFM
does the numbers; Gemini does the words.

## 10. Questions you may be asked

**Why not use the year as the input, like the old project?**
A year number only lets a model draw a straight line. Immigration has seasons, shocks and
policy changes. Lag features or time-series models capture those.

**Why not deep learning like LSTM?**
With 140 months per series, a deep network would memorise the noise. Foundation models like
TimesFM avoid this because they learned from millions of other series first.

**What is the accuracy?**
About 83% for the national monthly forecast (MAPE 16.7%), measured honestly by replaying
history, 12 months ahead.

**Why is the old capstone's R² of 0.88 higher?**
Its test years were mixed into the training period (leakage), and its final models used
simulated data. The new number is lower because it is real.

**What would improve it most?**
Feeding in the government's published targets as an extra input, for example with BigQuery ML
`ARIMA_PLUS_XREG` or TimesFM covariates.
