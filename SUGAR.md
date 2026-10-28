# 42 with Names — a design note on pointful syntax

*Draft design note, 2026-10-28. Nothing here is implemented. Every compiled
example in it has been written out by hand in `spike/sugar.42` and run against
the current interpreter. Where this note says "checked", that is what it means.*

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
11. [Where it would live](#11-where-it-would-live)
12. [Open questions](#12-open-questions)

---

## 1. The problem, and the part of it this note does not touch

Writing 42 is hard in two different ways.

**Plumbing.** There are no names, so values are routed by hand with
`swapprod`, `assocprod`, `unitprod!` and `dist`. `single` is four steps of
moving parentheses to say `[x]`. This difficulty is *accidental*. The manual's
§9 already says how to write a program: "Step 1 — write it with names, as an
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
error: in `f (rev, x) <-> …`, the pattern variable `rev` has the name of a
definition.  In a pattern, `rev t` runs `rev` backwards, so a variable may not
reuse the name.  Rename the variable.
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

**Worked: `single x <-> [x]`.** The pattern `x` has shape `x` and
`⟦x⟧! = id`. The term `[x]` has shape `(x, •)` and
`⟦[x]⟧ = (id * inl) ; inr`. The route from `x` to `(x, •)` is
`unitprod! ; swapprod`. Result:

```
unitprod! ; swapprod ; (id * inl) ; inr
```

which is the manual's `single`, step for step. The compiler has just run the
peel method of manual §9.

**Worked: `append (x:xs, ys) <-> x : append (xs, ys)`.** `⟦p⟧ = inr * id`, so
the match is `inr! * id`. The route from `((x, xs), ys)` to `(x, (xs, ys))` is
`assocprod!`. The build is `(id * append) ; inr`. Result:

```
(inr! * id) ; assocprod! ; (id * append) ; inr
```

After the case-tree step of §6, both `append` clauses together produce
prelude.42's `append` exactly (checked: `appendt` in the spike file).

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
oddity to be forbidden: it is what `copy!` has always meant (manual §6,
"Copying"). The canonical route merges all of a variable's source copies to one
and then splits that one to the target count, so `(x, x) <-> (x, x)` is the
test-and-rebuild, not `id`.

The two error rows are where the essential difficulty surfaces. They should
read as explanations:

```
error: in `length xs <-> n`, the variable `xs` is bound by the pattern and
never used.  42 cannot forget a value: run backwards, nothing would say what
`xs` was.  Return it (e.g. `(xs, n)`), or consume it in a call.
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
manual §5 already allows `def there_and_back m = m ; m!`. Only data variables
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
warning: clauses 1 and 2 of `f` both match `[]`:
    def f []  <->  …
    def f xs  <->  …
42 takes the union of matching clauses, not the first match, so `f []` gets
the answers of both.
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
teaches. If the clause *outputs* also differ by `L`/`R` at a common position,
the trailing `join` can become `dist!` and the label is carried through
instead of being forgotten. `ctrl`'s two clauses compile that way to
`dist ; (id + (id * m)) ; dist!`, which equals prelude.42's
`mat ; (id + m) ; mat!` (checked on all four inputs of `flip`). For 42 this is
an optimisation: the backward run no longer guesses at that point. For Q42 it
is mandatory (§9).

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
middle of the clause and constructor tests sit at its edges. Since the clause
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

Not yet checked: whether every clause set that obeys rule 2, over Q42's types,
compiles to Q42's generators. Theseus proves the analogous result into Π, and
QMANUAL §10 gives Q42's core as the rig-groupoid combinators, which are Π's, so it is expected to hold.
It should be proved before Q42 depends on it.

A *different* tool is also out of scope here: Bennett-style compilation of
irreversible classical code into Q42 oracles. It is useful, but it produces
`x ↦ (x, f x)`, not `f`, and belongs beside the emitter as Q42's own.

## 10. Precedents, and what is particular here

- **Manual §9** is the human version of §3, and the course's peel method
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

## 11. Where it would live

- **Parser.** `rel42`'s parser accepts clause definitions beside point-free
  ones, in the same `.42` files. A clause is recognised by `<->` at the top
  level of a `def`.
- **Desugarer.** A new module turns each clause group into a core term
  (§3, §6, §8) before type inference. It also issues the use-count and name
  errors (§2, §4) and the overlap warning (§6). Source positions are kept on
  every emitted node, so type errors and empty results point at the clause, not
  at generated plumbing.
- **`42 show`** prints the clauses, the emitted 42, and its reverse.
- **Tests.** Rewrite every definition in `course.42` and `prelude.42` that has a
  natural clause form, and check that it agrees with the original on sample
  values in both directions. `spike/sugar.42` is the hand-made first instalment.
- **The course is unchanged.** It teaches what the compiler emits, and that
  remains the thing you read when a result is empty. A later appendix could show
  each lesson's definition in clause form beside it.

## 12. Open questions

1. **Partiality.** Missing clauses are legitimate in 42: no answer is normal.
   Should non-exhaustive patterns warn at all?
2. **Resugaring.** Running a point-free program on symbolic variables yields
   its clause form for everything except `^`. A `42 explain` built on this would
   help *read* existing 42. It is not an inverse of desugaring, since routes are
   canonicalised, and should not be described as one.
3. **The Q42 compilation result** of §9, which should be proved rather than
   assumed.
