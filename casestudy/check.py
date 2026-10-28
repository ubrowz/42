#!/usr/bin/env python3
"""Check the Q42 modular adders against the 42 specification, and count gates.

For every modulus in ADDERS and every a, b < N, this runs `spec.42`'s `modadd`
in 42 on the numbers (a, (b, N)) and `modadd.42`'s adder in Q42 on the basis
state holding a and b with every ancilla at |0>, and asks that the Q42 output be
exactly one basis state, with amplitude exactly 1, holding the spec's answer and
every ancilla back at |0>.  The amplitudes are exact (q42/exact.py), so "exactly"
means what it says.

Then it checks the circuit as well as the term: it emits each adder with
`q42/emit.py` and runs the gate list on the same inputs, bit by bit, with a
ten-line simulator that shares no code with Q42.  The adders only permute basis
states, so following one bit string through the gates is the whole simulation.

It does not compare the two on inputs outside a, b < N, where the spec has no
answer and the circuit still does something: see casestudy/CASESTUDY.md.

    python3 casestudy/check.py            -- check, then print the gate counts
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(20000)

from rel42.core import Inl, Inr, Pair, Ref, Unit, run              # noqa: E402
from rel42.syntax import as_nat, from_nat, parse_program            # noqa: E402
from rel42.core import expand_env                                   # noqa: E402
from q42.__main__ import _load_reduced, _resolve, _typed            # noqa: E402
from q42.core import column                                          # noqa: E402
from q42.emit import emit                                            # noqa: E402
from q42.exact import ONE                                            # noqa: E402
from q42.types import ground                                         # noqa: E402

#: name in modadd.42, bits per number, modulus
ADDERS = [("mod3", 2, 3), ("mod5", 3, 5), ("mod7", 3, 7), ("mod13", 4, 13)]

BIT = {0: Inl(Unit()), 1: Inr(Unit())}


def register(k: int, n: int):
    """The n-bit register holding k, least significant bit first, nested right."""
    bits = [BIT[(k >> i) & 1] for i in range(n)]
    v = bits[-1]
    for b in reversed(bits[:-1]):
        v = Pair(b, v)
    return v


def state(a: int, b: int, n: int):
    """(a, (b, (z, (c, (k, s))))) with every ancilla at |0>."""
    return Pair(register(a, n), Pair(register(b, n),
                Pair(BIT[0], Pair(BIT[0], Pair(register(0, n), BIT[0])))))


def spec(env, a: int, b: int, N: int) -> int:
    out = run(Ref("modadd"), Pair(from_nat(a), Pair(from_nat(b), from_nat(N))), env)
    assert len(out) == 1, f"spec gives {len(out)} results for {a} + {b} mod {N}"
    (r,) = out
    assert as_nat(r.a) == a and as_nat(r.b.b) == N
    return as_nat(r.b.a)


def check(qenv, senv, name: str, n: int, N: int) -> int:
    term = _resolve(qenv, name)
    for a in range(N):
        for b in range(N):
            want = state(a, spec(senv, a, b, N), n)
            got = column(term, state(a, b, n), qenv)
            got = {v: amp for v, amp in got.items() if amp != 0}
            assert got == {want: ONE}, f"{name}: {a} + {b} mod {N} gives {got}"
    return N * N


def circuit(qenv, name: str):
    term = _resolve(qenv, name)
    at = ground(_typed(qenv, name, term))
    return emit(term, at.dom, qenv)


def bits(v) -> list:
    """A basis value's qubits in wire order: the leaves, left to right."""
    if isinstance(v, Pair):
        return bits(v.a) + bits(v.b)
    return [0 if isinstance(v, Inl) else 1]


def simulate(gates, wires: list) -> list:
    """Run x, cx, ccx and swap on a list of bits."""
    w = list(wires)
    for g in gates:
        name, qs = g[0], g[1]
        if name == "swap":
            w[qs[0]], w[qs[1]] = w[qs[1]], w[qs[0]]
        elif name in ("x", "cx", "ccx") and all(w[q] for q in qs[:-1]):
            w[qs[-1]] ^= 1
        elif name not in ("x", "cx", "ccx"):
            raise ValueError(f"not a classical gate: {name}")
    return w


def check_circuit(qenv, senv, name: str, n: int, N: int) -> int:
    gates, _wires = circuit(qenv, name)
    for a in range(N):
        for b in range(N):
            want = bits(state(a, spec(senv, a, b, N), n))
            got = simulate(gates, bits(state(a, b, n)))
            assert got == want, f"{name} circuit: {a} + {b} mod {N} gives {got}"
    return N * N


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    qenv = _load_reduced(str(here / "modadd.42"))
    senv = expand_env(parse_program((here / "spec.42").read_text(encoding="utf-8")))
    for name, n, N in ADDERS:
        k = check(qenv, senv, name, n, N)
        print(f"  [ok ] {name}: all {k} inputs a, b < {N} agree with spec.42")
        check_circuit(qenv, senv, name, n, N)
        print(f"  [ok ] {name}: so does the emitted circuit")
    print()
    print(f"  {'adder':6} {'bits':>4} {'qubits':>6} {'ccx':>4} {'cx':>4} {'x':>3} {'total':>5}")
    for name, n, N in ADDERS:
        gates, wires = circuit(qenv, name)
        c, total = Counter(g[0] for g in gates), len(gates)
        print(f"  {name:6} {n:>4} {wires:>6} {c['ccx']:>4} {c['cx']:>4} {c['x']:>3} {total:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
