"""Tests for 42.  Run with:  python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rel42.core import DepthExceeded  # noqa: E402
from rel42.syntax import (  # noqa: E402
    ParseError, as_byte, as_list, as_string, from_byte, from_list,
)
from rel42 import (  # noqa: E402
    Inl,
    Inr,
    Pair,
    Ref,
    UNIT,
    dagger,
    from_nat,
    parse_program,
    parse_term,
    parse_value,
    run,
    show,
)

PRELUDE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prelude.42")

with open(PRELUDE, encoding="utf-8") as _fh:
    ENV = parse_program(_fh.read())


def fwd(name, v, limit=5000):
    return run(Ref(name), v, ENV, max_depth=limit)


def bwd(name, v, limit=5000):
    return run(dagger(Ref(name)), v, ENV, max_depth=limit)


class TestDagger(unittest.TestCase):
    TERMS = [
        "id", "swapsum", "copy", "join",
        "dist ; (unitprod + (inr ; inl)) ; join",
        "copy | (id * id)",
        "(inl ; inr)^",
        "assocprod! ; swapprod",
    ]

    def test_involution(self):
        """dagger is involutive on the nose, syntactically."""
        for src in self.TERMS:
            t = parse_term(src)
            self.assertEqual(dagger(dagger(t)), t, src)

    def test_contravariance(self):
        """dagger(s ; t) == dagger(t) ; dagger(s)."""
        s, t = parse_term("copy"), parse_term("swapprod ; assocprod!")
        # Note `swapprod!`: swapprod is semantically self-inverse, but dagger
        # flips the syntactic flag regardless.  Involutivity is unaffected.
        self.assertEqual(
            dagger(parse_term("copy ; (swapprod ; assocprod!)")),
            parse_term("(assocprod ; swapprod!) ; copy!"),
        )
        self.assertEqual(dagger(dagger(s)), s)
        self.assertEqual(dagger(dagger(t)), t)


class TestDefiningLaw(unittest.TestCase):
    """x in P(y)  <=>  y in inv(P)(x), checked exhaustively on samples."""

    CASES = [
        ("add", [Pair(from_nat(m), from_nat(n)) for m in range(4) for n in range(4)]),
        ("double", [from_nat(n) for n in range(5)]),
        ("succ", [from_nat(n) for n in range(5)]),
        ("pred", [from_nat(n) for n in range(5)]),
        ("not", [Inl(UNIT), Inr(UNIT)]),
        ("rot3", [Pair(from_nat(1), Pair(from_nat(2), from_nat(3)))]),
        ("append", [Pair(parse_value("[1,2]"), parse_value("[3]")),
                    Pair(parse_value("[]"), parse_value("[1,2,3]"))]),
        ("toggle", [Inl(UNIT), Inr(UNIT)]),
    ]
    # `downfrom` is deliberately absent: its dagger is `succ^`, which does not
    # saturate.  The law still holds of it mathematically -- we simply cannot
    # check the backward half by enumeration.  See TestOneDirectionalComputability.

    def test_forward_then_backward(self):
        for name, inputs in self.CASES:
            for x in inputs:
                for y in fwd(name, x):
                    self.assertIn(
                        x, bwd(name, y),
                        f"{name}: {show(x)} -> {show(y)} but {show(y)} does not "
                        f"map back to {show(x)}",
                    )

    def test_backward_then_forward(self):
        """The law in the other direction, which is the half that pins inv down."""
        for name, inputs in self.CASES:
            for y in inputs:
                for x in bwd(name, y):
                    self.assertIn(y, fwd(name, x), f"{name}: {show(x)} / {show(y)}")


class TestGroupoidFragment(unittest.TestCase):
    """Bijections: singleton image and singleton preimage."""

    def test_not(self):
        self.assertEqual(fwd("not", Inl(UNIT)), {Inr(UNIT)})
        self.assertEqual(bwd("not", Inr(UNIT)), {Inl(UNIT)})

    def test_rot3(self):
        v = Pair(from_nat(1), Pair(from_nat(2), from_nat(3)))
        self.assertEqual(fwd("rot3", v), {Pair(from_nat(3), Pair(from_nat(1), from_nat(2)))})
        self.assertEqual(bwd("rot3", *fwd("rot3", v)), {v})


class TestPartialInjections(unittest.TestCase):
    def test_succ_pred(self):
        self.assertEqual(fwd("succ", from_nat(3)), {from_nat(4)})
        self.assertEqual(fwd("pred", from_nat(3)), {from_nat(2)})

    def test_pred_of_zero_is_empty(self):
        """Partiality, not error: zero simply has no preimage under succ."""
        self.assertEqual(fwd("pred", from_nat(0)), set())
        self.assertEqual(bwd("succ", from_nat(0)), set())


class TestRelations(unittest.TestCase):
    def test_add_forward_is_a_function(self):
        for m in range(5):
            for n in range(5):
                self.assertEqual(
                    fwd("add", Pair(from_nat(m), from_nat(n))), {from_nat(m + n)}
                )

    def test_add_backward_enumerates_every_preimage(self):
        for n in range(6):
            pre = bwd("add", from_nat(n))
            self.assertEqual(len(pre), n + 1, f"add!({n})")
            self.assertEqual(
                pre,
                {Pair(from_nat(i), from_nat(n - i)) for i in range(n + 1)},
            )

    def test_composition_can_restore_determinism(self):
        """add! is many-valued, yet (copy ; add)! is single-valued."""
        for n in range(6):
            self.assertEqual(fwd("double", from_nat(n)), {from_nat(2 * n)})
            self.assertEqual(bwd("double", from_nat(2 * n)), {from_nat(n)})
        for odd in (1, 3, 5, 7):
            self.assertEqual(bwd("double", from_nat(odd)), set(), f"double!({odd})")

    def test_append_backward_enumerates_splits(self):
        xs = parse_value("[1,2,3]")
        splits = bwd("append", xs)
        self.assertEqual(len(splits), 4)
        # nil prints as "0": see TestEncodingsCoincide below.
        self.assertEqual(
            {(show(p.a), show(p.b)) for p in splits},
            {("0", "[1, 2, 3]"), ("[1]", "[2, 3]"),
             ("[1, 2]", "[3]"), ("[1, 2, 3]", "0")},
        )
        self.assertEqual(
            {(p.a, p.b) for p in splits},
            {(parse_value("[]"), parse_value("[1,2,3]")),
             (parse_value("[1]"), parse_value("[2,3]")),
             (parse_value("[1,2]"), parse_value("[3]")),
             (parse_value("[1,2,3]"), parse_value("[]"))},
        )

    def test_append_forward(self):
        got = fwd("append", Pair(parse_value("[1,2]"), parse_value("[3,4]")))
        self.assertEqual({show(v) for v in got}, {"[1, 2, 3, 4]"})


class TestStar(unittest.TestCase):
    def test_downfrom(self):
        self.assertEqual(fwd("downfrom", from_nat(3)),
                         {from_nat(i) for i in range(4)})

    def test_star_is_reflexive(self):
        self.assertIn(from_nat(0), fwd("downfrom", from_nat(0)))

    def test_toggle_saturates(self):
        self.assertEqual(fwd("toggle", Inl(UNIT)), {Inl(UNIT), Inr(UNIT)})


class TestOneDirectionalComputability(unittest.TestCase):
    """A relation can be computable forwards and not backwards.

    `downfrom = pred^` saturates at zero; its dagger `succ^` is infinite.  The
    interpreter must say so rather than hang.
    """

    def test_forward_saturates(self):
        self.assertEqual(fwd("downfrom", from_nat(3)), {from_nat(i) for i in range(4)})

    def test_backward_reports_non_saturation(self):
        with self.assertRaises(DepthExceeded):
            run(dagger(Ref("downfrom")), from_nat(0), ENV, max_orbit=500)


class TestShapeMismatchIsEmptyNotError(unittest.TestCase):
    """Being outside a relation's domain yields the empty set, not a crash."""

    def test_wrong_shape(self):
        self.assertEqual(run(parse_term("swapprod"), Inl(UNIT)), set())
        self.assertEqual(run(parse_term("unitprod"), UNIT), set())
        self.assertEqual(run(parse_term("dist"), UNIT), set())


