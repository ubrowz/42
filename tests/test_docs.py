"""Tests for the documentation.  Run with:  python3 tests/test_docs.py

Prose goes stale silently, which is worse than code going stale: a wrong claim
in a manual is believed. Three things are checked here, and each corresponds to
a mistake actually found in this repository:

* every result the manual claims is re-run (`tools/checkmanual.py`) -- because
  a hand-transcribed test drifts when the manual is edited;
* every command shown in a transcript is executed and its output compared --
  because `24/24 unitary` outlived the change that made it `24/26`;
* every section with a contents list lists all of its subsections -- because
  section 3.7 was invisible to anyone reading section 3's contents.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

DOCS = ["MANUAL.md", "QMANUAL.md", "README.md", "RELATED.md", "Q42.md", "THEOREM.md"]

#: Commands the docs show in order to display an error.  They are expected to
#: fail; what matters is that they still fail with the message shown.
EXPECTED_TO_FAIL = {
    "42 prelude swap 5",
    "42 q42/classical ctrl 3",
    '42q rejected bad "|0>"',
}


def env_with_root_on_path():
    e = dict(os.environ)
    e["PATH"] = str(ROOT) + os.pathsep + e.get("PATH", "")
    return e


def transcripts(text):
    """Each `$ command` in the text, with the output lines shown beneath it."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^\$ ((?:42q?|python3 -m \w+) .+)$", lines[i])
        if not m:
            i += 1
            continue
        cmd, i, expected = m.group(1), i + 1, []
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith("$ ")
            and not lines[i].startswith("```")
        ):
            expected.append(lines[i])
            i += 1
        yield cmd, expected


class TestManualClaims(unittest.TestCase):
    """`$ f applied to x -> y` and `$ f(x) = y`, re-run against the language."""

    def test_every_claim_holds(self):
        import checkmanual

        failures = []
        text = (ROOT / "MANUAL.md").read_text(encoding="utf-8")
        checked = 0
        for lineno, line in enumerate(text.split("\n"), 1):
            if not line.startswith("$ "):
                continue
            result = checkmanual.check(line.rstrip(), lineno)
            if result is None:
                continue
            checked += 1
            ok, detail = result
            if not ok:
                failures.append(f"MANUAL.md:{lineno}  {detail}")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))
        self.assertGreater(checked, 40, "the checker stopped recognising claims")

    def test_uncheckable_lines_are_only_cli_transcripts(self):
        """Nothing may quietly escape both harnesses."""
        import checkmanual

        text = (ROOT / "MANUAL.md").read_text(encoding="utf-8")
        for lineno, line in enumerate(text.split("\n"), 1):
            if not line.startswith("$ "):
                continue
            if checkmanual.check(line.rstrip(), lineno) is None:
                with self.subTest(line=lineno):
                    self.assertRegex(
                        line, r"^\$ (42q?|python3 -m) ",
                        "this line claims a result that neither harness checks",
                    )


class TestTranscripts(unittest.TestCase):
    """Every `$ 42 ...` block in every document, executed."""

    def run_doc(self, doc):
        env = env_with_root_on_path()
        text = (ROOT / doc).read_text(encoding="utf-8")
        seen = 0
        for cmd, expected in transcripts(text):
            seen += 1
            r = subprocess.run(
                cmd, shell=True, cwd=ROOT, capture_output=True, text=True, env=env
            )
            out = r.stdout + r.stderr
            with self.subTest(doc=doc, cmd=cmd):
                if cmd in EXPECTED_TO_FAIL:
                    self.assertNotEqual(r.returncode, 0, "this should still error")
                else:
                    self.assertEqual(r.returncode, 0, out)
                for line in expected:
                    shown = re.split(r"\s+--\s", line.strip())[0].strip()
                    if not shown or shown == "...":
                        continue
                    self.assertIn(shown, out, f"{cmd} no longer prints this")
        return seen

    def test_manual(self):
        self.assertGreater(self.run_doc("MANUAL.md"), 5)

    def test_qmanual(self):
        self.assertGreater(self.run_doc("QMANUAL.md"), 3)

    def test_readme(self):
        self.assertGreater(self.run_doc("README.md"), 3)

    def test_q42_design_note(self):
        self.assertGreater(self.run_doc("Q42.md"), 2)


