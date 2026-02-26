# PART 1 — Comprendre le comportement temporel d'un système sous Linux

## Exercice 1 — Compréhension conceptuelle

**1. Différence entre hard et soft real-time:**

In a hard real-time system, missing a deadline constitutes a system failure — the result becomes valueless or dangerous (e.g., airbag deployment). In a soft real-time system, missing a deadline degrades quality but does not cause catastrophic failure (e.g., a dropped video frame). The distinction is about the consequence of a missed deadline, not about speed.

**2. Pourquoi Linux standard n'est pas hard real-time:**

Linux's scheduler (CFS — Completely Fair Scheduler) optimizes for global throughput and fairness across all processes, not for bounded worst-case latency. The kernel can preempt user tasks for interrupts, housekeeping (memory reclaim, RCU callbacks), and other kernel work at unpredictable times. There is no formal guarantee on maximum latency — you cannot prove an upper bound on response time. Additionally, `sleep()` relies on the kernel's timer subsystem which has granularity limitations and can oversleep due to scheduling delays.

**3. Un système peut-il être rapide sans être temps réel ?**

Yes. Speed and real-time are orthogonal concepts. A modern desktop CPU executing a task in microseconds on average can still occasionally stall for milliseconds due to interrupts, page faults, or scheduler decisions. A system is real-time not because it is fast, but because it provides deterministic timing guarantees. Conversely, a slow system (e.g., 100 ms period) can be hard real-time if it provably never exceeds its deadline.

---

## 5.2 — Lecture du code `rt_loop.py`

**Où est définie la période cible ?** `period_ns = int(period_ms * 1e6)` — derived from the `--period-ms` argument (default 20 ms).

**Où est mesuré le temps courant ?** `now_ns = time.monotonic_ns()` at the top of the main loop, and `t_ns = time.monotonic_ns()` after the busy-wait workload.

**Où est calculé le jitter ?** `jitter_ns = abs(dt_ns - period_ns)` — the absolute deviation of the measured inter-iteration interval from the target period.

**Comment est détectée une deadline manquée ?** `miss = 1 if dt_ns > (period_ns + epsilon_ns) else 0` — a miss occurs when the actual period exceeds the target plus the tolerance (epsilon).

**Pourquoi `time.monotonic_ns()` ?** It is a monotonically increasing clock that cannot go backward. It is immune to NTP adjustments, manual clock changes, or leap seconds. It measures elapsed time reliably.

**Pourquoi pas `time.time()` ?** `time.time()` returns wall-clock time which can jump forward or backward due to NTP synchronization or system clock adjustments. This would introduce artificial jitter artifacts in measurements. It is unsuitable for measuring precise time intervals.

---

## Exercice 2 — Interprétation initiale

**1. Comparez la moyenne et le maximum du jitter:**

In a nominal run (no external stress), the mean jitter is typically sub-millisecond (e.g., 0.05–0.3 ms), while the maximum can spike to several milliseconds (e.g., 1–5 ms). The maximum can be 10–100x the mean. This disparity is characteristic of non-deterministic systems.

**2. Pourquoi la moyenne seule est insuffisante ?**

The mean masks rare but large deviations. A mean jitter of 0.1 ms with a maximum of 8 ms tells a very different story than a mean of 0.1 ms with a maximum of 0.2 ms. In real-time analysis, the distribution tail (p99, p99.9, max) matters more than the central tendency because a single worst-case event can cause system failure.

**3. Dans un système de contrôle moteur, lequel est le plus critique ?**

The maximum. A motor control loop that must execute every 5 ms cannot tolerate even a single 15 ms gap — the physical system does not care about statistical averages. One missed deadline can cause overshoot, oscillation, or physical damage. Hard real-time analysis is fundamentally worst-case analysis (WCET — Worst Case Execution Time).

---

## Exercice 3 — Relier au scheduler

**1. Qui décide quel processus s'exécute ?**

