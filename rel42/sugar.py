"""Clause definitions: 42 with names, compiled to ordinary 42.

    def append ([], ys)    <->  ys
    def append (x:xs, ys)  <->  x : append (xs, ys)

SUGAR.md is the design; this module is section 3 of it made concrete.  A clause
`p <-> e` compiles to

    dagger(build p) ; route(shape p -> shape e) ; build e

-- match the pattern by building it backwards, rearrange, build the result --
and a definition is the `Union` of its clauses.  The output is an ordinary core
term, so nothing downstream (`run`, `dagger`, inference, meta.42) knows that
clauses exist.

Nothing here parses.  `syntax` builds the data terms below and hands each
clause group to `compile_clauses`; this module depends on `core` alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union as U

from .core import (
    App,
    Fun,
    Inl,
    Inr,
    Pair,
    Prim,
    Prod,
    Rel42Error,
    Seq,
    Sum,
    Term,
    Union,
    Unit,
    Value,
    dagger,
)


class SugarError(Rel42Error):
    """A clause definition that cannot be compiled, with the reason in 42's terms."""


# ---------------------------------------------------------------------------
# Data terms.  Patterns and terms are one language (SUGAR.md section 2).
# ---------------------------------------------------------------------------


class DTerm:
    __slots__ = ()


@dataclass(frozen=True)
class DVar(DTerm):
    name: str
    line: int = field(default=0, compare=False)


@dataclass(frozen=True)
class DConst(DTerm):
    """A literal: `()`, `3`, `[]`, `'a'`, `"hi"` -- already a value.

    `text` is how it was written, so `[]` is not printed back as `0`; it takes
    no part in equality, since the two are the same value.
    """

    value: Value
    text: str = field(default="", compare=False)


@dataclass(frozen=True)
class DPair(DTerm):
    a: DTerm
    b: DTerm


@dataclass(frozen=True)
class DInl(DTerm):
    t: DTerm


@dataclass(frozen=True)
class DInr(DTerm):
    """`R t`, also written `t + 1`, `h : t` or inside `[...]`.

    `form` records which of "R", "+", ":" or "[" was written, for printing only.
    """

    t: DTerm
    form: str = field(default="R", compare=False)


@dataclass(frozen=True)
class DApp(DTerm):
    """`P t`: run the program `P` on `t`.  In a pattern, that means backwards."""

    head: Term
    arg: DTerm


@dataclass(frozen=True)
class DLet(DTerm):
    """`let q = t in e`.  Only ever the body of a clause, or of another `let`."""

    pat: DTerm
    rhs: DTerm
    body: DTerm
    line: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Clause:
    pattern: DTerm
    body: DTerm
    line: int
    text: str  # the clause as written, for messages


# ---------------------------------------------------------------------------
# Shapes.  A term with its constructors and calls erased: variables at the
# leaves, `None` for a unit hole where a closed subterm stood, pairs kept.
# ---------------------------------------------------------------------------

Shape = U[str, None, Tuple["Shape", "Shape"]]

ID = Prim("id")


def _p(name: str, inv: bool = False) -> Term:
    return Prim(name, inv)


def variables(t: DTerm) -> List[DVar]:
    """Every variable occurrence, left to right, with repetitions."""
    match t:
        case DVar():
            return [t]
        case DConst():
            return []
        case DPair(a, b):
            return variables(a) + variables(b)
        case DInl(x) | DInr(x):
            return variables(x)
        case DApp(_, x):
            return variables(x)
        case DLet(q, r, e):
            return variables(q) + variables(r) + variables(e)
    raise TypeError(f"not a data term: {t!r}")


def _has_call(t: DTerm) -> bool:
    match t:
        case DApp():
            return True
        case DPair(a, b):
            return _has_call(a) or _has_call(b)
        case DInl(x) | DInr(x):
            return _has_call(x)
    return False


