# Outage Cascade Simulator

A small Python simulation of a global gateway fleet. It reproduces the shape of the 12 to 13 November 2026 Microsoft 365 outage: a fleet already short on capacity gets a traffic surge, a latent defect crashes overloaded servers, and the failure spreads to every region. It then compares the mitigations from Microsoft's "Code Red" response, load shedding and geographic partitioning, on the same scenario.

## The problem behind it

- On 12 to 13 November 2026, Outlook, Teams, Exchange Online and Copilot were down or degraded for about 24 hours. A Microsoft 365 executive called it the most customer-impacting event in the company's history. Microsoft says it was not a cyberattack ([Reuters via Investing.com](https://www.investing.com/news/stock-market-news/microsoft-declares-internal-code-red-after-historic-24hour-outage--reuters-5048793), [Fox News](https://www.foxnews.com/us/microsoft-declares-code-red-historic-service-outage)).
- Reports describe a latent defect in the networking gateway servers. It surfaced when a Teams failover added load while about 14% of gateway capacity was already offline, and the failure cascaded across the fleet worldwide because the normal isolation barriers did not hold ([IncidentHub](https://blog.incidenthub.cloud/microsoft-365-outage-nov-12-2026), [Windows Forum](https://windowsforum.com/news/microsoft-365-november-2026-outage-gateway-defect-teams-failover-and-recovery.453521/), [SlashGear](https://www.slashgear.com/2320849/microsoft-november-2026-outage-cause-explained/)). Sources differ on the exact trigger.
- Internal memos describe a Code Red with workstreams on load shedding, geographic traffic partitioning and faster recovery. They also say fragmented diagnostic tools slowed the first response ([Interesting Engineering](https://interestingengineering.com/culture/microsoft-code-red-24-hour-outage-engineering-overhaul), [The Globe and Mail](https://www.theglobeandmail.com/business/article-microsoft-code-red-outage/)).

## Run it

```bash
pip install -r requirements.txt     # only pytest; the simulator uses the standard library
python run.py                       # or: python run.py --retry-rate 0
python -m pytest -q                 # 7 passed
```

## Example output

```
Fleet: 40 gateways, 6 already offline. Surge of +700 req/tick into europe from t=10 to t=70. Retry rate 0.5.

strategy        mean avail   worst  outage min  peak down  recovered
no mitigation          8%      0%         110         34      never
partitioning          54%     41%          60          8      never
load shedding         89%     78%           0          0       t=71
both                  82%     65%           0          0       t=73

Availability over time (1 tick = 1 minute, surge marked with ^):
no mitigation  |█████                                                       |
partitioning   |█████▅▄▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▄▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅|
load shedding  |█████▇▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆█████████████████████████|
both           |█████▆▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▆████████████████████████|
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

What it shows:

1. **No mitigation:** the surge pushes every server past the defect threshold at the same moment, and the whole fleet goes down. When servers restart, client retries hit them straight away and they crash again. The fleet never recovers, even after the surge ends. This is a metastable failure: the trigger is gone, but the retries alone keep the system overloaded. Run `python run.py --retry-rate 0` and it recovers as soon as the surge stops.
2. **Partitioning** keeps the damage inside Europe (8 servers down, not 34). Europe still never recovers, and the other regions' spare capacity can't help it.
3. **Load shedding** rejects requests above 80% of capacity. No server crashes, about 1 in 5 requests are refused during the surge, and the fleet recovers one minute after the surge ends.
4. **Both together** is slightly worse than shedding alone in this scenario, because partitioning stops Europe from using spare capacity in other regions. That is the real trade-off between limiting the blast radius and sharing capacity.

## How it works

- `sim.py` (about 100 lines) holds the model. Each tick (one minute), every region gets its demand plus retries from the last tick, and the surge region gets extra load. Traffic is spread evenly over the servers that are up, either across the whole fleet or within each region when partitioning is on.
- A server that receives more than 90% of its capacity crashes (the latent defect) and is down for 5 ticks. With load shedding, a server accepts at most 80% and rejects the rest.
- Half of all failed or rejected requests are retried in the next tick.
- `run.py` runs the four strategies on the November scenario and prints a table and text sparklines.
- Everything is deterministic, with no randomness, so the tests can use exact numbers worked out by hand.

## Design choices and trade-offs

- **Deterministic and even balancing.** Every server in a pool gets the same load, so a pool either crashes all at once or not at all. That exaggerates the cliff edge, but it makes every result reproducible and easy to check by hand. Real load balancers are uneven, which tips some servers over earlier.
- **A small model rather than a big framework.** The point is to show the mechanism (latent defect + reduced capacity + surge + retries = metastable outage) clearly, not to predict Microsoft's real numbers. The scenario numbers are made up but shaped on the public reports (about 14% offline, surge from a failover).
- **No plotting library.** Unicode sparklines show the timeline in the terminal, so the only dependency is pytest.

## What was left out

- Random variation, uneven load balancing and gradual (staggered) restarts.
- Retry back-off with jitter, circuit breakers and admission control based on queue length.
- Spill-over between partitions: sending excess traffic to a neighbour cell only when that cell has room.
- The diagnostics side of the memo: correlating health signals from many tools to find the root cause faster.

## Next steps

1. Add exponential back-off with jitter and show how much it shortens the metastable phase.
2. Add controlled spill-over between partitions, which should beat both "partitioning" and "load shedding" alone.
3. Add random server capacity and run each strategy 1,000 times to report a range, not one number.
4. Add a small web page with sliders for retry rate, surge size and thresholds.

## Interview talking points

1. **Metastable failure.** I can explain why the outage lasted a day rather than minutes: once the fleet was down, client retries alone kept it overloaded after the trigger was gone. The simulator shows this directly by switching retries off.
2. **Blast radius versus shared capacity.** Partitioning contains a failure but strands spare capacity. Load shedding keeps servers alive but refuses some users. I measured both and can explain why combining them was not automatically better, and what spill-over would add.
3. **Testing a simulation.** The model is deterministic, so the tests use small cases worked out by hand: 2 servers at 95 requests each must crash, shedding must serve exactly 160 of 190, and partitioning must keep one region up while the global pool spreads the same load safely.
