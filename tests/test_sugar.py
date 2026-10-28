"""Tests for clause definitions (SUGAR.md).  Run with:  python3 tests/test_sugar.py

The desugarer's promise is that a clause definition means exactly what its
hand-written point-free counterpart means.  So most of these tests compile a
definition from clauses and check it against the version already in
`course.42`, `prelude.42` or `spike/sugar.42`, forwards and backwards.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import subprocess  # noqa: E402
import tempfile  # noqa: E402

from rel42 import Ref, dagger, parse_program, parse_value, run, show_term  # noqa: E402
from rel42.core import Rel42Error, expand_env  # noqa: E402
from rel42.core import Union  # noqa: E402
from rel42.sugar import compile_clause, compile_clauses, turned_round  # noqa: E402
from rel42.syntax import show_clause  # noqa: E402
from rel42.types import infer_program  # noqa: E402


def _load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return parse_program(fh.read())


SRC = """
type nat    = mu X. 1 + X
type list a = mu X. 1 + (a x X)

def single x            <->  [x]

def append ([], ys)     <->  ys
def append (x:xs, ys)   <->  x : append (xs, ys)

def split ys                    <->  ([], ys)
def split (x : append (xs, ys)) <->  (x:xs, ys)

def rev []              <->  []
def rev (x:xs)          <->  append (rev xs, [x])

def unrev []                        <->  []
def unrev (append (rev xs, [x]))    <->  x:xs

def initlast (append (xs, [x]))     <->  (xs, x)
def initlast2 zs  <->  let (xs, [x]) = append! zs in (xs, x)

def forget 0      <->  ()
def forget (n+1)  <->  forget n

def same (x, x) <-> x

def ctrl m (L (), a)    <->  (L (), a)
def ctrl m (R (), a)    <->  (R (), m a)
def flip = ctrl swapsum

def here   (x:xs)  <->  (x, xs)
def deeper (x:xs)  <->  let (y, ys) = pick xs in (y, x:ys)
def pick = here | deeper

def add (0, n)    <->  n
def add (m+1, n)  <->  add (m, n) + 1
def double n      <->  add (n, n)

def mul (0, n)      <->  (n, 0)
def mul (m + 1, n)  <->  let (k, p) = mul (m, n) in (k, add (k, p))
def twoproducts (n, (a, b))  <->  let (n, p) = mul (a, n) in let (n, q) = mul (b, n) in (n, (p, q))
def twofresh (n, (a, b))     <->  let (n1, p) = mul (a, n) in let (n2, q) = mul (b, n1) in (n2, (p, q))

