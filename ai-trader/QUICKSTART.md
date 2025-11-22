# Quick Start Guide - Running the Web Dashboard

## Option 1: Full System with Docker (All Services)

### Start Everything:
```bash
cd c:\Github\Personal\TradingSystem\ai-trader\deploy
docker-compose up -d
```

### Access the Dashboard:
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001

### Stop Services:
```bash
docker-compose down
```

---

## Option 2: Frontend Only (Development)

### Install Dependencies:
```bash
cd c:\Github\Personal\TradingSystem\ai-trader\ui
npm install
```

### Start Dev Server:
```bash
npm run dev
```

### Access:
- **Dashboard**: http://localhost:5173

**Note**: Frontend-only won't connect to backend unless backend services are running.

---

## Quick Demo (Frontend Only - 2 Minutes)

If you just want to see the UI without configuring credentials:

```bash
# Navigate to UI folder
cd c:\Github\Personal\TradingSystem\ai-trader\ui

# Install dependencies (one-time)
npm install

# Start dev server
npm run dev
```

Then open http://localhost:5173 in your browser!

The UI will show but won't have live data without the backend running.
