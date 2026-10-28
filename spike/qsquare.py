#!/usr/bin/env python3
"""The commuting square of QSUGAR.md section 1, checked on real definitions.

For each clause definition in spike/qsugar.42 that has a point-free Q42
counterpart, compile the clauses with today's 42 compiler and compare, on every
basis state and in both directions, the relation 42 gives with the support (the
nonzero entries) of the matrix Q42 gives.  Then report which compiled terms stay
inside the shared core C, the part both interpreters have.

    python3 spike/qsquare.py
"""

from __future__ import annotations

import itertools
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from q42.core import column  # noqa: E402
from q42.exact import is_zero  # noqa: E402
from q42.syntax import parse_program as qparse  # noqa: E402
from rel42 import Ref, parse_program, run  # noqa: E402
from rel42.core import (  # noqa: E402
    UNIT, App, Fun, Inl, Inr, Pair, Prim, Prod, Seq, Star, Sum, Union, expand_env,
)

CORE = {"id", "swapprod", "assocprod", "unitprod", "swapsum", "assocsum", "unitsum", "dist"}

SQUARE = [  # (clause definition, Q42 file, Q42 definition, qubits)
    ("cx", "q42/gates.42", "cx", 2),
    ("ccx", "q42/gates.42", "ccx", 3),
    ("orcnot", "q42/deutsch.42", "orcnot", 2),
    ("add4", "q42/fib.42", "add4", 4),
]


def register(bits):
    def bit(b):
        return Inr(UNIT) if b else Inl(UNIT)
    v = bit(bits[-1])
    for b in reversed(bits[:-1]):
        v = Pair(bit(b), v)
    return v


def outside_core(t) -> set:
    match t:
        case Prim(n, _):
            return set() if n in CORE else {n}
        case Seq(a, b) | Prod(a, b) | Sum(a, b):
            return outside_core(a) | outside_core(b)
        case Union(a, b):
            return {"|"} | outside_core(a) | outside_core(b)
        case Star(a):
            return {"^"} | outside_core(a)
        case Fun(_, b):
            return outside_core(b)
        case App(f, a):
            return outside_core(f) | outside_core(a)
    return set()


def main() -> int:
    src = (ROOT / "spike" / "qsugar.42").read_text(encoding="utf-8")
    clauses = parse_program(src)
    runnable = expand_env(clauses)
    for mine, path, theirs, n in SQUARE:
        q = expand_env(qparse((ROOT / path).read_text(encoding="utf-8")))
        for bits in itertools.product([0, 1], repeat=n):
            v = register(bits)
            for back in (False, True):
                rel = run(Ref(mine, back), v, runnable)
                amp = column(Ref(theirs, back), v, q)
                support = {w for w, a in amp.items() if not is_zero(a)}
                assert rel == support, (mine, bits, back, rel, support)
        print(f"square holds  {mine:7} = support of {path}:{theirs}, all {2 ** n} basis states, both ways")
    for name, term in clauses.items():
        extra = sorted(outside_core(term))
        print(f"core only     {name:7} {'yes' if not extra else 'no: uses ' + ', '.join(extra)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
