# Q42 with Names — a design note on clauses for Q42

*Design note, 2026-10-28, implemented through step 2 of §7: Q42 accepts every
clause definition §3 allows, compiling it with 42's compiler when input and
output split alike and with the general construction of §4.2 otherwise. It
builds on [SUGAR.md](SUGAR.md), the clause notation for 42, and decides where
Q42's version must differ. Where this
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

Not every permutation splits the same way on both sides, and how often it does
was measured rather than guessed. The case-tree builder tries every place the
inputs could split and keeps one whose partition the outputs also make (SUGAR.md
§6). With that, **all 24 permutations of two bits** compile inside the core.
An earlier draft of this note gave the 3-cycle `00 → 01 → 10 → 00` as a
counterexample. It is not one: split on the *second* bit, its outputs split the
same way on the first.

On three bits it changes: of 3000 random permutations, about three quarters
need more than aligned splits. The smallest one moves only two values, and
exchanges `000` with `111`:

```
def sw (L (), (L (), L ()))  <->  (R (), (R (), R ()))
def sw (R (), (R (), R ()))  <->  (L (), (L (), L ()))
def sw (L (), (L (), R ()))  <->  (L (), (L (), R ()))
… and the other five values to themselves
```

Wherever the inputs split, one side holds `000` or `111` and three fixed values,
and the outputs, which swap them, never split the same way. The 42 compiler then
falls back to `join` and `inl`/`inr` (checked: `spike/qsquare.py` reports `sw`
as using `inl`, `inr` and `join`), which is right for 42 and unavailable in Q42.

The general construction compiles the whole clause set at once. It is built
(step 2 of §7, `general` in `q42/sugar.py`), and Q42 uses it whenever the 42
compiler's aligned result would leave `C`. For clauses `p_i <-> e_i`:

```
f  =  M_in ; (+_j  mid_j ; N_j ; reshape_j) ; σ ; M_out!

M_in       :  A  ≅  Σ_j E_j          the input, split into input leaves j
mid_j      :  E_j  ≅  G_j             leaf j's lets and calls
N_j        :  G_j  ≅  Σ_{k ∈ K_j} F_k  the splits M_out made, made on G_j
reshape_j  :  each F_k into M_out's order of names
σ          :  the summands, from M_in's tree into M_out's
M_out      :  B  ≅  Σ_k F_k           the output, split into output leaves k
```

**Input leaves.** Splitting (§3.2) turns the clauses into *input leaves*: a
clause whose pattern has been split as far as the other patterns required, with
the same substitution made in its body. `E_j` is the tuple of leaf `j`'s names.
`M_in` is the case tree that sends an input to summand `j` holding those names;
it is made of pair rearrangements, `dist`, and the unit checks of SUGAR.md §3.

**The middle.** In leaf `j`'s body, every call in the final term is first lifted
into a `let` of its own, so that what remains is names and constructors. `G_j`
is the tuple of the names that final term uses, and `mid_j` is leaf `j`'s
`let` chain, from `E_j` to `G_j`, compiled by the 42 compiler as an ordinary
clause.

**Output leaves.** The leaves' final terms cover the output exactly once, and are
split the same way into *output leaves* `k`, each belonging to one input leaf.
Splitting on this side may divide a name of leaf `j`'s final term — a name the
pattern bound, or one a call produced — into `L y1` and `R y2`. `N_j` makes that
same division on `G_j`, so that leaf `j` arrives as a sum over its own output
leaves `K_j`; for a leaf whose final term was not split, `N_j` is the identity.
`reshape_j` reorders each output leaf's names into the order `M_out` holds them
in, and `σ` reorders the summands themselves, with `swapsum` and `assocsum`.

Every piece is a pair or sum rearrangement, `dist`, a unit check, or one of the
clauses' own calls. Checked: `sw`; the Berry set of §3.2, which compiles to the
identity; a definition whose output split falls on a call's result; 40 random
permutations of three bits and 4 of four bits, each exactly, both ways; and
`sw` with one pair of clauses replaced by `(R (), (L (), c)) <-> (R (), (L (), h c))`,
which equals `sw ; ctrl (nctrl h)` built point-free, amplitude for amplitude.

The aligned case of §4.1 is the case where every split of the input is matched
by one of the output, so that `N_j`, `reshape_j` and `σ` are all identities.

### 4.3 Why it is right

SUGAR.md §12 recorded this proof as owed. It is stated for the construction as
built.

