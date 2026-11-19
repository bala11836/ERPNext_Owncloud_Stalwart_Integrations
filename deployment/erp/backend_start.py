"""Resolve the Docker frontend before starting Gunicorn; fail closed on ambiguity."""
import ipaddress
import json
import os
from pathlib import Path
import socket
import time


def frontend_ip(host, network, *, attempts=30):
    allowed = ipaddress.ip_network(network)
    if allowed.version != 4:
        raise ValueError("Expected an IPv4 Docker network")
    for _ in range(attempts):
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in
                         socket.getaddrinfo(host, 8080, socket.AF_INET, socket.SOCK_STREAM)}
        except socket.gaierror:
            addresses = set()
        if addresses:
            if len(addresses) != 1 or any(address not in allowed for address in addresses):
                raise RuntimeError("Frontend DNS is ambiguous or outside its approved network")
            return str(addresses.pop())
        time.sleep(1)
    raise RuntimeError("Frontend DNS unavailable; refusing to start authentication backend")


def merge_payment_assets():
    overrides = Path('/opt/cloud-payment-assets.json')
    if not overrides.exists():
        return
    manifest = Path('/home/frappe/frappe-bench/assets/assets.json')
    assets = json.loads(manifest.read_text())
    additions = json.loads(overrides.read_text())
    assets.update(additions)
    manifest.write_text(json.dumps(assets, indent=2) + chr(10))


def main():
    merge_payment_assets()
    address = frontend_ip(os.environ["NETBIRD_AUTH_FRONTEND_DNS"],
                          os.environ["NETBIRD_AUTH_FRONTEND_NETWORK"])
    site = os.environ["NETBIRD_AUTH_SITE"]
    if Path(site).name != site or site in {".", ".."}:
        raise ValueError("Invalid site name")
    config_file = Path("/home/frappe/frappe-bench/sites") / site / "site_config.json"
    config = json.loads(config_file.read_text())
    trusted = [address + "/32"]
    if config.get("netbird_auth_trusted_proxies") != trusted:
        config["netbird_auth_trusted_proxies"] = trusted
        # Write the existing inode so bind-mounted readers see the new contents.
        config_file.write_text(json.dumps(config, indent=2) + "\n")
    environment = dict(os.environ, FORWARDED_ALLOW_IPS=address)
    print("Authentication backend trusts Docker frontend " + address + " only", flush=True)
    os.execve("/usr/local/bin/start.sh", ["start.sh"], environment)


if __name__ == "__main__":
    main()