def _const(v: Value) -> Term:
    """A program from `()` to the value `v`."""
    match v:
        case Unit():
            return ID
        case Inl(x):
            return Seq(_const(x), _p("inl"))
        case Inr(x):
            return Seq(_const(x), _p("inr"))
        case Pair(a, b):
            return Seq(_p("unitprod", True), Prod(_const(a), _const(b)))
    raise TypeError(f"not a value: {v!r}")


def build(t: DTerm) -> Tuple[Shape, Term]:
    """The term's shape, and the program from that shape to the term.

    A closed subterm becomes a unit hole, built from `()`.  For a pair, a side
    that calls a program is built *before* a side made only of constructors,
    so that run backwards the constructor test comes first (SUGAR.md section 8:
    without this, `rev!` exhausts the call depth).
    """
    if not variables(t):
        return None, _closed(t)
    match t:
        case DVar(name):
            return name, ID
        case DInl(x):
            s, b = build(x)
            return s, Seq(b, _p("inl"))
        case DInr(x):
            s, b = build(x)
            return s, Seq(b, _p("inr"))
        case DApp(head, x):
            s, b = build(x)
            return s, Seq(b, head)
        case DPair(a, c):
            sa, ba = build(a)
            sc, bc = build(c)
            if _has_call(a) and not _has_call(c):
                return (sa, sc), Seq(Prod(ba, ID), Prod(ID, bc))
            if _has_call(c) and not _has_call(a):
                return (sa, sc), Seq(Prod(ID, bc), Prod(ba, ID))
            return (sa, sc), Prod(ba, bc)
    raise SugarError("`let` may only stand as the whole body of a clause")


def _closed(t: DTerm) -> Term:
    """A program from `()` to a term with no variables in it."""
    match t:
        case DConst(v):
            return _const(v)
        case DInl(x):
            return Seq(_closed(x), _p("inl"))
        case DInr(x):
            return Seq(_closed(x), _p("inr"))
        case DApp(head, x):
            return Seq(_closed(x), head)
        case DPair(a, b):
            return Seq(_p("unitprod", True), Prod(_closed(a), _closed(b)))
    raise SugarError("`let` may only stand as the whole body of a clause")


# ---------------------------------------------------------------------------
# Routing.  route(s -> t) = flatten(s) ; permute ; dagger(flatten(t)), where a
# flat value is the right-nested tuple of the shape's variables, `()` when
# there are none.  Repeated variables are merged with `copy!` and duplicated
# with `copy` in the middle stage, so (x, x) <-> (x, x) is test-and-rebuild.
# Reversing a route gives the route of the reversed clause, which is what the
# inversion claim of SUGAR.md section 5 needs.
# ---------------------------------------------------------------------------


def _leaves(s: Shape) -> List[str]:
    if s is None:
        return []
    if isinstance(s, str):
        return [s]
    return _leaves(s[0]) + _leaves(s[1])


def _concat(la: List[str], lb: List[str]) -> Term:
    """(flat la, flat lb)  ->  flat (la + lb)."""
    if not la:
        return _p("unitprod")
    if not lb:
        return Seq(_p("swapprod"), _p("unitprod"))
    if len(la) == 1:
        return ID
    return Seq(_p("assocprod", True), Prod(ID, _concat(la[1:], lb)))


def flatten(s: Shape) -> Term:
    """A program from a value of shape `s` to its flat form."""
    if s is None or isinstance(s, str):
        return ID
    a, b = s
    return Seq(Prod(flatten(a), flatten(b)), _concat(_leaves(a), _leaves(b)))


def _at(i: int, op: Term) -> Term:
    """Apply `op` to the suffix of a flat tuple that starts at position `i`."""
    for _ in range(i):
        op = Prod(ID, op)
    return op


def _swap(n: int) -> Term:
    """Exchange the first two items of a flat tuple of length n."""
    if n == 2:
        return _p("swapprod")
    return Seq(Seq(_p("assocprod"), Prod(_p("swapprod"), ID)), _p("assocprod", True))


