# FortiGate Metrics Collector & Prometheus Exporter

This project consists of two Python scripts:

1. **`fortigate_collector.py`** – Asynchronously collects metrics from multiple FortiGate devices using the REST API and stores them as JSON files.
2. **`fortigate_prometheus_exporter.py`** – Serves those collected metrics in Prometheus format via an HTTP endpoint.

This setup allows you to monitor FortiGate BGP peers, IPsec tunnels, interface stats, system usage, and SD-WAN (virtual WAN) health through Prometheus and visualize them in Grafana.

---

## Features

* **Asynchronous collection** of metrics from multiple FortiGates using `asyncio` and `aiohttp`.
* Automatically checks for the first reachable IP for each FortiGate.
* Saves metrics to separate JSON files for each device and category.
* **Prometheus exporter** converts JSON into Prometheus metrics format.
* Metrics supported:

  * **BGP Peer Status**
  * **IPsec Tunnel Status, Incoming/Outgoing Bytes**
  * **Interface Stats** (bytes, packets, errors, link status)
  * **System Usage** (CPU, memory, sessions, etc.)
  * **Virtual WAN Health** (link status, SLA metrics)

---

## Directory Structure

After running the collector, the `metrics` directory will look like this:

```
metrics/
├── BGP/
│   ├── bgp_status_device1.json
│   └── ...
├── ipsec/
│   ├── ipsec_status_device1.json
│   └── ...
├── interface/
│   ├── interface_stats_device1.json
│   └── ...
├── system/
│   ├── system_usage_device1.json
│   └── ...
└── virtual-wan/
    ├── virtual_wan_health_device1.json
    └── ...
```

---

## Requirements

* Python 3.8+
* Required packages:

  ```bash
  pip install aiohttp flask
  ```

---

## Configuration

### `hosts.ini`

The collector script uses a simple `hosts.ini` inventory format.

**Example:**

```
[fortigates]
fortigate01 fortigate_ips=192.168.1.1,192.168.1.2 fortitoken=YOUR_API_TOKEN ansible_httpapi_port=443
fortigate02 fortigate_ips=10.0.0.1 fortitoken=YOUR_API_TOKEN ansible_httpapi_port=443
```

**Fields:**

* `fortigate_ips` – Comma-separated list of IPs to try for the device.
* `fortitoken` – API access token for the FortiGate.
* `ansible_httpapi_port` – HTTPS port (default: `443`).

---

## Running the Collector

The collector fetches metrics and saves them as JSON under the `metrics/` directory.

```bash
python3 fortigate_collector.py
```

**What it does:**

1. Reads `hosts.ini` and builds inventory.
2. Finds the first reachable IP for each FortiGate.
3. Fetches:

   * **BGP peers**: `/api/v2/cmdb/router/bgp`
   * **IPsec tunnels**: `/api/v2/monitor/vpn/ipsec`
   * **Interface stats**: `/api/v2/monitor/system/interface`
   * **System usage**: `/api/v2/monitor/system/resource/usage`
   * **Virtual WAN health**: `/api/v2/monitor/virtual-wan/health-check`
4. Saves data into JSON files grouped by category.

---

## Running the Prometheus Exporter

Once JSON files are available, start the exporter:

```bash
python3 fortigate_prometheus_exporter.py
```

By default, the exporter runs at:

```
http://0.0.0.0:8000/metrics
```

This endpoint can be scraped by Prometheus.

---

## Prometheus Configuration

Add the exporter to your Prometheus `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'fortigate'
    static_configs:
      - targets: ['<exporter_host>:8000']
```

Reload Prometheus after updating the configuration.

---

## Example Metrics

### IPsec

```
fortigate_ipsec_status{device="fortigate01",tunnel="Branch1"} 1
fortigate_ipsec_in_bytes{device="fortigate01",tunnel="Branch1"} 123456
fortigate_ipsec_out_bytes{device="fortigate01",tunnel="Branch1"} 654321
```

### BGP

```
fortigate_bgp_peer_up{device="fortigate01",peer="192.0.2.1"} 1
```

### Interface

```
fortigate_interface_link_up{device="fortigate01",interface="port1",alias="WAN1",mac="00:11:22:33:44:55",ip="192.168.1.1/24"} 1
fortigate_interface_rx_bytes{device="fortigate01",interface="port1",alias="WAN1",mac="00:11:22:33:44:55",ip="192.168.1.1/24"} 102400
```

### System

```
fortigate_system_cpu{device="fortigate01"} 12
fortigate_system_memory{device="fortigate01"} 45
```

### Virtual WAN

```
fortigate_virtual_wan_status{device="fortigate01",sla="SLA1",link="ISP1"} 1
fortigate_virtual_wan_latency{device="fortigate01",sla="SLA1",link="ISP1"} 5
```

---

## CI/CD Deployment

You can automate metric collection & exporter updates using systemd or a CI/CD pipeline.

**Example systemd service for collector:**

```ini
[Unit]
Description=FortiGate Metrics Collector
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/fortigate_collector.py
WorkingDirectory=/path/to/
Restart=always

[Install]
WantedBy=multi-user.target
```

**Example systemd timer (every 1 minute):**

```ini
[Unit]
Description=Run FortiGate Collector every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=60s
Unit=fortigate_collector.service

[Install]
WantedBy=timers.target
```

---

## Notes

* This script disables SSL verification for FortiGate connections (due to self-signed certs). Use caution in production.
* Ensure FortiGate API access and firewall policies allow the requests.
* JSON structure is directly based on FortiGate API responses—if FortiOS changes, metric parsing may need updates.

---

## License

MIT License – feel free to modify and use.
