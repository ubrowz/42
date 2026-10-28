"""The modular adder case study: casestudy/modadd.42 against casestudy/spec.42.

Every adder is checked on every input a, b < N, as a Q42 term with exact
amplitudes and as the emitted gate list, and the gate counts are pinned at the
ones CASESTUDY.md reports.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "casestudy"))

import check  # noqa: E402

QENV = check._load_reduced(os.path.join(ROOT, "casestudy", "modadd.42"))
with open(os.path.join(ROOT, "casestudy", "spec.42"), encoding="utf-8") as _fh:
    SENV = check.expand_env(check.parse_program(_fh.read()))

#: qubits, ccx, cx, x
COUNTS = {"mod3": (9, 20, 51, 6), "mod5": (12, 30, 71, 6),
          "mod7": (12, 30, 73, 8), "mod13": (15, 40, 93, 8)}


class TestModularAdder(unittest.TestCase):
    def test_the_term_agrees_with_the_spec(self):
        for name, n, N in check.ADDERS:
            with self.subTest(adder=name):
                self.assertEqual(check.check(QENV, SENV, name, n, N), N * N)

    def test_the_circuit_agrees_with_the_spec(self):
        for name, n, N in check.ADDERS:
            with self.subTest(adder=name):
                self.assertEqual(check.check_circuit(QENV, SENV, name, n, N), N * N)

    def test_the_gate_counts(self):
        """5 adders of 2n Toffolis and 4n + 1 CNOTs each, plus the constant N."""
        for name, n, N in check.ADDERS:
            with self.subTest(adder=name):
                gates, wires = check.circuit(QENV, name)
                ops = [g[0] for g in gates]
                got = (wires, ops.count("ccx"), ops.count("cx"), ops.count("x"))
                self.assertEqual(got, COUNTS[name])
                self.assertEqual(len(ops), sum(got[1:]), "only ccx, cx and x")
                ones = bin(N).count("1")
                self.assertEqual(got[1:], (5 * 2 * n, 5 * (4 * n + 1) + 2 * ones + 2,
                                           2 * ones + 2))


if __name__ == "__main__":
    unittest.main()