**Setting.** Types are finite: built from `1`, `+` and `x`, as Q42's are. A value
is a basis vector, and a program denotes a linear map on the space the values
of its type span. A clause definition `D` passed §3.1–3.3: every name is bound
and used exactly once, `let` patterns cannot fail, patterns contain no calls,
and the patterns, and the final terms read as patterns, each cover their type
exactly once. Calls denote unitaries; for a recursive definition this is an
assumption about the recursion, as everywhere else in Q42.

**What `D` means.** On a value `v`, exactly one clause `p_i <-> e_i` matches,
binding its names to parts of `v`. Then `e_i` is evaluated: a name gives the
value bound to it, a constructor applies to its parts, a call applies its
unitary, and `let q = t in e` evaluates `t`, matches each value in the result
against `q` — which cannot fail — and evaluates `e` with those bindings, the
results summed with the amplitudes of `t`. `⟦D⟧` is the linear map that does
this on every value.

**Lemma 1 (splitting).** Splitting a name `x` by a constructor's shape, in the
pattern and with the same substitution in the body, replaces a clause by
clauses with the same meaning, and preserves "covers exactly once" on both
sides. On one set of clauses it stops.

*Proof.* `x` matches exactly the values matched by `L x1` and by `R x2` together,
and no value is matched by both, so the two new clauses together match what the
old one did, and bind `x1` or `x2` to what `x` was bound to under its label; the
substituted body computes what the old one did. The same holds for a pair and
for `()`. Each split happens at a place where another clause has a constructor,
and removes one constructor from the subproblem on that branch while adding
none, since the name it splits becomes fresh names; so every branch of the
recursion is strictly smaller in the number of constructors left, and in the
number of places left. ∎

**Lemma 2 (case trees).** For a set of clauses that covers its side exactly once,
`M` (`M_in`, or `M_out` on the final terms, or `N_j` on the splits of `G_j`)
sends each value to the summand of the unique leaf matching it, holding that
leaf's names, and is a bijection between values and (leaf, names) pairs.

*Proof.* By induction on the recursion of Lemma 1. A place where every row has a
name moves that place into the leaf's names: no step. A place holding `()` is
dropped by `unitprod`, which accepts only `()`. A pair place becomes two places:
a rearrangement. A label place is brought to the front and split by `dist`, a
bijection onto a sum of two subproblems, each covering exactly once by Lemma 1.
At a leaf one row remains, and the route to its names is a rearrangement. All of
these are bijections on values, and so is their composite. ∎

**Lemma 3 (the middle).** For input leaf `j`, `mid_j ; N_j ; reshape_j`, followed
by output leaf `k`'s part of `M_out!`, computes `e_j` on `j`'s names.

*Proof.* Lifting a call `g t` out of the final term into `let z = g t in …` does
not change what the term computes, since the name `z` is then used exactly where
the call stood. `mid_j` is the 42 compiler's compilation of `E_j <-> let … in G_j`,
whose meaning is to run the lets and return the tuple of the names used, each
exactly once (SUGAR.md §3). The final term `e_j` builds its value from that
tuple with constructors only, so it is a map from tuples to outputs sending
basis values to basis values. On each tuple, `N_j` selects the output leaf `k`
whose split forms the tuple's values have (Lemma 2, applied to `N_j`), and
`M_out!` on summand `k` builds exactly the value `e_j` would (Lemma 2, applied to
`M_out`, read backwards); `reshape_j` only matches the order of names between
the two. ∎

**Lemma 4 (σ).** `σ` sends each output leaf's summand in `M_in`'s arrangement to
the same leaf's summand in `M_out`'s, and is a bijection.

*Proof.* It flattens the source tree into a right-nested sum with `assocsum!`,
exchanges adjacent summands with `swapsum` until they are in the target's order,
and unflattens with the target's flattening run backwards. Each step is a
bijection, and the leaves are tracked by name. ∎

**Theorem.** `⟦f⟧ = ⟦D⟧`, and `f` is unitary.

*Proof.* On a value `v` matching input leaf `j` with names `η`, `M_in` gives
`(j, η)` (Lemma 2), the middle gives `e_j` evaluated on `η` in the summands of
`j`'s output leaves (Lemma 3), and `σ` and `M_out!` put it in place (Lemma 4,
Lemma 2). By Lemma 1, `e_j` on `η` is what `D` gives on `v`. Both sides are
linear, so they agree everywhere. Each piece of `f` is a bijection on values or
a call, and so unitary; hence `f` is. ∎