class TestSyntax(unittest.TestCase):
    def test_dagger_eliminated_at_parse_time(self):
        self.assertEqual(parse_term("(copy ; join)!"), parse_term("join! ; copy!"))

    def test_precedence(self):
        self.assertEqual(parse_term("a ; b + c ; d"), parse_term("a ; (b + c) ; d"))
        self.assertEqual(parse_term("a + b * c"), parse_term("a + (b * c)"))
        self.assertEqual(parse_term("a | b ; c"), parse_term("a | (b ; c)"))

    def test_value_roundtrip(self):
        for src in ["0", "3", "()", "[]", "[1, 2, 3]", "(1, 2)", "L ()", "R R L ()"]:
            v = parse_value(src)
            self.assertEqual(parse_value(show(v)), v, src)

    def test_nat_and_list_encodings(self):
        self.assertEqual(parse_value("2"), Inr(Inr(Inl(UNIT))))
        self.assertEqual(parse_value("[0]"), Inr(Pair(Inl(UNIT), Inl(UNIT))))


class TestEncodingsCoincide(unittest.TestCase):
    """Zero and nil are the *same value*, and the printer cannot tell them apart.

    Both  mu X. 1 + X  and  mu X. 1 + (A x X)  use `Inl ()` for their base
    constructor, and the interpreter is untyped, so `0`, `[]` and `L ()` all
    denote one value.  This is a real consequence of an untyped Rel and not a
    printing bug: resolving it needs types, not a better show function.
    """

    def test_zero_is_nil(self):
        self.assertEqual(parse_value("0"), parse_value("[]"))
        self.assertEqual(parse_value("0"), parse_value("L ()"))
        self.assertEqual(show(parse_value("[]")), "0")

    def test_nonempty_lists_are_unambiguous(self):
        self.assertEqual(show(parse_value("[1,2]")), "[1, 2]")
        self.assertEqual(show(parse_value("3")), "3")


class TestTour(unittest.TestCase):
    """Every output claimed in the comments of tour.42, checked.

    The tour is documentation, so it is exactly the kind of thing that rots.
    These cases are transcribed from its comments; if a claim there stops
    being true, this fails.
    """

    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tour.42"),
        encoding="utf-8",
    ) as fh:
        TOUR = parse_program(fh.read())

    def check(self, name, src, expected, backward=False):
        term = Ref(name)
        if backward:
            term = dagger(term)
        got = {show(v) for v in run(term, parse_value(src), self.TOUR)}
        self.assertEqual(got, set(expected), f"{name} {src} {'backward' if backward else ''}")

    def test_bijections(self):
        self.check("not", "L ()", {"R ()"})
        self.check("not", "R ()", {"0"}, backward=True)
        self.check("rot3", "(1, (2, 3))", {"(3, (1, 2))"})
        self.check("rot3", "(3, (1, 2))", {"(1, (2, 3))"}, backward=True)

    def test_single(self):
        self.check("single", "7", {"[7]"})
        self.check("single", "[7]", {"7"}, backward=True)

    def test_partial(self):
        self.check("pred", "3", {"2"})
        self.check("pred", "0", set())
        self.check("succ", "3", {"4"})

    def test_union(self):
        self.check("near", "5", {"4", "6"})
        self.check("near", "0", {"1"})

    def test_recursion_idiom(self):
        self.check("append", "([1,2], [3,4])", {"[1, 2, 3, 4]"})
        self.check("rev", "[1,2,3]", {"[3, 2, 1]"})
        self.check("rev", "[3,2,1]", {"[1, 2, 3]"}, backward=True)

    def test_rev_is_its_own_dagger_semantically(self):
        """rev! is a syntactically different term that computes the same relation."""
        self.assertNotEqual(dagger(self.TOUR["rev"]), self.TOUR["rev"])
        for src in ["[]", "[1]", "[1,2]", "[1,2,3]", "[1,2,3,4]"]:
            v = parse_value(src)
            self.assertEqual(
                run(Ref("rev"), v, self.TOUR),
                run(dagger(Ref("rev")), v, self.TOUR),
                src,
            )

    def test_split_is_append_backwards(self):
        xs = parse_value("[1,2,3]")
        self.assertEqual(
            run(Ref("split"), xs, self.TOUR),
            run(dagger(Ref("append")), xs, self.TOUR),
        )
        self.check("split", "[1,2,3]",
                   {"(0, [1, 2, 3])", "([1], [2, 3])", "([1, 2], [3])", "([1, 2, 3], 0)"})

    def test_palin_is_a_coreflexive(self):
        for good in ["[]", "[1]", "[1,2,1]", "[1,2,2,1]"]:
            v = parse_value(good)
            self.assertEqual(run(Ref("palin"), v, self.TOUR), {v}, good)
        for bad in ["[1,2]", "[1,2,3]"]:
            self.assertEqual(run(Ref("palin"), parse_value(bad), self.TOUR), set(), bad)

    def test_palin_is_direction_agnostic(self):
        """A test does not care which way you run it."""
        for src in ["[1,2,1]", "[1,2]", "[]", "[1,2,3]"]:
            v = parse_value(src)
            self.assertEqual(
                run(Ref("palin"), v, self.TOUR),
                run(dagger(Ref("palin")), v, self.TOUR),
                src,
            )


