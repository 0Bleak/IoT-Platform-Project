import time
import csv
import argparse
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("WARNING: psutil not available, using dummy CPU load (install: sudo apt install python3-psutil)")


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
    return 25.0  # fallback


def run_loop(period_ms: float, duration_s: float, epsilon_ms: float, out_csv: Path) -> None:
    period_ns = int(period_ms * 1e6)
    epsilon_ns = int(epsilon_ms * 1e6)

    # Adaptive parameters
    NORMAL_WORKLOAD = 0.7
    DEGRADED_WORKLOAD = 0.3
    CPU_HIGH_THRESHOLD = 70.0
    CPU_LOW_THRESHOLD = 40.0

    mode = "NORMAL"
    workload_ratio = NORMAL_WORKLOAD

    # Initialize psutil (first call is meaningless, it needs a reference point)
    if HAS_PSUTIL:
        psutil.cpu_percent(interval=None)

    start_ns = time.monotonic_ns()
    prev_ns = start_ns
    next_deadline_ns = start_ns + period_ns

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "iter",
            "t_ns",
            "dt_ns",
            "jitter_ns",
            "miss",
            "workload_ratio",
            "cpu_load",
            "mode"
        ])

        it = 0
        end_ns = start_ns + int(duration_s * 1e9)

        while True:
            now_ns = time.monotonic_ns()
            if now_ns >= end_ns:
                break

            # --- Read CPU load and adapt ---
            cpu_load = get_cpu_load()

            if cpu_load > CPU_HIGH_THRESHOLD:
                mode = "DEGRADED"
            elif cpu_load < CPU_LOW_THRESHOLD:
                mode = "NORMAL"
            # else: keep current mode (hysteresis)

            if mode == "NORMAL":
                workload_ratio = NORMAL_WORKLOAD
            else:
                workload_ratio = DEGRADED_WORKLOAD

            # --- Simulated workload ---
            work_s = (period_ms / 1000.0) * workload_ratio
            if work_s > 0:
                busy_wait(work_s)

            # --- Measurement ---
            t_ns = time.monotonic_ns()
            dt_ns = t_ns - prev_ns
            jitter_ns = abs(dt_ns - period_ns)
            miss = 1 if dt_ns > (period_ns + epsilon_ns) else 0

            w.writerow([it, t_ns, dt_ns, jitter_ns, miss, workload_ratio, cpu_load, mode])

            # --- Sleep until next deadline ---
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
                    pass  # spin-wait for final precision


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period-ms", type=float, default=20.0)
    p.add_argument("--duration-s", type=float, default=120.0)
    p.add_argument("--epsilon-ms", type=float, default=2.0)
    p.add_argument("--out", type=str, default="logs/rt_adaptive_nominal.csv")
    args = p.parse_args()

    run_loop(
        period_ms=args.period_ms,
        duration_s=args.duration_s,
        epsilon_ms=args.epsilon_ms,
        out_csv=Path(args.out),
    )


if __name__ == "__main__":
    main()