"""Tests for Q42.  Run with:  python3 tests/test_q42.py

Supersedes spike/q42_spike.py, which checked the same numerical facts against a
throwaway evaluator.  What is new here beyond the spike is everything that comes
of being a real module: the type checker, the enumeration of a basis from a type,
the rejection of the constructors that need an idempotent semiring, and the claim
that all of this is *shared* with rel42 rather than copied from it.

`TestSharedWithRel42` is the one to read if you care about the architecture.
"""

from __future__ import annotations

import cmath
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import q42  # noqa: E402
import rel42  # noqa: E402
from q42 import (  # noqa: E402
    OMEGA,
    ONE,
    PRIMS,
    PRIM_SCHEMES,
    QUBIT,
    Q42Error,
    V_MATRIX,
    ZERO,
    apply_vec,
    basis_of,
    bits_of,
    column,
    ket,
    matrix,
    parse_program,
    parse_state,
    parse_term,
    show_ket,
)
from q42.exact import Exact, ROOT2  # noqa: E402
from q42.types import free_vars, ground, infer, infer_all, qubits  # noqa: E402
from rel42.core import (  # noqa: E402
    Inl,
    Pair,
    Ref,
    Rel42Error,
    Seq,
    UNIT,
    dagger,
    expand_env,
    run as rel_run,
)
from rel42.syntax import (  # noqa: E402
    from_nat,
    parse_program as rel_parse_program,
)
from rel42.types import Scheme, TOne, TProd, TSum, TVar  # noqa: E402

GATES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "q42", "gates.42"
)
with open(GATES, encoding="utf-8") as _fh:
    SRC = parse_program(_fh.read())      # as written: combinators intact
ENV = expand_env(SRC)                    # applications reduced, ready to run

TOL = 1e-10
BIT = [ZERO, ONE]
TWO = basis_of(qubits(2))
THREE = basis_of(qubits(3))

H_EXPECTED = [[2**-0.5, 2**-0.5], [2**-0.5, -(2**-0.5)]]
X_M = [[0, 1], [1, 0]]
Z_M = [[1, 0], [0, -1]]
I2 = [[1, 0], [0, 1]]


def mat(name, basis=None, env=None):
    return matrix(Ref(name), basis or BIT, env if env is not None else ENV)


def close(a, b, tol=TOL):
    return all(
        abs(a[i][j] - b[i][j]) < tol for i in range(len(a)) for j in range(len(a[0]))
    )


def ident(n):
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


class TestAxioms(unittest.TestCase):
    """(E1), (E2), (E3) -- the three equations that make the model quantum."""

    def test_e1_omega_is_an_eighth_root_of_unity(self):
        t = parse_term(" ; ".join(["omega"] * 8))
        self.assertAlmostEqual(column(t, UNIT).get(UNIT, 0), 1 + 0j, places=12)

    def test_e2_v_is_a_square_root_of_not(self):
        self.assertTrue(close(matrix(parse_term("v ; v"), BIT), X_M))

    def test_e3_picks_the_right_square_root(self):
        # v ; S ; v  =  omega^2 . (S ; v ; S),  with  S = id + omega^2.
        left = matrix(parse_term("v ; (id + (omega ; omega)) ; v"), BIT)
        right = matrix(parse_term("(id + (omega ; omega)) ; v ; (id + (omega ; omega))"), BIT)
        w2 = OMEGA * OMEGA
        self.assertTrue(close(left, [[w2 * z for z in row] for row in right]))

    def test_v_squares_to_x_as_a_matrix(self):
        v2 = [
            [sum(V_MATRIX[i][k] * V_MATRIX[k][j] for k in range(2)) for j in range(2)]
            for i in range(2)
        ]
        self.assertTrue(close(v2, X_M))


class TestDerivedGates(unittest.TestCase):
    def test_hadamard_is_exact_with_no_residual_phase(self):
        # H = omega . (X S V S X).  If the scalar were wrong this would still be
        # H up to a phase, so the equality is the interesting part.
        self.assertTrue(close(mat("h"), H_EXPECTED))

    def test_h_twice_is_the_identity(self):
        self.assertTrue(close(mat("hh"), I2))
        self.assertTrue(close(matrix(parse_term("h ; h"), BIT, ENV), I2))

    def test_s_squared_is_z_and_t_squared_is_s(self):
        self.assertTrue(close(matrix(parse_term("s ; s"), BIT, ENV), mat("z")))
        self.assertTrue(close(matrix(parse_term("t ; t"), BIT, ENV), mat("s")))

    def test_t_is_the_pi_over_four_phase(self):
        self.assertTrue(close(mat("t"), [[1, 0], [0, cmath.exp(1j * cmath.pi / 4)]]))

    def test_lemma_11(self):
        self.assertTrue(close(matrix(parse_term("h ; x ; h"), BIT, ENV), Z_M))
        self.assertTrue(close(matrix(parse_term("h ; z ; h"), BIT, ENV), X_M))

    def test_x_is_pauli_x(self):
        self.assertTrue(close(mat("x"), X_M))


