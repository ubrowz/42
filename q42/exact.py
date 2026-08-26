"""Exact amplitudes: the ring `Z[1/sqrt2, i]`, which is where they all live.

Q42's two generators are an eighth root of unity and a square root of `swapsum`,
and the semiring plumbing contributes only 0 and 1, so every amplitude any Q42
program can produce is a sum of products of those -- an element of
`Z[1/sqrt2, i]`.  That ring is countable and has decidable equality, so "do
these two terms denote the same matrix" is a question with an exact answer, and
this module is what makes the evaluator give it rather than a float that is
nearly right.

The representation is the usual one.  With `w = e^{i pi/4}` a primitive eighth
root of unity, `Z[w]` is a free Z-module on `1, w, w^2, w^3` (the minimal
polynomial of `w` is `x^4 + 1`, so those four are independent), and

    sqrt2 = w - w^3

lies in it.  An amplitude is therefore

    (a + b w + c w^2 + d w^3) / sqrt2^k

with `a, b, c, d` integers and `k >= 0`.  Reduced -- `k` made as small as it can
be -- that quadruple is unique, so equality is a tuple comparison and this
module needs no tolerance anywhere.

Mixed arithmetic keeps the exactness where it can and gives it up where it must:
combining with an `int` stays exact, combining with a `float` or a `complex`
falls back to `complex`.  Nothing inside the evaluator introduces a float, so in
practice the fallback is only reached by callers that have already chosen to
work numerically -- the printer, the sampler, the QASM cross-check.
"""

from __future__ import annotations

from typing import Tuple

__all__ = ["Exact", "OMEGA", "ONE", "ZERO", "ROOT2", "norm2", "is_zero"]

_Poly = Tuple[int, int, int, int]

_R2 = 2 ** 0.5


def _times_root2(n: _Poly) -> _Poly:
    """Multiply the numerator by `sqrt2 = w - w^3`, reducing `w^4 = -1`."""
    a, b, c, d = n
    return (b - d, a + c, b + d, c - a)


def _divisible(n: _Poly) -> bool:
    """Is the numerator a multiple of `sqrt2` in `Z[w]`?

    From `_times_root2`, a product with `sqrt2` has `a + c` and `b + d` both
    even, and the converse holds because the division below inverts it.
    """
    a, b, c, d = n
    return (a - c) % 2 == 0 and (b - d) % 2 == 0