def greet () <-> "hi"
def two (n+2) <-> n
def piped x <-> (swapprod ; swapprod) x
"""

ENV = parse_program(SRC)
SPIKE = _load("spike/sugar.42")
COURSE = _load("course.42")
PRELUDE = _load("prelude.42")

LISTS = ["[]", "[1]", "[1, 2]", "[1, 2, 3]", "[3, 1, 2, 0]"]
PAIRS = ["([], [])", "([1], [])", "([], [2])", "([1, 2], [3])", "([0], [1, 2])"]
NATS = ["0", "1", "2", "5"]


# Combinator applications such as `ctrl swapsum` are reduced at load time,
# exactly as the command line does before running anything.
RUNNABLE = {}


def _runnable(env):
    key = id(env)
    if key not in RUNNABLE:
        RUNNABLE[key] = expand_env(env)
    return RUNNABLE[key]


def fwd(env, name, v):
    return run(Ref(name), parse_value(v), _runnable(env))


def bwd(env, name, v):
    return run(dagger(Ref(name)), parse_value(v), _runnable(env))


class Agreement(unittest.TestCase):
    """Clause definitions against the hand-written ones, both directions."""

    def agree(self, name, other_env, other, fwd_inputs, bwd_inputs=()):
        for v in fwd_inputs:
            self.assertEqual(fwd(ENV, name, v), fwd(other_env, other, v), f"{name} {v}")
        for v in bwd_inputs:
            self.assertEqual(bwd(ENV, name, v), bwd(other_env, other, v), f"{name}! {v}")

    def test_single(self):
        self.agree("single", COURSE, "single", NATS + LISTS, ["[1]", "[1, 2]", "[]"])

    def test_append(self):
        self.agree("append", COURSE, "append", PAIRS, LISTS)
        self.agree("append", PRELUDE, "append", PAIRS, LISTS)

    def test_rev(self):
        self.agree("rev", COURSE, "rev", LISTS, LISTS)

    def test_split(self):
        self.agree("split", SPIKE, "split", LISTS, PAIRS)

    def test_initlast(self):
        self.agree("initlast", SPIKE, "initlast", LISTS, ["([1, 2], 3)", "([], 0)"])
        self.agree("initlast2", SPIKE, "initlast", LISTS, ["([1, 2], 3)", "([], 0)"])

    def test_forget(self):
        self.agree("forget", SPIKE, "forget", NATS)

    def test_same(self):
        self.agree("same", SPIKE, "same", ["(2, 2)", "(2, 3)", "([1], [1])"], NATS)

    def test_ctrl(self):
        cases = ["(L (), L ())", "(L (), R ())", "(R (), L ())", "(R (), R ())"]
        self.agree("flip", SPIKE, "flip", cases, cases)
        self.agree("flip", PRELUDE, "flip", cases, cases)

    def test_pick(self):
        self.agree("pick", SPIKE, "pick", LISTS, ["(9, [1, 2])", "(0, [])"])

    def test_add_and_double(self):
        self.agree("add", PRELUDE, "add", ["(0, 0)", "(2, 3)", "(3, 2)"], NATS)
        self.agree("double", PRELUDE, "double", NATS, ["0", "6", "7"])


class Inversion(unittest.TestCase):
    """SUGAR.md section 5: turning every clause round gives the inverse."""

    def same_relation(self, f, g_inverse, inputs):
        for v in inputs:
            self.assertEqual(fwd(ENV, f, v), bwd(ENV, g_inverse, v), f"{f} {v}")
            self.assertEqual(bwd(ENV, f, v), fwd(ENV, g_inverse, v), f"{f}! {v}")

    def test_split_is_append_turned_round(self):
        self.same_relation("split", "append", LISTS)
        self.same_relation("append", "split", PAIRS)

    def test_unrev_is_rev_turned_round(self):
        self.same_relation("unrev", "rev", LISTS)


class Emission(unittest.TestCase):
    """What the compiler writes, where the note makes a claim about it."""

    def test_single_is_the_manuals_single(self):
        self.assertEqual(show_term(ENV["single"]), "unitprod! ; swapprod ; id * inl ; inr")

    def test_double_is_the_preludes_double(self):
        self.assertEqual(show_term(ENV["double"]), show_term(PRELUDE["double"]))

    def test_let_and_function_pattern_compile_alike(self):
        self.assertEqual(ENV["initlast"], ENV["initlast2"])

    def test_nonlinear_pattern_is_an_equality_test(self):
        self.assertEqual(show_term(ENV["same"]), "copy!")

    def test_rev_backwards_terminates(self):
        # SUGAR.md section 8: the recursive call is built before the
        # constructor-only side, so run backwards the cheap test comes first.
        self.assertEqual(bwd(ENV, "rev", "[1, 2, 3]"), {parse_value("[3, 2, 1]")})

    def test_a_call_under_a_constructor_is_taken_apart_first(self):
        # Both halves of hanoi's pair call something.  The right half's calls
        # sit under a cons cell whose head must be the move (0, 2): run
        # backwards, that check has to come before the left half recurses, or
        # hanoi! exhausts the call depth (SUGAR.md section 8).
        tour = _load("tour.42")
        moves = parse_value("[(0, 1), (0, R R ()), (1, R R ())]")
        self.assertEqual(run(dagger(Ref("hanoi")), moves, tour), {parse_value("2")})

    def test_a_let_chain_carries_only_names_in_hand(self):
        # Regression: a `let` also tried to carry names that a *later* `let`
        # binds, so any chain of two failed to compile.
        env = expand_env(parse_program(
            "def add (0, n) <-> n\n"
            "def add (m + 1, n) <-> add (m, n) + 1\n"
            "def f (a, b) <-> let c = add (a, b) in let d = add (c, b) in (d, b)\n"
        ))
        self.assertEqual(run(Ref("f"), parse_value("(1, 2)"), env), {parse_value("(5, 2)")})

    def test_literals_and_offsets(self):
        self.assertEqual(fwd(ENV, "greet", "()"), {parse_value('"hi"')})
        self.assertEqual(fwd(ENV, "two", "5"), {parse_value("3")})
        self.assertEqual(fwd(ENV, "two", "1"), set())

    def test_a_parenthesised_pipeline_is_a_call(self):
        self.assertEqual(fwd(ENV, "piped", "(1, 2)"), {parse_value("(1, 2)")})

    def test_every_definition_typechecks(self):
        _, errors = infer_program(ENV)
        self.assertEqual(errors, {})

    def test_source_order_is_kept(self):
        self.assertEqual(list(ENV)[:3], ["single", "append", "split"])


class Rebinding(unittest.TestCase):
    """QSUGAR.md section 3.4: a name may be bound again once its value is consumed."""

    def test_rebinding_compiles_like_fresh_names(self):
        self.assertEqual(ENV["twoproducts"], ENV["twofresh"])

    def test_it_runs_both_ways(self):
        self.assertEqual(fwd(ENV, "twoproducts", "(3, (2, 5))"), {parse_value("(3, (6, 15))")})
        self.assertEqual(bwd(ENV, "twoproducts", "(3, (6, 15))"), {parse_value("(3, (2, 5))")})

    def test_consumed_by_the_same_let(self):
        env = parse_program("def g x <-> x\ndef f x <-> let x = g x in x")
        self.assertEqual(run(Ref("f"), parse_value("3"), expand_env(env)), {parse_value("3")})

    def test_messages_show_the_written_name(self):
        with self.assertRaises(Rel42Error) as cm:
            parse_program("def g x <-> x\n"
                          "def f x <-> let x = g x in let x = g x in ()")
        self.assertIn("the variable `x` is bound and never used", str(cm.exception))
        self.assertNotIn("#", str(cm.exception))


class CaseTrees(unittest.TestCase):
    """SUGAR.md section 6: the case tree is the union, compiled better."""

    SRC = """
