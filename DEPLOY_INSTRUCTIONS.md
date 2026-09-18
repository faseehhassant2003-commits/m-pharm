# Deploying to Render.com (Free Live Link)

This gives you ONE public URL (e.g. `https://your-app.onrender.com`) that
serves both the web page and the prediction API — nothing for the client
to install or run.

## What's in this folder

- `app.py` — Flask app (API + serves the web page)
- `predict.py` — prediction logic
- `metabolic_risk_model.pkl` — trained model
- `static/index.html` — the web page (served automatically at `/`)
- `requirements.txt` — exact library versions needed

## Steps

### 1. Create a free GitHub account (if you don't have one)
https://github.com/signup

### 2. Create a new repository
- Go to https://github.com/new
- Name it e.g. `metabolic-risk-tool`
- Keep it Public (Render's free tier needs this, or Private works too on
  most plans) → Create repository

### 3. Upload these files to the repository
Easiest way (no command line needed):
- On your new repo's page, click "uploading an existing file"
- Drag in: `app.py`, `predict.py`, `metabolic_risk_model.pkl`, `requirements.txt`
- Create a folder named `static` and upload `index.html` into it
  (GitHub lets you do this by naming the uploaded file `static/index.html`)
- Click "Commit changes"

### 4. Create a free Render account
https://render.com/ → Sign up (you can sign up directly with your GitHub account)

### 5. Create a new Web Service
- Click "New +" → "Web Service"
- Connect your GitHub account, select the `metabolic-risk-tool` repository
- Fill in:
  - **Name**: metabolic-risk-tool (or anything)
  - **Region**: closest to you
  - **Branch**: main
  - **Runtime**: Python 3
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn app:app`
  - **Instance Type**: Free
- Click "Create Web Service"

### 6. Wait for it to build (2-5 minutes)
Render will show build logs. Once it says "Live", your app is running at
a URL like:
```
https://metabolic-risk-tool.onrender.com
```

### 7. Send that link to your client
Opening it shows the same web form you tested locally — clicking
"Predict Risk" calls the API on the same server, no separate setup needed.

## Notes

- **Free tier sleeps after inactivity.** If no one visits for ~15 minutes,
  Render puts the app to sleep; the next visit takes ~30-50 seconds to
  wake up. This is normal on the free tier — mention it to your client so
  they're not confused by the first slow load.
- **To update later**, just upload new files to the same GitHub repo —
  Render automatically rebuilds and redeploys.
- **Keep `metabolic_risk_model.pkl` in the repo** — it's the trained
  model; the app can't make predictions without it.
