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
from rel42.sugar import compile_clauses, turned_round  # noqa: E402
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


class Q42(unittest.TestCase):
    def test_q42_refuses_clauses_with_the_reason(self):
        from q42.syntax import parse_program as qparse

        with self.assertRaises(Rel42Error) as cm:
            qparse("def f x <-> x")
        self.assertIn("42-only", str(cm.exception))
        self.assertIn("section 9", str(cm.exception))


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

    def test_let_may_not_rebind(self):
        self.rejects("def g x <-> x\ndef f x <-> let x = g x in x", "bound twice")

    def test_pattern_must_be_one_term(self):
        self.rejects("def f x : xs <-> x : xs", "single term")

    def test_reserved_names(self):
        self.rejects("def L x <-> x", "reserved")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main()
