"""Types for Q42.

The inference engine is `rel42.types`, reused whole: unification, the
equirecursive handling, generalisation, the grouping of recursive definitions,
and the printer all apply unchanged, because they are about *shapes* and Q42's
shapes are 42's shapes.  Only the primitive signatures differ, and they are
injected.

Two things about Q42 make types matter more here than they do in 42.

**They are not optional.**  In 42 an ill-shaped application yields the empty
relation, which is a real morphism of Rel, so the answer is semantically correct
even when it reflects a typo.  In Q42 it yields the zero column, and the zero
matrix is *not unitary* -- so a shape mismatch silently produces a term outside
the intended semantics, breaking the unitarity-by-construction guarantee that is
the whole point of the design.  Applying `omega` to a pair is enough to do it.

**They are still only shapes.**  Q42 needs no linear types, no ownership
tracking, no uncomputation inference -- the things Silq exists to provide.  Those
manage discarding, cloning and measurement, and Q42 has none of the three: there
is no `discard`, no `copy`, and no measurement.  Unitarity is not a typing
obligation, it is structural, guaranteed by the primitive set (Q42.md section 5).
So the checker only has to do what 42's already does.

`basis_of` is the one genuinely new piece, and it is what makes `matrix` and
`unitary` possible: to write a term's matrix down you must enumerate its domain,
and the type is the only thing that knows what that is.
"""

from __future__ import annotations

from typing import Dict, List

from rel42.types import (
    IllTyped,
    Inference,
    Scheme,
    TMu,
    TOne,
    TProd,
    TSum,
    TVar,
    TZero,
    Type,
    conform,
    infer_program,
    replace_var,
    infer_term,
    names_for,
    show_scheme,
    show_type,
)
from rel42.core import Value, UNIT, Inl, Inr, Pair

from .core import Q42Error

__all__ = [
    "PRIM_SCHEMES",
    "QUBIT",
    "basis_of",
    "conform",
    "free_vars",
    "ground",
    "dimension",
    "infer",
    "infer_all",
    "names_for",
    "qubits",
    "show_scheme",
    "show_type",
    "width",
]

_a, _b, _c = TVar(0), TVar(1), TVar(2)

#: A qubit is `1 + 1`: one injection is |0>, the other |1>.
QUBIT: Type = TSum(TOne(), TOne())

PRIM_SCHEMES: Dict[str, Scheme] = {
    "id": Scheme(_a, _a),
    # The rig-groupoid core.  Identical to 42's, because these are the same
    # isomorphisms -- over C they are permutation matrices, hence unitary.
    "swapsum": Scheme(TSum(_a, _b), TSum(_b, _a)),
    "assocsum": Scheme(TSum(_a, TSum(_b, _c)), TSum(TSum(_a, _b), _c)),
    "unitsum": Scheme(TSum(TZero(), _a), _a),
    "swapprod": Scheme(TProd(_a, _b), TProd(_b, _a)),
    "assocprod": Scheme(TProd(_a, TProd(_b, _c)), TProd(TProd(_a, _b), _c)),
    "unitprod": Scheme(TProd(TOne(), _a), _a),
    "dist": Scheme(TProd(TSum(_a, _b), _c), TSum(TProd(_a, _c), TProd(_b, _c))),
    # The two generators.  Note that both are *monomorphic*, unlike everything
    # above: `omega` is a scalar on the unit and `v` acts on one qubit.  42 has
    # no monomorphic primitive at all.
    "omega": Scheme(TOne(), TOne()),
    "v": Scheme(QUBIT, QUBIT),
}


def infer(term, env: Dict[str, Scheme] | None = None) -> Scheme:
    return infer_term(term, env or {}, PRIM_SCHEMES)


def infer_all(defs):
    return infer_program(defs, PRIM_SCHEMES)


# ---------------------------------------------------------------------------
# Enumerating a type.
# ---------------------------------------------------------------------------


def dimension(t: Type) -> int:
    """The number of basis values, i.e. the dimension of the Hilbert space."""
    return len(basis_of(t))


