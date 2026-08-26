"""Concrete syntax for Q42.

The *term* grammar is 42's, parsed by `rel42.syntax` with Q42's primitive names
injected -- there is no second parser.  What is added here is notation for
states, because the shared value syntax is unusable for qubits: `|011>` beats
`(L (), (R (), R ()))`, and the nat sugar would print `Inl ()` as `0` when it
means the state |0>.

Registers nest to the right, matching `Ctrl` in gates.42 and the `CCX` signature
in the paper: `|abc>` is `(a, (b, c))`.
"""

from __future__ import annotations

import re
from typing import Dict, List

from rel42.core import Inl, Inr, Pair, Term, UNIT, Unit, Value
from rel42.syntax import ParseError, parse_program as _parse_program
from rel42.syntax import parse_term as _parse_term
from rel42.syntax import parse_value as _parse_value
from rel42.syntax import show as _show_raw
from rel42.syntax import show_term
from rel42.types import TMu, TOne, TProd, TSum, TVar, Type

from .core import ONE, ONE_AMP, PRIMS, Vec, ZERO, Q42Error, normalise

__all__ = [
    "ParseError",
    "bits_of",
    "ket",
    "parse_program",
    "parse_state",
    "parse_term",
    "show_amplitude",
    "show_ket",
    "show_term",
]

_KET = re.compile(r"^\|([01]+)>$")


def parse_term(src: str) -> Term:
    return _parse_term(src, PRIMS)


def parse_program(src: str) -> Dict[str, Term]:
    return _parse_program(src, PRIMS)


def ket(bits: str) -> Value:
    """`"011"` -> the basis value for that register, nested to the right."""
    if not bits or any(c not in "01" for c in bits):
        raise ParseError(f"a ket is one or more of 0 and 1, not {bits!r}")
    v: Value = ONE if bits[-1] == "1" else ZERO
    for c in reversed(bits[:-1]):
        v = Pair(ONE if c == "1" else ZERO, v)
    return v


def parse_state(src: str) -> Vec:
    """A basis state, written `|0110>`, or any 42 value.

    Only basis states can be written down: there is no syntax for a
    superposition, because there is no need for one -- you make superpositions by
    applying `h` or `v`, which is the whole point.
    """
    src = src.strip()
    m = _KET.match(src)
    if m:
        return {ket(m.group(1)): ONE_AMP}
    if re.fullmatch(r"[01]+", src):  # bare bits, for convenience
        return {ket(src): ONE_AMP}
    return {_parse_value(src, PRIMS): ONE_AMP}


def bits_of(v: Value) -> str | None:
    """The register notation for a basis value, or None if it is not one."""
    out: List[str] = []
    while True:
        if v == ZERO:
            return "".join(out) + "0"
        if v == ONE:
            return "".join(out) + "1"
        if not isinstance(v, Pair):
            return None
        head = v.a
        if head == ZERO:
            out.append("0")
        elif head == ONE:
            out.append("1")
        else:
            return None
        v = v.b


def show_amplitude(z: complex) -> str:
    """An amplitude, kept short enough that a superposition stays readable."""
    re_, im = round(z.real, 6) + 0.0, round(z.imag, 6) + 0.0
    if im == 0:
        return f"{re_:g}"
    if re_ == 0:
        return f"{im:g}i"
    return f"({re_:g}{im:+g}i)"


def show_ket(psi: Vec, ty: Type | None = None) -> str:
    """Render a state.

    Basis values print as `|011>` when they are registers of qubits.  Anything
    else falls back to 42's value printer, which is right for the plumbing types
    -- a term of type `1 x (1+1) <-> ...` has states that are not registers, and
    pretending otherwise would be worse than verbose.
    """
    psi = normalise(psi)
    if not psi:
        return "0   (the zero vector)"

    def one(v: Value) -> str:
        bits = bits_of(v)
        return f"|{bits}>" if bits is not None else _show_raw(v, raw=True)

    terms = sorted(((one(v), z) for v, z in psi.items()), key=lambda kv: kv[0])
    parts = []
    for label, z in terms:
        a = show_amplitude(z)
        parts.append(label if a == "1" else f"{a}{label}")
    return "  +  ".join(parts)
