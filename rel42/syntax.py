"""Concrete syntax for 42: a lexer, a parser for terms and values, and a
pretty-printer.

Term grammar, loosest binding first:

    program := ('def' IDENT '=' term)*
    term    := comp ('|' comp)*        -- nondeterministic choice
    comp    := sum  (';' sum)*         -- composition, diagrammatic order
    sum     := prod ('+' prod)*        -- the sum functor
    prod    := post ('*' post)*        -- the product functor
    post    := atom ('!' | '^')*       -- dagger, star
    atom    := '(' term ')' | IDENT

`!` never reaches the abstract syntax: the parser applies `dagger` on the
spot, which is possible precisely because `dagger` is total.

Value grammar:

    value := 'L' value | 'R' value
           | '(' ')' | '(' value ',' value ')'
           | NUM                        -- Peano nat over  mu X. 1 + X
           | '[' value,* ']'            -- list over  mu X. 1 + (A x X)
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .core import (
    App,
    Fun,
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
    Var,
    dagger,
)

# `types` depends only on `core`, so this is a layering step outward, not a
# cycle.  It is here because printing a value against a type is a printer's job.
from .types import (
    Abbrev,
    Inference,
    TMu,
    TOne,
    TProd,
    TSum,
    TVar,
    TZero,
    refold,
)

# Note: identifiers do not admit a trailing quote, so that `'a'` always lexes
# as a character literal rather than being swallowed by a preceding name.
_TOKEN = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<comment>--[^\n]*)
    | (?P<string>"(?:[^"\\\n]|\\.)*")
    | (?P<char>'(?:[^'\\\n]|\\.)')
    | (?P<num>\d+)
    | (?P<ident>[A-Za-z_][A-Za-z_0-9]*)
    | (?P<op>[;|+*!^(),\[\]=.])
    """,
    re.VERBOSE,
)


class ParseError(Rel42Error):
    pass


def lex(src: str) -> List[Tuple[str, str, int]]:
    toks: List[Tuple[str, str, int]] = []
    i, line = 0, 1
    while i < len(src):
        m = _TOKEN.match(src, i)
        if not m:
            raise ParseError(f"line {line}: unexpected character {src[i]!r}")
        kind = m.lastgroup
        text = m.group()
        line += text.count("\n")
        if kind not in ("ws", "comment"):
            toks.append((kind, text, line))
        i = m.end()
    toks.append(("eof", "", line))
    return toks


