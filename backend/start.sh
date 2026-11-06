#!/bin/bash
cd /Users/harsh/DEVPILOT/backend
export PATH="/Users/harsh/DEVPILOT/backend/venv/bin:$PATH"
source /Users/harsh/DEVPILOT/backend/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