def _merge(n: int) -> Term:
    """Merge the first two items, which must be equal, of a flat tuple of length n."""
    if n == 2:
        return _p("copy", True)
    return Seq(_p("assocprod"), Prod(_p("copy", True), ID))


def _dup(n: int) -> Term:
    """Duplicate the first item of a flat tuple of length n."""
    if n == 1:
        return _p("copy")
    return Seq(Prod(_p("copy"), ID), _p("assocprod", True))


def permute(src: List[str], dst: List[str]) -> Term:
    """Flat `src` to flat `dst`.  Both must name the same set of variables."""
    steps: List[Term] = []
    cur = list(src)

    # Merge: bring each repeated variable next to its first occurrence.
    i = 0
    while i < len(cur):
        j = i + 1
        while j < len(cur):
            if cur[j] == cur[i]:
                for k in range(j - 1, i, -1):  # bubble it left to i + 1
                    steps.append(_at(k, _swap(len(cur) - k)))
                    cur[k], cur[k + 1] = cur[k + 1], cur[k]
                steps.append(_at(i, _merge(len(cur) - i)))
                del cur[i + 1]
                j = i + 1
            else:
                j += 1
        i += 1

    # Duplicate up to the counts the target wants.
    for name in dict.fromkeys(dst):
        for _ in range(dst.count(name) - 1):
            i = cur.index(name)
            steps.append(_at(i, _dup(len(cur) - i)))
            cur.insert(i, name)

    # Sort into the target's order by adjacent swaps.
    for want in range(len(dst)):
        k = cur.index(dst[want], want)
        while k > want:
            steps.append(_at(k - 1, _swap(len(cur) - k + 1)))
            cur[k - 1], cur[k] = cur[k], cur[k - 1]
            k -= 1
    assert cur == dst, (cur, dst)

    out: Term = ID
    for s in steps:
        out = Seq(out, s)
    return out


def route(s: Shape, t: Shape) -> Term:
    """From shape `s` to shape `t`.

    Only ever applied to what a match produced, which has shape `s`; so when the
    two shapes are the same and no variable repeats, nothing needs to move.
    """
    leaves = _leaves(s)
    if s == t and len(set(leaves)) == len(leaves):
        return ID
    return Seq(Seq(flatten(s), permute(_leaves(s), _leaves(t))), dagger(flatten(t)))


# ---------------------------------------------------------------------------
# Compiling a clause.
# ---------------------------------------------------------------------------


def _names(vs) -> List[str]:
    return [v.name for v in vs]


def _check(c: Clause, defined) -> None:
    """The use-count rule (SUGAR.md section 4), over the whole `let` chain."""
    bound: Dict[str, int] = {}  # name -> which binding site bound it
    used: set = set()
    site = 0

    def bind(vs):
        nonlocal site
        site += 1
        for v in vs:
            if v.name in defined:
                raise SugarError(
                    f"line {v.line}: in `{c.text}`, the pattern variable `{v.name}` "
                    f"has the name of a definition.  In a pattern, `{v.name} t` runs "
                    f"`{v.name}` backwards, so a variable may not reuse the name.  "
                    f"Rename the variable."
                )
            if v.name in bound:
                # A repeat inside one pattern is an equality test; a `let` may not
                # rebind a name that is already in hand.
                if bound[v.name] != site:
                    raise SugarError(
                        f"line {v.line}: in `{c.text}`, `{v.name}` is bound twice.  "
                        f"A `let` may not rebind a name that is already in hand; "
                        f"use a new one."
                    )
                continue
            bound[v.name] = site

    def use(vs):
        for v in vs:
            if v.name not in bound:
                raise SugarError(
                    f"line {v.line}: in `{c.text}`, `{v.name}` is used but never "
                    f"bound.  42 cannot invent a value: run backwards, it would "
                    f"have to be thrown away.  Bind it in the pattern."
                )
            used.add(v.name)

    bind(variables(c.pattern))
    body = c.body
    while isinstance(body, DLet):
        use(variables(body.rhs))
        bind(variables(body.pat))
        body = body.body
    use(variables(body))

    for name in bound:
        if name not in used:
            raise SugarError(
                f"line {c.line}: in `{c.text}`, the variable `{name}` is bound and "
                f"never used.  42 cannot forget a value: run backwards, nothing "
                f"would say what `{name}` was.  Return it, or consume it in a call."
            )


