import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import database
from tracker import get_weekly_volume, get_weekly_streak

logger = logging.getLogger(__name__)

app = FastAPI(title="Habit Tracker API")

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS — restricted to local network origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('templates/index.html')

def _compute_stats():
    """Shared stats computation using bounded queries."""
    since = (datetime.now() - timedelta(weeks=53)).isoformat()
    recent_history = database.get_logs_since(since)
    offset = database.get_offset()
    return {
        "volume": get_weekly_volume(recent_history),
        "streak": get_weekly_streak(recent_history),
        "total": database.get_log_count() + offset,
    }

@app.get("/dashboard")
def read_dashboard():
    """Single endpoint returning logs and stats."""
    try:
        stats = _compute_stats()
        since = (datetime.now() - timedelta(weeks=53)).isoformat()
        logs = database.get_logs_since(since)
        return {"logs": logs, "stats": stats}
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@app.get("/stats")
def read_stats():
    try:
        return _compute_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load stats")

@app.get("/logs")
def read_logs():
    try:
        return database.get_all_logs()
    except Exception as e:
        logger.error(f"Logs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load logs")

@app.post("/log")
def add_log():
    try:
        database.add_log()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add log")
