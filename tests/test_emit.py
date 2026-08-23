"""The two pieces an emitter needs before it can be written or trusted.

`q42.types.width` decides whether a term is emittable at all -- not every type is
a qubit register -- and `tools/qasm_sim.py` is an independent simulator over the
gate lists an emitter would produce.

`TestHarnessAgreesWithQ42` is the one to read.  It establishes that the harness
is trustworthy *before* there is an emitter to check with it, by running circuits
whose gate lists are known by hand and confirming that two entirely separate
pieces of code -- Q42's evaluator, and a hundred lines of complex arithmetic that
share nothing with it -- produce the same matrix.  Until that holds, a round-trip
failure would be as likely to mean the harness is wrong as the emitter is.
"""

from __future__ import annotations

import cmath
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from qasm_sim import agree, unitary_of                      # noqa: E402
from q42.core import column, matrix                        # noqa: E402
from q42.emit import NotEmittable, emit, to_qasm            # noqa: E402
from q42.syntax import parse_program, parse_term            # noqa: E402
from q42.types import (                                     # noqa: E402
    QUBIT,
    basis_of,
    ground,
    infer,
    infer_all,
    qubits,
    width,
)
from rel42.core import expand_env                           # noqa: E402
from rel42.types import TMu, TOne, TProd, TSum, TVar, TZero  # noqa: E402

GATES = os.path.join(ROOT, "q42", "gates.42")
with open(GATES, encoding="utf-8") as _fh:
    _SRC = parse_program(_fh.read())
_SCHEMES, _ = infer_all(_SRC)
_ENV = expand_env(_SRC)


def q42_matrix(name, n=None):
    """The matrix Q42 itself gives for a definition in `gates.42`, or a primitive."""
    if name in _SCHEMES:
        return matrix(_ENV[name], basis_of(ground(_SCHEMES[name], n).dom), _ENV)
    term = parse_term(name)                    # `v` and `omega` are not definitions
    return matrix(term, basis_of(ground(infer(term), n).dom), _ENV)


def reference(term, at, env):
    """Q42's own matrix, with separate bases for domain and codomain.

    `matrix` takes one basis and so assumes an endomorphism, which most gates
    are and the plumbing is not: `mat : (1+1) x a <-> a + a` has domain and
    codomain of the same width built from different values.
    """
    d, c = basis_of(at.dom), basis_of(at.cod)
    cols = [column(term, b, env) for b in d]
    return [[cols[j].get(c[i], 0) for j in range(len(d))] for i in range(len(c))]


def emitted(name, n=None):
    """The emitter's gates for a definition, and Q42's own matrix for it."""
    at = ground(_SCHEMES[name], n)
    gates, wires = emit(_ENV[name], at.dom, _ENV)
    return gates, wires, reference(_ENV[name], at, _ENV)


class TestWidth(unittest.TestCase):
    """`width` is the side condition §5 says a compiler needs and 42 does not."""

    def test_the_clauses(self):
        cases = [
            (TOne(), 0),                                   # no qubits, one state
            (QUBIT, 1),
            (qubits(2), 2),
            (qubits(5), 5),
            (TProd(TProd(QUBIT, QUBIT), QUBIT), 3),        # bracketing is irrelevant
            (TSum(QUBIT, QUBIT), 2),                       # a choice supplies a qubit
        ]
        for t, want in cases:
            with self.subTest(t=t):
                self.assertEqual(width(t), want)

    def test_a_good_type_can_be_a_bad_register(self):
        """§5's example: three dimensions, and no number of two-way lanes holds it."""
        self.assertEqual(width(TSum(TOne(), QUBIT)), None)

    def test_the_test_is_structural_not_arithmetic(self):
        """A power-of-two dimension is not enough; the branches must agree.

        `(1 + 1) + (1 + (1 + 1))` has dimension 5 -- but the point is that even
        where the dimension does come out right, it is the *shape* that decides.
        """
        lopsided = TSum(TOne(), TSum(TOne(), TSum(TOne(), TOne())))
        self.assertEqual(len(basis_of(lopsided)), 4)       # a power of two
        self.assertIsNone(width(lopsided))                 # and still not a register

    def test_what_is_refused(self):
        for t in (TZero(), TVar(0), TMu(0, TSum(TOne(), TVar(0)))):
            with self.subTest(t=t):
                self.assertIsNone(width(t))

    def test_a_vacuous_mu_is_looked_through(self):
        """`mu X. 1 + 1` never mentions X, so it is a qubit wearing a hat."""
        self.assertEqual(width(TMu(0, QUBIT)), 1)

    def test_every_library_definition_that_has_a_width_is_a_power_of_two(self):
        checked = 0
        for name, scheme in _SCHEMES.items():
            if scheme.params:
                continue
            w = width(ground(scheme).dom)
            if w is not None:
                self.assertEqual(len(basis_of(ground(scheme).dom)), 1 << w)
                checked += 1
        self.assertGreater(checked, 15)


