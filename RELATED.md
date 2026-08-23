# Related work

Where 42 sits in the literature on reversible programming, and what in it is
actually new.

---

## 0. The 1993 original

42 is not a new design. It is the second instantiation of a language specified
in 1993, and enough of the present one is already in that document that the
comparisons below cannot be dated without it.

**The source.** P. G. M. Jansen, *Reversible Programming in 4₂*, Master's thesis,
University of Amsterdam (study group Robotics and Artificial Intelligence),
1993; the research carried out at Philips Natuurkundig Laboratorium and IPO
(Institute for Perception Research), Eindhoven. The language is called **4₂**,
and the preface credits it to two people:

> The result was 4₂ (pronounce: forty-two), an imperative reversible programming
> language created by Joep Rous and Paul Jansen.

**Where it came from.** The *motivation* was machine translation, not reversible
computing: the Rosetta project at Philips, and a formalism of "M-rules" for
writing natural-language grammars that had to run in both directions: parse one
way, generate the other. When Rosetta closed the language was generalised rather
than abandoned. Bidirectionality was the requirement first, and reversible
computation the frame applied afterwards.

That is about motivation only. The thesis was **not** working in ignorance of
reversible computing: its bibliography cites Landauer (1961) and Bennett (1973)
directly, alongside the program-inversion literature: Dijkstra's `EWD671`
(1978), Gries (1981), Gries & van de Snepscheut (1989), Chen & Udding (1990).
§0.4 lists what was in view.

**The name.** From Douglas Adams. Deep Thought computes the answer, forty-two,
and the question is lost; a successor machine has to be built to recover it.

> The rationale of the name 4₂ then is: if Deep Thought would have made use of 4₂
> it should have been able to compute the original question: besides generating
> the normal interpretation of a program, the 4₂ compiler generates automatically
> the inverse of a program as well.

### 0.1 What is already there

**The defining law**, as numbered equation (2.2) of chapter 2:

```
∀s₁ ∈ S_left, s₂ ∈ S_right :  s₂ ∈ Π(s₁)  ⟺  s₁ ∈ Π⁻¹(s₂)
```

> This formula says that every end state which is the result of a program
> execution in one direction, results in a set of states containing the original
> start state if it is executed in the other direction.

In 42 that same law is written `x ∈ P(y) ⟺ y ∈ inv(P)(x)`, and glossed the same
way: running forward and then backward returns a set *containing* where you
started. Both the statement and the gloss are already 1993's.

**The contravariance of inversion**, as a definition rather than an
implementation detail. An operator `⊙` is called *syntactically reversible* when

```
∀(R₁,…,Rₙ) ∈ D_⊙ :  (⊙(R₁,…,Rₙ))⁻¹ = ⊙(Rₙ⁻¹,…,R₁⁻¹)
```

> A simple example of a syntactically reversible operator is the sequence
> operator ";". The inverse interpretation of the construct "R₁ ; R₂" is
> "R₂⁻¹ ; R₁⁻¹" which is exactly the same as reading the construct from right to
> left.

which is `case Seq(s, u): return Seq(dagger(u), dagger(s))` in `rel42/core.py`.

**Nondeterminism, accepted rather than excluded.** From §3.1, on inverting a
function applied to an uninstantiated argument:

> The fact that the inverse function is a set containing possibly more than one
> value makes the whole process indeterministic.

and failure is emptiness, not error:

> Failure of a transformer implies more or less that the environment of the
> transformer will produce an empty set of output states.

**The operators.** Sequence, union `|`, intersection `&`, repetition `{R}`, test
`R?`, relation call, with the lineage named:

> This enumeration defines the so called class of regular relations extended with
> an intersection operator and a possibility to do tests. In modal logic it
> resembles the system of Pratt as described in [Pratt80] and [Harel84].

So 42's `;`, `|` and `^` are all 1993, `|` down to the character, and repetition
is already reflexive-transitive closure — "the set of output states contains all
states generated in between, including the original input state", with the
backward asymmetry of `pred^` versus `succ^` noted in the same paragraph.

**Decidable atoms and no complement.** Atomic relations are defined by a formula
of a decidable language (§2.2), and complement is deliberately absent:

> the complement operator which corresponds with the logical negation at the
> level of complex relations is not implemented. The reason for this is the
> requirement of finiteness of result

Those are the two ingredients of the [expressiveness theorem](THEOREM.md)'s
soundness proof: decidable
primitives, and only positive operators over them. The 1993 reason is not the
2026 reason: theirs is that a complement in an infinite universe is not finitely
presentable, mine is that it leaves Σ⁰₁. Convergent instinct, different argument.

### 0.2 What is not there

**The point-free core.** 4₂ is imperative, and says so. It has variables
(topics, state variables, match variables) and its atomic construct is
assignment-shaped, `topic := t₁ ! t₂`, with the two terms read in opposite
orders depending on direction. There are no `0, 1, +, ×` primitives, no semiring
isomorphisms, and nothing resembling a rig groupoid. §6's claim that 42's
primitives are *forced rather than chosen* is therefore a claim about the second
instantiation only, and must not be back-dated.

The `!` did survive, but with a changed job: in 4₂ it separates the preterm from
the postterm, marking where the two readings meet. In 42 it is the operator that
swaps them.

### 0.3 The open problem, and what 42 does with it

Having defined syntactic reversibility, the thesis finds its own constructs
failing it. Of the conditional:

> It is easy to see that the "IF-THEN" construct we described above is not
> syntactically reversible.

and of the boolean test, which is implemented by copying the state, evaluating,
and returning the copy on success:

> An awkward consequence of this particular evaluation is the loss of syntactical
> reversibility … The boolean operator "?" could be made syntactically reversible
> by allowing only the subclass of symmetrical programs of 4₂ in boolean tests.
> Whether we loose expressiveness by restricting boolean tests to symmetrical
> programs is still an open question.

**42 is the language in which every operator is syntactically reversible**, and
that is what going point-free buys. There is no conditional to fail the property,
because branching is `+`; and there is no test operator, because filtering is the
composite `copy ; (test * id) ; unitprod`. That is the theorem's Lemma 5, and
it is its own dagger for *any* test, with no restriction to symmetrical
programs:

```
$ 42 theorem keep "R ()"
keep(R ()) =
  R ()
  -- 1 result
```

```
$ 42 theorem keepd "R ()"
keepd(R ()) =
  R ()
  -- 1 result
```

The expressiveness half of the 1993 question is settled by the theorem's Theorem
12: filters of exactly this shape reach every r.e. subset, so nothing is lost by
having no primitive test at all. Intersection goes the same way: 4₂'s `&` is
`copy ; (f * g) ; copy!`, running both and insisting the answers agree, so the
operator was absorbed rather than dropped.

Because `dagger` is total on every construct, `!` can be eliminated at parse time,
which is the syntactic form of the 1993 property:

```
parse("(copy ; join)!")  ==  parse("join! ; copy!")
```

### 0.4 What was in view in 1993

The thesis's bibliography answers a question this document would
otherwise have to guess at: what a designer in 1993 could see. Five groups.

