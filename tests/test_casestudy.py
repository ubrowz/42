"""The modular adder case study: casestudy/modadd.42 against casestudy/spec.42.

`42q check` runs each adder against the specification on every input a, b < N,
both as a Q42 term with exact amplitudes and as the emitted circuit, and the
gate counts are pinned at the ones CASESTUDY.md reports.
"""
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from q42.__main__ import _load_reduced, _resolve, _typed, main  # noqa: E402
from q42.emit import emit                                        # noqa: E402
from q42.types import ground                                     # noqa: E402

MODADD = os.path.join(ROOT, "casestudy", "modadd.42")
SPEC = os.path.join(ROOT, "casestudy", "spec.42")

#: adder, bits per number, modulus, then qubits, ccx, cx, x
ADDERS = [("mod3", 2, 3, 9, 20, 51, 6), ("mod5", 3, 5, 12, 30, 71, 6),
          ("mod7", 3, 7, 12, 30, 73, 8), ("mod13", 4, 13, 15, 40, 93, 8)]


def check(*argv):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(["check", *argv])
    return code, out.getvalue() + err.getvalue()


class TestModularAdder(unittest.TestCase):
    def test_every_adder_agrees_with_the_spec(self):
        for name, _n, N, *_ in ADDERS:
            with self.subTest(adder=name):
                code, out = check(MODADD, name, SPEC, "modadd", "--encode", f"enc{N}")
                self.assertEqual(code, 0, out)
                self.assertIn(f"the program: {N * N} input(s) agree, exactly", out)
                self.assertIn(f"the circuit: {N * N} input(s) agree", out)

    def test_a_wrong_adder_is_caught(self):
        """The 3-bit construction with 5 loaded where 7 is due."""
        import tempfile

        with open(MODADD, encoding="utf-8") as fh:
            src = fh.read() + "\ndef bad7 = modadd add3 load5 cload5\n"
        with tempfile.NamedTemporaryFile("w", suffix=".42", delete=False) as fh:
            fh.write(src)
        try:
            code, out = check(fh.name, "bad7", SPEC, "modadd", "--encode", "enc7")
        finally:
            os.unlink(fh.name)
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] the program", out)

    def test_the_gate_counts(self):
        """5 adders of 2n Toffolis and 4n + 1 CNOTs each, plus the constant N."""
        env = _load_reduced(MODADD)
        for name, n, N, *counts in ADDERS:
            with self.subTest(adder=name):
                term = _resolve(env, name)
                gates, wires = emit(term, ground(_typed(env, name, term)).dom, env)
                ops = [g[0] for g in gates]
                got = [wires, ops.count("ccx"), ops.count("cx"), ops.count("x")]
                self.assertEqual(got, counts)
                self.assertEqual(len(ops), sum(got[1:]), "only ccx, cx and x")
                ones = bin(N).count("1")
                self.assertEqual(got[1:], [5 * 2 * n, 5 * (4 * n + 1) + 2 * ones + 2,
                                           2 * ones + 2])


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main()
