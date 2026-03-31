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

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('templates/index.html')

@app.get("/dashboard")
def read_dashboard():
    """Single endpoint returning logs and stats in one DB read."""
    try:
        history = database.get_all_logs()
        offset = database.get_offset()

        vol = get_weekly_volume(history)
        streak = get_weekly_streak(history)
        total = len(history) + offset

        return {
            "logs": history,
            "stats": {
                "volume": vol,
                "streak": streak,
                "total": total
            }
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@app.get("/stats")
def read_stats():
    try:
        history = database.get_all_logs()
        offset = database.get_offset()

        vol = get_weekly_volume(history)
        streak = get_weekly_streak(history)
        total = len(history) + offset

        return {
            "volume": vol,
            "streak": streak,
            "total": total
        }
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