The Linux kernel scheduler (CFS for SCHED_OTHER, or the RT scheduler for SCHED_FIFO/SCHED_RR). It runs in kernel space and preempts user processes based on fairness metrics, priorities, and time-slice expiration.

**2. Pourquoi votre programme ne peut-il pas "réserver" le CPU ?**

Under standard Linux with SCHED_OTHER policy, processes share CPU time equitably. The kernel retains the right to preempt any user process for interrupt handling, kernel threads (kworker, ksoftirqd), and other system tasks. Even with elevated priority, hardware interrupts and certain kernel paths remain non-preemptible. True CPU reservation requires kernel-level mechanisms (isolcpus, SCHED_DEADLINE, or an RTOS).

**3. Si vous doublez la puissance du processeur, le problème disparaît-il ?**

No. Doubling CPU speed reduces average execution time but does not eliminate non-determinism. The sources of jitter — interrupts, scheduler preemption, cache effects, memory management — are structural, not computational. A faster CPU may reduce the magnitude of jitter but cannot bound it. The problem is architectural, not one of raw performance.

---

## Exercice 4 — Analyse de la priorité

**1. Comparaison avec et sans `nice -n -10`:**

With `nice -n -10`, the process receives a higher scheduling weight within CFS. Under CPU stress, it gets a larger share of CPU time and is rescheduled more quickly after preemption. The jitter distribution shifts left — more iterations complete closer to the target period.

**2. La priorité améliore-t-elle le jitter moyen ?**

Yes, typically. The mean jitter decreases because the process is scheduled more frequently and spends less time waiting in the run queue. The improvement is noticeable under load.

**3. Améliore-t-elle le jitter maximal ?**

Partially. The worst-case jitter may decrease somewhat, but large spikes can still occur. Hardware interrupts, kernel-level preemption, and non-preemptible kernel sections are unaffected by `nice`. The tail of the distribution improves less than the mean.

**4. Peut-on garantir une borne ?**

No. `nice` adjusts relative priority within the CFS fair-sharing model. It does not provide deterministic guarantees. To approach bounded latency, one would need SCHED_FIFO with `chrt`, CPU isolation via `isolcpus`, and ideally the PREEMPT_RT kernel patch. Even then, Linux cannot formally guarantee hard real-time bounds without rigorous WCET analysis.

---

## Exercice 5 — Comprendre l'affinité

**1. Pourquoi le cache CPU peut-il influencer le jitter ?**

When a process migrates between cores, its working set (code, data) is in the L1/L2 cache of the old core. On the new core, these caches are cold, causing compulsory cache misses. Fetching data from L3 or main memory introduces latency spikes of tens to hundreds of nanoseconds per access, which accumulates into measurable jitter at the microsecond/millisecond scale.

**2. Est-ce toujours bénéfique de fixer l'affinité ?**

Not necessarily. If the pinned core is shared with an interrupt-heavy device or a kernel thread, affinity can worsen performance. Additionally, pinning prevents the scheduler from load-balancing across cores, which can reduce overall throughput. It is beneficial when the goal is latency stability for a specific task, not when maximizing system-wide throughput.

**3. Peut-on isoler complètement un cœur sous Linux standard ?**

Partially. The `isolcpus` boot parameter removes a core from the general scheduler, and `irqaffinity` can redirect most interrupts away from it. However, certain kernel threads and non-maskable interrupts (NMIs) cannot be fully excluded. Complete isolation requires the PREEMPT_RT patch or a dedicated RTOS. Standard Linux cannot achieve total core isolation.

---

## Section 10 — Discussion finale

**Linux standard est-il hard real-time ?** No. It is a general-purpose OS optimized for throughput and fairness. It provides no formal worst-case latency guarantee.

**Peut-on garantir une période stricte ?** Not under standard Linux. Every mechanism tested (nice, taskset) improves statistical behavior but none provides a provable upper bound on jitter.

