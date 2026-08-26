"""Tests for the 42 type system.  Run with:  python3 tests/test_types.py

Three classes carry the weight here.  `TestEquirecursive` checks that `mu X.F(X)`
and its unfoldings are genuinely interchangeable, which is the whole content of
the equirecursive choice.  `TestDaggerReversesType` checks the type-level shadow
of the defining law -- inversion swaps the two sides and does nothing else --
over every definition in every library.  And `TestLibrariesAreWellTyped` asserts
the result that justified the pass: all 263 definitions across the ten .42 files
type, with no annotation added to any of them.
"""

from __future__ import annotations

import glob
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rel42 import (  # noqa: E402
    Inl,
    Inr,
    Pair,
    Ref,
    UNIT,
    dagger,
    from_list,
    from_nat,
    parse_program,
    parse_term,
    show,
    show_as,
)
from rel42.syntax import BITS, as_list, from_string  # noqa: E402
from rel42.core import (  # noqa: E402
    App,
    Fun,
    NotARelation,
    Prim,
    Rel42Error,
    Term,
    Var,
    expand,
    expand_env,
    is_combinator,
    substitute,
)
from rel42.syntax import ParseError  # noqa: E402
from rel42.types import (  # noqa: E402
    IllTyped,
    Inference,
    PRIM_SCHEMES,
    Scheme,
    TMu,
    TOne,
    TProd,
    TSum,
    TVar,
    TZero,
    conform,
    groups,
    match_type,
    infer_program,
    infer_term,
    inhabited,
    refold,
    show_scheme,
    show_type,
    unfold,
)
from rel42.types import _names  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = sorted(glob.glob(os.path.join(ROOT, "*.42")))

# nat = mu X. 1 + X   and   list a = mu X. 1 + (a x X), built by hand.
NAT = TMu(50, TSum(TOne(), TVar(50)))
LIST = TMu(51, TSum(TOne(), TProd(TVar(9), TVar(51))))


def byte_type():
    """Eight bits, right-nested -- the encoding of section 12 of the manual."""
    bit = TSum(TOne(), TOne())
    t = bit
    for _ in range(BITS - 1):
        t = TProd(bit, t)
    return t


def ty(src, env=None):
    """The inferred type of a term, as a string."""
    return show_scheme(infer_term(parse_term(src), env or {}))