class TestClassicalGatesStayClassical(unittest.TestCase):
    """`omega` and `v` buy nothing classical; `dist` was always enough."""

    def bits(self, v):
        return bits_of(v)

    def perm(self, name, basis):
        out = {}
        for b in basis:
            col = column(Ref(name), b, ENV)
            self.assertEqual(len(col), 1, f"{name} is not a permutation at {b!r}")
            (w, amp), = col.items()
            self.assertAlmostEqual(amp, 1 + 0j, places=12)
            out[self.bits(b)] = self.bits(w)
        return out

    def test_cx(self):
        self.assertEqual(
            self.perm("cx", TWO),
            {"00": "00", "01": "01", "10": "11", "11": "10"},
        )

    def test_ccx_is_the_toffoli(self):
        p = self.perm("ccx", THREE)
        self.assertEqual(p["110"], "111")
        self.assertEqual(p["111"], "110")
        for b in ["000", "001", "010", "011", "100", "101"]:
            self.assertEqual(p[b], b)

    def test_cswap_is_the_fredkin(self):
        p = self.perm("cswap", THREE)
        self.assertEqual(p["101"], "110")
        self.assertEqual(p["110"], "101")
        for b in ["000", "001", "010", "011", "100", "111"]:
            self.assertEqual(p[b], b)

    def test_ncx_fires_on_zero(self):
        self.assertEqual(
            self.perm("ncx", TWO),
            {"00": "01", "01": "00", "10": "10", "11": "11"},
        )


class TestUnitarity(unittest.TestCase):
    """Q42.md section 5: every term is unitary by construction.

    The argument is that the generators are unitary and that composition, direct
    sum, tensor and adjoint all preserve unitarity.  This audits it.
    """

    def test_every_definition_in_the_library(self):
        schemes, errors = infer_all(ENV)
        self.assertEqual(errors, {})
        checked = 0
        for name, body in ENV.items():
            for n in (None, 1, 2, 3):
                try:
                    basis = basis_of(ground(schemes[name], n).dom)
                except Rel42Error:
                    continue  # not enumerable, or not a gate on n qubits
                if not basis:
                    continue
                with self.subTest(defn=name, qubits=n):
                    m = matrix(Seq(body, dagger(body)), basis, ENV)
                    self.assertTrue(
                        close(m, ident(len(basis))),
                        f"{name} ; {name}! is not the identity at {len(basis)} dims",
                    )
                checked += 1
        self.assertGreater(checked, 40)

    def test_the_generators_themselves(self):
        self.assertTrue(close(matrix(parse_term("v ; v!"), BIT), I2))
        self.assertAlmostEqual(
            column(parse_term("omega ; omega!"), UNIT).get(UNIT, 0), 1 + 0j, places=12
        )


class TestInterferenceAndEntanglement(unittest.TestCase):
    """What the Boolean semiring cannot express."""

    def test_paths_cancel(self):
        plus = column(Ref("h"), ZERO, ENV)
        self.assertEqual(len(plus), 2)
        back = apply_vec(Ref("h"), plus, ENV)
        # The |1> amplitudes cancelled.  Over B they would have unioned.
        self.assertEqual(len(back), 1)
        self.assertAlmostEqual(back[ZERO], 1 + 0j, places=12)

    def test_bell_state(self):
        out = column(Ref("bell"), ket("00"), ENV)
        self.assertEqual(set(out), {ket("00"), ket("11")})
        for z in out.values():
            self.assertAlmostEqual(abs(z), 2**-0.5, places=12)

    def test_ghz_state(self):
        out = column(Ref("ghz"), ket("000"), ENV)
        self.assertEqual(set(out), {ket("000"), ket("111")})

    def test_apply_vec_is_needed_for_entanglement(self):
        # cx applied to |+>|0> is entangled, and there is no way to reach it by
        # applying cx at a basis index: a basis value is always a product state.
        plus = column(Ref("h"), ZERO, ENV)
        psi = {Pair(k, ZERO): z for k, z in plus.items()}
        out = apply_vec(Ref("cx"), psi, ENV)
        self.assertEqual(set(out), {ket("00"), ket("11")})

    def test_a_bell_state_is_not_a_product_state(self):
        out = column(Ref("bell"), ket("00"), ENV)
        # For a product state the 2x2 amplitude matrix has determinant zero.
        a = {(bits_of(v)): z for v, z in out.items()}
        det = a.get("00", 0) * a.get("11", 0) - a.get("01", 0) * a.get("10", 0)
        self.assertGreater(abs(det), 0.4)


class TestTheDaggerLaw(unittest.TestCase):
    """`<x|P|y> = conj(<y|P!|x>)` -- 42's defining law with `in` become `=`."""

    def test_over_the_library(self):
        schemes, _ = infer_all(ENV)
        checked = 0
        for name, body in ENV.items():
            for n in (None, 2, 3):
                try:
                    basis = basis_of(ground(schemes[name], n).dom)
                except Rel42Error:
                    continue  # not enumerable, or not a gate on n qubits
                if not basis:
                    continue
                for x in basis:
                    fwd = column(body, x, ENV)
                    for y, amp in fwd.items():
                        back = column(dagger(body), y, ENV).get(x, 0)
                        with self.subTest(defn=name, x=bits_of(x)):
                            self.assertAlmostEqual(back, amp.conjugate(), places=12)
                        checked += 1
                break
        self.assertGreater(checked, 50)

    def test_the_type_level_shadow_still_holds(self):
        # Now over combinators too: `Scheme.swap` inverts the result and leaves
        # the parameters alone, matching what `core.dagger` does to a `Fun`.
        schemes, _ = infer_all(SRC)
        combinators = 0
        for name, body in SRC.items():
            s, d = infer(body, schemes), infer(dagger(body), schemes)
            combinators += bool(s.params)
            with self.subTest(defn=name):
                self.assertEqual(q42.show_scheme(s.swap()), q42.show_scheme(d))
        self.assertGreater(combinators, 1, "no combinators were exercised")