def _later(body: DTerm) -> List[str]:
    """Distinct variables a `let` chain still needs, in first-use order."""
    return list(dict.fromkeys(_names(variables(body))))


def _flat_shape(names: List[str]) -> Shape:
    if not names:
        return None
    s: Shape = names[-1]
    for n in reversed(names[:-1]):
        s = (n, s)
    return s


def compile_clause(c: Clause, defined=frozenset()) -> Term:
    _check(c, defined)
    sp, bp = build(c.pattern)
    out: Term = dagger(bp)
    env: Shape = sp
    body = c.body
    while isinstance(body, DLet):
        sr, br = build(body.rhs)
        sq, bq = build(body.pat)
        bound_here = set(_names(variables(body.pat)))
        keep = [n for n in _later(body.body) if n not in bound_here]
        step = Seq(br, dagger(bq))
        if keep:
            keep_shape = _flat_shape(keep)
            out = Seq(Seq(out, route(env, (sr, keep_shape))), Prod(step, ID))
            env = (sq, keep_shape)
        else:
            out = Seq(Seq(out, route(env, sr)), step)
            env = sq
        body = body.body
    se, be = build(body)
    out = Seq(Seq(out, route(env, se)), be)
    return simplify(out)


def compile_clauses(params: List[str], clauses: List[Clause], defined=frozenset()) -> Term:
    """A definition from its clauses: their union, under its parameters."""
    terms = [compile_clause(c, defined) for c in clauses]
    out = terms[0]
    for t in terms[1:]:
        out = Union(out, t)
    for p in reversed(params):
        out = Fun(p, out)
    return out


def turned_round(c: Clause) -> Clause:
    """`p <-> e` as `e <-> p`, with any `let` chain reversed (SUGAR.md section 5).

        p <-> let q1 = t1 in let q2 = t2 in e
    becomes
        e <-> let t2 = q2 in let t1 = q1 in p
    """
    steps = []
    body = c.body
    while isinstance(body, DLet):
        steps.append(body)
        body = body.body
    out: DTerm = c.pattern
    for s in steps:
        out = DLet(s.rhs, s.pat, out, s.line)
    return Clause(body, out, c.line, c.text)


# ---------------------------------------------------------------------------
# Overlap (SUGAR.md section 6).  Two input patterns overlap when some value
# matches both.  Decided by unifying their constructor trees: a variable or a
# call counts as matching anything, so the check can warn about an overlap
# that a call would in fact rule out, and never misses one that exists.
# ---------------------------------------------------------------------------

WILD = "_"


def _tree(t: DTerm):
    """A pattern as nested ("L", x) / ("R", x) / ("P", a, b) / () / WILD."""
    match t:
        case DVar() | DApp():
            return WILD
        case DConst(v):
            return _vtree(v)
        case DInl(x):
            return ("L", _tree(x))
        case DInr(x):
            return ("R", _tree(x))
        case DPair(a, b):
            return ("P", _tree(a), _tree(b))
    return WILD


def _vtree(v: Value):
    match v:
        case Unit():
            return ()
        case Inl(x):
            return ("L", _vtree(x))
        case Inr(x):
            return ("R", _vtree(x))
        case Pair(a, b):
            return ("P", _vtree(a), _vtree(b))
    raise TypeError(f"not a value: {v!r}")


