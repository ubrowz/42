"""The encoding `meta.42` reads: 42 programs and values, as 42 values.

`meta.42` is an interpreter for 42 written in 42 (THEOREM.md section 7,
MANUAL.md section 14; `42 quote` is the command).  It takes a *state* -- an environment, a term and a
value, all encoded as ordinary 42 values -- and relates it to the states the
term reaches.  This module is the bridge: it turns a `Term` and a `Value` from
`rel42.core` into that encoding, and turns the answer back.

Nothing here is part of the language.  It exists so that `42 quote` can hand a
recursive program to the interpreter, which the quoting combinators in
`meta.42` itself cannot do: they build a quotation against the *empty*
environment, so they reach only programs that mention no definitions.

The tests in `tests/test_rel42.py` deliberately do **not** import this module.
They write the encoding out a second time, so that the interpreter is checked
against an independently written encoder rather than against the one it ships
with; `TestQuoteAgreesWithTheTestEncoding` is what keeps the two honest.
"""

from __future__ import annotations

import os
from typing import Dict, List

from .core import (
    Env,
    Inl,
    Inr,
    Pair,
    Prim,
    PRIMS,
    Prod,
    Ref,
    Rel42Error,
    Seq,
    Star,
    Sum,
    Term,
    UNIT,
    Union,
    Unit,
    Value,
    expand_env,
    is_combinator,
)
from .syntax import parse_program

#: The order of `meta.42`'s `n1 ... n13`, which is the order `PRIMS` is
#: registered in.  Written out rather than derived so that reordering the
#: primitive table cannot silently change what an encoded program means; the
#: assertion below is what ties the two together.
PRIM_ORDER: List[str] = [
    "id", "zero", "swapsum", "assocsum", "unitsum", "swapprod", "assocprod",
    "unitprod", "dist", "inl", "inr", "copy", "join",
]

assert PRIM_ORDER == list(PRIMS), (
    "meta.42's primitive tags follow the registration order in core.py; "
    "PRIMS has changed and rel42/meta.py has not"
)

#: The seven constructors of `tm`, in the order `meta.42` tags them.
_SEQ, _UNION, _SUM, _PROD = 3, 4, 5, 6


def _case(k: int, n: int, x: Value) -> Value:
    """The k-th of n right-nested summands, 1-indexed: `inl ; inr^(k-1)`."""
    v = x if k == n else Inl(x)
    for _ in range(k - 1):
        v = Inr(v)
    return v


def _flag(inv: bool) -> Value:
    return Inr(UNIT) if inv else Inl(UNIT)


def _nat(i: int) -> Value:
    v: Value = Inl(UNIT)
    for _ in range(i):
        v = Inr(v)
    return v


def encode_value(v: Value) -> Value:
    """`𝕍 -> V(val)`, the four constructors of section 14.1."""
    if isinstance(v, Pair):
        return Inr(Inr(Inr(Pair(encode_value(v.a), encode_value(v.b)))))
    if isinstance(v, Inl):
        return Inr(Inl(encode_value(v.v)))
    if isinstance(v, Inr):
        return Inr(Inr(Inl(encode_value(v.v))))
    if isinstance(v, Unit):
        return Inl(UNIT)
    raise Rel42Error(f"not a value: {v!r}")


def decode_value(v: Value) -> Value:
    """The converse of `encode_value`, partial on values outside the encoding."""
    if isinstance(v, Inl):
        return UNIT
    if not isinstance(v, Inr):
        raise Rel42Error("not an encoded value")
    w = v.v
    if isinstance(w, Inl):
        return Inl(decode_value(w.v))
    if not isinstance(w, Inr):
        raise Rel42Error("not an encoded value")
    w = w.v
    if isinstance(w, Inl):
        return Inr(decode_value(w.v))
    if not isinstance(w, Inr) or not isinstance(w.v, Pair):
        raise Rel42Error("not an encoded value")
    return Pair(decode_value(w.v.a), decode_value(w.v.b))


def encode_term(t: Term, names: List[str]) -> Value:
    """`Term -> V(tm)`.  `names` fixes which slot each definition occupies."""
    both = lambda k, s, u: _case(
        k, 7, Pair(encode_term(s, names), encode_term(u, names))
    )
    if isinstance(t, Prim):
        if t.name not in PRIM_ORDER:
            raise Rel42Error(f"unknown primitive: {t.name}")
        tag = _case(PRIM_ORDER.index(t.name) + 1, 13, UNIT)
        return _case(1, 7, Pair(tag, _flag(t.inv)))
    if isinstance(t, Ref):
        if t.name not in names:
            raise Rel42Error(f"undefined: {t.name}")
        return _case(2, 7, Pair(_nat(names.index(t.name)), _flag(t.inv)))
    if isinstance(t, Seq):
        return both(_SEQ, t.s, t.t)
    if isinstance(t, Union):
        return both(_UNION, t.s, t.t)
    if isinstance(t, Sum):
        return both(_SUM, t.s, t.t)
    if isinstance(t, Prod):
        return both(_PROD, t.s, t.t)
    if isinstance(t, Star):
        return _case(7, 7, encode_term(t.s, names))
    raise Rel42Error(
        f"{type(t).__name__} has no encoding: `meta.42` interprets the core, "
        f"and combinators are substituted away before it is reached"
    )


def relation_names(env: Env) -> List[str]:
    """The definitions that take a slot in the encoded environment.

    A file may define combinators as well (`def ctrl m = ...`).  Those are not
    relations: they are second-order, they are substituted away before the
    evaluator is reached (THEOREM.md 2.4), and `meta.42` has no constructor for
    one.  So they are not merely skipped for convenience -- there is nothing
    they could be encoded *as*, and giving them a slot would shift the indices
    of everything after them.
    """
    return [n for n in sorted(env) if not is_combinator(env[n])]


def encode_env(env: Env, names: List[str]) -> Value:
    """The definitions as a list of terms, in `names` order."""
    v: Value = Inl(UNIT)
    for n in reversed(names):
        v = Inr(Pair(encode_term(env[n], names), v))
    return v


def encode_state(env: Env, t: Term, v: Value, names: List[str] | None = None) -> Value:
    """`env × (tm × val)`, the state `meta.42`'s `eval` relates."""
    names = relation_names(env) if names is None else names
    return Pair(encode_env(env, names), Pair(encode_term(t, names), encode_value(v)))


def decode_state(s: Value) -> Value:
    """The value component of a state `eval` produced."""
    return decode_value(s.b.b)


def size(v: Value) -> int:
    """Nodes in an encoded value -- how big a program is, once written down."""
    if isinstance(v, Pair):
        return 1 + size(v.a) + size(v.b)
    if isinstance(v, (Inl, Inr)):
        return 1 + size(v.v)
    return 1


def meta_path() -> str:
    """`meta.42`, which sits beside the package rather than inside it."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "meta.42"
    )


def load_meta(path: str | None = None) -> Dict[str, Term]:
    """Parse `meta.42` and reduce its combinators away, ready to run."""
    with open(path or meta_path(), "r", encoding="utf-8") as fh:
        return expand_env(parse_program(fh.read()))
