import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database
from tracker import get_weekly_volume, get_weekly_streak

logger = logging.getLogger(__name__)

# Bound history queries to ~1 year; gives a safety margin over a 52-week heatmap.
RECENT_HISTORY_WEEKS = 53


class LogRequest(BaseModel):
    timestamp: str


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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('templates/index.html')

def _recent_history_cutoff() -> str:
    return (datetime.now() - timedelta(weeks=RECENT_HISTORY_WEEKS)).isoformat()

def _compute_stats(recent_history: list[str]) -> dict:
    """Compute stats from an already-fetched window of recent logs."""
    offset = database.get_offset()
    return {
        "volume": get_weekly_volume(recent_history),
        "streak": get_weekly_streak(recent_history),
        "total": database.get_log_count() + offset,
    }

@app.get("/dashboard")
def read_dashboard():
    """Single endpoint returning logs and stats from one DB read."""
    try:
        logs = database.get_logs_since(_recent_history_cutoff())
        return {"logs": logs, "stats": _compute_stats(logs)}
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@app.get("/stats")
def read_stats():
    try:
        recent_history = database.get_logs_since(_recent_history_cutoff())
        return _compute_stats(recent_history)
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

@app.get("/logs/{date}")
def read_logs_for_date(date: str):
    try:
        return database.get_logs_for_date(date)
    except Exception as e:
        logger.error(f"Logs for date error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load logs for date")

@app.post("/log")
def add_log(body: Optional[LogRequest] = None):
    try:
        if body and body.timestamp:
            database.add_log(body.timestamp)
        else:
            database.add_log()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add log")

@app.delete("/log/{log_id}")
def delete_log(log_id: int):
    try:
        if database.delete_log(log_id):
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Log not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete log")