class TestHarnessAgreesWithQ42(unittest.TestCase):
    """Two separate computations of the same matrix, for circuits we know by hand.

    Nothing here is a round trip yet -- there is no emitter.  These are the gate
    lists an emitter *should* produce, written out, so that when one is produced
    mechanically a disagreement means the emitter is wrong.
    """

    CIRCUITS = [
        ("x",    1, [("x", [0])]),
        ("z",    1, [("z", [0])]),
        ("s",    1, [("s", [0])]),
        ("t",    1, [("t", [0])]),
        ("h",    1, [("h", [0])]),
        ("hh",   1, [("h", [0]), ("h", [0])]),
        ("cx",   2, [("cx", [0, 1])]),
        ("cz",   2, [("cz", [0, 1])]),
        ("bell", 2, [("h", [0]), ("cx", [0, 1])]),
        ("ccx",  3, [("ccx", [0, 1, 2])]),
        ("ghz",  3, [("h", [0]), ("cx", [0, 1]), ("cx", [1, 2])]),
    ]

    def test_each_circuit(self):
        for name, n, gates in self.CIRCUITS:
            with self.subTest(gate=name):
                ok, why = agree(q42_matrix(name, n), unitary_of(gates, n))
                self.assertTrue(ok, f"{name}: {why}")

    def test_swap_needs_its_width_supplied(self):
        """`swapprod : a x b <-> b x a` is not a two-qubit gate until you say so."""
        ok, why = agree(q42_matrix("swap", 2), unitary_of([("swap", [0, 1])], 2))
        self.assertTrue(ok, why)

    def test_v_is_the_inverse_square_root_of_x_and_not_the_usual_one(self):
        """A detail that would silently produce wrong controlled circuits.

        OpenQASM's `sx` is the *other* square root: `v` is `sxdg` times -1.  Up to
        global phase either would pass a bare simulator check, and they differ the
        moment one of them is controlled.
        """
        v = q42_matrix("v", 1)
        ok, _ = agree(v, unitary_of([("sxdg", [0])], 1), up_to_phase=True)
        self.assertTrue(ok, "v should be sxdg up to phase")
        wrong, _ = agree(v, unitary_of([("sx", [0])], 1), up_to_phase=True)
        self.assertFalse(wrong, "v is NOT sx, even up to phase")
        exact, why = agree(v, unitary_of([("sxdg", [0]), ("gphase", [math.pi])], 1))
        self.assertTrue(exact, f"with the phase carried it should be exact: {why}")

    def test_the_harness_notices_a_wrong_circuit(self):
        """A check that cannot fail is not a check."""
        ok, why = agree(q42_matrix("cx", 2), unitary_of([("cx", [1, 0])], 2))
        self.assertFalse(ok)
        self.assertIn("differ by", why)

    def test_global_phase_is_carried_rather_than_ignored(self):
        plain = unitary_of([("x", [0])], 1)
        turned = unitary_of([("x", [0]), ("gphase", [math.pi])], 1)
        self.assertFalse(agree(plain, turned)[0])
        self.assertTrue(agree(plain, turned, up_to_phase=True)[0])


