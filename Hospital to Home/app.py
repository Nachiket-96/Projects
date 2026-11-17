from datetime import datetime, timezone
import os, json, secrets
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy

# App setup
app = Flask(__name__)
app.secret_key = os.environ.get("H2H_SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///h2h.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

def utcnow():
    """Naive UTC timestamp (SQLite stores datetimes without timezone)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ML Model Loading
from joblib import load
import pandas as pd
import sklearn

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "enhanced_model.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, "enhanced_metadata.json")
FEATURES = ["age", "hr", "spo2", "sbp", "creatinine", "comorb",
            "medication_count", "high_risk_meds", "length_of_stay", "previous_admissions"]

model_meta = {}
if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH) as f:
        model_meta = json.load(f)
FEATURE_MEDIANS = model_meta.get("feature_medians", {})

ml_model = None
if os.path.exists(MODEL_PATH):
    trained_with = model_meta.get("sklearn_version")
    if trained_with and trained_with != sklearn.__version__:
        print(f"⚠ Model trained with scikit-learn {trained_with}, running {sklearn.__version__} - retrain the model")
    try:
        ml_model = load(MODEL_PATH)
        print("✓ ML model loaded successfully")
    except Exception as e:
        print(f"⚠ ML model load failed: {e} - using rule-based scoring")
else:
    print("⚠ ML model not found - using rule-based scoring")

# Database Models
careteam_association = db.Table(
    "careteam_association",
    db.Column("patient_id", db.Integer, db.ForeignKey("patient.id")),
    db.Column("member_id", db.Integer, db.ForeignKey("care_team_member.id")),
)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phn = db.Column(db.String(30), unique=True)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(10))
    conditions = db.Column(db.String(500), default="")
    
    # NEW: Enhanced features
    medication_count = db.Column(db.Integer, default=0)
    high_risk_meds = db.Column(db.Boolean, default=False)
    length_of_stay = db.Column(db.Integer, default=0)
    previous_admissions = db.Column(db.Integer, default=0)
    
    last_vitals = db.Column(db.Text, default="{}")
    last_lab = db.Column(db.Text, default="{}")
    admitted_at = db.Column(db.DateTime, default=utcnow)
    discharged_at = db.Column(db.DateTime, nullable=True)
    risk_score = db.Column(db.Float, default=0.0)
    risk_label = db.Column(db.String(20), default="LOW")

    care_plan = db.relationship("CarePlan", backref="patient", uselist=False)
    care_team = db.relationship("CareTeamMember", secondary=careteam_association, backref="patients")
    notifications = db.relationship("Notification", backref="patient", order_by="desc(Notification.created_at)")

class CarePlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    plan_json = db.Column(db.Text, default="{}")
    updated_at = db.Column(db.DateTime, default=utcnow)

class CareTeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))
    name = db.Column(db.String(120))
    contact = db.Column(db.String(120))
    org = db.Column(db.String(120))
    notify_enabled = db.Column(db.Boolean, default=True)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    audience = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)
    read = db.Column(db.Boolean, default=False)

# Helper Functions
def features_from_patient(patient):
    """Extract features for ML model"""
    vit = json.loads(patient.last_vitals or "{}")
    lab = json.loads(patient.last_lab or "{}")
    comorb = len([c for c in (patient.conditions or "").split(",") if c.strip()])

    def measured(value, name):
        # Unrecorded vitals/labs get the training median instead of 0,
        # which would be far outside the range the model was trained on
        if value in (None, ""):
            return float(FEATURE_MEDIANS.get(name, 0))
        return float(value)

    return {
        "age": float(patient.age or 0),
        "hr": measured(vit.get("hr"), "hr"),
        "spo2": measured(vit.get("spo2"), "spo2"),
        "sbp": measured(vit.get("sbp"), "sbp"),
        "creatinine": measured(lab.get("creatinine"), "creatinine"),
        "comorb": float(comorb),
        "medication_count": float(patient.medication_count or 0),
        "high_risk_meds": float(1 if patient.high_risk_meds else 0),
        "length_of_stay": float(patient.length_of_stay or 0),
        "previous_admissions": float(patient.previous_admissions or 0),
    }

def compute_risk(patient):
    """Compute risk score and label"""
    if ml_model is not None:
        # Use ML model
        feat = features_from_patient(patient)
        X = pd.DataFrame([feat]).reindex(columns=FEATURES, fill_value=0)
        prob = float(ml_model.predict_proba(X)[0, 1])
        score = round(prob * 100, 1)
    else:
        # Rule-based fallback
        vitals = json.loads(patient.last_vitals or "{}")
        labs = json.loads(patient.last_lab or "{}")
        score = 0.0
        
        score += 0.5 * max(0, int(patient.age) - 65)
        conds = [c.strip() for c in (patient.conditions or "").split(",") if c.strip()]
        score += 3.0 * len(conds)
        
        hr = vitals.get("hr")
        spo2 = vitals.get("spo2")
        sbp = vitals.get("sbp")
        if hr and (hr < 50 or hr > 110): score += 7
        if spo2 and spo2 < 92: score += 10
        if sbp and sbp < 95: score += 6
        
        creat = labs.get("creatinine")
        if creat and float(creat) > 150: score += 7
        
        meds = patient.medication_count or 0
        los = patient.length_of_stay or 0
        score += 1.5 * meds
        if patient.high_risk_meds: score += 8
        if los > 7: score += 6
        elif los > 3: score += 3
        score += 4 * (patient.previous_admissions or 0)
        
        score = min(100.0, float(score))
    
    # Determine label
    if score >= 35:
        label = "HIGH"
    elif score >= 20:
        label = "MEDIUM"
    else:
        label = "LOW"
    
    return score, label

def get_risk_factors(patient):
    """Get list of risk factors for display"""
    factors = []
    vitals = json.loads(patient.last_vitals or "{}")
    labs = json.loads(patient.last_lab or "{}")
    
    if patient.age > 75:
        factors.append({"factor": "Advanced age", "value": f"{patient.age} years", "severity": "medium"})
    
    conds = [c.strip() for c in (patient.conditions or "").split(",") if c.strip()]
    if len(conds) >= 3:
        factors.append({"factor": "Multiple comorbidities", "value": f"{len(conds)} conditions", "severity": "high"})
    
    hr = vitals.get("hr")
    if hr and (hr < 50 or hr > 110):
        factors.append({"factor": "Abnormal heart rate", "value": f"{hr} bpm", "severity": "high"})
    
    spo2 = vitals.get("spo2")
    if spo2 and spo2 < 92:
        factors.append({"factor": "Low oxygen saturation", "value": f"{spo2}%", "severity": "critical"})
    
    if patient.medication_count >= 5:
        factors.append({"factor": "Polypharmacy", "value": f"{patient.medication_count} medications", "severity": "medium"})
    
    if patient.high_risk_meds:
        factors.append({"factor": "High-risk medications", "value": "Warfarin/Insulin/etc", "severity": "high"})
    
    if patient.length_of_stay > 7:
        factors.append({"factor": "Extended hospital stay", "value": f"{patient.length_of_stay} days", "severity": "medium"})
    
    if patient.previous_admissions >= 2:
        factors.append({"factor": "Recent readmissions", "value": f"{patient.previous_admissions} in 12 months", "severity": "high"})
    
    return factors

def push_notification(patient, title, body, audience_roles):
    """Create notification"""
    n = Notification(patient_id=patient.id, title=title, body=body, audience=",".join(audience_roles))
    db.session.add(n)
    db.session.commit()

def recompute_and_alert(patient):
    """Recompute risk, save, and notify the team only when risk newly reaches HIGH"""
    previous_label = patient.risk_label
    patient.risk_score, patient.risk_label = compute_risk(patient)
    db.session.commit()

    if patient.risk_label == "HIGH" and previous_label != "HIGH":
        push_notification(patient, "Risk escalated to HIGH",
                          f"{patient.name}'s risk score: {patient.risk_score:.1f}. Immediate review needed.",
                          ["Family Physician", "Community Nurse"])

    return jsonify({"ok": True, "risk_score": patient.risk_score, "risk_label": patient.risk_label})

def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Expected a JSON object")
    return data

def non_negative_int(data, key):
    try:
        value = int(data.get(key, 0))
    except (TypeError, ValueError):
        abort(400, description=f"{key} must be a whole number")
    if value < 0:
        abort(400, description=f"{key} cannot be negative")
    return value

# Routes
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    rf = request.args.get("risk", "").upper().strip()
    status = request.args.get("status", "all")

    patients = Patient.query
    if q:
        like = f"%{q}%"
        patients = patients.filter((Patient.name.ilike(like)) | (Patient.phn.ilike(like)))
    if rf in ("LOW","MEDIUM","HIGH"):
        patients = patients.filter(Patient.risk_label == rf)
    
    if status == "active":
        patients = patients.filter(Patient.discharged_at.is_(None))
    elif status == "discharged":
        patients = patients.filter(Patient.discharged_at.isnot(None))

    patients = patients.order_by(Patient.risk_score.desc()).all()

    # Summary cards always describe the whole caseload, not the filtered table
    everyone = Patient.query.all()
    total = len(everyone)
    high_risk = len([p for p in everyone if p.risk_label == "HIGH"])
    medium_risk = len([p for p in everyone if p.risk_label == "MEDIUM"])
    low_risk = len([p for p in everyone if p.risk_label == "LOW"])
    active = len([p for p in everyone if p.discharged_at is None])

    latest_notifs = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    return render_template("index.html",
                           patients=patients,
                           notifs=latest_notifs,
                           q=q,
                           risk_filter=rf,
                           status_filter=status,
                           total=total,
                           high_risk=high_risk,
                           medium_risk=medium_risk,
                           low_risk=low_risk,
                           active=active)

@app.route("/patient/<int:pid>")
def patient_detail(pid):
    patient = db.get_or_404(Patient, pid)
    vitals = json.loads(patient.last_vitals or "{}")
    plan = json.loads(patient.care_plan.plan_json) if patient.care_plan else {}
    risk_factors = get_risk_factors(patient)
    return render_template("patient.html", patient=patient, vitals=vitals, plan=plan, risk_factors=risk_factors)

@app.route("/patient/<int:pid>/update_vitals", methods=["POST"])
def update_vitals(pid):
    patient = db.get_or_404(Patient, pid)
    data = json_body()
    vitals = json.loads(patient.last_vitals or "{}")

    for k in ("hr", "spo2", "sbp"):
        if k not in data:
            continue
        try:
            vitals[k] = float(data[k])
        except (TypeError, ValueError):
            abort(400, description=f"{k} must be a number")

    patient.last_vitals = json.dumps(vitals)
    return recompute_and_alert(patient)

@app.route("/patient/<int:pid>/update_medications", methods=["POST"])
def update_medications(pid):
    patient = db.get_or_404(Patient, pid)
    data = json_body()

    patient.medication_count = non_negative_int(data, "medication_count")
    patient.high_risk_meds = non_negative_int(data, "high_risk_meds") > 0

    return recompute_and_alert(patient)

@app.route("/patient/<int:pid>/update_hospitalization", methods=["POST"])
def update_hospitalization(pid):
    patient = db.get_or_404(Patient, pid)
    data = json_body()

    patient.length_of_stay = non_negative_int(data, "length_of_stay")
    patient.previous_admissions = non_negative_int(data, "previous_admissions")

    return recompute_and_alert(patient)

@app.route("/patient/<int:pid>/update_plan", methods=["POST"])
def update_plan(pid):
    patient = db.get_or_404(Patient, pid)
    payload = json_body()
    if not patient.care_plan:
        patient.care_plan = CarePlan(plan_json=json.dumps(payload), updated_at=utcnow())
    else:
        patient.care_plan.plan_json = json.dumps(payload)
        patient.care_plan.updated_at = utcnow()
    db.session.commit()
    push_notification(patient, "Care plan updated", "Shared care plan has been modified.", ["Family Physician","Community Nurse","Pharmacist"])
    return jsonify({"ok": True})

@app.route("/discharge/<int:pid>", methods=["POST"])
def discharge(pid):
    patient = db.get_or_404(Patient, pid)
    patient.discharged_at = utcnow()
    score, label = compute_risk(patient)
    patient.risk_score, patient.risk_label = score, label
    db.session.commit()
    push_notification(patient, "Patient discharged", 
                     f"{patient.name} discharged - Risk: {label} ({score:.1f})", 
                     ["Family Physician","Community Nurse","Pharmacist"])
    return redirect(url_for("patient_detail", pid=pid))

@app.route("/api/notifications")
def api_notifications():
    since = request.args.get("since")
    q = Notification.query
    if since:
        try:
            dt = datetime.fromisoformat(since)
            q = q.filter(Notification.created_at > dt)
        except ValueError:
            abort(400, description="since must be an ISO-8601 timestamp")
    items = q.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([{
        "id": n.id,
        "patient_id": n.patient_id,
        "title": n.title,
        "body": n.body,
        "audience": n.audience,
        "created_at": n.created_at.isoformat(),
    } for n in items])

# CLI Commands
# Demo caseload: (name, phn, age, sex, conditions, (hr, spo2, sbp), creatinine,
#                meds, high_risk_meds, length_of_stay, previous_admissions, admitted_days_ago, discharged_days_ago)
DEMO_PATIENTS = [
    ("Jordan Bear", "SK-0001", 72, "M", "CHF, COPD, T2DM", (112, 90, 98), 165, 10, True, 8, 3, 9, None),
    ("Samantha Lee", "SK-0002", 58, "F", "Hypertension", (88, 96, 132), None, 3, False, 2, 0, 3, None),
    ("Noah Cardinal", "SK-0003", 83, "M", "CKD, CAD", (94, 91, 90), 180, 12, True, 10, 3, 12, None),
    ("Priya Sharma", "SK-0004", 66, "F", "T2DM, Hypertension", (92, 94, 118), 130, 7, True, 5, 0, 6, 1),
    ("Liam Okafor", "SK-0005", 45, "M", "Asthma", (78, 98, 124), 85, 2, False, 1, 0, 4, 3),
    ("Grace Whitehorse", "SK-0006", 79, "F", "COPD, Osteoporosis", (104, 92, 108), 120, 8, False, 7, 0, 8, None),
    ("Ethan Moreau", "SK-0007", 61, "M", "CAD", (96, 94, 112), 105, 5, True, 4, 1, 5, None),
    ("Olivia Bighead", "SK-0008", 88, "F", "CHF, AFib, CKD, Dementia", (116, 89, 92), 210, 14, True, 14, 4, 15, None),
    ("Daniel Kowalski", "SK-0009", 53, "M", "", (74, 99, 120), 90, 1, False, 2, 0, 7, 5),
    ("Aisha Rahman", "SK-0010", 70, "F", "CHF, T2DM", (98, 93, 104), 150, 9, True, 6, 2, 7, None),
    ("Marcus Thunderchild", "SK-0011", 67, "M", "COPD", (90, 93, 115), 115, 6, False, 4, 1, 5, 1),
    ("Emily Chen", "SK-0012", 49, "F", "Hypothyroidism", (70, 98, 116), 80, 2, False, 1, 0, 2, None),
    ("Robert Lafleur", "SK-0013", 76, "M", "CAD, Hypertension, CKD", (86, 95, 140), 160, 9, True, 9, 2, 10, None),
    ("Hannah Nakamura", "SK-0014", 63, "F", "Hypertension, Hyperlipidemia", (88, 95, 136), 100, 4, False, 3, 1, 4, 2),
    ("Victor Ironchild", "SK-0015", 81, "M", "AFib, Stroke history", (100, 94, 110), 135, 8, True, 6, 0, 7, None),
]

CARE_PLANS = {
    "HIGH": {
        "follow_up": {"who": "Family Physician", "within_days": 2},
        "home_care": {"visits_per_week": 5, "first_visit_within_hours": 48},
        "pharmacy": {"meds_review": True, "blister_packs": True},
        "monitoring": {"daily_vitals": True, "escalate_if": "SpO2 < 90 or HR > 120"},
    },
    "MEDIUM": {
        "follow_up": {"who": "Family Physician", "within_days": 7},
        "home_care": {"visits_per_week": 2},
        "pharmacy": {"meds_review": True},
        "monitoring": {"phone_check_in": "weekly"},
    },
    "LOW": {
        "follow_up": {"who": "Family Physician", "within_days": 14},
        "home_care": {"visits_per_week": 0},
        "pharmacy": {"meds_review": False},
    },
}

@app.cli.command("seed")
def seed():
    """Seed database with demo data"""
    from datetime import timedelta
    db.drop_all()
    db.create_all()

    team = {
        "fp": [CareTeamMember(role="Family Physician", name="Dr. Singh", contact="dr.singh@example.ca", org="Queen City Medical"),
               CareTeamMember(role="Family Physician", name="Dr. Fontaine", contact="dr.fontaine@example.ca", org="Wascana Family Clinic")],
        "nurse": [CareTeamMember(role="Community Nurse", name="A. Greyeyes", contact="nurse.greyeyes@example.ca", org="SaskHealth Home Care"),
                  CareTeamMember(role="Community Nurse", name="J. Morin", contact="nurse.morin@example.ca", org="SaskHealth Home Care")],
        "pharm": [CareTeamMember(role="Pharmacist", name="M. Patel", contact="mpatel@example.ca", org="Regent Park Pharmacy"),
                  CareTeamMember(role="Pharmacist", name="S. Nguyen", contact="snguyen@example.ca", org="Cathedral Pharmacy")],
        "sw": CareTeamMember(role="Social Worker", name="K. Desjarlais", contact="kdesjarlais@example.ca", org="Regina Community Services"),
        "pt": CareTeamMember(role="Physiotherapist", name="L. Becker", contact="lbecker@example.ca", org="SaskHealth Rehab"),
    }
    db.session.add_all(team["fp"] + team["nurse"] + team["pharm"] + [team["sw"], team["pt"]])
    db.session.commit()

    now = utcnow()
    notifications = []
    for i, (name, phn, age, sex, conds, (hr, spo2, sbp), creat, meds, hrm, los, prior, admitted_ago, discharged_ago) in enumerate(DEMO_PATIENTS):
        p = Patient(
            name=name, phn=phn, age=age, sex=sex, conditions=conds,
            last_vitals=json.dumps({"hr": hr, "spo2": spo2, "sbp": sbp}),
            last_lab=json.dumps({"creatinine": creat} if creat else {}),
            medication_count=meds, high_risk_meds=hrm,
            length_of_stay=los, previous_admissions=prior,
            admitted_at=now - timedelta(days=admitted_ago),
            discharged_at=now - timedelta(days=discharged_ago) if discharged_ago is not None else None,
        )
        p.risk_score, p.risk_label = compute_risk(p)
        p.care_plan = CarePlan(plan_json=json.dumps(CARE_PLANS[p.risk_label]))
        p.care_team.extend([team["fp"][i % 2], team["nurse"][i % 2], team["pharm"][i % 2]])
        if p.risk_label == "HIGH":
            p.care_team.append(team["sw"])
        if los >= 7:
            p.care_team.append(team["pt"])
        db.session.add(p)
        db.session.flush()

        # Notification history so the dashboard feed has realistic activity
        if p.risk_label == "HIGH":
            notifications.append(Notification(
                patient_id=p.id, title="Risk escalated to HIGH",
                body=f"{p.name}'s risk score: {p.risk_score:.1f}. Immediate review needed.",
                audience="Family Physician,Community Nurse",
                created_at=now - timedelta(hours=6 + i * 3)))
        if p.discharged_at:
            notifications.append(Notification(
                patient_id=p.id, title="Patient discharged",
                body=f"{p.name} discharged - Risk: {p.risk_label} ({p.risk_score:.1f})",
                audience="Family Physician,Community Nurse,Pharmacist",
                created_at=p.discharged_at))
        if i % 3 == 0:
            notifications.append(Notification(
                patient_id=p.id, title="Care plan updated",
                body=f"Shared care plan for {p.name} has been modified.",
                audience="Family Physician,Community Nurse,Pharmacist",
                created_at=now - timedelta(hours=2 + i * 4)))

    db.session.add_all(notifications)
    db.session.commit()
    print(f"✓ Seeded database with {len(DEMO_PATIENTS)} patients and {len(notifications)} notifications")

@app.context_processor
def inject_now():
    return {"now": utcnow}

AVATAR_COLORS = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed", "#2563eb", "#dc2626"]

@app.template_filter("initials")
def initials(name):
    parts = (name or "").split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"

@app.template_filter("avatar_color")
def avatar_color(name):
    return AVATAR_COLORS[sum(map(ord, name or "")) % len(AVATAR_COLORS)]

@app.template_filter("conditions_list")
def conditions_list(conditions):
    return [c.strip() for c in (conditions or "").split(",") if c.strip()]

@app.template_filter("notif_kind")
def notif_kind(title):
    """Visual category for a notification, shared with static/app.js"""
    t = (title or "").lower()
    if "high" in t:
        return "alert"
    if "discharged" in t:
        return "discharge"
    return "plan"

@app.template_filter("timeago")
def timeago(dt):
    seconds = int((utcnow() - dt).total_seconds())
    if seconds < 60:
        return "just now"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit} ago"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")