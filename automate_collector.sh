#!/bin/bash

# Path to your Python script
PYTHON_SCRIPT="./fortigate_collector.py"

# Infinite loop to run every 30 seconds
while true
do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running FortiGate interfaces Metrics Collector"
    python3 "$PYTHON_SCRIPT"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed. Waiting 30 seconds..."
    sleep 30
done