**Quelle manipulation améliore le plus la stabilité ?** CPU affinity (`taskset`) combined with `nice` provides the most consistent improvement, as it eliminates cache migration penalties while increasing scheduling priority. However, the effect is configuration-dependent.

**Quelle est la principale source de variabilité ?** The kernel scheduler and interrupt handling. These are fundamental to the OS design and cannot be eliminated without changing the kernel architecture (PREEMPT_RT) or using a dedicated RTOS.

# PART 2 — Adapter la boucle en fonction de l'état du système
### view code on github for rt_loop_adaptive.py
## Exercice 1 — Comprendre la mesure CPU

**1. Pourquoi la charge CPU varie-t-elle d'une seconde à l'autre ?**

CPU load is a time-averaged metric over a sampling window. Processes wake and sleep, interrupts fire sporadically, kernel housekeeping tasks run periodically (timers, RCU, writeback). The stochastic nature of system activity makes CPU utilization inherently non-stationary over short intervals.

**2. Cette valeur représente-t-elle uniquement votre programme ?**

No. `psutil.cpu_percent()` reports system-wide CPU utilization across all processes, kernel threads, and interrupt handlers. Your program's contribution is only a fraction of the total. Other processes (system daemons, stress_cpu, etc.) all contribute to the reported value.

**3. Pourquoi cette mesure dépend-elle du scheduler ?**

The scheduler determines which processes run and for how long on each core. CPU utilization is measured as the fraction of time CPUs spend in non-idle states, which is directly determined by scheduling decisions. If the scheduler assigns more time to a process, the measured load increases. The measurement is a reflection of scheduler behavior, not an independent physical quantity.

---

## Exercice 2 — Interprétation progressive

**1. Le workload reste-t-il constant (nominal, no stress) ?**

It should remain predominantly at 0.7 (NORMAL mode) since without external stress, CPU load stays below 70%. Minor fluctuations may briefly push CPU load above the threshold due to transient system activity, causing occasional brief switches to DEGRADED, but these should be rare.

**2. Pourquoi converge-t-il vers une valeur stable ?**

The system exhibits negative feedback. In NORMAL mode, the workload is 0.7 which contributes to CPU load. If this pushes load above 70%, the system switches to DEGRADED (0.3 workload), which reduces CPU load. If load drops below 40%, it returns to NORMAL. The hysteresis band (40–70%) prevents rapid oscillation, and in steady state the system settles into whichever mode is consistent with the ambient load.

**3. Si le CPU est peu chargé, pourquoi le workload augmente-t-il ?**

Because the adaptation rule interprets low CPU load (< 40%) as headroom available for computation. The system transitions to NORMAL mode, increasing workload_ratio to 0.7, which exploits the available CPU capacity. This is the intended design: maximize computation when resources permit, reduce when constrained.

---

## Sections 9–12 — Analysis and Discussion

### 9.1 — Comparison of means

The adaptive version under stress should show a lower mean jitter than the non-adaptive version under stress (Part 1, scenario B). The mean decreases because when CPU load is high, the adaptive loop reduces its own workload, freeing CPU cycles and reducing contention with the stress process. However, if the mean only decreases slightly while the maximum remains high, the system is not fundamentally more stable — it merely shifts the distribution. The mean alone is insufficient; the tail behavior determines real-time viability.

### 9.2 — Extreme values

The maximum jitter in the adaptive version should be lower than the non-adaptive stressed version, but it will not be zero. Spikes still occur due to kernel preemption, interrupts, and scheduler non-determinism — none of which are affected by workload reduction. A single spike exceeding the deadline makes the system unacceptable for hard real-time. The adaptation reduces the frequency of misses but cannot eliminate them. In a hard real-time system, "rare" is not "never," and that distinction is the entire point.

### 9.3 — Workload evolution under stress

