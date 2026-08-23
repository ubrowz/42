"""An independent simulator for the gate lists an emitter will produce.

This exists to be *not* `q42`.  The point of a round-trip check is that two
things computed different ways agree, so this file deliberately shares nothing
with the evaluator it is meant to check: no `Value`, no `Term`, no primitive
table, no basis enumeration.  It knows only about complex matrices, qubit
indices, and a gate set an OpenQASM backend would accept.

    >>> unitary_of([("h", [0]), ("cx", [0, 1])], 2)      # a Bell pair
    [[0.707..., 0, 0.707..., 0], ...]

CONVENTIONS, which must match `q42.types.basis_of`:

* qubit 0 is the **leftmost** in a ket, so |abc> has a at index 0.  A basis
  state's row is therefore `sum(bit_i << (n - 1 - i))`, big-endian.
* the gate list is applied left to right, in diagrammatic order, matching `;`.

`gphase` is carried explicitly rather than ignored.  Q42 tracks global phase
exactly, because `omega` acts on the unit type; OpenQASM 3 can say so with
`gphase`, and a round trip that compares exactly is worth more than one that
compares up to a factor nobody checked.
"""

from __future__ import annotations

import cmath
import math
from typing import Iterable, List, Sequence, Tuple

#: `(name, qubits)`, or `(name, qubits, angle)` for the parameterised phases.
Gate = Tuple[str, Sequence[int]]
Matrix = List[List[complex]]

_R2 = 1 / math.sqrt(2)

#: One- and two-qubit gates, as matrices over their own qubits.
GATES = {
    "id":   [[1, 0], [0, 1]],
    "x":    [[0, 1], [1, 0]],
    "y":    [[0, -1j], [1j, 0]],
    "z":    [[1, 0], [0, -1]],
    "h":    [[_R2, _R2], [_R2, -_R2]],
    "s":    [[1, 0], [0, 1j]],
    "sdg":  [[1, 0], [0, -1j]],
    "t":    [[1, 0], [0, cmath.exp(1j * math.pi / 4)]],
    "tdg":  [[1, 0], [0, cmath.exp(-1j * math.pi / 4)]],
    "sx":   [[(1 + 1j) / 2, (1 - 1j) / 2], [(1 - 1j) / 2, (1 + 1j) / 2]],
    "sxdg": [[(1 - 1j) / 2, (1 + 1j) / 2], [(1 + 1j) / 2, (1 - 1j) / 2]],
}

#: Gates given as a controlled version of a one-qubit gate: controls, then target.
CONTROLLED = {"cx": "x", "cz": "z", "ch": "h", "cy": "y", "ccx": "x", "ccz": "z"}

#: How many controls each of those takes.
NCONTROL = {"cx": 1, "cz": 1, "ch": 1, "cy": 1, "ccx": 2, "ccz": 2}


def _identity(dim: int) -> Matrix:
    return [[1 if i == j else 0 for j in range(dim)] for i in range(dim)]


def _bit(row: int, q: int, n: int) -> int:
    """Bit `q` of basis index `row`, counting qubit 0 as the most significant."""
    return (row >> (n - 1 - q)) & 1


def _with_bit(row: int, q: int, n: int, value: int) -> int:
    mask = 1 << (n - 1 - q)
    return (row | mask) if value else (row & ~mask)


def gate_matrix(name: str, qs: Sequence[int], n: int, angle: float | None = None) -> Matrix:
    """The `2**n` matrix of one gate acting on the named qubits."""
    dim = 1 << n
    out = [[0j] * dim for _ in range(dim)]

    if name in ("p", "cp"):
        # A relative phase: `p` multiplies the |1> component of one qubit, and
        # `cp` does so only when its control is set.  `p` is what a controlled
        # *global* phase becomes, which is how `id + omega` turns into a T gate.
        if angle is None:
            raise ValueError(f"{name} needs an angle")
        factor = cmath.exp(1j * angle)
        *controls, target = qs
        for row in range(dim):
            hot = _bit(row, target, n) and all(_bit(row, c, n) for c in controls)
            out[row][row] = factor if hot else 1
        return out

    if name in ("swap", "cswap"):
        *controls, a, b = qs
        for row in range(dim):
            if all(_bit(row, c, n) for c in controls):
                col = _with_bit(_with_bit(row, a, n, _bit(row, b, n)), b, n,
                                _bit(row, a, n))
            else:
                col = row
            out[col][row] = 1
        return out

    if name in CONTROLLED:
        *controls, target = qs
        if len(controls) != NCONTROL[name]:
            raise ValueError(f"{name} takes {NCONTROL[name]} control(s), got {controls}")
        base = GATES[CONTROLLED[name]]
        for row in range(dim):
            if all(_bit(row, c, n) for c in controls):
                bit = _bit(row, target, n)
                for new in (0, 1):
                    amp = base[new][bit]
                    if amp:
                        out[_with_bit(row, target, n, new)][row] += amp
            else:
                out[row][row] += 1
        return out

    if name not in GATES:
        raise ValueError(f"unknown gate: {name}")
    (target,) = qs
    base = GATES[name]
    for row in range(dim):
        bit = _bit(row, target, n)
        for new in (0, 1):
            amp = base[new][bit]
            if amp:
                out[_with_bit(row, target, n, new)][row] += amp
    return out


def _multiply(a: Matrix, b: Matrix) -> Matrix:
    """`a` applied after `b`, both square and the same size."""
    dim = len(a)
    return [[sum(a[i][k] * b[k][j] for k in range(dim)) for j in range(dim)]
            for i in range(dim)]


def unitary_of(gates: Iterable[Gate], n: int) -> Matrix:
    """The matrix of a whole gate list, applied left to right."""
    out = _identity(1 << n)
    phase = 1 + 0j
    for g in gates:
        name, qs = g[0], g[1]
        angle = g[2] if len(g) > 2 else None
        if name == "gphase":
            phase *= cmath.exp(1j * float(angle if angle is not None else qs[0]))
            continue
        out = _multiply(gate_matrix(name, qs, n, angle), out)
    if phase != 1:
        out = [[phase * x for x in row] for row in out]
    return out


def agree(a: Matrix, b: Matrix, *, up_to_phase: bool = False, tol: float = 1e-9):
    """Whether two matrices are equal; optionally ignoring one global factor.

    Returns `(True, None)` or `(False, reason)`, because a bare `False` in a test
    failure tells you nothing about which entry went wrong.
    """
    if len(a) != len(b):
        return False, f"different sizes: {len(a)} and {len(b)}"
    factor = 1 + 0j
    if up_to_phase:
        for i in range(len(a)):
            for j in range(len(a)):
                if abs(b[i][j]) > tol:
                    factor = a[i][j] / b[i][j]
                    break
            else:
                continue
            break
    worst, where = 0.0, None
    for i in range(len(a)):
        for j in range(len(a)):
            d = abs(a[i][j] - factor * b[i][j])
            if d > worst:
                worst, where = d, (i, j)
    if worst > tol:
        return False, f"differ by {worst:.3g} at {where}"
    return True, None