def neg (L x) <-> R x
def neg (R x) <-> L x
def deep ((a, L b), c) <-> (c, (a, L b))
def deep ((a, R b), c) <-> R (c, (b, a))
def right (x, L ()) <-> (L (), x)
def right (x, R y) <-> (R (y, y), x)
def two (L x, L y) <-> L (x, y)
def two (L x, R y) <-> R (L (x, y))
def two (R x, y) <-> R (R (x, y))
def consts (L (), 3) <-> [1]
def consts (R (), 3) <-> [2]
def consts (L (), 4) <-> []
def cross (L x, y) <-> (y, R x)
def cross (R x, y) <-> (y, L x)
def whole (L ()) <-> 0
"""
    VALUES = [
        "()", "0", "1", "[]", "[1]", "[2]", "L ()", "R ()", "L 5", "R 5",
        "L (L ())", "R (L ())", "(L (), L ())", "(R (), L ())", "(L (), R ())",
        "(L 5, L ())", "(1, L ())", "(1, R 2)", "((1, L 2), 3)", "((1, R 2), 3)",
        "(L 1, L 2)", "(L 1, R 2)", "(R 1, 2)", "(R (), R ())", "(L (), 3)",
        "(R (), 3)", "(L (), 4)", "(L 1, 3)", "(R 1, 4)", "(3, R 1)", "(4, L 1)",
        "(1, L (1, 2))", "(2, R (2, 1))", "(1, (2, L 3))",
    ]

    def test_case_trees_mean_the_union(self):
        # Untyped on purpose: the two must agree on every value, not only on
        # values of the right type.
        env = parse_program(self.SRC)
        runnable = expand_env(env)
        for name, (_, group) in env.clauses.items():
            union = compile_clause(group[0])
            for c in group[1:]:
                union = Union(union, compile_clause(c))
            both = dict(runnable, union=union)
            for v in self.VALUES:
                for back in (False, True):
                    with self.subTest(name=name, value=v, backward=back):
                        self.assertEqual(
                            run(Ref(name, back), parse_value(v), both),
                            run(Ref("union", back), parse_value(v), both),
                        )

    def test_append_and_add_are_the_preludes_exactly(self):
        self.assertEqual(ENV["append"], PRELUDE["append"])
        self.assertEqual(ENV["add"], PRELUDE["add"])

    def test_ctrl_is_the_corrected_hand_version_exactly(self):
        # SUGAR.md section 6: the earlier hand version was looser than these
        # clauses; this one checks the label's payload, as they do.
        self.assertEqual(ENV["ctrl"], SPIKE["ctrl"])
        v = parse_value("(L 5, L ())")
        self.assertEqual(run(Ref("flip"), v, _runnable(ENV)), set())

    def test_labels_on_both_sides_need_no_join(self):
        env = parse_program(self.SRC)
        self.assertEqual(show_term(env["neg"]), "swapsum")
        self.assertEqual(show_term(env["cross"]), "dist ; swapsum ; dist! ; swapprod")
        self.assertNotIn("join", show_term(ENV["ctrl"]))

    def test_a_matched_constant_is_checked(self):
        # Regression: a pattern that is a constant and nothing else was matched
        # without looking at the value under its label, so `L 5` passed for `L ()`.
        env = expand_env(parse_program(self.SRC))
        self.assertEqual(run(Ref("whole"), parse_value("L 5"), env), set())
        self.assertEqual(run(Ref("whole"), parse_value("L ()"), env), {parse_value("0")})


class DeadChecks(unittest.TestCase):
    """A matched constant's unit check is dropped exactly where the types
    already make it `()` (SUGAR.md section 3)."""

    def test_dropped_where_the_types_force_it(self):
        # rev's `[]` payload is () because append makes it so.
        self.assertTrue(show_term(ENV["rev"]).startswith("inl + "))
        self.assertNotIn("unitprod! ; swapprod ; unitprod", show_term(ENV["rev"]))

    def test_kept_where_it_narrows_the_type(self):
        # ctrl's clauses say `L ()` and forget's say `0`; nothing else in their
        # bodies does, so there the check is what makes the type narrower.
        self.assertIn("unitprod ; unitprod!", show_term(ENV["ctrl"]))
        self.assertIn("unitprod! ; swapprod ; unitprod", show_term(ENV["forget"]))

    def test_no_definitions_type_changes(self):
        checked = dict(ENV)
        for name, (params, group) in ENV.clauses.items():
            checked[name] = compile_clauses(params, group)
        a, _ = infer_program(checked)
        b, _ = infer_program(ENV)
        from rel42.types import show_scheme
        self.assertEqual({n: show_scheme(s) for n, s in a.items()},
                         {n: show_scheme(s) for n, s in b.items()})

    def test_the_stated_untyped_cost(self):
        # Untyped, the dropped check is visible: rev passes `L 5` through.
        # The command line refuses `L 5` for rev before running it.
        v = parse_value("L 5")
        self.assertEqual(run(Ref("rev"), v, _runnable(ENV)), {v})
        params, group = ENV.clauses["rev"]
        strict = dict(_runnable(ENV), strict=compile_clauses(params, group))
        self.assertEqual(run(Ref("strict"), v, strict), set())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.42")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(SRC)
            out = subprocess.run(
                [sys.executable, "-m", "rel42", "run", path, "rev", "L 5"],
                capture_output=True, text=True, cwd=ROOT,
            )
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("does not fit the domain", out.stdout + out.stderr)


class TurnedRound(unittest.TestCase):
    """`show` prints each definition's clauses turned round.  They must mean the
    inverse, and print as source that parses back to the same clauses."""

    CASES = {
        "single": NATS,
        "append": PAIRS,
        "rev": LISTS,
        "add": ["(0, 0)", "(2, 3)"],
        "initlast2": LISTS,
        "deeper": LISTS,
        "same": ["(2, 2)", "(2, 3)"],
        "twoproducts": ["(3, (2, 5))", "(0, (1, 1))", "(2, (0, 4))"],
    }

    def test_turned_round_clauses_are_the_inverse(self):
        for name, inputs in self.CASES.items():
            params, group = ENV.clauses[name]
            turned = compile_clauses(params, [turned_round(c) for c in group])
            env = dict(_runnable(ENV), turned=turned)
            for v in inputs:
                with self.subTest(name=name, value=v):
                    self.assertEqual(
                        run(Ref("turned", True), parse_value(v), env),
                        fwd(ENV, name, v),
                    )

    def test_printed_clauses_parse_back(self):
        extra = []
        for name, (params, group) in ENV.clauses.items():
            for c in group:
                extra.append(f"def rt_{show_clause(name, params, c)}")
            for c in group:
                extra.append(f"def tr_{show_clause(name, params, turned_round(c))}")
        env = parse_program(SRC + "\n" + "\n".join(extra))
        for name, (_, group) in ENV.clauses.items():
            with self.subTest(name=name):
                again = env.clauses[f"rt_{name}"][1]
                self.assertEqual([(c.pattern, c.body) for c in again],
                                 [(c.pattern, c.body) for c in group])
                turned = env.clauses[f"tr_{name}"][1]
                self.assertEqual(
                    [(c.pattern, c.body) for c in turned],
                    [(t.pattern, t.body) for t in map(turned_round, group)],
                )

    def test_constructors_print_as_written(self):
        params, group = ENV.clauses["ctrl"]
        self.assertEqual(show_clause("ctrl", params, group[1]), "ctrl m (R (), a) <-> (R (), m a)")
        params, group = ENV.clauses["add"]
        self.assertEqual(show_clause("add", params, group[1]), "add (m + 1, n) <-> add (m, n) + 1")
        params, group = ENV.clauses["single"]
        self.assertEqual(show_clause("single", params, turned_round(group[0])), "single [x] <-> x")


class Warnings(unittest.TestCase):
    """SUGAR.md section 6: overlapping input patterns warn; nothing else does."""

    def warnings(self, src):
        return parse_program(src).warnings

    def test_overlapping_inputs_warn(self):
        (w,) = self.warnings("def f [] <-> []\ndef f xs <-> xs")
        self.assertIn("clauses 1 and 2 of 'f'", w)
        self.assertIn("not the first match", w)
        self.assertIn("also `[]`", w)  # 0, [] and false are one value

    def test_the_witness_is_named(self):
        (w,) = self.warnings("def f (x : xs) <-> (x, xs)\ndef f (y : [])  <-> (y, [])")
        self.assertIn("`_ : 0`", w)

    def test_disjoint_inputs_do_not_warn(self):
        self.assertEqual(ENV.clauses and self.warnings(
            "def g [] <-> []\ndef g (x : xs) <-> x : xs"), [])

    def test_overlapping_outputs_do_not_warn(self):
        # append's outputs overlap: that is where split's answers come from.
        self.assertEqual(self.warnings(
            "def a ([], ys) <-> ys\ndef a (x:xs, ys) <-> x : a (xs, ys)"), [])

    def test_an_explicit_union_does_not_warn(self):
        self.assertEqual(self.warnings(
            "def h (x:xs) <-> (x, xs)\n"
            "def d (x:xs) <-> let (y, ys) = p xs in (y, x:ys)\n"
            "def p = h | d"), [])

    def test_a_call_in_a_pattern_counts_as_anything(self):
        # `split`'s two clauses really do overlap, and are meant to.  `unrev`'s
        # do not -- `append (rev xs, [x])` never matches `[]` -- but a call is
        # treated as matching anything, so it warns too.  That is the stated
        # cost of a check that never misses a real overlap.
        split, unrev = ENV.warnings
        self.assertIn("of 'split' both match `_ : _`", split)
        self.assertIn("of 'unrev' both match `0`", unrev)

    def test_files_without_clauses_have_none(self):
        self.assertEqual(PRELUDE.warnings, [])

    def test_the_command_line_prints_them_on_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.42")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("def f [] <-> []\ndef f xs <-> xs\n")
            out = subprocess.run(
                [sys.executable, "-m", "rel42", "run", path, "f", "[]"],
                capture_output=True, text=True, cwd=ROOT,
            )
        self.assertIn("warning:", out.stderr)
        self.assertNotIn("warning:", out.stdout)


Q_SRC = """
type qubit = 1 + 1
def x     = swapsum
def s     = id + (omega ; omega)
def hcore = x ; s ; v ; s ; x
def h     = unitprod! ; (omega * hcore) ; unitprod