def basis_of(t: Type, limit: int = 1 << 14) -> List[Value]:
    """Every value of `t`, in a fixed order -- the computational basis.

    Refuses the types it cannot enumerate rather than guessing:

    * a variable, because a polymorphic term has no one matrix.  A gate written
      with `id` alone is genuinely dimension-agnostic and asking for its matrix
      is a category error, not a missing feature.
    * a `mu`, because it is infinite.  Q42 has no infinite-dimensional spaces,
      so in practice this means a term that recursed without consuming a qubit.
    """
    match t:
        case TZero():
            return []
        case TOne():
            return [UNIT]
        case TSum(a, b):
            out = [Inl(x) for x in basis_of(a, limit)]
            out += [Inr(y) for y in basis_of(b, limit)]
        case TProd(a, b):
            left, right = basis_of(a, limit), basis_of(b, limit)
            if len(left) * len(right) > limit:
                raise Q42Error(
                    f"that space has at least {len(left) * len(right)} "
                    f"dimensions; refusing to enumerate it"
                )
            out = [Pair(x, y) for x in left for y in right]
        case TVar(_):
            raise Q42Error(
                "cannot enumerate a type variable: the term is polymorphic, so "
                "it has no single matrix.  Apply it at a concrete type."
            )
        case TMu(_, _):
            raise Q42Error(
                "cannot enumerate a recursive type: it is infinite, and Q42 "
                "has no infinite-dimensional spaces"
            )
        case _:
            raise Q42Error(f"not a type: {t!r}")
    if len(out) > limit:
        raise Q42Error(f"that space has {len(out)} dimensions; refusing to enumerate")
    return out


def free_vars(t: Type, bound: frozenset = frozenset()) -> set:
    match t:
        case TVar(i):
            return set() if i in bound else {i}
        case TSum(a, b) | TProd(a, b):
            return free_vars(a, bound) | free_vars(b, bound)
        case TMu(v, body):
            return free_vars(body, bound | {v})
    return set()


def ground(scheme: Scheme, n: int | None = None) -> Scheme:
    """A concrete instance of `scheme`, so that a matrix can be written down.

    Most gates are more polymorphic than "a gate on n qubits", and honestly so:
    `x = swapsum` has type `a + b <-> b + a` because negation really is just the
    symmetry, and `cx`'s target is `a + a` because the only thing controlling `x`
    requires is that the target be a *symmetric* sum.  Neither has one matrix.

    Two ways to pick an instance:

    * by default, take every free variable to be `1`.  That turns `a + b` into
      `1 + 1`, which is a qubit, and is right for the single- and multi-qubit
      gates whose registers are already spelled out.
    * with `n`, unify the domain with an `n`-qubit register instead.  This is for
      the gates whose polymorphism hides a whole qubit -- `cswap`'s target is
      `a x a`, and `a` wants to be `1 + 1`, not `1`.
    """
    if scheme.params:
        raise Q42Error(
            "a combinator has no matrix until its arguments are supplied: "
            f"`{show_scheme(scheme)}` still takes {len(scheme.params)}"
        )

    if n is None:
        subst = {i: TOne() for i in free_vars(scheme.dom) | free_vars(scheme.cod)}
        dom, cod = scheme.dom, scheme.cod
        for i, r in subst.items():
            dom, cod = replace_var(dom, i, r), replace_var(cod, i, r)
        return Scheme(dom, cod)

    inf = Inference(PRIM_SCHEMES)
    got = inf.instantiate(scheme)
    inf.unify(got.dom, qubits(n), f"reading `{show_scheme(scheme)}` at {n} qubit(s)")
    return inf.generalise(got)


def width(t: Type) -> int | None:
    """How many qubits `t` encodes, or `None` if it is not a register.

    An emitter targeting qubit hardware needs this and the language does not:
    `1 + (1 + 1)` is a perfectly good type and a perfectly bad register, being a
    three-dimensional space that no number of two-way lanes can hold.  The test
    is *not* "is the dimension a power of two", which would accept that type's
    sibling `(1 + 1) + (1 + 1)` for the wrong reason and is anyway not something
    you can read off a type.  It is structural, one clause per constructor:

        1        is a register of no qubits at all -- one state, nothing to store
        a + b    is a register when a and b are registers of the SAME width,
                 the choice between them supplying one further qubit
        a x b    is a register when both are, of the widths added

    So `qubit = 1 + 1` comes out at 1, `qubit x qubit` at 2, and `1 + (1 + 1)` at
    `None` because its branches disagree.  Bracketing is irrelevant: a left-nested
    product is as good as a right-nested one, `assocprod` being the term that
    moves between them.

    `0`, a variable and a `mu` are all rejected -- the first has no values, the
    second no fixed dimension, the third infinitely many.  A `mu` whose variable
    does not occur is not really recursive and is looked through.
    """
    match t:
        case TOne():
            return 0
        case TSum(a, b):
            wa, wb = width(a), width(b)
            return None if wa is None or wa != wb else wa + 1
        case TProd(a, b):
            wa, wb = width(a), width(b)
            return None if wa is None or wb is None else wa + wb
        case TMu(v, body):
            return None if v in free_vars(body) else width(body)
    return None


def qubits(n: int) -> Type:
    """The type of `n` qubits, nested to the right as `Ctrl` expects."""
    if n < 1:
        raise Q42Error("a register needs at least one qubit")
    t = QUBIT
    for _ in range(n - 1):
        t = TProd(QUBIT, t)
    return t