class TestManualSection3(unittest.TestCase):
    """Every worked example in MANUAL.md §3 (Values), checked."""

    def r(self, src, val):
        return {show(v) for v in run(parse_term(src), parse_value(val), ENV)}

    # -- 3.3 why the labels are visible ------------------------------------

    def test_tag_lets_a_program_reject(self):
        self.assertEqual(self.r("inl!", "L ()"), {"()"})
        self.assertEqual(self.r("inl!", "R ()"), set())

    def test_join_deletes_the_tag(self):
        self.assertEqual(self.r("join", "L ()"), {"()"})
        self.assertEqual(self.r("join", "R ()"), {"()"})

    def test_join_backwards_must_offer_both(self):
        self.assertEqual(
            run(parse_term("join!"), UNIT), {Inl(UNIT), Inr(UNIT)}
        )

    # -- 3.4 how pairs work ------------------------------------------------

    def test_nesting_is_part_of_the_value(self):
        self.assertNotEqual(parse_value("(1, (2, 3))"), parse_value("((1, 2), 3)"))
        self.assertEqual(self.r("assocprod", "(1, (2, 3))"), {"((1, 2), 3)"})
        self.assertEqual(self.r("assocprod", "((1, 2), 3)"), set())
        self.assertEqual(self.r("assocprod!", "((1, 2), 3)"), {"(1, (2, 3))"})

    def test_acting_on_one_half(self):
        self.assertEqual(self.r("id * succ", "(1, 2)"), {"(1, 3)"})
        self.assertEqual(self.r("succ * id", "(1, 2)"), {"(2, 2)"})

    def test_the_two_legal_ways_to_shrink_a_pair(self):
        self.assertEqual(self.r("unitprod", "((), 5)"), {"5"})
        self.assertEqual(self.r("copy", "5"), {"(5, 5)"})
        self.assertEqual(self.r("copy!", "(5, 5)"), {"5"})
        self.assertEqual(self.r("copy!", "(5, 6)"), set())

    def test_fst_cannot_be_expressed(self):
        """There is no primitive taking (a, b) to a for arbitrary b.

        Anything claiming to be `fst` must work for *every* second component;
        the two shrinking primitives each constrain it instead.
        """
        pairs = [Pair(from_nat(1), from_nat(n)) for n in range(4)]
        for name in ("unitprod", "copy!"):
            images = [run(parse_term(name), p, ENV) for p in pairs]
            self.assertFalse(
                all(img == {from_nat(1)} for img in images),
                f"{name} would be fst",
            )

    def test_shape_mismatch_is_not_an_error(self):
        self.assertEqual(self.r("swapprod", "5"), set())

    # -- 3.5 numbers -------------------------------------------------------

    def test_succ_is_just_a_label(self):
        self.assertEqual(parse_term("inr"), parse_term("inr"))
        self.assertEqual(ENV["succ"], parse_term("inr"))
        self.assertEqual(ENV["pred"], parse_term("inr!"))

    def test_pred_of_zero_needs_no_special_case(self):
        self.assertEqual(self.r("inr!", "0"), set())

    # -- 3.2 / 3.6 encodings -----------------------------------------------

    def test_bool_convention_matches_prelude(self):
        """false = L (), true = R (); `not` swaps them."""
        self.assertEqual(run(Ref("not"), Inl(UNIT), ENV), {Inr(UNIT)})
        self.assertEqual(run(Ref("not"), Inr(UNIT), ENV), {Inl(UNIT)})

    def test_list_is_a_label_plus_a_pair(self):
        self.assertEqual(parse_value("[1, 2]"), parse_value("R (1, R (2, L ()))"))


