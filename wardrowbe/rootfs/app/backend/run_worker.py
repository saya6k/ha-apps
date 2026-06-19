#!/opt/venv/bin/python3
import sys, os
sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")
try:
    from app.workers.worker import WorkerSettings
except ImportError:
    from app.workers.tagging import WorkerSettings
from arq.worker import run_worker
run_worker(WorkerSettings)