class TestRejections(unittest.TestCase):
    """What Q42 refuses, and whether it says why."""

    def test_union_needs_an_idempotent_semiring(self):
        with self.assertRaises(Q42Error) as cm:
            q42.validate(parse_term("id | id"))
        self.assertIn("2f", str(cm.exception))

    def test_star_needs_an_idempotent_semiring(self):
        with self.assertRaises(Q42Error) as cm:
            q42.validate(parse_term("swapsum^"))
        self.assertIn("1 + 1 = 1", str(cm.exception))

    def test_the_dropped_primitives_are_named_with_a_reason(self):
        for name in ["copy", "join", "inl", "inr", "zero"]:
            with self.subTest(prim=name):
                with self.assertRaises(Q42Error) as cm:
                    q42.validate(parse_term(name))
                msg = str(cm.exception)
                self.assertIn(name, msg)
                self.assertIn("Q42 does not have", msg)
                # every one gives an actual reason, not just a refusal
                self.assertGreater(len(msg.split(":")[-1].strip()), 20)

    def test_copy_is_explained_as_non_surjective_not_as_no_cloning(self):
        # The precise reason matters: copy is a legitimate isometry that copies
        # basis states, i.e. a measurement basis, not an illegal cloner.
        with self.assertRaises(Q42Error) as cm:
            q42.validate(parse_term("copy"))
        self.assertIn("surjection", str(cm.exception))

    def test_they_are_not_in_the_primitive_tables(self):
        for name in ["copy", "join", "inl", "inr", "zero"]:
            self.assertNotIn(name, PRIMS)
            self.assertNotIn(name, PRIM_SCHEMES)

    def test_the_two_generators_are_present(self):
        for name in ["omega", "v"]:
            self.assertIn(name, PRIMS)
            self.assertIn(name, PRIM_SCHEMES)


class TestTypes(unittest.TestCase):
    def test_the_whole_library_types(self):
        schemes, errors = infer_all(ENV)
        self.assertEqual(errors, {})
        self.assertEqual(set(schemes), set(ENV))

    def test_the_generators_are_monomorphic(self):
        # 42 has no monomorphic primitive at all; both of Q42's new ones are.
        self.assertEqual(free_vars(PRIM_SCHEMES["omega"].dom), set())
        self.assertEqual(free_vars(PRIM_SCHEMES["v"].dom), set())
        self.assertEqual(q42.show_scheme(PRIM_SCHEMES["v"]), "1 + 1 <-> 1 + 1")

    def test_hadamard_is_forced_to_one_qubit_by_v(self):
        schemes, _ = infer_all(ENV)
        self.assertEqual(q42.show_scheme(schemes["h"]), "1 + 1 <-> 1 + 1")

    def test_a_controlled_target_must_be_a_symmetric_sum(self):
        # cx negates its target, which forces both summands equal -- the
        # type-level content of "that argument is a bit".
        schemes, _ = infer_all(ENV)
        self.assertEqual(
            q42.show_scheme(schemes["cx"]),
            "(1 + 1) x (a + a) <-> (1 + 1) x (a + a)",
        )

    def test_an_ill_shaped_term_is_rejected(self):
        # omega is a scalar on the unit; handing it a pair is exactly the typo
        # that would silently produce a non-unitary zero column.
        defs = parse_program("def bad = swapprod ; omega\n")
        _, errors = infer_all(defs)
        self.assertIn("bad", errors)

    def test_basis_enumeration(self):
        self.assertEqual(basis_of(TOne()), [UNIT])
        self.assertEqual(basis_of(QUBIT), [ZERO, ONE])
        self.assertEqual(len(basis_of(qubits(3))), 8)
        self.assertEqual(basis_of(rel42.types.TZero()), [])

    def test_it_refuses_what_it_cannot_enumerate(self):
        with self.assertRaises(Q42Error) as cm:
            basis_of(TVar(0))
        self.assertIn("polymorphic", str(cm.exception))
        with self.assertRaises(Q42Error):
            basis_of(rel42.types.TMu(1, TSum(TOne(), TVar(1))))

    def test_grounding_at_one_makes_a_qubit(self):
        # x = swapsum : a + b <-> b + a, and a qubit is what you get at a = b = 1.
        schemes, _ = infer_all(ENV)
        self.assertEqual(q42.show_scheme(ground(schemes["x"])), "1 + 1 <-> 1 + 1")

    def test_grounding_at_n_qubits_uses_unification(self):
        schemes, _ = infer_all(ENV)
        at3 = ground(schemes["cswap"], 3)
        self.assertEqual(len(basis_of(at3.dom)), 8)


class TestKetSyntax(unittest.TestCase):
    def test_round_trip(self):
        for bits in ["0", "1", "01", "110", "1010"]:
            with self.subTest(bits=bits):
                self.assertEqual(bits_of(ket(bits)), bits)

    def test_registers_nest_to_the_right(self):
        self.assertEqual(ket("01"), Pair(ZERO, ONE))
        self.assertEqual(ket("011"), Pair(ZERO, Pair(ONE, ONE)))

    def test_parse_state_accepts_both_forms(self):
        self.assertEqual(parse_state("|01>"), {ket("01"): 1 + 0j})
        self.assertEqual(parse_state("01"), {ket("01"): 1 + 0j})

    def test_parse_state_falls_back_to_42_values(self):
        self.assertEqual(parse_state("(L (), R ())"), {ket("01"): 1 + 0j})

    def test_show_ket_of_a_superposition(self):
        out = show_ket(column(Ref("bell"), ket("00"), ENV))
        self.assertIn("|00>", out)
        self.assertIn("|11>", out)
        self.assertIn("+", out)

    def test_show_ket_of_the_zero_vector(self):
        self.assertIn("zero vector", show_ket({}))

    def test_a_non_register_value_still_prints(self):
        self.assertIsNone(bits_of(UNIT))
        self.assertIn("()", show_ket({UNIT: 1 + 0j}))


