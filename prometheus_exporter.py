import os
import json
from flask import Flask, Response

app = Flask(__name__)
BASE_DIR = "metrics"

@app.route("/metrics")
def metrics():
    metric_lines = []

    # ------------------------
    # IPsec tunnel metrics
    # ------------------------
    ipsec_dir = os.path.join(BASE_DIR, "ipsec")
    if os.path.isdir(ipsec_dir):
        for filename in os.listdir(ipsec_dir):
            if filename.startswith("ipsec_status_") and filename.endswith(".json"):
                device = filename.replace("ipsec_status_", "").replace(".json", "")
                filepath = os.path.join(ipsec_dir, filename)
                try:
                    with open(filepath) as f:
                        ipsec_data = json.load(f)

                    for tunnel in ipsec_data.get("results", []):
                        name = tunnel.get("name", "unknown")
                        proxyids = tunnel.get("proxyid", [])
                        status = proxyids[0].get("status", "down") if proxyids else "down"
                        incoming = tunnel.get("incoming_bytes", 0)
                        outgoing = tunnel.get("outgoing_bytes", 0)

                        metric_lines.append(f'fortigate_ipsec_status{{device="{device}",tunnel="{name}"}} {1 if status == "up" else 0}')
                        metric_lines.append(f'fortigate_ipsec_in_bytes{{device="{device}",tunnel="{name}"}} {incoming}')
                        metric_lines.append(f'fortigate_ipsec_out_bytes{{device="{device}",tunnel="{name}"}} {outgoing}')
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")

    # ------------------------
    # BGP peer metrics
    # ------------------------
    bgp_dir = os.path.join(BASE_DIR, "BGP")
    if os.path.isdir(bgp_dir):
        for filename in os.listdir(bgp_dir):
            if filename.startswith("bgp_status_") and filename.endswith(".json"):
                device = filename.replace("bgp_status_", "").replace(".json", "")
                filepath = os.path.join(bgp_dir, filename)
                try:
                    with open(filepath) as f:
                        bgp_data = json.load(f)

                    for peer in bgp_data.get("results", {}).get("peers", []):
                        ip = peer.get("ip", "unknown")
                        state = peer.get("state", "").lower()
                        metric_lines.append(f'fortigate_bgp_peer_up{{device="{device}",peer="{ip}"}} {1 if state == "established" else 0}')
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")

    # ------------------------
    # Interface stats
    # ------------------------
    interface_dir = os.path.join(BASE_DIR, "interface")
    if os.path.isdir(interface_dir):
        for filename in os.listdir(interface_dir):
            if filename.startswith("interface_stats_") and filename.endswith(".json"):
                device = filename.replace("interface_stats_", "").replace(".json", "")
                filepath = os.path.join(interface_dir, filename)
                try:
                    with open(filepath) as f:
                        interface_data = json.load(f)

                    for ifname, stats in interface_data.get("results", {}).items():
                        alias = stats.get("alias", "")
                        mac = stats.get("mac", "")
                        ip = stats.get("ip", "")
                        mask = stats.get("mask", 0)

                        rx_bytes = stats.get("rx_bytes", 0)
                        tx_bytes = stats.get("tx_bytes", 0)
                        rx_packets = stats.get("rx_packets", 0)
                        tx_packets = stats.get("tx_packets", 0)
                        rx_errors = stats.get("rx_errors", 0)
                        tx_errors = stats.get("tx_errors", 0)
                        link_status = 1 if stats.get("link") else 0

                        labels = f'device="{device}",interface="{ifname}",alias="{alias}",mac="{mac}",ip="{ip}/{mask}"'

                        metric_lines.append(f'fortigate_interface_link_up{{{labels}}} {link_status}')
                        metric_lines.append(f'fortigate_interface_rx_bytes{{{labels}}} {rx_bytes}')
                        metric_lines.append(f'fortigate_interface_tx_bytes{{{labels}}} {tx_bytes}')
                        metric_lines.append(f'fortigate_interface_rx_packets{{{labels}}} {rx_packets}')
                        metric_lines.append(f'fortigate_interface_tx_packets{{{labels}}} {tx_packets}')
                        metric_lines.append(f'fortigate_interface_rx_errors{{{labels}}} {rx_errors}')
                        metric_lines.append(f'fortigate_interface_tx_errors{{{labels}}} {tx_errors}')
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")

    # ------------------------
    # System usage stats
    # ------------------------
    system_dir = os.path.join(BASE_DIR, "system")
    if os.path.isdir(system_dir):
        for filename in os.listdir(system_dir):
            if filename.startswith("system_usage_") and filename.endswith(".json"):
                device = filename.replace("system_usage_", "").replace(".json", "")
                filepath = os.path.join(system_dir, filename)
                try:
                    with open(filepath) as f:
                        sys_data = json.load(f)

                    results = sys_data.get("results", {})
                    for key, value in results.items():
                        # Export all numeric values from system metrics
                        if isinstance(value, (int, float)):
                            metric_lines.append(f'fortigate_system_{key}{{device="{device}"}} {value}')
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")

    # ------------------------
    # Virtual-WAN health stats (all metrics)
    # ------------------------
    vwan_dir = os.path.join(BASE_DIR, "virtual-wan")
    if os.path.isdir(vwan_dir):
        for filename in os.listdir(vwan_dir):
            if filename.startswith("virtual_wan_health_") and filename.endswith(".json"):
                device = filename.replace("virtual_wan_health_", "").replace(".json", "")
                filepath = os.path.join(vwan_dir, filename)
                try:
                    with open(filepath) as f:
                        vwan_data = json.load(f)

                    results = vwan_data.get("results", {})
                    # results = { "SLA_NAME": { "link": { "metric": value, ...}, ... }, ... }
                    for sla_name, links in results.items():
                        if isinstance(links, dict):
                            for link_name, link_stats in links.items():
                                # Export status as 1/0
                                status = link_stats.get("status", "down").lower()
                                metric_lines.append(
                                    f'fortigate_virtual_wan_status{{device="{device}",sla="{sla_name}",link="{link_name}"}} {1 if status == "up" else 0}'
                                )
                                # Export other numeric metrics
                                for metric, value in link_stats.items():
                                    if metric != "status" and isinstance(value, (int, float)):
                                        metric_lines.append(
                                            f'fortigate_virtual_wan_{metric}{{device="{device}",sla="{sla_name}",link="{link_name}"}} {value}'
                                        )
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")

    return Response("\n".join(metric_lines), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
