# Reversibility without Injectivity

### a point-free reversible language interpreted in Rel

**The 15-page conference draft.** Written for Reversible Computation, compiles,
and fits. It is now the *basis for a journal version* at roughly twice this
length rather than the submission itself. Sections here that read as compressed
— the simulation proofs, the gadget proofs, related work — are compressed on
purpose. Places needing an author decision are marked `[AUTHORS]`. Every
language compared here has now been read directly; nothing in the draft rests on
a description at second hand.

`[AUTHORS]` *Authorship.* The 1993 language this one descends from is credited in
its thesis to Joep Rous and Paul Jansen, and the paper listed there as
forthcoming was to be joint. Whether this paper is single- or joint-authored is
not a decision this draft makes.

---

## Abstract

Reversible functional languages require the clauses of a program to be
non-overlapping, so that backward execution is deterministic. Inv assumes the
condition and leaves checking it as future work, Theseus makes it the single rule
a programmer must maintain, RFUN relaxes it into a first-match ordering,
PisoLang decides it by unification, and Chardonnet et al. formalise it as an
orthogonality premise in the typing rule. We ask what happens if it is simply not
imposed.

The answer is 42, a point-free language interpreted in the category **Rel** of
sets and relations, whose defining law is `x ∈ P(y) ⟺ y ∈ inv(P)(x)`. Giving up
injectivity makes the metatheory *smaller*: inversion becomes a total, involutive
operation with no side conditions, no well-formedness checks and no proof
obligations, computed by an eight-line structural recursion and eliminated at
parse time. We present the language and its equirecursive type system, which is
inferred with no annotations and in which the occurs check is a diagnosis rather
than a failure; we prove type soundness, in a form that is necessarily two-sided
because inversion is total; and we characterise expressiveness: the relations
denotable in 42 are exactly the recursively enumerable ones, with Turing
completeness as the single-valued case. An implementation, all examples and a
machine-checked version of every claim in this paper are available as an
artifact.

**Keywords:** reversible computation · relational semantics · point-free
programming · dagger categories · expressiveness

---

## 1. Introduction

Every functional reversible language in the literature carries the same
obligation. If a program is a set of clauses and it must run backwards
deterministically, then no two clauses may produce results that overlap — and the
languages differ mainly in how they discharge it.

**Inv** assumes it. Mu, Hu and Takeichi require that in `f ∪ g` "*not only the
domains, but the ranges of `f` and `g`*" be disjoint, and add that "*the
disjointness may be checked by a type system, but we have not explored this
possibility*". The condition costs them a primitive: an inequality test `neq`
exists in the language because it is "*sometimes necessary for ensuring the
disjointness of the two branches of a union*".

**Theseus** makes it the single rule a programmer must maintain, on both sides of
every clause:

> Non-overlapping and exhaustive coverage in pattern clauses. The collections of
> patterns in the left-hand side (LHS) of each clause must be a complete
> non-overlapping covering of the input type. Similarly, the collections of
> patterns in the right-hand side (RHS) of each clause must also be a complete
> non-overlapping covering of the return type.

**RFUN** identifies the same problem — "*case branches may be non-orthogonal: the
result might conceivable have come from several branches*", which it calls "*the
functional variant of the problem of the general irreversibility of if-then-else
constructs*" — and answers it not by forbidding overlap but by ordering it, under
a first-match policy in which a result "*must never match a branch that textually
precedes it*".

**PisoLang** decides orthogonality by unification, as two premises of its
case-typing rule. **Chardonnet, Lemonnier and Valiron** formalise it as a
structural relation `v₁ ⊥ v₂` appearing twice in the typing rule for an iso,
keeping non-overlap while dropping exhaustivity "*in order to allow
non-terminating behaviour*". In the imperative branch, **Janus** obliges the programmer to
discharge it. Its conditional carries a second predicate: "*the predicate after
`if` is the test, and that after `fi` is the assertion*", and "*the assertion
makes the conditional reversible*" — at the price, stated as plainly, that "*if
the assertion does not have the required value, execution of the loop is
undefined*".

Six languages, six answers, and one question none of them asks: **what if the
condition is simply not imposed?**

### 1.1 What happens if you decline

Declining it means leaving the category **PInj** of partial injections for the
category **Rel** of sets and relations. The backward direction becomes
many-valued, and the defining law of the language acquires an `∈`:

```
                    x ∈ P(y)   ⟺   y ∈ inv(P)(x)
```

Read carefully, this says that running forwards and then backwards returns a set
*containing* where you started, rather than returning where you started. That is
the price, it is paid in exactly one place, and we state it at the outset because
the rest of the paper is an argument that it is worth paying.

What it buys is that inversion becomes **total**. There is no side condition, no
well-formedness check, no proof obligation and no undecidable question anywhere
in the definition of the inverse of a program. Concretely, the entire inversion
algorithm of the implementation is

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

and `dagger(dagger(t)) = t` holds syntactically, on the nose. Because it is
total, the surface syntax can eliminate the inversion operator `!` at parse time,
so that it never appears in the abstract syntax at all:

```
    parse("(copy ; join)!")  ==  parse("join! ; copy!")
```