class TestSharedWithRel42(unittest.TestCase):
    """Q42 is a sibling of rel42, not a fork of it.

    Q42.md section 10.1 argued for sharing the parser, values, terms, `dagger`
    and the type engine while forking only the evaluator and primitive table.
    These assert that the sharing is real rather than aspirational.
    """

    def test_dagger_is_literally_rel42s(self):
        self.assertIs(q42.dagger, rel42.dagger)

    def test_values_are_rel42s(self):
        self.assertIs(type(ZERO), Inl)
        self.assertIsInstance(ket("01"), Pair)

    def test_the_parser_is_rel42s_with_a_different_primitive_set(self):
        import rel42.syntax

        # Same function, different `prims` argument -- `v` is a Q42 primitive and
        # a mere reference to 42.
        self.assertIsInstance(parse_term("v"), rel42.core.Prim)
        self.assertIsInstance(rel42.syntax.parse_term("v"), rel42.core.Ref)

    def test_the_inference_engine_is_rel42s(self):
        import rel42.types

        s = infer(parse_term("swapprod"))
        self.assertEqual(q42.show_scheme(s), "a x b <-> b x a")
        # The very same engine, given the other table, still knows 42's copy.
        self.assertEqual(
            rel42.types.show_scheme(
                rel42.types.infer_term(rel42.syntax.parse_term("copy"), {})
            ),
            "a <-> a x a",
        )

    def test_q42_does_not_disturb_rel42(self):
        # Importing q42 must not mutate 42's primitive table, which is what the
        # spike had to do and a real module must not.
        self.assertNotIn("omega", rel42.core.PRIMS)
        self.assertNotIn("v", rel42.core.PRIMS)
        self.assertNotIn("omega", rel42.types.PRIM_SCHEMES)


class TestFibonacci(unittest.TestCase):
    """q42/fib.42 -- Fibonacci mod 4 as a unitary on two 2-bit registers.

    The point of the file is what it *cannot* be: PisoLang's
    `fib : nat <-> nat * nat` is impossible here, because `succ` is `inr`, which
    on `nat` is injective but not surjective -- the unilateral shift, an isometry
    that is not a unitary.  Fixing the register width and working mod 2^n is what
    makes the recurrence a permutation, hence expressible.
    """

    FIB = os.path.join(os.path.dirname(GATES), "fib.42")

    @classmethod
    def setUpClass(cls):
        with open(cls.FIB, encoding="utf-8") as fh:
            cls.src = parse_program(fh.read())
        cls.env = expand_env(cls.src)

    @staticmethod
    def enc(x, y):
        return ket(f"{x & 1}{(x >> 1) & 1}{y & 1}{(y >> 1) & 1}")

    @staticmethod
    def dec(v):
        b = bits_of(v)
        return (int(b[0]) + 2 * int(b[1]), int(b[2]) + 2 * int(b[3]))

    def one(self, name, v):
        col = column(Ref(name), v, self.env)
        self.assertEqual(len(col), 1, f"{name} is not a permutation at {v!r}")
        (out, amp), = col.items()
        self.assertAlmostEqual(amp, 1 + 0j, places=12)
        return out

    def test_the_obstruction_is_real(self):
        # succ has no Q42 term, and nat has no basis.
        with self.assertRaises(Q42Error):
            q42.validate(parse_term("inr"))
        import rel42.types as rt

        with self.assertRaises(Q42Error):
            basis_of(rt.TMu(1, rt.TSum(TOne(), rt.TVar(1))))

    def test_add4_is_addition_mod_four(self):
        for x in range(4):
            for y in range(4):
                with self.subTest(x=x, y=y):
                    out = self.one("add4", self.enc(x, y))
                    self.assertEqual(self.dec(out), (x, (x + y) % 4))

    def test_swapregs_swaps_the_registers(self):
        for x in range(4):
            for y in range(4):
                with self.subTest(x=x, y=y):
                    out = self.one("swapregs", self.enc(x, y))
                    self.assertEqual(self.dec(out), (y, x))

    def test_it_generates_the_fibonacci_numbers_mod_four(self):
        fibs = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        v = self.enc(0, 1)
        for i, f in enumerate(fibs):
            with self.subTest(step=i):
                a, b = self.dec(v)
                self.assertEqual(a, f % 4, f"step {i} holds {a}, want F_{i}={f} mod 4")
            v = self.one("fib", v)

    def test_the_step_is_a_unitary_on_sixteen_dimensions(self):
        schemes, errors = infer_all(self.env)
        self.assertEqual(errors, {})
        basis = basis_of(ground(schemes["fib"], 4).dom)
        self.assertEqual(len(basis), 16)
        m = matrix(Seq(self.env["fib"], dagger(self.env["fib"])), basis, self.env)
        self.assertTrue(close(m, ident(16)))

    def test_it_runs_backwards_exactly(self):
        # Not "returns a set containing the seed" -- returns the seed.
        v = self.enc(0, 1)
        for _ in range(7):
            v = self.one("fib", v)
        for _ in range(7):
            col = column(dagger(Ref("fib")), v, self.env)
            (v, _), = col.items()
        self.assertEqual(self.dec(v), (0, 1))

    def test_its_order_is_the_pisano_period(self):
        # pi(4) = 6.
        v = start = self.enc(0, 1)
        for n in range(1, 40):
            v = self.one("fib", v)
            if v == start:
                self.assertEqual(n, 6)
                return
        self.fail("fib did not return to the seed within 40 steps")

    def test_a_superposed_seed_advances_both_orbits(self):
        psi = column(Ref("qfib"), self.enc(1, 0), self.env)
        self.assertEqual(len(psi), 2)
        self.assertEqual({self.dec(v) for v in psi}, {(0, 1), (1, 2)})
        for z in psi.values():
            self.assertAlmostEqual(abs(z), 2**-0.5, places=12)
        # Six more steps and the superposition is back where it started.
        for _ in range(6):
            psi = apply_vec(Ref("fib"), psi, self.env)
        self.assertEqual({self.dec(v) for v in psi}, {(0, 1), (1, 2)})


