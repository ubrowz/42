#!/usr/bin/env python3
"""The Qiskit baseline for the modular adder case study.

Needs Qiskit and its OpenQASM 3 importer, which the rest of the repository does
not:

    python3 -m venv /tmp/qvenv
    /tmp/qvenv/bin/pip install qiskit qiskit_qasm3_import
    /tmp/qvenv/bin/python casestudy/baseline.py

For each adder in ADDERS it builds the same construction in Qiskit, from
Qiskit's own ripple-carry adder (`CDKMRippleCarryAdder`, the Cuccaro adder), and
checks it on every input a, b < N against spec.42, through the same encoders
`42q check` uses.  It then reads Q42's emitted OpenQASM into
Qiskit, so that both circuits are counted by the same code, and runs both
through Qiskit's transpiler at its highest optimisation level, once into
{ccx, cx, x} and once into Clifford+T, where a Toffoli costs seven T gates.
"""
from __future__ import annotations

import pathlib
import sys

from qiskit import QuantumCircuit, QuantumRegister, qasm3, transpile
from qiskit.circuit.library import CDKMRippleCarryAdder

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.setrecursionlimit(20000)

from q42.__main__ import _leaves, _load_reduced, _resolve, _run_bits, _typed  # noqa: E402
from q42.emit import emit, to_qasm                                     # noqa: E402
from q42.types import ground                                           # noqa: E402
from rel42.core import Pair, Ref, expand_env, run                      # noqa: E402
from rel42.syntax import from_nat, parse_program                       # noqa: E402

#: name in modadd.42, bits per number, modulus; the encoder is enc<N>
ADDERS = [("mod3", 2, 3), ("mod5", 3, 5), ("mod7", 3, 7), ("mod13", 4, 13)]

CLIFFORD_T = ["h", "s", "sdg", "t", "tdg", "cx", "x"]


def qiskit_modadd(n: int, N: int) -> QuantumCircuit:
    """Vedral-Barenco-Ekert from Qiskit's Cuccaro adder, wires as in modadd.42."""
    a, b, z, c = (QuantumRegister(n, "a"), QuantumRegister(n, "b"),
                  QuantumRegister(1, "z"), QuantumRegister(1, "c"))
    k, s = QuantumRegister(n, "k"), QuantumRegister(1, "s")
    qc = QuantumCircuit(a, b, z, c, k, s)
    add = CDKMRippleCarryAdder(n, kind="half")         # wires: a, b, cout, help
    sub = add.inverse()
    ones = [i for i in range(n) if N >> i & 1]

    def adder(gate, x):
        qc.compose(gate, list(x) + list(b) + [z[0], c[0]], inplace=True)

    adder(add, a)                                      # b := a + b
    for i in ones:
        qc.x(k[i])
    adder(sub, k)                                      # b := b - N
    for i in ones:
        qc.x(k[i])
    qc.cx(z[0], s[0])                                  # s := (a + b < N)
    for i in ones:
        qc.cx(s[0], k[i])
    adder(add, k)                                      # b := b + s N
    for i in ones:
        qc.cx(s[0], k[i])
    adder(sub, a)                                      # b := b - a
    qc.x(z[0])
    qc.cx(z[0], s[0])                                  # s := 0
    qc.x(z[0])
    adder(add, a)                                      # b := b + a
    return qc


def gates_of(qc: QuantumCircuit):
    """A circuit in {ccx, cx, x, swap} as gate tuples on wire indices."""
    return [(i.operation.name, [qc.find_bit(q).index for q in i.qubits]) for i in qc.data]


def one(vs):
    (v,) = vs
    return v


def verify(qc: QuantumCircuit, spec, n: int, N: int) -> None:
    """On every a, b < N: encode, run the circuit, compare with the spec's answer."""
    gates = gates_of(transpile(qc, basis_gates=["ccx", "cx", "x", "swap"],
                               optimization_level=0))
    enc = Ref(f"enc{N}")
    for x in range(N):
        for y in range(N):
            given = Pair(from_nat(x), Pair(from_nat(y), from_nat(N)))
            want = one(run(enc, one(run(Ref("modadd"), given, spec)), spec))
            got = _run_bits(gates, _leaves(one(run(enc, given, spec))))
            assert got == _leaves(want), f"qiskit: {x} + {y} mod {N} gives {got}"


def row(label: str, qc: QuantumCircuit) -> str:
    raw = transpile(qc, basis_gates=["ccx", "cx", "x", "swap"], optimization_level=0)
    opt = transpile(qc, basis_gates=["ccx", "cx", "x", "swap"], optimization_level=3,
                    seed_transpiler=0)
    ct = transpile(qc, basis_gates=CLIFFORD_T, optimization_level=3, seed_transpiler=0)
    r, o, c = raw.count_ops(), opt.count_ops(), ct.count_ops()
    t = c.get("t", 0) + c.get("tdg", 0)
    return (f"  {label:14} {qc.num_qubits:>6} {r.get('ccx', 0):>4} {r.get('cx', 0):>4}"
            f" {o.get('ccx', 0):>7} {o.get('cx', 0):>6} {t:>7} {c.get('cx', 0):>6}"
            f" {ct.depth():>6}")


def main() -> int:
    qenv = _load_reduced(str(HERE / "modadd.42"))
    spec = expand_env(parse_program((HERE / "spec.42").read_text("utf-8")))
    print(f"  {'':14} {'qubits':>6} {'ccx':>4} {'cx':>4}  opt:ccx {'cx':>6}"
          f"  T-count {'cx':>6} {'depth':>6}")
    for name, n, N in ADDERS:
        term = _resolve(qenv, name)
        gates, wires = emit(term, ground(_typed(qenv, name, term)).dom, qenv)
        q42 = qasm3.loads(to_qasm(gates, wires, name))
        theirs = qiskit_modadd(n, N)
        verify(theirs, spec, n, N)
        print(row(f"{name} Q42", q42))
        print(row(f"{name} Qiskit", theirs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