- **Thermodynamics and reversible computation.** Landauer, *Irreversibility and
  Heat Generation in the Computing Process* (1961), and Bennett, *Logical
  Reversibility of Computation* (1973). Both cited directly. Whatever else is
  true, 4₂ was not designed in ignorance of the field.
- **Program inversion, and a Dutch one.** Dijkstra, *Program inversion*
  (`EWD671`, Eindhoven, 1978); Gries, *The Science of Programming* (1981); Gries
  & van de Snepscheut, *Inorder traversal of a binary tree and its inversion*
  (1989); Chen & Udding, *Program Inversion: more than fun!* (1990). This is a
  tradition the rest of this document does not mention at all, and it is the
  closest thing to a direct ancestor: inverting a *given* program by hand, where
  4₂ and 42 make the inverse fall out of the syntax.
- **Relational and modal semantics.** Pratt (1980), Harel (1984), Plotkin's
  powerdomain construction (1976). §0.1's operators come from here.
- **Denotational semantics as a craft.** Stoy (1977), Gordon (1979), Schmidt
  (1986), Watt (1991): four textbooks, which is what a thesis with two chapters
  of formal semantics in it looks like from the outside.
- **Rosetta and compilers.** Landsbergen's *M-Rules* (1985) and *Control
  Expressions* (1986), Leermakers (1986), Appelo & Landsbergen (1986), Odijk
  (1991), Augusteijn's ELEGANT compiler generator, and the dragon book.

Notably absent: Lutz & Derby's Janus (1986). It was invisible until Yokoyama &
Glück revived it in 2007, and its absence here is direct evidence of that.

And one entry that is not a source but a plan, the last one alphabetically
before Schmidt:

> Rous, J. and Jansen, P.G.M., *Reversible Programming in 4₂*, forthcoming.

That is the thesis's own title, under two names instead of one. The bibliography
contains a forward reference to the paper the thesis was meant to become: same
work, joint authorship, submitted nowhere. It did not appear.

### 0.5 A note on citing this

The thesis exists on paper only. The quotations in §0 were transcribed from page
images. The pages were read in full, but unlike `inv.pdf` and `pisolang.pdf`
the scan carries no text layer, so
`tests/test_docs.py::TestRelatedWorkQuotations` cannot check them mechanically.
Treat them as hand-transcribed. What has been read is the preface, chapters 2 and
3.1–3.5, and the bibliography; chapters 4 and 5, which carry the formal syntax
and semantics, have not.

---

## 1. The axis everything sits on

Every language here can be placed by how many answers running backwards may
give:

| Setting | `\|P(y)\|` | Languages |
|---|---|---|
| **Groupoid** — total bijections | exactly 1 | Π; **Q42** (unitaries) |
| **PInj** — partial injections | ≤ 1 | Janus, Theseus, RFUN, **Inv**, Chardonnet et al., PisoLang |
| **Rel** — relations | arbitrary | **42** |

The middle row holds almost every language in the field. Reversible languages
are, with near-unanimity, *injective* languages; they differ in surface syntax
and in how injectivity is enforced rather than in what they denote.

42's position is the bottom row, and its thesis is that the bottom row has the
simpler metatheory. Q42 is the top row, and reaches it by changing the semiring
rather than by adding restrictions.

---

## 2. Inv — the nearest relative

Mu, Hu & Takeichi, *An Injective Language for Reversible Computation*, MPC 2004.

Inv is 42's closest predecessor. PisoLang's related-work section describes it
as follows:

> Mu et al. present Inv, an injective language for reversible computation
> formulated in a point-free, combinator-style functional setting with a
> relational semantics.

Which is 42's design space, described by someone else, in 2004. Inv is a
point-free functional language with a *relational* semantics in which only
injective functions are definable; non-injective computations are accommodated by
returning a history, and it is computationally equivalent to Bennett's reversible
Turing machines.

**The defining law is the same equation.** Inv, §2:

> The converse of a relation `R`, written `R°`, is obtained by swapping the pairs
> in `R`. That is, `(b, a) ∈ R° ≡ (a, b) ∈ R`.

42:

> `x ∈ P(y) ⟺ y ∈ inv(P)(x)`

These are the same statement. 42's law is a restatement of the converse of a
relation, not a new formulation.

**The inversion rules are the same rules.** Inv gives:

```
(f ; g)° = g° ; f°        (f × g)° = f° × g°
(f ∪ g)° = f° ∪ g°        (µF)°    = µ(° ; F ; °)
```

and 42's `dagger` is, line for line:

```python
case Seq(s, u):   return Seq(dagger(u), dagger(s))
case Prod(s, u):  return Prod(dagger(s), dagger(u))
case Union(s, u): return Union(dagger(s), dagger(u))
case Ref(n, i):   return Ref(n, not i)
```

**`copy`/`copy!` is `dup`/`eq`, and the observation about them is the same
observation.** Inv, §2:

> `dup° = fst ∩ snd`. Given a pair, `fst` extracts its first component, while
> `snd` extracts the second. The intersection means that the results have to be
> equal. That is, `dup°` takes a pair and lets it go through only if the two
> components are equal. That explains the observation that to "undo" a
> duplication, we have to perform an equality test.

42's primitive table: *"`copy`, the diagonal `a → a×a`; its converse is the
partial 'these agree'."* The fact and its framing are Inv's, from 2004.

Three languages solve it three ways, and the third is the most ingenious. Inv
has `dup` and `eq` as separate constructs with `eq = dup°`. 42 has one primitive
`copy` whose dagger is partial. RFUN has one operator `⌊·⌋` that is
*total and self-inverse*, because it answers the equality question in the arity
of its result:

```
⌊⟨x⟩⌋    =  ⟨x, x⟩
⌊⟨x, y⟩⌋ =  ⟨x⟩      if x = y
            ⟨x, y⟩   if x ≠ y
```

> Thus, if the input is a binary tuple we can discern from the arity of the
> result tuple whether the arguments were equal or not; and if the input is a
> unary tuple, the result is a duplication of the value.

RFUN pays no partiality at all here, where 42 pays it in `copy!` and Inv in
`eq`. That is worth recording as a case where the injective setting produces the
neater construct rather than the clumsier one.

**Where 42 differs from Inv.** Three differences. The first two are trade-offs
in expressiveness; the third is the one §6 claims as new.

1. *Inv restricts to injective functions; 42 does not.* Inv's whole discipline is
   "injectivity by construction": the problematic constructs of its ambient
   language `Fun` (constant functions, `fst`, `snd`, the split) are replaced by
   more structured ones. 42 admits the whole of Rel and takes the many-valued
   dagger as a feature.
2. *Inv's `dup`/`eq` are parameterised families; 42's `copy` is one primitive.*
   Inv's `dup :: (Fa → a) → Fa → (Fa × a)` takes a selector argument, and Inv
   also has a primitive `neq`. In 42 selection is done by composition and there
   is no inequality test at all, which is simpler and less expressive.