class _Parser:
    def __init__(self, toks, prims=None):
        self.toks = toks
        self.i = 0
        # Which identifiers are primitives rather than references.  Injected so
        # that a sibling language over the same grammar -- q42 -- can bring its
        # own primitive set without a second parser.
        self.prims = PRIMS if prims is None else prims
        # Parameters of the definition being parsed.  An identifier in scope is
        # a `Var`; otherwise it is a primitive or a reference.
        self.params: set = set()
        # Type-variable ids for `type` declarations.  Kept well clear of the ids
        # `Inference` allocates, so a declaration can never accidentally alias an
        # inference variable.
        self._tvar = 900_000

    def peek(self):
        return self.toks[self.i]

    def next(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def at(self, text: str) -> bool:
        k, t, _ = self.peek()
        return t == text and k in ("op", "ident")

    def expect(self, text: str):
        k, t, ln = self.next()
        if t != text:
            raise ParseError(f"line {ln}: expected {text!r}, found {t or 'end of input'!r}")
        return t

    # -- terms -------------------------------------------------------------

    def term(self) -> Term:
        node = self.comp()
        while self.at("|"):
            self.next()
            node = Union(node, self.comp())
        return node

    def comp(self) -> Term:
        node = self.sum()
        while self.at(";"):
            self.next()
            node = Seq(node, self.sum())
        return node

    def sum(self) -> Term:
        node = self.prod()
        while self.at("+"):
            self.next()
            node = Sum(node, self.prod())
        return node

    def prod(self) -> Term:
        node = self.app()
        while self.at("*"):
            self.next()
            node = Prod(node, self.app())
        return node

    def app(self) -> Term:
        """Juxtaposition: `ctrl x`.  Binds tighter than every operator.

        Postfix binds tighter still, so `ctrl x!` is `ctrl (x!)` -- which is what
        you want, since the argument is the thing being inverted.
        """
        node = self.post()
        while self._starts_atom():
            node = App(node, self.post())
        return node

    def _starts_atom(self) -> bool:
        kind, text, _ = self.peek()
        if text == "(":
            return True
        # `def` is a hard keyword here: without this, `def f = x def g = y`
        # would read `x def` as an application.
        return kind == "ident" and text != "def"

    def post(self) -> Term:
        node = self.atom()
        while True:
            if self.at("!"):
                self.next()
                node = dagger(node)  # eliminated at parse time
            elif self.at("^"):
                self.next()
                node = Star(node)
            else:
                return node

    def atom(self) -> Term:
        kind, text, ln = self.peek()
        if text == "(":
            self.next()
            node = self.term()
            self.expect(")")
            return node
        if kind == "ident":
            self.next()
            if text in self.params:
                return Var(text)
            return Prim(text) if text in self.prims else Ref(text)
        raise ParseError(f"line {ln}: expected a term, found {text or 'end of input'!r}")

    # -- types -------------------------------------------------------------
    #
    #   typeexpr := 'mu' IDENT '.' typeexpr | tsum
    #   tsum     := tprod ('+' tprod)*
    #   tprod    := tatom ('x' tatom)*
    #   tatom    := '0' | '1' | IDENT | '(' typeexpr ')'
    #
    # `x` is the product operator, matching what `show_type` prints, so it is not
    # available as a variable name.  `mu` extends as far right as it can.

    def typeexpr(self, scope: Dict[str, int]):
        if self.at("mu"):
            self.next()
            kind, name, ln = self.next()
            if kind != "ident":
                raise ParseError(f"line {ln}: expected a name after 'mu'")
            if name == "x":
                raise ParseError(f"line {ln}: 'x' is the product operator in a "
                                 f"type and cannot name a variable")
            self.expect(".")
            i = self._fresh_tvar()
            return TMu(i, self.typeexpr({**scope, name: i}))
        return self.tsum(scope)

    def tsum(self, scope):
        node = self.tprod(scope)
        while self.at("+"):
            self.next()
            node = TSum(node, self.tprod(scope))
        return node

    def tprod(self, scope):
        node = self.tatom(scope)
        while self.at("x"):
            self.next()
            node = TProd(node, self.tatom(scope))
        return node

    def tatom(self, scope):
        kind, text, ln = self.peek()
        if text == "(":
            self.next()
            node = self.typeexpr(scope)
            self.expect(")")
            return node
        self.next()
        if kind == "num" and text in ("0", "1"):
            return TZero() if text == "0" else TOne()
        if kind == "ident":
            if text not in scope:
                raise ParseError(
                    f"line {ln}: '{text}' is not bound in this type -- every name "
                    f"must be a parameter of the declaration or bound by a 'mu'"
                )
            return TVar(scope[text])
        raise ParseError(f"line {ln}: expected a type, found {text or 'end of input'!r}")

    def _fresh_tvar(self) -> int:
        self._tvar += 1
        return self._tvar

    # -- values ------------------------------------------------------------

    def value(self) -> Value:
        kind, text, ln = self.next()
        if text == "L":
            return Inl(self.value())
        if text == "R":
            return Inr(self.value())
        if text == "(":
            if self.at(")"):
                self.next()
                return UNIT
            first = self.value()
            if self.at(","):
                self.next()
                second = self.value()
                self.expect(")")
                return Pair(first, second)
            self.expect(")")
            return first
        if text == "[":
            items = []
            if not self.at("]"):
                items.append(self.value())
                while self.at(","):
                    self.next()
                    items.append(self.value())
            self.expect("]")
            return from_list(items)
        if kind == "string":
            return from_string(_unescape(text[1:-1], ln))
        if kind == "char":
            s = _unescape(text[1:-1], ln)
            if len(s.encode("utf-8")) != 1:
                raise ParseError(
                    f"line {ln}: {text} is not one byte; a character is a byte, "
                    f"so write it as a string"
                )
            return from_byte(s.encode("utf-8")[0])
        if kind == "num":
            return from_nat(int(text))
        raise ParseError(f"line {ln}: expected a value, found {text or 'end of input'!r}")


# ---------------------------------------------------------------------------
# Encodings.  Nats are  mu X. 1 + X;  lists are  mu X. 1 + (A x X).
# ---------------------------------------------------------------------------


def from_nat(n: int) -> Value:
    v: Value = Inl(UNIT)
    for _ in range(n):
        v = Inr(v)
    return v


def as_nat(v: Value):
    n = 0
    while isinstance(v, Inr):
        v = v.v
        n += 1
    return n if v == Inl(UNIT) else None


def from_list(items) -> Value:
    v: Value = Inl(UNIT)
    for x in reversed(items):
        v = Inr(Pair(x, v))
    return v


def as_list(v: Value, allow_empty: bool = False):
    """The items of a list, or None.

    An empty list is `Inl ()`, which is also the nat 0 and also `false`, so by
    default this refuses it rather than guessing.  A caller that knows the type
    is a list -- `show_as` -- passes `allow_empty` and gets `[]`.
    """
    items = []
    while isinstance(v, Inr) and isinstance(v.v, Pair):
        items.append(v.v.a)
        v = v.v.b
    if v != Inl(UNIT):
        return None
    return items if items or allow_empty else None


# ---------------------------------------------------------------------------
# Text.  A character is a byte: eight bits, most significant first, nested to
# the right --  (b7, (b6, (b5, (b4, (b3, (b2, (b1, b0))))))).  A bit is a
# boolean, so `L ()` and `R ()`.  A string is then just a list of bytes, which
# is why every list program already works on text.
#
# Binary rather than unary is not only faster: a byte is a nest of *pairs*
# while a number is a chain of *labels*, so the two can never be confused, and
# the printer never has to guess between "abc" and a list of numbers.
# ---------------------------------------------------------------------------

BITS = 8

FALSE: Value = Inl(UNIT)
TRUE: Value = Inr(UNIT)


def from_byte(n: int) -> Value:
    """Encode 0..255 as a right-nested tuple of eight bits, MSB first."""
    if not 0 <= n < 1 << BITS:
        raise ValueError(f"not a byte: {n}")
    v: Value = TRUE if n & 1 else FALSE
    for i in range(1, BITS):
        v = Pair(TRUE if (n >> i) & 1 else FALSE, v)
    return v


def _as_bit(v: Value):
    if v == FALSE:
        return 0
    if v == TRUE:
        return 1
    return None


def as_byte(v: Value):
    n = 0
    for _ in range(BITS - 1):
        if not isinstance(v, Pair):
            return None
        b = _as_bit(v.a)
        if b is None:
            return None
        n = (n << 1) | b
        v = v.b
    b = _as_bit(v)
    return None if b is None else (n << 1) | b


def from_string(s: str) -> Value:
    return from_list([from_byte(b) for b in s.encode("utf-8")])


def as_string(v: Value):
    items = as_list(v)
    if not items:
        return None
    out = bytearray()
    for item in items:
        b = as_byte(item)
        if b is None:
            return None
        out.append(b)
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


_ESCAPE_OUT = {"\\": "\\\\", "\n": "\\n", "\t": "\\t", "\r": "\\r", "\0": "\\0"}
_ESCAPE_IN = {"\\": "\\", "n": "\n", "t": "\t", "r": "\r", "0": "\0",
              '"': '"', "'": "'"}


def _escape(s: str, quote: str) -> str:
    out = []
    for ch in s:
        if ch == quote:
            out.append("\\" + ch)
        elif ch in _ESCAPE_OUT:
            out.append(_ESCAPE_OUT[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return quote + "".join(out) + quote


def _unescape(body: str, line: int) -> str:
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= len(body):
            raise ParseError(f"line {line}: trailing backslash")
        nxt = body[i + 1]
        if nxt == "x":
            if i + 3 >= len(body):
                raise ParseError(f"line {line}: truncated \\x escape")
            try:
                out.append(chr(int(body[i + 2:i + 4], 16)))
            except ValueError:
                raise ParseError(f"line {line}: bad \\x escape") from None
            i += 4
            continue
        if nxt not in _ESCAPE_IN:
            raise ParseError(f"line {line}: unknown escape \\{nxt}")
        out.append(_ESCAPE_IN[nxt])
        i += 2
    return "".join(out)


# ---------------------------------------------------------------------------
# Printing.
# ---------------------------------------------------------------------------


def show(v: Value, raw: bool = False) -> str:
    if not raw:
        n = as_nat(v)
        if n is not None:
            return str(n)
        b = as_byte(v)
        if b is not None:
            return _escape(bytes([b]).decode("latin-1"), "'")
        s = as_string(v)
        if s is not None:
            return _escape(s, '"')
        items = as_list(v)
        if items is not None:
            return "[" + ", ".join(show(x, raw) for x in items) + "]"
    match v:
        case Unit():
            return "()"
        case Inl(x):
            return f"L {show(x, raw)}"
        case Inr(x):
            return f"R {show(x, raw)}"
        case Pair(a, b):
            return f"({show(a, raw)}, {show(b, raw)})"
    return repr(v)


# ---------------------------------------------------------------------------
# Type-directed printing.
#
# `show` has to guess, because the value universe is ambiguous: `Inl ()` is the
# nat 0, and the empty list, and `false`, and it cannot be all three on the
# page.  `show` picks 0.  Given a type there is nothing to guess, which is what
# the README meant by "resolving it requires types, not a better `show`".
#
# The rule is conservative on purpose: **override only where the type positively
# identifies an encoding.**  Most inferred types are more general than the one
# the programmer had in mind -- `succ = inr` gets `a <-> b + a`, not
# `nat <-> nat`, because `inr` really is that polymorphic -- and printing
# `succ 3` as `R 3` because the type failed to say "nat" would be a regression
# dressed up as rigour.  So a sum that is not recognisably a nat, list or bit
# falls back to the old heuristics wholesale, while products are descended
# through, since that is how a `[]` nested inside a pair gets reached.
# ---------------------------------------------------------------------------

_BIT_TYPE = TSum(TOne(), TOne())


# Recognising "is this a list?" cannot be done by matching syntax, because
# equirecursive types have no canonical form: `append`'s second argument arrives
# as `b + (mu Y. a x (b + Y))`, the same infinite tree as `mu X. b + (a x X)` but
# with the binder in a different place, and no single unfolding relates them.
# Unification already decides exactly this question, so ask it.  A failure is an
# answer, not an error -- hence the broad except, since a printer must never be
# the thing that crashes.


def _nat_like(t) -> bool:
    inf = Inference()
    x = inf.fresh()
    try:
        inf.unify(t, TMu(x.id, TSum(TOne(), TVar(x.id))), "printing")
    except (Rel42Error, RecursionError):
        return False
    return True


def _list_like(t):
    """The element type if `t` is a list, in whatever presentation it arrived."""
    inf = Inference()
    x, base, elem = inf.fresh(), inf.fresh(), inf.fresh()
    try:
        inf.unify(t, TMu(x.id, TSum(base, TProd(elem, TVar(x.id)))), "printing")
    except (Rel42Error, RecursionError):
        return None
    return inf.apply(elem)


def _byte_type(t) -> bool:
    """Eight bits, right-nested -- the encoding in section 12 of the manual."""
    for _ in range(BITS - 1):
        if not (isinstance(t, TProd) and t.a == _BIT_TYPE):
            return False
        t = t.b
    return t == _BIT_TYPE


def show_as(v: Value, ty=None, raw: bool = False) -> str:
    """Render `v`, using `ty` to settle what the encoding ambiguities mean."""
    if raw or ty is None:
        return show(v, raw)
    t = refold(ty)  # `1 + (mu X. 1 + X)` and `mu X. 1 + X` should read alike

    if _nat_like(t):
        n = as_nat(v)
        if n is not None:
            return str(n)

    elem = _list_like(t)
    if elem is not None:
        s = as_string(v)
        if s is not None:
            return _escape(s, '"')
        items = as_list(v, allow_empty=True)
        if items is not None:
            if not items and _byte_type(elem):
                return '""'
            return "[" + ", ".join(show_as(x, elem, raw) for x in items) + "]"

    if t == _BIT_TYPE and isinstance(v, (Inl, Inr)) and v.v == UNIT:
        return f"{'L' if isinstance(v, Inl) else 'R'} ()"

    if isinstance(t, TProd) and isinstance(v, Pair):
        b = as_byte(v)
        if b is not None:
            return _escape(bytes([b]).decode("latin-1"), "'")
        return f"({show_as(v.a, t.a, raw)}, {show_as(v.b, t.b, raw)})"

    return show(v, raw)


_PREC = {Union: 0, Seq: 1, Sum: 2, Prod: 3, App: 4}


def show_term(t: Term, outer: int = 0) -> str:
    def wrap(inner: int, s: str) -> str:
        return f"({s})" if inner < outer else s

    match t:
        case Prim(n, i) | Ref(n, i) | Var(n, i):
            return n + ("!" if i else "")
        case Star(s):
            return show_term(s, 5) + "^"
        case App(f, a):
            return wrap(4, f"{show_term(f, 4)} {show_term(a, 5)}")
        case Fun(param, b):
            # No surface syntax for a bare abstraction -- parameters are written
            # on the definition -- so this form is for display only.
            return wrap(0, f"fun {param} -> {show_term(b, 0)}")
        case Union(s, u):
            return wrap(0, f"{show_term(s, 0)} | {show_term(u, 1)}")
        case Seq(s, u):
            return wrap(1, f"{show_term(s, 1)} ; {show_term(u, 2)}")
        case Sum(s, u):
            return wrap(2, f"{show_term(s, 2)} + {show_term(u, 3)}")
        case Prod(s, u):
            return wrap(3, f"{show_term(s, 3)} * {show_term(u, 4)}")
    return repr(t)


# ---------------------------------------------------------------------------
# Entry points.
# ---------------------------------------------------------------------------


def parse_term(src: str, prims=None) -> Term:
    p = _Parser(lex(src), prims)
    t = p.term()
    if p.peek()[0] != "eof":
        raise ParseError(f"line {p.peek()[2]}: trailing input {p.peek()[1]!r}")
    return t


def parse_value(src: str, prims=None) -> Value:
    p = _Parser(lex(src), prims)
    v = p.value()
    if p.peek()[0] != "eof":
        raise ParseError(f"line {p.peek()[2]}: trailing input {p.peek()[1]!r}")
    return v


class Program(dict):
    """Definitions, plus any `type` abbreviations declared alongside them.

    A `dict` subclass so that every existing caller -- which only ever wanted the
    definitions -- keeps working unchanged.  `types` is consulted by the printer
    and by nothing else.
    """

    def __init__(self, defs=(), types=()):
        super().__init__(defs)
        self.types: List[Abbrev] = list(types)


def parse_program(src: str, prims=None) -> "Program":
    """Parse `def` bindings and `type` abbreviations into an environment."""
    p = _Parser(lex(src), prims)
    env: Dict[str, Term] = {}  # insertion-ordered, so source order is preserved
    types: List[Abbrev] = []
    while p.peek()[0] != "eof":
        if p.at("type"):
            p.next()
            kind, name, ln = p.next()
            if kind != "ident":
                raise ParseError(f"line {ln}: expected a name after 'type'")
            if any(a.name == name for a in types):
                raise ParseError(f"line {ln}: type '{name}' is already declared")
            scope: Dict[str, int] = {}
            order: List[int] = []
            while not p.at("="):
                kind, pname, pln = p.next()
                if kind != "ident":
                    raise ParseError(
                        f"line {pln}: expected a parameter name or '=', "
                        f"found {pname!r}"
                    )
                if pname == "x":
                    raise ParseError(
                        f"line {pln}: 'x' is the product operator in a type and "
                        f"cannot name a parameter"
                    )
                scope[pname] = p._fresh_tvar()
                order.append(scope[pname])
            p.expect("=")
            types.append(Abbrev(name, tuple(order), p.typeexpr(scope)))
            continue
        p.expect("def")
        kind, name, ln = p.next()
        if kind != "ident":
            raise ParseError(f"line {ln}: expected a name after 'def'")
        if name in p.prims:
            raise ParseError(f"line {ln}: '{name}' is a primitive and cannot be redefined")
        if name in env:
            raise ParseError(f"line {ln}: '{name}' is already defined")

        params: List[str] = []
        while not p.at("="):
            kind, text, pln = p.next()
            if kind != "ident":
                raise ParseError(
                    f"line {pln}: expected a parameter name or '=', found {text!r}"
                )
            if text in p.prims:
                raise ParseError(
                    f"line {pln}: '{text}' is a primitive and cannot be a parameter"
                )
            if text in params:
                raise ParseError(f"line {pln}: parameter '{text}' is repeated")
            params.append(text)
        p.expect("=")

        p.params = set(params)
        body = p.term()
        p.params = set()
        for name_ in reversed(params):
            body = Fun(name_, body)
        env[name] = body
    return Program(env, types)
