import os
import json
from flask import Flask, Response

app = Flask(__name__)
BASE_DIR = "metrics"

declared_metrics = set()


def declare(lines, name, mtype, help_text):
    if name not in declared_metrics:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {mtype}")
        declared_metrics.add(name)


@app.route("/metrics")
def metrics():
    metric_lines = []
    declared_metrics.clear()

    # =====================================================
    # IPsec Metrics
    # =====================================================
    declare(metric_lines, "fortigate_ipsec_status", "gauge", "IPsec tunnel up/down status")
    declare(metric_lines, "fortigate_ipsec_in_bytes", "counter", "IPsec incoming bytes")
    declare(metric_lines, "fortigate_ipsec_out_bytes", "counter", "IPsec outgoing bytes")

    ipsec_dir = os.path.join(BASE_DIR, "ipsec")
    if os.path.isdir(ipsec_dir):
        for fn in os.listdir(ipsec_dir):
            if fn.startswith("ipsec_status_") and fn.endswith(".json"):
                device = fn.replace("ipsec_status_", "").replace(".json", "")
                try:
                    data = json.load(open(os.path.join(ipsec_dir, fn)))
                    for t in data.get("results", []):
                        name = t.get("name", "unknown")
                        proxy = t.get("proxyid", [])
                        up = 1 if proxy and proxy[0].get("status") == "up" else 0
                        metric_lines.append(f'fortigate_ipsec_status{{device="{device}",tunnel="{name}"}} {up}')
                        metric_lines.append(f'fortigate_ipsec_in_bytes{{device="{device}",tunnel="{name}"}} {t.get("incoming_bytes",0)}')
                        metric_lines.append(f'fortigate_ipsec_out_bytes{{device="{device}",tunnel="{name}"}} {t.get("outgoing_bytes",0)}')
                except Exception as e:
                    print(f"[IPSEC ERROR] {e}")

    # =====================================================
    # BGP Metrics (FIXED – supports FortiGate variants)
    # =====================================================
    declare(metric_lines, "fortigate_bgp_peer_up", "gauge", "BGP peer established state")

    bgp_dir = os.path.join(BASE_DIR, "BGP")
    if os.path.isdir(bgp_dir):
        for fn in os.listdir(bgp_dir):
            if fn.startswith("bgp_status_") and fn.endswith(".json"):
                device = fn.replace("bgp_status_", "").replace(".json", "")
                try:
                    data = json.load(open(os.path.join(bgp_dir, fn)))
                    results = data.get("results", [])

                    if isinstance(results, list):
                        for peer in results:
                            ip = peer.get("neighbor") or peer.get("ip") or "unknown"
                            state = peer.get("state", "").lower()
                            metric_lines.append(
                                f'fortigate_bgp_peer_up{{device="{device}",peer="{ip}"}} {1 if state=="established" else 0}'
                            )

                    elif isinstance(results, dict):
                        for ip, peer in results.get("peers", {}).items():
                            state = peer.get("state", "").lower()
                            metric_lines.append(
                                f'fortigate_bgp_peer_up{{device="{device}",peer="{ip}"}} {1 if state=="established" else 0}'
                            )
                except Exception as e:
                    print(f"[BGP ERROR] {e}")

    # =====================================================
    # Interface Metrics
    # =====================================================
    declare(metric_lines, "fortigate_interface_link_up", "gauge", "Interface link status")
    declare(metric_lines, "fortigate_interface_rx_bytes", "counter", "Interface RX bytes")
    declare(metric_lines, "fortigate_interface_tx_bytes", "counter", "Interface TX bytes")
    declare(metric_lines, "fortigate_interface_rx_packets", "counter", "Interface RX packets")
    declare(metric_lines, "fortigate_interface_tx_packets", "counter", "Interface TX packets")
    declare(metric_lines, "fortigate_interface_rx_errors", "counter", "Interface RX errors")
    declare(metric_lines, "fortigate_interface_tx_errors", "counter", "Interface TX errors")

    iface_dir = os.path.join(BASE_DIR, "interface")
    if os.path.isdir(iface_dir):
        for fn in os.listdir(iface_dir):
            if fn.startswith("interface_stats_") and fn.endswith(".json"):
                device = fn.replace("interface_stats_", "").replace(".json", "")
                try:
                    data = json.load(open(os.path.join(iface_dir, fn)))
                    for ifname, s in data.get("results", {}).items():
                        labels = (
                            f'device="{device}",interface="{ifname}",'
                            f'alias="{s.get("alias","")}",'
                            f'mac="{s.get("mac","")}",'
                            f'ip="{s.get("ip","")}/{s.get("mask",0)}"'
                        )
                        metric_lines.append(f'fortigate_interface_link_up{{{labels}}} {1 if s.get("link") else 0}')
                        metric_lines.append(f'fortigate_interface_rx_bytes{{{labels}}} {s.get("rx_bytes",0)}')
                        metric_lines.append(f'fortigate_interface_tx_bytes{{{labels}}} {s.get("tx_bytes",0)}')
                        metric_lines.append(f'fortigate_interface_rx_packets{{{labels}}} {s.get("rx_packets",0)}')
                        metric_lines.append(f'fortigate_interface_tx_packets{{{labels}}} {s.get("tx_packets",0)}')
                        metric_lines.append(f'fortigate_interface_rx_errors{{{labels}}} {s.get("rx_errors",0)}')
                        metric_lines.append(f'fortigate_interface_tx_errors{{{labels}}} {s.get("tx_errors",0)}')
                except Exception as e:
                    print(f"[INTERFACE ERROR] {e}")

    # =====================================================
    # System Metrics (FIXED)
    # =====================================================
    system_dir = os.path.join(BASE_DIR, "system")
    if os.path.isdir(system_dir):
        for fn in os.listdir(system_dir):
            if fn.startswith("system_usage_") and fn.endswith(".json"):
                device = fn.replace("system_usage_", "").replace(".json", "")
                try:
                    data = json.load(open(os.path.join(system_dir, fn)))
                    for key, val in data.get("results", {}).items():
                        if isinstance(val, (int, float)):
                            metric = f"fortigate_system_{key}"
                            declare(metric_lines, metric, "gauge", f"System metric {key}")
                            metric_lines.append(f'{metric}{{device="{device}"}} {val}')

                        elif isinstance(val, list):
                            for idx, item in enumerate(val):
                                for k, v in item.items():
                                    if isinstance(v, (int, float)):
                                        metric = f"fortigate_system_{key}_{k}"
                                        declare(metric_lines, metric, "gauge", f"System metric {key} {k}")
                                        metric_lines.append(
                                            f'{metric}{{device="{device}",cpu="{idx}"}} {v}'
                                        )
                except Exception as e:
                    print(f"[SYSTEM ERROR] {e}")

    # =====================================================
    # SD-WAN Metrics
    # =====================================================
    declare(metric_lines, "fortigate_virtual_wan_status", "gauge", "SD-WAN link status")
    declare(metric_lines, "fortigate_virtual_wan_latency", "gauge", "SD-WAN latency ms")
    declare(metric_lines, "fortigate_virtual_wan_jitter", "gauge", "SD-WAN jitter ms")
    declare(metric_lines, "fortigate_virtual_wan_packet_loss", "gauge", "SD-WAN packet loss percent")
    declare(metric_lines, "fortigate_virtual_wan_packet_sent", "counter", "SD-WAN packets sent")
    declare(metric_lines, "fortigate_virtual_wan_packet_received", "counter", "SD-WAN packets received")

    vwan_dir = os.path.join(BASE_DIR, "virtual-wan")
    if os.path.isdir(vwan_dir):
        for fn in os.listdir(vwan_dir):
            if fn.startswith("virtual_wan_health_") and fn.endswith(".json"):
                device = fn.replace("virtual_wan_health_", "").replace(".json", "")
                try:
                    data = json.load(open(os.path.join(vwan_dir, fn)))
                    for sla, links in data.get("results", {}).items():
                        for link, stats in links.items():
                            up = 1 if stats.get("status") == "up" else 0
                            metric_lines.append(
                                f'fortigate_virtual_wan_status{{device="{device}",sla="{sla}",link="{link}"}} {up}'
                            )
                            for k, v in stats.items():
                                if k != "status" and isinstance(v, (int, float)):
                                    metric_lines.append(
                                        f'fortigate_virtual_wan_{k}{{device="{device}",sla="{sla}",link="{link}"}} {v}'
                                    )
                except Exception as e:
                    print(f"[SD-WAN ERROR] {e}")

    return Response("\n".join(metric_lines) + "\n", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)