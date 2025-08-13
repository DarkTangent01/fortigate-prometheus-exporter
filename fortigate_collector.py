import asyncio
import aiohttp
import os
import json

HOSTS_FILE = "hosts.ini"
METRICS_BASE_DIR = "./metrics"
SUBDIRS = ["BGP", "ipsec", "interface", "system", "virtual-wan"]  # Added 'system' & 'virtual-wan'

# -------------------------------------------------------------------
# STEP 1: Parse hosts.ini to build FortiGate inventory
# -------------------------------------------------------------------
def parse_hosts_ini(filepath):
    fortigates = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("[") or line.startswith("#"):
                continue

            parts = line.split()
            hostname = parts[0]

            # Extract params
            params = {k: v for k, v in (p.split("=", 1) for p in parts[1:] if "=" in p)}
            ips = [ip.strip() for ip in params.get("fortigate_ips", "").split(",") if ip.strip()]
            token = params.get("fortitoken", "")
            port = int(params.get("ansible_httpapi_port", "443"))

            if ips and token:
                fortigates[hostname] = {"ips": ips, "token": token, "port": port}

    return fortigates

FORTIGATES = parse_hosts_ini(HOSTS_FILE)

# Ensure metrics directories exist
for subdir in SUBDIRS:
    os.makedirs(os.path.join(METRICS_BASE_DIR, subdir), exist_ok=True)


# -------------------------------------------------------------------
# STEP 2: API Call Helpers
# -------------------------------------------------------------------
async def check_ip(session, ip, port, token):
    """Check if FortiGate API is reachable."""
    url = f"https://{ip}:{port}/api/v2/monitor/system/status"
    try:
        async with session.get(url, headers={"Authorization": f"Bearer {token}"}, ssl=False, timeout=3) as resp:
            if resp.status == 200:
                return ip
    except Exception:
        return None
    return None


async def fetch_json(session, url, token):
    """Fetch JSON data from FortiGate API."""
    try:
        async with session.get(url, headers={"Authorization": f"Bearer {token}"}, ssl=False, timeout=5) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception:
        return {}
    return {}


# -------------------------------------------------------------------
# STEP 3: Process each FortiGate
# -------------------------------------------------------------------
async def process_fortigate(name, info):
    port = info["port"]
    token = info["token"]

    async with aiohttp.ClientSession() as session:
        # Find first reachable IP
        tasks = [check_ip(session, ip, port, token) for ip in info["ips"]]
        results = await asyncio.gather(*tasks)
        reachable_ips = [ip for ip in results if ip]

        if not reachable_ips:
            print(f"[ERROR] No reachable IP for {name}")
            return

        selected_ip = reachable_ips[0]
        print(f"[INFO] {name} → using {selected_ip}")

        # Fetch BGP
        bgp_data = await fetch_json(session, f"https://{selected_ip}:{port}/api/v2/cmdb/router/bgp", token)
        with open(f"{METRICS_BASE_DIR}/BGP/bgp_status_{name}.json", "w") as f:
            json.dump(bgp_data, f, indent=2)

        # Fetch IPsec
        ipsec_data = await fetch_json(session, f"https://{selected_ip}:{port}/api/v2/monitor/vpn/ipsec?scope=global", token)
        with open(f"{METRICS_BASE_DIR}/ipsec/ipsec_status_{name}.json", "w") as f:
            json.dump(ipsec_data, f, indent=2)

        # Fetch interface stats
        interface_data = await fetch_json(session, f"https://{selected_ip}:{port}/api/v2/monitor/system/interface", token)
        with open(f"{METRICS_BASE_DIR}/interface/interface_stats_{name}.json", "w") as f:
            json.dump(interface_data, f, indent=2)

        # Fetch system usage
        system_data = await fetch_json(session, f"https://{selected_ip}:{port}/api/v2/monitor/system/resource/usage", token)
        with open(f"{METRICS_BASE_DIR}/system/system_usage_{name}.json", "w") as f:
            json.dump(system_data, f, indent=2)

        # Fetch virtual WAN health check
        vwan_data = await fetch_json(session, f"https://{selected_ip}:{port}/api/v2/monitor/virtual-wan/health-check", token)
        with open(f"{METRICS_BASE_DIR}/virtual-wan/virtual_wan_health_{name}.json", "w") as f:
            json.dump(vwan_data, f, indent=2)


# -------------------------------------------------------------------
# STEP 4: Main Runner
# -------------------------------------------------------------------
async def main():
    tasks = [process_fortigate(name, info) for name, info in FORTIGATES.items()]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
