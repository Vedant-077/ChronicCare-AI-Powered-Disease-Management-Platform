# ChronicCare — Day 1 + Day 2 + Day 3 + Day 4

**Day 1:** patient signup/login, a protected profile, and a diagnosis-history log.
**Day 2:** medicines with reminder times, and a background scheduler that fires
reminders automatically — plus a notification bell on the dashboard.
**Day 3:** a Scikit-learn model that predicts a "Risk Level" (Low/Medium/High)
from 4 numbers (glucose, blood pressure, BMI, age), served through a
`/risk/predict` endpoint and shown as a badge on the dashboard.
**Day 4:** real browser pop-up alerts for reminders (not just the in-app
bell), and a trend chart showing how your risk level has changed over time.

## How to run it on your own machine

You need **Python 3.10+** and **Node.js 18+** installed first.

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv

# Activate the virtual environment:
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
uvicorn main:app --reload
```

Backend now runs at **http://localhost:8000**
Open **http://localhost:8000/docs** — FastAPI auto-generates an interactive
page where you can test every endpoint by clicking buttons.

### 2. Frontend (React)

Open a **second terminal** (keep the backend running in the first one):

```bash
cd frontend
npm install
npm run dev
```

Frontend now runs at **http://localhost:5173** — open that in your browser.

## What each folder is

```
backend/
  database.py       -> connects to the database (SQLite file)
  models.py         -> defines the "tables" (User, DiagnosisHistory, Medicine, Notification, RiskAssessment)
  schemas.py        -> defines what valid requests/responses look like
  auth.py           -> password hashing + login tokens (JWT)
  scheduler.py      -> background job: checks every 60s if a reminder is due
  main.py           -> every API route
  ml/train_model.py -> run ONCE to train + save the risk model (risk_model.pkl)
  ml/predictor.py   -> loads risk_model.pkl and runs predictions
  ml/risk_model.pkl -> the already-trained model file (included, ready to use)

frontend/
  src/api.js    -> all calls to the backend, in one place
  src/App.jsx   -> Login, Register, Dashboard (profile, medicines, readings, bell, risk check)
  src/App.css   -> all styling
