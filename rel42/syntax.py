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

Clause definitions (SUGAR.md), compiled to terms by `sugar`:

    clause := 'def' IDENT IDENT* datom '<->' dterm
    dterm  := 'let' dcons '=' dcons 'in' dterm | dcons
    dcons  := dplus (':' dcons)?        -- x : xs,  right-associative
    dplus  := dapp ('+' NUM)*           -- n + 1
    dapp   := 'L' datom | 'R' datom | head datom | datom
    head   := IDENT postfix* post^arity | '(' term ')' postfix*
    datom  := VAR | '(' ')' | '(' dcons ',' dcons ')' | '(' dcons ')'
            | NUM | CHAR | STRING | '[' dcons,* ']'

An identifier in a data term is a variable exactly when it does not name a
definition, a parameter or a primitive.  That needs every definition's name
before parsing starts, so `parse_program` reads the headers first.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from . import sugar as S
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
    | (?P<op><->|[;|+*!^(),\[\]=.:])
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
        # Every definition in the file, with its number of parameters: what tells
        # a call from a data variable inside a clause.
        self.arity: Dict[str, int] = {}

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

    # -- data terms (clause definitions) -------------------------------------
    #
    # `pattern` is True while parsing the left of `<->` or of a `let`'s `=`; it
    # only changes which error message a misplaced definition name gets.

    _KEYWORDS = {"let", "in", "def", "L", "R"}

    def _is_head(self, name: str) -> bool:
        return name in self.arity or name in self.params or name in self.prims

    def _starts_datom(self) -> bool:
        kind, text, _ = self.peek()
        if text in ("(", "["):
            return True
        if kind in ("num", "char", "string"):
            return True
        return kind == "ident" and text not in self._KEYWORDS

    def _after_parens(self) -> int:
        """Index of the token after the bracket group starting at the cursor."""
        depth, j = 0, self.i
        while True:
            _, text, _ = self.toks[j]
            if text in ("(", "["):
                depth += 1
            elif text in (")", "]"):
                depth -= 1
                if depth == 0:
                    return j + 1
            elif self.toks[j][0] == "eof":
                return j
            j += 1

    def dterm(self, pattern: bool = False):
        if self.at("let"):
            _, _, ln = self.next()
            q = self.dcons(True)
            self.expect("=")
            rhs = self.dcons(False)
            self.expect("in")
            return S.DLet(q, rhs, self.dterm(pattern), ln)
        return self.dcons(pattern)

    def dcons(self, pattern: bool):
        head = self.dplus(pattern)
        if self.at(":"):
            self.next()
            return S.DInr(S.DPair(head, self.dcons(pattern)), ":")
        return head

    def dplus(self, pattern: bool):
        node = self.dapp(pattern)
        while self.at("+") and self.toks[self.i + 1][0] == "num":
            self.next()
            for _ in range(int(self.next()[1])):
                node = S.DInr(node, "+")
        return node

    def dapp(self, pattern: bool):
        kind, text, ln = self.peek()
        if kind == "ident" and text in ("L", "R"):
            self.next()
            arg = self.datom(pattern)
            return S.DInl(arg) if text == "L" else S.DInr(arg)
        if kind == "ident" and self._is_head(text):
            head = self.post()
            for _ in range(self.arity.get(text, 0)):
                head = App(head, self.post())
            if not self._starts_datom():
                raise self._name_clash(text, ln, pattern)
            return S.DApp(head, self.datom(pattern))
        if text == "(":
            # A bracket group directly followed by a data term can only be a
            # program applied to it: data terms are never juxtaposed otherwise.
            saved = self.i
            self.i = self._after_parens()
            while self.at("!"):
                self.next()
            is_call = self._starts_datom()
            self.i = saved
            if is_call:
                self.next()
                head = self.term()
                self.expect(")")
                while self.at("!"):
                    self.next()
                    head = dagger(head)
                return S.DApp(head, self.datom(pattern))
        return self.datom(pattern)

    def _name_clash(self, name: str, ln: int, pattern: bool) -> ParseError:
        what = (
            "a parameter" if name in self.params
            else "a primitive" if name in self.prims
            else "a definition"
        )
        if pattern:
            return ParseError(
                f"line {ln}: the pattern variable `{name}` has the name of {what}.  "
                f"In a pattern, `{name} t` runs `{name}` backwards, so a variable "
                f"may not reuse the name.  Rename the variable."
            )
        return ParseError(
            f"line {ln}: `{name}` is {what}, so here it must be applied to an "
            f"argument: `{name} t`.  A variable may not reuse the name."
        )

    def datom(self, pattern: bool):
        kind, text, ln = self.next()
        if text == "(":
            if self.at(")"):
                self.next()
                return S.DConst(UNIT, "()")
            first = self.dcons(pattern)
            if self.at(","):
                self.next()
                second = self.dcons(pattern)
                self.expect(")")
                return S.DPair(first, second)
            self.expect(")")
            return first
        if text == "[":
            items = []
            if not self.at("]"):
                items.append(self.dcons(pattern))
                while self.at(","):
                    self.next()
                    items.append(self.dcons(pattern))
            self.expect("]")
            node = S.DConst(Inl(UNIT), "[]")
            for item in reversed(items):
                node = S.DInr(S.DPair(item, node), "[")
            return node
        if kind in ("num", "char", "string"):
            self.i -= 1
            return S.DConst(self.value(), text)
        if kind == "ident" and text not in self._KEYWORDS:
            if self._is_head(text):
                raise self._name_clash(text, ln, pattern)
            return S.DVar(text, ln)
        raise ParseError(f"line {ln}: expected a data term, found {text or 'end of input'!r}")


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

    def __init__(self, defs=(), types=(), clauses=None, warnings=()):
        super().__init__(defs)
        self.types: List[Abbrev] = list(types)
        # Clause definitions as written, name -> (params, clauses), for `show`;
        # and what the compiler warned about.  Neither affects meaning.
        self.clauses: Dict[str, Tuple[List[str], List[S.Clause]]] = dict(clauses or {})
        self.warnings: List[str] = list(warnings)