class TestDeutsch(unittest.TestCase):
    """q42/deutsch.42 -- the smallest algorithm that beats its classical rival.

    QMANUAL section 9 answers "what use is a language that cannot measure?" partly
    with this file, so the claim it rests on is checked: after one oracle query
    the first qubit is |0> for a constant f and |1> for a balanced one, with
    certainty and with no sampling.
    """

    CONSTANT = ["d0", "d1"]
    BALANCED = ["did", "dnot"]

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(GATES), "deutsch.42")
        with open(path, encoding="utf-8") as fh:
            cls.src = parse_program(fh.read())
        cls.env = expand_env(cls.src)

    def first_qubit(self, name):
        """The first qubit of the output, if every term agrees on it."""
        out = column(Ref(name), ket("01"), self.env)
        firsts = {bits_of(v)[0] for v in out}
        self.assertEqual(len(firsts), 1, f"{name} leaves the first qubit undecided")
        return firsts.pop()

    def test_a_constant_oracle_leaves_the_first_qubit_at_zero(self):
        for name in self.CONSTANT:
            with self.subTest(oracle=name):
                self.assertEqual(self.first_qubit(name), "0")

    def test_a_balanced_oracle_leaves_the_first_qubit_at_one(self):
        for name in self.BALANCED:
            with self.subTest(oracle=name):
                self.assertEqual(self.first_qubit(name), "1")

    def test_the_answer_is_certain_not_probable(self):
        """The amplitudes on the wrong answer cancel exactly, not approximately."""
        for name in self.CONSTANT + self.BALANCED:
            with self.subTest(circuit=name):
                out = column(Ref(name), ket("01"), self.env)
                total = sum(abs(z) ** 2 for z in out.values())
                self.assertAlmostEqual(total, 1.0, places=12)
                self.assertEqual(len(out), 2, "two terms, differing only in qubit 2")

    def test_the_oracles_really_compute_those_four_functions(self):
        """(x, y) -> (x, y XOR f(x)) for each of the four one-bit functions."""
        for name, f in [("orc0", lambda b: 0), ("orc1", lambda b: 1),
                        ("orcid", lambda b: b), ("orcnot", lambda b: 1 - b)]:
            for xb in (0, 1):
                for yb in (0, 1):
                    with self.subTest(oracle=name, x=xb, y=yb):
                        out = column(Ref(name), ket(f"{xb}{yb}"), self.env)
                        (v, amp), = out.items()
                        self.assertAlmostEqual(amp, 1 + 0j, places=12)
                        self.assertEqual(bits_of(v), f"{xb}{yb ^ f(xb)}")

    def test_one_query_is_all_it_uses(self):
        """Each circuit names its oracle exactly once -- that is the whole point."""
        from rel42.types import references

        for name, oracle in zip(self.CONSTANT + self.BALANCED,
                                ["orc0", "orc1", "orcid", "orcnot"]):
            with self.subTest(circuit=name):
                self.assertIn(oracle, references(self.src[name]))

    def test_everything_in_the_file_is_unitary(self):
        schemes, errors = infer_all(self.env)
        self.assertEqual(errors, {})
        for name, body in self.env.items():
            try:
                basis = basis_of(ground(schemes[name], 2).dom)
            except Rel42Error:
                continue
            with self.subTest(defn=name):
                m = matrix(Seq(body, dagger(body)), basis, self.env)
                self.assertTrue(close(m, ident(len(basis))))


