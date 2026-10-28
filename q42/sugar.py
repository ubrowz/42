"""Clause definitions in Q42 (QSUGAR.md).

Q42 compiles clauses with 42's compiler, and adds the rules that make a
definition unitary rather than merely a relation:

* every name is used exactly once, on each side (section 3.1);
* the patterns cover the input type exactly once, and the terms, read as
  patterns, cover the output type exactly once (section 3.2);
* a `let` pattern cannot fail, and a pattern contains no call (section 3.3).

Coverage is decided without types, by splitting: where one clause has a
constructor and another a name, the name is split by the constructor's shape,
until every place has a constructor in every clause or a name in every clause.

What the 42 compiler produces is then accepted only if it stays inside the core
both languages share, plus calls (section 4.1).  The general construction of
section 4.2 is not built yet, and a definition that needs it is refused with
that reason.

This module is Q42's own: 42 never imports it.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from rel42 import sugar as S
from rel42.core import (
    App, Fun, Prim, Prod, Seq, Star, Sum, Term, UNIT, Union, Unit, dagger,
)

from .core import PRIMS, Q42Error


class ClauseError(Q42Error, S.SugarError):
    """A clause definition Q42 cannot accept, with the reason."""


# ---------------------------------------------------------------------------
# Section 3.1 and 3.3: names, lets and calls.
# ---------------------------------------------------------------------------


def _bindings(c: S.Clause):
    """Each binding site's variables: the pattern, then each `let` pattern."""
    sites = [S.variables(c.pattern)]
    body = c.body
    while isinstance(body, S.DLet):
        sites.append(S.variables(body.pat))
        body = body.body
    return sites


def _uses(c: S.Clause):
    out = []
    body = c.body
    while isinstance(body, S.DLet):
        out += S.variables(body.rhs)
        body = body.body
    return out + S.variables(body)


def _has_call(t: S.DTerm) -> bool:
    match t:
        case S.DApp():
            return True
        case S.DPair(a, b):
            return _has_call(a) or _has_call(b)
        case S.DInl(x) | S.DInr(x):
            return _has_call(x)
    return False


def _cannot_fail(t: S.DTerm) -> bool:
    match t:
        case S.DVar():
            return True
        case S.DConst(v):
            return isinstance(v, Unit)
        case S.DPair(a, b):
            return _cannot_fail(a) and _cannot_fail(b)
    return False


def check_names(c: S.Clause) -> None:
    """Exact linearity, no calls in patterns, `let` patterns that cannot fail."""
    if _has_call(c.pattern):
        raise ClauseError(
            f"line {c.line}: in `{c.text}`, the pattern calls a program.  Calls in "
            f"patterns are 42-only for now; match first, then call the program "
            f"backwards in a `let`."
        )
    body = c.body
    while isinstance(body, S.DLet):
        if _has_call(body.pat) or not _cannot_fail(body.pat):
            raise ClauseError(
                f"line {body.line}: in `{c.text}`, a `let` pattern can fail.  A "
                f"call's result may be a superposition, so a pattern after a call "
                f"may contain only names, pairs and ()."
            )
        body = body.body

    for site in _bindings(c):
        seen = set()
        for v in site:
            if v.name in seen:
                raise ClauseError(
                    f"line {v.line}: in `{c.text}`, `{S._shown(v.name)}` is matched "
                    f"twice.  An equality test discards the pairs that differ, "
                    f"which is not unitary in Q42."
                )
            seen.add(v.name)

    counts = {}
    for v in _uses(c):
        counts[v.name] = counts.get(v.name, 0) + 1
        if counts[v.name] == 2:
            raise ClauseError(
                f"line {v.line}: in `{c.text}`, `{S._shown(v.name)}` is used twice.  "
                f"Q42 cannot copy a value: copying maps a space into a bigger one, "
                f"so it is not unitary (QMANUAL section 5.2)."
            )


# ---------------------------------------------------------------------------
# Section 3.2: covering exactly once, by splitting.
#
# A row is one clause's pattern as a list of columns, each a tree in the form
# `sugar._tree` gives: ("L", t), ("R", t), ("P", a, b), () or WILD.  The answer
# is None when every value is matched by exactly one row, or else what went
# wrong and a value it went wrong at.
# ---------------------------------------------------------------------------

WILD = S.WILD


