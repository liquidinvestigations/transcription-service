#!/bin/bash
set -e

(
        echo "starting auto-delete..."
        while true; do
                sleep 60
                python autodelete.py || true
        done
) &

set -x
echo "starting python app..."
uvicorn app:app --host 0.0.0.0 --port 8000 --server-header --date-header --timeout-graceful-shutdown 30 --no-access-log --log-level warning
