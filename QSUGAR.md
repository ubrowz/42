# Q42 with Names — a design note on clauses for Q42

*Draft design note, 2026-10-28. Nothing here is implemented in Q42, which
refuses clause definitions today. It builds on [SUGAR.md](SUGAR.md), the
clause notation for 42, and decides where Q42's version must differ. Where this
note says "checked", `spike/qsquare.py` does it, against the clause definitions
in `spike/qsugar.42`.*

*Settled before drafting: the Q42 sugar is designed for Q42, and may differ from
42's wherever Q42 is better served.*

*Decided 2026-10-28 (§9): a name may be bound again once its value is consumed,
in both languages; the first version permutes only, reuses the 42 compiler,
emits circuits for the aligned case, and leaves calls out of Q42 patterns.*

## Contents

1. [How Q42 relates to 42](#1-how-q42-relates-to-42)
2. [What clauses are for in Q42](#2-what-clauses-are-for-in-q42)
3. [The rules](#3-the-rules)
4. [Compilation](#4-compilation)
5. [Circuits](#5-circuits)
6. [Messages](#6-messages)
7. [Plan](#7-plan)
8. [Precedents](#8-precedents)
9. [Decisions, and what is left for later](#9-decisions-and-what-is-left-for-later)

---

## 1. How Q42 relates to 42

```
42 clauses ──compile──▶  42 core  ⊃   C   ⊂  Q42 core  ◀──compile── Q42 clauses
                       (Bool matrices)  (permutations)  (ℂ matrices)
```

**The outer arrows are compilation.** Each turns a clause definition into one
core term with the same meaning. Turning the clauses round and then compiling
gives the same result as compiling and then running backwards (SUGAR.md §5).

**The middle is a shared core, not an equivalence.** The two point-free
languages overlap; neither contains the other.

```
42 core   =  C  +  { inl, inr, zero, copy, join, |, ^ }
Q42 core  =  C  +  { omega, v }

C  =  id, swapprod, assocprod, unitprod, swapsum, assocsum, unitsum, dist,
      with  ;  *  +  !  and parameters
```

Both languages denote matrices: 42's entries are Booleans, so a matrix is a
relation, and Q42's entries are complex numbers. Every term of `C` denotes a
*permutation* matrix, and a permutation matrix exists over any semiring, so on
`C` the two meanings determine each other: the 42 relation is the set of
nonzero entries of the Q42 matrix, and the Q42 matrix is the 0/1 matrix of the
42 relation.

Outside `C` there is no translation either way. 42 to Q42 fails because `copy`,
`join`, `inl` and `|` are not unitary (QMANUAL §5). Q42 to 42 fails for a
deeper reason: "keep the nonzero entries" does not commute with composition,
because entries can cancel. Over ℂ, `1 + (−1) = 0`; over the Booleans,
`true ∨ true = true`. That failure is interference, and it is QMANUAL §5.1's
`1 + 1 = 1` seen from the other side.

**A fourth relation connects the two sugars.** A Q42 clause definition obeys
stricter rules than a 42 one (§3), so — the rebinding question of §3.4 aside —
it is also a valid 42 clause definition. When its calls stay inside `C`,
compiling it both ways must land on the same meaning:

```
Q42 clauses (calls in C) ──Q42 compile──▶  P  (permutation matrix)
         │ also valid as
         ▼
    42 clauses           ──42 compile──▶   R  (relation)

claim:   R  =  the nonzero entries of P
```

Checked on four real definitions: `cx` and `ccx` from `q42/gates.42`, Deutsch's
`orcnot` from `q42/deutsch.42`, and `fib.42`'s adder `add4`. Each was written
as 42 clauses in `spike/qsugar.42`, compiled by today's 42 compiler, and
compared with Q42's point-free definition on every basis state, in both
directions. They agree on all of them. Once Q42 compiles clauses itself, the
square becomes a test of every clause definition it accepts.

The two sugars therefore agree exactly where the two semirings do. That is the
overlap finding of README and RELATED.md, one level up.

## 2. What clauses are for in Q42

Q42 code is short, and its difficulty is not the plumbing that makes 42 hard.
It is knowing *which qubit* a gate acts on. `fib.42`'s adder on
`|x0 x1 y0 y1>` is:

```
def cc03 = ctrl (on2 (ctrl x))     -- Toffoli: controls q0, q2; target q3
def cx02 = ctrl (on2 (x * id))     -- CNOT: q0 -> q2
def cx13 = on2 (ctrl (on2 x))      -- CNOT: q1 -> q3
def add4 = cc03 ; cx02 ; cx13
```

and the comments are what make it readable. With clauses, **a name is a wire**,
and a call names the wires it acts on. The compiler routes them together and
back:

```
def add4 (x0, (x1, (y0, y1))) <->
    let (x0, (y0, y1)) = ccx (x0, (y0, y1)) in
    let (x0, y0)       = cx  (x0, y0)       in
    let (x1, y1)       = cx  (x1, y1)       in
    (x0, (x1, (y0, y1)))
```

That reads as the circuit, in the style of Quipper and other languages with
named wires. It reuses `x0`, `y0`, `y1` and `x1` after a gate has consumed
them, which §3.4 allows; `spike/qsugar.42` has it exactly as written here. The routing costs nothing in a circuit: `swapprod` is carried in the
layout and `assocprod` re-brackets, so neither emits a gate (QMANUAL §9.4).

Two other uses come straight from the clause form.

**Control is a definition.** `ctrl x` is two clauses, and compiles to exactly
`mat ; (id + x) ; mat!`:

```
def cx (L (), q)  <->  (L (), q)
def cx (R (), q)  <->  (R (), x q)
```

**Classical functions are truth tables.** Deutsch's oracle for `f(x) = not x`
is today `(x * id) ; ctrl x ; (x * id)`. As clauses it is the table itself:

```
def orcnot (L (), y)  <->  (L (), x y)      -- f(0) = 1: flip y
def orcnot (R (), y)  <->  (R (), y)        -- f(1) = 0: leave y
```

Two things clauses do *not* do, which the Q42 manual must say plainly.

- **They do not make superpositions.** A clause definition with no calls
  permutes basis states and nothing else. Every genuinely quantum step, `h`,
  `v`, `omega` and what is built from them, enters as a call.
- **Matching on a qubit is not classical branching.** A qubit in superposition
  matches *both* clauses, and both run, weighted by its amplitudes. A pattern
  match on a qubit is quantum control, which is what QMANUAL §6.4 already says
  about `dist`.

## 3. The rules

### 3.1 Exact linearity

Every name a clause binds is used exactly once, and every name it uses is bound
exactly once. 42's two relaxations go:

| In 42 | In Q42 |
|---|---|
| a name used twice in a term is a `copy` | an error |
| a name used twice in a pattern is an equality test (`copy!`) | an error |

The error should give QMANUAL §5.2's reason rather than the no-cloning theorem:
`copy` maps a space into a bigger one, which makes it an isometry and not a
unitary. It copies basis states only, so it is not an illegal cloner; it is
simply not square.

### 3.2 Both sides cover their type exactly once

The patterns of a definition must match every input exactly once: no two may
overlap, and none may be missing. The terms, read as patterns, must do the same
for the output. This is Theseus's rule (RELATED.md §3), and in Q42 it is not a
choice: a definition that left a gap would be a partial map, and one with an
overlap would add two matrices. Neither is unitary.

So overlap, a warning in 42 (SUGAR.md §6), is an **error** in Q42, and so is a
gap, which 42 does not even mention.

Coverage can be decided **without types**. Where one pattern has a constructor
and another has a variable at the same place, the variable is split by the
constructor's shape: `x` against `L t` becomes the two cases `L x1` and `R x2`
(with `x` replaced by `L x1` or `R x2` in the term), `x` against a pair becomes
`(x1, x2)`, and `x` against `()` becomes `()`. Splitting preserves the meaning,
and on finite patterns it stops. When it has stopped, every place has either a
constructor in every clause or a variable in every clause; the clauses then form
a case tree whose leaves have no constructors left, and coverage is read off
it: an empty leaf is a gap, a leaf with two clauses is an overlap.

Splitting is also what makes the rule complete. Some sets of patterns cover
their type exactly once and yet have no single place where every pattern has a
constructor; Berry's three-argument function is the textbook case. Splitting
handles those too.

### 3.3 `let` patterns cannot fail

A `let` pattern may contain only names, pairs and `()`. The reason is particular
to Q42: a call's result may be a superposition, and a pattern that can fail
would keep part of it and drop the rest, which is not unitary. A top-level
pattern may fail, because §3.2 guarantees another clause catches what it misses.

The same reasoning would allow a call inside a pattern (`P t`, matched by
running `P!` and then matching `t`) as long as `t` cannot fail. The first
version leaves calls out of Q42 patterns altogether (§9): nothing in the Q42
libraries needs them yet, and they can be added without changing anything else.

### 3.4 Reusing a wire's name

`add4` above binds `x0` again after `ccx` has consumed it. Until step 0 of §7,
42 refused that ("`x0` is bound twice"). Once a name's value has been consumed, nothing else can
refer to it, so binding the name again is unambiguous, and turning the clause
round still works: the reversed chain rebinds in the opposite order. Circuit
code needs it; without it every gate renames every wire it touches.

**Decided:** a name may be bound again once its value has been consumed, in both
languages, so that the two sugars do not diverge on something that is not about
unitarity. What stays forbidden is binding a name whose value is still in hand.

For 42 this brought the compiler in line with its own manual, which already
stated the rule this way. It is implemented (step 0 of §7): each legal
rebinding is renamed apart before checking and compiling, so it compiles to
exactly what fresh names would (SUGAR.md §7).

### 3.5 Recursion

Q42 allows recursive definitions, and its emitter bounds their unrolling
(QMANUAL §9.4). Clause definitions should inherit that position unchanged.
Coverage (§3.2) is checked per definition and says nothing about termination.

## 4. Compilation

### 4.1 When input and output split the same way, reuse the 42 compiler

The 42 compiler builds case trees (SUGAR.md §6). When the outputs carry a label
at a common place, sorted the same way as the inputs, it ends a split with
`dist!` instead of `join`. Under §3's rules, if every split of the inputs has
such a matching split of the outputs, the compiled term uses nothing outside
`C` plus the definition's calls. Checked:

| Definition | Compiled by today's 42 compiler | Inside `C` |
|---|---|---|
| `cx` | `dist ; (unitprod ; unitprod!) + (unitprod ; not ; unitprod!) ; dist!` | yes |
| `ccx` | `dist ; (unitprod ; unitprod!) + (unitprod ; cx ; unitprod!) ; dist!` | yes |
| `orcnot` | `dist ; (unitprod ; not ; unitprod!) + (unitprod ; unitprod!) ; dist!` | yes |
| `add4` | a long route of `swapprod` and `assocprod`, with the three calls | yes |

`cx`'s line is `ctrl not` with `mat` written out.

The reason is structural. Under the rules, a leaf of the case tree is a single
clause with no constructors left in its pattern or its term, since a leftover
constructor on one side would leave that side uncovered. So each leaf compiles
to routing and calls. And each split is a `dist` closed by a `dist!`, possibly
with a `swapsum` between. No `inl`, `inr`, `join`, `copy` or `|` is ever needed.

### 4.2 When they do not, the general construction

Not every permutation splits the same way on both sides. The 3-cycle on two bits
`00 → 01 → 10 → 00`, with `11` fixed, is a permutation and hence unitary:

```
def cyc (L (), L ())  <->  (L (), R ())
def cyc (L (), R ())  <->  (R (), L ())
def cyc (R (), L ())  <->  (L (), L ())
def cyc (R (), R ())  <->  (R (), R ())
```

Split the inputs on the first bit: one half goes to `{01, 10}` and the other to
`{00, 11}`. Neither output bit sorts the outputs that way. The 42 compiler then
falls back to `join` and `inl`/`inr` (checked: `spike/qsquare.py` reports `cyc`
as using `inl`, `inr` and `join`), which is right for 42 and unavailable in Q42.

The general construction compiles the whole clause set at once. For clauses
`p_i <-> e_i`, `i = 1 … n`:

```
M_in    :  A  ≅  E_1 + … + E_n        the input case tree, after splitting (§3.2)
σ       :  reorder the summands to the output tree's order
mid_i   :  E_i  ≅  F_i                clause i's routing and calls
M_out   :  B  ≅  F_1 + … + F_n        the output case tree, built from the terms

f  =  M_in ; σ ; (mid_1 + … + mid_n) ; M_out!
```

`E_i` is the product of clause `i`'s pattern names, and `F_i` that of its
term's (calls in a term become names whose values the `let`s of `mid_i`
compute). `M_in` and `M_out` are built from `dist` and pair plumbing exactly as
the case trees of §4.1 are; `σ` from `swapsum` and `assocsum`; `mid_i` from the
42 compiler's routing. Every piece is in `C` or a call.

The aligned case of §4.1 is the case where `σ` is the identity at every level
and the two trees can be interleaved split by split.

### 4.3 Why it is right: the proof sketch

SUGAR.md §12 recorded this proof as owed. The sketch:

1. **Splitting** (§3.2) replaces a clause by clauses with the same meaning, and
   preserves "covers exactly once". It terminates because each split moves a
   constructor from one clause into another at a place where some clause
   already had one, and patterns are finite.
2. **`M_in` is an isomorphism** onto the sum: by induction on the case tree,
   each `dist` is one, and each leaf, having only names, pairs and `()`, is a
   rearrangement. Exactly-once coverage is what makes each value land in
   exactly one summand. The same holds for `M_out`.
3. **`σ` exists**, because `+` is symmetric and associative up to `swapsum` and
   `assocsum`, and any reordering of the leaves of one sum tree into another is
   a composite of those. This is the coherence theorem for symmetric monoidal
   categories, applied to `+`.
4. **Each `mid_i` is unitary**: a linear rearrangement of names is a
   permutation, a call is unitary by assumption, and a `let` whose pattern
   cannot fail (§3.3) is a rearrangement too.
5. **The meaning is the clauses'.** On a basis state `v`, exactly one clause
   `i` matches; `M_in` sends `v` to summand `i` holding its names; `mid_i`
   computes the term's values; `M_out!` builds `e_i`. So `f` sends `v` where
   clause `i` says, and by linearity `f` is determined. On the core fragment
   this is also the square of §1: the relation 42 gives is the set of nonzero
   entries of `f`.

What remains for a full proof is writing steps 1 and 3 out in detail, and
stating the exact grammar of patterns covered. Theseus proves the corresponding
result into Π for its own language; the argument here has the same shape.

## 5. Circuits

The evaluator runs any finite type. The circuit emitter does not: it works on
*register* types, and `assocsum` and `unitsum` "cannot occur at a register type
in the first place" (QMANUAL §9.4). That splits the compilation question in two.

- **The aligned case stays at register types.** A `dist` on a qubit splits a
  register `(1+1) x A` into `A + A`, whose two sides have the same width, so
  every intermediate type in §4.1's output is a register. Controls, oracles and
  adders are aligned, and emit.
- **The general case may leave them.** `σ` reorders a sum of clause
  environments of different widths, and that intermediate is not a register.
  The evaluator does not care; the emitter would refuse.

A register-level circuit always *exists* for a clause definition without calls,
because such a definition is a permutation of basis states, and multiply
controlled NOTs generate every permutation of `{0,1}^n`. A NOT on bit `j`,
controlled on every other bit taking the values in `s`, exchanges `s` with `s`
flipped at `j`, and those exchanges, along the edges of a connected cube,
generate the whole symmetric group. Q42 has them all, by nesting `ctrl`. But
existence is not a compiler: turning an arbitrary permutation into a short
circuit is a hard optimisation problem.

**Proposal for a first version:** the evaluator accepts every definition §3
allows; the emitter accepts what stays at register types, which includes every
aligned definition, and says why when it refuses. A register-level compilation
of the general case is left for later (§9, item 4).

## 6. Messages

Draft wording, in the style of the 42 messages (SUGAR.md §4, MANUAL §19):

| Situation | Message |
|---|---|
| a name used twice in a term | ``in `f …`, `x` is used twice.  Q42 cannot copy a value: copying maps a space into a bigger one, so it is not unitary (QMANUAL §5.2).`` |
| a name twice in a pattern | ``in `f …`, `x` is matched twice.  An equality test discards the pairs that differ, which is not unitary in Q42.`` |
| overlap | ``clauses i and j of `f` both match `…`.  In Q42 a definition is the sum of its clauses, so they must not overlap.`` |
| gap | ``no clause of `f` matches `…`.  In Q42 every input needs exactly one clause, or the definition is not unitary.`` |
| output overlap or gap | the same two, for the terms read as patterns |
| a `let` pattern that can fail | ``in `f …`, the pattern `…` can fail.  A call's result may be a superposition, so a pattern after a call may contain only names, pairs and ().`` |
| a call in a pattern | ``in `f …`, the pattern calls `P`.  Calls in patterns are 42-only for now; match first, then call `P!` in a `let`.`` |
| emitter, general case | ``f compiles, but not at register types (QMANUAL §9.4); it runs in the evaluator and cannot be emitted yet.`` |

## 7. Plan

Each step is a commit with every test passing, as for the 42 sugar.

0. **Rebinding, in the shared compiler** (§3.4). *Done.* A second binding of a
   name whose value has been consumed is accepted, in 42 at once; SUGAR.md §7
   and MANUAL §7 and §19 say so, with an example, and tests check that it
   compiles exactly as fresh names would and that, turned round, it still
   compiles to the inverse.
1. **Q42 accepts clauses: the rules and the aligned case.** The Q42 parser
   stops refusing clauses. Before compiling, it checks §3.1–3.3, refuses calls
   in patterns, and decides coverage by the splitting of §3.2, with the
   messages of §6. Then it compiles with the 42 compiler. If the result stays
   inside `C` plus calls, Q42 accepts it; otherwise it refuses with "needs the
   general construction, not built yet". Tests: the rules and every message;
   and the square of §1 for every accepted definition whose calls stay inside
   `C`, generalising `spike/qsquare.py`. `cx`, `ccx`, `orcnot` and `add4` are
   the first cases, written with rebinding as in §2.
2. **The general construction** of §4.2, replacing that refusal, with the proof
   of §4.3 written out (as THEOREM.md writes its proofs). `cyc` is the first
   test.
3. **The emitter.** Definitions whose compiled form stays at register types
   emit, which includes every aligned one. The rest run in the evaluator, and
   the emitter refuses them with §6's message.
4. **The Q42 manual**, rewritten as the 42 manual was: clauses first, the core
   as what they compile to. The five fixes found while reviewing it (who it is
   for, §4.2's "42's syntax", clauses in §5, §6.4's reference, the reference's
   source-file summary) fold into the rewrite, as do the stale manual
   references in the comments of the `.42` files.

Then the held push: the 42 work and the Q42 work go out together.

## 8. Precedents

- **Theseus** (James & Sabry, 2014): pattern-matching isomorphisms whose
  clauses cover both sides exactly once, compiled to Π. §3.2 is its rule.
- **Sabry, Valiron & Vizzotto**, "From Symmetric Pattern-Matching to Quantum
  Control" (FoSSaCS 2018; extended version arXiv:1804.00952, in `sources/` as
  `sabry.pdf`). The closest precedent. Isomorphisms are written as clauses
  `v ↔ v′`, every variable occurring exactly once on each side; the patterns on
  each side must be pairwise orthogonal (non-overlapping) and exhaustive; a
  `let` pattern may contain only `()`, variables and pairs, the restriction §3.3
  arrives at here; and their first example already writes the arrow `<->`. The
  quantum step goes further than this note: clause bodies may be linear
  combinations of values, subject to the resulting matrix being unitary, so
  that the Hadamard gate is itself an iso (their Example 2.1):

  ```
  tt  ↔  1/√2 tt + 1/√2 ff
  ff  ↔  1/√2 tt − 1/√2 ff
  ```

  Q42 does not take that step here (§9, item 2): its gates stay primitives
  and library definitions, and clauses permute. Their language also has lists
  and structurally recursive fixpoints, whose meaning lives in
  infinite-dimensional Hilbert spaces; Q42 stays finite.
- **Chardonnet, Lemonnier & Valiron** (2024): the descendant of Theseus that
  RELATED.md §3 discusses, with exhaustivity dropped. Q42 cannot drop it.
- **Quipper** (Green, Lumsdaine, Ross, Selinger & Valiron, PLDI 2013): named
  wires in a circuit language, which is §2's reading of a clause variable.

## 9. Decisions, and what is left for later

Decided 2026-10-28:

1. **Rebinding: yes, in both languages** (§3.4).
2. **Superpositions in clause bodies: not in the first version.** Clauses
   permute; gates stay primitives and library definitions. It stays possible
   later, and more cheaply than in general: the condition Sabry, Valiron &
   Vizzotto impose is that the clause bodies' coefficient matrix be unitary,
   and Q42 computes with exact amplitudes (`q42/exact.py`), so it could check
   that condition exactly, with no rounding.
3. **One compiler, for now.** Q42 reuses the 42 compiler, so the square of §1 is
   a statement about a single compiler. Revisit when the general construction
   exists, which is the point where a circuit-minded Q42 compiler could start
   to pay.
4. **Circuits for the general case: later.** The first version emits the
   aligned case and refuses the rest with a reason (§5).
5. **Calls in Q42 patterns: not in the first version** (§3.3).

Left for later, in no particular order: superposition bodies (2), a separate
Q42 compiler (3), a register-level compilation of the general case (4), calls
in patterns (5), and clause definitions over recursive types, which Q42 does
not have.