def cx (L (), q)  <->  (L (), q)
def cx (R (), q)  <->  (R (), x q)

def ccx (L (), qs)  <->  (L (), qs)
def ccx (R (), qs)  <->  (R (), cx qs)

def orcnot (L (), y)  <->  (L (), x y)
def orcnot (R (), y)  <->  (R (), y)

def add4 (x0, (x1, (y0, y1)))  <->
    let (x0, (y0, y1)) = ccx (x0, (y0, y1)) in
    let (x0, y0)       = cx (x0, y0)        in
    let (x1, y1)       = cx (x1, y1)        in
    (x0, (x1, (y0, y1)))

def bell (a, b)  <->  let a = h a in cx (a, b)

def cyc (L (), L ())  <->  (L (), R ())
def cyc (L (), R ())  <->  (R (), L ())
def cyc (R (), L ())  <->  (L (), L ())
def cyc (R (), R ())  <->  (R (), R ())
"""


def _register(bits):
    from rel42.core import Inl, Inr, Pair, UNIT
    def bit(b):
        return Inr(UNIT) if b else Inl(UNIT)
    v = bit(bits[-1])
    for b in reversed(bits[:-1]):
        v = Pair(bit(b), v)
    return v


class Q42Clauses(unittest.TestCase):
    """QSUGAR.md: Q42 accepts clauses under its own rules (plan step 1)."""

    @classmethod
    def setUpClass(cls):
        from q42.syntax import parse_program as qparse
        cls.qparse = staticmethod(qparse)
        cls.Q = expand_env(qparse(Q_SRC))

    def column(self, env, name, bits, back=False):
        from q42.core import column
        return column(Ref(name, back), _register(bits), env)

    def test_clauses_equal_the_point_free_gates_exactly(self):
        import itertools
        cases = [("cx", "q42/gates.42", "cx", 2), ("ccx", "q42/gates.42", "ccx", 3),
                 ("orcnot", "q42/deutsch.42", "orcnot", 2), ("add4", "q42/fib.42", "add4", 4),
                 ("bell", "q42/gates.42", "bell", 2)]
        for mine, path, theirs, n in cases:
            with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                ref = expand_env(self.qparse(fh.read()))
            for bits in itertools.product([0, 1], repeat=n):
                for back in (False, True):
                    with self.subTest(name=mine, bits=bits, backward=back):
                        self.assertEqual(self.column(self.Q, mine, bits, back),
                                         self.column(ref, theirs, bits, back))

    def test_bell_compiles_to_what_gates_42_writes(self):
        self.assertEqual(show_term(self.qparse(Q_SRC)["bell"]), "h * id ; cx")

    def test_the_square(self):
        # QSUGAR.md section 1: compiled by 42 the same clauses give a relation,
        # and it is the set of nonzero entries of Q42's matrix.
        import itertools
        from q42.exact import is_zero
        rel = expand_env(parse_program(Q_SRC))
        for name, n in [("cx", 2), ("ccx", 3), ("orcnot", 2), ("add4", 4), ("cyc", 2)]:
            for bits in itertools.product([0, 1], repeat=n):
                for back in (False, True):
                    with self.subTest(name=name, bits=bits, backward=back):
                        amp = self.column(self.Q, name, bits, back)
                        self.assertEqual(
                            run(Ref(name, back), _register(bits), rel),
                            {w for w, a in amp.items() if not is_zero(a)},
                        )

    def rejects(self, clauses, *fragments):
        from q42.core import Q42Error
        src = "def x = swapsum\n" + clauses
        with self.assertRaises(Q42Error) as cm:
            self.qparse(src)
        for frag in fragments:
            self.assertIn(frag, str(cm.exception))

    def test_a_name_used_twice_is_refused(self):
        self.rejects("def dup a <-> (a, a)", "`a` is used twice", "QMANUAL section 5.2")

    def test_a_name_matched_twice_is_refused(self):
        self.rejects("def eq (a, a) <-> a", "`a` is matched twice")

    def test_a_gap_is_refused(self):
        self.rejects("def f (L (), q) <-> (L (), q)", "no clause of `f` matches `(R _, _)`")

    def test_overlapping_patterns_are_refused(self):
        self.rejects("def f (a, b) <-> (a, b)\ndef f (L (), b) <-> (R (), b)",
                     "patterns of clauses 1 and 2 of `f` both match")

    def test_overlapping_terms_are_refused(self):
        self.rejects("def f (L (), q) <-> (L (), q)\ndef f (R (), q) <-> (L (), q)",
                     "terms of clauses 1 and 2 of `f` both produce")

    def test_a_let_pattern_that_can_fail_is_refused(self):
        self.rejects("def g a <-> a\ndef f a <-> let L () = g a in ()", "a `let` pattern can fail")

    def test_a_call_in_a_pattern_is_refused(self):
        self.rejects("def g a <-> a\ndef f (g a) <-> a", "the pattern calls a program")

    def test_coverage_is_decided_by_splitting(self):
        # No column has a constructor in every clause, yet the five cover the
        # eight values of three bits exactly once.  Coverage accepts them; the
        # refusal is the general construction's, not a gap or an overlap.
        berry = "\n".join([
            "def berry (L (), (R (), c)) <-> (L (), (R (), c))",
            "def berry (R (), (b, L ())) <-> (R (), (b, L ()))",
            "def berry (a, (L (), R ())) <-> (a, (L (), R ()))",
            "def berry (L (), (L (), L ())) <-> (L (), (L (), L ()))",
            "def berry (R (), (R (), R ())) <-> (R (), (R (), R ()))",
        ])
        self.rejects(berry, "needs the general construction")

    def test_a_split_neither_side_shares_needs_the_general_construction(self):
        # Exchange 000 and 111, fix the rest: the smallest such permutation.
        states = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
        def v(s):
            l = ["R ()" if x else "L ()" for x in s]
            return f"({l[0]}, ({l[1]}, {l[2]}))"
        image = {(0, 0, 0): (1, 1, 1), (1, 1, 1): (0, 0, 0)}
        src = "\n".join(f"def sw {v(s)} <-> {v(image.get(s, s))}" for s in states)
        self.rejects(src, "`sw` covers both sides exactly once",
                     "QSUGAR.md section 4.2", "uses inl, inr, join")


class Errors(unittest.TestCase):
    def rejects(self, src, *fragments):
        with self.assertRaises(Rel42Error) as cm:
            parse_program(src)
        for frag in fragments:
            self.assertIn(frag, str(cm.exception))

    def test_forgetting(self):
        self.rejects("def length xs <-> 0", "`xs` is bound and never used",
                     "cannot forget")

    def test_inventing(self):
        self.rejects("def f x <-> (x, y)", "`y` is used but never bound",
                     "cannot invent")

    def test_forgetting_through_a_let(self):
        self.rejects("def g x <-> x\ndef f x <-> let y = g x in ()", "`y`")

    def test_pattern_variable_named_like_a_definition(self):
        self.rejects("def g x <-> x\ndef f (g, x) <-> (g, x)",
                     "pattern variable `g` has the name of a definition")

    def test_pattern_variable_named_like_a_parameter(self):
        self.rejects("def f m (m, x) <-> (m, x)",
                     "pattern variable `m` has the name of a parameter")

    def test_pattern_variable_named_like_a_primitive(self):
        self.rejects("def f (copy, x) <-> (copy, x)", "name of a primitive")

    def test_definition_name_used_as_a_value(self):
        self.rejects("def g x <-> x\ndef f x <-> (g, x)", "must be applied to an argument")

    def test_clauses_must_be_together(self):
        self.rejects("def f x <-> x\ndef g y <-> y\ndef f z <-> z", "written together")

    def test_clauses_share_parameters(self):
        self.rejects("def f m x <-> x\ndef f n x <-> x", "same parameters")

    def test_clause_and_point_free_cannot_mix(self):
        self.rejects("def f = id\ndef f x <-> x", "already defined")
        self.rejects("def f x <-> x\ndef f = id", "already defined")

    def test_a_name_still_in_hand_may_not_be_bound_again(self):
        self.rejects("def g x <-> x\ndef f (x, y) <-> let x = g y in x",
                     "`x` is bound again while its value is still in hand")

    def test_pattern_must_be_one_term(self):
        self.rejects("def f x : xs <-> x : xs", "single term")

    def test_reserved_names(self):
        self.rejects("def L x <-> x", "reserved")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main()
