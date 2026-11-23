import io
import json
import os
import unittest
from contextlib import redirect_stdout

from headroom import build_pool, cascade, check, main, max_safe_shift

HERE = os.path.dirname(os.path.abspath(__file__))


class BuildPool(unittest.TestCase):
    def test_spread_is_linear(self):
        self.assertEqual(build_pool(4, 1, 10, 0.5), [5.0, 10.0, 15.0])

    def test_single_server(self):
        self.assertEqual(build_pool(2, 1, 10, 0.5), [10.0])

    def test_rejects_empty_pool(self):
        with self.assertRaises(ValueError):
            build_pool(3, 3, 10)


class Cascade(unittest.TestCase):
    def test_no_failure_when_everyone_fits(self):
        # 2.7 rps over 3 servers = 0.9 each, smallest limit is 1
        alive, rounds = cascade([1, 2, 3], 2.7)
        self.assertEqual((len(alive), rounds), (3, []))

    def test_partial_cascade_settles(self):
        # 5/3=1.67 kills the 1; 5/2=2.5 fits on the two 3s
        alive, rounds = cascade([1, 3, 3], 5)
        self.assertEqual((alive, rounds), ([3, 3], [1]))

    def test_full_collapse(self):
        # 1.5 kills 1 -> 2.25 kills 2 -> 4.5 kills 3
        alive, rounds = cascade([1, 2, 3], 4.5)
        self.assertEqual((alive, rounds), ([], [1, 1, 1]))

    def test_lock_limit_triggers_failure_below_rated_capacity(self):
        # 0.9 per server is under rated 1.0 but over the bugged limit 0.8
        self.assertEqual(cascade([1, 1, 1], 2.7)[1], [])
        self.assertEqual(cascade([1, 1, 1], 2.7, lock_limit=0.8)[1], [3])


class MaxSafeShift(unittest.TestCase):
    def test_bound_by_weakest_server(self):
        # no-cascade bound 3*1=3, target bound 0.8*6=4.8 -> 3 - 1 load
        self.assertEqual(max_safe_shift([1, 2, 3], 1), 2)

    def test_bound_by_target(self):
        # no-cascade bound 10, target bound 0.5*10=5 -> 5 - 1
        self.assertEqual(max_safe_shift([5, 5], 1, target=0.5), 4)

    def test_never_negative(self):
        self.assertEqual(max_safe_shift([1, 1], 5), 0)

    def test_shifting_exactly_the_max_causes_no_cascade(self):
        caps = build_pool(100, 14, 1000, 0.2)
        shift = max_safe_shift(caps, 55000, lock_limit=0.85)
        self.assertEqual(cascade(caps, 55000 + shift, 0.85)[1], [])
        self.assertNotEqual(cascade(caps, 55000 + shift + 1, 0.85)[1], [])


class Scenarios(unittest.TestCase):
    def load(self, name):
        with open(os.path.join(HERE, "scenarios", name)) as f:
            return json.load(f)

    def test_verdicts(self):
        self.assertEqual(check(self.load("1_normal_day.json"))["verdict"], "SAFE")
        self.assertEqual(check(self.load("2_reduced_capacity.json"))["verdict"], "SAFE")
        r = check(self.load("3_latent_bug.json"))
        self.assertEqual((r["verdict"], r["survivors"]), ("CASCADE", 0))

    def test_at_risk(self):
        s = self.load("1_normal_day.json")
        s["pool"]["capacity_spread"] = 0  # even fleet: 850 rps each, all servers rated 1000
        s["failover"]["load_rps"] = 30000  # 85% utilisation, above the 80% target
        self.assertEqual(check(s)["verdict"], "AT RISK")

    def test_cli_exit_code_is_worst_verdict(self):
        paths = [os.path.join(HERE, "scenarios", n)
                 for n in ("1_normal_day.json", "3_latent_bug.json")]
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(paths)
        self.assertEqual(code, 2)
        self.assertIn("Verdict: CASCADE", out.getvalue())


if __name__ == "__main__":
    unittest.main()
