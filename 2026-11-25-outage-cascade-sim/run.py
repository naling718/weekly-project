"""Compare mitigation strategies on the Nov 2026 scenario.  python run.py [--retry-rate 0.5]"""
import argparse
from dataclasses import replace

from sim import NOV_2026, STRATEGIES, simulate, summarise

BARS = " ▁▂▃▄▅▆▇█"


def sparkline(values, width=60):
    step = len(values) / width
    return "".join(BARS[round(values[int(i * step)] * (len(BARS) - 1))] for i in range(width))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--retry-rate", type=float, default=NOV_2026.retry_rate)
    args = p.parse_args()
    if not 0 <= args.retry_rate < 1:
        p.error("--retry-rate must be in [0, 1)")
    sc = replace(NOV_2026, retry_rate=args.retry_rate)

    print(f"Fleet: {sum(sc.servers.values())} gateways, {sum(sc.offline.values())} already offline. "
          f"Surge of +{sc.surge_extra:.0f} req/tick into {sc.surge_region} from t={sc.surge_start} to t={sc.surge_end}. "
          f"Retry rate {sc.retry_rate}.\n")
    print(f"{'strategy':<15}{'mean avail':>11}{'worst':>8}{'outage min':>12}{'peak down':>11}{'recovered':>11}")
    timelines = {}
    for name, (partition, shed) in STRATEGIES.items():
        h = simulate(sc, partition, shed)
        s = summarise(h, sc.surge_end)
        rec = f"t={s['recovered_at']}" if s["recovered_at"] is not None else "never"
        print(f"{name:<15}{s['mean_availability']:>10.0%}{s['worst_availability']:>8.0%}"
              f"{s['outage_ticks']:>12}{s['peak_servers_down']:>11}{rec:>11}")
        timelines[name] = sparkline([x["availability"] for x in h])
    print("\nAvailability over time (1 tick = 1 minute, surge marked with ^):")
    marks = "".join("^" if sc.surge_start <= i * sc.ticks / 60 < sc.surge_end else " " for i in range(60))
    for name, line in timelines.items():
        print(f"{name:<15}|{line}|")
    print(f"{'':<15} {marks}")