def _unify(a, b):
    """The most general tree matching both, or None when nothing does."""
    if a == WILD:
        return b
    if b == WILD:
        return a
    if a == () or b == ():
        return () if a == b else None
    if a[0] != b[0]:
        return None
    if a[0] == "P":
        x = _unify(a[1], b[1])
        y = _unify(a[2], b[2]) if x is not None else None
        return None if y is None else ("P", x, y)
    x = _unify(a[1], b[1])
    return None if x is None else (a[0], x)


def tree_value(tree):
    """The tree as a value, or None if it still has a wildcard in it."""
    if tree == WILD:
        return None
    if tree == ():
        return Unit()
    if tree[0] == "P":
        a, b = tree_value(tree[1]), tree_value(tree[2])
        return None if a is None or b is None else Pair(a, b)
    x = tree_value(tree[1])
    if x is None:
        return None
    return Inl(x) if tree[0] == "L" else Inr(x)


def overlaps(clauses: List[Clause]):
    """(i, j, witness) for every pair of clauses whose patterns can both match."""
    trees = [_tree(c.pattern) for c in clauses]
    out = []
    for i in range(len(trees)):
        for j in range(i + 1, len(trees)):
            w = _unify(trees[i], trees[j])
            if w is not None:
                out.append((i, j, w))
    return out


# ---------------------------------------------------------------------------
# Simplification.  Only rewrites that are equalities of relations on every
# value, typed or not, so `show` reads well and nothing changes meaning.
# ---------------------------------------------------------------------------

# `f ; f!` is the identity on every value exactly when `f` is total and
# injective: these are the primitives (and directions) for which that holds.
_TOTAL_INJECTIVE = {("unitprod", True), ("copy", False), ("inl", False), ("inr", False)}


# Their own converses, so `f!` prints as `f`.
_SELF_INVERSE = {"id", "swapprod", "swapsum"}


def _is_id(t: Term) -> bool:
    return isinstance(t, Prim) and t.name == "id"


def _chain(t: Term) -> List[Term]:
    if isinstance(t, Seq):
        return _chain(t.s) + _chain(t.t)
    return [t]


def simplify(t: Term) -> Term:
    match t:
        case Prim(name, True) if name in _SELF_INVERSE:
            return Prim(name)
        case Prod(a, b):
            a, b = simplify(a), simplify(b)
            return ID if _is_id(a) and _is_id(b) else Prod(a, b)
        case Sum(a, b):
            a, b = simplify(a), simplify(b)
            return ID if _is_id(a) and _is_id(b) else Sum(a, b)
        case Union(a, b):
            return Union(simplify(a), simplify(b))
        case App(f, a):
            return App(simplify(f), simplify(a))
        case Fun(p, b):
            return Fun(p, simplify(b))
        case Seq():
            return _simplify_chain([simplify(x) for x in _chain(t)])
    return t


def _simplify_chain(items: List[Term]) -> Term:
    out: List[Term] = []
    for x in items:
        for y in _chain(x):
            if _is_id(y):
                continue
            if out:
                prev = out[-1]
                # f ; f!  with f total and injective
                if (isinstance(prev, Prim) and isinstance(y, Prim)
                        and prev.name == y.name and prev.inv != y.inv
                        and (prev.name, prev.inv) in _TOTAL_INJECTIVE):
                    out.pop()
                    continue
                # (a * id) ; (b * id)  =  (a ; b) * id, and the mirror.  Never
                # fuses across components, so the section 8 order survives.
                if isinstance(prev, Prod) and isinstance(y, Prod):
                    if _is_id(prev.t) and _is_id(y.t):
                        out[-1] = Prod(_simplify_chain([prev.s, y.s]), ID)
                        continue
                    if _is_id(prev.s) and _is_id(y.s):
                        out[-1] = Prod(ID, _simplify_chain([prev.t, y.t]))
                        continue
            out.append(y)
    if not out:
        return ID
    res = out[0]
    for y in out[1:]:
        res = Seq(res, y)
    return res