def _exactly_once(rows: List[Tuple[int, list]]):
    if not rows or not rows[0][1]:
        if len(rows) == 1:
            return None
        return ("gap" if not rows else "overlap", [], [i for i, _ in rows])

    heads = [cols[0] for _, cols in rows]
    shaped = [h for h in heads if h != WILD]
    if not shaped:
        found = _exactly_once([(i, cols[1:]) for i, cols in rows])
        return found and (found[0], [WILD] + found[1], found[2])

    kind = shaped[0] if shaped[0] == () else shaped[0][0]
    if kind == ():
        found = _exactly_once([(i, cols[1:]) for i, cols in rows])
        return found and (found[0], [()] + found[1], found[2])
    if kind == "P":
        split = []
        for i, cols in rows:
            h = cols[0]
            a, b = (WILD, WILD) if h == WILD else (h[1], h[2])
            split.append((i, [a, b] + cols[1:]))
        found = _exactly_once(split)
        if found:
            w = found[1]
            return (found[0], [("P", w[0], w[1])] + w[2:], found[2])
        return None
    for label in ("L", "R"):
        sub = []
        for i, cols in rows:
            h = cols[0]
            if h == WILD:
                sub.append((i, [WILD] + cols[1:]))
            elif h[0] == label:
                sub.append((i, [h[1]] + cols[1:]))
        if not sub:
            return ("gap", [(label, WILD)] + [WILD] * (len(rows[0][1]) - 1), [])
        found = _exactly_once(sub)
        if found:
            w = found[1]
            return (found[0], [(label, w[0])] + w[1:], found[2])
    return None


def show_witness(tree) -> str:
    """A value, in L/R form: in Q42 `L ()` is a qubit, not the number 0."""
    def go(t) -> str:
        if t == WILD:
            return "_"
        if t == ():
            return "()"
        if t[0] == "P":
            return f"({go(t[1])}, {go(t[2])})"
        inner = go(t[1])
        return f"{t[0]} {inner}" if " " not in inner or inner.startswith("(") else f"{t[0]} ({inner})"
    return f"`{go(tree)}`"


def _outputs_tree(c: S.Clause):
    # In a term, a call is like a name: a unitary call can produce any value
    # of its type.  `_tree` already reads a call as a wildcard.
    return S._tree(S._final(c.body))


def check_coverage(name: str, clauses: List[S.Clause]) -> None:
    for side, trees in (
        ("input", [S._tree(c.pattern) for c in clauses]),
        ("output", [_outputs_tree(c) for c in clauses]),
    ):
        found = _exactly_once([(i, [t]) for i, t in enumerate(trees)])
        if found is None:
            continue
        what, witness, which = found
        value = show_witness(witness[0]) if witness else "anything"
        where = "patterns" if side == "input" else "terms"
        if what == "gap":
            raise ClauseError(
                f"no clause of `{name}` {'matches' if side == 'input' else 'produces'} "
                f"{value}.  In Q42 every {side} needs exactly one clause, or the "
                f"definition is not unitary."
            )
        i, j = which[0], which[1]
        raise ClauseError(
            f"line {clauses[j].line}: the {where} of clauses {i + 1} and {j + 1} of "
            f"`{name}` both {'match' if side == 'input' else 'produce'} {value}.  "
            f"In Q42 a definition is the sum of its clauses, so they must not "
            f"overlap."
        )


# ---------------------------------------------------------------------------
# Section 4.1: accept what stays inside the shared core, plus calls.
# ---------------------------------------------------------------------------


def _outside(t: Term) -> set:
    match t:
        case Prim(n, _):
            return set() if n in PRIMS else {n}
        case Seq(a, b) | Prod(a, b) | Sum(a, b):
            return _outside(a) | _outside(b)
        case Union(a, b):
            return {"|"} | _outside(a) | _outside(b)
        case Star(a):
            return {"^"} | _outside(a)
        case Fun(_, b):
            return _outside(b)
        case App(f, a):
            return _outside(f) | _outside(a)
    return set()


