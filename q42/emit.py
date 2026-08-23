"""Turning a Q42 term into a list of gates on numbered qubits.

WHAT THIS IS FOR.  A device, or any of the standard toolchains, wants gates
applied to indices: `cx q[0], q[2]`.  Q42 addresses qubits *structurally* -- a
term acts on a type, and which qubit it touches is a matter of where it sits in
the nesting.  This module converts the one into the other.

THE SURPRISE, and the reason the module is short: **seven of the ten primitives
emit nothing at all.**  `id`, `assocprod`, `unitprod` and `dist` re-bracket the
register without moving anything; `swapprod` exchanges two blocks, which a format
with no fixed topology can honour by relabelling rather than by emitting a SWAP;
and `assocsum` and `unitsum` can never appear at a register type at all (see
`_layout_of` below).  Only `swapsum`, `omega` and `v` produce output.

CONTROL NEEDS NO SPECIAL CASE, which matters because `ctrl` is a library
definition rather than a language feature, and an emitter that pattern-matched on
it would be lying about where control comes from.  The rule is structural:

    at a type `a + b`, the first qubit is the tag, and `f + g` means
    f under the tag being 0 and g under the tag being 1.

`dist` is what puts you at such a type, and `ctrl m = mat ; (id + m) ; mat!` then
emits exactly what it should with no rule of its own.  So does `t = id + omega`:
a controlled *global* phase is a relative one, which is the T gate, derived
rather than tabulated.

CONVENTIONS.  Qubit 0 is leftmost in a ket, matching `basis_of`.  A type of width
w occupies w wires in the order its structure lays them out, and for a sum the
tag comes first.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from rel42.core import (
    Prim,
    Prod,
    Ref,
    Seq,
    Star,
    Sum,
    Term,
    Union,
    dagger,
)
from rel42.types import TMu, TOne, TProd, TSum, Type

from .core import Q42Error
from .types import width

Gate = Tuple
Layout = Tuple[int, ...]
Ctrls = Tuple[Tuple[int, int], ...]

#: An eighth turn, which is the only angle `omega` knows.
EIGHTH = math.pi / 4


class NotEmittable(Q42Error):
    """The term cannot be written as gates on numbered qubits, and why."""


# ---------------------------------------------------------------------------
# Types, as they lay out over wires.
# ---------------------------------------------------------------------------


def _unfold(t: Type) -> Type:
    """Look through a `mu` that does not actually recurse."""
    while isinstance(t, TMu):
        t = t.body
    return t


def _split_prod(t: Type):
    t = _unfold(t)
    if not isinstance(t, TProd):
        raise NotEmittable(f"expected a pair type, got {t!r}")
    return t.a, t.b


def _split_sum(t: Type):
    t = _unfold(t)
    if not isinstance(t, TSum):
        raise NotEmittable(f"expected a choice type, got {t!r}")
    return t.a, t.b


def _w(t: Type) -> int:
    n = width(t)
    if n is None:
        raise NotEmittable(
            "that type is not a qubit register, so it has no wires to emit on"
        )
    return n


# ---------------------------------------------------------------------------
# Gates, with a control context.
# ---------------------------------------------------------------------------


def _flips(ctrls: Ctrls) -> List[Gate]:
    """`x` on every control that fires on 0, so the rest can assume 1."""
    return [("x", [w]) for w, bit in ctrls if bit == 0]


def _phase(wires: Sequence[int], angle: float) -> List[Gate]:
    """A phase on the all-ones state of `wires`, at any number of them.

    One gate for one wire, `cp` for two, and above that the halving recursion of
    Barenco et al.: a phase under k controls is three phases under k-1 controls,
    at half the angle, with two `cx` between them.  No ancilla is needed, which
    is why this is preferred here -- an ancilla would change the emitter's
    contract from "n wires in, n wires out" to something the round-trip test
    would have to make allowances for.

        C^k P(t) = C^(k-1) P(t/2) . CX . C^(k-1) P(-t/2) . CX . C^(k-1) P(t/2)

    Exponential in the number of controls, and that is fine at the widths a
    simulator can reach; a device-bound compiler would spend ancillas instead.
    """
    ws = list(wires)
    if not ws:
        return [("gphase", [], angle)]
    if len(ws) == 1:
        return [("p", [ws[0]], angle)]
    if len(ws) == 2:
        return [("cp", ws, angle)]
    a, b, rest = ws[0], ws[1], ws[2:]
    half = angle / 2
    return (_phase([b] + rest, half)
            + [("cx", [a, b])]
            + _phase([b] + rest, -half)
            + [("cx", [a, b])]
            + _phase([a] + rest, half))


def _controlled(name: str, wires: Sequence[int], ctrls: Ctrls, angle=None) -> List[Gate]:
    """One gate under `len(ctrls)` controls, or a refusal naming what is missing."""
    flips = _flips(ctrls)
    lines = [w for w, _ in ctrls]

    if name == "gphase":
        # A controlled global phase is a relative phase on the controls.
        return flips + _phase(lines, angle) + flips

    if name == "p":
        # A phase on a wire, under controls, is a phase on all of them together.
        return flips + _phase(lines + list(wires), angle) + flips

    if name == "x":
        # X is a phase in the other basis: H, then a phase of pi on every wire
        # at once, then H.  At nought or one control the direct gate is smaller.
        (target,) = wires
        if len(lines) <= 2:
            direct = {0: "x", 1: "cx", 2: "ccx"}[len(lines)]
            return flips + [(direct, lines + [target])] + flips
        return (flips + [("h", [target])] + _phase(lines + [target], math.pi)
                + [("h", [target])] + flips)

    if name == "z":
        (target,) = wires
        return flips + _phase(lines + [target], math.pi) + flips

    table = {0: {"h": "h", "s": "s", "swap": "swap"},
             1: {"h": "ch", "swap": "cswap"}}
    depth = len(lines)
    if depth in table and name in table[depth]:
        return flips + [(table[depth][name], lines + list(wires))] + flips
    raise NotEmittable(
        f"`{name}` under {depth} control(s) has no decomposition here. Phases and "
        "`x` are handled at any depth; `h` is handled at nought and one, which is "
        "all the libraries need, and deeper would want the square-root recursion."
    )


# ---------------------------------------------------------------------------
# The walk.
# ---------------------------------------------------------------------------


def _walk(t: Term, ty: Type, layout: Layout, ctrls: Ctrls, env: Dict[str, Term],
          depth: int) -> Tuple[List[Gate], Layout, Type]:
    """Emit `t` acting on `layout`, returning the gates and the outgoing layout."""
    if depth <= 0:
        raise NotEmittable("recursion too deep; is a definition recursive?")

    match t:
        case Ref(name, inv):
            if name not in env:
                raise NotEmittable(f"undefined: {name}")
            body = env[name]
            return _walk(dagger(body) if inv else body, ty, layout, ctrls, env, depth - 1)

        case Prim(name, inv):
            return _prim(name, inv, ty, layout, ctrls)

        case Seq(s, u):
            gs, layout, mid = _walk(s, ty, layout, ctrls, env, depth)
            hs, layout, out = _walk(u, mid, layout, ctrls, env, depth)
            return gs + hs, layout, out

        case Prod(s, u):
            a, b = _split_prod(ty)
            wa = _w(a)
            gs, la, ca = _walk(s, a, layout[:wa], ctrls, env, depth)
            hs, lb, cb = _walk(u, b, layout[wa:], ctrls, env, depth)
            return gs + hs, la + lb, TProd(ca, cb)

        case Sum(s, u):
            a, b = _split_sum(ty)
            if _w(a) != _w(b):
                raise NotEmittable("a choice between registers of different widths")
            tag, rest = layout[0], layout[1:]
            gs, la, ca = _walk(s, a, rest, ctrls + ((tag, 0),), env, depth)
            hs, lb, cb = _walk(u, b, rest, ctrls + ((tag, 1),), env, depth)
            if la != lb:
                # `ctrl swap` lands here: one branch is `id` and the other
                # permutes.  Bring the second back to the first's layout with
                # swaps under that branch's own controls -- which is how the
                # Fredkin gate falls out of `ctrl swapprod`.
                for w1, w2 in _swaps_from_to(lb, la):
                    hs += _controlled("swap", (w1, w2), ctrls + ((tag, 1),))
            return gs + hs, (tag,) + la, TSum(ca, cb)

        case Union(_, _):
            raise NotEmittable("`|` is not a Q42 construct")
        case Star(_):
            raise NotEmittable("`^` is not a Q42 construct")

    raise NotEmittable(f"cannot emit {t!r}")


def _prim(name: str, inv: bool, ty: Type, layout: Layout, ctrls: Ctrls):
    """The ten primitives.  Seven of them return no gates."""
    sign = -1 if inv else 1

    if name == "id":
        return [], layout, ty

    if name == "omega":
        return _controlled("gphase", (), ctrls, sign * EIGHTH), layout, ty

    if name == "v":
        # `v` is a square root of X -- but the *other* one, `sxdg` times -1, and
        # `sxdg` is not in the standard include.  Rather than invent a definition
        # for it (a phase is easy to get wrong there, and a wrong phase under a
        # control is a wrong circuit), spell it with gates the target already has:
        #
        #     v = e^(3i.pi/4) . S H S            checked in tests/test_emit.py
        #
        # written as a phase rather than `s` so that multi-control handling has
        # only phases and `h` to deal with.
        w = layout[0]
        turn = [("s", math.pi / 2)] if not inv else [("s", -math.pi / 2)]
        gs = _controlled("gphase", (), ctrls, sign * 3 * math.pi / 4)
        gs += _controlled("p", (w,), ctrls, turn[0][1])
        gs += _controlled("h", (w,), ctrls)
        gs += _controlled("p", (w,), ctrls, turn[0][1])
        a, b = _split_sum(ty)
        return gs, layout, TSum(a, b)

    if name == "swapsum":
        a, b = _split_sum(ty)
        if _w(a) != _w(b):
            raise NotEmittable("`swapsum` between registers of different widths")
        return _controlled("x", (layout[0],), ctrls), layout, TSum(b, a)

    if name == "swapprod":
        a, b = _split_prod(ty) if not inv else _split_prod(ty)[::-1]
        wa = _w(a)
        # No gate: exchanging two blocks is a relabelling in a format with no
        # fixed topology, and the layout carries it.
        return [], layout[wa:] + layout[:wa], TProd(b, a)

    if name in ("assocprod", "unitprod", "dist"):
        # Pure re-bracketing.  The wires and their order are untouched; only the
        # type's shape changes, and `_reshape` says how.
        return [], layout, _reshape(name, inv, ty)

    if name in ("assocsum", "unitsum"):
        raise NotEmittable(
            f"`{name}` cannot appear at a register type: its two sides cannot "
            "both be registers, so a term using it is not emittable"
        )

    raise NotEmittable(f"unknown primitive: {name}")


def _reshape(name: str, inv: bool, ty: Type) -> Type:
    """The codomain of a re-bracketing primitive, given its domain."""
    if name == "assocprod":
        if not inv:
            a, bc = _split_prod(ty)
            b, c = _split_prod(bc)
            return TProd(TProd(a, b), c)
        ab, c = _split_prod(ty)
        a, b = _split_prod(ab)
        return TProd(a, TProd(b, c))
    if name == "unitprod":
        if not inv:
            _one, a = _split_prod(ty)
            return a
        return TProd(TOne(), ty)
    if name == "dist":
        if not inv:
            ab, c = _split_prod(ty)
            a, b = _split_sum(ab)
            return TSum(TProd(a, c), TProd(b, c))
        ac, bc = _split_sum(ty)
        a, c = _split_prod(ac)
        b, _c = _split_prod(bc)
        return TProd(TSum(a, b), c)
    raise NotEmittable(f"not a reshaping primitive: {name}")


# ---------------------------------------------------------------------------
# The entry point.
# ---------------------------------------------------------------------------


def emit(term: Term, dom: Type, env: Dict[str, Term] | None = None,
         depth: int = 200) -> Tuple[List[Gate], int]:
    """Gates for `term` read at domain `dom`, and how many wires they need."""
    n = _w(dom)
    gates, layout, _cod = _walk(term, dom, tuple(range(n)), (), env or {}, depth)
    if layout != tuple(range(n)):
        # A term may end with its wires permuted; say so with swaps rather than
        # leaving the caller to guess.
        gates = gates + _swaps_to_identity(layout)
    return gates, n


def _swaps_from_to(src: Layout, dst: Sequence[int]) -> List[Tuple[int, int]]:
    """Pairs of wires to exchange so that `src` becomes `dst`."""
    cur = list(src)
    out: List[Tuple[int, int]] = []
    for i in range(len(cur)):
        if cur[i] == dst[i]:
            continue
        w1, w2 = cur[i], dst[i]
        out.append((w1, w2))
        for k in range(len(cur)):
            if cur[k] == w2:
                cur[k] = w1
        cur[i] = w2
    return out


def _swaps_to_identity(layout: Layout) -> List[Gate]:
    """Swaps returning a permuted layout to `0, 1, 2, ...`."""
    return [("swap", [a, b]) for a, b in _swaps_from_to(layout, tuple(range(len(layout))))]


# ---------------------------------------------------------------------------
# OpenQASM 3 text.
# ---------------------------------------------------------------------------

#: Gates from the standard include, so the output needs no definitions of its own.
_STD = {"x", "y", "z", "h", "s", "sdg", "t", "tdg", "sx", "cx", "cy", "cz", "ch",
        "ccx", "ccz", "swap", "cswap", "p", "cp"}


def to_qasm(gates: Sequence[Gate], n: int, name: str = "main") -> str:
    """The gates as OpenQASM 3, ready for any toolchain that reads it.

    Two notes on fidelity. `sxdg` is not in the standard include, so it is
    emitted as its own one-line definition rather than silently replaced by
    something equal up to a phase. And `gphase` is written out: Q42 knows its
    global phase exactly, most formats do not care, and throwing away a fact
    because the reader may ignore it is not the emitter's decision to make.
    """
    lines = ['OPENQASM 3.0;', 'include "stdgates.inc";', "",
             f"qubit[{n}] q;", ""]
    for g in gates:
        op, qs = g[0], list(g[1])
        angle = g[2] if len(g) > 2 else None
        if op == "gphase":
            lines.append(f"gphase({angle:.17g});")
            continue
        if op not in _STD:
            raise NotEmittable(f"`{op}` is not in the standard gate set")
        args = ", ".join(f"q[{i}]" for i in qs)
        lines.append(f"{op}({angle:.17g}) {args};" if angle is not None
                     else f"{op} {args};")
    return "\n".join(lines) + "\n"
