import time
import csv
import argparse
from pathlib import Path

def busy_wait(duration_s: float) -> None:
    """Occupe le CPU pendant duration_s (approx) sans sleep."""
    end = time.perf_counter() + duration_s
    x = 0
    while time.perf_counter() < end:
        x += 1  # opération inutile, juste pour occuper
    # éviter optimisation (symbolique)
    if x < 0:
        print(x)

def run_loop(period_ms: float, duration_s: float, epsilon_ms: float, workload_ratio: float, out_csv: Path) -> None:
    period_ns = int(period_ms * 1e6)
    epsilon_ns = int(epsilon_ms * 1e6)

    start_ns = time.monotonic_ns()
    prev_ns = start_ns
    next_deadline_ns = start_ns + period_ns

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        # colonnes minimales + quelques utiles
        w.writerow([
            "iter",
            "t_ns",
            "dt_ns",
            "jitter_ns",
            "miss",
            "workload_ratio"
        ])

        it = 0
        end_ns = start_ns + int(duration_s * 1e9)

        while True:
            now_ns = time.monotonic_ns()
            if now_ns >= end_ns:
                break

            # --- travail simulé (occup. CPU) : workload_ratio du budget de période ---
            # ex: 0.3 => ~6ms de CPU sur 20ms
            work_s = (period_ms / 1000.0) * workload_ratio
            if work_s > 0:
                busy_wait(work_s)

            # --- mesure ---
            t_ns = time.monotonic_ns()
            dt_ns = t_ns - prev_ns
            jitter_ns = abs(dt_ns - period_ns)
            miss = 1 if dt_ns > (period_ns + epsilon_ns) else 0

            w.writerow([it, t_ns, dt_ns, jitter_ns, miss, workload_ratio])

            # --- ordonnanceur : dormir jusqu’à la prochaine deadline ---
            # Stratégie : "sleep le gros, busy-wait la fin" pour réduire l’oversleep
            prev_ns = t_ns
            it += 1

            next_deadline_ns += period_ns
            while True:
                now_ns = time.monotonic_ns()
                remaining_ns = next_deadline_ns - now_ns
                if remaining_ns <= 0:
                    break
                # dormir tant qu'il reste > 1ms
                if remaining_ns > 1_000_000:
                    time.sleep((remaining_ns - 500_000) / 1e9)  # garde une marge
                else:
                    # fin en spin pour éviter l'imprécision de sleep
                    pass

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period-ms", type=float, default=20.0)
    p.add_argument("--duration-s", type=float, default=120.0)
    p.add_argument("--epsilon-ms", type=float, default=2.0)
    p.add_argument("--workload-ratio", type=float, default=0.2)  # 20% de CPU sur la période
    p.add_argument("--out", type=str, default="logs/rt_nominal.csv")
    args = p.parse_args()

    run_loop(
        period_ms=args.period_ms,
        duration_s=args.duration_s,
        epsilon_ms=args.epsilon_ms,
        workload_ratio=args.workload_ratio,
        out_csv=Path(args.out),
    )

if __name__ == "__main__":
    main()