class TestMeasurement(unittest.TestCase):
    """Terminal measurement -- the Born rule, and nothing else.

    The design point being protected: measurement is *not* a term. It operates on
    a state a program already produced, so no constructor was added, `dagger` is
    untouched, and every term is still unitary. `test_it_is_not_a_term` asserts
    exactly that.
    """

    def test_it_is_not_a_term(self):
        """No new syntax, so the language's central property is unaffected."""
        from rel42.core import PRIMS as REL_PRIMS

        self.assertNotIn("measure", PRIMS)
        self.assertNotIn("measure", PRIM_SCHEMES)
        self.assertNotIn("sample", PRIMS)
        self.assertNotIn("measure", REL_PRIMS)
        with self.assertRaises(Rel42Error):
            infer(parse_term("measure"))

    def test_probabilities_are_the_squared_amplitudes(self):
        st = column(Ref("bell"), ket("00"), ENV)
        probs = q42.probabilities(st)
        self.assertEqual({bits_of(v) for v in probs}, {"00", "11"})
        for p in probs.values():
            self.assertAlmostEqual(p, 0.5, places=12)

    def test_they_sum_to_one_for_every_gate(self):
        """Unitary maps preserve length, so this needs no renormalising."""
        schemes, _ = infer_all(ENV)
        checked = 0
        for name in ENV:
            if schemes[name].params:
                continue
            try:
                basis = basis_of(ground(schemes[name]).dom)
            except Rel42Error:
                continue
            if not basis:
                continue
            for b in basis:
                with self.subTest(gate=name):
                    total = sum(q42.probabilities(column(Ref(name), b, ENV)).values())
                    self.assertAlmostEqual(total, 1.0, places=12)
                checked += 1
        self.assertGreater(checked, 30)

    def test_a_certain_outcome_is_drawn_every_time(self):
        st = column(Ref("hh"), ZERO, ENV)
        drawn = q42.sample(st, 500, seed=0)
        self.assertEqual(len(drawn), 1)
        (v, n), = drawn.items()
        self.assertEqual(bits_of(v), "0")
        self.assertEqual(n, 500)

    def test_the_seed_makes_a_draw_reproducible(self):
        st = column(Ref("bell"), ket("00"), ENV)
        self.assertEqual(q42.sample(st, 200, seed=7), q42.sample(st, 200, seed=7))
        self.assertNotEqual(q42.sample(st, 200, seed=7), q42.sample(st, 200, seed=8))

    def test_a_draw_matches_the_distribution_it_came_from(self):
        st = column(Ref("bell"), ket("00"), ENV)
        drawn = q42.sample(st, 4000, seed=0)
        self.assertEqual(sum(drawn.values()), 4000)
        for n in drawn.values():
            self.assertLess(abs(n / 4000 - 0.5), 0.05, "far from the Born weights")

    def test_only_outcomes_with_amplitude_are_ever_drawn(self):
        """The Bell state must never yield 01 or 10, however many shots."""
        st = column(Ref("bell"), ket("00"), ENV)
        drawn = q42.sample(st, 2000, seed=3)
        self.assertEqual({bits_of(v) for v in drawn}, {"00", "11"})

    def test_the_zero_vector_has_nothing_to_measure(self):
        self.assertEqual(q42.probabilities({}), {})
        self.assertEqual(q42.sample({}, 10, seed=0), {})

    def test_a_marginal_sums_the_outcomes_that_agree(self):
        from q42.core import marginal

        st = column(Ref("ghz"), ket("000"), ENV)
        probs = q42.probabilities(st)
        # measuring only qubit 0 of the GHZ state: half 0, half 1
        one = marginal(probs, {0}, bits_of)
        self.assertEqual(set(one), {"0__", "1__"})
        for p in one.values():
            self.assertAlmostEqual(p, 0.5, places=12)
        # measuring qubits 0 and 2: they always agree, so 0_0 and 1_1 only
        two = marginal(probs, {0, 2}, bits_of)
        self.assertEqual(set(two), {"0_0", "1_1"})

    def test_deutsch_now_answers_its_question(self):
        """The point of adding this: a certain answer after one query."""
        from q42.core import marginal

        path = os.path.join(os.path.dirname(GATES), "deutsch.42")
        with open(path, encoding="utf-8") as fh:
            env = expand_env(parse_program(fh.read()))
        for name, expected in [("d0", "0"), ("d1", "0"),
                               ("did", "1"), ("dnot", "1")]:
            with self.subTest(circuit=name):
                probs = q42.probabilities(column(Ref(name), ket("01"), env))
                first = marginal(probs, {0}, bits_of)
                self.assertEqual(len(first), 1, "the answer should be certain")
                (key, p), = first.items()
                self.assertEqual(key[0], expected)
                self.assertAlmostEqual(p, 1.0, places=12)


class TestTeleportation(unittest.TestCase):
    """q42/teleport.42 -- the case against adding mid-circuit measurement.

    Teleportation is the textbook algorithm said to need measuring in the middle.
    By the principle of deferred measurement it does not, and QMANUAL section 9.2
    leans on that, so it is checked here rather than asserted.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(GATES), "teleport.42")
        with open(path, encoding="utf-8") as fh:
            cls.env = expand_env(parse_program(fh.read()))

    def test_the_whole_protocol_is_an_ordinary_unitary_term(self):
        """No measurement, no effect layer -- just a term like any other."""
        basis = basis_of(qubits(3))
        for name in ["tele", "check", "checkh"]:
            with self.subTest(circuit=name):
                body = self.env[name]
                m = matrix(Seq(body, dagger(body)), basis, self.env)
                self.assertTrue(close(m, ident(8)))

    def test_a_basis_state_arrives(self):
        for sent, expect in [("000", "0"), ("100", "1")]:
            with self.subTest(sent=sent):
                out = column(Ref("tele"), ket(sent), self.env)
                thirds = {bits_of(v)[2] for v in out}
                self.assertEqual(thirds, {expect}, "q2 did not receive the state")

    def test_a_superposition_with_a_phase_arrives_intact(self):
        """Prepare, teleport, un-prepare: q2 must return to |0> exactly."""
        from q42.core import marginal

        for name in ["checkh", "check"]:
            with self.subTest(circuit=name):
                probs = q42.probabilities(column(Ref(name), ket("000"), self.env))
                third = marginal(probs, {2}, bits_of)
                self.assertEqual(len(third), 1, "the outcome should be certain")
                (key, p), = third.items()
                self.assertEqual(key[2], "0")
                self.assertAlmostEqual(p, 1.0, places=12)

    def test_the_deferred_measurements_are_the_other_two_qubits(self):
        """Alice's four outcomes, still there, evenly weighted."""
        out = column(Ref("checkh"), ket("000"), self.env)
        self.assertEqual({bits_of(v) for v in out},
                         {"000", "010", "100", "110"})
        for z in out.values():
            self.assertAlmostEqual(abs(z), 0.5, places=12)