3. **Inv's primitive set is chosen; 42's is forced.** Inv has `swap`, `assocr`,
   `dup`, `eq`, `neq`, and constructors `succ | cons`; `assocl` is derived rather
   than primitive. Its core carries no coproduct, no `dist` and no unit
   isomorphisms. Sum types arrive only in §6, as `inl`/`inr`/`unit`/`in`
   introduced for the history-logging translation, with the core deferring them
   (*"some more operators will be introduced in sections to come to deal with the
   sum type, trees, etc."*). 42's primitives are exactly the isomorphisms
   witnessing the commutative-semiring structure of `(0, 1, +, ×)`, which is to
   say a *rig groupoid presentation*, which is to say Π. That is what makes the
   primitive table forced rather than curated, and it is what makes the Q42
   extension of §5 possible: Inv cannot be taken to ℂ by the same route, because
   the rig structure the two new generators attach to is not present in its
   core.

---

## 3. The disjointness condition, six ways

The same condition appears in six languages here and is discharged six different
ways, which locates 42 more precisely than any other single comparison.

Inv, §4 — *assumed, and flagged as unexplored*:

> An extra restriction needs to be imposed on union. To preserve reversibility,
> in `f ∪ g` we require not only the domains, but the ranges of `f` and `g`, to
> be disjoint. **The disjointness may be checked by a type system, but we have
> not explored this possibility.**

The condition costs Inv a primitive. Its inequality test `neq p₁ p₂` is a partial
function that lets `(x, y)` through only when `p₁ x ≠ p₂ y`, and its stated
purpose is that *"it is sometimes necessary for ensuring the disjointness of the
two branches of a union."* So one of Inv's twelve constructs exists to discharge a
proviso 42 does not have.

PisoLang, `I-Case` — *the same condition, now statically checked*.
Its typing rule for a case-expression carries two premises beyond the types:

```
∀i ≠ j,  pᵢ ⊥ pⱼ        (the patterns do not overlap)
∀i ≠ j,  eᵢ ⊥ eⱼ        (the output expressions do not overlap either)
```

with orthogonality defined as `p₁ ⊥ p₂ ⇔ σ(p₁) ≠ σ(p₂)` for every substitution
`σ`, decided by unification: the type system Mu et al. left unexplored.

Theseus — *the same condition, on both sides, as the language's only
rule*. §3.1 states it as the single constraint a programmer must maintain:

> **Non-overlapping and exhaustive coverage in pattern clauses.** The collections
> of patterns in the left-hand side (LHS) of each clause must be a complete
> non-overlapping covering of the input type. Similarly, the collections of
> patterns in the right-hand side (RHS) of each clause must also be a complete
> non-overlapping covering of the return type.

Chardonnet, Lemonnier & Valiron — *the same condition again, with
exhaustivity dropped*. Non-overlap is kept and made formal as an orthogonality
relation `v₁ ⊥ v₂` decided structurally, appearing as two premises `∀i ≠ j, vᵢ ⊥
vⱼ` and `∀i ≠ j, eᵢ ⊥ eⱼ` in the typing rule for an iso; exhaustivity goes,
deliberately, "*in order to allow non-terminating behaviour*". So within one
lineage the condition survives on both sides while totality is given up, which
is a useful data point for how load-bearing each half is.

RFUN — *the same condition, relaxed into an ordering*. Thomsen &
Axelsen name it as one of the two ways irreversibility enters their irreversible
source language:

> **Non-orthogonality of case-branches.** Slightly more subtle is the issue that
> case branches may be non-orthogonal: the result might conceivable have come
> from several branches, i.e., match several of the left-expressions terminating
> the case branches. This is the functional variant of the problem of the general
> irreversibility of if-then-else constructs.

and RFUN's answer is not to forbid overlap but to order it:

> A **first match policy** for case branches. The result of a case-expression
> branch may match several terminating left-expressions, but it must never match
> a branch that textually precedes it.

which is a third option: neither assumed nor statically decided, but made
harmless by fixing which branch wins. Note the connection RFUN draws and
Theseus draws independently: this is *if-then-else*, and it is the same construct
the 1993 thesis found violating its own definition of syntactic reversibility
(§0.3). Four languages, one conditional.

Janus — *the same condition, discharged by the programmer*. Yokoyama
& Glück formalise the language and are exact about the mechanism:

> A reversible conditional has two predicates: the predicate after `if` is the
> test, and that after `fi` is the assertion. If the test is true, the
> then-branch is executed and afterward the assertion must be true; if it is
> false, the conditional is undefined. … The assertion makes the conditional
> reversible.

The loop is symmetric, and the cost is stated as plainly: "*If the assertion does
not have the required value, execution of the loop is undefined.*" So Janus does
not decide the condition, nor assume it, nor order it. It obliges the programmer
to supply a predicate that makes backward flow deterministic, and undefines the
program when the predicate is wrong.

One further point is sharper than the usual summary of Janus allows, and it
bears directly on §6. Janus does **not** require its operations to be injective:

> The evaluation of expressions is not backward deterministic because function
> `[[⊙]]` is not injective, and thus there exists no inverse. As we shall see,
> this does not harm the backward and forward determinism of Janus statements.

Injectivity is demanded of *statements*, not of the arithmetic, and the syntactic
restriction that `x` may not occur in the right-hand side of `x ⊕= e` is what
buys it. Janus and 42 therefore agree that non-injective operations are
admissible and disagree about where to pay for them: Janus pays in a restriction
on assignment plus an assertion per conditional, 42 pays in the `∈`.

**42 has no such condition.** `join!` keeps both branches, so nothing needs to be
disjoint, and `dagger` is total with no side conditions, no well-formedness
checks, and no proof obligations. The price is paid in exactly one place: the `∈`
in the defining law, which is to say that forward-then-backward returns a set
*containing* where you started rather than where you started.

Stated as a progression, and now datable: **dropped (4₂, 1993) → assumed (Inv,
2004) → made the only rule (Theseus, 2014) → kept but shorn of exhaustivity
(Chardonnet et al., 2024) → checked statically (PisoLang, 2026)**. That is not the order of a fix
being found; it is three different answers, and the earliest is the one that
declines the question. §0 gives the 1993 evidence: the defining law is stated
there with the `∈` already in it, and nondeterminism is called a consequence to
be accepted rather than a condition to be excluded.

This is a claim about the design space, not a claim of superiority. Inv and
PisoLang want injectivity and must therefore pay for it; 4₂ and 42 want something
weaker and do not.

---

## 4. PisoLang

Onodera, Nakano, Asada & Kikuchi, *PisoLang: a User-Friendly Reversible
Programming Language with Inductive Types*, RC 2026.
Implementation: `github.com/42067/reversible_lang`.

An ML-style surface language over the reversible core calculus of Chardonnet,
Lemonnier & Valiron, itself descended from Theseus. Its goal is
usability, and the surface language supplies it: algebraic data types with user-defined
constructors, OCaml-style pattern matching, Hindley–Milner inference so functions
are polymorphic by default, higher-order functions over isos, nested patterns and
nested applications elaborated to an invertible let-normal form.

Its `add` is 42's padding trick, arrived at independently:

> The function `add` … takes two natural numbers `m` and `n` and returns a pair
> `(m + n, n)` **in order to make the function injective**.

42 makes the same trade in `mul : (m, n) → (n, m×n)`, where keeping the
multiplier costs one component and buys injectivity. Same move, same reason.

**Where 42's generality earns something.** Beyond the disjointness condition of
§3:

- *No padding for `add`.* PisoLang's `add : nat*nat ↔ nat*nat` must keep `n`;
  42's `add` returns the sum alone, because `add!` is permitted to enumerate all
  six preimages of 5. This does not generalise as far as it first appears.
  PisoLang's `len : 'a list ↔ nat * 'a list` must return the list, and so must
  any 42 version, because forgetting the elements needs `discard`, which 42
  omits. The advantage is real for `add` and absent for `len`.
- *No failure of progress.* PisoLang's Example 2.6 exists to record that
  `(case True ↔ ()) False` is well-typed but **stuck**, so progress does not hold.
  In 42 that term denotes `∅`, a legitimate morphism of Rel, and there is no
  theorem to weaken. In 42, partiality is not failure, which is the same point.
- *No linearity.* PisoLang types expressions in a **linear** context, and says so:
  *"the rules for expressions treat `∆` as a linear context, and that isos are
  typed without `∆`; these aspects contribute to the reversibility of isos."* It
  then has to carve out "controlled non-linear use of variables" to recover
  duplication. 42 has no variables, so there is no linear discipline to impose
  and no exception to carve.
- *`copy` and `copy!` are one primitive and its dagger.* PisoLang needs two
  separate syntactic affordances, repeated variables in *expressions*
  (duplication) and repeated variables in *patterns* (equality constraints),
  and remarks that the latter *"is hard to express, despite being the inverse of
  duplication"*. In 42 that inverse relationship is structural. This is the same
  point Inv makes about `dup`/`eq`; PisoLang is where it costs something.

**Where PisoLang is more expressive.**

- **Higher-order over isos, inferred.** `map : ('a <-> 'b) -> ('a list <-> 'b list)`
  and `run_length : ('a * 'a <-> bool * ('a * 'a)) -> ('a list <-> ('a * nat) list)`.

  42 closes part of this with parameterised definitions:
  `def ctrl m = mat ; (id + m) ; mat!` is inferred as
  `(a <-> a) -> (qubit x a <-> qubit x a)` with no annotation. Two differences
  remain. 42's is deliberately **second-order**: a parameter denotes
  a relation, never another combinator, where PisoLang's `T₁ → T₂` nests freely.
  And 42's inversion convention differs: PisoLang fixes variables under
  inversion (`ϕ⁻¹ := ϕ`) and inverts an application's argument, while 42 flips
  the variable and leaves the argument alone. Either way it is a matched pair,
  but 42 needs its version because `!` is eliminated at parse time, so a variable
  without its own flag would make `m!` and `m` parse identically.

  **On `map`, this document was wrong, and the truth is more specific.** It is
  not that a parameter cannot be applied to a list. `map` is *writable and
  well-typed* in 42: a list is already a sum, so the sum functor does the case
  split with no plumbing at all:

  ```
  def map f = id + (f * map f)
  ```

  inferred as `(a <-> b) -> (mu X. c + a x X <-> mu Y. c + b x Y)`, which is
  `(a <-> b) -> (list a <-> list b)`, the very scheme PisoLang's `map` has. Its
  dagger is computed correctly too: `42 show` prints `map! not` for the inverse
  of `map not`.

  What fails is *evaluation*, and for a reason that is about the elimination
  strategy rather than about types or arity. Parameterised definitions are
  removed by substitution before evaluation, which is what `expand` does and why
  neither evaluator has a case for an application, and a **recursive**
  combinator has no finite expansion. Running `map not` reports `application
  depth exhausted; is a combinator recursive?`, and raising the limit does not
  help, because the divergence is in the expansion and so independent of the
  input.

  So the honest statement of the gap: 42 admits recursive combinators in its
  type system and rejects them in its reduction strategy. Interpreting `App`
  rather than expanding it away would close this, and nothing in the type system
  stands in the way.
- **Nominal ADTs dissolve the `0`/`[]` collision.** `type nat = Z | S of nat` and
  `type 'a list = Nil | Cons of 'a * 'a list`. Because `Z` and `Nil` are
  different constructors, the ambiguity that 42 addresses with type-directed
  printing cannot arise.
- **Turing-completeness demonstrated**, via a reversible Turing machine encoding.
  42 has no such result.
- **Readability**, the paper's stated thesis, and supported by the surface
  syntax above.

**The type systems, side by side.** 42's checker is close enough in kind to
invite direct comparison:

| | PisoLang | 42 |
|---|---|---|
| Algorithm | algorithm W, constraints + unification | the same |
| Recursive types | **nominal**, user-declared, standard occurs check | **inferred equirecursive**, no occurs check |
| Inversion | an `Inverted` type former, normalised during unification | `Scheme.swap()` at the point of use |
| Annotations | none required, but types are *declared* | nothing is written at all |
| Verified | no — *"the algorithm for type inference needs to be verified"* | no |

The inversion row records a simplification specific to the point-free
setting.
PisoLang's `unify_type` must handle cases like
`Inverted i, BiArrow{a,b} → (i, BiArrow{b,a})`, because `inv ω` is a term whose
type must be deferred. In 42, `!` is eliminated at parse time, so inversion never
enters the type language.

The recursion row is the conventional choice against an unconventional one and
neither is better. Theirs means the programmer writes `type nat = Z | S of nat`;
42's means nobody writes anything and `μX. 1 + X` appears because unification
closed a loop.

---

## 5. The Π branch, and Q42

### 5.0 Π, exactly

A second line descends from Theseus. James & Sabry's **Π** is a
reversible language whose terms are the isomorphisms witnessing a
commutative-semiring structure, which is 42's primitive table, arrived at
independently.
Two things need saying precisely, because the loose version of this claim is
wrong.

**Which Π.** *Information Effects* (POPL 2012) gives `Π` with

```
value types, b ::= 1 | b + b | b × b
```

— **no `0`**, and six isomorphism pairs: `swap+`, `assocl+/assocr+`,
`unite/uniti`, `swap×`, `assocl×/assocr×`, `distrib/factor`. The zero arrives
with `Πo`, whose table is given in full in *Theseus* §2: types
`0 | 1 | b + b | b ∗ b | x | µx.b`, and additionally `zeroe/zeroi : 0 + b ↔ b`,
`distrib0/factor0 : 0 ∗ b ↔ 0`, and `fold/unfold`. Of that presentation Theseus
says exactly what this document has been saying of 42:

> Collectively the isomorphisms state that the structure `(b, +, 0, ∗, 1)` is a
> commutative semiring.

**The correspondence, term by term.** Against `Πo`:

| `Πo` | 42 |
|---|---|
| `zeroe/zeroi`, `swap+`, `assocl+/assocr+` | `unitsum`, `swapsum`, `assocsum` |
| `unite/uniti`, `swap∗`, `assocl∗/assocr∗` | `unitprod`, `swapprod`, `assocprod` |
| `distrib/factor` | `dist` |
| `distrib0/factor0 : 0 ∗ b ↔ 0` | **absent** — `0 × a` is uninhabited, so it is extensionally `zero` |
| `fold/unfold` | **absent** — types are equirecursive, so there is nothing to write |
| `id`, `sym`, `#`, `+`, `∗` | `id`, `!`, `;`, `+`, `*` |
| `trace` | — |
| — | `zero`, `inl`, `inr`, `copy`, `join`, `\|`, `^` |

Two rows are the whole difference. `fold`/`unfold` are the isorecursive tax 42
does not pay. And the last row is 42 leaving the groupoid.

**The last row is not arbitrary.** *Information Effects* §3.1, having listed the
isomorphisms, names the two identities that are *not* among them:

> ```
> b × b            ↮   b
> b1 + (b2 × b3)   ↮   (b1 + b2) × (b1 + b3)
> ```

and 42's two extra primitives are witnesses for precisely the first of these and
its dual: `copy : a ↔ a × a` and `join : a + a ↔ a`. What is more, Π *does*
recover both, but only in the arrow metalanguage `MLΠ`, as **information
effects** built from `create` and `erase`. `clone` is Lemma 7.2 there; `join` is
defined as

> We define an operator `join : b + b ⇝ b` that takes a value of type `b` tagged
> by either `left` and `right` and removes the tag. The definition converts the
> input `b + b` to `(1 + 1) × b` and then erases the first component.

So the position is sharp, and it is the same one §3 reaches from the other
direction: **what Π must treat as an effect, requiring a type-and-effect system
and a metalanguage, 42 has as a primitive**, because in Rel those two morphisms
are morphisms, and the price is paid once, in the `∈` of the defining law, rather
than per-use in an effect system.

### 5.1 √Π and the quantum branch


Carette, Heunen, Kaarsgaard & Sabry, **√Π** (POPL 2024), prove that a
rig groupoid extended with **two maps and three equations** is computationally
universal for quantum computing, and equationally sound and complete for
Clifford, ≤2-qubit Clifford+T, and Gaussian Clifford+T. The maps are an 8th root
of the identity on the unit and a square root of the symmetry on `1 + 1`. Q42
is 42 taken to ℂ along exactly this route, and `q42/` implements it.

### 5.2 Two routes from a rig groupoid to quantum

*The Quantum Effect* is the other half of this branch, by overlapping
authors, and it reaches universal quantum computation from Π by a completely
different road than √Π does. Setting the two side by side is the sharpest thing
this document can say about where Q42 sits.

**QuantumΠ layers effects.** It takes *two* copies of Π, `Π_Z` and `Π_φ`, rotated
with respect to each other, amalgamates them with an arrow so their expressions
interleave, layers a second arrow introducing a state `zero` and an effect
`assertZero`, and then **imposes the complementarity equation**. The payoff is
their canonicity theorem: satisfying the classical-structure laws, the execution
laws and complementarity is *enough* to force computational universality. The
The argument is short: `arr_φ swap+` must be involutive, being the lifting of a
symmetry, which rules out `SH` and leaves Hadamard.

**Q42 changes the semiring.** One copy, no arrows, no imposed equation:
reinterpret the same terms over ℂ instead of 𝔹 and adjoin √Π's two generators.

Three consequences of the difference are worth recording.

- **Different categories.** QuantumΠ's model is one of *partial* maps. The paper
  says so explicitly, "the model of QuantumΠ
  is one of partial maps (whereas the model of UΠ𝑎 is one of total maps)", and Fig. 1 lands it in
  **Contraction**, finite-dimensional Hilbert spaces and linear contractions. Q42
  stays in **Unitary**. That is the formal content of Q42's refusal to add
  measurement as a term (QMANUAL §9.2): the moment `zero`/`assertZero` exist, you
  have left the unitary category.
- **Both lose the additive structure, for different reasons.** In QuantumΠ, "the
  semantics of the additive structure is however not lifted to the amalgamated
  language", so the arrow layer keeps only `×`. In Q42, `|` and `^` go because
  their meaning requires addition to be idempotent. Same casualty, unrelated
  causes, which is a suggestive coincidence rather than a theorem.
- **Measurement is derived there, absent here.** QuantumΠ obtains it by layering
  *hiding* on top: `measure_Z = copy_Z ≫ fst`, where `fst` needs `discard`. The
  authors are candid that their Agda `discard` "is dangerous, as it does not
  enforce that it is only applied to total maps". Q42 has terminal measurement
  outside the language and no `discard` at all.

One item of their future work is directly Q42's territory: extending QuantumΠ
from finite Π to `Πo` with a trace operator, which they judge "would require
answering fundamental open questions about the nature of infinite-dimensional
quantum computation". Q42 meets the same wall from the other side and gets a
sharper, more elementary statement of it: closure is a least fixed point wanting
`1 + 1 = 1`, so it cannot survive the move to ℂ at all.

### 5.3 Control and the rig structure are the same thing

*One rig to control them all* answers a question this document had
been posing loosely, whether Q42's `ctrl` should be primitive or derived, and
the answer is that the question dissolves. Heunen, Kaarsgaard and Lemonnier give
**seven** equations for control (not eight, as this document previously said from
its abstract), and prove that adding them to a prop of base circuits constructs
the *free rig category* on that prop. Their title claim, stated in the
introduction:

> These results also substantiate the claim in the title, that rig structure
> encapsulates controlled computation, and only controlled computation. Thus rig
> categories form the bare minimum model of computation: the ability to compose
> instructions sequentially (with ∘), to consider data in parallel (with ⊗), and
> to use one piece of data to condition computations on another (using ⊕).

So control and rig structure are interderivable, and 42 and their construction are
the two directions of one correspondence. **42 takes the rig structure as
primitive, which is what its primitive table is, and derives `ctrl` from `dist`
in one parameterised definition. They take control as the added theory and derive
the rig.** Neither is more fundamental; what differs is which end you build from.

Two consequences are worth carrying into Q42's paper.

**Their Theorem 27 is about Q42's generators.** Taking the prop generated by
`ω : 0 → 0`, `V : 1 → 1` and `S : 1 → 1` with `ω⁸ = id`, `V⁴ = id` and
`SVS = VSV`, forming its controlled prop and quotienting by `S = ω²`, they obtain
soundness and completeness for Clifford, ≤2-qubit Clifford+T and Gaussian
Clifford+T: the same three fragments √Π covers, and the same generators `q42/`
implements. Their proof notes that √Π's results needed only `ω⁸ = id`,
`V² = γ₁,₁` and `SVS = VSV`, "as well as the axioms of rig categories, which are
implied by the control equations". Q42 has those axioms as primitives, so it sits
on the other side of that implication.

**There is a no-go theorem, and 42's parameters step around it.** They note that
"there is no quantum circuit implementation of a controlled unitary where the
unitary is a black box input", and that physical implementations bypass it by
identifying subspaces with auxiliary dimensions. Q42's `ctrl` is not troubled by
this, and the reason is a design decision made for unrelated motives: a parameter
in 42 denotes a **term**, not a value, and applications are eliminated by
substitution before evaluation (§4). `ctrl m` never receives a black box; it
receives syntax, and expands. The second-order restriction that §7 records as a
*limitation* is what keeps `ctrl` on the right side of a no-go theorem.

Their future work also touches Q42's: the control equations "implicitly assume
only two possibilities on each wire" and they ask about qutrits, which is
QMANUAL §9.4's register-width question from the other direction, since `1 + (1 +
1)` is a perfectly good Q42 type and a perfectly bad qubit register.

Note that **Lemonnier** appears on both branches, as an author of PisoLang's
semantic basis and of *One rig*, so the two lines are not as separate as their
citation graphs suggest.

PisoLang has no quantum content, so §4's comparison and this section concern
disjoint parts of the design space.

---

## 6. What is actually new in 42

§2 and §3 establish that much of 42 is not new. This section separates the
remainder.

**Not new.** The point-free relational setting; the defining law
`x ∈ P(y) ⟺ y ∈ inv(P)(x)`; the contravariant inversion rules; the observation
that undoing duplication is an equality test; the padding trick for injectivity.
All of this is Inv (2004), and some is older.

**New, or at least not found elsewhere:**

1. **Making every operator syntactically reversible**, so that the metatheory
   is *simpler* rather than more complicated: `dagger` is total, needs no side
   conditions, and satisfies `dagger(dagger(t)) == t` syntactically. Be careful
   what is being claimed. Dropping the disjointness condition is **1993**, not
   new here, and neither is the property itself, which has been named
   independently at least three times:

   | | name | formulation |
   |---|---|---|
   | 4₂, 1993 | *syntactic reversibility* | `(⊙(R₁,…,Rₙ))⁻¹ = ⊙(Rₙ⁻¹,…,R₁⁻¹)` |
   | Janus, 2007 | *local invertibility* | "*for any given program unit the inversion can always produce an inverse unit*" |
   | Theseus, 2014 | *syntactic reversibility* | the inverse reading coincides with the inverse meaning |

   All three give sequential composition as the worked example and all three get
   the contravariant law: Janus as `(s₁ s₂)˘ ∼ s̆₂ s̆₁`, 4₂ and Theseus as the
   displayed equation. Where they differ is what it costs to hold it everywhere.
   Janus holds it, and pays with a programmer-supplied assertion on every
   conditional, undefining the program when the assertion is wrong. Theseus does
   not hold it: its own conditional and its own boolean test fail, and the repair
   is left open. 4₂ does not hold it either, for the same reason.
   What is new is holding the property everywhere **without** either price:
   no assertion for the programmer to discharge, and no construct excluded.
   Going point-free is the repair. There is no conditional, because branching is
   `+`, and there is no test operator, because filtering is a composite of
   `copy`. The README states the consequence as *"dropping restrictions is what
   buys the elegance here"*. The claim is about metatheory, not expressive
   power.
2. **A primitive set that is forced rather than chosen.** Inv's primitives are
   curated; 42's are the semiring isomorphisms and nothing else, with `copy` and
   `join` named as precisely the two morphisms that make the setting Rel rather
   than a groupoid. The generating set coinciding with Π's is evidence it is the
   right one. Unlike (1) this cannot be back-dated: 4₂ is imperative and has no
   such primitives (§0.2).
3. **Equirecursive types inferred rather than declared**, with the occurs-check
   failure read as a *diagnosis*: `μX. F(X)` is admitted when `F(0)` is
   inhabited and rejected when it is not. `(inr!)^` is therefore accepted at
   `mu X. a + X`, which is `nat` when `a = 1`, while `copy^` is rejected, with the
   occurs check reported as the reason: `X would have to equal X x X`. No language here does this; all of them declare their inductive types.
4. **The quantum extension being a semiring change rather than a new language.**
   `q42/` shares `Value`, `Term`, `dagger`, the parser and the entire
   type-inference engine with `rel42/`; only the primitive table and the
   evaluator differ. `q42/classical.42` runs under both interpreters unmodified.
   This is a consequence of (2): the rig structure is what the two generators
   attach to.

**Caveat on (1).** Inv, PisoLang, Theseus and RFUN all *want* injectivity,
and pay for it deliberately. 42 wants something weaker, so it is not paying a
cost they failed to avoid. The right claim is that the weaker setting is
underexplored and better behaved, not that the others made a mistake.

---

## 7. What 42 lacks that the others have

- **Full higher-order.** 42's parameterised definitions are second-order only: a
  parameter denotes a relation, so a combinator cannot be passed to a combinator.
  PisoLang and Chardonnet et al. nest arrows freely, the latter listing
  higher-order among its contributions, "*features higher-order (unlike [7])*",
  which is what `map` needs. See §4.

  **Theseus does not**, and this document said otherwise until the paper was
  read. Its parametrised maps look higher-order and are not:

  > This parametrization should be thought of as a macro or a meta-language
  > construction. Theseus does not have high-order maps in the formal sense. In
  > other words, the final type of a Theseus program must be of the form `a ↔ b`
  > and every occurrence of an arrow type `→` must be instantiated at compile
  > time.

  > While parametrized maps add tremendous programming convenience to Theseus,
  > they don't change the expressive power of the language. All programs
  > expressible with parametrized maps, can be expressed without them by fully
  > inlining the actual parameters.

  **RFUN does not either**, and says so in the same words. Its functional
  parameters are described as "*not enough to make functions first class
  citizens*", yet "*sufficient to implement certain very useful higher-order
  functions such as (reversible) map*".

  So three languages, Theseus, RFUN and 42, independently chose second-order
  parameters and independently described them as not-first-class. The gap in this
  row is against PisoLang and Chardonnet et al. only. What separates 42 from the
  other two is narrower and is stated in §4: all three admit `map`, but 42
  eliminates parameters by substitution and so cannot *run* a recursive
  combinator, while RFUN and Theseus interpret theirs.
- **A discipline against erasure.** Lemma 5 of the expressiveness theorem shows
  `drop : C <-> 1`
  is *definable* in 42, at every type, though it is not a primitive. Theseus
  lists exactly that program as ill-formed. Its §3.1 gives `drop_var`, in which
  a bound `n` is not used on the other side, as one of four examples of invalid
  expressions, alongside `dup_var`, which uses one twice. Both are enforced by
  its second rule, that each variable "*must appear exactly once on the other
  side and with the same type*". 42 has no variables and so no such rule, and
  gets `copy` and `drop` as ordinary morphisms. Whether that is a gap or a
  feature is the whole argument of §6, but it is certainly a difference in what
  the language will refuse to accept.
- **Nominal types.** Every other language here declares its inductive types
  with named constructors. 42 infers structural ones, and its `type`
  declarations, including parameterised ones like
  `type list a = mu X. 1 + (a x X)`, are *abbreviations* over those structural
  types rather than new types. The
  difference is not only notational: because `Z` and `Nil` are distinct
  constructors in PisoLang, the `0`/`[]` ambiguity that 42 handles by
  type-directed printing does not arise there at all.
- **An inequality test.** Inv has `neq` as a primitive, and 4₂ had `.LT.`,
  `.GT.`, `.GE.`, `.LE.` and a negation available inside boolean tests; 42 has
  only `copy!`, to filter on two values *agreeing*, and no way to filter on their
  differing. This
  one is less of a gap than it looks, since `neq` is there largely to establish
  the disjointness 42 does not require (§3), but the expressiveness difference
  is real and worth checking rather than assuming away.
- **A mechanised proof of it.** 42 has a completeness result,
  summarised in the note below, but like PisoLang's and Inv's it is on paper.
  Nobody in this table has a machine-checked one.
- **Verified inference.** Nobody has this, PisoLang included, so it is a
  field-wide gap rather than a deficit.
- **Mid-circuit measurement, in Q42.** √Π excludes state preparation and
  measurement. Q42 has terminal measurement, in which `42q sample` applies the
  Born rule to the state a program produced (QMANUAL §7.5), and that required no
  addition to the language, because it operates on the output rather than being a term.
  Measurement *within* a program is absent by decision rather than omission:
  measurement is not unitary, so admitting it as a term would make `!` partial.
  By the principle of deferred measurement the exclusion costs no expressiveness,
  which `q42/teleport.42` demonstrates on the canonical case (QMANUAL §8.5, §9.2).
- **A path to a machine.** Every language here that has one is listed in §8. 42
  has an interpreter and Q42 a simulator; neither emits anything a device or a
  reversible processor could run. §8.4 argues that this gap is wide but shallow,
  since the layers below the emitter are commodity.

**A note on which completeness theorem applies.** The result the neighbouring
languages prove is Axelsen & Glück's: reversible Turing machines compute exactly
the *injective computable functions*. That is the right statement for a language
whose terms denote injections, and it is the wrong shape for 42, whose terms
denote relations. The statement proved in the [expressiveness
theorem](THEOREM.md) is a characterisation
rather than a lower bound:

> a relation `R ⊆ A × B` is denotable in 42 iff `R` is recursively enumerable

with ordinary Turing completeness as the single-valued case. Two things about
it bear on this document's comparisons.

The **soundness** half is an induction over terms: the r.e. relations are closed
under composition, union, product, sum, converse and reflexive-transitive
closure, which is the whole of 42's syntax, and nothing in the language forms a
complement, so the denotations cannot leave Σ⁰₁. The *converse* clause, which an
injective language has to argue for, is free here: 42's total `dagger` and the
class of r.e. relations have the same closure properties. That correspondence is
the same fact §2 and §3 keep circling: dropping the disjointness condition is
what lets the semantic class be one that is already closed under the operation
the language is built around.

That shape is not hypothetical: Chardonnet, Lemonnier & Valiron prove
exactly the injective version, and say so in those words:

> we showed that for any computable function `f` from PInj, there exists an iso
> whose semantics is `f`, thus our language fully characterises all of the
> computable morphisms in PInj.

Read side by side, their theorem and Theorem 14 here are the same
statement in two different categories: *every computable morphism of the ambient
category is denotable*, with PInj there and Rel here. That is the cleanest way to
put what 42 changes: not the theorem, the category.

The **completeness** half is where 42's extra generality is visibly cheaper than
the neighbours'. The proof guesses the output and checks it, and both halves of
that come from constructions the language already had rather than from anything
added for the proof: the guess is `drop_A ; drop_B!`, and the check is `copy`.
An injective language cannot write the guess at all.

---

## 8. The backend axis

Every section above compares *semantics*. This one compares what happens after
the semantics: whether a language reaches a machine. Two of the languages here
were designed with a compilation target in view, so the axis is a real one, and
it is where 42 is furthest behind.

None of these papers was read for this document; the descriptions come from
general knowledge of the field and must be checked before any of it is repeated
in print. The claims made here concern only
*shape*: which layers exist, and which systems occupy them.

### 8.1 Reversible classical: a complete stack, since 2011

The Janus lineage goes all the way to silicon:

```
  Janus  ->  RIL / RSSA  ->  PISA  ->  Pendulum
  (1986)     (Axelsen)      (ISA)     (a reversible processor)
