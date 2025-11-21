from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import database
from tracker import get_weekly_volume, get_weekly_streak

app = FastAPI(title="Habit Tracker API")

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('templates/index.html')

@app.get("/stats")
def read_stats():
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

@app.get("/logs")
def read_logs():
    return database.get_all_logs()

@app.post("/log")
def add_log():
    database.add_log()
    return {"status": "success"}