class TestCli(unittest.TestCase):
    def call(self, *argv):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        from q42.__main__ import main

        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue() + err.getvalue()

    def test_run(self):
        code, out = self.call("run", GATES, "bell", "|00>")
        self.assertEqual(code, 0)
        self.assertIn("|00>", out)
        self.assertIn("|11>", out)

    def test_unitary_over_the_library(self):
        code, out = self.call("unitary", GATES)
        self.assertEqual(code, 0)
        # The two skipped are `ctrl` and `nctrl`: a combinator has no matrix
        # until its argument is supplied.
        self.assertIn("24/26 unitary, 2 with no single matrix", out)

    def test_type_over_the_library(self):
        code, out = self.call("type", GATES)
        self.assertEqual(code, 0)
        self.assertIn("26/26 typed", out)

    def test_law(self):
        code, out = self.call("law", GATES, "h", "|0>")
        self.assertEqual(code, 0)
        self.assertIn("law holds", out)

    def test_matrix(self):
        code, out = self.call("matrix", GATES, "ccx")
        self.assertEqual(code, 0)
        self.assertIn("|110>", out)

    def test_qubits_flag(self):
        code, out = self.call("matrix", GATES, "cswap", "--qubits", "3")
        self.assertEqual(code, 0)
        self.assertIn("|111>", out)

    def test_sample(self):
        code, out = self.call("sample", GATES, "bell", "|00>", "-n", "50")
        self.assertEqual(code, 0)
        self.assertIn("50.0%", out)
        self.assertIn("50 shots", out)

    def test_sample_with_bits(self):
        code, out = self.call(
            "sample", os.path.join(os.path.dirname(GATES), "deutsch.42"),
            "dnot", "|01>", "--bits", "0",
        )
        self.assertEqual(code, 0)
        self.assertIn("|1_>", out)
        self.assertIn("100.0%", out)

    def test_bits_out_of_range_is_refused(self):
        code, out = self.call("sample", GATES, "h", "|0>", "--bits", "5")
        self.assertEqual(code, 1)
        self.assertIn("numbered 0 to 0", out)

    def test_a_bad_state_is_refused(self):
        code, out = self.call("run", GATES, "h", "|00>")
        self.assertEqual(code, 1)
        self.assertIn("not in the domain", out)


class TestGeneratedQFT(unittest.TestCase):
    """The circuit *family* generated by `qft.42`, which is a 42 program.

    Q42 has no loop, so `n |-> C_n` has to be computed somewhere else.  Here it
    is computed in 42, and these tests check what that buys: the emitted text is
    a Q42 term, the three-qubit member is the exact QFT, the four-qubit member is
    the approximation Q42's gate set forces, and the generator inverts.
    """

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(cls.ROOT, "tools"))
        import unquote as emitter

        cls.emitter = emitter
        with open(os.path.join(cls.ROOT, "qft.42"), encoding="utf-8") as fh:
            cls.host = expand_env(rel_parse_program(fh.read()))

    def emit(self, n: int) -> str:
        """The n-th member of the family, as Q42 source."""
        [value] = rel_run(self.host["aqft"], from_nat(n), self.host)
        return self.emitter.emit(value)

    def matrix_on(self, qubits: int):
        """Parse the member for that many qubits and evaluate it as a matrix."""
        src = self.emitter.PREAMBLE + f"\ndef main = {self.emit(qubits - 1)}\n"
        env = expand_env(parse_program(src))
        basis = [ZERO, ONE]
        for _ in range(qubits - 1):
            basis = [Pair(b, rest) for b in (ZERO, ONE) for rest in basis]
        return matrix(env["main"], basis, env)

    def test_the_cutoff_costs_more_at_every_extra_qubit(self):
        """`(n-3)(n-2)/2` rotations are dropped, so the error grows with width.

        `R_k` occurs `n-k+1` times in the n-qubit transform and everything past
        `R_3` is dropped, so the count is quadratic in the width.  The total
        dropped angle is what sets the fidelity, and it grows roughly linearly,
        which is why `cos(pi/16)` is a fact about *four* qubits and not about
        the truncation: past about six the generated member stops meaning
        anything.  Coppersmith's cutoff grows with the register to avoid exactly
        this; Q42's cannot, being where `omega` runs out rather than a choice.
        """
        for qubits in (3, 4, 5, 6, 7):
            with self.subTest(qubits=qubits):
                self.assertEqual(
                    dropped_rotations(self.emit(qubits - 1)),
                    (qubits - 3) * (qubits - 2) // 2 if qubits > 3 else 0,
                )

    def test_the_generated_text_is_what_the_recursion_says(self):
        self.assertEqual(self.emit(0), "h")
        self.assertEqual(self.emit(1), "((h * id) ; (ctrl (s) ; (id * h)))")

    def test_the_cutoff_appears_exactly_where_the_gate_set_ends(self):
        """R_4 needs a 16th root of unity; `omega` is an 8th.  So it is `id`."""
        self.assertIn("(s * t)", self.emit(2))          # three qubits: R_2, R_3
        self.assertIn("(s * (t * id))", self.emit(3))   # four: R_4 dropped

    def test_three_qubits_is_the_exact_qft(self):
        """Nothing is dropped below four qubits, so this is the QFT itself --
        with the output in reversed bit order, the usual no-final-swaps form."""
        m = self.matrix_on(3)
        w = cmath.exp(2j * cmath.pi / 8)
        rev = [int(format(k, "03b")[::-1], 2) for k in range(8)]
        worst = max(
            abs(m[i][j] - w ** (rev[i] * j) / cmath.sqrt(8))
            for i in range(8)
            for j in range(8)
        )
        self.assertLess(worst, 1e-12)

    def test_four_qubits_is_the_approximation_and_still_unitary(self):
        """The fidelity is `cos(pi/16)`, and that is forced rather than measured.

        `R_4` occurs once in the four-qubit transform and is the one rotation
        dropped, so the approximation replaces a phase of `pi/8` by nothing.  A
        unitary whose eigenvalues span an arc `theta` has worst-case overlap
        `cos(theta/2)`, so the answer is `cos(pi/16)` exactly -- `pi/8` being the
        angle `omega` cannot name.  Asserting the closed form rather than a bound
        of 0.98 is the difference between checking the number and checking the
        reason: a change to the truncation rule would still clear the bound.
        """
        m = self.matrix_on(4)
        w = cmath.exp(2j * cmath.pi / 16)
        rev = [int(format(k, "04b")[::-1], 2) for k in range(16)]
        fidelity = min(
            abs(sum(m[i][j].conjugate() * w ** (rev[i] * j) / 4 for i in range(16)))
            for j in range(16)
        )
        self.assertAlmostEqual(fidelity, cmath.cos(cmath.pi / 16).real, places=12)
        self.assertLess(fidelity, 1.0)                  # it really is approximate
        for j in range(16):                             # and still an isometry
            self.assertAlmostEqual(
                sum(abs(m[i][j]) ** 2 for i in range(16)), 1.0, places=10
            )

    def test_the_generator_inverts(self):
        """`aqft!` reads a circuit back to the width that produced it.  No other
        host can do this: a Python function has no converse."""
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(100000)
        try:
            [circuit] = rel_run(self.host["aqft"], from_nat(2), self.host)
            back = rel_run(
                dagger(Ref("aqft")), circuit, self.host, max_depth=2000
            )
        finally:
            sys.setrecursionlimit(old)
        self.assertEqual(back, {from_nat(2)})


