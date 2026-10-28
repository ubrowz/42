# 42 with Names — a design note on pointful syntax

*Design note, 2026-10-28. Implemented in `rel42/sugar.py`, with the parser
changes in `rel42/syntax.py`; §11 describes what exists and what building it
turned up. Every example here compiles and runs, and `tests/test_sugar.py`
checks them. `spike/sugar.42` keeps the hand-desugared versions written before
the compiler existed, as a reference. Where this note says "checked", a test
does it.*

*Decided 2026-10-28: the clause arrow is `<->` (§2); a pattern variable may not
share a name with a definition (§2, "Names"); overlapping input patterns warn,
and an intended overlap is written as `f = g | h` (§6, "Overlap warns").*

## Contents

1. [The problem, and the part of it this note does not touch](#1-the-problem-and-the-part-of-it-this-note-does-not-touch)
2. [The notation, by example](#2-the-notation-by-example)
3. [How one clause compiles](#3-how-one-clause-compiles)
4. [The use-count rule](#4-the-use-count-rule)
5. [Inversion is turning the arrows around](#5-inversion-is-turning-the-arrows-around)
6. [Several clauses: a union, then a case tree](#6-several-clauses-a-union-then-a-case-tree)
7. [`let`: a clause in the middle](#7-let-a-clause-in-the-middle)
8. [Same relation, different search](#8-same-relation-different-search)
9. [Q42: the same notation under Theseus's rule](#9-q42-the-same-notation-under-theseuss-rule)
10. [Precedents, and what is particular here](#10-precedents-and-what-is-particular-here)
11. [Where it lives, and what building it found](#11-where-it-lives-and-what-building-it-found)
12. [Open questions](#12-open-questions)

---

## 1. The problem, and the part of it this note does not touch

Writing 42 is hard in two different ways.

**Plumbing.** There are no names, so values are routed by hand with
`swapprod`, `assocprod`, `unitprod!` and `dist`. `single` is four steps of
moving parentheses to say `[x]`. This difficulty is *accidental*. The manual's
§16 already says how to write a program: "Step 1 — write it with names, as an
equation", then peel the target shape layer by layer. Steps 2 and 3 are an
algorithm that people currently run on paper.

**Not forgetting.** You cannot write `f x = 0`. `length` has to give the list
back, and every join loses a bit that the backward run must guess. This
difficulty is *essential*: it is the one rule of manual §2, and it is what 42
is.

The proposal is a surface notation that removes the first difficulty and
makes the second one legible. It rests on four commitments:

1. **It desugars to ordinary 42.** No new primitive, no new combining form, no
   change to `!`, to the type engine, or to anything `THEOREM.md` proves.
   `42 show` prints what was produced.
2. **Inverting a sugared definition means turning its clauses around** (§5).
   42's law becomes visible in the source.
3. **Forgetting is never accidental.** A name that is bound and then dropped is
   a compile error that says why (§4).
4. **A definition is the union of its clauses.** Nothing is first-match. This
   is 42's relational reading carried to the surface (§6), and it is why the
   disjointness conditions of Theseus, RFUN and Janus do not appear.

## 2. The notation, by example

A clause is `def`, a name, any program parameters, a **pattern**, `<->`, and a
**term**. Several clauses with the same name form one definition.

```
def single x            <->  [x]

def append ([], ys)     <->  ys
def append (x:xs, ys)   <->  x : append (xs, ys)

def rev []              <->  []
def rev (x:xs)          <->  append (rev xs, [x])

def initlast (append (xs, [x]))  <->  (xs, x)

def ctrl m (L (), a)    <->  (L (), a)
def ctrl m (R (), a)    <->  (R (), m a)
```

Patterns and terms are the **same language**:

| Form | Meaning |
|---|---|
| `x` | a data variable |
| `()`, `(t, u)`, `L t`, `R t` | the four building blocks of manual §3.1 |
| `0`, `3`, `'a'`, `"hi"`, `[]`, `[t, u]` | the value notation the command line already reads |
| `t : u`, `t + 1` | `R (t, u)` and `R t`, for lists and numbers |
| `P t` | apply a program `P` to the term `t` |

`P` is any 42 program expression: a defined name, a parameter, `append!`,
`ctrl swapsum`, or a parenthesised pipeline `(f ; g)`. Bare `P t` therefore
embeds the whole point-free language, and the two styles mix freely.

**The arrow is `<->`.** The clause is read in both directions (§5), and
`42 type` already prints `<->` between a definition's two sides. `=` would hide
that symmetry and would clash with point-free `def f = …`. `|->` reads one-way.

**Names.** A data variable in a pattern may not have the same name as a
definition, and for the same reason it may not have the same name as one of
the clause's own program parameters. Inside a term, `P t` and a variable are
told apart only by name. In `def f (rev, x) <-> …` it would be unclear whether
`rev` binds a value or runs the definition backwards as a function pattern
(§5). The rule settles it before any reader has to:

```
error: line 2: the pattern variable `rev` has the name of a definition.  In a
pattern, `rev t` runs `rev` backwards, so a variable may not reuse the name.
Rename the variable.
```

## 3. How one clause compiles

Three pieces.

**The shape of a term** is the term with all constructors and calls erased and
every closed subterm (one with no variables, like `[]` or `3`) replaced by a
unit hole `•`. Pairs are kept:

| Term | Shape |
|---|---|
| `[x]`, which is `R (x, L ())` | `(x, •)` |
| `(x:xs, ys)` | `((x, xs), ys)` |
| `x : append (xs, ys)` | `(x, (xs, ys))` |
| `append (rev xs, [x])` | `(xs, (x, •))` |

**Building a term**, written `⟦t⟧`, is a 42 program from the term's shape to
the term:

| Term | `⟦t⟧` |
|---|---|
| `x` | `id` |
| a closed term `c` | the program that builds `c` from `()`, e.g. `⟦[]⟧ = inl` |
| `(t, u)` | `⟦t⟧ * ⟦u⟧` |
| `L t`, `R t` | `⟦t⟧ ; inl`, `⟦t⟧ ; inr` |
| `P t` | `⟦t⟧ ; P` |

**Routing**, written `route(s → s')`, is a pure plumbing program from one shape
to another. It uses `swapprod`, `assocprod`, `f * g`, `unitprod` and
`unitprod!` for the `•` holes, and `copy` and `copy!` where a variable occurs
a different number of times on the two sides (§4).

A clause `p <-> e` then compiles to:

```
⟦p⟧! ; route(shape p → shape e) ; ⟦e⟧
```

That is: match the pattern by *building it backwards*, rearrange, build the
result. Matching is not a separate mechanism. It is `⟦·⟧` run through `!`.

**A matched constant is checked in the route.** Building a closed term starts
from `()`, so building it backwards *ends* at a hole, and whatever value stood
under the constant's label is left in that hole. The route removes every hole
with `unitprod`, which accepts only `()`. A hole that is the whole of the
shape gets an explicit test, `unitprod! ; swapprod ; unitprod`, which passes
`()` and nothing else. Without this, `def f (L ()) <-> 0` would accept `L 5`.
The first implementation had exactly that bug (§11).

**Where the types already guarantee it, the check is dropped.** In `rev`, the
payload under `[]`'s label is `()` because `append` makes it so, and a check
there can never fail on a well-typed value. The rule: each definition is also
compiled without its checks, and that version is kept only if it leaves *every*
definition's inferred type unchanged. The command line refuses an argument
outside the inferred type, so on every input it accepts, the two versions agree.
So `rev`'s empty branch compiles to `inl`, as the course writes it. `ctrl` and
`forget` keep their checks, because there the check is what makes the type
narrower: their clauses say `L ()` and `0`, and nothing else in their bodies
does. The cost: run with `--untyped`, a definition whose checks were dropped
accepts ill-typed values its clauses would refuse (`rev` passes `L 5` through).

**Worked: `single x <-> [x]`.** The pattern `x` has shape `x` and
`⟦x⟧! = id`. The term `[x]` has shape `(x, •)` and
`⟦[x]⟧ = (id * inl) ; inr`. The route from `x` to `(x, •)` is
`unitprod! ; swapprod`. Result:

```
unitprod! ; swapprod ; (id * inl) ; inr
```

which is the manual's `single`, step for step. The compiler has just run the
peel method of manual §16.

**Worked: `append (x:xs, ys) <-> x : append (xs, ys)`.** `⟦p⟧ = inr * id`, so
the match is `inr! * id`. The route from `((x, xs), ys)` to `(x, (xs, ys))` is
`assocprod!`. The build is `(id * append) ; inr`. Result:

```
(inr! * id) ; assocprod! ; (id * append) ; inr
```

After the case-tree step of §6, both `append` clauses together produce
prelude.42's `append` exactly, term for term (checked).

## 4. The use-count rule

Count each data variable's occurrences in the pattern (`m`) and in the term
(`n`):

| `m` | `n` | Compiles to | Reading |
|---|---|---|---|
| 1 | 1 | rearrangement only | the ordinary case |
| 1 | ≥ 2 | `copy` in the route | the value is used twice |
| ≥ 2 | 1 | `copy!` in the route | **an equality test**: `same (x, x) <-> x` holds only on equal pairs |
| ≥ 1 | 0 | **error** | the value would be forgotten |
| 0 | ≥ 1 | **error** | the value would have to be invented |

The rule is symmetric, as §5 requires. Swap the sides of a clause and the last
two rows swap, and so do `copy` and `copy!`. A non-linear pattern is not an
oddity to be forbidden: it is what `copy!` has always meant (manual §14,
"Copying"). The canonical route merges all of a variable's source copies to one
and then splits that one to the target count, so `(x, x) <-> (x, x)` is the
test-and-rebuild, not `id`.

The two error rows are where the essential difficulty surfaces. They should
read as explanations:

```
error: line 1: in `length xs <-> 0`, the variable `xs` is bound and never
used.  42 cannot forget a value: run backwards, nothing would say what `xs`
was.  Return it, or consume it in a call.
```

**Forgetting on purpose** is still possible, the same way 42 does it: one
clause per shape, so that the lost information is the choice *between* clauses.

```
def forget 0      <->  ()
def forget (n+1)  <->  forget n
```

Each clause obeys the rule. The union forgets the number, and the inverse shows
what that cost: `forget!` on `()` asks for every natural number and exhausts the
call depth (checked). The notation does not hide the price. It makes you write
the clauses that pay it.

**Program parameters are exempt.** They stand for programs, not values, and
manual §13 already allows `def there_and_back m = m ; m!`. Only data variables
are counted.

## 5. Inversion is turning the arrows around

> **Claim.** If `D` is a sugared definition and `D˘` is `D` with every clause
> `p <-> e` replaced by `e <-> p`, then `desugar(D˘) = desugar(D)!` as relations.

*Sketch.* One clause gives `(⟦p⟧! ; r ; ⟦e⟧)! = ⟦e⟧! ; r! ; ⟦p⟧`, which is the
compiled form of `e <-> p` provided `r! = route(shape e → shape p)`. It is: the
canonical route's merge, permute and split stages reverse into split⁻¹ = merge,
permute⁻¹ and merge⁻¹ = split. Clauses are joined by `|`, and
`(c₁ | c₂)! = c₁! | c₂!`. Recursion goes through unchanged because of one
detail of §3: **a call inside a pattern already means "run it backwards"**.
`⟦P t⟧! = P! ; ⟦t⟧!`. So when a clause is turned round, the recursive call in
its term lands in a pattern and is read as the inverse, with no renaming. ∎

Here is `append` turned round, which is `split`:

```
def split ys                    <->  ([], ys)
def split (x : append (xs, ys)) <->  (x:xs, ys)
```

The second pattern says: a cons cell whose tail, *run backwards through
`append`*, gives `(xs, ys)`. That is what splitting a non-empty list is, read
off the page. Compiled and run, it returns all three splits of `[1, 2]`
(checked). The sugar does not need a separate inversion procedure. The law of
the language becomes a fact about the notation.

The same detail gives **calls in patterns** generally. Curry calls these
*function patterns*. `initlast (append (xs, [x])) <-> (xs, x)` compiles to
`append!` followed by a single-element match on the right half. `append!`
offers every split, and the match keeps the one whose right half has length
one. Forward it returns `([1, 2], 3)` for `[1, 2, 3]`, and backward it rebuilds
the list (checked; `law holds`).

`42 show` prints every clause definition three ways: the clauses, the same
clauses turned round, and the compiled term with its reverse. The middle block
is the inverse, read off the page:

```
$ ./42 show FILE single
single   x <-> [x]
single!  [x] <-> x
single   = unitprod! ; swapprod ; id * inl ; inr
single!  = inr! ; id * inl! ; swapprod ; unitprod
```

The tests check, for every definition, that the turned-round clauses compile
to the inverse and that both printed blocks parse back to the same clauses.

## 6. Several clauses: a union, then a case tree

**Meaning.** A definition with clauses `c₁ … cₙ` denotes `c₁ | … | cₙ`.
Every clause whose pattern matches contributes. This is the relational
reading, and it differs from Haskell's first-match on purpose. First-match is
an ordered conditional, and an ordered conditional is exactly what RELATED.md
§3 shows every reversible language paying for in some way: Janus with an exit
assertion, Theseus by making non-overlap the only rule, and RFUN with a
first-match policy checked on the output.

42 pays nothing there because `join!` keeps both branches. The sugar inherits
that answer unchanged. `append`'s two clause *outputs* overlap (`ys` can be
any list), and that overlap is precisely why `split` returns several answers.
No condition is imposed, and none needs to be checked.

### Overlap warns

The union is the meaning, but a programmer coming from Haskell will write
overlapping clauses by accident and expect the first one to win. So when two
clauses' **input** patterns can match the same value, the compiler warns:

```
warning: line 2: clauses 1 and 2 of 'f' both match `0` (which is also `[]` and `false`):
    def f [] <-> []
    def f xs <-> xs
42 takes the union of matching clauses, not the first match, so both give
answers there.  If that is meant, give each its own name and write the union:
`def f = ... | ...`.
```

- **Inputs only.** Overlapping *outputs* never warn in 42, because they are
  exactly how a multi-valued inverse arises. `append`'s outputs overlap, and
  that overlap is `split`.
- **Decided by unification over constructors.** This is the orthogonality test
  of RELATED.md §3. Literals are compared by their L/R encoding, so `0`, `[]`
  and `false` overlap. When the clash comes from two notations for one value,
  the message names both.
- **A call inside a pattern counts as a wildcard.** Whether a function pattern
  such as `append (xs, [x])` overlaps another pattern is undecidable in
  general. Treating it as matching anything makes the check conservative: it can
  warn when no value actually lies in both patterns, and it never misses an
  overlap that does exist.
- **Turned-round definitions often warn, and mostly they should.** Turning
  clauses round makes the outputs the inputs. `split` is `append` turned round:
  its two clauses really do overlap, and that overlap is its several answers.
  But `unrev [] <-> []` beside `unrev (append (rev xs, [x])) <-> x:xs` warns
  too, although the call cannot produce `[]`. That warning is the wildcard
  rule's cost (§12).

It is a warning and not an error, because overlap is sometimes intended: it is
how a definition says "both". In Q42 it is an error (§9).

**An intended overlap is written as an explicit union.** Put the overlapping
clauses under separate names and join them with 42's own `|`. No two clauses
of one definition then overlap, so nothing warns, and the source says in plain
42 that both answers are meant:

```
def here   (x:xs)  <->  (x, xs)
def deeper (x:xs)  <->  let (y, ys) = pick xs in (y, x:ys)
def pick = here | deeper
```

`pick` relates a list to each way of taking one element out of it. Run
backwards, it inserts an element at every position (checked: `pick` on
`[1, 2, 3]` gives three answers, `pick!` on `(9, [1, 2])` gives three lists, and
`law holds`). Written as two clauses of a single definition, the same pair would
warn, which is correct: a reader coming from Haskell would take the second
clause for dead code. No pragma or clause mark is needed, because the language
already has a way to say "both".

**Compilation.** `|` is correct but blind. When the clause patterns differ by
`L`/`R` at the same position, the compiler emits a case tree instead. The
equation that licenses this, for the first component of a pair, is:

```
(inl! * id) ; A  |  (inr! * id) ; B   =   dist ; (A + B) ; join
```

Both sides denote the same relation, and the right-hand side is what the course
teaches. The compiler looks for the shallowest such position, reaching into
pairs; a position other than the root or the root's left is first brought
forward with `swapprod` and `assocprod!`. Each branch is then compiled the same
way, recursively.

If the clause *outputs* also differ by `L`/`R` at a common position, sorted
the same way as the inputs, the trailing `join` becomes `dist!` and the label
is carried through instead of being forgotten. Sorted exactly the opposite way,
it becomes `swapsum ; dist!`. For 42 this is an optimisation: the backward run
no longer guesses at that point. For Q42 it is mandatory (§9). What comes out:

```
append = dist ; unitprod + (assocprod! ; id * append ; inr) ; join   -- prelude.42's, exactly
add    = dist ; unitprod + (add ; inr) ; join                         -- prelude.42's, exactly
neg    = swapsum                                    -- neg (L x) <-> R x ;  neg (R x) <-> L x
cross  = dist ; swapsum ; dist! ; swapprod          -- cross (L x, y) <-> (y, R x) ; …
ctrl   = fun m -> dist ; (unitprod ; unitprod!) + (unitprod ; m ; unitprod!) ; dist!
```

`ctrl` is prelude.42's `mat ; (id + m) ; mat!` with `mat` written out. An
earlier draft of this note gave it as `dist ; (id + (id * m)) ; dist!`. That
agrees on the four well-typed inputs, but it never checks that the label's
payload is `()`, so untyped it accepts `(L 5, x)`, which the clauses do not.
Case trees are checked against the plain union on untyped values in both
directions, which is the test that would have caught it.

## 7. `let`: a clause in the middle

A term may be `let q = t in e`. It builds `t` from some of the variables in
hand, matches the result against `q`, and continues with the variables `q`
binds plus the ones left over:

```
def initlast zs  <->  let (xs, [x]) = append! zs in (xs, x)
```

This is the §5 example again, written forwards. A `let` is a clause placed in
the middle of a clause, so it inverts the same way: reverse the chain and swap
each `let`'s two sides. The use-count rule applies across the whole chain.
Every variable is consumed exactly once after it is bound, counting copies.

`let` is what makes larger programs writable, because it is how intermediate
results get names. It is also where most of the plumbing hides in today's 42.

## 8. Same relation, different search

There is one consequence of compiling mechanically that was not expected and
that matters. `rev`'s second clause, `rev (x:xs) <-> append (rev xs, [x])`,
builds the pair `(rev xs, [x])`. The straightforward emission is
`(rev * single) ; append`, and it can be serialised two ways. As relations they
are identical, but the interpreter's search treats them differently:

```
$ ./42 spike/sugar revpar [1,2,3] --backward
depth exceeded: call depth exhausted while unfolding 'append'

$ ./42 spike/sugar rev [1,2,3] --backward
rev!([1, 2, 3]) =
  [3, 2, 1]
  -- 1 result
```

Backwards, `append!` offers every split of the list, including
`([3, 2, 1], [])`. In `revpar` the recursive `rev!` runs on the left half
before the right half's single-element test can reject the split, so it recurses
on a list as long as the one it started with. In `rev` the test runs first.
The course's hand-written `rev` puts `(id * single)` after `swapprod` for the
same reason, though it never says so.

**Rule:** serialise every `f * g` so that recursive calls sit nearest the
middle of the clause and constructor tests sit at its edges. As implemented: in
a pair, each side gets a rank: 0 for constructors only, 1 for a call under a
constructor, 2 for a call outermost. The higher rank is built first,
`(call * id) ; (id * constructors)`, so running it backwards takes the lower
rank apart first, and its checks come before the other side's calls.

The middle rank was added when `tour.42`'s `hanoi` was rewritten in clauses:

```
def hanoi (n+1)  <->  append (relabelA (hanoi n), (L (), R (R ())) : relabelB (hanoi n))
```

Both halves of the pair call something. Run backwards, `append!` offers every
split, and the left half recursed on the whole list before the right half
could check that its first move is (0, 2), so `hanoi!` exhausted the call
depth. The right half's calls sit under a cons cell, which ranks it 1 against
the left half's 2. So the cons-cell check now runs first, and `hanoi!` answers
at once (checked). Since the clause
is `match ; route ; build`, the tests at the front of the match and at the end
of the build run first in their own direction, and both directions get them
early. This is a heuristic, not a termination guarantee (backward termination is
undecidable in general). It is cheap, though, it reproduces what careful hand
code does, and the compiler can apply it everywhere without the programmer
knowing.

This is worth stating in the documentation: **the sugar fixes the denotation
exactly, and the operational behaviour by a stated policy.**

## 9. Q42: the same notation under Theseus's rule

Q42 drops `copy`, `inl`, `inr`, `join`, `|` and `^` (QMANUAL §5). Put through
the sugar, that has three consequences:

1. **The use-count rule tightens to exact linearity.** `n ≥ 2` and `m ≥ 2`
   become errors, because there is no `copy`. QMANUAL §5.2 is careful about the
   reason, and the error message should repeat it: the diagonal is an
   isometry, not a unitary. It is not the no-cloning theorem.
2. **Clause sets compile only as case trees on both sides.** With no `inl`,
   `inr` or `join`, a clause cannot introduce or forget a label alone. Labels can
   only be carried through by `dist … dist!`. So the patterns must cover the
   input type exhaustively without overlap, and the outputs must cover the output
   type the same way. That is **Theseus's single rule**, quoted in RELATED.md
   §3, arrived at from the other side.
3. **Constants appear only as parts of a partition.** `forget` is impossible,
   as it should be.

So the notation is shared and the discipline differs, and the difference lands
exactly on the line the literature already draws between PInj languages and
42. This is reported as a finding, not as a reason to keep the two front ends
the same. If Q42 later wants, say, Silq-style automatic uncomputation in its
`let`, that belongs to Q42 alone.

As implemented, Q42 refuses clause definitions outright and says why: what a
clause compiles to uses `inl`, `inr`, `copy` and `|`. The rule-2 compiler
described above does not exist yet.

Not yet checked: whether every clause set that obeys rule 2, over Q42's types,
compiles to Q42's generators. Theseus proves the analogous result into Π, and
QMANUAL §10 gives Q42's core as the rig-groupoid combinators, which are Π's, so it is expected to hold.
It should be proved before Q42 depends on it.

A *different* tool is also out of scope here: Bennett-style compilation of
irreversible classical code into Q42 oracles. It is useful, but it produces
`x ↦ (x, f x)`, not `f`, and belongs beside the emitter as Q42's own.

## 10. Precedents, and what is particular here

- **Manual §16** is the human version of §3, and the course's peel method
  (Lesson 5) is the same algorithm run by hand.
- **Paterson's arrow notation** (2001) compiles `proc` blocks with named
  variables into point-free arrow combinators. It is the closest engineering
  precedent for §3's routing.
- **Elliott's "Compiling to categories"** (2017) states the general result:
  lambda terms translate into any cartesian closed category. The case needed
  here is the restricted one, linear terms into a symmetric monoidal category,
  with `copy` added.
- **Theseus** (James & Sabry, 2014) and **Chardonnet, Lemonnier & Valiron**
  (2024) are pattern-clause surface languages over Π-style cores, with
  disjointness required on both sides.
- **RFUN** (Yokoyama, Axelsen & Glück, 2011) has `let` chains that invert by
  reversal, its duplication/equality operator, and first-match.
- **Curry's function patterns** (Antoy & Hanus, 2005) allow calls in patterns,
  evaluated by narrowing.

What a relational target changes:

1. **No disjointness condition.** The union of clauses is already the meaning,
   so the condition that the other clause languages impose, order or discharge
   is not needed (§6).
2. **Matching is building run backwards.** Patterns need no mechanism of their
   own, function patterns come free, and inversion is syntactic (§5).
3. **Non-linear patterns are equality tests, by the same rule as `copy`.**
   Nothing extra is needed (§4).

## 11. Where it lives, and what building it found

- **Parser** (`rel42/syntax.py`). Clause definitions sit beside point-free
  ones in the same `.42` files. A `def` is a clause when `<->` comes before
  `=`. Every `def` header is read first, so an identifier in a clause is a
  variable exactly when it names no definition, parameter or primitive. That
  is what makes the naming rule of §2 decidable without types. Clauses of one
  definition must be written together and must share their parameters.
- **Compiler** (`rel42/sugar.py`). Shapes, building, routing (§3), the
  use-count and naming errors (§2, §4), turning clauses round (§5), the overlap
  check and case trees (§6), `let` (§7), the order rule (§8), and a peephole
  pass that keeps only rewrites that are equalities of relations. It depends on
  `core` alone and hands back ordinary terms, so `run`, `!`, inference and
  meta.42 never see a clause.
- **What a program sees.** `parse_program` returns the compiled definitions as
  before. It also keeps the clauses as written (`Program.clauses`) and the
  warnings (`Program.warnings`); the command line prints warnings on stderr.
  `42 show` prints the three blocks of §5.
- **Q42** parses with clauses switched off, and the refusal names §9.
- **Tests** (`tests/test_sugar.py`, 58). Every example is checked against its
  hand-written counterpart in `course.42`, `prelude.42` or `spike/sugar.42`,
  forwards and backwards. Turned-round clauses compile to the inverse. Printed
  clauses parse back. Case trees agree with the plain union on 34 untyped
  values. Every error and warning is triggered.
- **One promise not kept.** Errors give the clause's line, not the position of
  the generated node they came from. Carrying positions on every node would
  change `core`'s term classes, which Q42 shares, and that was not worth doing
  yet (§12).
- **The course is unchanged.** It teaches what the compiler emits, which is
  still what you read when a result is empty.

**What building it found.**

1. **Matched constants were not checked.** The first version matched a
   constant by building it backwards and relied, without saying so, on the
   route's `unitprod` to check the hole it left behind. Two shortcuts skipped
   that `unitprod`: one for a route between identical shapes, one for a pattern
   that is only a constant. So `def f (L ()) <-> 0` accepted `L 5`. The case
   trees exposed it, because moving a label out of a pattern often leaves just
   such a shape. Fixed as §3 describes, with a regression test.
2. **The hand-written `ctrl` was looser than its clauses** (§6). What the
   compiler emits agrees with the prelude; the spike file has been corrected.
3. **Checking constants cost some readability**, until the checks the types
   make dead were dropped (§3). `rev`'s empty-list branch went from
   `unitprod! ; swapprod ; unitprod ; inl` back to `inl`.
4. **The order rule matters, as §8 predicted.** Without it `rev!` written as
   clauses exhausts the call depth. With it, it answers at once.
5. **Overlap warnings on turned-round definitions** (§6).
6. **A chain of two `let`s did not compile.** A `let` also tried to carry past
   itself names that a *later* `let` binds. Every test had used one `let`;
   rewriting `arith.42`'s `undivmod` in clauses was the first chain of two.
   Fixed, with a regression test.
7. **Rewriting the libraries improved the output.** The output case tree of
   §6 now looks at the final term of a `let` chain, so `lt` compiles to
   `dist ; … ; dist!` rather than `join`. And inside a route, where every value
   has a known shape, a rearrangement followed by its inverse is cancelled
   (never a unit check), which shortened `undivmod` considerably.

## 12. Open questions

1. **Partiality.** Missing clauses are legitimate in 42: no answer is normal.
   Should non-exhaustive patterns warn at all?
2. **Resugaring.** Running a point-free program on symbolic variables yields
   its clause form for everything except `^`. A `42 explain` built on this would
   help *read* existing 42. It is not an inverse of desugaring, since routes are
   canonicalised, and should not be described as one.
3. **The Q42 compilation result** of §9, which should be proved rather than
   assumed, and then the rule-2 compiler built on it.
4. **A sharper overlap check for calls in patterns.** Treating a call as a
   wildcard warns on `unrev`, whose call can never produce `[]`. The check
   could look at what the called definition can return: its clauses' outputs
   when it has clauses, or its inferred type. More precise, but the warning
   would then depend on another definition's body.
5. **Source positions on generated nodes** (§11).
