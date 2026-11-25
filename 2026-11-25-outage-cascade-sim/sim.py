"""Deterministic simulation of a gateway fleet tipping into a cascading, self-sustaining outage."""
from dataclasses import dataclass, field

NEVER = float("inf")


@dataclass
class Scenario:
    servers: dict                      # region -> server count
    demand: dict                       # region -> requests per tick
    offline: dict = field(default_factory=dict)  # region -> servers already down before the incident
    surge_region: str = ""
    surge_extra: float = 0.0
    surge_start: int = 0
    surge_end: int = 0
    capacity: float = 100.0            # requests a server can handle per tick
    crash_at: float = 0.9              # latent defect: a server crashes above this share of capacity
    shed_at: float = 0.8               # with load shedding, servers reject anything above this share
    restart_ticks: int = 5
    retry_rate: float = 0.5            # share of failed requests that clients retry next tick
    ticks: int = 120


def simulate(sc: Scenario, partition: bool, shed: bool) -> list:
    """Return one dict per tick: offered, served, availability, servers_down."""
    if shed and sc.shed_at >= sc.crash_at:
        raise ValueError("shed_at must be below crash_at or shedding cannot prevent crashes")
    down_until = {r: [NEVER] * sc.offline.get(r, 0) + [0] * (n - sc.offline.get(r, 0)) for r, n in sc.servers.items()}
    backlog = {r: 0.0 for r in sc.servers}
    history = []
    for t in range(sc.ticks):
        offered = {r: sc.demand[r] + backlog[r] for r in sc.servers}
        if sc.surge_start <= t < sc.surge_end:
            offered[sc.surge_region] += sc.surge_extra
        pools = [[r] for r in sc.servers] if partition else [list(sc.servers)]
        served = {}
        for pool in pools:
            up = [(r, i) for r in pool for i, d in enumerate(down_until[r]) if d <= t]
            total = sum(offered[r] for r in pool)
            if not up:
                ok = 0.0
            else:
                load = total / len(up)  # shortcut: perfectly even balancing; real balancers skew, which tips servers earlier
                accepted = min(load, sc.shed_at * sc.capacity) if shed else load
                if accepted > sc.crash_at * sc.capacity:
                    for r, i in up:
                        down_until[r][i] = t + sc.restart_ticks
                    ok = 0.0
                else:
                    ok = accepted * len(up)
            share = ok / total if total else 1.0
            for r in pool:
                served[r] = offered[r] * share
        for r in sc.servers:
            backlog[r] = sc.retry_rate * (offered[r] - served[r])
        o, s = sum(offered.values()), sum(served.values())
        history.append({
            "tick": t, "offered": o, "served": s, "availability": s / o if o else 1.0,
            "servers_down": sum(d > t for ds in down_until.values() for d in ds) - sum(sc.offline.values()),
        })
    return history


def summarise(history: list, surge_end: int) -> dict:
    avail = [h["availability"] for h in history]
    healthy_from = next((h["tick"] for h in history[surge_end:]
                         if all(a >= 0.99 for a in avail[h["tick"]:])), None)
    return {
        "mean_availability": sum(avail) / len(avail),
        "worst_availability": min(avail),
        "outage_ticks": sum(a < 0.5 for a in avail),
        "peak_servers_down": max(h["servers_down"] for h in history),
        "recovered_at": healthy_from,
    }


# Shaped on public reports of the 12-13 Nov 2026 Microsoft 365 outage: ~14% of gateway
# capacity already offline, then a Teams failover pushed extra load onto the fleet.
NOV_2026 = Scenario(
    servers={"europe": 10, "us-east": 10, "us-west": 10, "asia": 10},
    demand={"europe": 600, "us-east": 600, "us-west": 600, "asia": 600},
    offline={"europe": 2, "us-east": 2, "us-west": 1, "asia": 1},
    surge_region="europe", surge_extra=700, surge_start=10, surge_end=70,
)

STRATEGIES = {
    "no mitigation": (False, False),
    "partitioning": (True, False),
    "load shedding": (False, True),
    "both": (True, True),
}