def _over_root2(n: _Poly) -> _Poly:
    """Divide the numerator by `sqrt2`; only valid when `_divisible`."""
    a, b, c, d = n
    return ((b - d) // 2, (a + c) // 2, (b + d) // 2, (c - a) // 2)


def _reduce(n: _Poly, k: int) -> Tuple[_Poly, int]:
    if n == (0, 0, 0, 0):
        return n, 0
    while k > 0 and _divisible(n):
        n, k = _over_root2(n), k - 1
    return n, k


def _mul(x: _Poly, y: _Poly) -> _Poly:
    out = [0, 0, 0, 0]
    for i in range(4):
        if not x[i]:
            continue
        for j in range(4):
            if not y[j]:
                continue
            p, term = i + j, x[i] * y[j]
            if p >= 4:  # w^4 = -1
                out[p - 4] -= term
            else:
                out[p] += term
    return (out[0], out[1], out[2], out[3])


class Exact:
    """`(a + b w + c w^2 + d w^3) / sqrt2^k`, reduced, with `w = e^{i pi/4}`."""

    __slots__ = ("n", "k")

    def __init__(self, a: int = 0, b: int = 0, c: int = 0, d: int = 0, k: int = 0):
        if k < 0:  # a negative exponent is a whole power of sqrt2 in the numerator
            n = (a, b, c, d)
            for _ in range(-k):
                n = _times_root2(n)
            a, b, c, d = n
            k = 0
        object.__setattr__(self, "n", None)  # placate __slots__ ordering
        self.n, self.k = _reduce((a, b, c, d), k)

    # -- construction ------------------------------------------------------

    @staticmethod
    def _raw(n: _Poly, k: int) -> "Exact":
        out = Exact.__new__(Exact)
        out.n, out.k = _reduce(n, k)
        return out

    @staticmethod
    def coerce(z):
        """`z` as an `Exact`, or None if it is not exactly representable."""
        if isinstance(z, Exact):
            return z
        if isinstance(z, int):
            return Exact._raw((z, 0, 0, 0), 0)
        return None

    # -- arithmetic --------------------------------------------------------

    def _align(self, other: "Exact") -> Tuple[_Poly, _Poly, int]:
        k = max(self.k, other.k)
        x, y = self.n, other.n
        for _ in range(k - self.k):
            x = _times_root2(x)
        for _ in range(k - other.k):
            y = _times_root2(y)
        return x, y, k

    def __add__(self, other):
        o = Exact.coerce(other)
        if o is None:
            if isinstance(other, (float, complex)):
                return complex(self) + other
            return NotImplemented
        x, y, k = self._align(o)
        return Exact._raw(tuple(p + q for p, q in zip(x, y)), k)

    __radd__ = __add__

    def __neg__(self):
        return Exact._raw(tuple(-p for p in self.n), self.k)

    def __sub__(self, other):
        o = Exact.coerce(other)
        if o is None:
            if isinstance(other, (float, complex)):
                return complex(self) - other
            return NotImplemented
        return self + (-o)

    def __rsub__(self, other):
        o = Exact.coerce(other)
        if o is None:
            if isinstance(other, (float, complex)):
                return other - complex(self)
            return NotImplemented
        return o + (-self)

    def __mul__(self, other):
        o = Exact.coerce(other)
        if o is None:
            if isinstance(other, (float, complex)):
                return complex(self) * other
            return NotImplemented
        return Exact._raw(_mul(self.n, o.n), self.k + o.k)

    __rmul__ = __mul__

    def __truediv__(self, other):
        """Division leaves the ring, so it leaves exactness with it.

        `Z[1/sqrt2, i]` is a ring and not a field -- `1/(1 + w)` is not in it --
        so there is no exact answer to return in general and no point pretending
        otherwise for the cases where there would be.  Nothing in the evaluator
        divides; the callers that do (the global-phase check in
        `tools/qasm_sim.py`, the printer) are numeric already.
        """
        if isinstance(other, (Exact, int, float, complex)):
            return complex(self) / complex(other)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, (Exact, int, float, complex)):
            return complex(other) / complex(self)
        return NotImplemented

    def __pow__(self, e: int):
        if not isinstance(e, int) or e < 0:
            return NotImplemented
        out, base = ONE, self
        while e:
            if e & 1:
                out = out * base
            base, e = base * base, e >> 1
        return out

    # -- the complex number it denotes -------------------------------------

    def conjugate(self) -> "Exact":
        """`w` conjugates to `w^7 = -w^3`, and `sqrt2` is real."""
        a, b, c, d = self.n
        return Exact._raw((a, -d, -c, -b), self.k)

    def __complex__(self) -> complex:
        # w = (1+i)/sqrt2 and w^3 = (-1+i)/sqrt2, so the rational part and the
        # sqrt2 part separate.  Whichever of k, k+1 is even gives an exact
        # power-of-two divisor, which leaves one multiplication by sqrt2 as the
        # only inexact step -- `Exact(0,0,0,1,1)` then comes out -0.5+0.5j on
        # the nose rather than a bit under it.
        a, b, c, d = self.n
        rational, rooted = complex(a, c), complex(b - d, b + d)
        if self.k % 2 == 0:
            half = 2 ** (self.k // 2)
            return rational / half + rooted * _R2 / (2 * half)
        half = 2 ** ((self.k + 1) // 2)
        return rational * _R2 / half + rooted / half

    @property
    def real(self) -> float:
        return complex(self).real

    @property
    def imag(self) -> float:
        return complex(self).imag

    def __abs__(self) -> float:
        return abs(complex(self))

    # -- comparison --------------------------------------------------------

    def __eq__(self, other) -> bool:
        o = Exact.coerce(other)
        if o is not None:
            return self.n == o.n and self.k == o.k
        if isinstance(other, (float, complex)):
            return complex(self) == other
        return NotImplemented

    def __bool__(self) -> bool:
        return self.n != (0, 0, 0, 0)

    def __hash__(self) -> int:
        return hash(complex(self))

    def __repr__(self) -> str:
        a, b, c, d = self.n
        return f"Exact({a}, {b}, {c}, {d}, k={self.k})"


ZERO = Exact()
ONE = Exact(1)
OMEGA = Exact(0, 1, 0, 0)          # w = e^{i pi/4}
ROOT2 = Exact(0, 1, 0, -1)         # w - w^3


def is_zero(z) -> bool:
    """Exactly zero for an `Exact`, zero to within tolerance for a float."""
    if isinstance(z, Exact):
        return not z
    return abs(z) <= 1e-12


def norm2(z) -> float:
    """`|z|^2`, computed in the ring when it can be.

    `z * conj(z)` is real and lies in `Z[1/sqrt2]`, so this is one rounding at
    the end rather than a square root followed by a squaring.
    """
    if isinstance(z, Exact):
        return (z * z.conjugate()).real
    return abs(z) ** 2