class TestArithmetic(unittest.TestCase):
    """arith.42 -- and the point that division needs no algorithm."""

    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arith.42"),
        encoding="utf-8",
    ) as fh:
        A = parse_program(fh.read())

    def call(self, name, value, backward=False):
        term = dagger(Ref(name)) if backward else Ref(name)
        return run(term, value, self.A)

    def n(self, *xs):
        return tuple(from_nat(x) for x in xs)

    def test_add(self):
        for m in range(5):
            for k in range(5):
                self.assertEqual(
                    self.call("add", Pair(*self.n(m, k))), {from_nat(m + k)}
                )

    def test_mul_keeps_its_multiplier(self):
        for m in range(5):
            for k in range(5):
                self.assertEqual(
                    self.call("mul", Pair(*self.n(m, k))),
                    {Pair(from_nat(k), from_nat(m * k))},
                    f"mul({m}, {k})",
                )

    def test_lt_is_a_filter(self):
        for a in range(5):
            for b in range(5):
                got = self.call("lt", Pair(*self.n(a, b)))
                want = {Pair(*self.n(a, b))} if a < b else set()
                self.assertEqual(got, want, f"lt({a}, {b})")

    def test_divexact_is_mul_backwards(self):
        """No division algorithm exists in arith.42; this is mul reversed."""
        self.assertEqual(self.A["divexact"], dagger(Ref("mul")))
        for k in range(1, 5):
            for m in range(5):
                self.assertEqual(
                    self.call("divexact", Pair(*self.n(k, m * k))),
                    {Pair(*self.n(m, k))},
                    f"divexact({k}, {m * k})",
                )

    def test_divexact_is_empty_when_it_does_not_divide(self):
        for k, p in [(3, 7), (5, 12), (4, 6)]:
            self.assertEqual(self.call("divexact", Pair(*self.n(k, p))), set())

    def test_divmod(self):
        for a in range(13):
            for b in range(1, 5):
                q, r = divmod(a, b)
                self.assertEqual(
                    self.call("divmod", Pair(*self.n(a, b))),
                    {Pair(Pair(*self.n(q, r)), from_nat(b))},
                    f"divmod({a}, {b})",
                )

    def test_mul_backwards_at_zero_does_not_terminate(self):
        """mul(m, 0) = (0, 0) for every m, so mul!(0, 0) is infinite.

        Not a defect: every number divides zero. It is the one place where
        `mul` fails to be injective, and the interpreter says so rather than
        pretending.
        """
        with self.assertRaises(DepthExceeded):
            run(dagger(Ref("mul")), Pair(*self.n(0, 0)), self.A, max_depth=200)

    def test_divmod_by_zero_fails_fast(self):
        """The trailing `nonzero` guard is what makes this terminate.

        `lt` already forces b > 0 going forwards, but reversal puts it last --
        after `mul!` has already been asked to divide by zero. Restating the
        constraint at the end of the pipeline puts it first under reversal.
        """
        self.assertEqual(self.call("divmod", Pair(*self.n(7, 0))), set())

    def test_the_guard_is_load_bearing(self):
        """Without the trailing guard, divmod(7, 0) diverges. Verify that."""
        unguarded = parse_program(
            "def add = dist ; (unitprod + (add ; inr)) ; join\n"
            "def mul = dist ; ((swapprod ; (id * inl))"
            "                 + (mul ; (copy * id) ; assocprod! ; (id * add))) ; join\n"
            "def lt  = dist ; ((id * (inr! ; inr))"
            "                 + ((id * inr!) ; lt ; (id * inr))) ; dist!\n"
            "def u   = assocprod! ; (id * lt) ; (id * swapprod) ; assocprod"
            "        ; (mul * id) ; assocprod! ; (id * add) ; swapprod\n"
        )
        with self.assertRaises(DepthExceeded):
            run(dagger(Ref("u")), Pair(*self.n(7, 0)), unguarded, max_depth=200)
        # ...and with the guard, the same query is simply empty.
        self.assertEqual(self.call("divmod", Pair(*self.n(7, 0))), set())

    def test_sub_is_addk_backwards(self):
        self.assertEqual(self.A["sub"], dagger(Ref("addk")))
        for a in range(6):
            for b in range(6):
                got = self.call("sub", Pair(*self.n(a, b)))
                want = {Pair(*self.n(a - b, b))} if a >= b else set()
                self.assertEqual(got, want, f"sub({a}, {b})")

    def test_every_example_printed_in_manual_section_11(self):
        """Transcribed from MANUAL.md §11. If the manual claims it, it runs."""
        cases = [
            ("add",      "(2, 3)",       {"5"}),
            ("mul",      "(4, 5)",       {"(5, 20)"}),
            ("mul",      "(0, 7)",       {"(7, 0)"}),
            ("divexact", "(3, 12)",      {"(4, 3)"}),
            ("divexact", "(5, 20)",      {"(4, 5)"}),
            ("divexact", "(3, 7)",       set()),
            ("addk",     "(2, 3)",       {"(5, 3)"}),
            ("sub",      "(5, 3)",       {"(2, 3)"}),
            ("sub",      "(3, 5)",       set()),
            ("lt",       "(2, 5)",       {"(2, 5)"}),
            ("lt",       "(5, 2)",       set()),
            ("divmod",   "(17, 5)",      {"((3, 2), 5)"}),
            ("divmod",   "(12, 4)",      {"((3, 0), 4)"}),
            ("divmod",   "(3, 5)",       {"((0, 3), 5)"}),
            ("divmod",   "(7, 0)",       set()),
        ]
        for name, src, want in cases:
            got = {show(v) for v in self.call(name, parse_value(src))}
            self.assertEqual(got, want, f"{name}{src}")

        self.assertEqual(
            {show(v) for v in self.call("add", from_nat(5), backward=True)},
            {"(0, 5)", "(1, 4)", "(2, 3)", "(3, 2)", "(4, 1)", "(5, 0)"},
        )

    def test_the_defining_law_holds_throughout(self):
        cases = [
            ("add", [Pair(*self.n(m, k)) for m in range(4) for k in range(4)]),
            # k starts at 1: mul!(0, 0) is infinite, so the backward half of
            # the law cannot be checked by enumeration there. See
            # test_mul_backwards_at_zero_does_not_terminate.
            ("mul", [Pair(*self.n(m, k)) for m in range(4) for k in range(1, 4)]),
            ("addk", [Pair(*self.n(m, k)) for m in range(4) for k in range(4)]),
            ("lt", [Pair(*self.n(a, b)) for a in range(4) for b in range(4)]),
            ("divmod", [Pair(*self.n(a, b)) for a in range(8) for b in range(1, 4)]),
        ]
        for name, inputs in cases:
            for x in inputs:
                for y in self.call(name, x):
                    self.assertIn(x, self.call(name, y, backward=True), f"{name}")


