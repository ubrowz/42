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
from rel42.core import App, Fun, Prim, Prod, Seq, Star, Sum, Term, Union, Unit

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


class Rules:
    """The hook `rel42.syntax.parse_program` calls for each clause definition."""

    def check(self, name: str, params: List[str], clauses: List[S.Clause]) -> None:
        renamed = [S.rebindings_apart(c) for c in clauses]
        for c in renamed:
            check_names(c)
        check_coverage(name, renamed)

    def accept(self, name: str, term: Term, clauses: List[S.Clause]) -> None:
        extra = _outside(term)
        if extra:
            raise ClauseError(
                f"`{name}` covers both sides exactly once, but its input and output "
                f"do not split the same way, so it needs the general construction "
                f"of QSUGAR.md section 4.2, which is not built yet (compiled with "
                f"42's compiler it uses {', '.join(sorted(extra))})."
            )