def not_emittable(name: str, env, general: set) -> Optional[str]:
    """Section 5's reason, if `name` is or calls a general-construction term."""
    from rel42.types import references

    seen, todo = set(), [name]
    while todo:
        n = todo.pop()
        if n in seen or n not in env:
            continue
        seen.add(n)
        if n in general:
            via = "" if n == name else f", because it calls `{n}`"
            return (
                f"`{name}` runs in the evaluator but cannot be emitted yet{via}: "
                f"`{n}` is a clause definition whose input and output do not split "
                f"alike, so it is compiled by the general construction of "
                f"QSUGAR.md section 4.2, and that reorders sums of different widths, "
                f"which are not registers (QMANUAL section 9.4)."
            )
        todo.extend(references(env[n]) & set(env))
    return None


# ---------------------------------------------------------------------------
# Section 4.2: the general construction.
#
#     f  =  M_in ; (+_j  mid_j ; N_j ; reshape) ; sigma ; M_out!
#
# M_in splits the input into one summand per *input leaf*: a clause after the
# splitting of section 3.2, holding that leaf's names.  mid_j runs the leaf's
# clause body -- its lets, and its calls, lifted into lets so that what is
# left is names and constructors -- and ends with the tuple of the names the
# final term uses.  M_out splits the output the same way, into *output
# leaves*; where it split a name of input leaf j's final term, N_j makes that
# split on j's tuple, so leaf j arrives as the sum of its output leaves.
# reshape puts each output leaf's names in M_out's order, and sigma reorders
# the summands from M_in's tree to M_out's.  Every piece is pair and sum
# rearrangement, `dist`, a unit check, or the clause's own calls.
# ---------------------------------------------------------------------------

_fresh_count = [0]


def _fresh(base: str) -> str:
    _fresh_count[0] += 1
    return f"{base}~{_fresh_count[0]}"     # `~` cannot occur in a written name


def _tup(items):
    if not items:
        return None
    s = items[-1]
    for i in reversed(items[:-1]):
        s = (i, s)
    return s


def _tup_term(names: List[str]) -> S.DTerm:
    if not names:
        return S.DConst(UNIT, "()")
    t: S.DTerm = S.DVar(names[-1])
    for n in reversed(names[:-1]):
        t = S.DPair(S.DVar(n), t)
    return t


def _replace(shape, old, new):
    if shape == old:
        return new
    if isinstance(shape, tuple):
        return (_replace(shape[0], old, new), _replace(shape[1], old, new))
    return shape


def _subst(t: S.DTerm, sub) -> S.DTerm:
    match t:
        case S.DVar(n):
            return _subst(sub[n], sub) if n in sub else t
        case S.DPair(a, b):
            return S.DPair(_subst(a, sub), _subst(b, sub))
        case S.DInl(x):
            return S.DInl(_subst(x, sub))
        case S.DInr(x):
            return S.DInr(_subst(x, sub), t.form)
        case S.DApp(h, x):
            return S.DApp(h, _subst(x, sub))
        case S.DLet(q, r, e):
            return S.DLet(q, _subst(r, sub), _subst(e, sub), t.line)
    return t


class _Row:
    def __init__(self, ident, cols, names=None, sub=None):
        self.ident = ident      # what this row stands for
        self.cols = cols        # one DTerm per remaining column
        self.names = dict(names or {})   # position -> the name held there
        self.sub = dict(sub or {})       # name -> what splitting made it

    def but(self, cols, **extra):
        r = _Row(self.ident, cols, self.names, self.sub)
        r.sub.update(extra.get("sub", {}))
        return r