This property has been named in the literature at least three times, which is
itself worth recording. Theseus calls an operator **syntactically reversible**
when its inverse reading coincides with its inverse meaning. Yokoyama and Glück
call an inversion **local** "*iff for any given program unit the inversion can
always produce an inverse unit*", and prove Janus has it. And the 1993 design of
§1.3 states it as an equation, `(⊙(R₁,…,Rₙ))⁻¹ = ⊙(Rₙ⁻¹,…,R₁⁻¹)`. All three give
sequential composition as the worked example, and all three arrive at the
contravariant law — Janus as `(s₁ s₂)˘ ∼ s̆₂ s̆₁`.

Where they differ is what it costs to hold the property everywhere. **Janus holds
it**, and pays with the assertion: a predicate the programmer must supply for
every conditional, undefining the program when it is wrong. **Theseus does not
hold it** — its own conditional fails, and so does its boolean test, leaving open
whether restricting tests to a symmetric subclass costs expressiveness. The 1993
design does not hold it either, for the same reason.

**This paper's language holds it with neither price**: nothing for the programmer
to discharge, and no construct excluded. The mechanism is that there is no
conditional to fail it and no test operator to weaken — branching is the sum
functor, and filtering is a composite of the diagonal (§5.3).

### 1.2 Contributions

1. **A point-free reversible language over Rel in which every combinator is
   syntactically reversible** (§2, §3). We show that this is precisely what
   dropping the disjointness condition buys, and that the resulting metatheory is
   smaller than that of the injective languages rather than larger.
2. **An equirecursive type system, inferred with no annotations** (§4), in which
   a cyclic substitution is admitted exactly when the recursive type it describes
   is inhabited — the occurs check as a diagnosis rather than a failure. We prove
   type soundness, and show that the statement must be two-sided, because at the
   inversion rule the goal concerns the domain of the premise.
3. **A characterisation of expressiveness** (§5): the relations denotable in 42
   are exactly the recursively enumerable ones. Turing completeness is the
   single-valued case; the upper bound is the more informative half, and it holds
   because every combinator is a positive operation and nothing in the language
   forms a complement.

### 1.3 Provenance

The design is not new. It is the second instantiation of a language called 4₂,
specified in a 1993 Master's thesis at the University of Amsterdam and never
published, which arose not from reversible computing but from machine
translation — bidirectional grammars for the Rosetta project at Philips. That
thesis already states the defining law above as a numbered equation, already
defines syntactic reversibility as `(⊙(R₁,…,Rₙ))⁻¹ = ⊙(Rₙ⁻¹,…,R₁⁻¹)`, and
already finds its own conditional violating it. What it does not have is the
point-free core: 4₂ is imperative, with variables and assignment-shaped
transformers, and the semiring primitive set of §2 is the second instantiation's
contribution. We record the lineage for honesty about priority, not as evidence;
nothing in this paper rests on it.

---

## 2. The language

### 2.1 Syntax

Types are the trees over `0`, `1`, `+` and `×`, with variables and a recursion
binder:

```
    T  ::=  0 | 1 | T + T | T × T | X | μX. T
```

and are **equirecursive**: `μX. F` and `F[μX.F/X]` are the same type, not merely
isomorphic. Values are finite trees over the same four constructors — `()`, `L v`,
`R v`, `(v₁, v₂)` — and `V(T)` denotes the values of type `T`. We write `𝕍` for
the union of all of them, since the evaluator is untyped and works on `𝕍`.

A program is a set of definitions over thirteen primitives and six combinators:

```
    t  ::=  p | t ; t | t + t | t * t | t | t | t^ | t!
```

with `;` sequential composition in diagrammatic order, `+` and `*` the sum and
product functors, `|` union, `^` reflexive-transitive closure and `!` inversion.

The thirteen primitives are the isomorphisms witnessing the commutative-semiring
structure of `(0, 1, +, ×)` — that is, a rig groupoid presentation — together
with the two morphisms that make the setting Rel rather than a groupoid.