class TestRationals(unittest.TestCase):
    """rational.42.  Numbers are kept small: arithmetic here is unary."""

    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rational.42"),
        encoding="utf-8",
    ) as fh:
        Q = parse_program(fh.read())

    def frac(self, p, q):
        return Pair(from_nat(p), from_nat(q))

    def call(self, name, value, backward=False):
        term = dagger(Ref(name)) if backward else Ref(name)
        return run(term, value, self.Q)

    # -- plumbing ----------------------------------------------------------

    def test_transpose_is_its_own_inverse(self):
        v = parse_value("((1, 2), (3, 4))")
        self.assertEqual(self.call("transpose", v), {parse_value("((1, 3), (2, 4))")})
        self.assertEqual(
            self.call("transpose", *self.call("transpose", v)), {v}
        )

    # -- multiplication ----------------------------------------------------

    def test_qmul_is_one_line(self):
        self.assertEqual(self.Q["qmul"], parse_term("transpose ; (mul * mul) ; transpose"))
        self.assertEqual(self.Q["qdiv"], dagger(Ref("qmul")))

    def test_qmul(self):
        for p, q, r, s in [(1, 2, 3, 4), (2, 3, 3, 5), (0, 1, 2, 3), (1, 1, 1, 1)]:
            self.assertEqual(
                self.call("qmul", Pair(self.frac(p, q), self.frac(r, s))),
                {Pair(self.frac(r, s), self.frac(p * r, q * s))},
                f"{p}/{q} * {r}/{s}",
            )

    def test_qdiv_is_qmul_backwards(self):
        for p, q, r, s in [(1, 2, 3, 4), (2, 3, 3, 5)]:
            product = Pair(self.frac(r, s), self.frac(p * r, q * s))
            self.assertEqual(
                self.call("qdiv", product),
                {Pair(self.frac(p, q), self.frac(r, s))},
            )

    # -- addition ----------------------------------------------------------

    def test_qadd(self):
        for p, q, r, s in [(1, 2, 1, 3), (3, 4, 1, 4), (0, 1, 2, 3), (2, 5, 1, 2)]:
            self.assertEqual(
                self.call("qadd", Pair(self.frac(p, q), self.frac(r, s))),
                {Pair(self.frac(r, s), self.frac(p * s + q * r, q * s))},
                f"{p}/{q} + {r}/{s}",
            )

    def test_qsub_is_qadd_backwards(self):
        self.assertEqual(self.Q["qsub"], dagger(Ref("qadd")))
        for p, q, r, s in [(1, 2, 1, 3), (3, 4, 1, 4), (2, 5, 1, 2)]:
            total = Pair(self.frac(r, s), self.frac(p * s + q * r, q * s))
            self.assertEqual(
                self.call("qsub", total), {Pair(self.frac(p, q), self.frac(r, s))}
            )

    def test_qsub_is_exact_on_representations_not_on_values(self):
        """A real limitation of unreduced fractions, worth pinning down.

        1/2 + 1/2 produces denominator 2*2 = 4, so the inverse recognises 4/4
        and nothing else. Handing it the equal-valued 1/1 gives nothing,
        because no p/q with q*2 == 1 can solve it. To subtract at the level of
        rational *values* rather than representations, scale first.
        """
        self.assertEqual(
            self.call("qadd", Pair(self.frac(1, 2), self.frac(1, 2))),
            {Pair(self.frac(1, 2), self.frac(4, 4))},
        )
        self.assertEqual(
            self.call("qsub", Pair(self.frac(1, 2), self.frac(4, 4))),
            {Pair(self.frac(1, 2), self.frac(1, 2))},
        )
        self.assertEqual(
            self.call("qsub", Pair(self.frac(1, 2), self.frac(1, 1))), set()
        )
        # ...even though 4/4 and 1/1 are the same number.
        v = Pair(self.frac(4, 4), self.frac(1, 1))
        self.assertEqual(self.call("qeq", v), {v})

    # -- equality ----------------------------------------------------------

    def test_qeq_accepts_equal_rationals(self):
        for p, q, r, s in [(1, 2, 2, 4), (1, 2, 1, 2), (0, 1, 0, 5), (2, 3, 4, 6)]:
            v = Pair(self.frac(p, q), self.frac(r, s))
            self.assertEqual(self.call("qeq", v), {v}, f"{p}/{q} == {r}/{s}")

    def test_qeq_rejects_unequal_rationals(self):
        for p, q, r, s in [(1, 2, 3, 4), (1, 3, 1, 2), (0, 1, 1, 2)]:
            v = Pair(self.frac(p, q), self.frac(r, s))
            self.assertEqual(self.call("qeq", v), set(), f"{p}/{q} != {r}/{s}")

    def test_qeq_is_a_filter_in_both_directions(self):
        v = Pair(self.frac(1, 2), self.frac(2, 4))
        self.assertEqual(self.call("qeq", v), self.call("qeq", v, backward=True))

    # -- scaling -----------------------------------------------------------

    def test_reduceby_and_scaleby(self):
        self.assertEqual(
            self.call("reduceby", Pair(self.frac(6, 8), from_nat(2))),
            {Pair(self.frac(3, 4), from_nat(2))},
        )
        self.assertEqual(self.Q["scaleby"], dagger(Ref("reduceby")))
        self.assertEqual(
            self.call("scaleby", Pair(self.frac(3, 4), from_nat(2))),
            {Pair(self.frac(6, 8), from_nat(2))},
        )

    def test_reduceby_rejects_a_non_divisor(self):
        self.assertEqual(
            self.call("reduceby", Pair(self.frac(6, 8), from_nat(4))), set()
        )

    def test_there_is_no_reduce(self):
        """Reduction to lowest terms is deliberately absent: it cannot exist.

        Euclid's algorithm discards a quotient at every step, and this
        language cannot discard. Any gcd program must hand the quotients back.
        """
        self.assertNotIn("reduce", self.Q)
        self.assertNotIn("gcd", self.Q)

    # -- the law -----------------------------------------------------------

    def test_the_defining_law(self):
        cases = [
            ("qmul", [Pair(self.frac(p, q), self.frac(r, s))
                      for p, q, r, s in [(1, 2, 3, 4), (2, 3, 1, 2), (0, 1, 2, 3)]]),
            ("qadd", [Pair(self.frac(p, q), self.frac(r, s))
                      for p, q, r, s in [(1, 2, 1, 3), (3, 4, 1, 4), (0, 1, 2, 3)]]),
            ("qeq", [Pair(self.frac(1, 2), self.frac(2, 4)),
                     Pair(self.frac(1, 2), self.frac(3, 4))]),
            ("reduceby", [Pair(self.frac(6, 8), from_nat(2))]),
        ]
        for name, inputs in cases:
            for x in inputs:
                for y in self.call(name, x):
                    self.assertIn(x, self.call(name, y, backward=True), name)


