# FortiGate Metrics Collector & Prometheus Exporter (Dockerized)

This project provides a **Dockerized FortiGate monitoring solution** that:

* Periodically **collects metrics from multiple FortiGate firewalls**
* Stores raw data as JSON files on disk
* Exposes those metrics via a **Prometheus-compatible HTTP endpoint**
* Can be visualized easily using **Grafana**

The solution runs **two Python components inside a single container**:

1. A **collector loop** that fetches metrics at fixed intervals
2. A **Flask-based Prometheus exporter** that serves `/metrics`

---

## Architecture Overview

```
FortiGate Firewalls
        │
        │  (REST API)
        ▼
fortigate_collector.py
        │
        │  (JSON files)
        ▼
metrics/  ←── bind-mounted volume
        │
        ▼
prometheus_exporter.py  →  /metrics (HTTP)
        │
        ▼
Prometheus → Grafana
```

---

## Components

### 1. fortigate_collector.py

* Asynchronously collects metrics using **asyncio + aiohttp**
* Reads inventory from `hosts.ini`
* Automatically determines the **first reachable IP** per FortiGate
* Writes structured JSON files under the `metrics/` directory

### 2. automate_collector.sh

* Runs the collector in a **continuous loop**
* Sleeps for a configurable interval between runs
* Executed automatically when the container starts

### 3. prometheus_exporter.py

* Flask-based HTTP server
* Reads JSON files from `metrics/`
* Converts them into Prometheus metric format
* Exposes metrics at `/metrics` (default port: `8000`)

---

## Metrics Collected

* **BGP** – Peer status
* **IPsec** – Tunnel status, incoming/outgoing bytes
* **Interfaces** – Link status, RX/TX bytes, packets, errors
* **System** – CPU, memory usage
* **SD-WAN / Virtual WAN** – Link health, SLA latency/jitter/loss

---

## Directory Structure

```
fortigate-prometheus-exporter/
├── Dockerfile
├── entrypoint.sh
├── automate_collector.sh
├── docker-compose.yml
├── fortigate_collector.py
├── prometheus_exporter.py
├── requirements.txt
├── hosts.ini            # bind-mounted
├── metrics/             # bind-mounted
│   ├── BGP/
│   ├── ipsec/
│   ├── interface/
│   ├── system/
│   └── virtual-wan/
└── README.md
```

---

## Configuration

### hosts.ini

The collector reads FortiGate inventory from a bind-mounted `hosts.ini` file.

**Example:**

```ini
[fortigates]
fortigate01 fortigate_ips=192.168.1.1,192.168.1.2 fortitoken=API_TOKEN_1 ansible_httpapi_port=443
fortigate02 fortigate_ips=10.0.0.1 fortitoken=API_TOKEN_2 ansible_httpapi_port=443
```

---

## Docker Deployment (Recommended)

You can run the exporter using **Docker CLI** or **Docker Compose**.

---

### Option 1: Docker CLI

#### Build Image

```bash
docker build -t fortigate-prometheus-exporter .
```

#### Run Container

```bash
docker run -d \
  --name fortigate-exporter \
  -p 8000:8000 \
  -v $(pwd)/hosts.ini:/app/hosts.ini:ro \
  -v $(pwd)/metrics:/app/metrics \
  fortigate-prometheus-exporter
```

---

### Option 2: Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
services:
  fortigate-exporter:
    build: .
    container_name: fortigate-exporter
    ports:
      - "8000:8000"
    volumes:
      - ./hosts.ini:/app/hosts.ini:ro
      - ./metrics:/app/metrics
    restart: unless-stopped
```

#### Start Services

```bash
docker compose up -d
```

#### Rebuild After Code or Dependency Changes

```bash
docker compose up -d --build
```

#### Stop Services

```bash
docker compose down
```

---

## Prometheus Configuration

```yaml
scrape_configs:
  - job_name: fortigate
    static_configs:
      - targets:
          - <docker-host-ip>:8000
```

---

## Example Metrics

```
fortigate_ipsec_status{device="fortigate01",tunnel="Branch1"} 1
fortigate_bgp_peer_up{device="fortigate01",peer="192.0.2.1"} 1
fortigate_interface_rx_bytes{device="fortigate01",interface="port1"} 102400
fortigate_system_cpu{device="fortigate01"} 12
fortigate_virtual_wan_latency{device="fortigate01",sla="SLA1",link="ISP1"} 5
```

---

## Notes

* SSL verification is disabled for FortiGate API calls (self-signed certificates)
* Ensure REST API access is enabled on FortiGate
* Flask built-in server is sufficient for Prometheus scraping

---

## License

MIT License — free to use, modify, and extend.
