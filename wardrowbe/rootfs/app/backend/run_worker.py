#!/opt/venv/bin/python3
import sys
import os
sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")
try:
    from app.workers.worker import WorkerSettings
except ImportError:
    from app.workers.tagging import WorkerSettings
from arq.worker import run_worker  # noqa: E402
run_worker(WorkerSettings)