class TestQManualNumbers(unittest.TestCase):
    """The arithmetic QMANUAL.md prints, checked against the real thing.

    Q42's manual differs from 42's in that most of its claims are *numeric*
    rather than transcripts — an interference table, a determinant, a period, a
    physical constant. None of that is covered by running a command, so each is
    parsed out of the document and recomputed here.
    """

    @classmethod
    def setUpClass(cls):
        # Module-level names, not class attributes: a plain function stored on a
        # class becomes a bound method and swallows its first argument.
        global Ref, column, ket, bits_of
        from rel42.core import Ref, expand_env

        from q42 import bits_of, column, ket, parse_program

        cls.text = (ROOT / "QMANUAL.md").read_text(encoding="utf-8")
        cls.gates = expand_env(parse_program((ROOT / "q42" / "gates.42").read_text()))
        cls.fib = expand_env(parse_program((ROOT / "q42" / "fib.42").read_text()))

    def test_the_interference_table_is_arithmetic_that_works(self):
        """Each `+a x +b = +c` line multiplies out, and the sums are the sums."""
        rows = re.findall(
            r"from \|(\d)> -> \|(\d)> :\s+([+-][\d.]+) x ([+-][\d.]+)\s+=\s+([+-][\d.]+)"
            r"(?:\s+sum:\s*([+-]?[\d.]+))?",
            self.text,
        )
        self.assertEqual(len(rows), 4, "the interference table changed shape")
        totals = {}
        for src, dst, a, b, prod, stated in rows:
            with self.subTest(route=f"{src}->{dst}"):
                self.assertAlmostEqual(float(a) * float(b), float(prod), places=3)
            totals.setdefault(dst, []).append(float(prod))
            if stated:
                with self.subTest(target=dst):
                    self.assertAlmostEqual(sum(totals[dst]), float(stated), places=3)
        # and the |1> column must cancel, which is the whole point of the section
        self.assertAlmostEqual(sum(totals["1"]), 0.0, places=3)

    def test_the_interference_amplitudes_are_the_real_ones(self):
        """0.7071 in that table is really H's entry, not a plausible number."""
        ZERO = ket("0")
        col = column(Ref("h"), ZERO, self.gates)
        for amp in col.values():
            self.assertAlmostEqual(abs(amp), 0.7071, places=4)
        back = column(Ref("hh"), ZERO, self.gates)
        self.assertEqual(len(back), 1, "hh|0> should be a single component")

    def test_the_phase_gates_are_the_subgroup_chain(self):
        """Section 6.2 says z, s and t generate the order 2, 4 and 8 subgroups.

        Computed in `q42.exact`, so "comes back to the identity" is an equality
        and not a distance under a tolerance -- which is the claim §6.2 is
        making about a *group*, and would be a weaker claim without it.
        """
        from q42.exact import ONE

        self.assertIn("three nontrivial subgroups", self.text)
        one = ket("1")
        for name, order in [("z", 2), ("s", 4), ("t", 8)]:
            with self.subTest(gate=name):
                # A phase gate fixes |0> and scales |1>, so the order of the
                # gate is the order of that one amplitude.
                phase = column(Ref(name), one, self.gates)[one]
                self.assertEqual(phase ** order, ONE,
                                 f"{name} should have order {order}")
                for i in range(1, order):
                    self.assertNotEqual(phase ** i, ONE,
                                        f"{name}^{i} is already the identity")

    def test_0_707107_really_is_one_over_root_two(self):
        self.assertIn("`0.707107` is `1/√2`", self.text)
        self.assertAlmostEqual(2 ** -0.5, 0.707107, places=6)

    def test_landauers_constant(self):
        import math

        self.assertIn("2.9 × 10⁻²¹", self.text)
        joules = 1.380649e-23 * 300 * math.log(2)
        self.assertAlmostEqual(joules / 1e-21, 2.9, places=1)

    def test_the_bell_determinant(self):
        """The manual computes 0.7071 x 0.7071 - 0 x 0 = 0.5; check both."""
        self.assertIn("0.7071 x 0.7071 - 0 x 0  =  0.5", self.text)
        out = column(Ref("bell"), ket("00"), self.gates)
        amp = {bits_of(v): z for v, z in out.items()}
        det = amp.get("00", 0) * amp.get("11", 0) - amp.get("01", 0) * amp.get("10", 0)
        self.assertAlmostEqual(det.real, 0.5, places=4)
        self.assertNotAlmostEqual(det.real, 0.0, places=4)  # i.e. entangled

    def test_the_fibonacci_matrix_determinant(self):
        self.assertIn("has determinant `−1`", self.text)
        self.assertEqual(0 * 1 - 1 * 1, -1)  # [[0,1],[1,1]]

    def test_the_fibonacci_table(self):
        """Every row of the step table, re-run."""
        rows = re.findall(
            r"^step\s+(\d+): register = \((\d+), (\d+)\)\s+F_(\d+)\s*= (\d+)",
            self.text, re.M,
        )
        self.assertEqual(len(rows), 4, "the Fibonacci table changed shape")
        fibs = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]

        def decode(v):
            b = bits_of(v)
            return (int(b[0]) + 2 * int(b[1]), int(b[2]) + 2 * int(b[3]))

        want = {int(step): (int(a), int(b)) for step, a, b, _, _ in rows}
        for step, _a, _b, idx, value in rows:
            with self.subTest(step=step):
                self.assertEqual(int(idx), int(step), "step and F index disagree")
                self.assertEqual(int(value), fibs[int(step)], "that is not F_step")
        v = ket("0010")  # the seed (0, 1)
        for step in range(11):
            if step in want:
                with self.subTest(step=step):
                    self.assertEqual(decode(v), want[step])
                    self.assertEqual(decode(v)[0], fibs[step] % 4)
            (v, _), = column(Ref("fib"), v, self.fib).items()

    def test_section_1s_grids_are_the_real_relations(self):
        """§1.1-1.2 draw four 42 programs as grids of marks. Check each cell."""
        from rel42 import run
        from rel42.core import Inl, Inr, UNIT
        from rel42.syntax import parse_term

        two, one = [Inl(UNIT), Inr(UNIT)], [UNIT]
        cases = [
            ("swapsum", two, two, [[0, 1], [1, 0]]),
            ("inl!",    two, one, [[1], [0]]),
            ("join!",   one, two, [[1, 1]]),
            ("join",    two, one, [[1], [1]]),
        ]
        for prog, dom, cod, want in cases:
            with self.subTest(program=prog):
                term = parse_term(prog)
                got = [[1 if c in run(term, d, {}) else 0 for c in cod] for d in dom]
                self.assertEqual(got, want, f"§1's grid for {prog} is wrong")
        # and `join` really is `join!` transposed, which is what §1.2 claims
        jb = [[1 if c in run(parse_term("join!"), d, {}) else 0 for c in two]
              for d in one]
        jf = [[1 if c in run(parse_term("join"), d, {}) else 0 for c in one]
              for d in two]
        self.assertEqual([list(r) for r in zip(*jb)], jf)

    def test_the_matrix_printer_puts_outputs_in_rows(self):
        """§1.4 warns that `42q matrix` is the transpose of §1.1's grids."""
        flat = re.sub(r"\s+", " ", self.text)
        self.assertIn("rows are outputs and its columns are inputs", flat)
        src = (
            "type qubit = 1 + 1\ndef x = swapsum\n"
            "def s = id + (omega ; omega)\ndef xs = x ; s\n"
        )
        from rel42.core import expand_env

        from q42 import matrix, parse_program

        env = expand_env(parse_program(src))
        m = matrix(Ref("xs"), [ket("0"), ket("1")], env)
        # x then s sends |0> to i|1>, so the i belongs at row |1>, column |0>
        self.assertAlmostEqual(abs(m[1][0]), 1.0, places=9)
        self.assertAlmostEqual(m[1][0].imag, 1.0, places=9)
        self.assertAlmostEqual(abs(m[0][1]), 1.0, places=9)
        self.assertAlmostEqual(m[0][1].imag, 0.0, places=9)

    def test_section_9_4s_primitive_classification(self):
        """Only `swapsum`, `omega` and `v` do anything to the bits."""
        from rel42.core import UNIT, Inl, Pair, Prim, Unit
        from rel42.types import TOne, TProd, TSum, TZero

        from q42.types import QUBIT, basis_of

        def flat(v):
            if isinstance(v, Unit):
                return ""
            if isinstance(v, Pair):
                return flat(v.a) + flat(v.b)
            tag = "0" if isinstance(v, Inl) else "1"
            return tag if isinstance(v.v, Unit) else tag + flat(v.v)

        Q = QUBIT
        structural = {
            "id": Q,
            "assocprod": TProd(Q, TProd(Q, Q)),
            "unitprod": TProd(TOne(), Q),
            "dist": TProd(Q, Q),
        }
        for name, dom in structural.items():
            with self.subTest(primitive=name):
                for b in basis_of(dom):
                    col = column(Prim(name), b, {})
                    self.assertEqual(len(col), 1)
                    (out, amp), = col.items()
                    self.assertEqual(flat(out), flat(b), f"{name} moved a bit")
                    self.assertAlmostEqual(amp, 1 + 0j, places=12)

        # `unitsum` is structural for a different reason: the tag it removes has
        # an uninhabited branch, so `0 + a` and `a` are the same dimension.
        self.assertEqual(len(basis_of(TSum(TZero(), Q))), len(basis_of(Q)))

        # and the three that are not structural really are not
        self.assertNotEqual(
            flat(next(iter(column(Prim("swapsum"), basis_of(Q)[0], {})))),
            flat(basis_of(Q)[0]),
        )
        self.assertEqual(len(column(Prim("v"), basis_of(Q)[0], {})), 2)
        self.assertNotAlmostEqual(
            column(Prim("omega"), UNIT, {})[UNIT], 1 + 0j, places=6
        )

    def test_section_9_4s_register_predicate(self):
        """The width rule accepts what §9.4 says it does, and rejects the rest."""
        from rel42.types import TMu, TOne, TProd, TSum, TVar, TZero

        from q42.types import QUBIT, qubits

        def width(t):
            match t:
                case TOne():
                    return 0
                case TProd(a, b):
                    wa, wb = width(a), width(b)
                    return None if wa is None or wb is None else wa + wb
                case TSum(a, b):
                    wa, wb = width(a), width(b)
                    if wa is None or wb is None or wa != wb:
                        return None
                    return 1 + wa
            return None

        self.assertEqual(width(QUBIT), 1)
        self.assertEqual(width(qubits(3)), 3)
        self.assertEqual(width(TSum(QUBIT, QUBIT)), 2, "a tag plus one qubit")
        self.assertIsNone(width(TSum(TOne(), QUBIT)), "dimension 3 is no register")
        self.assertIsNone(width(TZero()))
        self.assertIsNone(width(TVar(0)))
        self.assertIsNone(width(TMu(1, TSum(TOne(), TVar(1)))))

        # §9.4 claims every library definition already passes.
        from rel42.core import expand_env

        from q42 import parse_program
        from q42.types import ground, infer_all

        for lib, expected in [("gates", 24), ("fib", 15),
                              ("deutsch", 13), ("classical", 4)]:
            env = expand_env(parse_program(
                (ROOT / "q42" / f"{lib}.42").read_text(encoding="utf-8")))
            schemes, errors = infer_all(env)
            self.assertEqual(errors, {})
            shaped = 0
            for name, sch in schemes.items():
                if sch.params:
                    continue
                if width(ground(sch).dom) is not None:
                    shaped += 1
                else:
                    self.fail(f"q42/{lib}.42:{name} is not register-shaped")
            with self.subTest(library=lib):
                self.assertEqual(shaped, expected, "§9.4 states this count")

    def test_the_stated_period_is_the_order_of_fib(self):
        self.assertIn("Pisano period of 4", self.text)
        start = v = ket("0010")
        for n in range(1, 30):
            (v, _), = column(Ref("fib"), v, self.fib).items()
            if v == start:
                self.assertEqual(n, 6, "the manual says the period is 6")
                return
        self.fail("fib never returned to its seed")


