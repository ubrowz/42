# 42

A point-free reversible programming language, interpreted in **Rel** — the
category of sets and relations.

**The manuals are the way in:** [42](https://ubrowz.github.io/42/manual.html)
and [Q42](https://ubrowz.github.io/42/qmanual.html), with everything else at
[ubrowz.github.io/42](https://ubrowz.github.io/42/). This file is the design
note behind them, and assumes more mathematics than they do.

A program denotes a relation, and the defining law of the language is

```
x ∈ P(y)   ⟺   y ∈ inv(P)(x)
```

`inv` is the converse. Rel is a *dagger category*: `inv` is an
identity-on-objects, involutive, contravariant functor. Every rule in the
implementation is forced by that fact rather than chosen, which is the whole
point of the design.

```
$ 42 prelude add "(2, 3)"
add(2, 3) =
  5
  -- 1 result

$ 42 prelude add 5 --backward
add!(5) =
  (0, 5)
  (1, 4)
  (2, 3)
  (3, 2)
  (4, 1)
  (5, 0)
  -- 6 results
```

Forwards, `add` is a function. Backwards, it enumerates every preimage. Both
directions run the *same definition*; the backward one is its dagger, computed
mechanically.

The three words after `42` are a file, a program defined in it, and an input:
`prelude` is `prelude.42`, a file of worked examples that ships with the project,
and `add` is one of the definitions in it.

**New here? Start with [`MANUAL.md`](MANUAL.md)** — a ground-up user manual
that assumes no vocabulary beyond a CS background. This README describes the
*design* in mathematical terms and will be much easier after it.

## The dagger

The entire inversion algorithm, from `rel42/core.py`:

```python
def dagger(t: Term) -> Term:
    match t:
        case Prim(n, i):  return Prim(n, not i)
        case Ref(n, i):   return Ref(n, not i)
        case Seq(s, u):   return Seq(dagger(u), dagger(s))   # contravariant
        case Union(s, u): return Union(dagger(s), dagger(u))
        case Sum(s, u):   return Sum(dagger(s), dagger(u))
        case Prod(s, u):  return Prod(dagger(s), dagger(u))
        case Star(s):     return Star(dagger(s))
```

It is **total**: no side conditions, no well-formedness checks, no proof
obligations, no undecidable questions. `dagger(dagger(t)) == t` holds
syntactically, on the nose.

Compare Janus, which needs every conditional to carry an exit assertion
(`if b then … else … fi a`) so that backward execution can tell which branch
it came from. 42 needs no such thing, because nondeterministic choice is a
first-class construct: where Janus must *separate* two branches with a
predicate, 42 simply keeps both. **Dropping restrictions is what buys the
elegance here** — the more general setting has the simpler metatheory.

Because `dagger` is total, the surface syntax can eliminate `!` at parse time.
It never appears in the abstract syntax:

```
parse("(copy ; join)!")  ==  parse("join! ; copy!")
```

## Where 42 sits

Set size is the design dial, and it picks out three nested settings:

| Setting | `\|P(y)\|` | Law | In 42 |
|---|---|---|---|
| **Groupoid** (bijections) | exactly 1 | `S ; S† = id` | `not`, `swap`, `rot3` |
| **PInj** (partial injections) | ≤ 1 | `S ; S† ; S = S` | `succ`, `pred`, `double` |
| **Rel** (relations) | arbitrary | `S ⊆ S ; S† ; S` | `add`, `append` |

Be clear-eyed about the bottom row: **in Rel, running forward then backward
does not return you to where you started.** It returns a set *containing*
where you started. That is the price of the generality, and the `∈` in the
defining law is where it is paid.

Two illustrations the interpreter makes concrete:

- **Partiality is not failure.** `pred 0` is the empty set, because 0 has no
  predecessor. Being outside a relation's domain is not an error condition; it
  is simply having no image. A shape *mismatch* denotes the empty relation for
  the same reason — though the CLI now type-checks first and refuses it, since
  you almost never mean it.
- **Composition can restore determinism.** `add!` is many-valued, yet
  `double = copy ; add` has a single-valued dagger: `copy!` keeps only the
  pairs whose components agree, so `double! 6 = {3}` and `double! 7 = {}`.

## The language

```
program := (typedecl | 'def' IDENT IDENT* '=' term)*
typedecl := 'type' IDENT IDENT* '=' typeexpr
term := comp ('|' comp)*        -- nondeterministic choice (union)
comp := sum  (';' sum)*         -- composition, diagrammatic order
sum  := prod ('+' prod)*        -- the sum functor
prod := app  ('*' app)*         -- the product functor
app  := post+                   -- application, by juxtaposition
post := atom ('!' | '^')*       -- dagger, reflexive transitive closure
atom := '(' term ')' | IDENT
```

The extra identifiers after a definition's name are **parameters**, and they range
over *terms*, not values — 42 still has no binder over a value. That is enough to
write a combinator once:

```
def ctrl m = mat ; (id + m) ; mat!      -- (a <-> a) -> ((1+1) x a <-> (1+1) x a)
def cx     = ctrl swapsum
def ccx    = ctrl cx
```

Two conventions make this survive inversion, and they are a matched pair. A `!`
written on a parameter is recorded on the variable, so `dagger` flips it exactly
as it flips a reference; and `dagger` therefore leaves an application's *argument*
alone, `dagger(f a) = dagger(f) a`, letting substitution discharge the inversion
later. The result is that `dagger` commutes with reduction, so `ctrl! m` is
`ctrl m!` — in physics, `(Ctrl U)† = Ctrl U†`. `dagger` stays total, stays an
involution, and gains no side condition.

Applications are reduced away before evaluation, which is why neither evaluator
has a case for one. Deliberately second-order: a parameter denotes a relation,
never another combinator.

Primitives are the isomorphisms witnessing the commutative-semiring structure
of `0, 1, +, ×`, plus the two morphisms that make this Rel rather than a
groupoid:

| | |
|---|---|
| `id`, `zero` | identity, empty relation |
| `swapsum`, `assocsum`, `unitsum` | `a+b ↔ b+a`, `a+(b+c) ↔ (a+b)+c`, `0+a ↔ a` |
| `swapprod`, `assocprod`, `unitprod` | `a×b ↔ b×a`, `a×(b×c) ↔ (a×b)×c`, `1×a ↔ a` |
| `dist` | `(a+b)×c ↔ (a×c)+(b×c)` |
| `inl`, `inr` | injections — partial injections, not bijections |
| `copy` | the diagonal `a → a×a`; its converse is the partial "these agree" |
| `join` | the codiagonal `a+a → a`; **its converse is the only source of nondeterminism in the language** |

Everything with more than one answer traces back to `join!`. That is worth
knowing: ambiguity in 42 has exactly one origin.

Two primitives are deliberately absent:

- `absorb : 0×a ↔ 0` is omitted because `0×a` has no inhabitants, so it is
  extensionally just `zero`.
- `discard : a → 1` is omitted because its converse must generate *every*
  value of a type, which is not finitary.

The second omission constrains the *shape* of what you can write, but far less
than it first appears. `mul : (m, n) → m×n` is indeed not expressible, since
the base case `0 × n = 0` must discard `n`. But `mul : (m, n) → (n, m×n)` is,
and keeping the multiplier costs one component and buys injectivity — so
`mul!` is exact division. See `arith.42`, where `divexact`, `divmod` and `sub`
are all defined as inverses of the easy direction, with no algorithm written
for any of them.

## Values

Untyped at runtime. The universe is generated by `0, 1, +, ×`:

```
()              the inhabitant of 1
L v   R v       injections
(a, b)          pairs
3               sugar for the Peano nat over  μX. 1 + X
[1, 2, 3]       sugar for the list over  μX. 1 + (A × X)
```

Note that `0`, `[]` and `L ()` are **the same value** — both recursive types
use `Inl ()` as their base constructor and the interpreter is untyped. The
printer picks `0`. This is a genuine consequence of an untyped Rel, not a
printing bug; resolving it requires types, not a better `show`.

So `run` and `law` print against the type they inferred, and get it right:

```
$ 42 prelude append "[1,2,3]" --backward
append!([1, 2, 3]) =
  ([], [1, 2, 3])
  ([1], [2, 3])
  ([1, 2], [3])
  ([1, 2, 3], [])
```

The rule is conservative: it overrides only where the type *positively*
identifies an encoding, and recognising one has to be done by unification rather
than by matching syntax, since a list can arrive as `μX. b + (a × X)` or as
`b + (μY. a × (b + Y))`. Where the inferred type is more general than the one you
meant — `succ = inr` gets `a <-> b + a`, which never says "nat" — the old
guessing stands, because printing `succ 3` as `R 3` would be a regression
dressed up as rigour.

## Types

A term denotes a relation, so its type has two sides: `t : A ↔ B` means
`⟦t⟧ ⊆ A × B`. Types are the trees over the same four things the values are —
`0`, `1`, `+`, `×` — plus variables, because the plumbing is polymorphic, plus
`μX. F(X)` for the recursive ones. The primitive schemes are therefore just the
semiring axioms read as types, which is what the primitives were chosen to be.

**All 263 definitions in the ten libraries typecheck**, with no annotation added
to any of them. Types are inferred, never written: nothing in the surface syntax
mentions one, and there is no `fold`/`unfold`.

```
$ 42 type prelude
not       : a + b <-> b + a
rot3      : a x (b x c) <-> c x (a x b)
succ      : a <-> b + a
pred      : a + b <-> b
add       : nat x (mu Y. a + Y) <-> mu Y. a + Y
double    : nat <-> nat
downfrom  : mu X. a + X <-> mu X. a + X
```

(`nat` is an abbreviation the file declares; see below. `add`'s second argument is
*not* `nat` — its zero case carries an unconstrained `a`, because `inr` is
polymorphic — and the printer is right not to pretend otherwise.)

Recursion is **equirecursive**: `μX. F(X)` and `F(μX. F(X))` are silently the
same type. A `μ` is never something the programmer reaches for — it is what the
checker infers when unification closes a loop. `nat` is not declared anywhere;
`double = copy ; add` comes out as `μX. 1 + X ↔ μY. 1 + Y` because `copy` forces
`add`'s two summands to agree, and that *is* `nat ↔ nat`.

Four things fall out rather than being decided:

- **Inversion swaps the two sides, and does nothing else.** `dagger` is
  identity-on-objects and contravariant, so at the level of shapes it can only
  exchange domain and codomain. Inference implements `!` by swapping a scheme,
  so `t : A ↔ B ⟹ t! : B ↔ A` holds by construction — the type-level shadow of
  the defining law, checked over all 263 definitions.
- **Generalisation is nearly trivial, because 42 has almost no binders.** Every
  definition is a closed term, so there is no environment of monomorphic
  assumptions to avoid capturing and none of the usual machinery (levels, ranks,
  the value restriction) is needed. The one exception is a mutually recursive
  group — `cipher.42`'s `cbc`/`cbcstep` — which is solved as a unit against
  monomorphic assumptions and generalised once, Milner-style.
- **A cycle in unification *is* the recursive type.** Where a finite-tree checker
  runs an occurs check and gives up, this one binds the variable to a term
  containing itself and carries on. Unification then works up to unfolding,
  coinductively: assume the two sides equal and check the assumption survives a
  layer. The set of assumptions is what makes it terminate.
- **But a cycle is still read before it is trusted.** `b = a + b` is `μX. a + X`,
  a list, which has finite values. `a = a × a` is `μX. X × X`, which has none —
  and `copy^` is how you write it. One unfolding with the variable taken empty
  settles which: `μX. F(X)` has a finite value exactly when `F(0)` does, and if
  `F(0)` is empty then so is `F(F(0))`.

What the types say is sharper than it looks. `cipher.42`'s `cnot1` comes out as
`(a + b) × (c + c) ↔ (a + b) × (c + c)`, and that repeated `c` is the type-level
content of "the second argument is a bit" — the summands forced equal by the fact
that the program negates it.

One wrinkle is inherent to the choice: equirecursive types have no unique
syntactic form. `μX. b + (a + X)` and `μY. a + (b + Y)` are the same infinite
tree, and telling them apart properly means minimising a regular tree. The
printer collapses the common case — anything that is literally one unfolding of a
`μ` inside it — and leaves the rest, so a type may read wordier than necessary
but never wrongly.

### Abbreviations

`μX. 1 + X` is correct and unreadable. A file may name the types it is about:

```
type nat    = mu X. 1 + X
type list a = mu X. 1 + (a x X)
```

```
double : nat <-> nat                    -- was  mu X. 1 + X <-> mu Y. 1 + Y
rev    : list a <-> list a              -- was  mu X. 1 + a x X <-> mu Y. 1 + a x Y
ctrl   : (a <-> a) -> (qubit x a <-> qubit x a)
```

This is a **display layer and nothing else**: no new primitives, no new
semantics, and every program typechecks identically whether or not a single
abbreviation is declared — which is asserted in the tests.

Matching has to be up to equirecursive equality, since the same infinite tree has
many presentations, so it reuses the unifier — but *one-way*. An abbreviation may
describe the type it is offered and may never constrain it; otherwise
`type nat = mu X. 1 + X` would match every type variable and everything would
print as `nat`. Declarations are tried in source order, first match winning, so
put the specific ones first.

`x` is the product operator in a type, so it cannot name a variable. The printer
therefore never generates it either — which incidentally fixed a latent
ambiguity, since `cipher.42` has a definition with 27 type variables and used to
print `(x + x) x (a + b)`.

## Usage

```
42      FILE MAIN VALUE [--backward]   apply a definition
42 law  FILE MAIN VALUE                check the defining law
42 show FILE [MAIN]                    print each def and its dagger
42 type FILE [MAIN]                    infer  A <-> B  for each def
42 quote FILE MAIN [VALUE]             run it through meta.42, the 42
                                       interpreter written in 42

42q     FILE MAIN STATE [--backward]   the same for Q42, over C
42q sample  FILE MAIN STATE            ...and measure the result
42q emit    FILE [MAIN]                write it out as OpenQASM 3
42q unitary|matrix|law|type|show FILE [MAIN]
```

`42` and `42q` are shell wrappers for `python3 -m rel42` and `python3 -m q42`,
which keep working unchanged. Each assumes `run` when the first word is not a
subcommand, makes the `.42` extension optional, and finds files beside itself, so

```
42 prelude append "([1,2], [3])"
```

means `python3 -m rel42 run prelude.42 append "([1,2], [3])"`.

They live in the repository root. Put it on your `PATH` to use them by name:

```sh
export PATH="/path/to/42:$PATH"     # in ~/.zshrc, ~/.bashrc, …
```

Or run them in place as `./42` and `./42q`, which needs no setup. (`42q` is
spelled that way round because a file cannot share a name with the `q42/`
package directory beside it.)

`law` is the one that matters for the theory — it computes `P(x)`, then for
each result `y` checks that `x ∈ inv(P)(y)`:

```
$ 42 law prelude append "([1,2], [3])"
append([1, 2], [3]) has 1 result(s)
  [ok ] [1, 2, 3]: inv has 4 preimage(s), input in it
law holds
```

Flags: `--raw` disables nat/list sugar, `--limit` bounds call depth, `--orbit`
bounds how large a `Star` closure may grow before being declared infinite, and
`--untyped` skips the type check that `run` and `law` otherwise apply.

Tests: `python3 tests/test_rel42.py` (132), `python3 tests/test_types.py` (125),
`python3 tests/test_q42.py` (103), `python3 tests/test_docs.py` (32) and
`python3 tests/test_emit.py` (27) — 419 in all. Stdlib only, no dependencies, and `test_docs.py` checks the documentation
itself, including these counts.

## Q42 — the same language over ℂ

Rel is matrices over the Boolean semiring. Swap the semiring for ℂ and you get
finite-dimensional Hilbert spaces and unitary maps, which is quantum computing.
That is `q42/`, and [`Q42.md`](Q42.md) is its design.

```
$ 42q gates ghz "|000>"
ghz |000>
  = 0.707107|000>  +  0.707107|111>

$ 42q unitary gates
-- 24/26 unitary, 2 with no single matrix
```

**[`QMANUAL.md`](QMANUAL.md) is its user manual** — the physics developed from
scratch for a computer scientist, and the parts Q42 does not model named as such.

It is a sibling, not a fork: `Value`, `Term`, `dagger`, the parser and the
type-inference engine are all rel42's, unchanged — `q42.dagger is rel42.dagger`.
Only the primitive table and the evaluator differ. Two departures are worth
knowing, and both are forced rather than chosen:

- **`|` and `^` are gone**, because they are exactly the two constructors whose
  meaning needs addition to be *idempotent*: `f | f` would denote `2f`, and
  `Star` is a least fixed point wanting `1 + 1 = 1`. Superposition comes from the
  new generator `v`, not from choice.
- **`copy`, `join`, `inl`, `inr` and `zero` are gone**, because none is unitary.
  `copy` is the interesting one: it is a perfectly good isometry that copies
  basis states, so it is a measurement basis rather than an illegal cloner — it
  is excluded only for not being surjective.

What is added is two generators, `omega` and `v`, an 8th root of unity and a
square root of `swapsum`. That is enough for universal quantum computation
(Carette, Heunen, Kaarsgaard & Sabry, POPL 2024), and `dagger` needs no change at
all — it stops being the converse and becomes the adjoint, and because every Q42
term is unitary, `t ; t!` is now `id` on the nose rather than a set containing
where you started.

## Honest limitations

- **A relation can be computable in one direction and not the other.**
  `downfrom = pred^` saturates at zero; its dagger `succ^` is the infinite set
  of all larger numbers. The interpreter reports non-saturation rather than
  hanging, but it cannot *decide* which case it is in — it gives up on a
  budget.
- **`Star` is computed by naive saturation**, so it only terminates when the
  orbit is finite.
- **The checker gates the CLI, not the library.** `run` and `law` reject an
  ill-typed definition, and reject an argument outside the domain, with
  `--untyped` to override. `core.run` is deliberately left untyped: in Rel the
  empty relation is a real morphism, so a shape mismatch genuinely *denotes*
  nothing, and the library should keep saying so. Only the CLI adds the
  judgement that you probably did not mean it.
- **Inferred types are not canonical.** Equirecursive types have no unique
  syntactic form, and producing one means minimising a regular tree. `show_type`
  collapses one-step unfoldings and no more, so `append`'s second argument
  *reads* `b + (μY. a × (b + Y))` where a minimised form would be shorter.
  Correct, not tidy. It costs nothing beyond legibility: the value printer asks
  unification rather than matching syntax, so it recognises that type as a list
  regardless.
- **Recursion is monomorphic.** A definition is typed at one type inside its own
  group, Milner-style. Polymorphic recursion is undecidable in general and
  nothing in the libraries wants it, but a program that did would be rejected.
- **Backward runs can be exponential.** Nothing here prunes the search.

## Layout

```
42, 42q           shorthand for `python3 -m rel42` / `python3 -m q42`
rel42/core.py     values, terms, the dagger, primitives, the evaluator
rel42/syntax.py   lexer, parser, pretty-printer (type-directed when given a type)
rel42/types.py    types, equirecursive unification, inference
rel42/meta.py     the encoding meta.42 reads: 42 programs and values, as values
rel42/__main__.py CLI
MANUAL.md         user manual -- start here
QMANUAL.md        user manual for Q42, the version over C
tour.42           the manual's ground, in runnable form
arith.42          arithmetic: + and * written, / and - inverted
rational.42       exact rationals; why `reduce` cannot exist
strings.42        text: bytes as bit-tuples; every list program works on it
cipher.42         a Feistel cipher in CBC mode; `decrypt = cbc!` is the whole decryptor
tm.42             a Turing machine as `init ; step^ ; final` (MANUAL section 13)
theorem.42        the constructions THEOREM.md's proof is assembled from
meta.42           the core of 42, interpreted by a 42 program (THEOREM.md §7,
                  MANUAL §14).  `42 quote arith mul "(3, 4)"`
qft.42            a Q42 circuit family, generated -- 42 as the host Q42 lacks
prelude.42        worked examples
tests/            419 tests, including the defining law checked exhaustively,
                  every output claimed in tour.42, that all 263 library
                  definitions typecheck, and that results land in the codomain
                  the checker predicted
q42/emit.py       a term to gates on numbered qubits, and to OpenQASM 3
q42/exact.py      amplitudes as elements of Z[1/sqrt2, i] rather than as
                  doubles, so that equality of two terms is decided
q42/              Q42 -- the same language over C instead of the Booleans.
                  Shares Value, Term, dagger, the parser and the type engine
                  with rel42; forks the primitive table and the evaluator.
                  `42q unitary gates`.  gates.42 is the gate set; fib.42,
                  deutsch.42, grover.42, gsum.42 and teleport.42 are worked
                  examples;
                  classical.42 is the one that runs under either interpreter.
Q42.md            the design, and why each departure from 42 is forced
RELATED.md        where 42 sits in the literature, and what in it is new
THEOREM.md        the proof that 42 denotes exactly the r.e. relations
DRAFT.md          the 15-page conference draft, basis for the journal version
DRAFT-Q42.md      the Q42 draft for RC 2027
paper/            the same draft as Springer LNCS LaTeX, with refs.bib
sources/          README only: the papers RELATED.md quotes are third-party PDFs
                  and are not redistributed here.  Drop them in to enable the
                  quotation test, which skips itself when they are absent
spike/            throwaway experiments, superseded by q42/ but kept as the
                  evidence Q42.md was written from
tools/selfinterp.py  meta.42 interpreting meta.42; THEOREM.md 7.5's numbers
tools/render.py   renders the manuals into docs/*.html
tools/unquote.py  turns a generated circuit value into Q42 source text
tools/qasm_sim.py an independent simulator over gate lists, sharing no code
                  with the evaluator, so the emitter can be round-tripped
                  against something that could not agree by construction
tools/checkmanual.py  re-runs every result MANUAL.md claims
docs/             the site, served by GitHub Pages: a landing page, the two
                  manuals, RELATED.md and THEOREM.md, rendered for a browser.
                  Generated -- rerun tools/render.py and commit the result
plain/            the two papers retold for a reader with no mathematics, using a
                  warehouse instead of algebra; hand-written HTML, not generated,
                  with four stepped demonstrations.  Hand-edited, so render.py
                  neither writes nor overwrites them
```