def _header(toks, i: int):
    """Read a `def` header whose name is at `toks[i]`, without consuming it.

    Returns (separator, sep_index, params, pattern_index): the separator is `=`
    for a point-free definition and `<->` for a clause, whose pattern is the
    single bracket group or token just before it.  Everything between the name
    and the pattern is a parameter.
    """
    depth, j = 0, i + 1
    while True:
        kind, text, ln = toks[j]
        if kind == "eof" or (depth == 0 and text == "def" and kind == "ident"):
            raise ParseError(f"line {ln}: expected '=' or '<->' in the definition "
                             f"of '{toks[i][1]}'")
        if depth == 0 and text in ("=", "<->"):
            break
        if text in ("(", "["):
            depth += 1
        elif text in (")", "]"):
            depth -= 1
        j += 1
    if text == "=":
        return "=", j, [t for _, t, _ in toks[i + 1:j]], None
    k = j - 1
    if toks[k][1] in (")", "]"):
        depth = 0
        while True:
            t = toks[k][1]
            if t in (")", "]"):
                depth += 1
            elif t in ("(", "["):
                depth -= 1
                if depth == 0:
                    break
            k -= 1
    if k <= i:
        raise ParseError(f"line {toks[j][2]}: a clause of '{toks[i][1]}' needs a "
                         f"pattern before '<->'")
    for kind, text, ln in toks[i + 1:k]:
        if kind != "ident":
            raise ParseError(
                f"line {ln}: a clause's pattern must be a single term just before "
                f"'<->'; put brackets round it"
            )
    return "<->", j, [t for _, t, _ in toks[i + 1:k]], k


def _source(toks) -> str:
    """Tokens back to readable text, for quoting a clause in a message."""
    out = ""
    for _, text, _ in toks:
        if out and not (out.endswith(("(", "[")) or text in (")", "]", ",", "!")):
            out += " "
        out += text
    return out