class TestTheoremFigures(unittest.TestCase):
    """THEOREM.md 2.2 and 2.3 reproduce the implementation; check that they do.

    A paper's figures are the first thing to go stale, and these two are copies
    of `PRIM_SCHEMES` and `PRIMS`. The soundness proof in 2.5 argues case by case
    over exactly these, so a primitive added to the language and not to the
    figure would leave a proof with a missing case and nothing to notice it.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "THEOREM.md").read_text(encoding="utf-8")

    def test_the_typing_figure_is_the_checkers_own_output(self):
        from rel42.types import PRIM_SCHEMES, show_scheme

        for name, scheme in PRIM_SCHEMES.items():
            row = f"| `{name}` | `{show_scheme(scheme)}` |"
            with self.subTest(primitive=name):
                self.assertIn(row, self.text, f"section 2.2 does not match {name}")

    def test_the_semantics_figure_names_every_primitive_and_no_others(self):
        from rel42.core import PRIMS

        start = self.text.index("### 2.3 The denotation")
        figure = self.text[start:self.text.index("### 2.4")]
        named = set(re.findall(r"⟦(\w+)⟧", figure))
        combinators = {"t", "u"}          # the clauses for `t ; u` and friends
        self.assertEqual(
            named - combinators, set(PRIMS),
            "section 2.3 lists a different set of primitives than rel42.core",
        )

    def test_the_proof_covers_every_typing_rule(self):
        """Every rule named in 2.2's figure gets a case in 2.5's induction."""
        proof = self.text[self.text.index("*Proof.* Induction on the derivation."):]
        proof = proof[: proof.index("∎")]
        for rule in ["seq", "sum", "prod", "union", "star", "dagger"]:
            with self.subTest(rule=rule):
                self.assertIn(f"**{rule}.**", proof, f"no case for the {rule} rule")


class TestReadmeCounts(unittest.TestCase):
    """The numbers README.md states, recomputed.

    Every count in it was maintained by hand and at least one had already gone
    stale (it claimed 298 tests when there were 316). A number in prose that
    nothing checks is a number that is eventually wrong.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_the_library_definition_count(self):
        import glob

        from rel42 import parse_program

        total = sum(
            len(parse_program(pathlib.Path(f).read_text(encoding="utf-8")))
            for f in sorted(glob.glob(str(ROOT / "*.42")))
        )
        self.assertIn(f"All {total} definitions", self.text)
        self.assertIn(f"{total} definitions in the ten libraries", self.text)

    def test_the_per_suite_and_total_test_counts(self):
        # Counted by loading each module, not by running it: this file is one of
        # the four, and running it from inside itself does not terminate.
        import unittest as ut

        loader = ut.TestLoader()
        counts = {}
        for name in ["test_rel42", "test_types", "test_q42", "test_docs", "test_emit"]:
            counts[name] = loader.loadTestsFromName(name).countTestCases()

        for name, n in counts.items():
            with self.subTest(suite=name):
                self.assertRegex(
                    self.text, rf"tests/{name}\.py`?\s*\({n}\)",
                    f"README does not say {name} has {n} tests",
                )
        total = sum(counts.values())
        self.assertIn(f"{total} in", self.text, "the stated total is wrong")
        self.assertIn(f"{total} tests", self.text, "the layout's total is wrong")

    def test_the_primitive_count_in_the_manual(self):
        from rel42.core import PRIMS

        words = {12: "twelve", 13: "thirteen", 14: "fourteen"}
        manual = (ROOT / "MANUAL.md").read_text(encoding="utf-8")
        self.assertIn(f"only {words[len(PRIMS)]} primitives", manual)