class TestStrings(unittest.TestCase):
    """Text: the encoding, the literals, and strings.42."""

    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "strings.42"),
        encoding="utf-8",
    ) as fh:
        S = parse_program(fh.read())

    def call(self, name, src, backward=False):
        term = dagger(Ref(name)) if backward else Ref(name)
        return {show(v) for v in run(term, parse_value(src), self.S)}

    # -- encoding ----------------------------------------------------------

    def test_byte_roundtrip(self):
        for n in range(256):
            self.assertEqual(as_byte(from_byte(n)), n, n)

    def test_a_byte_is_eight_bits_nested_right(self):
        v = from_byte(0b01100001)  # 'a'
        bits = []
        for _ in range(7):
            self.assertIsInstance(v, Pair)
            bits.append(v.a)
            v = v.b
        bits.append(v)
        self.assertEqual(len(bits), 8)
        self.assertEqual(
            [b == Inr(UNIT) for b in bits],
            [False, True, True, False, False, False, False, True],
        )

    def test_literals_roundtrip(self):
        for src in ["'a'", "'A'", "'0'", '"hi"', '"Hello, world!"', '"héllo"']:
            v = parse_value(src)
            self.assertEqual(parse_value(show(v)), v, src)

    def test_escapes(self):
        self.assertEqual(show(parse_value('"a\\nb"')), '"a\\nb"')
        self.assertEqual(as_string(parse_value('"a\\tb"')), "a\tb")
        self.assertEqual(as_byte(parse_value("'\\\\'")), 0x5C)

    def test_utf8(self):
        self.assertEqual(as_string(parse_value('"héllo"')), "héllo")

    def test_text_is_never_confused_with_numbers(self):
        """A byte is a nest of pairs; a number is a chain of labels."""
        self.assertEqual(show(parse_value("[72, 105]")), "[72, 105]")
        self.assertIsNone(as_byte(from_nat(97)))
        self.assertIsNone(as_string(parse_value("[1,2,3]")))
        self.assertEqual(show(parse_value('"Hi"')), '"Hi"')

    def test_char_literal_must_be_one_byte(self):
        with self.assertRaises(ParseError):
            parse_value("'ab'")
        with self.assertRaises(ParseError):
            parse_value("'é'")  # two bytes in UTF-8

    def test_a_string_really_is_a_list(self):
        self.assertEqual(
            parse_value('"hi"'),
            from_list([from_byte(ord("h")), from_byte(ord("i"))]),
        )

    # -- programs ----------------------------------------------------------

    def test_list_programs_work_on_text_unchanged(self):
        self.assertEqual(self.call("concat", '("foo", "bar")'), {'"foobar"'})
        self.assertEqual(self.call("reverse", '"stressed"'), {'"desserts"'})
        self.assertEqual(self.call("palin", '"racecar"'), {'"racecar"'})
        self.assertEqual(self.call("palin", '"apple"'), set())

    def test_concat_and_split_are_one_definition(self):
        self.assertEqual(self.S["concat"], Ref("append"))
        self.assertEqual(self.S["split"], dagger(Ref("append")))
        self.assertEqual(
            self.call("split", '"abc"'),
            {'("a", "bc")', '("ab", "c")', '("abc", 0)', '(0, "abc")'},
        )

    def test_flipcase_flips_exactly_bit_five(self):
        for n in range(256):
            got = run(Ref("flipcase"), from_byte(n), self.S)
            self.assertEqual(got, {from_byte(n ^ 0x20)}, n)

    def test_swapbyte_is_total_and_single_valued(self):
        """The two guards are disjoint AND cover every byte."""
        for n in range(256):
            got = run(Ref("swapbyte"), from_byte(n), self.S)
            self.assertEqual(len(got), 1, f"byte {n} gave {len(got)} answers")

    def test_swapbyte_leaves_non_letters_alone(self):
        for ch in " ,.!0123456789\t\n":
            n = ord(ch)
            self.assertEqual(
                run(Ref("swapbyte"), from_byte(n), self.S), {from_byte(n)}, repr(ch)
            )

    def test_swapcase(self):
        self.assertEqual(self.call("swapcase", '"Hello, World!"'), {'"hELLO, wORLD!"'})
        self.assertEqual(self.call("swapcase", '"abc 123 XYZ"'), {'"ABC 123 xyz"'})

    def test_swapcase_is_its_own_inverse(self):
        for src in ['"Hello, World!"', '"abc"', '"A"', '"123"']:
            self.assertEqual(
                self.call("swapcase", src), self.call("swapcase", src, backward=True), src
            )

    def test_documented_caveat_is_accurate(self):
        """@[\\]^_`{|}~ and DEL do get mapped onto each other. State it, test it."""
        for ch in "@[\\]^_`{|}~\x7f":
            n = ord(ch)
            self.assertEqual(run(Ref("swapbyte"), from_byte(n), self.S), {from_byte(n ^ 0x20)})