def dropped_rotations(src: str) -> int:
    """`id` occurrences inside the `ctrl (...)` fan-outs of a generated QFT.

    Each one is a rotation the gate set could not name, left as the identity.
    Counted from the emitted text rather than the term, because `expand_env`
    inlines `ctrl` and the shape is gone by then.
    """
    total, i = 0, 0
    while (i := src.find("ctrl (", i)) != -1:
        j, depth = i + 5, 0
        while True:
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        total += src.count("id", i, j)
        i = j
    return total


class TestExactAmplitudes(unittest.TestCase):
    """Amplitudes are elements of `Z[1/sqrt2, i]`, not doubles that resemble them.

    Every amplitude a Q42 program can produce is built from 0, 1, `omega` and
    `v`, so all of them lie in that ring, which is countable and has decidable
    equality.  These tests are the difference between saying so and doing it.
    """

    def test_the_ring_agrees_with_complex_arithmetic(self):
        """Randomised, because the reduction step is where a bug would hide."""
        import random

        rng = random.Random(20260826)
        w = cmath.exp(1j * cmath.pi / 4)

        def rand():
            return Exact(*[rng.randint(-6, 6) for _ in range(4)],
                         k=rng.randint(0, 5))

        for _ in range(2000):
            x, y = rand(), rand()
            cx, cy = complex(x), complex(y)
            for got, want in ((x + y, cx + cy), (x - y, cx - cy),
                              (x * y, cx * cy),
                              (x.conjugate(), cx.conjugate())):
                self.assertAlmostEqual(complex(got), want, places=9)

    def test_the_reduced_form_is_canonical(self):
        """Equal values have equal representations, which is why `==` decides."""
        import random

        rng = random.Random(11)
        for _ in range(2000):
            n = [rng.randint(-4, 4) for _ in range(4)]
            k = rng.randint(0, 4)
            x = Exact(*n, k=k)
            # The same number written with a bigger denominator: multiply the
            # numerator by sqrt2 = w - w^3 and add one to k.
            a, b, c, d = n
            y = Exact(b - d, a + c, b + d, c - a, k=k + 1)
            self.assertEqual(x, y)
            self.assertEqual((x.n, x.k), (y.n, y.k))

    def test_omega_has_order_exactly_eight(self):
        """QMANUAL section 6.1's claim, decided rather than approximated."""
        powers = [OMEGA ** i for i in range(1, 9)]
        self.assertEqual(powers[-1], 1)
        for i, p in enumerate(powers[:-1], start=1):
            self.assertNotEqual(p, 1, f"omega^{i} should not be the identity")

    def test_root_two_squares_to_two(self):
        self.assertEqual(ROOT2 * ROOT2, 2)

    def test_v_is_the_matrix_it_always_was(self):
        want = [[(-1 + 1j) / 2, (-1 - 1j) / 2], [(-1 - 1j) / 2, (-1 + 1j) / 2]]
        for i in range(2):
            for j in range(2):
                self.assertIsInstance(V_MATRIX[i][j], Exact)
                self.assertAlmostEqual(complex(V_MATRIX[i][j]), want[i][j],
                                       places=12)

    def test_no_float_reaches_the_evaluator(self):
        """The claim that makes the rest of this class worth anything.

        If any primitive still handed back a `complex`, one product would drag a
        whole matrix out of the ring and nothing above would be checking the
        thing it says it checks.
        """
        schemes, _ = infer_all(ENV)
        for name in sorted(schemes):
            try:
                b = basis_of(ground(schemes[name], 3).dom)
            except Rel42Error:
                continue  # a combinator, or not a gate at this width
            with self.subTest(gate=name):
                for row in matrix(Ref(name), b, ENV):
                    for z in row:
                        self.assertIsInstance(z, (Exact, int), f"{name} leaked {z!r}")

    def test_interference_cancels_to_nothing_at_all(self):
        """`h ; h = id`: the |1> amplitude is absent, not 1e-17."""
        col = column(parse_term("h ; h"), ZERO, ENV)
        self.assertEqual(col, {ZERO: 1})
        self.assertEqual(list(col.values()), [Exact(1)])

    def test_equality_of_two_spellings_is_decided(self):
        """Two terms, one matrix, and no tolerance anywhere in the comparison."""
        for left, right in [("z", "s ; s"), ("s", "t ; t"), ("x", "v ; v"),
                            ("h ; h", "id"), ("z ; z", "id")]:
            with self.subTest(claim=f"{left} = {right}"):
                b = basis_of(QUBIT)
                a = matrix(parse_term(left), b, ENV)
                c = matrix(parse_term(right), b, ENV)
                self.assertEqual(a, c)

    def test_the_ring_is_not_a_field(self):
        """Division leaves it, and `Exact` says so by handing back a complex."""
        self.assertIsInstance(OMEGA / 2, complex)


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main(verbosity=2)