class TestRelatedWorkQuotations(unittest.TestCase):
    """Every verbatim quotation in RELATED.md still appears in its source.

    RELATED.md is meant to become a paper's related-work section, and quotes its
    sources verbatim. A quotation that has drifted from its source would undo
    that, so the papers are read from `sources/` and the quotations are checked
    against them.
    """

    SOURCES = {
        "inv": "sources/inv.pdf",
        "piso": "sources/pisolang.pdf",
        "pi": "sources/pi-information-effects.pdf",
        "theseus": "sources/theseus.pdf",
        "chardonnet": "sources/chardonnet-fscd2024.pdf",
        "rfun": "sources/rfun.pdf",
        "janus": "sources/janus.pdf",
        "qeffect": "sources/quantum-effect.pdf",
        "onerig": "sources/one-rig.pdf",
        "lenses": "sources/lenses.pdf",
        "matsuda": "sources/matsuda-icfp2007.pdf",
        "bigul": "sources/bigul.pdf",
        "bancilhon": "sources/bancilhon.pdf",
        "silq": "sources/silq.pdf",
        "prolog": "sources/prolog-fifty-years.pdf",
        "minikanren": "sources/minikanren-quines.pdf",
        "backens": "sources/backens.pdf",
        "jeandel": "sources/jeandel.pdf",
        "coecke": "sources/coecke-duncan.pdf",
        "ngwang": "sources/ngwang.pdf",
        "hadzi": "sources/hadzihasanovic.pdf",
        "vilmart": "sources/vilmart.pdf",
        "wetering": "sources/wetering.pdf",
    }

    #: (source, the quoted fragment).  Short, distinctive substrings rather than
    #: whole sentences, so that line-wrapping in the PDF cannot cause a spurious
    #: failure.
    QUOTES = [
        ("prolog", "one can check if a logic solver can be considered as a Prolog system"),
        ("prolog", "deconstruct a list as in"),
        ("prolog", "with any arbitrary instantiation of the arguments"),
        ("prolog", "allowing programmers to write truly reversible predicates"),
        ("minikanren", "We present relational interpreters for several subsets of"),
        ("minikanren", "generating programs that evaluate"),
        ("minikanren", "trivially generate quines"),
        ("silq", "the first quantum language that addresses this challenge"),
        ("silq", "safe, automatic uncomputation"),
        ("bancilhon", "the database could be computed from the view and its complement"),
        ("bancilhon", "a view can have many different complements"),
        ("bancilhon", "the choice of a complement determines an update policy"),
        ("bancilhon", "constant complement is the only method of translation"),
        ("lenses", "the putback function must capture all of the information"),
        ("lenses", "there are many ways to equip a given get function with a putback"),
        ("lenses", "we need some means of specifying which putback is intended"),
        ("lenses", "onerous proof obligations or checking of side conditions"),
        ("lenses", "update translation under a constant complement"),
        ("matsuda", "a view complement function of f is a function from the source to"),
        ("bigul", "uniquely determines its get component"),
        ("bigul", "ensuring the well-behavedness of a put"),
        ("inv", "we require not only the domains, but the ranges of"),
        ("inv", "may be checked by a type system, but we have not explored"),
        ("inv", "lets it go through only if the two components are equal"),
        ("inv", "we have to perform an equality test"),
        ("inv", "necessary for ensuring the disjointness of the two branches"),
        ("piso", "in order to make the function injective"),
        ("piso", "linear context, and that isos are typed without"),
        ("piso", "hard to express, despite being the inverse of duplication"),
        ("piso", "algorithm for type inference needs to be verified"),
        ("piso", "point-free, combinator-style functional setting"),
        # Pi -- what 42 adds to the semiring isomorphisms, and why
        ("pi", "removes the tag"),
        ("pi", "erases the first component"),
        # Theseus -- the disjointness condition, and the second-order restriction
        ("theseus", "complete non-overlapping covering of the input type"),
        ("theseus", "does not have high-order maps in the formal sense"),
        ("theseus", "instantiated at compile time"),
        ("theseus", "commutative semiring"),
        # Chardonnet et al. -- exhaustivity dropped, and the PInj characterisation
        ("chardonnet", "in order to allow non-terminating behaviour"),
        ("chardonnet", "features higher-order"),
        ("chardonnet", "computable morphisms in PInj"),
        # RFUN -- the first-match policy, dup/eq in one operator, second-order
        ("rfun", "must never match a branch that textually"),
        ("rfun", "case branches may be non-orthogonal"),
        ("rfun", "not enough to make functions first class citizens"),
        ("rfun", "discern from the arity of the"),
        ("rfun", "irreversibility of if-then-else constructs"),
        # Janus -- the assertion, its cost, and local invertibility
        ("janus", "If the assertion does not have the required value"),
        ("janus", "produce an inverse unit"),
        ("janus", "is not injective, and thus there exists no"),
        # The Quantum Effect -- the other route to quantum, and its cost
        ("qeffect", "is one of partial maps"),
        ("qeffect", "is however not lifted to the amalgamated"),
        ("qeffect", "it is only applied to total maps"),
        ("qeffect", "the nature of infinite-dimensional quantum computation"),
        # One rig -- control is the rig structure, and the black-box no-go
        ("onerig", "only controlled computation"),
        ("onerig", "implied by the control equations"),
        ("onerig", "where the unitary is a black box"),
        # ZX -- what it was built to avoid, and how far its completeness reaches
        ("backens", "The only way to simplify or compare quantum circuit diagrams"),
        ("backens", "can also be derived pictorially"),
        ("jeandel", "one of the main open questions in categorical quantum mechanics"),
        ("jeandel", "by adding two new axioms to the language"),
        ("jeandel", "of the ring of dyadic rationals"),
        ("coecke", "intuitive and universal graphical calculus for multi-qubit systems"),
        ("ngwang", "a universal completion of the ZX-calculus for the whole of pure"),
        ("hadzi", "show their completeness for pure-state qubit theory"),
        ("wetering", "all reasoning about quantum computation can be done inside"),
        ("vilmart", "were numerous, tedious to manipulate and lacked a physical"),
        ("vilmart", "all their equations are necessary"),
        ("coecke", "can have any number of inputs or outputs (including none)"),
        ("coecke", "with 1 input and 2 outputs (cf. copying)"),
        ("coecke", "with 1 input and no output (cf. erasing)"),
        ("coecke", "The points in the calculus are not normalized"),
        ("coecke", "the equational theory of the zx-calculus is strictly weaker"),
        ("coecke", "is therefore isomorphic to the circle"),
    ]

    @classmethod
    def setUpClass(cls):
        import shutil

        if not shutil.which("pdftotext"):
            raise unittest.SkipTest("pdftotext is not installed")
        cls.text = {}
        for key, rel in cls.SOURCES.items():
            path = ROOT / rel
            if not path.exists():
                raise unittest.SkipTest(f"{rel} is not present")
            out = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                capture_output=True, text=True,
            )
            cls.text[key] = re.sub(r"\s+", " ", out.stdout.replace("’", "'"))

    def test_every_quotation_is_in_its_source(self):
        for source, quote in self.QUOTES:
            with self.subTest(source=source, quote=quote[:40]):
                self.assertIn(
                    re.sub(r"\s+", " ", quote), self.text[source],
                    "this quotation is no longer in the paper it cites",
                )

    def test_the_quotations_are_actually_used_in_related_md(self):
        """A stale entry here would give false assurance."""
        # Strip the blockquote markers first: a quotation that wraps mid-sentence
        # would otherwise have a stray "> " inside it.  The leading `\s*` matters
        # -- a quotation nested inside a list item is indented, and without it
        # such a quotation silently fails to match.
        raw = (ROOT / "RELATED.md").read_text(encoding="utf-8")
        related = re.sub(r"\s+", " ", re.sub(r"^\s*>\s?", "", raw, flags=re.M))
        for source, quote in self.QUOTES:
            with self.subTest(quote=quote[:40]):
                self.assertIn(re.sub(r"\s+", " ", quote), related)

    def test_invs_construct_count(self):
        """RELATED.md says one of Inv's *twelve* constructs discharges the proviso."""
        related = (ROOT / "RELATED.md").read_text(encoding="utf-8")
        self.assertIn("twelve constructs", related)
        grammar = re.search(
            r"I ::=(.*?)C ::=", self.text["inv"].replace(" | ", "|"), re.S
        )
        self.assertIsNotNone(grammar, "Inv's grammar is no longer where it was")
        alternatives = [a for a in grammar.group(1).split("|") if a.strip()]
        self.assertEqual(len(alternatives), 12, alternatives)


