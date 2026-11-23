"""Failover headroom checker.

Question it answers: if one gateway pool fails over onto another, does the
receiving pool absorb the traffic, or do its servers fall over one by one?
"""
import argparse
import json
import sys


def build_pool(servers, out_of_service, capacity_rps, capacity_spread=0.0):
    """Rated capacity (requests/sec) of each in-service server.

    Real fleets are uneven (older hardware, noisy neighbours), so capacities are
    spread linearly from capacity*(1-spread) to capacity*(1+spread). Deterministic
    on purpose: the same scenario always gives the same answer.
    """
    if servers < 1 or not 0 <= out_of_service < servers:
        raise ValueError("need at least one in-service server")
    if not 0 <= capacity_spread < 1:
        raise ValueError("capacity_spread must be in [0, 1)")
    n = servers - out_of_service
    if n == 1:
        return [float(capacity_rps)]
    lo, hi = capacity_rps * (1 - capacity_spread), capacity_rps * (1 + capacity_spread)
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def cascade(capacities, load_rps, lock_limit=1.0):
    """Spread load evenly over live servers. Any server pushed past its limit stops
    responding, its share moves to the rest, and we repeat until nothing else fails.

    lock_limit < 1 models a latent bug (like lock contention) that makes a server
    hang before it reaches its rated capacity.
    Returns (surviving capacities, list of how many servers failed in each round).
    """
    alive = list(capacities)
    rounds = []
    while alive:
        per_server = load_rps / len(alive)
        still_up = [c for c in alive if per_server <= c * lock_limit]
        if len(still_up) == len(alive):
            break
        rounds.append(len(alive) - len(still_up))
        alive = still_up
    return alive, rounds


def max_safe_shift(capacities, load_rps, lock_limit=1.0, target=0.8):
    """Most extra traffic the pool can take while staying under the utilisation
    target AND with no server past its limit (so no cascade can start)."""
    no_cascade = len(capacities) * min(capacities) * lock_limit
    under_target = target * sum(capacities)
    return max(0.0, min(no_cascade, under_target) - load_rps)


def check(scenario):
    """Run one scenario dict and return a plain result dict."""
    pool = scenario["pool"]
    caps = build_pool(pool["servers"], pool.get("out_of_service", 0),
                      pool["capacity_rps"], pool.get("capacity_spread", 0.0))
    lock = pool.get("lock_limit", 1.0)
    target = scenario.get("headroom_target", 0.8)
    before = pool["load_rps"]
    after = before + scenario["failover"]["load_rps"]
    survivors, rounds = cascade(caps, after, lock)
    util_after = after / sum(caps)
    if rounds:
        verdict = "CASCADE"
    elif util_after > target:
        verdict = "AT RISK"
    else:
        verdict = "SAFE"
    return {
        "pool": pool["name"],
        "from": scenario["failover"]["from"],
        "in_service": len(caps),
        "rated_capacity_rps": sum(caps),
        "util_before": before / sum(caps),
        "util_after": util_after,
        "verdict": verdict,
        "failure_rounds": rounds,
        "survivors": len(survivors),
        "max_safe_shift_rps": max_safe_shift(caps, before, lock, target),
        "failover_rps": scenario["failover"]["load_rps"],
    }


def report(r):
    lines = [
        f"Pool {r['pool']}: {r['in_service']} servers in service, "
        f"rated {r['rated_capacity_rps']:,.0f} rps",
        f"Utilisation before failover: {r['util_before']:.0%}",
        f"Failover from {r['from']}: +{r['failover_rps']:,.0f} rps "
        f"-> {r['util_after']:.0%} of rated capacity",
        f"Verdict: {r['verdict']}",
    ]
    if r["failure_rounds"]:
        lines.append(f"Cascade: {r['in_service'] - r['survivors']} of {r['in_service']} servers "
                     f"stop responding over {len(r['failure_rounds'])} rounds "
                     f"(per round: {r['failure_rounds']})")
    lines.append(f"Max safe shift right now: {r['max_safe_shift_rps']:,.0f} rps "
                 f"({r['max_safe_shift_rps'] / r['failover_rps']:.0%} of the failover traffic)")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("scenario", nargs="+", help="scenario JSON file(s)")
    args = p.parse_args(argv)
    worst = 0
    for path in args.scenario:
        with open(path) as f:
            r = check(json.load(f))
        print(f"== {path}\n{report(r)}\n")
        worst = max(worst, ["SAFE", "AT RISK", "CASCADE"].index(r["verdict"]))
    return worst  # exit code: 0 safe, 1 at risk, 2 cascade (usable as a CI gate)


if __name__ == "__main__":
    sys.exit(main())