class TestEmitterRoundTrips(unittest.TestCase):
    """The emitter's gates, simulated independently, against Q42's own matrix.

    This is what the harness was built for: `q42.emit` walks a term and produces
    indices, `tools/qasm_sim` reads those indices back into a matrix knowing
    nothing about terms, and the two must agree.
    """

    def test_the_gate_library(self):
        cases = [("x", 1), ("y", 1), ("z", 1), ("s", 1), ("t", 1), ("sdg", 1),
                 ("tdg", 1), ("h", 1), ("hh", 1), ("vdg", 1),
                 ("cx", 2), ("cz", 2), ("swap", 2), ("bell", 2), ("ncx", 2),
                 ("ccx", 3), ("ghz", 3), ("cswap", 3)]
        for name, n in cases:
            with self.subTest(gate=name):
                gates, wires, want = emitted(name, n)
                ok, why = agree(want, unitary_of(gates, wires))
                self.assertTrue(ok, f"{name}: {why}")

    def test_the_re_bracketing_primitives_emit_nothing(self):
        """The claim `q42/emit.py` opens with, checked rather than asserted."""
        # given as types rather than widths: `unitprod : 1 x a <-> a` has a
        # domain no `n`-qubit register unifies with, its first factor being `1`.
        cases = [("id", QUBIT),
                 ("assocprod", qubits(3)),
                 ("unitprod", TProd(TOne(), QUBIT)),
                 ("dist", TProd(QUBIT, QUBIT))]
        for name, dom in cases:
            with self.subTest(prim=name):
                gates, _ = emit(parse_term(name), dom, {})
                self.assertEqual(gates, [], f"{name} should need no gate")

    def test_swapprod_is_free_in_the_middle_and_not_at_the_end(self):
        """The one place the "no gate" claim needs care.

        Exchanging two blocks is a relabelling, so a `swapprod` *inside* a term
        costs nothing -- the layout carries it and later gates simply use the
        other indices. But a term that *ends* with its wires permuted has to hand
        them back in the standard order, and that costs a real swap. Both halves
        of that matter, so both are checked.
        """
        there_and_back = parse_term("swapprod ; swapprod")
        at = ground(infer(there_and_back), 2)
        self.assertEqual(emit(there_and_back, at.dom, {})[0], [])

        once = parse_term("swapprod")
        gates, _ = emit(once, ground(infer(once), 2).dom, {})
        self.assertEqual([g[0] for g in gates], ["swap"])

    def test_a_choice_is_a_control_with_no_rule_of_its_own(self):
        """`cx` and `ccx` come out as one gate each, from `ctrl` alone."""
        self.assertEqual(emitted("cx", 2)[0], [("cx", [0, 1])])
        self.assertEqual(emitted("ccx", 3)[0], [("ccx", [0, 1, 2])])

    def test_the_fredkin_falls_out_of_ctrl_swapprod(self):
        """One branch permutes and the other does not; the emitter reconciles.

        A single Fredkin, and which of its two targets is named first does not
        matter -- a swap is symmetric in them.
        """
        (gate,), _, _ = emitted("cswap", 3)
        name, qs = gate[0], list(gate[1])
        self.assertEqual(name, "cswap")
        self.assertEqual(qs[0], 0)
        self.assertEqual(sorted(qs[1:]), [1, 2])

    def test_a_controlled_global_phase_is_the_t_gate(self):
        """`t = id + omega` needs no table entry: it derives."""
        self.assertEqual(emitted("t", 1)[0], [("p", [0], math.pi / 4)])

    def test_a_negative_control_is_spelled_out(self):
        self.assertEqual(emitted("ncx", 2)[0],
                         [("x", [0]), ("cx", [0, 1]), ("x", [0])])

    def test_a_phase_decomposes_to_any_depth(self):
        """`ccz` is a phase under three controls, and `cccz` under four."""
        for name, n in [("ccz", 3), ("cz", 2)]:
            with self.subTest(gate=name):
                gates, wires, want = emitted(name, n)
                ok, why = agree(want, unitary_of(gates, wires))
                self.assertTrue(ok, f"{name}: {why}")
                self.assertTrue(all(g[0] in {"p", "cp", "cx"} for g in gates),
                                f"{name} should be phases and cx: {gates}")

    def test_a_controlled_hadamard_works_at_depth_one(self):
        for name in ("ch", "cv"):
            with self.subTest(gate=name):
                gates, wires, want = emitted(name, 2)
                ok, why = agree(want, unitary_of(gates, wires))
                self.assertTrue(ok, f"{name}: {why}")

    def test_deeper_hadamard_says_what_is_missing(self):
        """The one gap left, and it names itself rather than failing obscurely."""
        from q42.emit import _controlled
        with self.assertRaises(NotEmittable) as caught:
            _controlled("h", (2,), ((0, 1), (1, 1)))
        self.assertIn("square-root recursion", str(caught.exception))

    def test_a_term_that_is_not_a_register_is_refused(self):
        with self.assertRaises(NotEmittable):
            emit(parse_term("id"), TSum(TOne(), QUBIT), {})

    def test_the_qasm_is_well_formed(self):
        gates, wires, _ = emitted("bell", 2)
        text = to_qasm(gates, wires, "bell")
        self.assertIn("OPENQASM 3.0;", text)
        self.assertIn("qubit[2] q;", text)
        self.assertIn("cx q[0], q[1];", text)
        self.assertNotIn("gate ", text)             # nothing invented; stdgates only
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith(("//", "OPENQASM", "include", "gate")):
                self.assertTrue(line.endswith((";", "}")), f"unterminated: {line}")