class TestRelatedWorkFacts(unittest.TestCase):
    def test_e2_has_no_model_over_the_booleans(self):
        """Q42.md's case for a separate module rests on this, so compute it."""
        import itertools

        note = (ROOT / "Q42.md").read_text(encoding="utf-8")
        self.assertIn("of all 16 boolean 2×2 matrices", note)

        def mul(a, b):
            return tuple(
                tuple(any(a[i][k] and b[k][j] for k in range(2)) for j in range(2))
                for i in range(2)
            )

        X = ((False, True), (True, False))
        mats = [
            ((p[0], p[1]), (p[2], p[3]))
            for p in itertools.product([False, True], repeat=4)
        ]
        self.assertEqual(len(mats), 16)
        self.assertEqual([m for m in mats if mul(m, m) == X], [])


class TestStructure(unittest.TestCase):
    def test_every_contents_list_is_complete(self):
        text = (ROOT / "MANUAL.md").read_text(encoding="utf-8").split("\n")
        current, listed, subs = None, {}, {}
        for line in text:
            top = re.match(r"^## (\d+)\. ", line)
            sub = re.match(r"^### (\d+)\.(\d+) ", line)
            item = re.match(r"^- \[(\d+)\.(\d+) ", line)
            if top:
                current = top.group(1)
                listed.setdefault(current, [])
            elif item and current:
                listed[current].append(f"{item.group(1)}.{item.group(2)}")
            elif sub:
                subs.setdefault(sub.group(1), []).append(
                    f"{sub.group(1)}.{sub.group(2)}"
                )
        for section, have in listed.items():
            if not have:
                continue  # a section may legitimately have no contents list
            with self.subTest(section=section):
                self.assertEqual(
                    sorted(set(subs.get(section, [])) - set(have)), [],
                    f"section {section}'s contents list omits a subsection",
                )

    def test_internal_links_resolve(self):
        """A `[text](#anchor)` must point at a heading that exists."""
        for doc in DOCS:
            text = (ROOT / doc).read_text(encoding="utf-8")
            slugs = set()
            for m in re.finditer(r"^#{1,6}\s+(.*)$", text, re.M):
                h = re.sub(r"`([^`]+)`", r"\1", m.group(1))
                h = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", h).lower()
                h = re.sub(r"[^\w\s-]", "", h)
                slugs.add(re.sub(r"[\s_]", "-", h.strip()).strip("-"))
            for m in re.finditer(r"\]\(#([\w-]+)\)", text):
                with self.subTest(doc=doc, anchor=m.group(1)):
                    self.assertIn(m.group(1), slugs, "dangling internal link")

    def test_referenced_files_exist(self):
        """A link to another document must point at a file that is there."""
        for doc in DOCS:
            text = (ROOT / doc).read_text(encoding="utf-8")
            for m in re.finditer(r"\]\((?!https?:|#)([^)]+)\)", text):
                target = m.group(1).split("#")[0]
                with self.subTest(doc=doc, target=target):
                    self.assertTrue(
                        (ROOT / target).exists(), f"{doc} links to a missing file"
                    )


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main(verbosity=2)