Under CPU stress, the workload will quickly drop to 0.3 (DEGRADED) as measured CPU load exceeds 70%. When stress terminates, CPU load drops below 40% and workload returns to 0.7 (NORMAL). The transition is not instantaneous — `psutil.cpu_percent()` has a smoothing window, so mode changes lag behind actual load changes. Oscillation can occur near the thresholds if CPU load hovers around 40% or 70%, which is why the hysteresis band exists.

### 12.1 — Efficacité de l'adaptation

The adaptation improves the global observed behavior: lower mean jitter, fewer deadline misses, and more predictable period under stress. This is visible on both the mean and the distribution (p95, p99 improve). However, worst-case jitter (the absolute maximum) may only improve modestly because extreme events are caused by OS-level factors outside the application's control.

### 12.2 — Le compromis

The cost is reduced computation per iteration. At workload_ratio 0.3 instead of 0.7, the system performs approximately 57% less useful work per cycle. Whether this trade-off is justified depends on the application: if the primary requirement is temporal stability (e.g., control loop), sacrificing secondary computation is correct engineering. If the computation itself is safety-critical (e.g., sensor fusion), reducing it may create a different failure mode.

### 12.3 — Limites structurelles

The adaptation cannot guarantee a strict bound because it operates at user-space level and reacts to observed load, not predicted load. The fundamental uncontrollable element is the Linux kernel scheduler — it can preempt any user process at any time for interrupt servicing, kernel thread execution, or scheduling decisions. No amount of user-space adaptation changes the OS's non-deterministic nature. To guarantee a bound, one needs either the PREEMPT_RT patch, a co-kernel architecture (Xenomai), or a dedicated RTOS.

### Section 11 — Le système est-il devenu temps réel ?

No. The system remains soft real-time under a general-purpose OS. The adaptation is a best-effort engineering strategy that improves statistical behavior. It does not change the theoretical properties of the platform. A hard real-time guarantee requires formal analysis of worst-case execution time, bounded interrupt latency, and deterministic scheduling — none of which Linux standard provides. The adaptation is analogous to adding shock absorbers to a vehicle: it improves ride quality but does not change the road surface.

# PART 3 — Intégration MQTT + EdgeX
### view rt_loop_mqtt.py on github 

## Part 3 — Answers to All Questions

### Section 9.2 — Différence entre "ressource" et "commande"

A **deviceResource** (e.g., `Mode`) is a data point — an attribute the device possesses, with a type, read/write permissions, and a default value. It is analogous to a variable or register.

A **deviceCommand** (e.g., `SetMode`) is an operation — it groups one or more resource operations into a named action that can be invoked via the EdgeX API. It is analogous to a function call that writes to one or more resources.

EdgeX needs the profile YAML because it is a generic platform that must interact with heterogeneous devices. The profile provides a standardized schema so that EdgeX can expose a uniform REST API (Core Command) without knowing the internal implementation of each device. Without it, EdgeX cannot know what operations are valid for a given device.

### Section 11.A.3 — Pourquoi l'intervalle n'est pas strictement 200 ms ?

Multiple factors:

1. The publish check (`now_pub - last_pub >= PUBLISH_INTERVAL`) executes only once per 20 ms loop iteration, introducing up to 20 ms of quantization error.
2. The MQTT `publish()` call has variable latency depending on TCP buffer state, network conditions (especially over Wi-Fi), and broker load.
3. The Linux scheduler can delay the loop iteration itself, shifting the moment when the publish check runs.
4. Docker networking on the gateway introduces additional latency between the Mosquitto container and the host network stack.
5. Wi-Fi introduces variable frame transmission delays, retransmissions, and contention with other stations.

### Section 12 — Point pédagogique clé (expanded)

The architecture implements a clean separation of concerns:

**The Device Profile** defines capabilities abstractly — it declares "this type of device can receive a SetMode command writing a String to the Mode resource." It is reusable across multiple devices of the same type.