class TestMultiControl(unittest.TestCase):
    """The decomposition, and the two identities it rests on."""

    def test_v_is_that_particular_product(self):
        """`v = e^(3i.pi/4) . S H S`, which is what the emitter spells it as.

        Checked because `to_qasm` used to define `sxdg` as `s; h; s` -- right up
        to a phase of e^(i.pi/4), and a global phase stops being global the moment
        the gate sits under a control.  The emitter now emits only gates the
        target defines, and this is the identity that lets it.
        """
        v = q42_matrix("v", 1)
        spelled = unitary_of([("gphase", [], 3 * math.pi / 4),
                              ("s", [0]), ("h", [0]), ("s", [0])], 1)
        ok, why = agree(v, spelled)
        self.assertTrue(ok, f"exactly, not up to phase: {why}")

    def test_the_halving_recursion(self):
        """A phase on the all-ones state of k wires, for k past what the format has."""
        from q42.emit import _phase
        for k in (1, 2, 3, 4, 5):
            with self.subTest(wires=k):
                gates = _phase(list(range(k)), math.pi / 3)
                got = unitary_of(gates, k)
                want = [[0j] * (1 << k) for _ in range(1 << k)]
                for i in range(1 << k):
                    want[i][i] = 1
                want[-1][-1] = cmath.exp(1j * math.pi / 3)
                ok, why = agree(want, got)
                self.assertTrue(ok, f"{k} wires: {why}")
                if k > 2:
                    self.assertTrue(all(g[0] in {"p", "cp", "cx"} for g in gates))

    def test_x_at_depth_three_goes_through_the_phase_route(self):
        """C^3 X, which the format has no name for: h, a deep phase, h."""
        from q42.emit import _controlled
        gates = _controlled("x", (3,), ((0, 1), (1, 1), (2, 1)))
        got = unitary_of(gates, 4)
        want = [[1 if i == j else 0j for j in range(16)] for i in range(16)]
        want[14][14], want[15][15] = 0, 0
        want[14][15], want[15][14] = 1, 1
        ok, why = agree(want, got)
        self.assertTrue(ok, why)


class TestWholeAlgorithmsEmit(unittest.TestCase):
    """The libraries, end to end -- which is the claim §8 wanted to make."""

    LIBS = ["classical", "deutsch", "fib", "gates", "grover", "gsum", "qft3",
            "teleport"]

    def test_every_definition_of_every_library_round_trips(self):
        import glob

        total = 0
        for path in sorted(glob.glob(os.path.join(ROOT, "q42", "*.42"))):
            src = parse_program(open(path, encoding="utf-8").read())
            schemes, _ = infer_all(src)
            env = expand_env(src)
            for name, scheme in schemes.items():
                if scheme.params:
                    continue
                at = ground(scheme)
                w = width(at.dom)
                if w is None or w > 5 or width(at.cod) != w:
                    continue
                with self.subTest(lib=os.path.basename(path), definition=name):
                    gates, wires = emit(env[name], at.dom, env)
                    to_qasm(gates, wires, name)          # must also be writable
                    d, c = basis_of(at.dom), basis_of(at.cod)
                    cols = [column(env[name], b, env) for b in d]
                    want = [[cols[j].get(c[i], 0) for j in range(len(d))]
                            for i in range(len(c))]
                    ok, why = agree(want, unitary_of(gates, wires))
                    self.assertTrue(ok, f"{name}: {why}")
                    total += 1
        self.assertGreater(total, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