```

## Try it

1. Open http://localhost:5173, register an account
2. In "Medicines & reminders," add a medicine with a reminder time set to
   **1-2 minutes from now** (use the time picker)
3. Wait — within a minute of that time, the bell icon in the top-right will
   show a red badge with the reminder
4. The reminder was created entirely by the background scheduler, with no
   button click involved — that's the point of a "background task scheduler"

## Try Day 3 (risk check)

1. Open the dashboard and find the **"Risk check"** panel
2. Enter 4 numbers: fasting glucose, systolic blood pressure, BMI, and age
   (try `180, 150, 34, 62` for a high-risk example, or `90, 115, 22, 30` for
   a low-risk one)
3. Click **"Check my risk"** — the model responds instantly (it's not
   retraining, just asking an already-trained model for a prediction) and a
   colored **Risk Level** badge appears next to your profile, plus a
   confidence percentage in the panel
4. Every check is saved, so `GET /risk/history` in the API docs shows your
   past checks too

## Try Day 4 (browser alerts + risk trend)

1. A banner appears under the top bar: **"Want reminders as real browser
   pop-ups..."** — click **"Enable browser alerts"** and allow the
   permission prompt your browser shows
2. Add a medicine with a reminder time 1-2 minutes out, like in Day 2 — this
   time, when it fires, you'll get a real OS-level notification popup, not
   just the in-app bell badge
3. Run the risk check (Day 3) two or more times with different numbers — a
   small line chart appears under the risk panel showing Low → Medium →
   High over time

## Design decision: APScheduler instead of Celery + Redis

The original project plan mentioned Celery + Redis for scheduling. We used
**APScheduler** instead for Day 2, because it runs inside the same Python
process as the API — no separate Redis server to install and keep running.
For a resume, describe this honestly as: *"Implemented a background task
scheduler (APScheduler) that checks medicine schedules and generates
reminder notifications."* Celery + Redis is the standard upgrade path if
this needed to scale across multiple servers — worth knowing about, but not
what's actually running here.

## Design decision: synthetic training data instead of a downloaded dataset

The original Day 3 plan said "train on a public dataset" (e.g. the Pima
Indians Diabetes dataset). The sandbox this was built in had no internet
access to download one, so `ml/train_model.py` generates its own training
data instead — using the **same real clinical risk thresholds** a doctor
would recognize (fasting glucose ≥126 = diabetic range, ≥100 = prediabetic
per ADA; BMI ≥30 = obese per WHO; systolic BP ≥130 = elevated per AHA; age
as a compounding factor), plus randomized noise so the model has to actually
learn the pattern rather than memorize an if/else rule. It trains a
`RandomForestClassifier` and validates ~78% accuracy on held-out test data
(this was run and confirmed working, not just written and assumed to work).

**Resume-accurate phrasing:** *"Trained a Scikit-learn RandomForest
classifier on clinically-informed patient data to predict a 3-tier health
risk level, served through a FastAPI endpoint."* If you want it trained on
a real downloaded dataset instead, `ml/train_model.py` has a comment at the
bottom showing exactly what to swap in — it's a 3-line change.

## Design decision: browser Notification API instead of real push/SMS

The Day 3 "Next" list suggested real push/SMS (Firebase Cloud Messaging or
Twilio) for Day 4. Both need a paid/registered external service and API
keys — not something to wire up sight-unseen. Instead, Day 4 uses the
browser's built-in **Notification API**: once you grant permission, the app
can pop a real OS-level notification (the kind that shows even if the
ChronicCare tab isn't focused). The honest limitation: the browser tab
still has to be *open* somewhere (even in the background) for this to work,
since there's no service worker yet — closing the tab or browser stops it.
Real push (via FCM/APNs) is the correct next step if you need alerts to
arrive even with the browser fully closed — that requires a backend
registration flow and a paid/free-tier push service, which is a good
"Day 5" scope.

**Resume-accurate phrasing:** *"Implemented browser-based push notifications
using the Web Notification API for real-time medicine reminders."* — don't
call it "push notifications" in the FCM/native-app sense unless you build
that layer too.

## Known limitations (fix later)

- `bcrypt` is pinned to `4.0.1` in requirements.txt — newer versions have a
  compatibility bug with `passlib`. Re-pin it if you ever see a bcrypt error
  after upgrading packages.
- Reminders are currently in-app only (shown via the bell icon while the
  dashboard is open). Real push/SMS notifications (e.g. via Firebase Cloud
  Messaging or Twilio) would be a good "Day 4 polish" addition if you want
  it to work even when the browser tab is closed.
- **This build wasn't run end-to-end live** the way Day 1 and Day 2 were.
  This sandbox has no internet access this session, so `pip install`/
  `npm install` can't reach the package registries to actually start the
  servers together. What *was* verified directly this round: the trend-chart
  coordinate math (tested standalone with Node — an oldest-to-newest line
  where Low plots lower than High, confirmed correct) and every brace/
  paren/bracket in App.jsx is balanced. The Day 3 ML pipeline was verified
  live in the Day 3 session. Run the "How to run it" steps on your own
  machine to see Day 4 live — if the browser alert permission prompt or the
  trend chart don't behave as expected, paste me the error and I'll fix it.
- Browser alerts fire for any reminder that's unread at the moment you
  enable them, even old ones — so if you have unread reminders sitting in
  the bell already, turning alerts on may pop several at once. Not a bug,
  just worth knowing.

## Next (Day 5 ideas)

- Real push notifications (Firebase Cloud Messaging) so alerts work even
  with the browser fully closed, via a service worker + push subscription
- Swap the synthetic training data for a real downloaded dataset
- Export diagnosis history / risk history as a PDF report for a doctor visit

