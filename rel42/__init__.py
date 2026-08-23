"""42 — a point-free reversible language interpreted in Rel."""

from .core import (
    EMPTY,
    Inl,
    Inr,
    Pair,
    Prim,
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
    dagger,
    run,
)
from .syntax import (
    as_list,
    as_nat,
    from_list,
    from_nat,
    parse_program,
    parse_term,
    parse_value,
    show,
    show_as,
    show_term,
)

__all__ = [
    "EMPTY", "Inl", "Inr", "Pair", "Prim", "Prod", "Ref", "Rel42Error", "Seq",
    "Star", "Sum", "Term", "UNIT", "Union", "Unit", "Value", "dagger", "run",
    "as_list", "as_nat", "from_list", "from_nat", "parse_program", "parse_term",
    "parse_value", "show", "show_term",
]