**Corollary (the square of §1).** If `D`'s calls stay inside `C`, `⟦f⟧` is a
permutation of values, and the relation 42 compiles `D` to is its set of nonzero
entries, since both are the clauses' meaning: the 42 compiler's (SUGAR.md §3, §6)
read over the Booleans, `f` over ℂ, and a permutation's nonzero entries are the
same in both.

This is a proof about the construction, by hand, in the manner of THEOREM.md;
it is not mechanised. The tests check its conclusion on the cases above.

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

**As built:** the evaluator accepts every definition §3 allows; the emitter
accepts what stays at register types, which includes every aligned definition,
and says why when it refuses (§6). A register-level compilation
of the general case is left for later (§9, item 4).

## 6. Messages

As implemented in `q42/sugar.py` (step 1 of §7), each triggered by a test:

| Situation | Message |
|---|---|
| a name used twice in a term | ``in `dup a <-> (a, a)`, `a` is used twice.  Q42 cannot copy a value: copying maps a space into a bigger one, so it is not unitary (QMANUAL section 5.2).`` |
| a name twice in a pattern | ``in `eq (a, a) <-> a`, `a` is matched twice.  An equality test discards the pairs that differ, which is not unitary in Q42.`` |
| a gap | ``no clause of `f` matches `(R _, _)`.  In Q42 every input needs exactly one clause, or the definition is not unitary.`` |
| an overlap | ``the patterns of clauses 1 and 2 of `f` both match `(L (), _)`.  In Q42 a definition is the sum of its clauses, so they must not overlap.`` |
| the same, on the output side | ``no clause of `f` produces …`` and ``the terms of clauses i and j of `f` both produce …`` |
| a `let` pattern that can fail | ``in `f …`, a `let` pattern can fail.  A call's result may be a superposition, so a pattern after a call may contain only names, pairs and ().`` |
| a call in a pattern | ``in `f …`, the pattern calls a program.  Calls in patterns are 42-only for now; match first, then call the program backwards in a `let`.`` |
| emitter, general case | ``` `sw` runs in the evaluator but cannot be emitted yet: `sw` is a clause definition whose input and output do not split alike, so it is compiled by the general construction of QSUGAR.md section 4.2, and that reorders sums of different widths, which are not registers (QMANUAL section 9.4).``` A definition that calls one gets the same, with ``, because it calls `sw` ``. |

Values in Q42 messages are written with `L` and `R`: in Q42, `L ()` is a qubit,
not the number `0` that 42's messages would call it.

## 7. Plan

Each step is a commit with every test passing, as for the 42 sugar.

0. **Rebinding, in the shared compiler** (§3.4). *Done.* A second binding of a
   name whose value has been consumed is accepted, in 42 at once; SUGAR.md §7
   and MANUAL §7 and §19 say so, with an example, and tests check that it
   compiles exactly as fresh names would and that, turned round, it still
   compiles to the inverse.
1. **Q42 accepts clauses: the rules and the aligned case.** *Done.* The Q42 parser
   stops refusing clauses. Before compiling, it checks §3.1–3.3, refuses calls
   in patterns, and decides coverage by the splitting of §3.2, with the
   messages of §6. Then it compiles with the 42 compiler. If the result stays
   inside `C` plus calls, Q42 accepts it; otherwise it refuses with "needs the
   general construction, not built yet" (until step 2). Tests: the rules and every message;
   and the square of §1 for every accepted definition whose calls stay inside
   `C`, generalising `spike/qsquare.py`. `cx`, `ccx`, `orcnot` and `add4` are
   the first cases, written with rebinding as in §2. As built: the shared
   parser takes Q42's rules as a hook (`q42/sugar.py`); the clauses equal the
   point-free gates *exactly*, amplitude for amplitude, and `bell (a, b) <->
   let a = h a in cx (a, b)` compiles to `h * id ; cx`, which is `gates.42`'s
   own definition; `42q show` prints clauses as `42 show` does.
2. **The general construction** of §4.2, replacing that refusal, with the proof
   of §4.3 written out (as THEOREM.md writes its proofs). *Done.* Q42 now
   accepts every clause definition §3 allows.
3. **The emitter.** Definitions whose compiled form stays at register types
   emit, which includes every aligned one. The rest run in the evaluator, and
   the emitter refuses them with §6's message. *Done.* The emitter needed no
   change to refuse them: its own register check already rejects `assocsum`
   at a register type, as §5 predicted. Step 3 added the reason in clause
   terms, for a general-construction definition and for anything that calls
   one; `cx` written as clauses emits as the single gate `cx q[0], q[1]`.
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
