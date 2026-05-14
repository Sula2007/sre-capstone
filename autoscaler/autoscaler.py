"""
Autoscaler for Shop Catalog backend (Docker Compose).

Polls Prometheus every 30s, scales the backend service up/down
based on current RPS. Uses `docker compose up --scale` to adjust replicas.
"""

import subprocess
import time
import requests

PROMETHEUS_URL = "http://localhost:9090"
COMPOSE_FILE = "../app/docker-compose.yml"
SERVICE = "backend"

MIN_REPLICAS = 1
MAX_REPLICAS = 5
SCALE_UP_RPS = 15    # add a replica when RPS exceeds this
SCALE_DOWN_RPS = 5   # remove a replica when RPS drops below this
POLL_INTERVAL = 30   # seconds between checks

current_replicas = 1


def get_rps() -> float:
    """Query Prometheus for current request rate (last 1 minute)."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "sum(rate(http_requests_total[1m]))"},
            timeout=5,
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
    except Exception as e:
        print(f"[autoscaler] Prometheus query failed: {e}")
    return 0.0


def scale(replicas: int) -> None:
    """Scale the Docker Compose service to the given number of replicas."""
    cmd = [
        "docker", "compose",
        "-f", COMPOSE_FILE,
        "up", "-d", "--scale", f"{SERVICE}={replicas}",
        "--no-recreate",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[autoscaler] Scaled {SERVICE} to {replicas} replica(s)")
    else:
        print(f"[autoscaler] Scale command failed: {result.stderr.strip()}")


def main() -> None:
    global current_replicas
    print(f"[autoscaler] Started. Polling Prometheus at {PROMETHEUS_URL} every {POLL_INTERVAL}s")

    while True:
        rps = get_rps()
        print(f"[autoscaler] RPS={rps:.2f}  replicas={current_replicas}")

        if rps > SCALE_UP_RPS and current_replicas < MAX_REPLICAS:
            current_replicas += 1
            scale(current_replicas)

        elif rps < SCALE_DOWN_RPS and current_replicas > MIN_REPLICAS:
            current_replicas -= 1
            scale(current_replicas)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