def _cover(rows: List[_Row], acc, cols, cur):
    """A term from a value of shape `cur` to a sum with one summand per leaf.

    `cols` are the positions still to match and `acc` those already matched
    against a name in every row; positions are opaque strings, and a shape is
    a nested tuple of them (None for a unit).  Returns the term and the tree
    of leaves: ("leaf", row, acc) or ("+", left, right).
    """
    if not cols:
        if len(rows) != 1:   # coverage (section 3.2) has already ruled this out
            raise ClauseError("internal: a leaf with %d clauses" % len(rows))
        return S.route(cur, _tup(acc)), ("leaf", rows[0], list(acc))

    c0, rest = cols[0], cols[1:]
    heads = [S._expose(r.cols[0]) for r in rows]
    shaped = [h for h in heads if not isinstance(h, S.DVar)]

    if not shaped:                      # a name in every row: keep it
        out = []
        for r, h in zip(rows, heads):
            nr = r.but(r.cols[1:])
            nr.names[c0] = h.name
            out.append(nr)
        return _cover(out, acc + [c0], rest, cur)

    first = shaped[0]
    if isinstance(first, S.DConst):     # (): one value, nothing to keep
        out = []
        for r, h in zip(rows, heads):
            extra = {h.name: S.DConst(UNIT, "()")} if isinstance(h, S.DVar) else {}
            out.append(r.but(r.cols[1:], sub=extra))
        return _cover(out, acc, rest, _replace(cur, c0, None))

    if isinstance(first, S.DPair):      # a pair: two positions
        a, b = _fresh("p"), _fresh("p")
        out = []
        for r, h in zip(rows, heads):
            if isinstance(h, S.DVar):
                x1, x2 = _fresh(h.name), _fresh(h.name)
                out.append(r.but([S.DVar(x1), S.DVar(x2)] + r.cols[1:],
                                 sub={h.name: S.DPair(S.DVar(x1), S.DVar(x2))}))
            else:
                out.append(r.but([h.a, h.b] + r.cols[1:]))
        return _cover(out, acc, [a, b] + rest, _replace(cur, c0, (a, b)))

    # A label: bring it to the front and split with `dist`.
    others = acc + rest
    front = (c0, _tup(others)) if others else c0
    term: Term = S.route(cur, front)
    branches = []
    for label, make in (("L", S.DInl), ("R", S.DInr)):
        inner = _fresh("p")
        out = []
        for r, h in zip(rows, heads):
            if isinstance(h, S.DVar):
                x = _fresh(h.name)
                out.append(r.but([S.DVar(x)] + r.cols[1:], sub={h.name: make(S.DVar(x))}))
            elif (label == "L") == isinstance(h, S.DInl):
                out.append(r.but([h.t] + r.cols[1:]))
        if not out:
            raise ClauseError("internal: an empty branch after the coverage check")
        cur_b = (inner, _tup(others)) if others else inner
        branches.append(_cover(out, acc, [inner] + rest, cur_b))
    if others:
        term = Seq(term, S._p("dist"))
    else:
        # A bare label: no pair to distribute over.
        pass
    return Seq(term, Sum(branches[0][0], branches[1][0])), ("+", branches[0][1], branches[1][1])


def _leaves(tree):
    if tree[0] == "leaf":
        return [tree]
    return _leaves(tree[1]) + _leaves(tree[2])


def _map_tree(tree, f):
    """Replace each leaf by f(leaf) = (term, subtree); combine with `+`."""
    if tree[0] == "leaf":
        return f(tree)
    lt, ls = _map_tree(tree[1], f)
    rt, rs = _map_tree(tree[2], f)
    return Sum(lt, rt), ("+", ls, rs)


def _sum_leaves(tree):
    if tree[0] == "leaf":
        return [tree[1]]
    return _sum_leaves(tree[1]) + _sum_leaves(tree[2])


def _sum_concat(ll, lr) -> Term:
    """(sum of ll) + (sum of lr)  ->  sum of ll + lr, right-nested."""
    if len(ll) == 1:
        return S.ID
    return Seq(S._p("assocsum", True), Sum(S.ID, _sum_concat(ll[1:], lr)))


def _sum_flatten(tree) -> Term:
    if tree[0] == "leaf":
        return S.ID
    return Seq(Sum(_sum_flatten(tree[1]), _sum_flatten(tree[2])),
               _sum_concat(_sum_leaves(tree[1]), _sum_leaves(tree[2])))


def _sum_at(i: int, op: Term) -> Term:
    for _ in range(i):
        op = Sum(S.ID, op)
    return op


def _sum_swap(n: int) -> Term:
    if n == 2:
        return S._p("swapsum")
    return Seq(Seq(S._p("assocsum"), Sum(S._p("swapsum"), S.ID)), S._p("assocsum", True))


def _sum_route(src, dst) -> Term:
    """Reorder the summands of tree `src` into tree `dst` (same leaves)."""
    cur, want = _sum_leaves(src), _sum_leaves(dst)
    out: Term = _sum_flatten(src)
    for i in range(len(want)):
        k = cur.index(want[i], i)
        while k > i:
            out = Seq(out, _sum_at(k - 1, _sum_swap(len(cur) - k + 1)))
            cur[k - 1], cur[k] = cur[k], cur[k - 1]
            k -= 1
    return Seq(out, dagger(_sum_flatten(dst)))