**Figure 1** *(primitive schemes; these are the implementation's own table, and
are checked against it by the artifact's test suite)*

| primitive | scheme | | primitive | scheme |
|---|---|---|---|---|
| `id` | `a <-> a` | | `dist` | `(a + b) x c <-> a x c + b x c` |
| `zero` | `a <-> b` | | `inl` | `a <-> a + b` |
| `swapsum` | `a + b <-> b + a` | | `inr` | `a <-> b + a` |
| `assocsum` | `a + (b + c) <-> a + b + c` | | `copy` | `a <-> a x a` |
| `unitsum` | `0 + a <-> a` | | `join` | `a + a <-> a` |
| `swapprod` | `a x b <-> b x a` | | | |
| `assocprod` | `a x (b x c) <-> a x b x c` | | | |
| `unitprod` | `1 x a <-> a` | | | |

`copy` and `join` are the diagonal and the codiagonal. Neither is an isomorphism,
and their presence is the whole of the difference between this language and the
groupoid fragment; §6 returns to the fact that Π names exactly these two as
identities that do *not* hold, and recovers them only as effects.

### 2.2 Typing

**Figure 2** *(typing rules)*

```
    ⊢ t : A <-> B    ⊢ u : B <-> C            ⊢ t : A <-> B    ⊢ u : C <-> D
    ──────────────────────────────  seq       ──────────────────────────────  sum
          ⊢ t ; u : A <-> C                     ⊢ t + u : A + C <-> B + D

    ⊢ t : A <-> B    ⊢ u : C <-> D            ⊢ t : A <-> B    ⊢ u : A <-> B
    ──────────────────────────────  prod      ──────────────────────────────  union
      ⊢ t * u : A × C <-> B × D                      ⊢ t | u : A <-> B

              ⊢ t : A <-> A                              ⊢ t : A <-> B
              ─────────────  star                        ─────────────  dagger
             ⊢ t^ : A <-> A                             ⊢ t! : B <-> A
```

together with the primitives of Figure 1 as axioms, at every ground
instantiation.

Two remarks. There are no `fold` and `unfold` rules, and their absence *is* the
equirecursive choice: `μX.F` and its unfolding are the same type, so nothing has
to be written to pass between them. And the **dagger** rule is the type-level
shadow of the defining law — it exchanges the two sides and does nothing else,
which is why it is implemented as a swap of the inferred scheme.

### 2.3 Semantics

The evaluator is untyped: `⟦t⟧ ⊆ 𝕍 × 𝕍`, and a shape mismatch denotes the empty
relation rather than raising an error. Being outside the domain of a relation is
not a failure; it is having no image.

**Figure 3** *(denotations; `v`, `a`, `b`, `c` range over `𝕍`)*

```
⟦id⟧        = { (v, v) }                    ⟦zero⟧   = ∅
⟦swapsum⟧   = { (L v, R v) } ∪ { (R v, L v) }
⟦assocsum⟧  = { (L a, L (L a)) } ∪ { (R (L b), L (R b)) } ∪ { (R (R c), R c) }
⟦unitsum⟧   = { (R v, v) }
⟦swapprod⟧  = { ((a, b), (b, a)) }
⟦assocprod⟧ = { ((a, (b, c)), ((a, b), c)) }
⟦unitprod⟧  = { (((), v), v) }
⟦dist⟧      = { ((L a, c), L (a, c)) } ∪ { ((R b, c), R (b, c)) }
⟦inl⟧       = { (v, L v) }                  ⟦inr⟧    = { (v, R v) }
⟦copy⟧      = { (v, (v, v)) }               ⟦join⟧   = { (L v, v) } ∪ { (R v, v) }

⟦t ; u⟧ = { (a, c) : ∃b. (a, b) ∈ ⟦t⟧ ∧ (b, c) ∈ ⟦u⟧ }
⟦t + u⟧ = { (L a, L b) : (a, b) ∈ ⟦t⟧ } ∪ { (R c, R d) : (c, d) ∈ ⟦u⟧ }
⟦t * u⟧ = { ((a, c), (b, d)) : (a, b) ∈ ⟦t⟧ ∧ (c, d) ∈ ⟦u⟧ }
⟦t | u⟧ = ⟦t⟧ ∪ ⟦u⟧      ⟦t^⟧ = ⋃_{n ≥ 0} ⟦t⟧ⁿ      ⟦t!⟧ = ⟦t⟧°
```

`⟦inl⟧` and `⟦inr⟧` are total functions forwards and partial backwards, which is
where partiality enters. `⟦join!⟧` is the only primitive whose image can have two
elements: **every set larger than a singleton anywhere in the language traces
back to it**, which is worth knowing, because it means ambiguity in 42 has
exactly one origin.

A program is a finite, possibly mutually recursive system of definitions inducing
`Φ : Rel^n → Rel^n`. Every operation above is monotone and Scott-continuous —
including converse, which is a lattice isomorphism — so the program denotes
`lfp Φ = ⋃_k Φ^k(∅⃗)`.

Parameterised definitions (`def ctrl m = mat ; (id + m) ; mat!`) are
second-order: a parameter denotes a relation, never another combinator. They are
eliminated by substitution before evaluation, and we assume throughout that
programs contain none. §6 notes that Theseus and RFUN make the same choice and
describe it in the same terms.

### 2.4 This is not Kleene algebra with tests

`;`, `|` and `^` are the regular operators, and the resemblance is not accidental:
the 1993 design cites Pratt and Harel for exactly this fragment. The differences
are two, and they are what the paper is about.

First, Kleene algebra with tests is **single-sorted** — one carrier, with tests a
Boolean subalgebra of it — whereas terms here are typed `A <-> B` between
*different* objects, and `+` and `*` are **functors** on that typing, not
operations on a single carrier. Second, the base is not an arbitrary alphabet but
a fixed, forced generating set: the semiring isomorphisms. The setting is
therefore *regular control over rig-groupoid data*, and the content is in the
interaction: `dist` is what lets `;`/`|`/`^` see inside a sum, and `copy`/`join`
are what let them leave the groupoid.

One consequence is worth stating early because it recurs in §5. Over **finite**
types, `;`, `|` and `^` give exactly finite-state power; all unboundedness comes
from the `μ`-types, never from the control structure.

---

## 3. What dropping the condition buys

### 3.1 The obligation, and what it costs those who accept it

§1 listed six discharges of one condition. What is less often noted is what each
costs.

- **Inv** spends a primitive. `neq` is in the language to establish disjointness.
- **Theseus** must reject programs that a programmer would expect to write: its
  §3.1 gives four examples of invalid expressions, of which `drop_var` merely
  fails to use a bound variable on the other side, and `dup_var` uses one twice.
  Both are forbidden by its rule that each variable "*must appear exactly once on
  the other side and with the same type*".
- **PisoLang** must decide pattern orthogonality by unification, and must carve
  out a "controlled non-linear use of variables" to recover duplication at all.
- **Chardonnet et al.** carry orthogonality as two premises in a typing rule.
- **RFUN** must fix an order on clauses and make the semantics depend on it.
- **Janus** pushes the obligation onto the programmer, who must choose an exit
  assertion for every conditional such that backward flow is deterministic, and
  whose program is undefined if the choice is wrong.

Janus repays a closer look, because on one point it agrees with us against the
functional languages. It does **not** require its operations to be injective:
"*The evaluation of expressions is not backward deterministic because function
`[[⊙]]` is not injective, and thus there exists no inverse. As we shall see, this
does not harm the backward and forward determinism of Janus statements.*"
Injectivity is demanded of statements, not of arithmetic, and a syntactic
restriction on assignment buys it. So Janus and this paper agree that
non-injective operations are admissible, and differ only in where the cost is
paid: Janus in a restriction plus an assertion per conditional, 42 in the `∈`.

### 3.2 What declining it buys

Four things, and the first is the one that matters.

**Inversion is total.** `dagger` is defined on every term, by the eight-line
structural recursion of §1.1. There is no case in which it is undefined, no
condition it must check, and no property of the argument it must establish first.
`dagger ∘ dagger = id` holds syntactically.

**`!` need not exist in the abstract syntax.** Because inversion is total, the
parser can push it to the leaves and discard it, so no evaluator, printer,
optimiser or type rule ever encounters an inverted composite.

**There is no progress theorem to weaken.** In a language of partial isomorphisms
a stuck term is an embarrassment: PisoLang records that `(case True ↔ ()) False`
is well-typed and stuck, so progress fails. Here that term denotes `∅`, which is
a perfectly good morphism of Rel, and no theorem is lost because none was
claimed.

**Ambiguity has one source.** Every non-singleton image traces to `join!` (§2.3).
A language that forbids ambiguity must exclude it everywhere; one that permits it
can localise it.

### 3.3 What it costs

The `∈`. Forward-then-backward returns a set containing where you started:

```
    add(2,3) = 5          add!(5) = {(0,5), (1,4), (2,3), (3,2), (4,1), (5,0)}
```

Both directions run the *same definition*; the backward one is its dagger,
computed mechanically. Whether this is acceptable is a question about what one
wants a reversible language for — and we note that composition can restore
determinism that a factor lacks. `double = copy ; add` has a single-valued
dagger, because `copy!` keeps only pairs whose components agree, so `double! 6 =
{3}` and `double! 7 = ∅`.

**The `∈` does not improve on sets, and cannot be made to.** One naturally asks
whether the law recovers an equality when lifted from points to sets. Writing
`⟦t⟧[Y] = ⋃_{y ∈ Y} ⟦t⟧(y)` for the direct image, the candidate is

```
                    X = ⟦t⟧[Y]   ⟺   Y = ⟦t!⟧[X]
```

and it fails in both directions, for two dual reasons that are exactly Figure 1's
last two rows. `join` refutes `⟹`: taking `Y = {L a}` gives `X = {a}` and
`⟦join!⟧[X] = {L a, R a} ⊋ Y`. `inl` refutes `⟸`: taking `X = {R b}` gives
`Y = ∅` and `⟦inl⟧[∅] = ∅ ⊊ X`. What survives is the inclusion
`Y ⊆ ⟦t!⟧[⟦t⟧[Y]]`, for `t` total on `Y` — the same `∈`, one level up. The
biconditional holds for all `X` and `Y` precisely when `⟦t⟧` is a bijection
`V(A) → V(B)`, which is the top row of §6's axis.

There *is* a genuine set-level biconditional, but it is an adjunction rather than
an inversion, and it replaces the direct image of the converse by the **universal**
preimage:

```
                ⟦t⟧[Y] ⊆ X   ⟺   Y ⊆ { y : ⟦t⟧(y) ⊆ X }
```

That operation is not definable in 42, and necessarily not. Take `X = ∅`: the
right-hand side becomes `{ y : ⟦t⟧(y) = ∅ }`, the complement of the domain of `t`.
Domains are r.e. and their complements are not, so the relation
`{(y, ()) : ⟦t⟧(y) = ∅}` is not `Σ⁰₁` and Corollary 5 forbids it outright.

This is worth stating because **it makes two of the paper's results one result.**
The `∈` is not an artefact of presentation that a cleverer formulation could
remove: the operation that would convert it into an `=` is precisely a
complement-former, and a complement-former is precisely what §5.2 identifies as
the thing the language does not have and cannot acquire without losing Theorem 3.
The price paid here and the ceiling proved there have a single cause.

### 3.4 Why the trade is favourable in principle, not only in practice

There is a reason the metatheory gets smaller rather than larger, and it is
semantic. The class of relations 42 denotes will be shown in §5 to be the
recursively enumerable relations, and that class is **closed under converse** —
swap the pairs in the enumeration. The class an injective language denotes,
computable partial injections, is closed under inverse too, but the closure has
to be *earned*: an injective language must ensure that every construct it admits
preserves injectivity, which is exactly the disjointness obligation. A language
over Rel gets the closure for free, because the ambient category is already a
dagger category. **The totality of `!` in the syntax is a shadow of the fact that
Rel has a dagger and PInj's inverse must be constructed.**

---

## 4. Types

Types are inferred and never written. Nothing in the surface syntax mentions a
type, and there is no `fold`/`unfold`.

### 4.1 Inference

Algorithm W with constraints and unification. Because every definition is a
closed term, there is no environment of monomorphic assumptions to avoid
capturing, and none of the usual generalisation machinery — levels, ranks, the
value restriction — is needed. Mutually recursive groups are solved as a unit
against monomorphic assumptions and generalised once, Milner-style.

A `μ` is never something a programmer reaches for. It is what the checker infers
when unification closes a loop:

```
    def double = copy ; add        double : μX. 1 + X <-> μY. 1 + Y
```

`nat` is declared nowhere; `copy` forces `add`'s two summands to agree, and that
*is* `nat <-> nat`.

### 4.2 A cycle is the recursive type

Where a finite-tree checker runs an occurs check and gives up, this one binds the
variable to a term containing itself and carries on. Unification then works up to
unfolding, **coinductively**: assume the two sides equal, and check that the
assumption survives one layer. The set of assumptions is finite because the
regular trees a cyclic substitution can describe have finitely many distinct
subterms, and that is what makes the procedure terminate.

### 4.3 But a cycle is read before it is trusted

Not every cycle is a type. `b = a + b` is `μX. a + X`, a list, which has finite
values; `a = a × a` is `μX. X × X`, which has none — and `copy^` is how one
writes it. The test is one unfolding with the variable taken empty:

> `μX. F(X)` has a finite value exactly when `F(0)` does.

If `F(0)` is empty then so is `F(F(0))`, and so on. The occurs check therefore
becomes a *diagnosis*: a cycle is admitted when the recursive type it describes
is inhabited and rejected when it is not, and the rejection message names the
equation that could not be satisfied. We know of no other language in this family
that infers its recursive types at all; all of them are declared.

### 4.4 Soundness, and why it must be two-sided

The rules of §2.2 constrain the untyped relations of §2.3. Stating how takes one
turn of care.

> **Proposition 1 (Soundness).** Let `⊢ t : A <-> B` with `A`, `B` ground. Then
> for every `(v, w) ∈ ⟦t⟧`,
>
> ```
>     v ∈ V(A)  or  w ∈ V(B)   implies   v ∈ V(A) and w ∈ V(B).
> ```

The expected form — *`v ∈ V(A)` implies `w ∈ V(B)`* — **cannot be proved by
induction here**. At the `dagger` rule the goal for `t!` concerns the codomain of
`t!`, which is the *domain* of `t`, and the induction hypothesis says nothing
about domains. The statement must therefore carry both directions at once. Stated
as above it is **self-dual**: the claim for `t : A <-> B` and the claim for
`t! : B <-> A` are literally the same sentence, so the dagger case is discharged
by observing that `⟦t!⟧ = ⟦t⟧°` and that the condition is symmetric.

This is the defining law appearing in the metatheory. *A language whose inversion
is total cannot have a one-sided type soundness theorem, and does not need one.*

*Proof.* Induction on the derivation. The thirteen primitive cases are immediate
from Figure 3, and three are representative. For `join : A' + A' <-> A'` a pair
is `(L a, a)` or `(R a, a)`, and `L a ∈ V(A'+A') ⟺ a ∈ V(A')` — the
biconditional the statement wants. For `inl : A <-> A + B'` a pair is `(v, L v)`
and `L v ∈ V(A + B') ⟺ v ∈ V(A)`. For `unitsum : 0 + A <-> A` a pair is
`(R v, v)`, and `V(0 + A)` has no `L` component at all because `V(0) = ∅` — which
is exactly why the evaluator returns the empty set on an `L`. `zero` is vacuous.

For `seq`, let `(a, c) ∈ ⟦t ; u⟧`, so `(a, x) ∈ ⟦t⟧` and `(x, c) ∈ ⟦u⟧`. If
`a ∈ V(A)` the hypothesis for `t` gives `x ∈ V(B)` and then that for `u` gives
`c ∈ V(C)`; if instead `c ∈ V(C)`, the hypotheses are used in the other order.
Both readings are available precisely because the statement is two-sided. `sum`
and `prod` reduce to the hypotheses componentwise, and `prod` needs the two-sided
form even with no dagger in sight, since knowing only `(b,d) ∈ V(B×D)` requires
reading each hypothesis backwards. `union` applies either hypothesis. For `star`,
`A = B`, `n = 0` is the identity and each further step is the hypothesis for `t`
in whichever direction the given end supplies. `dagger` is as above. For a
recursive group, `⟦f_i⟧ = ⋃_k Φ^k(∅⃗)_i`; each approximant satisfies the property
and the property is preserved by unions of chains, being a condition on
individual pairs. ∎

> **Corollary 2.** If `⊢ t : A <-> B` and `v ∈ V(A)` then every result of running
> `t` forwards on `v` lies in `V(B)`; and if `w ∈ V(B)`, every result of running
> it backwards lies in `V(A)`.

Note what this does *not* say. Nothing here promises a result exists: `⟦pred⟧` at
`0` is empty, which is a legitimate morphism, so there is no progress property to
state and none is lost (§3.2).

---

## 5. Expressiveness

### 5.1 The statement

> **Theorem 3.** Let `A`, `B` be closed types and `R ⊆ V(A) × V(B)`. There is a
> closed 42 program denoting `R` **iff** `R` is recursively enumerable.

Two remarks on why this and not "42 is Turing complete", which is the `⊇` half
alone. First, the `⊆` half is the more informative one: it says 42 denotes
*exactly* `Σ⁰₁`, so no program decides the complement of the halting problem and
no extension of the primitive table can change that without adding a form of
negation. Second, the statement has the right shape for a relational language.
The reference result in this area is Axelsen and Glück's, that reversible Turing
machines compute exactly the injective computable functions; Chardonnet et al.
prove the corresponding statement for a Theseus-descended language, concluding
that it "*fully characterises all of the computable morphisms in PInj*". Read
together, their theorem and Theorem 3 are the same statement in two different
categories — *every computable morphism of the ambient category is denotable* —
with PInj there and Rel here. **What 42 changes is not the theorem; it is the
category.**

### 5.2 Soundness

> **Proposition 4.** For every program and every closed term `t : A <-> B` over
> it, `⟦t⟧` is recursively enumerable, and an index is computable from the text.

*Proof sketch.* Three steps. The primitives denote decidable relations on a
decidable set of finite trees. The six operations preserve r.e. uniformly:
composition by dovetailing, union by interleaving, `+` and `*` by applying the
tag or the pairing, converse by swapping each enumerated pair, and `t^` because
`⟦t⟧ⁿ` is uniformly r.e. in `n`. Recursion adds nothing: by continuity
`lfp Φ = ⋃_k Φ^k(∅⃗)`, an index for each approximant is computable from `k`, and
dovetailing gives the limit. ∎

> **Corollary 5.** No 42 program denotes a relation that is not `Σ⁰₁`.

**Where the bound comes from** is worth naming, because it is not where one might
expect. Not from reversibility, and not from any restriction on recursion — 42
has general recursion. It comes from the shape of the syntax: every combinator is
a *positive* operation, and **nothing in the language forms a complement**. A
hypothetical combinator "`t` fails here" would denote the complement of a domain
and break Proposition 4 at once. The practical consequence is that the primitive
table may be enlarged with any decidable relation and the theorem survives.

It is a small pleasure that the 1993 design excluded complement too, for a
related but distinct reason: that the complement of a finite result set in an
infinite universe is not finitely presentable. Convergent instinct, different
argument.

### 5.3 Four definable gadgets

Completeness is assembled from four constructions, each a schema indexed by a
type and each defined by structural recursion on it.

> **Lemma 6 (Discard).** For every closed `C` there is `drop_C : C <-> 1` with
> `⟦drop_C⟧ = V(C) × {()}`.

by `drop_0 = zero`, `drop_1 = id`, `drop_{A+B} = (drop_A + drop_B) ; join`,
`drop_{A×B} = (drop_A * drop_B) ; unitprod`, and a recursive definition following
`F` for `μX.F`; totality on the last is an induction on the size of the finite
tree.

This deserves a comment. `discard` is the operation the language is designed to
avoid — the rule is that nothing may be thrown away — and there is no such
primitive. It is definable anyway, and there is no contradiction: the rule is
that if a step loses information then the backward direction must be allowed to
return several candidates, and `drop!` returns all of them. **42 forbids
forgetting reversibly, not forgetting.** By contrast Theseus lists precisely this
program, `drop_var`, among its invalid expressions (§3.1).

> **Lemma 7 (Universal relation).** `univ = drop_A ; drop_B!` denotes
> `V(A) × V(B)`.

> **Lemma 8 (Filter).** For any `test : C <-> 1` with domain `U`, the term
> `copy ; (test * id) ; unitprod` denotes the partial identity on `U`.

This is how a semi-decision becomes a program, and it is also the answer to
Theseus's open question of §1.1: the filter is not a construct but a composite,
it is its own dagger for *any* test, and no restriction to a symmetric subclass
is needed.

> **Lemma 9 (Serialisation).** For every closed `C` there is `ser_C : C <-> bits`
> denoting the graph of an injective computable `e_C : V(C) → {0,1}*` whose image
> is prefix-free and decidable.

by `ser_1 = inl`, `ser_{A+B} = ((ser_A ; cons0) + (ser_B ; cons1)) ; join`,
`ser_{A×B} = (ser_A * ser_B) ; append`, and recursion for `μ`. Prefix-freeness is
the same induction: two prefixes of one string are comparable, so concatenation
of prefix-free codes is prefix-free.

The product clause is worth pausing on because it looks unsound and is not.
`append` run backwards yields **every** way to split a list — six, for the
five-bit string encoding `(1,2)` — and yet `ser_{nat×nat}` run backwards yields
exactly one, because prefix-freeness leaves only the split that decodes.
Composition restoring determinism that a factor lacks (§3.3) is here doing real
work in a proof.

### 5.4 Simulation

> **Lemma 10 (Halting).** For every deterministic Turing machine `M` there is a
> term `halts_M : bits <-> 1` with `⟦halts_M⟧ = {(x, ()) : M halts on x}`.

We assume `M` normalised to a binary alphabet, a one-way infinite tape it never
falls off, and a single halting state; all three are standard and preserve the
halting set.

**The encoding.** A tape is `bits × ((1+1) × bits)` — left reversed, head, right —
and a configuration is `conf = tape + (tape + (⋯ + tape))` with one summand per
state. The control state is a **label, not a component of a pair**: to act
differently in each state one then writes `f + g + h`, which is the sum functor
doing exactly what it is for, and no plumbing is needed to reach the state and
put it back. This one decision is what keeps the transition relation to a line.

Head movement is `right = assocprod ; ((swapprod ; inr) * id) ; (id * inr!)`,
pushing the head cell onto the left list and popping the right, and **`left` is
not written out — it is `right!`**. Reading the head is
`readhead = focus ; dist ; (unitprod + unitprod)`, and writing it is `readhead`
run backwards. For `δ(q,s) = (q', s', m)`:

```
β_{q,s}  = write_{s'} ; move_m ; tag_{q'}
δ_q      = readhead ; (β_{q,0} + β_{q,1}) ; join            δ_{q_h} = zero
step     = (δ_{q₁} + (δ_{q₂} + ⋯)) ; collapse_h
halts_M  = load ; tag_{q₁} ; step^ ; tag_{q_h}! ; drop_tape
```

**Correctness** is four lemmas. `⟦step⟧` is a partial function; it simulates `δ`
on representations; the halting state is a dead end because `δ_{q_h} = zero`; and
therefore `⟦step^⟧` is exactly the run, from which `tag_{q_h}!` selects the
halted configuration, of which minimality of the halting time gives at most one.

The one case worth keeping in full is where the finite/infinite mismatch is paid
for. A Turing tape is infinite and a value is a finite tree, so the encoding is
**many-to-one**: trailing blanks are represented by their absence. When the head
moves right off the end of the finite list, a padding branch invents a blank —
and this is correct precisely because an empty right-list forces the next cell to
be blank. Note what the simulation lemma does *not* claim: it says nothing about
`v'` being canonical. Feed it a representation with three trailing blanks and it
returns one with three trailing blanks, and since the statement is about the
*reading* of `v'`, the padding simply rides along. The mismatch costs one branch
of one definition and one case of one proof.

An instance of this construction — a three-state machine incrementing a binary
number — is in the artifact and runs.

### 5.5 Completeness

> **Theorem 11.** For closed `A`, `B` and r.e. `R ⊆ V(A) × V(B)`, some closed 42
> program denotes `R`.

*Proof.* Put `C = A × B`, so `R ⊆ V(C)`. By Lemma 9, `S = e_C(R) ⊆ {0,1}*` is
r.e., since `e_C` is a computable injection with decidable image. Take `M`
halting exactly on `S`; by Lemma 10, `test = ser_C ; halts_M` has domain `R`. By
Lemma 8, `filt = copy ; (test * id) ; unitprod` is the partial identity on `R`.
With `univ` from Lemma 7, put

```
    t  =  copy ; (id * univ) ; filt ; (drop_A * id) ; unitprod
```

and trace `x ∈ V(A)`: `copy` gives `(x, x)`; `(id * univ)` gives `(x, y)` for
**every** `y ∈ V(B)`; `filt` keeps those with `(x,y) ∈ R`; `(drop_A * id)` gives
`((), y)`; `unitprod` gives `y`. So `⟦t⟧ = R`. ∎

The shape of that argument is the point: **guess the output, then check it.** The
guess is `drop_A ; drop_B!` and the check is `copy` — both already in the
language, neither invented for the proof. An injective language cannot write the
guess at all.

> **Corollary 12 (Turing completeness).** Every partial computable
> `f : V(A) ⇀ V(B)` is denoted by some program, its graph being r.e.; and by
> Proposition 4 no program denotes anything worse.

---

## 6. Related work

**The axis.** One dial — how many answers running backwards may give — orders the
field.

| setting | `|P(y)|` | languages |
|---|---|---|
| **Groupoid**, total bijections | exactly 1 | Π |
| **PInj**, partial injections | ≤ 1 | Janus, Theseus, RFUN, Inv, Chardonnet et al., PisoLang |
| **Rel**, relations | arbitrary | **this paper** |

Almost the whole field is the middle row: reversible languages are, with near
unanimity, *injective* languages, differing in surface syntax and in how
injectivity is enforced rather than in what they denote.

**Inv** is the nearest relative and deserves generosity. Mu, Hu and Takeichi's
point-free relational setting is this one; their converse law is this law; and
their observation that undoing a duplication requires an equality test — "*`dup°`
takes a pair and lets it go through only if the two components are equal*" — is
the observation this paper makes about `copy!`, twenty years earlier. What
differs is that Inv restricts to injective functions and 42 does not.

**The Π branch.** Π's terms are the isomorphisms witnessing that "*the structure
`(b, +, 0, ∗, 1)` is a commutative semiring*", which is Figure 1 minus two rows.
The two rows are the interesting ones. Having listed the isomorphisms, *Information
Effects* names two identities that are *not* among them — `b × b ↮ b` and
`b1 + (b2 × b3) ↮ (b1 + b2) × (b1 + b3)` — and 42's `copy` and `join` are
witnesses for the first and its dual. Π does recover both, but only in an arrow
metalanguage, as **information effects** built from `create` and `erase`; `join`
there "*converts the input `b + b` to `(1 + 1) × b` and then erases the first
component*". So: **what Π must treat as an effect, requiring a type-and-effect
system and a metalanguage, this language has as a primitive** — because in Rel
those two morphisms are morphisms. Two further differences: Π is isorecursive and
pays `fold`/`unfold`, where equirecursive types pay nothing; and Π's `distrib0 :
0 ∗ b ↔ 0` is absent here, `0 × a` being uninhabited and so extensionally `zero`.

**Second-order parameters.** Theseus's parametrised maps are "*a macro or a
meta-language construction*" — "*Theseus does not have high-order maps in the
formal sense*" — and RFUN's functional parameters are "*not enough to make
functions first class citizens*". This paper's parameters are the same choice,
made independently and for the same reason. PisoLang and Chardonnet et al. nest
arrows freely, the latter listing higher-order among its contributions.

**Program inversion** is the classical ancestor: Dijkstra's `EWD671`, Gries's
*Science of Programming*, Gries and van de Snepscheut on inverting an inorder
traversal, and Chen and Udding. Where that tradition inverts a *given* program by
hand, 42 makes the inverse fall out of the syntax.

**Janus** is the imperative ancestor and the only prior language we know of that
holds local invertibility for every construct. It buys it with the assertion; we
buy it by admitting many-valued backward results. The two prices are the
alternatives this paper is really comparing, and Janus's is the more familiar
one: it is a proof obligation, discharged per program, whose failure mode is an
undefined execution rather than a rejected one.

---

## 7. Conclusion

We have presented a reversible language that declines the injectivity its
neighbours buy, and argued that the trade is favourable: inversion becomes total,
`!` leaves the abstract syntax, no progress theorem is at risk, ambiguity has a
single source, and the price is one `∈`. We have given an equirecursive type
system inferred without annotation, proved it sound in the two-sided form that a
total inversion forces, and characterised the denotable relations as exactly the
recursively enumerable ones — the same theorem the injective languages prove,
read in a larger category.

**Limitations**, stated here rather than left to reviewers.

- Nothing is mechanised; no proof assistant has seen these proofs.
- Three standard Turing machine normalisations are cited, not reproved.
- `^` is computed by naive saturation, so it terminates only on finite orbits: a
  relation can be computable in one direction and not the other, and `pred^`
  saturates where `succ^` does not.
- Backward runs can be exponential; nothing prunes the search.
- Recursion is monomorphic, Milner-style.
- Inferred types are not canonical, equirecursive types having no unique
  syntactic form.
- Parameterised definitions are eliminated by substitution, so a **recursive**
  combinator cannot be run even when it typechecks. `map f = id + (f * map f)` is
  well-typed at `(a <-> b) -> (list a <-> list b)` and its dagger is computed
  correctly, but it has no finite expansion. Interpreting application rather than
  expanding it away would close this, and nothing in the type system stands in
  the way.

**Future work.** The last limitation is the most inviting. Beyond it: the
denotable class is `Σ⁰₁` precisely because nothing forms a complement, which
suggests a principled account of what a complement-forming extension would cost —
and §3.3 identifies one thing it would buy, since the same operation is what would
lift the defining law from points to sets.

**Q42.** Rel is matrices over the Boolean semiring. Replacing 𝔹 by ℂ turns the
same terms into finite-dimensional unitaries, and the implementation shares
`Value`, `Term`, the parser, the type engine and the inversion function itself
with the classical one — `q42.dagger is rel42.dagger`. Two constructors must go,
`|` and `^`, being exactly those whose meaning needs addition to be idempotent.
That is a separate paper.

**Artifact.** An implementation with no dependencies, 363 tests, every claim in
the manual re-run by a checker, and the two figures of §2 verified against the
implementation by the test suite.

---

## References

`[AUTHORS]` To be formatted for LNCS. The full list, with the `[read]`/`[cited]`
status of each, is maintained in the project's `RELATED.md`; references are not
counted against the page limit, so the list should be given in full.