**The Device instance** binds a profile to a concrete communication channel — "device1 uses the device-mode-profile and speaks MQTT on topic `tp/device1/cmd`." This allows the same profile to work over MQTT, Modbus, BACnet, or any other protocol EdgeX supports.

**Events** represent the supervision path: sampled, delayed, best-effort. They flow from device to broker to EdgeX Core Data. They are inherently non-real-time — their purpose is monitoring, logging, and analytics, not control.

**SetMode** represents the command path: a soft real-time feedback loop where a supervisor (human or automated) can reconfigure device behavior. The latency of this path includes EdgeX processing, MQTT delivery, and Wi-Fi propagation — it is measured in tens to hundreds of milliseconds, orders of magnitude slower than the 20 ms control loop.

This demonstrates the fundamental architectural principle: **control is local, supervision is remote**. The 20 ms loop never waits for or depends on the network. MQTT publication is fire-and-forget within the loop. Command reception is asynchronous via callback. If the network fails, the device continues operating autonomously in its current mode.





## Complete Execution Sequence (for reference)

bash

```bash
# ─── Part 1 ───
mkdir -p logs figures

# Scenario A: nominal
python3 rt_loop.py --period-ms 20 --duration-s 120 --epsilon-ms 2 --workload-ratio 0.2 --out logs/rt_A_nominal.csv

# Scenario B: CPU stress
python3 stress_cpu.py --seconds 130 &
python3 rt_loop.py --period-ms 20 --duration-s 120 --epsilon-ms 2 --workload-ratio 0.2 --out logs/rt_B_cpu_stress.csv
wait

# Scenario C: nice
python3 stress_cpu.py --seconds 130 &
nice -n -10 python3 rt_loop.py --period-ms 20 --duration-s 120 --epsilon-ms 2 --workload-ratio 0.2 --out logs/rt_C_nice.csv
wait

# Scenario D: CPU affinity
python3 stress_cpu.py --seconds 130 &
taskset -c 2 python3 rt_loop.py --period-ms 20 --duration-s 120 --epsilon-ms 2 --workload-ratio 0.2 --out logs/rt_D_affinity.csv
wait

# Analysis
python3 analyze_rt.py logs/rt_A_nominal.csv logs/rt_B_cpu_stress.csv logs/rt_C_nice.csv logs/rt_D_affinity.csv

# ─── Part 2 ───
# Scenario E: adaptive nominal
python3 rt_loop_adaptive.py --out logs/rt_E_adaptive_nominal.csv

# Scenario F: adaptive under stress
python3 stress_cpu.py --seconds 130 &
python3 rt_loop_adaptive.py --out logs/rt_F_adaptive_stress.csv
wait

python3 analyze_rt.py logs/*.csv

# ─── Part 3 ───
# On gateway: start EdgeX stack
cd Part3/gateway
docker compose up -d

# On gateway: verify services
curl http://localhost:59881/api/v2/ping
curl http://localhost:59880/api/v2/ping

# Inject profile
curl -X POST "http://localhost:59881/api/v2/deviceprofile" \
  -H "Content-Type: application/yaml" \
  --data-binary "@profile-device-mode.yaml"

# Inject device
curl -X POST "http://localhost:59881/api/v2/device" \
  -H "Content-Type: application/json" \
  --data-binary "@device1.json"

# On device: run MQTT-enabled loop
python3 rt_loop_mqtt.py --gateway-ip 192.168.X.X --out logs/rt_G_mqtt.csv

# On gateway: verify metrics flow
mosquitto_sub -h localhost -t "tp/device1/metrics"

# Verify EdgeX ingestion
curl "http://localhost:59880/api/v2/event?limit=5"

# Test SetMode command via MQTT
mosquitto_pub -h localhost -t "tp/device1/cmd" -m '{"Mode":"DEGRADED"}'
mosquitto_pub -h localhost -t "tp/device1/cmd" -m '{"Mode":"NORMAL"}'
```