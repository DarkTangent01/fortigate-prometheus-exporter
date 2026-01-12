#!/bin/sh
set -e

echo "Starting FortiGate metrics collector..."
./automate_collector.sh &

echo "Starting Prometheus exporter..."
exec python prometheus_exporter.py