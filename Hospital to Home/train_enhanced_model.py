"""
Enhanced ML Model Training Script
Creates readmission risk model with 10 features
"""
import os, time, json
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, accuracy_score, precision_score, recall_score
from joblib import dump

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

print("="*60)
print("Hospital-to-Home Enhanced ML Model Training")
print("="*60)

rng = np.random.RandomState(42)

# Generate synthetic dataset
print("\n[1/5] Generating synthetic dataset...")
N = 3000

age = rng.randint(40, 95, size=N)
hr = rng.normal(85, 15, size=N).clip(40, 160)
spo2 = rng.normal(95, 3, size=N).clip(80, 100)
sbp = rng.normal(120, 20, size=N).clip(70, 190)
creatinine = rng.normal(110, 40, size=N).clip(50, 350)
comorb = rng.randint(0, 5, size=N)

# NEW FEATURES
medication_count = rng.randint(0, 15, size=N)
high_risk_meds = rng.binomial(1, 0.3, size=N)
length_of_stay = rng.randint(1, 21, size=N)
previous_admissions = rng.poisson(0.8, size=N).clip(0, 5)

# Create correlations
sickness_factor = 0.02 * (age - 65) + 0.3 * comorb + rng.normal(0, 0.5, size=N)
medication_count = (medication_count + (sickness_factor * 2)).clip(0, 20).astype(int)
length_of_stay = (length_of_stay + (sickness_factor * 1.5)).clip(1, 30).astype(int)

# Logistic function. Prior admissions carry the largest weight, in line with
# published readmission indices (e.g. LACE). The intercept keeps the overall
# readmission rate realistic (~20%) instead of labelling almost everyone positive.
logit = (
    -2.6 +
    0.03 * (age - 65) +
    0.02 * (hr - 90) -
    0.15 * (spo2 - 94) -
    0.01 * (sbp - 110) +
    0.005 * (creatinine - 120) +
    0.3 * comorb +
    0.08 * (medication_count - 7) +
    0.8 * high_risk_meds +
    0.05 * (length_of_stay - 10) +
    0.9 * previous_admissions
)

prob = 1 / (1 + np.exp(-logit))
# Sample the outcome so labels carry real-world noise, rather than thresholding at 0.5
y = rng.binomial(1, prob)

X = pd.DataFrame({
    "age": age,
    "hr": hr,
    "spo2": spo2,
    "sbp": sbp,
    "creatinine": creatinine,
    "comorb": comorb,
    "medication_count": medication_count,
    "high_risk_meds": high_risk_meds,
    "length_of_stay": length_of_stay,
    "previous_admissions": previous_admissions,
})

print(f"✓ Generated {N} patient records")
print(f"  Positive cases: {y.sum()} ({100*y.mean():.1f}%)")

# Split data
print("\n[2/5] Splitting data (75% train, 25% test)...")
Xtr, Xte, ytr, yte = train_test_split(X, y, stratify=y, test_size=0.25, random_state=42)
print(f"  Training: {len(Xtr)} samples")
print(f"  Test: {len(Xte)} samples")

# Train model
print("\n[3/5] Training Gradient Boosting model...")
model = GradientBoostingClassifier(
    n_estimators=150,
    learning_rate=0.05,
    max_depth=3,
    random_state=42
)
model.fit(Xtr, ytr)
print("✓ Training complete")

# Evaluate
print("\n[4/5] Evaluating model...")
y_pred = model.predict(Xte)
y_proba = model.predict_proba(Xte)[:, 1]

acc = accuracy_score(yte, y_pred)
auc = roc_auc_score(yte, y_proba)
baseline_acc = max(yte.mean(), 1 - yte.mean())
# Recall/precision at the app's HIGH threshold (score >= 35)
high_pred = (y_proba >= 0.35).astype(int)
prec_high = precision_score(yte, high_pred, zero_division=0)
rec_high = recall_score(yte, high_pred, zero_division=0)

print(f"\n{'='*60}")
print(f"PERFORMANCE METRICS")
print(f"{'='*60}")
print(f"Accuracy:  {acc:.3f} ({acc*100:.1f}%)  [baseline: {baseline_acc*100:.1f}%]")
print(f"ROC-AUC:   {auc:.3f}")
print(f"HIGH (>=35) precision: {prec_high:.3f}  recall: {rec_high:.3f}")
print(f"{'='*60}\n")

print("Classification Report:")
print(classification_report(yte, y_pred, target_names=["No Readmission", "Readmission"], digits=3))

# Feature importance
feature_imp = model.feature_importances_
imp_df = pd.DataFrame({
    'Feature': X.columns,
    'Importance': feature_imp,
    'Importance %': feature_imp * 100
}).sort_values('Importance', ascending=False)

print("\n" + "="*60)
print("FEATURE IMPORTANCE")
print("="*60)
print(imp_df.to_string(index=False))
print("="*60)

# Save model
print("\n[5/5] Saving model...")
os.makedirs(MODELS_DIR, exist_ok=True)

model_path = os.path.join(MODELS_DIR, "enhanced_model.joblib")
dump(model, model_path)
print(f"✓ Saved model: {model_path}")

# Save metadata
metadata = {
    "algorithm": "GradientBoostingClassifier",
    "model_version": "2.1",
    "sklearn_version": sklearn.__version__,
    "trained_on": int(time.time()),
    "train_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    "n_samples": int(X.shape[0]),
    "n_features": int(X.shape[1]),
    "features": list(X.columns),
    "positive_rate": float(y.mean()),
    "accuracy": float(acc),
    "baseline_accuracy": float(baseline_acc),
    "auc": float(auc),
    "high_threshold_precision": float(prec_high),
    "high_threshold_recall": float(rec_high),
    "feature_importance": {feat: float(imp) for feat, imp in zip(X.columns, feature_imp)},
    # Used by the app to fill vitals/labs that have not been recorded yet
    "feature_medians": {col: float(X[col].median()) for col in X.columns},
    "description": "Enhanced readmission risk model with medications, LOS, and prior admissions"
}

metadata_path = os.path.join(MODELS_DIR, "enhanced_metadata.json")
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"✓ Saved metadata: {metadata_path}")

# Save training data
training_data = X.copy()
training_data["label"] = y
training_data_path = os.path.join(MODELS_DIR, "enhanced_training_data.csv")
training_data.to_csv(training_data_path, index=False)
print(f"✓ Saved training data: {training_data_path}")

print("\n" + "="*60)
print("TRAINING COMPLETE!")
print("="*60)
print("\nNext steps:")
print("  1. flask --app app seed")
print("  2. python app.py")
print("  3. Visit: http://127.0.0.1:5000")
print("="*60)
