# Failover headroom checker

A small Python CLI that answers one question: if traffic from one server pool fails over onto another, will the receiving pool absorb it, or will its servers drop out one by one?

## The problem behind it (Microsoft)

On 12 and 13 November 2026 Microsoft 365 (Outlook, Teams, Copilot) was down for most of a day. Microsoft's preliminary post-incident report gave three causes together:

- a lock-contention bug added to the Microsoft 365 networking gateways in July that stayed hidden for months,
- Teams failing over onto the Exchange Online gateways about 15 hours earlier, adding traffic,
- about 14% of gateway capacity already out of service.

More than 80% of gateway servers became unresponsive. Sources: [BleepingComputer](https://bleepingcomputer.com/news/microsoft/microsoft-says-months-old-bug-caused-global-microsoft-365-outage), [iTnews](https://www.itnews.com.au/news/microsoft-says-three-month-old-bug-behind-global-m365-outage-630382), [Network World](https://www.networkworld.com/article/4249392/microsoft-outage-a-cascading-failure-that-started-with-an-undetected-bug-2.html).

None of the three causes was enough alone. This tool shows that with numbers.

## Run it

Python 3.9+, no third-party packages.

```
cd 2026-11-23-failover-headroom
python3 headroom.py scenarios/*.json
python3 -m unittest -v
```

## Example output

The scenarios use invented numbers shaped like the incident: a 100-server mail gateway pool at 55,000 requests/sec takes a 10,000 rps failover from the chat pool.

```
== scenarios/2_reduced_capacity.json
Pool mail-gateways: 86 servers in service, rated 86,000 rps
Utilisation before failover: 64%
Failover from chat-gateways: +10,000 rps -> 76% of rated capacity
Verdict: SAFE
Max safe shift right now: 13,800 rps (138% of the failover traffic)

== scenarios/3_latent_bug.json
Pool mail-gateways: 86 servers in service, rated 86,000 rps
Utilisation before failover: 64%
Failover from chat-gateways: +10,000 rps -> 76% of rated capacity
Verdict: CASCADE
Cascade: 86 of 86 servers stop responding over 3 rounds (per round: [19, 54, 13])
Max safe shift right now: 3,480 rps (35% of the failover traffic)
```

Same failover, same 76% average. The only difference is the latent bug (servers hang at 85% of rated capacity). The weakest 19 servers go first, their load moves to the rest, and the whole pool falls in three rounds. The exit code is the worst verdict (0 SAFE, 1 AT RISK, 2 CASCADE), so it can gate a deploy or a failover runbook in CI.

## How it works

- `build_pool` gives each in-service server a rated capacity. Capacities are spread evenly between `capacity*(1-spread)` and `capacity*(1+spread)`, because real fleets are uneven.
- `cascade` spreads load evenly across live servers. Any server above `capacity * lock_limit` stops responding, its share moves to the others, and it repeats until nothing else fails.
- `max_safe_shift` is the largest extra load that keeps every server under its limit and the pool under the headroom target (default 80%).

## Design choices and trade-offs

- **Deterministic, no randomness.** The same scenario always gives the same verdict, which makes it testable and usable in CI. Real load is noisy; a Monte Carlo version would be the next step.
- **Even load balancing.** Real balancers are not perfectly even, which makes things worse than this model shows. So the tool is optimistic, and it still finds the cascade.
- **Failed servers never come back.** Real servers restart, then get hit again (a retry storm). Leaving that out keeps the model simple and still shows the point.
- **Standard library only.** Nothing to install, nothing to break.
- **JSON scenarios.** Easy to write by hand, easy to generate from a monitoring export later.

## Left out, and next steps

- Latency and queueing (an M/M/c model would show slowdowns before failure).
- Retries and client back-off, which make real cascades worse.
- Staged failover planning: "move 20% now, wait, move 20% more".
- Reading live numbers from Prometheus or Azure Monitor instead of a file.
- A small web page with a slider for failover size.

## Interview talking points

1. **Averages hide failure.** At 76% average utilisation the pool looked fine. The weakest servers were already past their real limit, and once they dropped out the load on everyone else rose. Capacity checks have to look at the weakest server, not the mean.
2. **Incidents usually need several causes at once.** The scenarios add one cause at a time (reduced capacity, then a latent bug) and only the combination cascades. That is what Microsoft's report described, and it is why chaos testing combines faults.
3. **Make reliability checks automatic.** The exit code turns the model into a gate: a failover runbook or deploy pipeline can refuse to shift traffic when the answer is CASCADE. I tested the core logic with small hand-worked cases (for example three servers rated 1, 2 and 3 under 4.5 rps fail one per round).

## Files

- `headroom.py` - the model and CLI
- `test_headroom.py` - 14 unit tests
- `scenarios/` - three example scenarios (invented numbers)
- `ideas.md` - the five ideas considered this week and how they were rated