def lib(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return parse_program(fh.read())


def lib_reduced(name):
    from rel42.core import expand_env

    return expand_env(lib(name))


class TestPrimitives(unittest.TestCase):
    def test_every_primitive_has_a_scheme(self):
        from rel42.core import PRIMS

        self.assertEqual(set(PRIMS), set(PRIM_SCHEMES))

    def test_the_semiring_isomorphisms(self):
        self.assertEqual(ty("id"), "a <-> a")
        self.assertEqual(ty("swapsum"), "a + b <-> b + a")
        self.assertEqual(ty("swapprod"), "a x b <-> b x a")
        self.assertEqual(ty("unitsum"), "0 + a <-> a")
        self.assertEqual(ty("unitprod"), "1 x a <-> a")
        self.assertEqual(ty("assocsum"), "a + (b + c) <-> a + b + c")
        self.assertEqual(ty("assocprod"), "a x (b x c) <-> a x b x c")
        self.assertEqual(ty("dist"), "(a + b) x c <-> a x c + b x c")

    def test_zero_relates_anything_to_anything(self):
        self.assertEqual(ty("zero"), "a <-> b")

    def test_copy_and_join(self):
        self.assertEqual(ty("copy"), "a <-> a x a")
        self.assertEqual(ty("join"), "a + a <-> a")

    def test_injections_leave_the_other_summand_free(self):
        self.assertEqual(ty("inl"), "a <-> a + b")
        self.assertEqual(ty("inr"), "a <-> b + a")


class TestConstructors(unittest.TestCase):
    def test_composition_matches_the_middle(self):
        self.assertEqual(ty("inl ; swapsum"), "a <-> b + a")

    def test_composition_rejects_a_mismatched_middle(self):
        # copy makes a product; join consumes a sum.  At runtime this is the
        # empty relation and no error at all -- which is the silence the type
        # system exists to break.
        with self.assertRaises(IllTyped):
            ty("copy ; join")

    def test_functors_do_not_constrain_their_arguments(self):
        self.assertEqual(ty("id + id"), "a + b <-> a + b")
        self.assertEqual(ty("id * id"), "a x b <-> a x b")

    def test_choice_forces_both_ends_to_agree(self):
        self.assertEqual(ty("id | id"), "a <-> a")

    def test_star_forces_a_type_to_itself(self):
        self.assertEqual(ty("swapsum^"), "a + a <-> a + a")


class TestEquirecursive(unittest.TestCase):
    """`mu X. F(X)` and `F(mu X. F(X))` are the same type, silently."""

    def test_a_mu_unifies_with_its_own_unfolding(self):
        Inference().unify(NAT, unfold(NAT), "test")

    def test_a_mu_unifies_across_several_unfoldings(self):
        # 1 + (1 + nat)  and  1 + (1 + (1 + nat)), i.e. two and three layers off.
        twice = TSum(TOne(), unfold(NAT))
        thrice = TSum(TOne(), twice)
        Inference().unify(NAT, twice, "test")
        Inference().unify(NAT, thrice, "test")
        Inference().unify(twice, thrice, "test")

    def test_unfolding_does_not_make_everything_equal(self):
        # The coinduction must not be so eager that it accepts a real clash.
        with self.assertRaises(IllTyped):
            Inference().unify(NAT, TSum(TZero(), NAT), "test")
        with self.assertRaises(IllTyped):
            Inference().unify(NAT, LIST, "test")

    def test_a_cycle_is_inferred_not_declared(self):
        # `pred^` closes a loop, and the loop *is* the recursive type.  Nothing
        # in the source of `downfrom` mentions a type at all.
        self.assertEqual(ty("inr! ^"), "mu X. a + X <-> mu X. a + X")

    def test_the_star_of_a_two_step_gets_a_two_step_mu(self):
        self.assertEqual(ty("(inr ; inr)^"), "mu X. a + (b + X) <-> mu X. a + (b + X)")

    def test_nat_and_list_come_out_of_the_libraries(self):
        schemes, _ = infer_program(lib("prelude.42"))
        # double = copy ; add, and copy forces the two summands to agree, which
        # turns add's free base case into 1 -- so this is exactly nat <-> nat.
        self.assertEqual(show_scheme(schemes["double"]), "mu X. 1 + X <-> mu Y. 1 + Y")
        schemes, _ = infer_program(lib("tour.42"))
        self.assertEqual(
            show_scheme(schemes["rev"]), "mu X. 1 + a x X <-> mu Y. 1 + a x Y"
        )
        self.assertEqual(
            show_scheme(schemes["palin"]), "mu X. 1 + a x X <-> mu X. 1 + a x X"
        )

    def test_unification_terminates_on_mutually_recursive_shapes(self):
        # Two different presentations of the same infinite tree.
        a = TMu(70, TSum(TOne(), TVar(70)))
        b = TSum(TOne(), TSum(TOne(), TMu(71, TSum(TOne(), TVar(71)))))
        Inference().unify(a, b, "test")


class TestUninhabitedCyclesAreStillErrors(unittest.TestCase):
    """A cycle is only trusted if the recursive type it names has values."""

    def test_mu_x_x_times_x_has_no_values(self):
        self.assertFalse(inhabited(TMu(80, TProd(TVar(80), TVar(80)))))

    def test_mu_x_one_plus_x_does(self):
        self.assertTrue(inhabited(NAT))
        self.assertTrue(inhabited(LIST))

    def test_a_product_needs_both_sides(self):
        self.assertFalse(inhabited(TProd(TZero(), TOne())))
        self.assertTrue(inhabited(TSum(TZero(), TOne())))

    def test_copy_star_is_rejected(self):
        # copy^ demands  a = a x a, i.e.  mu X. X x X, whose only inhabitants
        # would be infinite trees of pairs.  No recursion rescues it.
        with self.assertRaises(IllTyped) as cm:
            ty("copy^")
        self.assertIn("no finite values", str(cm.exception))

    def test_copy_choice_id_is_rejected(self):
        with self.assertRaises(IllTyped):
            ty("copy | id")


class TestRefold(unittest.TestCase):
    def test_one_unfolding_is_folded_back(self):
        self.assertEqual(refold(unfold(NAT)), NAT)
        self.assertEqual(refold(unfold(LIST)), LIST)

    def test_it_shows_up_in_inferred_types(self):
        # Without refold this reads  a + (mu X. a + X).
        self.assertEqual(ty("inr! ^"), "mu X. a + X <-> mu X. a + X")

    def test_it_leaves_non_recursive_types_alone(self):
        t = TSum(TOne(), TProd(TVar(1), TZero()))
        self.assertEqual(refold(t), t)


class TestDaggerReversesType(unittest.TestCase):
    """If  t : A <-> B  then  t! : B <-> A, and nothing else changes."""

    def test_on_every_primitive(self):
        for name in PRIM_SCHEMES:
            with self.subTest(prim=name):
                s = infer_term(parse_term(name), {})
                d = infer_term(parse_term(name + "!"), {})
                self.assertEqual(show_scheme(Scheme(s.cod, s.dom)), show_scheme(d))

    def test_on_every_definition_in_every_library(self):
        checked = 0
        for path in LIBS:
            with open(path, encoding="utf-8") as fh:
                defs = parse_program(fh.read())
            schemes, _ = infer_program(defs)
            for name, body in defs.items():
                self.assertIn(name, schemes)
                s = infer_term(body, schemes)
                d = infer_term(dagger(body), schemes)
                # `params` must be carried over, not dropped: for a combinator
                # `dagger` inverts the *result* and leaves the parameter arrows
                # alone (that is what makes `ctrl! m` equal `ctrl m!`), so the
                # expected scheme keeps its parameters and swaps only the ends.
                with self.subTest(lib=os.path.basename(path), name=name):
                    want = Scheme(s.cod, s.dom, params=s.params)
                    if show_scheme(want) != show_scheme(d):
                        # Equirecursive types have no canonical syntactic form,
                        # so two presentations of the same infinite tree can
                        # print differently -- `meta.42`'s states nest a `mu`
                        # inside a `mu` deeply enough to reach that.  Falling
                        # back to the unifier tests the property rather than the
                        # printer; the string comparison stays first because it
                        # is the stronger check where it applies.
                        self.assertSameType(want, d)
                checked += 1
        self.assertEqual(checked, 263)

    def assertSameType(self, want: Scheme, got: Scheme) -> None:
        inf = Inference()
        a, b = inf.instantiate(want), inf.instantiate(got)
        try:
            inf.unify(a.dom, b.dom, "dom")
            inf.unify(a.cod, b.cod, "cod")
        except Rel42Error as exc:  # pragma: no cover -- a real failure
            self.fail(f"dagger did not reverse the type: {exc}")

    def test_double_dagger_is_the_original_type(self):
        for src in ["dist", "copy ; swapprod", "inl ; swapsum", "id + copy", "inr!^"]:
            with self.subTest(src=src):
                self.assertEqual(ty(src), ty(f"({src})!!"))


class TestRecursiveGroups(unittest.TestCase):
    def test_self_recursion_is_one_group(self):
        gs = groups(lib("prelude.42"))
        self.assertIn(["add"], gs)
        self.assertIn(["append"], gs)

    def test_mutual_recursion_is_grouped_together(self):
        # cipher.42's cbc and cbcstep call each other, so they must be solved
        # as a unit against monomorphic assumptions.
        gs = groups(lib("cipher.42"))
        self.assertIn(["cbc", "cbcstep"], gs)

    def test_dependencies_come_before_dependents(self):
        defs = lib("arith.42")
        seen = set()
        for comp in groups(defs):
            for n in comp:
                from rel42.types import references

                for m in references(defs[n]) & defs.keys():
                    self.assertTrue(m in seen or m in comp, f"{n} before {m}")
            seen.update(comp)

    def test_the_mutually_recursive_group_actually_types(self):
        schemes, errors = infer_program(lib("cipher.42"))
        self.assertIn("cbc", schemes)
        self.assertIn("cbcstep", schemes)
        self.assertEqual(errors, {})


class TestPrinter(unittest.TestCase):
    """Neither operator is associative, so the printer must not flatten."""

    NAMES = {0: "a", 1: "b", 2: "c"}

    def test_products_are_not_associative(self):
        a, b, c = TVar(0), TVar(1), TVar(2)
        left = show_type(TProd(TProd(a, b), c), self.NAMES)
        right = show_type(TProd(a, TProd(b, c)), self.NAMES)
        self.assertNotEqual(left, right)
        self.assertEqual(left, "a x b x c")
        self.assertEqual(right, "a x (b x c)")

    def test_sums_are_not_associative(self):
        a, b, c = TVar(0), TVar(1), TVar(2)
        self.assertEqual(show_type(TSum(TSum(a, b), c), self.NAMES), "a + b + c")
        self.assertEqual(show_type(TSum(a, TSum(b, c)), self.NAMES), "a + (b + c)")

    def test_product_binds_tighter_than_sum(self):
        a, b, c = TVar(0), TVar(1), TVar(2)
        self.assertEqual(show_type(TSum(TProd(a, b), c), self.NAMES), "a x b + c")
        self.assertEqual(show_type(TProd(TSum(a, b), c), self.NAMES), "(a + b) x c")

    def test_mu_is_looser_than_both_and_gets_bracketed_inside_them(self):
        self.assertEqual(show_scheme(Scheme(NAT, NAT)), "mu X. 1 + X <-> mu X. 1 + X")
        self.assertEqual(
            show_scheme(Scheme(TProd(NAT, TOne()), TOne())),
            "(mu X. 1 + X) x 1 <-> 1",
        )

    def test_binders_get_capitals_and_free_variables_letters(self):
        s = show_scheme(Scheme(LIST, TVar(9)))
        self.assertEqual(s, "mu X. 1 + a x X <-> a")

    def test_constants(self):
        self.assertEqual(show_type(TZero()), "0")
        self.assertEqual(show_type(TOne()), "1")

    def test_rot3_matches_its_comment_in_prelude(self):
        self.assertEqual(ty("assocprod ; swapprod"), "a x (b x c) <-> c x (a x b)")


class TestLibrariesAreWellTyped(unittest.TestCase):
    """Every definition in every .42 file types.

    263 definitions written with no type system in sight, no annotation added to
    any of them, and nothing left over.
    """

    def test_all_263_definitions_type(self):
        total = 0
        for path in LIBS:
            with open(path, encoding="utf-8") as fh:
                defs = parse_program(fh.read())
            schemes, errors = infer_program(defs)
            with self.subTest(lib=os.path.basename(path)):
                self.assertEqual(errors, {}, f"failures: {list(errors)}")
                self.assertEqual(set(schemes), set(defs))
            total += len(defs)
        self.assertEqual(total, 263)

    def test_the_plumbing_layer(self):
        schemes, _ = infer_program(lib("prelude.42"))
        self.assertEqual(show_scheme(schemes["not"]), "a + b <-> b + a")
        self.assertEqual(show_scheme(schemes["swap"]), "a x b <-> b x a")
        self.assertEqual(show_scheme(schemes["rot3"]), "a x (b x c) <-> c x (a x b)")
        self.assertEqual(show_scheme(schemes["succ"]), "a <-> b + a")
        self.assertEqual(show_scheme(schemes["pred"]), "a + b <-> b")
        self.assertEqual(show_scheme(schemes["toggle"]), "a + a <-> a + a")
        self.assertEqual(
            show_scheme(schemes["downfrom"]), "mu X. a + X <-> mu X. a + X"
        )

    def test_add_takes_a_nat_on_the_left(self):
        schemes, _ = infer_program(lib("prelude.42"))
        self.assertEqual(
            show_scheme(schemes["add"]),
            "(mu X. 1 + X) x (mu Y. a + Y) <-> mu Y. a + Y",
        )

    def test_a_flippable_target_must_be_a_symmetric_sum(self):
        # cipher.42's cnot1 negates its second component, which forces both
        # summands of that component to be the same type -- the type-level
        # content of "that argument is a bit".
        schemes, _ = infer_program(lib("cipher.42"))
        self.assertEqual(
            show_scheme(schemes["cnot1"]), "(a + b) x (c + c) <-> (a + b) x (c + c)"
        )


class TestConform(unittest.TestCase):
    """Does a value inhabit a type?"""

    def test_units_and_the_empty_type(self):
        self.assertIsNone(conform(UNIT, TOne()))
        self.assertIsNotNone(conform(Inl(UNIT), TOne()))
        # Nothing at all inhabits 0.
        self.assertIsNotNone(conform(UNIT, TZero()))

    def test_a_free_variable_accepts_anything(self):
        # It is universally quantified: the caller picks what it stands for.
        for v in [UNIT, Inl(UNIT), Pair(UNIT, UNIT), from_nat(3)]:
            self.assertIsNone(conform(v, TVar(0)))

    def test_nats_inhabit_nat(self):
        for n in range(5):
            self.assertIsNone(conform(from_nat(n), NAT), f"{n} : nat")

    def test_a_pair_is_not_a_nat(self):
        self.assertIsNotNone(conform(Pair(UNIT, UNIT), NAT))

    def test_lists_inhabit_list(self):
        for items in [[], [from_nat(1)], [from_nat(1), from_nat(2)]]:
            self.assertIsNone(conform(from_list(items), LIST))

    def test_sums_and_products_descend(self):
        self.assertIsNone(conform(Pair(UNIT, Inl(UNIT)), TProd(TOne(), TSum(TOne(), TZero()))))
        self.assertIsNotNone(
            conform(Pair(UNIT, Inr(UNIT)), TProd(TOne(), TSum(TOne(), TZero())))
        )

    def test_it_reports_the_innermost_clash(self):
        # The outer pair is fine; the right component is not a nat.
        bad = conform(Pair(from_nat(1), UNIT), TProd(NAT, NAT))
        self.assertIsNotNone(bad)
        self.assertEqual(bad[0], UNIT)


class TestSoundnessSpotCheck(unittest.TestCase):
    """Outputs land in the codomain the checker predicted.

    Not a proof, and weakened wherever a type has free variables (`conform`
    accepts anything there, correctly).  It still exercises the `mu`, `1` and
    `0` structure, which is where an unsound rule would show up first.
    """

    CASES = [
        ("prelude.42", "add", "(2, 3)", False),
        ("prelude.42", "add", "5", True),
        ("prelude.42", "append", "([1,2], [3])", False),
        ("prelude.42", "append", "[1,2,3]", True),
        ("prelude.42", "double", "3", False),
        ("prelude.42", "double", "6", True),
        ("prelude.42", "downfrom", "3", False),
        ("tour.42", "rev", "[1,2,3]", False),
        ("tour.42", "palin", "[1,2,1]", False),
        ("arith.42", "divmod", "(7, 2)", False),
        ("arith.42", "divexact", "(3, 6)", False),
        ("arith.42", "sub", "(5, 3)", False),
    ]

    def test_every_result_inhabits_the_codomain(self):
        from rel42 import parse_value, run

        for fname, name, val, backward in self.CASES:
            defs = lib(fname)
            schemes, _ = infer_program(defs)
            term = Ref(name)
            if backward:
                term = dagger(term)
            scheme = infer_term(term, schemes)
            v = parse_value(val)
            self.assertIsNone(
                conform(v, scheme.dom),
                f"{name}: the test's own input does not fit the domain",
            )
            results = run(term, v, defs)
            self.assertTrue(results, f"{name}({val}) produced nothing")
            for r in results:
                with self.subTest(defn=name, value=val, backward=backward):
                    self.assertIsNone(
                        conform(r, scheme.cod),
                        f"{name}({val}) returned {r!r}, outside its codomain",
                    )


class TestCliTypeGate(unittest.TestCase):
    """The CLI rejects; `core.run` does not."""

    def call(self, *argv):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        from rel42.__main__ import main

        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue() + err.getvalue()

    def test_shape_mismatch_is_rejected(self):
        code, out = self.call("run", os.path.join(ROOT, "prelude.42"), "swap", "5")
        self.assertEqual(code, 1)
        self.assertIn("does not fit the domain", out)

    def test_untyped_restores_the_relational_answer(self):
        code, out = self.call(
            "run", os.path.join(ROOT, "prelude.42"), "swap", "5", "--untyped"
        )
        self.assertEqual(code, 0)
        self.assertIn("empty: no result", out)

    def test_well_typed_partiality_is_not_an_error(self):
        # This is the distinction the gate has to get right: `divexact(3, 7)` is
        # empty because 3 does not divide 7, not because anything is ill-shaped.
        for name, val in [("divexact", "(3, 7)"), ("sub", "(3, 5)")]:
            code, out = self.call("run", os.path.join(ROOT, "arith.42"), name, val)
            with self.subTest(defn=name):
                self.assertEqual(code, 0)
                self.assertIn("empty: no result", out)

    def test_pred_of_zero_is_still_empty(self):
        code, out = self.call("run", os.path.join(ROOT, "prelude.42"), "pred", "0")
        self.assertEqual(code, 0)
        self.assertIn("empty: no result", out)

    def test_an_ill_typed_definition_is_rejected(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".42", delete=False) as fh:
            fh.write("def bad = copy ; join\n")
            path = fh.name
        try:
            code, out = self.call("run", path, "bad", "3")
            self.assertEqual(code, 1)
            self.assertIn("ill-typed", out)
        finally:
            os.unlink(path)

    def test_law_is_gated_too(self):
        code, _ = self.call("law", os.path.join(ROOT, "prelude.42"), "swap", "5")
        self.assertEqual(code, 1)

    def test_core_run_is_still_untyped(self):
        # The library keeps saying what Rel says: a shape mismatch denotes the
        # empty relation, and that is not an error.
        from rel42 import run

        self.assertEqual(run(parse_term("swapprod"), Inl(UNIT)), set())


class TestTypeDirectedPrinting(unittest.TestCase):
    """`show_as` settles the encoding ambiguities that `show` has to guess."""

    def test_the_collision_itself(self):
        # L () is the nat 0, the empty list, and false.  show must guess; given
        # a type there is nothing to guess.
        empty = Inl(UNIT)
        self.assertEqual(show(empty), "0")
        self.assertEqual(show_as(empty, NAT), "0")
        self.assertEqual(show_as(empty, LIST), "[]")
        self.assertEqual(show_as(empty, TSum(TOne(), TOne())), "L ()")

    def test_nats_and_lists(self):
        self.assertEqual(show_as(from_nat(3), NAT), "3")
        self.assertEqual(show_as(from_list([from_nat(1), from_nat(2)]), LIST), "[1, 2]")

    def test_it_descends_into_pairs(self):
        # This is why products are walked: an empty list hides inside a pair.
        v = Pair(from_list([from_nat(1)]), Inl(UNIT))
        self.assertEqual(show_as(v, TProd(LIST, LIST)), "([1], [])")

    def test_a_shifted_mu_is_still_recognised_as_a_list(self):
        # `append`'s second argument arrives as  b + (mu Y. a x (b + Y)) --
        # the same infinite tree as a list, with the binder elsewhere.  Syntactic
        # matching misses it; unification does not.
        shifted = TSum(TVar(2), TMu(90, TProd(TVar(9), TSum(TVar(2), TVar(90)))))
        self.assertEqual(show_as(Inl(UNIT), shifted), "[]")

    def test_raw_and_no_type_fall_back_to_guessing(self):
        self.assertEqual(show_as(Inl(UNIT), LIST, raw=True), "L ()")
        self.assertEqual(show_as(Inl(UNIT), None), "0")

    def test_a_polymorphic_type_does_not_degrade_output(self):
        # succ = inr has type  a <-> b + a, which never says "nat".  Printing
        # `succ 3` as `R 3` because of that would be a regression, so a sum the
        # type does not identify falls back to the old heuristics wholesale.
        schemes, _ = infer_program(lib("prelude.42"))
        cod = schemes["succ"].cod
        self.assertEqual(show_as(from_nat(4), cod), "4")

    def test_strings_survive(self):
        s = from_string("abc")
        listish = TMu(91, TSum(TOne(), TProd(byte_type(), TVar(91))))
        self.assertEqual(show_as(s, listish), '"abc"')

    def test_an_empty_string_prints_as_a_string(self):
        listish = TMu(92, TSum(TOne(), TProd(byte_type(), TVar(92))))
        self.assertEqual(show_as(Inl(UNIT), listish), '""')

    def test_as_list_still_refuses_empty_without_permission(self):
        # The old behaviour is what `show` depends on, so it must not change.
        self.assertIsNone(as_list(Inl(UNIT)))
        self.assertEqual(as_list(Inl(UNIT), allow_empty=True), [])

    def test_cli_prints_the_empty_list(self):
        from contextlib import redirect_stdout
        from io import StringIO

        from rel42.__main__ import main

        buf = StringIO()
        with redirect_stdout(buf):
            main(["run", os.path.join(ROOT, "prelude.42"), "append", "[1,2]", "-b"])
        out = buf.getvalue()
        self.assertIn("([], [1, 2])", out)
        self.assertIn("([1, 2], [])", out)
        self.assertNotIn(", 0)", out)


class TestParameterisedDefinitions(unittest.TestCase):
    """`def f p = ...` -- abstraction over terms, not over values.

    The property under test throughout is that inversion survives it: `dagger`
    stays total, stays an involution, and commutes with reduction, so
    `dagger(f a)` really is the adjoint of `f a`.
    """

    SRC = """
    def mat    = dist ; (unitprod + unitprod)
    def ctrl m = mat ; (id + m) ; mat!
    def twice f = f ; f
    def cx     = ctrl swapsum
    def ccx    = ctrl cx
    def cdg m  = ctrl m!
    """

    def env(self):
        return parse_program(self.SRC)

    # -- syntax ------------------------------------------------------------

    def test_parameters_parse_as_variables_not_references(self):
        env = self.env()
        self.assertIsInstance(env["ctrl"], Fun)
        self.assertEqual(env["ctrl"].param, "m")
        # `m` inside the body is a Var; `mat` is still a Ref.
        names = {t.name for t in _walk(env["ctrl"].body) if isinstance(t, Var)}
        self.assertEqual(names, {"m"})

    def test_application_is_juxtaposition(self):
        env = self.env()
        self.assertEqual(env["cx"], App(Ref("ctrl"), Prim("swapsum")))

    def test_postfix_binds_tighter_than_application(self):
        # `ctrl m!` is `ctrl (m!)`, which is what you want: the argument is the
        # thing being inverted.
        body = self.env()["cdg"].body
        self.assertEqual(body, App(Ref("ctrl"), Var("m", True)))

    def test_def_is_a_hard_keyword(self):
        # Without this, `def f = x def g = y` would read `x def` as application.
        env = parse_program("def f = id\ndef g = swapsum\n")
        self.assertEqual(set(env), {"f", "g"})

    def test_a_parameter_may_not_shadow_a_primitive(self):
        with self.assertRaises(ParseError):
            parse_program("def f id = id\n")

    def test_a_repeated_parameter_is_rejected(self):
        with self.assertRaises(ParseError):
            parse_program("def f m m = m\n")

    # -- inversion ---------------------------------------------------------

    def test_dagger_is_still_an_involution(self):
        for name, body in self.env().items():
            with self.subTest(defn=name):
                self.assertEqual(dagger(dagger(body)), body)

    def test_dagger_commutes_with_reduction(self):
        """The property the whole design rests on.

        `dagger` may be applied before or after applications are reduced away,
        and the two agree -- so `dagger(ctrl x)` is the adjoint of `ctrl x`.
        """
        env = self.env()
        for name in ["cx", "ccx", "cdg"]:
            with self.subTest(defn=name):
                t = env[name]
                self.assertEqual(
                    expand(dagger(t), env), dagger(expand(t, env))
                )

    def test_substitution_discharges_the_inversion(self):
        # dagger pushes the `!` onto the variable's flag; substitution applies it.
        self.assertEqual(substitute(Var("m", True), "m", Prim("inl")), Prim("inl", True))
        self.assertEqual(substitute(Var("m"), "m", Prim("inl")), Prim("inl"))

    def test_the_dagger_of_a_controlled_gate_controls_the_dagger(self):
        # (Ctrl U)-dagger = Ctrl U-dagger, which is the physics and also what
        # falls out of the two conventions in `core.dagger`.
        env = self.env()
        lhs = expand(dagger(App(Ref("ctrl"), Prim("inl"))), env)
        rhs = expand(App(Ref("ctrl"), Prim("inl", True)), env)
        # Same up to `id` vs `id!`, which denote the same relation; compare types
        # and behaviour instead of syntax.
        schemes, _ = infer_program(env)
        self.assertEqual(
            show_scheme(infer_term(lhs, schemes)),
            show_scheme(infer_term(rhs, schemes)),
        )

    # -- reduction ---------------------------------------------------------

    def test_expand_env_removes_every_application(self):
        env = expand_env(self.env())
        for name, body in env.items():
            with self.subTest(defn=name):
                self.assertFalse(
                    any(isinstance(t, App) for t in _walk(body)),
                    "an application survived expansion",
                )

    def test_expand_env_keeps_the_combinators(self):
        env = expand_env(self.env())
        self.assertTrue(is_combinator(env["ctrl"]))
        self.assertFalse(is_combinator(env["cx"]))

    def test_expand_env_leaves_recursion_alone(self):
        # A Ref is unfolded only when it heads an application, so an ordinary
        # recursive definition survives for the evaluator to unfold lazily.
        env = expand_env(lib("prelude.42"))
        self.assertIn("add", str(env["add"]))

    def test_the_reduced_gate_denotes_what_the_hand_written_one_did(self):
        env = expand_env(self.env())
        hand = parse_program(
            "def mat = dist ; (unitprod + unitprod)\n"
            "def ccx = mat ; (id + (mat ; (id + swapsum) ; mat!)) ; mat!\n"
        )
        from rel42 import run

        basis = [
            Pair(a, Pair(b, c))
            for a in [Inl(UNIT), Inr(UNIT)]
            for b in [Inl(UNIT), Inr(UNIT)]
            for c in [Inl(UNIT), Inr(UNIT)]
        ]
        for v in basis:
            with self.subTest(value=v):
                self.assertEqual(
                    run(Ref("ccx"), v, env), run(Ref("ccx"), v, hand)
                )

    # -- types -------------------------------------------------------------

    def test_a_combinator_gets_a_combinator_type(self):
        schemes, errors = infer_program(self.env())
        self.assertEqual(errors, {})
        self.assertEqual(
            show_scheme(schemes["ctrl"]),
            "(a <-> a) -> ((1 + 1) x a <-> (1 + 1) x a)",
        )
        self.assertEqual(show_scheme(schemes["twice"]), "(a <-> a) -> (a <-> a)")

    def test_the_instantiations_type_as_before(self):
        schemes, _ = infer_program(self.env())
        self.assertEqual(
            show_scheme(schemes["cx"]),
            "(1 + 1) x (a + a) <-> (1 + 1) x (a + a)",
        )

    def test_swap_leaves_the_parameters_alone(self):
        # Forced by core.dagger's convention: the argument keeps its type and
        # only the result is inverted.
        schemes, _ = infer_program(self.env())
        s = schemes["ctrl"]
        self.assertEqual(s.swap().params, s.params)
        self.assertEqual(s.swap().dom, s.cod)

    def test_an_unapplied_combinator_is_not_a_relation(self):
        # Every operator composes relations, so a missing argument is an error.
        _, errors = infer_program(parse_program(self.SRC + "\ndef bad = ctrl ; id\n"))
        self.assertIn("bad", errors)
        self.assertIn("combinator", str(errors["bad"]))

    def test_too_many_arguments_is_an_error(self):
        _, errors = infer_program(parse_program(self.SRC + "\ndef oops = cx swapsum\n"))
        self.assertIn("oops", errors)

    def test_second_order_only(self):
        # A parameter denotes a relation, so a combinator cannot be an argument.
        _, errors = infer_program(parse_program(self.SRC + "\ndef no = twice ctrl\n"))
        self.assertIn("no", errors)
        self.assertIn("second-order", str(errors["no"]))

    def test_a_recursive_combinator_is_typed_at_its_arity(self):
        # `rep m` is m composed with itself one or more times -- a combinator that
        # calls itself, so the recursive group's assumption has to carry a
        # parameter too.
        env = parse_program("def rep m = m | (m ; rep m)\n")
        schemes, errors = infer_program(env)
        self.assertEqual(errors, {})
        self.assertTrue(schemes["rep"].is_combinator)
        self.assertEqual(show_scheme(schemes["rep"]), "(a <-> a) -> (a <-> a)")

    def test_a_recursive_combinator_that_cannot_be_typed_says_why(self):
        # This one demands  A = (1 + 1) x A, whose only values are infinite.
        env = parse_program(
            "def mat = dist ; (unitprod + unitprod)\n"
            "def deep m = m | (mat ; (id + (deep m)) ; mat!)\n"
        )
        _, errors = infer_program(env)
        self.assertIn("deep", errors)
        self.assertIn("no finite values", str(errors["deep"]))

    # -- running -----------------------------------------------------------

    def test_running_a_combinator_is_refused(self):
        from rel42 import run

        env = expand_env(self.env())
        with self.assertRaises(NotARelation):
            run(Ref("ctrl"), Inl(UNIT), env)


def _walk(t):
    """Every subterm, for tests that need to look inside."""
    yield t
    for f in ("s", "t", "f", "a", "body"):
        if hasattr(t, f):
            child = getattr(t, f)
            if isinstance(child, Term):
                yield from _walk(child)


class TestAbbreviations(unittest.TestCase):
    """`type nat = mu X. 1 + X` -- a display layer, and nothing more.

    The property that makes it safe is that matching is *one-way*: an
    abbreviation may describe the type it is offered but never constrain it.
    Without that, `nat` would match every type variable.
    """

    SRC = """
    type nat    = mu X. 1 + X
    type list a = mu X. 1 + (a x X)
    def double  = copy ; add
    def add     = dist ; (unitprod + (add ; inr)) ; join
    """

    def prog(self):
        return parse_program(self.SRC)

    def test_declarations_are_parsed(self):
        types = self.prog().types
        self.assertEqual([a.name for a in types], ["nat", "list"])
        self.assertEqual(types[0].params, ())
        self.assertEqual(len(types[1].params), 1)

    def test_a_declaration_is_the_type_it_names(self):
        nat = self.prog().types[0]
        self.assertIsNotNone(match_type(nat.body, NAT, frozenset()))

    def test_matching_is_up_to_unfolding(self):
        nat = self.prog().types[0]
        self.assertIsNotNone(match_type(nat.body, unfold(NAT), frozenset()))

    def test_matching_never_binds_the_subject(self):
        # The whole safety property: `nat` must not match an arbitrary variable,
        # or every inferred type would print as `nat`.
        nat = self.prog().types[0]
        self.assertIsNone(match_type(nat.body, TVar(9), frozenset()))
        self.assertIsNone(match_type(nat.body, TOne(), frozenset()))

    def test_a_parameterised_abbreviation_extracts_its_argument(self):
        lst = self.prog().types[1]
        found = match_type(lst.body, LIST, frozenset(lst.params))
        self.assertIsNotNone(found)
        self.assertEqual(found[lst.params[0]], TVar(9))

    def test_it_shows_up_in_printed_types(self):
        prog = self.prog()
        schemes, errors = infer_program(prog)
        self.assertEqual(errors, {})
        self.assertEqual(show_scheme(schemes["double"], prog.types), "nat <-> nat")

    def test_the_libraries_read_better_for_it(self):
        # tour.42 declares both; `rev` and `palin` are the payoff.
        prog = lib("tour.42")
        schemes, _ = infer_program(prog)
        self.assertEqual(show_scheme(schemes["rev"], prog.types), "list a <-> list a")
        self.assertEqual(show_scheme(schemes["palin"], prog.types), "list a <-> list a")
        # and without the declarations, the same type, spelled out
        self.assertEqual(
            show_scheme(schemes["rev"]), "mu X. 1 + a x X <-> mu Y. 1 + a x Y"
        )

    def test_without_declarations_nothing_changes(self):
        # The checker is unaffected: same types, only the rendering differs.
        prog = self.prog()
        schemes, _ = infer_program(prog)
        self.assertEqual(
            show_scheme(schemes["double"]), "mu X. 1 + X <-> mu Y. 1 + Y"
        )

    def test_declaring_a_type_does_not_change_inference(self):
        bare = parse_program(self.SRC.replace("type nat    = mu X. 1 + X\n", ""))
        a, _ = infer_program(self.prog())
        b, _ = infer_program(bare)
        for name in a:
            with self.subTest(defn=name):
                self.assertEqual(show_scheme(a[name]), show_scheme(b[name]))

    def test_the_more_specific_declaration_should_come_first(self):
        # `nat` also matches `natp 1`, so order decides.  First match wins.
        prog = parse_program(
            "type nat = mu X. 1 + X\ntype natp a = mu X. a + X\ndef d = copy ; add\n"
            "def add = dist ; (unitprod + (add ; inr)) ; join\n"
        )
        schemes, _ = infer_program(prog)
        self.assertEqual(show_scheme(schemes["d"], prog.types), "nat <-> nat")
        self.assertEqual(
            show_scheme(schemes["d"], list(reversed(prog.types))), "natp 1 <-> natp 1"
        )

    def test_x_is_the_product_operator_not_a_variable(self):
        with self.assertRaises(ParseError):
            parse_program("type bad x = x\n")

    def test_a_free_name_in_a_declaration_is_rejected(self):
        with self.assertRaises(ParseError) as cm:
            parse_program("type bad = mu X. 1 + Y\n")
        self.assertIn("not bound", str(cm.exception))

    def test_x_is_never_generated_as_a_variable_name(self):
        # cipher.42 has a definition with 27 type variables; without excluding
        # `x` the printer would emit `(x + x) x (a + b)`.
        schemes, _ = infer_program(lib("cipher.42"))
        for name, s in schemes.items():
            with self.subTest(defn=name):
                self.assertNotIn("x", _names(s).values())

    def test_duplicate_declarations_are_rejected(self):
        with self.assertRaises(ParseError):
            parse_program("type nat = 1\ntype nat = 0\n")

    def test_abbreviations_survive_expansion(self):
        prog = expand_env(self.prog())
        self.assertEqual([a.name for a in prog.types], ["nat", "list"])

    def test_a_file_with_no_declarations_still_works(self):
        prog = parse_program("def f = id\n")
        self.assertEqual(prog.types, [])


class TestShellWrappers(unittest.TestCase):
    """`./42` and `./42q`.

    Every transcript in the manual and the README is written with these, so a
    break here breaks the documentation.
    """

    #: The documented setup: the repository root on PATH, so the scripts are
    #: reachable by name.  Set explicitly here rather than relying on the
    #: developer's shell profile, so the test asserts what the docs promise
    #: without requiring anyone to have followed them.
    @staticmethod
    def env():
        e = dict(os.environ)
        e["PATH"] = ROOT + os.pathsep + e.get("PATH", "")
        return e

    def sh(self, cmd, cwd=None):
        import subprocess

        r = subprocess.run(
            cmd, shell=True, cwd=cwd or ROOT, capture_output=True, text=True,
            env=self.env(),
        )
        return r.returncode, r.stdout + r.stderr

    def test_they_are_executable(self):
        for name in ["42", "42q"]:
            with self.subTest(script=name):
                self.assertTrue(os.access(os.path.join(ROOT, name), os.X_OK))

    def test_run_is_the_default_subcommand(self):
        code, out = self.sh('42 prelude append "([1,2], [3])"')
        self.assertEqual(code, 0)
        self.assertIn("[1, 2, 3]", out)

    def test_a_subcommand_is_used_when_given(self):
        code, out = self.sh("42 type prelude")
        self.assertEqual(code, 0)
        self.assertIn("double    : nat <-> nat", out)

    def test_the_extension_is_optional_but_accepted(self):
        for arg in ["prelude", "prelude.42"]:
            with self.subTest(arg=arg):
                code, out = self.sh(f"42 {arg} double 3")
                self.assertEqual(code, 0)
                self.assertIn("6", out)

    def test_it_agrees_with_the_long_form(self):
        a = self.sh('42 prelude append "([1,2], [3])"')
        b = self.sh('python3 -m rel42 run prelude.42 append "([1,2], [3])"')
        self.assertEqual(a, b)

    def test_it_works_from_another_directory(self):
        # Both spellings: by name via PATH, and in place by absolute path.
        code, out = self.sh("42 prelude double 3", cwd="/")
        self.assertEqual(code, 0, out)
        self.assertIn("6", out)
        code, out = self.sh(f"{os.path.join(ROOT, '42')} prelude double 3", cwd="/")
        self.assertEqual(code, 0, out)
        self.assertIn("6", out)

    def test_the_in_place_spelling_also_works(self):
        # `./42` needs no PATH setup, which is what the docs offer as the
        # alternative.
        import subprocess

        r = subprocess.run(
            "./42 prelude double 3", shell=True, cwd=ROOT,
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("6", r.stdout)

    def test_the_q42_wrapper_finds_its_libraries_by_bare_name(self):
        code, out = self.sh('42q gates bell "|00>"')
        self.assertEqual(code, 0)
        self.assertIn("|11>", out)
        code, out = self.sh("42q unitary gates")
        self.assertEqual(code, 0)
        self.assertIn("unitary", out)

    def test_equal_decides_rather_than_denies(self):
        """`42q equal` is the command form of QMANUAL §6.1's decidability claim.

        Three outcomes matter: agreement, disagreement with the offending cell
        named, and a type mismatch that is refused before any matrix is built.
        """
        code, out = self.sh("42q equal gates x x")
        self.assertEqual(code, 0, out)
        self.assertIn("equal on 2 dimension(s)", out)
        # and no hedging: an exact comparison must not describe itself as one
        # made to within a tolerance
        self.assertNotIn("tolerance", out)

        code, out = self.sh("42q equal gates s t")
        self.assertEqual(code, 1, out)
        self.assertIn("differ at", out)

        code, out = self.sh("42q equal gates cx x")
        self.assertEqual(code, 1, out)
        self.assertIn("different types", out)

    def test_equal_decides_a_derived_identity(self):
        """`s ; s` and `z` are the same gate, and nothing here rounds."""
        # Written into a scratch file so the test does not depend on the gate
        # library happening to carry two spellings of the same thing.
        import tempfile, os as _os

        src = ("type qubit = 1 + 1\n"
               "def ss = (id + (omega;omega)) ; (id + (omega;omega))\n"
               "def zz = id + (omega;omega;omega;omega)\n")
        with tempfile.NamedTemporaryFile("w", suffix=".42", delete=False) as fh:
            fh.write(src)
            path = fh.name
        try:
            code, out = self.sh(f"42q equal {path} ss zz")
            self.assertEqual(code, 0, out)
            self.assertIn("equal on 2 dimension(s)", out)
            self.assertNotIn("tolerance", out)
        finally:
            _os.unlink(path)

    def test_an_unknown_file_still_reports_itself(self):
        # No match, so the argument is passed through untouched and the Python
        # layer gives its own message rather than the wrapper inventing one.
        code, out = self.sh("42 nosuchfile double 3")
        self.assertEqual(code, 1)
        self.assertIn("no such file", out.lower())

    def test_no_arguments_prints_help(self):
        code, out = self.sh("42")
        self.assertIn("usage", out.lower())


class TestErrors(unittest.TestCase):
    def test_unknown_primitive_or_reference(self):
        with self.assertRaises(Rel42Error):
            infer_term(parse_term("nosuchthing"), {})

    def test_errors_are_rel42_errors_so_the_cli_catches_them(self):
        self.assertTrue(issubclass(IllTyped, Rel42Error))

    def test_a_failed_group_blocks_its_dependents_without_crashing(self):
        defs = parse_program("def bad = copy ; join\ndef worse = bad ; id\n")
        schemes, errors = infer_program(defs)
        self.assertEqual(schemes, {})
        self.assertIn("bad", errors)
        self.assertIn("worse", errors)
        self.assertIn("did not typecheck", str(errors["worse"]))

    def test_inference_state_is_not_shared_between_runs(self):
        i1, i2 = Inference(), Inference()
        self.assertEqual(i1.infer(parse_term("id"), {}), i2.infer(parse_term("id"), {}))


class TestOccursTerminatesOnCyclicSubstitutions(unittest.TestCase):
    """`occurs` must cut cycles, exactly as `unify` does with `assumed`.

    Substitutions here are deliberately cyclic -- that is what makes the types
    equirecursive -- so a walk with no visited-set follows one forever.  It went
    unnoticed because every library definition is small: the first program to
    trigger it was the Turing machine above, where `step^` forces the two ends
    of a configuration type that is already cyclic to be unified.  Before the
    fix this raised RecursionError from `occurs` rather than typing or reporting
    an error, and no recursion limit rescued it -- the walk does not terminate.
    """

    def test_the_turing_machine_types(self):
        with open(os.path.join(ROOT, "tm.42"), encoding="utf-8") as fh:
            src = fh.read()
        schemes, errors = infer_program(parse_program(src))
        self.assertEqual(errors, {}, "the machine should typecheck")
        self.assertIn("step", schemes)
        self.assertIn("inc", schemes)

    def test_occurs_cuts_a_cycle_rather_than_following_it(self):
        inf = Inference()
        loop, inner, other = inf.fresh(), inf.fresh(), inf.fresh()
        # Tie a knot by hand -- `loop := inner x loop` -- which is the shape a
        # cyclic substitution really has.  `other` is unbound, so asking whether
        # it occurs in `loop` is the question `_bind` asks, and answering it
        # means walking a cycle that does not contain the variable sought.
        inf.subst[loop.id] = TProd(inner, loop)
        self.assertFalse(inf.occurs(other.id, loop), "must terminate, and say no")
        self.assertTrue(inf.occurs(inner.id, loop), "inner really is in there")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    unittest.main(verbosity=2)
