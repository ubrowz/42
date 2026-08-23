"""Q42 -- 42 over C: a point-free quantum language, interpreted in Unitary.

    python3 -m q42 matrix  q42/gates.42 h
    python3 -m q42 run     q42/gates.42 bell "|00>"
    python3 -m q42 unitary q42/gates.42

Sibling of `rel42`, not a fork of it.  `Value`, `Term`, `dagger`, the parser and
the type-inference engine are imported from there unchanged; what differs is the
primitive table and the evaluator.  See Q42.md.
"""

from .core import (
    OMEGA,
    ONE,
    PRIMS,
    V_MATRIX,
    Vec,
    ZERO,
    Q42Error,
    apply_vec,
    column,
    dagger,
    matrix,
    normalise,
    probabilities,
    sample,
    validate,
)
from .syntax import (
    bits_of,
    ket,
    parse_program,
    parse_state,
    parse_term,
    show_ket,
    show_term,
)
from .types import (
    PRIM_SCHEMES,
    QUBIT,
    basis_of,
    dimension,
    infer,
    infer_all,
    qubits,
    show_scheme,
)

__all__ = [
    "OMEGA",
    "ONE",
    "PRIMS",
    "PRIM_SCHEMES",
    "QUBIT",
    "Q42Error",
    "V_MATRIX",
    "Vec",
    "ZERO",
    "apply_vec",
    "basis_of",
    "bits_of",
    "column",
    "dagger",
    "dimension",
    "infer",
    "infer_all",
    "ket",
    "matrix",
    "normalise",
    "parse_program",
    "probabilities",
    "parse_state",
    "parse_term",
    "qubits",
    "sample",
    "show_ket",
    "show_scheme",
    "show_term",
    "validate",
]