def _lift_calls(t: S.DTerm, lets):
    """`t` with every call replaced by a fresh name, the calls collected."""
    match t:
        case S.DApp():
            z = _fresh("z")
            lets.append((S.DVar(z), t))
            return S.DVar(z)
        case S.DPair(a, b):
            return S.DPair(_lift_calls(a, lets), _lift_calls(b, lets))
        case S.DInl(x):
            return S.DInl(_lift_calls(x, lets))
        case S.DInr(x):
            return S.DInr(_lift_calls(x, lets), t.form)
    return t


def _with_lets(body: S.DTerm, extra, final: S.DTerm) -> S.DTerm:
    if isinstance(body, S.DLet):
        return S.DLet(body.pat, body.rhs, _with_lets(body.body, extra, final), body.line)
    out = final
    for pat, rhs in reversed(extra):
        out = S.DLet(pat, rhs, out, 0)
    return out


def general(clauses: List[S.Clause]) -> Term:
    """Section 4.2's construction, for clauses that passed the checks."""
    # M_in: the input, split into input leaves.
    rows = [_Row(i, [c.pattern]) for i, c in enumerate(clauses)]
    m_in, in_tree = _cover(rows, [], ["in"], "in")

    # Each input leaf's body, its calls lifted into lets.
    prepared = {}
    for leaf in _leaves(in_tree):
        _, row, acc = leaf
        c = clauses[row.ident]
        body = _subst(c.body, row.sub)
        lets = []
        final = _lift_calls(S._final(body), lets)
        uses = list(dict.fromkeys(v.name for v in S.variables(final)))
        env = [row.names[a] for a in acc]
        prepared[id(leaf)] = (leaf, env, body, lets, final, uses)

    # M_out: the output, split into output leaves, one row per input leaf.
    out_rows = [_Row(key, [p[4]]) for key, p in prepared.items()]
    m_out, out_tree = _cover(out_rows, [], ["out"], "out")
    out_leaves = {}
    for leaf in _leaves(out_tree):
        _, row, acc = leaf
        out_leaves.setdefault(row.ident, []).append(leaf)

    def per_input_leaf(leaf):
        _, row, acc = leaf
        _, env, body, lets, final, uses = prepared[id(leaf)]
        mid_clause = S.Clause(_tup_term(env), _with_lets(body, lets, _tup_term(uses)),
                              0, "the general construction")
        mid = S.compile_clause(mid_clause)
        # N_j: make on this leaf's tuple the splits M_out made on its names.
        mine = out_leaves[id(leaf)]
        ids = [_fresh("g") for _ in uses]
        n_rows = [_Row(id(ol), [_subst(S.DVar(u), ol[1].sub) for u in uses])
                  for ol in mine]
        n_term, n_tree = _cover(n_rows, [], ids, _tup(ids))
        by_key = {id(ol): ol for ol in mine}

        def reshape(nleaf):
            _, nrow, nacc = nleaf
            target = by_key[nrow.ident]
            have = _tup([nrow.names[a] for a in nacc])
            want = _tup([target[1].names[a] for a in target[2]])
            return S.route(have, want), ("leaf", nrow.ident)

        r_term, r_tree = _map_tree(n_tree, reshape)
        return Seq(Seq(mid, n_term), r_term), r_tree

    middle, src_tree = _map_tree(in_tree, per_input_leaf)
    dst_tree = _map_tree(out_tree, lambda l: (S.ID, ("leaf", id(l))))[1]
    sigma = _sum_route(src_tree, dst_tree)
    return S.simplify(Seq(Seq(Seq(m_in, middle), sigma), dagger(m_out)))


class Rules:
    """The hook `rel42.syntax.parse_program` calls for each clause definition.

    `general` collects the names compiled by section 4.2's construction, so that
    the emitter can say why it cannot emit them (section 5).
    """

    def __init__(self):
        self.general: set = set()

    def check(self, name: str, params: List[str], clauses: List[S.Clause]) -> None:
        renamed = [S.rebindings_apart(c) for c in clauses]
        for c in renamed:
            check_names(c)
        check_coverage(name, renamed)

    def compile(self, name: str, params: List[str], clauses: List[S.Clause],
                term: Term) -> Term:
        """42's compilation if it stays in the shared core; else section 4.2's."""
        if not _outside(term):
            return term
        self.general.add(name)
        out = general([S.rebindings_apart(c) for c in clauses])
        for p in reversed(params):
            out = Fun(p, out)
        return out
