import time
import csv
import json
import argparse
from pathlib import Path
from collections import deque

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("WARNING: psutil not available")

import paho.mqtt.client as mqtt

# ─── MQTT Configuration ───
IP_GATEWAY = "192.168.1.1"  # CHANGE THIS to your gateway IP
MQTT_PORT = 1883
TOPIC_METRICS = "tp/device1/metrics"
TOPIC_CMD = "tp/device1/cmd"
PUBLISH_INTERVAL = 0.2  # 200 ms


def busy_wait(duration_s: float) -> None:
    end = time.perf_counter() + duration_s
    x = 0
    while time.perf_counter() < end:
        x += 1
    if x < 0:
        print(x)


def get_cpu_load():
    if HAS_PSUTIL:
        return psutil.cpu_percent(interval=None)
    return 25.0


def run_loop(period_ms: float, duration_s: float, epsilon_ms: float,
             out_csv: Path, gateway_ip: str) -> None:
    global IP_GATEWAY
    IP_GATEWAY = gateway_ip

    period_ns = int(period_ms * 1e6)
    epsilon_ns = int(epsilon_ms * 1e6)

    # Adaptive parameters
    NORMAL_WORKLOAD = 0.7
    DEGRADED_WORKLOAD = 0.3
    CPU_HIGH_THRESHOLD = 70.0
    CPU_LOW_THRESHOLD = 40.0

    mode = "NORMAL"
    workload_ratio = NORMAL_WORKLOAD

    # ─── Rolling statistics for MQTT publishing ───
    jitter_window = deque(maxlen=10)  # last 10 iterations for metrics
    miss_window = deque(maxlen=10)

    # ─── MQTT Setup ───
    def on_connect(client, userdata, flags, rc):
        print(f"MQTT connected (rc={rc})")
        client.subscribe(TOPIC_CMD)

    def on_message(client, userdata, msg):
        nonlocal mode
        try:
            payload = json.loads(msg.payload.decode())
            if "Mode" in payload:
                new_mode = payload["Mode"]
                if new_mode in ("NORMAL", "DEGRADED"):
                    mode = new_mode
                    print(f"Mode updated via MQTT: {mode}")
        except Exception as e:
            print(f"Invalid command received: {e}")

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(IP_GATEWAY, MQTT_PORT, 60)
        mqtt_client.loop_start()
        mqtt_connected = True
        print(f"MQTT connecting to {IP_GATEWAY}:{MQTT_PORT}")
    except Exception as e:
        print(f"MQTT connection failed: {e}. Running without MQTT.")
        mqtt_connected = False

    # Initialize psutil
    if HAS_PSUTIL:
        psutil.cpu_percent(interval=None)

    start_ns = time.monotonic_ns()
    prev_ns = start_ns
    next_deadline_ns = start_ns + period_ns

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    last_pub = time.perf_counter()

    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "iter", "t_ns", "dt_ns", "jitter_ns", "miss",
            "workload_ratio", "cpu_load", "mode"
        ])

        it = 0
        end_ns = start_ns + int(duration_s * 1e9)

        while True:
            now_ns = time.monotonic_ns()
            if now_ns >= end_ns:
                break

            # ─── CPU load & adaptation ───
            cpu_load = get_cpu_load()

            # Only auto-adapt if not overridden by MQTT command
            # (here we let MQTT override take priority via on_message)
            if cpu_load > CPU_HIGH_THRESHOLD:
                mode = "DEGRADED"
            elif cpu_load < CPU_LOW_THRESHOLD:
                mode = "NORMAL"

            if mode == "NORMAL":
                workload_ratio = NORMAL_WORKLOAD
            else:
                workload_ratio = DEGRADED_WORKLOAD

            # ─── Simulated workload ───
            work_s = (period_ms / 1000.0) * workload_ratio
            if work_s > 0:
                busy_wait(work_s)

            # ─── Measurement ───
            t_ns = time.monotonic_ns()
            dt_ns = t_ns - prev_ns
            jitter_ns = abs(dt_ns - period_ns)
            miss = 1 if dt_ns > (period_ns + epsilon_ns) else 0

            w.writerow([it, t_ns, dt_ns, jitter_ns, miss,
                        workload_ratio, cpu_load, mode])

            jitter_window.append(jitter_ns)
            miss_window.append(miss)

            # ─── MQTT publish (slow path, non-blocking, every 200 ms) ───
            now_pub = time.perf_counter()
            if mqtt_connected and (now_pub - last_pub >= PUBLISH_INTERVAL):
                try:
                    jitter_mean = sum(jitter_window) / len(jitter_window) / 1e6 if jitter_window else 0
                    jitter_max = max(jitter_window) / 1e6 if jitter_window else 0
                    miss_rate = sum(miss_window) / len(miss_window) * 100 if miss_window else 0

                    payload = {
                        "timestamp": time.time(),
                        "mode": mode,
                        "jitter_mean": round(jitter_mean, 3),
                        "jitter_max": round(jitter_max, 3),
                        "miss_rate": round(miss_rate, 2),
                        "workload": workload_ratio,
                        "cpu_load": round(cpu_load, 1)
                    }
                    mqtt_client.publish(TOPIC_METRICS, json.dumps(payload))
                except Exception:
                    pass  # never let MQTT errors affect the critical loop
                last_pub = now_pub

            # ─── Sleep until next deadline ───
            prev_ns = t_ns
            it += 1
            next_deadline_ns += period_ns

            while True:
                now_ns = time.monotonic_ns()
                remaining_ns = next_deadline_ns - now_ns
                if remaining_ns <= 0:
                    break
                if remaining_ns > 1_000_000:
                    time.sleep((remaining_ns - 500_000) / 1e9)
                else:
                    pass

    # Cleanup
    if mqtt_connected:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print(f"Done. {it} iterations logged to {out_csv}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period-ms", type=float, default=20.0)
    p.add_argument("--duration-s", type=float, default=120.0)
    p.add_argument("--epsilon-ms", type=float, default=2.0)
    p.add_argument("--out", type=str, default="logs/rt_G_mqtt.csv")
    p.add_argument("--gateway-ip", type=str, default="192.168.1.1",
                    help="IP address of the MQTT broker / gateway")
    args = p.parse_args()

    run_loop(
        period_ms=args.period_ms,
        duration_s=args.duration_s,
        epsilon_ms=args.epsilon_ms,
        out_csv=Path(args.out),
        gateway_ip=args.gateway_ip,
    )


if __name__ == "__main__":
    main()