class TestCipher(unittest.TestCase):
    """cipher.42 -- a Feistel cipher whose decryptor is derived, not written."""

    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cipher.42"),
        encoding="utf-8",
    ) as fh:
        C = parse_program(fh.read())

    KEY, IV = 0x4B, 0x3C

    def ecb(self, msg):
        v = Pair(from_byte(self.KEY), parse_value(f'"{msg}"'))
        return run(Ref("ecb"), v, self.C)

    def enc(self, msg, key=None, iv=None):
        v = Pair(from_byte(key or self.KEY),
                 Pair(from_byte(self.IV if iv is None else iv), parse_value(f'"{msg}"')))
        return run(Ref("cbc"), v, self.C)

    def dec(self, ct, key=None, iv=None):
        v = Pair(from_byte(key or self.KEY),
                 Pair(from_byte(self.IV if iv is None else iv), ct))
        return run(dagger(Ref("cbc")), v, self.C)

    # -- the claim ---------------------------------------------------------

    def test_decrypt_is_literally_cbc_backwards(self):
        """The entire implementation of decryption."""
        self.assertEqual(self.C["decrypt"], dagger(Ref("cbc")))

    def test_round_trip(self):
        for msg in ["attack at dawn", "a", "", "Hello, World!", "\x00\xff", "aaaaaaaa"]:
            (out,) = self.enc(msg)
            (back,) = self.dec(out.b.b)
            self.assertEqual(as_string(back.b.b) or "", msg, repr(msg))

    def test_key_and_iv_both_survive(self):
        """42 will not let encryption discard either -- which is also correct,
        since decryption needs both."""
        (out,) = self.enc("abc")
        self.assertEqual(out.a, from_byte(self.KEY))
        self.assertEqual(out.b.a, from_byte(self.IV))

    def test_single_valued_in_both_directions(self):
        (out,) = self.enc("abc")
        self.assertEqual(len(self.enc("abc")), 1)
        self.assertEqual(len(self.dec(out.b.b)), 1)

    def test_key_matters(self):
        (a,) = self.enc("attack at dawn")
        (b,) = self.enc("attack at dawn", key=0x5A)
        self.assertNotEqual(a.b.b, b.b.b)

    def test_iv_matters(self):
        (a,) = self.enc("attack at dawn")
        (b,) = self.enc("attack at dawn", iv=0x00)
        self.assertNotEqual(a.b.b, b.b.b)

    def test_wrong_key_gives_garbage_not_an_error(self):
        (out,) = self.enc("attack at dawn")
        (bad,) = self.dec(out.b.b, key=0x5A)
        self.assertNotEqual(as_string(bad.b.b), "attack at dawn")

    # -- the point of CBC --------------------------------------------------

    def test_ecb_leaks_the_plaintext_pattern(self):
        """'attack at dawn' has 'a' at 0, 3, 7, 11 -- and so does the ECB
        ciphertext. This is the weakness CBC exists to remove."""
        (out,) = self.ecb("attack at dawn")
        ct = as_list(out.b)
        for i in (3, 7, 11):
            self.assertEqual(ct[i], ct[0])
        self.assertEqual(ct[2], ct[1])

    def test_cbc_does_not(self):
        (out,) = self.enc("attack at dawn")
        ct = as_list(out.b.b)
        for i in (3, 7, 11):
            self.assertNotEqual(ct[i], ct[0], f"position {i} still matches position 0")
        self.assertNotEqual(ct[2], ct[1])

    def test_cbc_hides_a_wholly_repetitive_plaintext(self):
        """The sharpest case: eight identical bytes."""
        (ecb_out,) = self.ecb("aaaaaaaa")
        self.assertEqual(len(set(as_list(ecb_out.b))), 1)      # ECB: all identical
        (cbc_out,) = self.enc("aaaaaaaa")
        self.assertGreater(len(set(as_list(cbc_out.b.b))), 1)  # CBC: not

    # -- the pieces --------------------------------------------------------

    def test_cnot1_is_xor_keeping_the_first_operand(self):
        F, T = Inl(UNIT), Inr(UNIT)
        for a, b, want in [(F, F, F), (F, T, T), (T, F, T), (T, T, F)]:
            self.assertEqual(run(Ref("cnot1"), Pair(a, b), self.C), {Pair(a, want)})

    def test_cnot1_is_its_own_inverse(self):
        F, T = Inl(UNIT), Inr(UNIT)
        for a in (F, T):
            for b in (F, T):
                v = Pair(a, b)
                self.assertEqual(
                    run(Ref("cnot1"), v, self.C), run(dagger(Ref("cnot1")), v, self.C)
                )

    def test_xorbyte(self):
        for a, b in [(0x00, 0xFF), (0x4B, 0x3C), (0xAA, 0x55), (0x61, 0x61)]:
            self.assertEqual(
                run(Ref("xorbyte"), Pair(from_byte(a), from_byte(b)), self.C),
                {Pair(from_byte(a), from_byte(a ^ b))},
                f"{a:02x} ^ {b:02x}",
            )

    def test_toffoli(self):
        F, T = Inl(UNIT), Inr(UNIT)
        for a in (F, T):
            for b in (F, T):
                for c in (F, T):
                    flip = a == T and b == T
                    want = (F if c == T else T) if flip else c
                    self.assertEqual(
                        run(Ref("toffoli"), Pair(Pair(a, b), c), self.C),
                        {Pair(Pair(a, b), want)},
                    )

    def test_tonibbles_splits_a_byte_in_half(self):
        def nib(x):
            bits = []
            for _ in range(3):
                bits.append(x.a == Inr(UNIT))
                x = x.b
            bits.append(x == Inr(UNIT))
            return sum(b << (3 - i) for i, b in enumerate(bits))

        for n in (0, 97, 255, 0x4B):
            (v,) = run(Ref("tonibbles"), from_byte(n), self.C)
            self.assertEqual((nib(v.a), nib(v.b)), (n >> 4, n & 0xF), n)

    def test_feistel_round_is_a_bijection_on_every_byte(self):
        for n in range(256):
            (halves,) = run(Ref("tonibbles"), from_byte(n), self.C)
            out = run(Ref("feistel"), halves, self.C)
            self.assertEqual(len(out), 1, n)
            self.assertEqual(run(dagger(Ref("feistel")), *out, self.C), {halves}, n)

    def test_blockenc_is_a_permutation_of_all_256_bytes(self):
        """The real test of a block cipher: it must not collide."""
        key = from_byte(self.KEY)
        seen = {run(Ref("blockenc"), Pair(key, from_byte(n)), self.C).pop().b
                for n in range(256)}
        self.assertEqual(len(seen), 256)


