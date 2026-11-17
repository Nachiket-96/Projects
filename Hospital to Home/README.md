# Hospital to Home

Predictive monitoring system for patients moving from hospital to home care. It predicts each patient's 30-day readmission risk, flags the factors behind it, and keeps the care team (family physician, community nurse, pharmacist) on one shared care plan with live notifications.

> Demo project. The model is trained on synthetic data and is **not** for clinical use.

## Features

- **Readmission risk score** (0–100, LOW / MEDIUM / HIGH) from a Gradient Boosting model with 10 features: age, heart rate, SpO₂, systolic BP, creatinine, comorbidities, medication count, high-risk medications, length of stay, and previous admissions
- **Contributing risk factors** shown per patient (polypharmacy, abnormal vitals, recent readmissions, ...)
- **Live recalculation** when vitals, medications, or hospitalization history change
- **Shared care plan** (JSON) visible to the whole care team
- **Notifications** when a patient newly reaches HIGH risk, is discharged, or has their care plan changed

## Tech stack

Python 3.13 · Flask · Flask-SQLAlchemy (SQLite) · scikit-learn · Bootstrap 5

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

flask --app app seed            # create the database with 15 demo patients
python app.py                   # http://127.0.0.1:5000
```

Optional environment variables:

| Variable | Purpose |
|---|---|
| `H2H_SECRET_KEY` | Flask secret key (a random one is generated if unset) |
| `FLASK_DEBUG=1` | Run in debug mode |

## Retraining the model

```bash
python train_enhanced_model.py
```

This regenerates the synthetic dataset and writes `models/enhanced_model.joblib`, `models/enhanced_metadata.json` and `models/enhanced_training_data.csv`. The app warns at startup if the installed scikit-learn version differs from the one the model was trained with.

Current model (synthetic data, 27.8% readmission rate): accuracy 74.9% (baseline 72.1%), ROC-AUC 0.75. Previous admissions is the strongest predictor (23.6% importance).

## Project structure

```
app.py                     Flask app: models, risk scoring, routes, seed command
train_enhanced_model.py    Synthetic data generation and model training
models/                    Trained model, metadata, training data
templates/                 Jinja templates (dashboard, patient page)
static/                    CSS and JavaScript
Hospital_to_Home.docx      Project documentation
```

## Before real-world use

- Retrain and validate on real EMR data
- Add authentication, role-based access, and audit logging (required under Saskatchewan's Health Information Protection Act)
