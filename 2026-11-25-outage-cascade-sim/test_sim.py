from dataclasses import replace

import pytest

from sim import NOV_2026, Scenario, simulate, summarise

# One region, 2 servers of capacity 100. Crash above 90 per server, shed above 80.
ONE = Scenario(servers={"a": 2}, demand={"a": 150}, ticks=10, retry_rate=0.0)


def test_under_threshold_serves_everything():
    h = simulate(ONE, partition=False, shed=False)
    assert [x["availability"] for x in h] == [1.0] * 10
    assert max(x["servers_down"] for x in h) == 0


def test_over_threshold_crashes_whole_pool_then_restarts_into_same_overload():
    h = simulate(replace(ONE, demand={"a": 190}), partition=False, shed=False)  # 95 per server > 90
    assert h[0]["availability"] == 0.0 and h[0]["servers_down"] == 2
    assert h[4]["servers_down"] == 2          # still restarting (restart_ticks=5)
    assert h[5]["availability"] == 0.0        # back up at t=5, crashes again at once
    assert summarise(h, 0)["recovered_at"] is None


def test_shedding_caps_load_and_prevents_crash():
    h = simulate(replace(ONE, demand={"a": 190}), partition=False, shed=True)
    assert h[0]["served"] == 160              # 2 servers x 80
    assert h[0]["availability"] == pytest.approx(160 / 190)
    assert max(x["servers_down"] for x in h) == 0


def test_retries_add_to_next_tick():
    h = simulate(replace(ONE, demand={"a": 190}, retry_rate=0.5), partition=False, shed=False)
    assert h[1]["offered"] == 190 + 95


def test_partitioning_contains_blast_radius_but_strands_spare_capacity():
    two = Scenario(servers={"a": 2, "b": 2}, demand={"a": 190, "b": 100}, ticks=1, retry_rate=0.0)
    part = simulate(two, partition=True, shed=False)[0]
    assert part["served"] == 100 and part["servers_down"] == 2       # only region a falls over
    glob = simulate(two, partition=False, shed=False)[0]
    assert glob["served"] == 290 and glob["servers_down"] == 0       # 72.5 each, spread over 4 servers


def test_shed_limit_must_be_below_crash_limit():
    with pytest.raises(ValueError):
        simulate(replace(ONE, shed_at=0.95), partition=False, shed=True)


def test_nov_2026_scenario_headline_results():
    end = NOV_2026.surge_end
    base = summarise(simulate(NOV_2026, False, False), end)
    assert base["peak_servers_down"] == 34 and base["recovered_at"] is None   # metastable: never recovers
    no_retry = summarise(simulate(replace(NOV_2026, retry_rate=0), False, False), end)
    assert no_retry["recovered_at"] == end                                       # recovers when surge stops
    shed = summarise(simulate(NOV_2026, False, True), end)
    assert shed["peak_servers_down"] == 0 and shed["recovered_at"] is not None