def parse_program(src: str, prims=None, clause_rules=None) -> "Program":
    """Parse `def` bindings and `type` abbreviations into an environment.

    `clause_rules` is how a sibling language over the same grammar -- Q42 --
    adds its own discipline to clause definitions (QSUGAR.md): its `check` sees
    each definition's clauses before they are compiled, and its `accept` sees
    the compiled term.  With rules in place, 42's own overlap warnings and its
    dropping of dead unit checks are left out: the rules decide overlap, and a
    unit check costs nothing where every value of `1` is `()`.
    """
    toks = lex(src)
    p = _Parser(toks, prims)
    for i, (kind, text, _) in enumerate(toks[:-1]):
        if kind == "ident" and text == "def" and toks[i + 1][0] == "ident":
            _, _, params, _ = _header(toks, i + 1)
            p.arity[toks[i + 1][1]] = len(params)
    env: Dict[str, Term] = {}  # insertion-ordered, so source order is preserved
    types: List[Abbrev] = []
    clauses: Dict[str, Tuple[List[str], List[S.Clause]]] = {}
    last = None  # the previous definition's name: clauses must be contiguous
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
            last = None
            continue
        p.expect("def")
        kind, name, ln = p.next()
        if kind != "ident":
            raise ParseError(f"line {ln}: expected a name after 'def'")
        if name in p.prims:
            raise ParseError(f"line {ln}: '{name}' is a primitive and cannot be redefined")
        if name in ("L", "R", "let", "in"):
            raise ParseError(f"line {ln}: '{name}' is reserved and cannot name a definition")

        sep, j, params, k = _header(toks, p.i - 1)
        if sep == "<->":
            if name in env and name not in clauses:
                raise ParseError(f"line {ln}: '{name}' is already defined")
            if name in clauses:
                if last != name:
                    raise ParseError(
                        f"line {ln}: the clauses of '{name}' must be written together; "
                        f"another definition comes between them"
                    )
                if clauses[name][0] != params:
                    raise ParseError(
                        f"line {ln}: every clause of '{name}' must have the same "
                        f"parameters ({' '.join(clauses[name][0]) or 'none'})"
                    )
            for pname in params:
                if pname in p.prims or pname in p.arity:
                    raise ParseError(
                        f"line {ln}: '{pname}' names a primitive or a definition "
                        f"and cannot be a parameter"
                    )
            p.i = k
            p.params = set(params)
            start = k
            pat = p.datom(True)
            if p.i != j:
                raise ParseError(f"line {ln}: a clause's pattern must be a single "
                                 f"term just before '<->'; put brackets round it")
            p.expect("<->")
            body = p.dterm()
            p.params = set()
            text = f"{name} {_source(toks[start:p.i])}"
            clauses.setdefault(name, (params, []))[1].append(S.Clause(pat, body, ln, text))
            env[name] = None  # placeholder, so source order is kept
            last = name
            continue
        if name in env:
            raise ParseError(f"line {ln}: '{name}' is already defined")
        last = name

        params = []
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
    warnings: List[str] = []
    unchecked: Dict[str, Term] = {}
    for name, (params, group) in clauses.items():
        if clause_rules is not None:
            clause_rules.check(name, params, group)
            env[name] = S.compile_clauses(params, group)
            clause_rules.accept(name, env[name], group)
            continue
        env[name] = S.compile_clauses(params, group)
        unchecked[name] = S.compile_clauses(params, group, units=False)
        for i, j, witness in S.overlaps(group):
            warnings.append(
                f"line {group[j].line}: clauses {i + 1} and {j + 1} of '{name}' both "
                f"match {show_witness(witness)}:\n"
                f"    def {group[i].text}\n"
                f"    def {group[j].text}\n"
                f"42 takes the union of matching clauses, not the first match, so "
                f"both give answers there.  If that is meant, give each its own "
                f"name and write the union: `def {name} = ... | ...`."
            )
    if unchecked:
        S.drop_dead_checks(env, unchecked)
    return Program(env, types, clauses, warnings)


def show_witness(tree) -> str:
    """A value two patterns share, `_` where anything will do."""
    v = S.tree_value(tree)
    if v == Inl(UNIT):
        return "`0` (which is also `[]` and `false`)"
    return f"`{_witness(tree)}`"


def _witness(tree) -> str:
    if tree == S.WILD:
        return "_"
    v = S.tree_value(tree)
    if v is not None:
        return show(v)
    if tree[0] == "P":
        return f"({_witness(tree[1])}, {_witness(tree[2])})"
    if tree[0] == "R" and isinstance(tree[1], tuple) and tree[1][:1] == ("P",):
        return f"{_witness(tree[1][1])} : {_witness(tree[1][2])}"
    if tree[0] == "R":
        k = 0
        while isinstance(tree, tuple) and tree[:1] == ("R",):
            k, tree = k + 1, tree[1]
        return f"{_witness(tree)} + {k}"
    inner = _witness(tree[1])
    return f"L {inner}" if " " not in inner or inner.startswith(("(", "[")) else f"L ({inner})"


# ---------------------------------------------------------------------------
# Printing data terms, for `show`.
# ---------------------------------------------------------------------------


def show_clause(name: str, params: List[str], c: "S.Clause") -> str:
    head = " ".join([name, *params, _dt(c.pattern, 3)])
    return f"{head} <-> {_dt(c.body, 0)}"


def _dt(t, outer: int = 0) -> str:
    """Levels: 0 let, 1 cons, 2 plus/application, 3 atom."""
    def wrap(level: int, s: str) -> str:
        return f"({s})" if level < outer else s

    match t:
        case S.DVar(name):
            return name
        case S.DConst(v, text):
            return text or show(v)
        case S.DPair(a, b):
            return f"({_dt(a)}, {_dt(b)})"
        case S.DLet(q, r, e):
            return wrap(0, f"let {_dt(q, 1)} = {_dt(r, 1)} in {_dt(e, 0)}")
        case S.DInl(x):
            return wrap(2, f"L {_dt(x, 3)}")
        case S.DApp(head, x):
            return wrap(2, f"{show_term(head, 4)} {_dt(x, 3)}")
        case S.DInr(S.DPair(a, b), "["):
            items, rest = [a], b
            while isinstance(rest, S.DInr) and rest.form == "[":
                items.append(rest.t.a)
                rest = rest.t.b
            return "[" + ", ".join(_dt(x) for x in items) + "]"
        case S.DInr(S.DPair(a, b), ":"):
            return wrap(1, f"{_dt(a, 2)} : {_dt(b, 1)}")
        case S.DInr(x, "+"):
            k = 1
            while isinstance(x, S.DInr) and x.form == "+":
                k, x = k + 1, x.t
            return wrap(2, f"{_dt(x, 2)} + {k}")
        case S.DInr(x):
            return wrap(2, f"R {_dt(x, 3)}")
    return repr(t)
