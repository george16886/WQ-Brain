from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import json
import os
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlphaRequest(BaseModel):
    content: str

@app.get("/api/alphas")
def get_alphas():
    if os.path.exists("alphas.txt"):
        with open("alphas.txt", "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": ""}

@app.post("/api/alphas")
def save_alphas(req: AlphaRequest):
    with open("alphas.txt", "w", encoding="utf-8") as f:
        f.write(req.content)
    return {"status": "success"}

@app.get("/api/settings")
def get_settings():
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.post("/api/settings")
def save_settings(req: Dict[str, Any]):
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(req, f, indent=4)
    return {"status": "success"}

@app.get("/api/stats")
def get_stats():
    import importlib
    import parameters
    importlib.reload(parameters)
    return {
        "alphas": len(parameters.codes),
        "simulations": len(parameters.DATA)
    }

current_process = None

@app.post("/api/run")
def run_simulation():
    global current_process
    if current_process and current_process.poll() is None:
        return {"status": "already running"}

    if not os.path.exists("data"):
        os.makedirs("data")
    log_file = "data/sim_latest.log"
    # 清空原本的 log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("Simulation Started...\n")
    
    try:
        current_process = subprocess.Popen(["python", "-u", "main.py"], stdout=open(log_file, "a", encoding="utf-8"), stderr=subprocess.STDOUT)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
def stop_simulation():
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate()
        return {"status": "stopped"}
    return {"status": "not running"}

@app.post("/api/shutdown")
def shutdown_server():
    import threading
    def shutdown():
        os._exit(0)
    threading.Timer(0.5, shutdown).start()
    return {"status": "shutting down"}

@app.get("/api/logs")
def get_logs():
    log_file = "data/sim_latest.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            return {"content": f.read()}
    return {"content": "Waiting for simulation to start...\n"}

# 確保 static 目錄存在
if not os.path.exists("static"):
    os.makedirs("static")

# 掛載前端靜態檔案
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting WQ-Brain Web UI on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