class TestCLI(unittest.TestCase):
    """The manual tells people to write flags after the arguments, so that
    form must work."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TOUR = os.path.join(ROOT, "tour.42")
    PRELUDE = os.path.join(ROOT, "prelude.42")

    def call(self, *argv):
        from io import StringIO
        from contextlib import redirect_stdout

        from rel42.__main__ import main

        buf = StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_raw_flag_after_positional_args(self):
        code, out = self.call("run", self.TOUR, "single", "7", "--raw")
        self.assertEqual(code, 0)
        self.assertIn("R (R R R R R R R L (), L ())", out)

    def test_sugar_is_the_default(self):
        code, out = self.call("run", self.TOUR, "single", "7")
        self.assertEqual(code, 0)
        self.assertIn("[7]", out)

    def test_backward_flag(self):
        code, out = self.call("run", self.PRELUDE, "add", "5", "--backward")
        self.assertEqual(code, 0)
        self.assertIn("6 results", out)

    def test_header_reads_as_an_application(self):
        """A pair argument supplies its own parentheses; no nested pair."""
        _, out = self.call("run", self.PRELUDE, "append", "([1,2], [3])")
        self.assertTrue(out.startswith("append([1, 2], [3]) ="), out)

        _, out = self.call("run", self.PRELUDE, "append", "[1,2,3]", "-b")
        self.assertTrue(out.startswith("append!([1, 2, 3]) ="), out)

        _, out = self.call("run", self.PRELUDE, "double", "3")
        self.assertTrue(out.startswith("double(3) ="), out)

        _, out = self.call("law", self.PRELUDE, "append", "([1,2], [3])")
        self.assertTrue(out.startswith("append([1, 2], [3]) has"), out)

    def test_law_command(self):
        code, out = self.call("law", self.TOUR, "rev", "[1,2,3]")
        self.assertEqual(code, 0)
        self.assertIn("law holds", out)

    def test_show_command(self):
        code, out = self.call("show", self.PRELUDE, "double")
        self.assertEqual(code, 0)
        self.assertIn("copy ; add", out)
        self.assertIn("add! ; copy!", out)

    def test_orbit_flag_reports_divergence(self):
        code, _ = self.call("run", self.PRELUDE, "downfrom", "3", "-b", "--orbit", "50")
        self.assertEqual(code, 2)

    def test_missing_definition_is_an_error(self):
        code, _ = self.call("run", self.TOUR, "nosuch", "1")
        self.assertEqual(code, 1)


class TestTheoremGadgets(unittest.TestCase):
    """The four constructions THEOREM.md's completeness proof is built from.

    Each is a schema indexed by a type; `theorem.42` holds one instance of every
    clause, and these check that the instances behave as the lemmas claim.  The
    proofs are in THEOREM.md sections 4; what is checked here is that the terms
    they name really do denote what the statements say.
    """

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "theorem.42"), encoding="utf-8") as fh:
            cls.ENV = parse_program(fh.read())

    def go(self, name, value):
        return run(Ref(name), value, self.ENV)

    def test_lemma_3_discard_is_definable_though_it_is_not_a_primitive(self):
        """`drop : C <-> 1` is total on values of C, at every clause."""
        for n in range(6):
            self.assertEqual(self.go("dropnat", from_nat(n)), {UNIT})
        self.assertEqual(self.go("droppair", Pair(from_nat(2), from_nat(3))), {UNIT})
        self.assertEqual(self.go("dropbool", Inl(UNIT)), {UNIT})
        self.assertEqual(self.go("dropbool", Inr(UNIT)), {UNIT})
        self.assertEqual(self.go("drop1", UNIT), {UNIT})

    def test_lemma_3_forgetting_is_allowed_because_it_is_not_reversible(self):
        """`drop!` returns every candidate, which is what MANUAL section 2 asks."""
        got = run(dagger(Ref("dropbool")), UNIT, self.ENV)
        self.assertEqual(got, {Inl(UNIT), Inr(UNIT)})

    def test_lemma_4_the_universal_relation(self):
        """`drop_A ; drop_B!` relates every value of A to every value of B."""
        both = {Inl(UNIT), Inr(UNIT)}
        for v in both:
            self.assertEqual(self.go("univbool", v), both)

    def test_lemma_5_a_semi_decision_becomes_a_partial_identity(self):
        """`copy ; (test * id) ; unitprod` filters, and adds nothing."""
        for n in range(8):
            with self.subTest(n=n):
                want = {from_nat(n)} if n % 2 == 0 else set()
                self.assertEqual(self.go("onlyeven", from_nat(n)), want)

    def test_lemma_6_serialisation_is_injective_because_it_is_prefix_free(self):
        """The product clause: `append` is many-valued, `serpair` is not.

        This is the step that would sink the proof if it failed -- concatenating
        two codes is only injective when the codes are prefix-free.
        """
        seen = {}
        for a in range(4):
            for b in range(4):
                (code,) = self.go("serpair", Pair(from_nat(a), from_nat(b)))
                self.assertNotIn(code, seen, f"({a},{b}) collides with {seen.get(code)}")
                seen[code] = (a, b)
                # and decoding really does pick out the one split that works
                self.assertEqual(
                    self.go("unpair", code), {Pair(from_nat(a), from_nat(b))}
                )
        # `append!` alone offers many more splits than that, which is the point
        code = next(iter(self.go("serpair", Pair(from_nat(1), from_nat(2)))))
        self.assertGreater(len(self.go("splits", code)), 1)

    def test_section_5_load_is_total_including_on_the_empty_input(self):
        """`load` must cover every bit list: the head needs a cell to sit on.

        THEOREM.md 5.3 splits it into a cons branch and a nil branch, and the
        nil branch is the one `tm.42` does not have -- which is why `42 tm incval
        "[]"` is empty while `loadtotal` here is not.
        """
        nil, one = Inl(UNIT), Inr(UNIT)          # bit 0 / bit 1, and [] is Inl
        # [] loads to ([], (0, [])): a single blank cell
        self.assertEqual(
            self.go("loadtotal", nil), {Pair(nil, Pair(nil, nil))}
        )
        # [1, 0] loads to ([], (1, [0]))
        inp = Inr(Pair(one, Inr(Pair(nil, nil))))
        self.assertEqual(
            self.go("loadtotal", inp), {Pair(nil, Pair(one, Inr(Pair(nil, nil))))}
        )

    def test_section_5_the_state_tags_are_injective_with_disjoint_images(self):
        """Lemma 8 needs exactly this: no two states can be confused."""
        v = from_nat(2)
        images = {}
        for i, name in enumerate(["tag1", "tag2", "tag3", "tag4"], start=1):
            (out,) = self.go(name, v)
            self.assertNotIn(out, images, f"{name} collides with {images.get(out)}")
            images[out] = name
        # and the collapse chain undoes all four tags, which is what `step` needs
        for name in ["tag1", "tag2", "tag3", "tag4"]:
            (tagged,) = self.go(name, v)
            self.assertEqual(run(Ref("collapse4"), tagged, self.ENV), {v})

    def test_lemma_6_decoding_rejects_a_string_outside_the_code(self):
        bits = self.go("sernat", from_nat(2))
        (good,) = bits
        self.assertEqual(self.go("unnat", good), {from_nat(2)})
        # [1, 1] is a proper prefix of a codeword, so it decodes to nothing
        prefix = Inr(Pair(Inr(UNIT), Inr(Pair(Inr(UNIT), Inl(UNIT)))))
        self.assertEqual(self.go("unnat", prefix), set())



if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main(verbosity=2)