```

**Janus** (Lutz & Derby 1986; semantics and inverter by Yokoyama & Glück, PEPM
2007) compiles through Axelsen's reversible intermediate languages to **PISA**,
the Pendulum Instruction Set Architecture, and PISA was implemented in Vieri's
adiabatic reversible processor at MIT (1999). **ROOPL** (Haulund) reaches PISA
from a reversible object-oriented language; **Hermes** (Mogensen) compiles a
reversible language for cryptographic primitives down to C.

The paper to read first, if 42 ever grows a compiler, is Axelsen's *Clean
Translation of an Imperative Reversible Programming Language* (CC 2011). Its
subject is the obligation that makes reversible compilation different from
ordinary compilation: **each translation step must itself be reversible**, or the
compiler destroys the property it exists to preserve. That constraint applies to
42 exactly as written, and it is not a constraint 42's design has yet been tested
against.

PISA is a *classical* reversible ISA, valued in 𝔹, the semiring in which 42 is
interpreted (§1). The natural compilation target for **42**, as distinct from
Q42, is therefore this branch rather than quantum hardware.

### 8.2 Quantum: the stack is standardised, but the front ends are not languages

| layer | what occupies it |
|---|---|
| front end | Qiskit, Cirq, pyQuil, Q#, Guppy |
| IR | **OpenQASM 3**, **QIR** (LLVM-based) |
| optimiser / router | tket, Qiskit's transpiler, **VOQC** (formally verified) |
| device | superconducting and trapped-ion hardware |

The asymmetry is the point. The lower three layers are mature, shared and
vendor-neutral; anything that can produce OpenQASM 3 or QIR inherits routing and
gate synthesis for free. The top layer is mostly *circuit-assembly libraries
embedded in Python* rather than languages with a semantics. Q# is the clearest
exception, and reaches hardware through QIR.

Two front ends are relevant here for opposite reasons. **Quipper** (Green,
Lumsdaine, Ross, Selinger, Valiron, PLDI 2013) is a real circuit-generating
toolchain, aimed at resource estimation more than at a chip. **Guppy**
(Quantinuum) exists to expose precisely what Q42 declines to have: mid-circuit
measurement with real-time classical feedback. It is the shape of language you
get when the hardware's capabilities, rather than a semantics, set the design.

### 8.3 The Π lineage has no backend at all

Π, √Π, Theseus, RFUN, PisoLang, Inv: **none emits anything executable on
hardware.** They are calculi with interpreters and, in the best cases,
mechanised proofs. √Π's relation to Clifford+T is a completeness *theorem*, not
a code generator.

The nearest thing to a bridge is **Qunity** (Voichick, Li, Rand & Hicks, POPL
2023), which is close to Q42 in spirit, being a unified quantum/classical
language built on sums and products, and which describes a compilation procedure
down to circuits. How far the implementation goes is not something this document
can assert, none of §8 having been read at first hand. **Silq** (Bichsel, Baader,
Gehr & Vechev, PLDI 2020) is likewise simulator-centred; its contribution is the
uncomputation inference, not a path to a device.

So the position 42 and Q42 are in is the *normal* position for this family, not
an unusual deficit. What is unusual is how little would close it.

### 8.4 What closing it would take

For **Q42**, an emitter rather than a backend: lower a term to OpenQASM 3 or QIR
and let an existing compiler route it. Routing and rotation synthesis, the two
two costly parts, are commodity. Specific to Q42 are wire assignment (the width
rule of QMANUAL §9.4 read constructively) and unrolling recursive definitions to
a fixed depth.

One component has no existing counterpart. Q42 defers every measurement, by
construction (QMANUAL §9.2), and on hardware deferral costs coherence time and
prevents qubit reuse. A lowering would therefore want to apply the principle of
deferred measurement **in reverse**: recognise a `ctrl` whose control qubit is
not used again, and emit measure-and-branch where the term specifies quantum
control. No prior language requires such a pass, because none is structurally
obliged to defer.

For **42**, the target is §8.1's, not §8.2's: a reversible classical ISA. That is
a much less fashionable direction and a much better fit, and Axelsen's
reversibility-preserving translation discipline is the thing to read before
attempting it.

---

## References

- P. G. M. Jansen. *Reversible Programming in 4₂.* Master's thesis, University
  of Amsterdam, study group Robotics and Artificial Intelligence, 1993. Research
  carried out at Philips Natuurkundig Laboratorium and IPO, Eindhoven, within the
  Rosetta project; the language is credited in the preface to Joep Rous and Paul
  Jansen. Paper only — see §0.5.
- J. Rous, P. G. M. Jansen. *Reversible Programming in 4₂.* Listed as
  **forthcoming** in the thesis's own bibliography — the same title under joint
  authorship. Never published.
- S.-C. Mu, Z. Hu, M. Takeichi. *An Injective Language for Reversible
  Computation.* MPC 2004, LNCS 3125, 289–313.
  <https://takeichi.ipl-lab.org/~scm/pub/reversible.pdf>
- K. Onodera, K. Nakano, K. Asada, K. Kikuchi. *PisoLang: a User-Friendly
  Reversible Programming Language with Inductive Types.* RC 2026.
  Full version: <https://www.riec.tohoku.ac.jp/~ksk/pub/Onodera26rc-full.pdf>
- J. Carette, C. Heunen, R. Kaarsgaard, A. Sabry. *With a Few Square Roots,
  Quantum Computing is as Easy as Π.* POPL 2024.
  <https://arxiv.org/abs/2310.14056>
- J. Carette, C. Heunen, R. Kaarsgaard, A. Sabry. *The Quantum Effect: A Recipe
  for QuantumΠ.* arXiv:2302.01885, 2023. Agda development:
  <https://github.com/JacquesCarette/QuantumPi>
- C. Heunen, R. Kaarsgaard, L. Lemonnier. *One rig to control them all.*
  arXiv:2510.05032, 2025.
- R. P. James, A. Sabry. *Information Effects.* POPL 2012, 73–84. (Π)
- T. Yokoyama, R. Glück. *A Reversible Programming Language and its Invertible
  Self-Interpreter.* PEPM 2007, 144–153. <https://doi.org/10.1145/1244381.1244404>
- M. K. Thomsen, H. B. Axelsen. *Interpretation and Programming of the
  Reversible Functional Language RFUN.* IFL 2015, Koblenz.
  <https://doi.org/10.1145/2897336.2897345> Implementation:
  <https://github.com/kirkedal/rfun>
- R. P. James, A. Sabry. *Theseus: A High Level Language for Reversible
  Computing.* 2014. (Πo's full primitive table is in its §2.)
- K. Chardonnet, L. Lemonnier, B. Valiron. *Semantics for a Turing-Complete
  Reversible Programming Language with Inductive Types.* FSCD 2024, LIPIcs 299,
  19:1–19:19. <https://doi.org/10.4230/LIPIcs.FSCD.2024.19>

**From the 1993 thesis's bibliography** (§0.4), transcribed from it:

- V. R. Pratt. *Applications of a modal logic to programming.* Studia Logica 39
  (1980), pp. 257–274. — the regular relation operators.
- D. Harel. *Dynamic Logic.* In Gabbay & Guenther, *Handbook of Philosophical
  Logic*, Vol. 2, Reidel, Dordrecht, 1984, pp. 497–604.
- G. D. Plotkin. *A Powerdomain Construction.* SIAM Journal of Computing, Vol. 5
  (1976), pp. 452–487. — for `Π : S_start → ℘(S_end)`.
- R. Landauer. *Irreversibility and Heat Generation in the Computing Process.*
  IBM Journal of Research and Development 5 (1961), pp. 192–203.
- C. H. Bennett. *Logical Reversibility of Computation.* IBM Journal of Research
  and Development 17 (1973), pp. 525–532.
- E. W. Dijkstra. *Program inversion.* EWD671, University of Technology,
  Eindhoven, 1978.
- D. Gries. *The Science of Programming.* Springer-Verlag, New York, 1981.
- D. Gries, J. L. A. van de Snepscheut. *Inorder traversal of a binary tree and
  its inversion.* In Dijkstra, *Formal Development of Programs and Proofs*,
  Addison-Wesley, 1989, pp. 37–42.
- W. Chen, J. T. Udding. *Program Inversion: more than fun!* Science of Computer
  Programming 15 (1990), pp. 1–13.
- J. E. Hopcroft, J. D. Ullman. *Introduction to Automata Theory, Languages, and
  Computation.* Addison-Wesley, Reading, 1979. — the source of the Turing
  machine normalisations §5.1 of the expressiveness theorem assumes, and on the
  1993 shelf.
- R. Leermakers, J. Rous. *The Translation Method of Rosetta.* Computers and
  Translation, Vol. 1, No. 3 (1986), pp. 169–183.
- L. Appelo, J. Landsbergen. *The Machine Translation Project Rosetta.* Proc.
  First International Conference on State of Art in Machine Translation,
  Saarbrücken, 1986, pp. 34–51.
- D. Adams. *The Hitch Hiker's Guide to the Galaxy.* Pan Books, London, 1979. —
  the source of the language's name.

**Other references.**

- C. Lutz. *Janus: a time-reversible language.* 1986. — the original letter;
  known here through Yokoyama & Glück's formalisation.
- H. B. Axelsen. *Clean Translation of an Imperative Reversible Programming
  Language.* CC 2011. (Janus → PISA; the reversibility-preserving discipline.)
- C. J. Vieri. *Reversible Computer Engineering and Architecture.* MIT, 1999.
  (Pendulum / PISA.)
- A. S. Green, P. LeFanu Lumsdaine, N. J. Ross, P. Selinger, B. Valiron.
  *Quipper: a scalable quantum programming language.* PLDI 2013.
- B. Bichsel, M. Baader, T. Gehr, M. Vechev. *Silq.* PLDI 2020.
- F. Voichick, L. Li, R. Rand, M. Hicks. *Qunity: A Unified Language for
  Quantum and Classical Computing.* POPL 2023.
- K. Hietala, R. Rand, S.-H. Hung, X. Wu, M. Hicks. *A Verified Optimizer for
  Quantum Circuits.* POPL 2021. (VOQC.)
- A. W. Cross et al. *OpenQASM 3: A broader and deeper quantum assembly
  language.* 2022. QIR Alliance: <https://www.qir-alliance.org/>
- R. Glück, T. Yokoyama. *A minimalist's reversible while language.* IEICE 2017.
- S. Abramsky, B. Coecke. *A Categorical Semantics of Quantum Protocols.*
  LiCS 2004.
- B. Coecke, D. Pavlović. *Quantum measurements without sums.*
- S. Abramsky, A. Brandenburger. *The sheaf-theoretic structure of non-locality
  and contextuality.*
