FROM python:3.11-slim

WORKDIR /app

# Install system deps (optional but safe)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY fortigate_collector.py .
COPY prometheus_exporter.py .
COPY automate_collector.sh .
COPY entrypoint.sh .
COPY README.md .

# Permissions
RUN chmod +x automate_collector.sh entrypoint.sh

# Create metrics directory
RUN mkdir -p /app/metrics

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]