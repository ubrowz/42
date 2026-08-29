# Q42 — User Manual

For a reader with a computer science background who has read
[the 42 manual](MANUAL.md). No prior knowledge of quantum mechanics is assumed;
the physics is developed here from scratch, but only as far as Q42 actually
needs it, and the parts Q42 does *not* model are named as such.

---

## Contents

1. [One change, and everything follows](#1-one-change-and-everything-follows)
2. [Why reversibility is forced](#2-why-reversibility-is-forced)
3. [The physics you need](#3-the-physics-you-need)
4. [Why 42 already fitted](#4-why-42-already-fitted)
5. [What Q42 drops](#5-what-q42-drops)
6. [What Q42 adds](#6-what-q42-adds)
7. [Writing programs](#7-writing-programs)
8. [Worked examples](#8-worked-examples)
9. [What Q42 is, and is not, for](#9-what-q42-is-and-is-not-for)
10. [Reference](#10-reference)

[Appendix: a program and its circuit](#appendix-a-program-and-its-circuit)

---

## 1. One change, and everything follows

- [1.1 A program is a grid](#11-a-program-is-a-grid)
- [1.2 Running backwards is reading the other way](#12-running-backwards-is-reading-the-other-way)
- [1.3 Composing is combining grids](#13-composing-is-combining-grids)
- [1.4 Q42 puts numbers in the cells](#14-q42-puts-numbers-in-the-cells)
- [1.5 The whole difference, in one table](#15-the-whole-difference-in-one-table)

42 computes with **sets**: a program relates inputs to outputs, and running it
backwards gives the set of everything an answer could have come from.

Q42 computes with **complex numbers**: each input–output pairing carries a
number, and those numbers can cancel.

That is the entire difference. The rest of this section makes it concrete,
because the way to see it is to draw a 42 program as a grid and then change what
sits in the cells.

### 1.1 A program is a grid

Take a shape with finitely many values, say the two-value shape `1 + 1`, whose
values are `L ()` and `R ()` (the 42 manual, §3.1). A program from that shape to
itself either can or cannot turn each input into each output, so you can write
the whole program down as a grid: one row per input, one column per output, and a
mark where the program can get from one to the other.

Here is `not`, which is `swapsum`:

```
        to  L ()  R ()
  from
  L ()        .     *
  R ()        *     .
```

Read a **row** as "what this input can produce". `L ()` produces only `R ()`,
which is what negation does.

A program need not have exactly one mark per row. `inl!` removes an `L` label
and rejects anything else, so its row for `R ()` is empty. That is 42's `{}`,
drawn:

```
        to    ()
  from
  L ()        *
  R ()        .
```

And `join!`, which forgets nothing going backwards and so must offer both
labels, has two marks in one row. That is a set of two answers, drawn:

```
        to  L ()  R ()
  from
    ()        *     *
```

Nothing new has been said yet. This is the same "a program returns a set" from
the 42 manual's §7, written as a picture instead of as a list.

### 1.2 Running backwards is reading the other way

Now the useful part. To run a program backwards you ask, of an output, which
inputs could have produced it, which is reading the grid down a column instead
of along a row.

So `!` **is the grid, flipped about its diagonal.** Compare `join!` above with
`join`:

```
                                        to    ()
        to  L ()  R ()           from
  from                    !  =   L ()        *
    ()        *     *            R ()        *
```

Same marks, rows and columns exchanged. This is why 42 never needed a second
algorithm for the backward direction, and why `f!!` is `f`: flipping
twice puts everything back.

### 1.3 Composing is combining grids

`f ; g` means "do `f`, then `g`". So `f ; g` can get from `x` to `z` exactly when
there is some middle value `y` with `f` reaching `y` and `g` reaching `z` from
it. In grid terms: to fill in cell `(x, z)`, walk along row `x` of `f` and down
column `z` of `g`, and look for a position where **both** have a mark.

That rule, *for each middle value take AND, and across all middle values take
OR*, is what mathematicians call **matrix multiplication**, with `and` in place
of `×` and `or` in place of `+`. So 42's grids are matrices whose entries are
`0` and `1`, and `;` is matrix multiplication over those. That is all that "42
is matrices over the booleans" means.

### 1.4 Q42 puts numbers in the cells

Q42 changes one thing: a cell holds a **complex number** instead of a mark. Call
it an **amplitude**; §3.2 says what it means physically.

Here is `h`, the Hadamard gate, whose grid Q42 will print for you:

```
$ 42q matrix gates h
h : qubit <-> qubit
     |0>  [  0.707107   0.707107 ]
     |1>  [  0.707107  -0.707107 ]
```

Same 2×2 grid as `not`, but with numbers, and one of them is negative. That is
the point.

One wrinkle before going on. The grids in §1.1 put inputs in rows, which reads
naturally as "from, to". `42q matrix` prints them the other way up: its **rows are
outputs and its columns are inputs**. That is the universal convention in physics,
because a gate is written as acting on a column of amplitudes, `U|ψ>`. The two
pictures hold the same information, one being the other transposed, and the
difference does not show on `h`, whose grid happens to be symmetric. It does show on, say, `x ; s`,
where the lone `i` sits in row `|1>`, column `|0>`: the gate takes input `|0>` to
output `i|1>`.

Composition works exactly as in §1.3, with the OR and AND becoming ordinary `+`
and `×`, since that is what they were standing in for. So compose `h` with itself
and fill in the `|1>` cell of the first row: walk along `h`'s row for `|0>` and
down `h`'s column for `|1>`, multiplying and adding.

```
    via |0> :  +0.7071 x +0.7071  =  +0.5000
    via |1> :  +0.7071 x -0.7071  =  -0.5000
    total   :                        0.0000
```

The two routes **cancel**. With marks that could not have happened: `* or *` is
`*`, and more ways of reaching an answer only ever makes it more reachable. With
numbers, one route can undo another.

```
$ 42q gates hh "|0>"
hh |0>
  = |0>
```

Two Hadamards leave `|0>` exactly where it started. This is called
**interference**, it is the source of every quantum algorithm's advantage over a
classical one, and §3.5 returns to it. For now it is enough that it is arithmetic
you can check by hand.

### 1.5 The whole difference, in one table

With §§1.1–1.4 in hand, the summary is readable:

| | 42 | Q42 |
|---|---|---|
| a cell holds | a mark: reachable or not | a complex number |
| a row says | the **set** of answers | the answers, each with an amplitude |
| `;` combines grids by | AND down the middle, then OR | `×` down the middle, then `+` |
| `!` is | the grid flipped (§1.2) | flipped, and each entry conjugated |
| `+` and `*` | build a bigger grid out of two | the same, unchanged |
| more routes to an answer | only ever helps | can cancel out |

The last row is the only one that is a real difference, and every other
difference follows from it. Numbers have negatives; marks do not.

Two names for the record, since the literature uses them. A system with an
addition and a multiplication but no need for subtraction is a **semiring**;
`{0,1}` with `or`/`and` is one, and ℂ is another, so "Q42 is 42 over a different
semiring" is a one-line way to say all of the above. And flipping-and-conjugating
a matrix is called taking its **adjoint**, written `M†`. So `!` denotes the
converse of a relation in 42 and the adjoint of a matrix in Q42, which §4.1
shows is the same operation twice.

## 2. Why reversibility is forced

Before the physics, the engineering reason a computer scientist should care.

### Erasing a bit costs energy

**Landauer's principle** (1961): erasing one bit of information in a computer at
temperature `T` must dissipate at least `kT ln 2` joules as heat, where `k` is
Boltzmann's constant. At room temperature that is about `2.9 × 10⁻²¹` joules,
negligible per bit today, and a floor that no cleverness removes.

The point is *why* there is a floor. Information that is destroyed has to go
somewhere; it becomes entropy in the environment. A computation that never
destroys information has no such floor, and Bennett showed in 1973 that any
computation can be rearranged into one that doesn't. That is the origin of
reversible computing as a field, and of 42.

### Quantum mechanics has no choice at all

For quantum computers this stops being an efficiency argument and becomes a
constraint. The evolution of an isolated quantum system is described by a
**unitary** matrix (§3), and every unitary has an inverse. There is no such
thing as an irreversible quantum gate, in the way that there is no such thing as
a triangle with four sides. It is not a design decision anyone made.

So the familiar irreversible operations are simply unavailable:

```
c = a AND b
```

destroys information, since knowing `c = 0` tells you almost nothing about `a`
and `b`, so there is no two-input AND gate. What exists instead is the **Toffoli**
gate, which keeps its inputs and writes the answer into a third wire:

```
(a, b, c)  |->  (a, b, c XOR (a AND b))
```

Set `c = 0` and the third component becomes `a AND b`, with `a` and `b` still
there. This is the padding trick from the 42 manual's §11.3, where `mul` keeps its
multiplier in order to stay invertible; the same pressure produces the same
answer in both places.

### Uncomputation

Padding has a cost: the kept-around values pile up. If you compute an
intermediate `x`, use it, and no longer want it, you cannot drop it, since that
would be erasing information. You must **uncompute** it by running its producer
backwards.

The pattern is `P ; Q ; P!`: do the work, use it, undo the work. In Q42 that
is an ordinary term, because `!` is part of the language, and because every Q42
term is invertible `P!` really is `P`'s inverse. Languages like Silq spend
considerable machinery on *inferring* where this goes, so that the programmer
never has to decide. Q42 does not infer: you decide, and then writing it costs
three characters. What the language gives you is that what you wrote is exact.

---

## 3. The physics you need

- [3.1 A state is a vector of amplitudes](#31-a-state-is-a-vector-of-amplitudes)
- [3.2 Amplitudes are not probabilities](#32-amplitudes-are-not-probabilities)
- [3.3 A gate is a unitary matrix](#33-a-gate-is-a-unitary-matrix)
- [3.4 Superposition](#34-superposition)
- [3.5 Interference — the one that matters](#35-interference--the-one-that-matters)
- [3.6 Entanglement](#36-entanglement)
- [3.7 What Q42 does not model](#37-what-q42-does-not-model)

Enough to read Q42 programs, and no more. Everything here is finite-dimensional
linear algebra; nothing requires an understanding of physics.

### 3.1 A state is a vector of amplitudes

A classical bit is `0` or `1`. A **qubit** is a pair of complex numbers, one
attached to each of those two possibilities:

```
|psi>  =  c0 |0>  +  c1 |1>          c0, c1 in C
```

`|0>` and `|1>` are names for the two basis vectors. The notation `|x>` is
called a *ket* and is a way of writing "the basis vector labelled `x`". The `cᵢ` are **amplitudes**.

For `n` qubits there are `2ⁿ` basis states, `|000…>` through `|111…>`, and a
state is `2ⁿ` amplitudes. That exponential is the whole reason simulating
quantum computers is expensive, and the whole reason building them might be
worth it.

### 3.2 Amplitudes are not probabilities

The probability of seeing outcome `x` if you look is `|cₓ|²`, the squared
magnitude. This is the **Born rule**, and it is where the physics enters; the
rest is linear algebra.

Two consequences a computer scientist should internalise:

- Probabilities must sum to `1`, so `Σ |cᵢ|² = 1`. A state is a **unit vector**.
- Amplitudes can be **negative**, or complex. Probabilities cannot. This is the
  entire difference between a quantum computer and a randomised classical one,
  and everything interesting comes from it.

### 3.3 A gate is a unitary matrix

A gate on `n` qubits is a `2ⁿ × 2ⁿ` complex matrix `U` satisfying

```
U† U  =  U U†  =  I
```

where `U†` ("U dagger") is the **adjoint**: transpose the matrix and conjugate
every entry. Such a matrix is called **unitary**.

Two things follow, and they are why the condition is the one physics imposes:

- **`U† ` is `U`'s inverse.** Reversibility, for free, for every gate.
- **`U` preserves length.** Since states are unit vectors and probabilities are
  squared magnitudes, a map that changed length would produce probabilities not
  summing to `1`. Unitarity is exactly the condition "still a valid state
  afterwards".

Q42 spells `U†` as `U!`, which is the same `!` that 42 uses for running
a program backwards. It is not an analogy: in 42 the operation is the converse
of a relation, in Q42 the adjoint of a matrix, and they are the same structural
operation in two different settings (§4).

Q42 never checks unitarity, because it never has to: every primitive is unitary
and every way of combining them preserves unitarity (§6). You can audit
the claim:

```
$ 42q unitary gates
  [ok ] h ; h! = id on 2 dimension(s)
  [ok ] ccx ; ccx! = id on 8 dimension(s)
  ...
-- 24/26 unitary, 2 with no single matrix
```

### 3.4 Superposition

A state with more than one nonzero amplitude is in **superposition**. The
Hadamard gate makes one from a definite input:

```
$ 42q gates h "|0>"
h |0>
  = 0.707107|0>  +  0.707107|1>
```

`0.707107` is `1/√2`, so both outcomes have probability `(1/√2)² = 1/2`.

It is tempting, and wrong, to read this as "the qubit is secretly 0 or 1 and we
don't know which". The next section is why.

### 3.5 Interference — the one that matters

Apply `h` a second time. Classically, randomising a coin twice leaves it random.
Here:

```
$ 42q gates hh "|0>"
hh |0>
  = |0>
```

The randomness is *gone*. Follow the arithmetic. `H|0>` is `0.7071|0> +
0.7071|1>`; now apply `H` to each part and collect the results:

```
    from |0> -> |0> :  +0.7071 x +0.7071  =  +0.5
    from |1> -> |0> :  +0.7071 x +0.7071  =  +0.5      sum: +1.0
    from |0> -> |1> :  +0.7071 x +0.7071  =  +0.5
    from |1> -> |1> :  +0.7071 x -0.7071  =  -0.5      sum:  0.0
```

Two routes lead to `|1>` and they arrive with **opposite signs**, so they cancel.
This is **destructive interference**, and it has no classical counterpart:
probabilities are non-negative and adding more routes to an outcome can only
make it likelier. Amplitudes are not so constrained.

Every quantum algorithm that beats its classical rival does it this way, by
arranging for the wrong answers' amplitudes to cancel and the right answer's to
reinforce. Grover's search and Shor's factoring are both this, elaborately.

This is what 42 cannot express. Over the booleans the two routes to `|1>` would
be `1 ∨ 1 = 1`, still possible, and there is no `−1` to cancel with.
42 tells you which outcomes are *reachable*; it cannot tell you that two ways of
reaching one annihilate.

### 3.6 Entanglement

Two qubits have four basis states, and a state of the pair is four amplitudes.
Sometimes those factor into "this qubit is in state `ψ`, that one in state `φ`",
and sometimes they do not. When they do not, the qubits are **entangled** and
neither has a state of its own.

```
$ 42q gates bell "|00>"
bell |00>
  = 0.707107|00>  +  0.707107|11>
```

Both qubits are certainly equal and neither is certainly anything. The test is
mechanical: write the amplitudes as a 2×2 matrix indexed by the two qubits, and
the state is a product exactly when the determinant is zero. Here

```
c00 c11 - c01 c10  =  0.7071 x 0.7071 - 0 x 0  =  0.5
```

which is not zero, so it does not factor.

Entanglement is why Q42 needs one piece of machinery 42 did not (§7.4): a state
of a compound system is not in general a pair of states.

### 3.7 What Q42 does not model

Stated plainly, because a manual that quietly omits these would be misleading.

- **Measurement, except at the end.** Q42 computes the unitary. You may measure
  the *result* (§7.5), which is the Born rule applied to a finished state, but
  nothing collapses mid-program, so there is no measuring, branching on the
  outcome, and carrying on. §9.2 is precise about the difference.
- **Normalisation.** Q42 does not enforce `Σ|cᵢ|² = 1`. It does not need to: a
  ket you type in is a unit vector, and unitary maps preserve length, so a
  well-formed program cannot leave that set.
- **Noise, decoherence, error correction.** Nothing here is modelled.
- **Global phase.** Multiplying an entire state by a unit complex number is
  physically undetectable. Q42 tracks it faithfully anyway, which is why some
  gate identities hold only "up to phase" (§6.3).

---

## 4. Why 42 already fitted

- [4.1 `inv` and `†` are the same operation](#41-inv-and--are-the-same-operation)
- [4.2 42's primitives were the right ones already](#42-42s-primitives-were-the-right-ones-already)

Q42 differs from 42 in very little, and the reason is structural rather than
accidental.

### 4.1 `inv` and `†` are the same operation

Both settings are **dagger categories**: a structure with composition, an
identity, and an inversion operation `†` satisfying

```
(f ; g)†  =  g† ; f†                 inversion reverses composites
f††       =  f                       it is an involution
id†       =  id                      it fixes identities
```

Relations satisfy these with `†` = converse. Complex matrices satisfy them with
`†` = conjugate transpose. This is the founding observation of *categorical
quantum mechanics* (Abramsky & Coecke, 2004), and it means `rel42/core.py`'s
`dagger` function is already the right function; only the primitive table it
consults has to change.

The two laws, side by side:

```
42 :   x in P(y)      <=>   y in inv(P)(x)
Q42:   <x| P |y>       =    conj( <y| P! |x> )
```

The same law, with membership replaced by amplitude equality. `<x| P |y>` is
the matrix entry of `P` in row `x`, column `y`. You can check it:

```
$ 42q law gates h "|0>"
h |0> has 2 component(s)
  [ok ] |0>: <y|P|x> = 0.707107, <x|P!|y> = 0.707107
  [ok ] |1>: <y|P|x> = 0.707107, <x|P!|y> = 0.707107
law holds
```

### 4.2 42's primitives were the right ones already

42's primitives are the isomorphisms witnessing that `0, 1, +, ×` form a
commutative semiring: `a + b ↔ b + a`, `1 × a ↔ a`, `(a + b) × c ↔ a×c + b×c`
and so on. That collection has a name. It is a presentation of a **rig
groupoid**, and is close to the language **Π** of James & Sabry, arrived
at independently in 42.

This matters because of a result of Carette, Heunen, Kaarsgaard & Sabry
(POPL 2024): a rig groupoid extended with **two maps and three equations** is
computationally universal for quantum computing. Those two maps are §6. Q42 is
that construction, given 42's syntax.

So the whole of the difference is: the semiring changes, the primitives that are
not unitary go, and two unitary ones arrive. The evaluator, the type system and
`dagger` are 42's, unchanged.

---

## 5. What Q42 drops

- [5.1 `|` and `^` need `1 + 1 = 1`](#51--and--need-1--1--1)
- [5.2 `copy` is not the no-cloning theorem](#52-copy-is-not-the-no-cloning-theorem)
- [5.3 Where the restriction actually bites](#53-where-the-restriction-actually-bites)

Five primitives and two combining forms. Each is dropped for a reason you can
check, not by taste.

### 5.1 `|` and `^` need `1 + 1 = 1`

This one is exact. Over the booleans `x ∨ x = x`, so adding is **idempotent**.
Over ℂ, `1 + 1 = 2`.

`f | g` means "either", which as a matrix is `⟦f⟧ + ⟦g⟧`. Over the booleans
`f | f` is `f`; over ℂ it would be `2f`, which is not the same relation and not
even unitary. And `f^` is a least fixed point computed by saturation, repeating
until nothing new appears, which is only meaningful when repetition stabilises.

Write `def bad = id | id` in a Q42 file and it is refused before it runs, with
the reason: *"over C it would denote the sum of two matrices, so `f | f` would be
`2f`. Superposition comes from `v`, not from choice."* (`v` is one of the two
primitives Q42 adds; section 6.)

There is a trap worth naming. `|` *looks* like where superposition should come
from, since over ℂ it is literally adding two vectors. It is not. Superposition
comes from applying a gate (`v` or `h`) to a definite state. Keeping `|` would
buy nothing but the ability to write non-unitary sums.

### 5.2 `copy` is not the no-cloning theorem

`copy : a ↔ a × a` is dropped, and the reason is more interesting than "quantum
states can't be copied".

The **no-cloning theorem** says there is no unitary `U` with
`U(|ψ> ⊗ |0>) = |ψ> ⊗ |ψ>` for *every* `ψ`. 42's `copy` does not attempt that.
It maps each *basis* state `|x>` to `|x,x>` and extends linearly, so it sends
`|0>+|1>` to `|00>+|11>`, which is the Bell state, not `(|0>+|1>)⊗(|0>+|1>)`.
That is a perfectly legitimate quantum operation. In categorical quantum
mechanics this map, with its adjoint, is a **classical structure**, and Coecke
and Pavlović showed those correspond exactly to a choice of measurement basis.

So why is it out? Because it is not **square**. It maps a space of dimension `n`
into one of dimension `n²`, and a unitary must map a space to itself. A
length-preserving map into a *larger* space is called an **isometry**; every
unitary is an isometry, but not conversely.

`q42/rejected.42` contains nothing but `def bad = copy`, so that you can see the
refusal for yourself:

```
$ 42q rejected bad "|0>"
error: `bad` uses `copy`, a 42 primitive that Q42 does not have: the diagonal is
an isometry but not a surjection, hence not unitary. It copies basis states
only, so it is a measurement basis rather than an illegal cloner -- but it still
has no adjoint that inverts it
```

`inl`, `inr` and `zero` go for the same dimensional reason: `inl : a ↔ a + b`
embeds `ℂⁿ` in `ℂⁿ⁺ᵐ`, and `zero` is the zero matrix, which inverts nothing.
`join : a + a ↔ a` maps down rather than up, and is the mirror image of the same
problem. It was 42's only source of many-valued answers, so with it goes all
nondeterminism.

### 5.3 Where the restriction actually bites

A useful sanity check, because "not unitary" sounds more restrictive than it is.
In finite dimensions, an isometry from a space to itself is automatically
unitary, so the restriction has only two ways to catch you:

1. **The spaces differ in size**: `copy`, `inl`, `inr`. Nothing can be done;
   these are not gates.
2. **The space is infinite-dimensional.** This is the subtler one and it is why
   Q42 has no arithmetic on unbounded numbers; §8 is the worked case.

---

## 6. What Q42 adds

- [6.1 The generators](#61-the-generators)
- [6.2 Phases are the sum functor](#62-phases-are-the-sum-functor)
- [6.3 Hadamard, and "up to phase"](#63-hadamard-and-up-to-phase)
- [6.4 Control is `dist`, which you have already met](#64-control-is-dist-which-you-have-already-met)

Two primitives. Everything else in `q42/gates.42` is derived from them and from
42's existing plumbing.

### 6.1 The generators

```
omega : 1 <-> 1            a scalar; an 8th root of 1
v     : 1+1 <-> 1+1        a square root of `swapsum`
```

`omega` acts on the unit type. It is a number rather than a gate, and
multiplies whatever it is combined with. `v` acts on one qubit and squares to negation:
apply it twice and you have flipped the bit, so it is "half a NOT", which has no
classical meaning at all.

They satisfy three equations, where `S = id + (omega ; omega)`:

```
(E1)  omega^8   =  id
(E2)  v ; v     =  swapsum
(E3)  v ; S ; v =  omega^2 . (S ; v ; S)
```

(E1) and (E2) only say the two square roots exist. **(E3) is the one that does
the work.** Without it, `omega = id` would satisfy everything and the language
would collapse to classical reversible computing. (E3) says that two ways of
decomposing a rotation, around one axis then another or the other way about,
agree. That is the *Euler decomposition* of the Hadamard gate, and pinning it
down is what forces `omega` to be a genuine eighth root of unity rather than 1.
And eighth is not a choice among many. Read (E3) as an equation in `omega`, with
`v` the square root of `swapsum` that Q42 fixes, and it has exactly two
solutions: `e^{iπ/4}` and `−e^{iπ/4}`, both primitive eighth roots of unity —
nothing of order 16, and nothing that is not a root of unity at all. (The other
two primitive eighth roots satisfy it only for the conjugate square root of
`swapsum`.) A finer angle is therefore not a matter of relaxing a relation; it
needs a further generator, which is the ladder §9.4 ends on.

In the standard model `omega = e^{iπ/4}` and `v` is a specific square root of
the NOT matrix. You never write a complex number in a Q42 program; you write
`omega` and `v`.

**What the three settle, and what they do not.** They are sound: two terms they
prove equal do denote the same matrix. They are *complete* — every true equation
provable — only in fragments, namely Clifford, Clifford+T on at most two qubits,
and Gaussian Clifford+T. Beyond those, `ccz` for one, two Q42 terms can denote
the same matrix with nothing derivable from (E1)–(E3) saying so. What the
language offers in place of a proof is evaluation. Because the generators are
discrete, every amplitude lies in the ring `Z[1/√2, i]`, and `q42/exact.py`
evaluates in that ring rather than in floating point — so comparing two terms
*decides*, and does not approximate. `h ; h` and `id` are the same matrix, not
the same to twelve places, and the amplitude that cancels is absent rather than
small. That is what `42q equal` does:

```
$ 42q equal gates x x
x : qubit <-> qubit
x : qubit <-> qubit
  equal on 2 dimension(s)

$ 42q equal gates s t
s : qubit <-> qubit
t : qubit <-> qubit
  differ at row |1>, column |1>: 1i vs (0.707107+0.707107i)
```

RELATED §11 sets this against the ZX-calculus, which has a complete
axiomatisation of all of Clifford+T and makes the opposite trade to get it.

### 6.2 Phases are the sum functor

A phase gate multiplies `|1>` by a constant and leaves `|0>` alone. In 42's
notation that is `id + <something>`, the sum functor acting on the right branch
only:

```
def t = id + omega                              -- diag(1, e^{i pi/4})
def s = id + (omega ; omega)                    -- diag(1, i)
def z = id + (omega ; omega ; omega ; omega)    -- diag(1, -1)
```

```
$ 42q matrix gates s
s : qubit <-> qubit
     |0>  [  1   0 ]
     |1>  [  0  1i ]
```

Nothing was added to the language to express this. `+` already meant "switch on
the label", and a phase gate is a switch that does nothing on one branch.

**The three are one group.** Look at what `t`, `s` and `z` have in common. Each
is `id +` some power of `omega`, and by (E1) there are only eight such powers,
which under multiplication form a cyclic group of order eight. The three gates
above are its three nontrivial subgroups:

```
z  is  id + omega^4   generates  {1, -1}                  order 2
s  is  id + omega^2   generates  {1, i, -1, -i}           order 4
t  is  id + omega     generates  all eight powers         order 8
```

Nobody chose those three. They are the subgroup chain of the group `omega`
generates, written out in the language, and there is no fourth one to write.

**This is what (E3) is for.** §6.1 put its job negatively — without it `omega`
could be `id` and the language would collapse to classical reversible computing.
The useful way to say it is that (E3) fixes *which* group the phases form, and
that single choice carries the physical content of the language. The phases the
Clifford gates give you are exactly the order-four subgroup: `s`, `z`, and
nothing finer. Circuits confined to it are efficiently simulable on an ordinary
computer by the Gottesman–Knill theorem, entanglement and interference included
(§9.3). Order eight is Clifford+T, and is not. **The step from `s` to `t` is the
step from a theory a laptop can simulate to one it cannot**, and in group terms
it is one rung of that chain.

The idea has a name outside Q42. Coecke & Duncan attach to each observable the
group of phases available to it — its *phase group* — and show the invariant is
sharp enough to separate physical theories: the qubit stabiliser theory and
Spekkens' toy model agree about very nearly everything and differ in this, `Z₄`
against `Z₂ × Z₂`, and that difference is exactly where the non-locality of the
GHZ state lives. Q42's phase group is `Z₈`. RELATED §11.4 sets the two calculi
side by side generator for generator.

### 6.3 Hadamard, and "up to phase"

```
def h = <scale by omega> (x ; s ; v ; s ; x)
```

which is the Euler decomposition of §6.1 written out. Note that `x ; s ; v ; s ; x`
is a palindrome, so for once it reads the same in either direction.

The `omega` in front is a **global phase**. Physically it is undetectable, since
no measurement can distinguish `|ψ>` from `e^{iθ}|ψ>`, so many gate identities
in the literature hold only "up to phase". Q42 tracks it exactly anyway, which is
why `h` comes out as the textbook matrix on the nose rather than nearly:

```
$ 42q matrix gates h
h : qubit <-> qubit
     |0>  [  0.707107   0.707107 ]
     |1>  [  0.707107  -0.707107 ]
```

### 6.4 Control is `dist`, which you have already met

A **controlled** gate applies its target gate only when the control qubit is
`|1>`. That is a conditional, and 42 does conditionals with `dist` (the 42
manual, §12.5). So:

```
def mat    = dist ; (unitprod + unitprod)       -- (1+1) x A  <->  A + A
def ctrl m = mat ; (id + m) ; mat!
```

split on the control bit, apply `m` on the `R` branch only, put it back. Every
controlled gate is one line:

```
def cx    = ctrl x                              -- CNOT
def ccx   = ctrl cx                             -- Toffoli
def cswap = ctrl swap                           -- Fredkin
```

The inferred type says what control requires and nothing more:

```
ctrl : (a <-> a) -> (qubit x a <-> qubit x a)
```

the target must be an *endo*-relation, with the same type in and out, because
both branches of `id + m` have to meet the `A + A` that `mat` produces.

And its adjoint needs no definition. `ctrl! m` is `ctrl m!`, which in physics is
`(Ctrl U)† = Ctrl U†`: the adjoint of a controlled gate is the controlled
adjoint. That falls out of how `!` treats a parameter and is not arranged.

---

## 7. Writing programs

- [7.1 A qubit is `1 + 1`](#71-a-qubit-is-1--1)
- [7.2 Registers and kets](#72-registers-and-kets)
- [7.3 The commands](#73-the-commands)
- [7.4 Superpositions in, and why that needed new machinery](#74-superpositions-in-and-why-that-needed-new-machinery)
- [7.5 Measuring the result](#75-measuring-the-result)

### 7.1 A qubit is `1 + 1`

There is no qubit type. As in 42, a two-case choice carrying no data is `1 + 1`,
and the two cases are `L ()` and `R ()`. Q42 calls them `|0>` and `|1>` when
printing, and a file may name the type:

```
type qubit = 1 + 1
```

which is a printing abbreviation and changes nothing (the 42 manual, §3.7).

### 7.2 Registers and kets

Several qubits are a nested pair, to the right:

```
|abc>   is   (a, (b, c))
```

You write states as kets on the command line: `"|0110>"`, or just `"0110"`.
Only *basis* states can be written down, which is deliberate. You make
superpositions by applying a gate.

### 7.3 The commands

```
42q FILE GATE STATE [-b]     apply a gate to a state
42q sample  FILE GATE STATE  apply it, then measure -- see section 7.5
42q law     FILE GATE STATE  check that `!` really is the adjoint
42q unitary FILE [GATE]      check `t ; t! = id` over the whole basis
42q matrix  FILE [GATE]      print the matrix
42q equal   FILE GATE GATE   decide whether two gates are the same -- 6.1
42q emit    FILE [GATE]      write it out as OpenQASM 3 -- see section 9.4
42q type    FILE [GATE]      infer the type
42q show    FILE [GATE]      print a definition and its adjoint
```

`matrix` and `unitary` need to know how big the space is, and the *type* is what
tells them. Most gates are more polymorphic than "a gate on n qubits": `x` is
just `swapsum`, so its type is `a + b <-> b + a`. Those two commands therefore
take `--qubits N`, to read a type at a given width:

```
$ 42q matrix gates cswap --qubits 3
cswap : qubit x (qubit x qubit) <-> qubit x (qubit x qubit)
   |000>  [ 1  0  0  0  0  0  0  0 ]
   ...
   |101>  [ 0  0  0  0  0  0  1  0 ]
   |110>  [ 0  0  0  0  0  1  0  0 ]
   ...
```

### 7.4 Superpositions in, and why that needed new machinery

42 applies a program to one value at a time and unions the results. Q42 cannot
quite do that, and the reason is entanglement.

A *basis* value like `(a, b)` is always a product: qubit `a` and qubit `b`,
separately. So applying `f * g` to a basis value can be done componentwise, and
Q42's evaluator does what 42's does there. Entanglement appears only
when you **add** such results together, which happens when the input is already
a superposition. So Q42 has one function 42 has no need for, `apply_vec`, which
applies a gate to a whole state rather than to a basis value.

You see this in `bell`: applied to `|00>` it is a single column, but the answer
is a state that no pair of single-qubit states could produce.

### 7.5 Measuring the result

`42q FILE GATE STATE` shows you the state. `42q sample` measures it, which is what
a real device would do:

```
$ 42q sample gates bell "|00>"
bell |00>
    outcome   exact  drawn
    |00>   50.0%     63  ###############
    |11>   50.0%     37  ###############
  -- 100 shots, seed 0
```

Two columns, deliberately. **exact** is the Born probability `|amplitude|²`,
which only a simulator can know. **drawn** is a sample of that many shots, which
is all a real machine would give you. Seeing them together is the point: it shows
what measurement costs you.

`--shots N` sets how many draws, and `--seed S` fixes them so a transcript stays
true. The probabilities never need renormalising: a Q42 program starts from a
unit vector and every term is unitary, so they already sum to 1.

**Measuring only some qubits.** `--bits` takes the positions you care about,
counting from 0, and reports the distribution over those alone:

```
$ 42q sample deutsch dnot "|01>" --bits 0
    outcome   exact  drawn
    |1_>  100.0%    100  ##############################
```

The `_` marks a qubit that was not measured. That is §8.4's algorithm answering
its question: **one query, one qubit, and the answer is certain.**

Measurement is *terminal*: it happens after the program, never inside it. That
is a deliberate line rather than a limitation of the command, and §9.2 explains
what it costs and why.

---

## 8. Worked examples

- [8.1 Fibonacci: why the obvious version cannot exist](#81-fibonacci-why-the-obvious-version-cannot-exist)
- [8.2 What works: fix the width](#82-what-works-fix-the-width)
- [8.3 The quantum part](#83-the-quantum-part)
- [8.4 Deutsch's algorithm, and what Q42 shows you](#84-deutschs-algorithm-and-what-q42-shows-you)
- [8.5 Teleportation, without measuring in the middle](#85-teleportation-without-measuring-in-the-middle)

A useful exercise, because the obvious approach is impossible and the reason is
instructive.

### 8.1 Fibonacci: why the obvious version cannot exist

In a reversible functional language you would write Fibonacci over the natural
numbers, `fib : nat <-> nat * nat`. Q42 cannot have that, and not for want of a
feature.

`nat` is `mu X. 1 + X`, an infinite type. Its space is infinite-dimensional,
and Q42 has only finite-dimensional spaces. Ask for a basis and it says so:

```
cannot enumerate a recursive type: it is infinite, and Q42 has no
infinite-dimensional spaces
```

Underneath that is something sharper. `succ` is `inr`. On `nat`, `succ` is
injective, since no two numbers have the same successor, but **not surjective**,
because zero is nobody's successor. In finite dimensions that combination is
impossible (§5.3); in infinite dimensions it is the standard example of an
isometry that is not unitary, called the **unilateral shift**. Its adjoint is
not its inverse: shifting up then down gets you back, but down then up loses
zero.

So: Q42 has no successor, hence no naturals, hence no unbounded arithmetic. This
is what "unitary" means, not a gap in the implementation.

### 8.2 What works: fix the width

Real quantum hardware has registers of fixed size and does arithmetic **mod
2ⁿ**. Do the same and the recurrence

```
(a, b)  |->  (b, a + b  mod 2^n)
```

becomes a *permutation* of the `2ⁿ × 2ⁿ` basis states. The matrix `[[0,1],[1,1]]`
has determinant `−1`, which is invertible mod `2ⁿ`, so the permutation is
unitary and therefore expressible. `q42/fib.42` does it on two 2-bit registers:

```
def add4     = cc03 ; cx02 ; cx13              -- (x,y) -> (x, x+y mod 4)
def swapregs = assocprod ; swapprod ; assocprod!
def fib      = swapregs ; add4
```

`add4` is three gates because `y += x` is "if `x₀` then `y += 1`" followed by
"if `x₁` then `y += 2`", and a two-bit increment is `CNOT` then `X`. `swapregs`
is three *primitives* and no gates at all: reassociate so the halves are
adjacent, swap them, reassociate back.

Iterating gives the Fibonacci numbers mod 4:

```
step  0: register = (0, 1)     F_0  = 0
step  3: register = (2, 3)     F_3  = 2
step  5: register = (1, 0)     F_5  = 5,  mod 4 = 1
step 10: register = (3, 1)     F_10 = 55, mod 4 = 3
```

and since it is unitary, running it backwards recovers the seed exactly, rather
than "a set containing the seed", which is what 42 would give you. Its order is 6,
which is the Pisano period of 4.

### 8.3 The quantum part

Everything above is a permutation, so it is reversible *classical* computing and
42 could do it too. What Q42 adds is that the seed may be a superposition:

```
def qfib = hy0 ; fib
```

puts one bit of the seed through a Hadamard first, after which the register
holds two Fibonacci orbits at once and every later step advances both. The whole
thing still inverts exactly.

### 8.4 Deutsch's algorithm, and what Q42 shows you

Fibonacci is arithmetic. Deutsch's algorithm is a real quantum algorithm, the
smallest one there is and the first found to beat its classical rival.

The problem: you are handed a black box computing an unknown one-bit function
`f`, and asked whether `f` is **constant** (`f(0) = f(1)`) or **balanced**
(`f(0) ≠ f(1)`). Classically you must evaluate `f` twice, since one evaluation
tells you nothing about the other. Deutsch's algorithm answers after one.

The oracle has to be reversible like everything else, so it takes the standard
shape `(x, y) ↦ (x, y XOR f(x))`. That is the Toffoli trick from §2,
which is also `mul` keeping its multiplier in the 42 manual's §11.3. There are only
four one-bit functions, so `q42/deutsch.42` writes all four out:

```
def orc0   = id                              -- f(x) = 0       constant
def orc1   = id * x                          -- f(x) = 1       constant
def orcid  = ctrl x                          -- f(x) = x       balanced
def orcnot = (x * id) ; ctrl x ; (x * id)     -- f(x) = not x   balanced
```

**The algorithm** is three steps: superpose both inputs, query the oracle once,
and interfere the results back together.

```
def d0 = (h * h) ; orc0 ; (h * id)
```

Now run each of the four, and watch the **first** qubit:

```
$ 42q deutsch d0 "|01>"
d0 |01>
  = 0.707107|00>  +  -0.707107|01>

$ 42q deutsch dnot "|01>"
dnot |01>
  = -0.707107|10>  +  0.707107|11>
```

For `d0`, every term begins `|0`. For `dnot`, every term begins `|1`. The other
two behave the same way as their partner: **the first qubit is `|0>` for a
constant `f` and `|1>` for a balanced one, with certainty.** One query, and the
answer is not probable but definite.

And it will say so outright if you measure the first qubit (§7.5):

```
$ 42q sample deutsch dnot "|01>" --bits 0
    outcome   exact  drawn
    |1_>  100.0%    100  ##############################
```

But the *state* is the more instructive output, and worth pausing on. A device
hands you one bit and hides the mechanism. Q42 shows you the amplitudes, so you
can see the second qubit's `+/-0.707107` carrying the phase the oracle deposited
and the final Hadamard converts into the answer. For understanding *why* an
algorithm works, as opposed to what it returns, that is worth more than a
sample. §9.1 returns to this.

### 8.5 Teleportation, without measuring in the middle

Teleportation is the textbook example of an algorithm that *requires* measuring
half way through. Alice measures her two qubits, sends Bob two classical bits,
and Bob applies `X` and/or `Z` depending on what they say. Q42 has no mid-circuit
measurement (§9.2), so this ought to be impossible.

It is not, and the reason is a theorem. The **principle of deferred measurement**
(Nielsen & Chuang §4.4) says that any circuit with mid-circuit measurements and
classically-controlled gates can be rewritten with every measurement moved to the
*end*, each classical control replaced by a **quantum** control. Q42 has quantum
control, namely `ctrl`, so the rewritten circuit is an ordinary Q42 term.

`q42/teleport.42` is that circuit, and the deferral is visible in one line:

```
def bell  = (id * (h * id)) ; (id * cx)      -- entangle q1 with q2
def alice = (ctrl (x * id)) ; (h * id)       -- CNOT q0->q1, then H on q0
def bob   = (id * cx) ; (ctrl (id * z))      -- CNOT q1->q2, CZ q0->q2
def tele  = bell ; alice ; bob
```

`bob` is where "if Alice's bit is 1, apply X" became a CNOT: the same conditional,
controlled by the qubit rather than by a bit read out of it.

It is unitary like everything else:

```
$ 42q unitary teleport tele --qubits 3
  [ok ] tele ; tele! = id on 8 dimension(s)
```

Sending `|0>` proves little, so prepare a real state on `q0`, a superposition
with a phase, teleport it, and apply the preparing gate's inverse to `q2`. If the state genuinely arrived, amplitudes and phase
intact, `q2` must return to `|0>` with certainty:

```
$ 42q sample teleport check "|000>" --bits 2
    |__0>  100.0%    100  ##############################
```

It does. The deferred measurements have not vanished: they are the other two
qubits, which end up spread evenly over all four outcomes, exactly the four
results Alice would have read:

```
$ 42q teleport checkh "|000>"
  = 0.5|000>  +  0.5|010>  +  0.5|100>  +  0.5|110>
```

So the canonical mid-circuit algorithm runs here today, unchanged and unitary.
That is the strongest single argument in §9.2 for leaving the language alone.

---

## 9. What Q42 is, and is not, for

- [9.1 What it is for](#91-what-it-is-for)
- [9.2 Where the language stops](#92-where-the-language-stops)
- [9.3 The comparison that is not the right one](#93-the-comparison-that-is-not-the-right-one)
- [9.4 Could a Q42 program run on real hardware?](#94-could-a-q42-program-run-on-real-hardware)

### 9.1 What it is for

A fair reading of a list of limitations is "then what use is it?", so the useful
part first.

**Expressiveness.** `omega` and `v` generate Clifford+T, the standard universal
gate set, so any unitary can be approximated to any precision you like and
Clifford+T circuits are represented exactly. Grover's diffusion operator, Shor's
modular arithmetic, the quantum Fourier transform: all writable. §8.4 writes out
Deutsch's algorithm in six lines.

**Gate identities, checked mechanically.** `√Π`'s contribution is an *equational
theory*, a set of rules for proving two circuits equal, and Q42 makes it
executable. `42q law` checks that `!` really is the adjoint; `42q unitary` checks
`t ; t! = id` across a whole library; `42q matrix` prints the matrix so you can
compare. Gate identities like `H ; H = id`, `H ; X ; H = Z`, `S ; S = Z` and
`(Ctrl U)† = Ctrl U†`: all of these can be run, and each is a test in
`tests/test_q42.py`.

**Amplitudes and samples, side by side.** `42q sample` measures a result as a
device would, and prints the exact Born probabilities next to the draw (§7.5).
So Deutsch's question gets an answer, `|1_> 100.0%`, while the state that
produced it stays visible: `-0.707107|10> + 0.707107|11>`, from which you can
see why the first qubit is certainly `|1>`. A real machine gives you only the
right-hand column, and for learning or debugging a circuit, having both is worth
more than either.

**Uncomputation as a term.** It is `P ; Q ; P!`, and because every Q42 term is
invertible, `P!` really is `P`'s inverse — the undo is derived from the forward
term rather than written a second time and trusted to match.

Be accurate about the comparison, though, because it is easy to overstate. Silq's
contribution is *safe, automatic* uncomputation: its point is that the programmer
never decides where the undo goes. Q42 is in the category Silq set out to improve
on, the one where you trigger it yourself — as Quipper's `with_computed` and Q#'s
`ApplyWith` do. What Q42 adds within that category is that the inverse is a
syntactic consequence of the forward term instead of a second definition to keep
in step, and that invoking it costs three characters. That is a smaller claim
than Silq's, and a different one.

**Evidence for a claim about language design.** `q42/` shares `Value`, `Term`,
the parser and the whole type checker with `rel42/`, and `q42.dagger is
rel42.dagger`, the same function object. The claim being
demonstrated is that 42's primitives are not a curated set but a forced one, so
that reaching quantum computing is a change of number system rather than a new
language. Q42 existing, and being this small, is the argument.

**What the change of semiring costs.** Worth saying beside the claims it
qualifies. 42's unusual property is the one §5 removed: its programs denote
relations and may give many answers, in both directions at once. Unitaries are
bijections, so Q42 does not have it — §4 puts Q42 where Π is, and the property
that separated 42 from the other reversible languages is exactly the one the
change of number system gives up. Nothing above depends on it. The case for Q42
is the paragraphs above; it is not that Q42 inherited what made 42 unusual,
because it did not.

### 9.2 Where the language stops

Q42 is a language for the **unitary layer** of quantum computing, with
measurement at its edge. That sentence is the boundary, and it is chosen rather
than unfinished: it is what buys every property in §9.1.

**Inside the line.** Every term denotes a unitary, so `!` is defined on every
term with no side conditions, `t ; t! = id` holds by construction, and
`42q unitary` can assert it over a whole file. Measurement sits at the end:
`42q sample` applies the Born rule to the state the program produced (§7.5).
That is an operation on the *output*, not a term in the language, which is
exactly why it costs the language nothing.

**Outside the line: measuring half way through, branching on the result, and
carrying on.** Q42 has no such term and is not going to acquire one. Measurement
is not unitary, being neither invertible nor deterministic, so a
`measure` term would be one for which `!` has no answer, and every property in
the paragraph above would become conditional: unitary *except* where a
measurement appears. The literature reaches the same conclusion and treats
measurement as a layer over a unitary core rather than a primitive inside it. The
construction is Carette et al., *The Quantum Effect*, and it is worth seeing how
much machinery it takes. Measurement there is not a primitive but a derived
term, `measure_Z = copy_Z ≫ fst`, where `fst` needs a `discard` that arrives
with a further *hiding* arrow layered on top; and the resulting model is one of
**partial maps**, landing in the category of finite-dimensional Hilbert spaces
and linear *contractions* rather than unitaries. The authors are candid about the
cost, noting that their `discard` postulate "is dangerous, as it does not enforce
that it is only applied to total maps".

That is the formal content of the line drawn here. Adding measurement is not an
addition to a unitary language; it is leaving the unitary category. Q42 stays.

The line also costs no expressiveness. The **principle of deferred
measurement** (Nielsen & Chuang §4.4) is a theorem: any
circuit that measures mid-way and applies gates conditioned on the classical
outcome can be rewritten with the measurements moved to the end and the control
made quantum, which is what `ctrl` does. So the missing construct is a
convenience of execution rather than a source of computational power.

`q42/teleport.42` is that theorem made concrete. Quantum teleportation is the
example usually offered as *the* reason a language needs mid-circuit
measurement, and it runs here unchanged, as a single unitary on three qubits:

```
$ 42q unitary teleport tele --qubits 3
  [ok ] tele ; tele! = id on 8 dimension(s)
```

Alice's two classical bits are never extracted; her four possible outcomes stay
in superposition and Bob's corrections are applied with `ctrl` instead. §8.5
works through it, including the check that a state carrying a genuine phase
arrives intact.

The same holds for **Shor's algorithm**, which is often assumed to need
mid-circuit measurement and does not: its quantum part is one unitary followed
by one measurement, and the continued-fraction step and the retry loop are
ordinary classical code *around* that subroutine. Q42 hands you the measured
value and a script does the rest.

What is genuinely on the far side of the line is narrower than it first looks:
**error correction**, where syndromes are measured and acted on repeatedly while
the computation continues; **measurement-based computing**, whose entire model is
adaptive measurement; and **qubit reuse**, which matters when hardware has a fixed
qubit budget and not at all in a simulator. None of these is what Q42 is for.

Two smaller boundaries follow from the same place:

- **No mid-program state preparation.** A Q42 program is a unitary on a fixed
  space, so there is no conjuring a fresh `|0>` half way through; that would
  change the dimension. Inputs come from the command line instead.
- **No noise.** No decoherence, no gate fidelities, no error model. Everything
  here is the idealised unitary layer.

### 9.3 The comparison that is not the right one

An `n`-qubit gate is a `2ⁿ × 2ⁿ` matrix, so running Q42 costs exponential time
and memory. It is worth being precise about what that does and does not mean.

It does **not** distinguish Q42 from other quantum languages. Every classical
simulator of quantum circuits pays this, Qiskit's included; it is a fact about
simulating quantum mechanics on a classical machine, not about this
implementation. A quantum *language* is not in competition with quantum
*hardware*: Q42's peers are Silq, Π and Quipper, not a superconducting chip.

There is one genuine nuance. By the **Gottesman–Knill theorem**, circuits built
only from Clifford gates (`h`, `s`, `cx`) are efficiently simulable classically,
despite looking thoroughly quantum, entanglement and interference included. So
"quantum-looking" and "hard to simulate" are not the same property. It is `t`
that takes a circuit beyond Clifford, and Q42 has `t`. §6.2 says the same thing
as a fact about groups rather than about simulation: `s` generates the
order-four phase group and `t` the order-eight one, and the boundary
Gottesman–Knill draws falls between them.

In summary: Q42 is a language and a proof-checker for the unitary
layer of quantum computing, complete for that layer, with measurement at its
edge (§9.2) and simulation cost as the price everybody pays.

### 9.4 Could a Q42 program run on real hardware?

It can, once machines are stable and large enough: `42q emit` writes any
definition out as OpenQASM 3, which every mainstream toolchain reads. This
section says why the language sits well for that, what the emitter does, and
where the real limit is.

The language is well placed for it. A Q42 program already is a unitary circuit
in a fault-tolerant gate set: `omega` and `v` generate Clifford+T, which is what
surface-code architectures target, and what T-count, the standard cost measure
for such machines, is counted in. Nothing needs translating into another model of
computation.

Better, most of the language costs nothing to execute. Classifying each primitive
by what it does to the underlying bits:

| primitive | effect on the bits | on hardware |
|---|---|---|
| `id`, `assocsum`, `assocprod`, `unitsum`, `unitprod`, `dist` | nothing at all | **free** |
| `swapprod` | permutes them | a relabelling, or a SWAP |
| `swapsum` | flips one | Pauli X |
| `omega` | nothing, but multiplies by a phase | a phase gate |
| `v` | superposes them | √X |

Only **three of the ten** are physical operations, and they are exactly X, phase
and √X. Everything else is the semiring plumbing of §1.5, and plumbing is
compile-time bookkeeping: `assocprod` regroups `a × (b × c)` into `(a × b) × c`
and the bit string is untouched, while `unitsum` removes a tag whose other branch
is uninhabited, `0 + qubit` and `qubit` being both two-dimensional, so there was
never a bit there to move.

Inlining the library bears this out:

```
  gate     structural  physical   which physical operations
  ccx              14         1   {swapsum: 1}
  cswap             7         1   {swapprod: 1}
  bell             12         9   {omega: 5, swapsum: 3, v: 1}
```

A Toffoli is fourteen structural steps and **one** real gate. Every `ctrl` is
`dist`-plumbing wrapped round a single operation, which is a direct consequence of
the primitives being the semiring isomorphisms rather than a hand-picked set.

Not every type is a qubit register. `a + b` has dimension `dim(a) + dim(b)`,
which need not be a power of two: `1 + (1 + 1)` is a *qutrit*, a perfectly good
three-dimensional space with no qubit realisation.
Q42 itself does not care, because it evaluates in any finite dimension; a
compiler would, and the condition it needs is not "is the dimension a power of
two" but a recursive width:

```
width(1)      = 0
width(a x b)  = width(a) + width(b)
width(a + b)  = 1 + width(a),  provided width(a) = width(b)
```

a sum is a register exactly when both branches are the same width, and then the
tag is one qubit and the branches share the rest. That correctly accepts
`(1+1) + (1+1)` as two qubits and rejects `1 + (1+1)`. It is `q42.types.width`,
and it returns `None` for the types that are not registers, among them `0`, a
variable and a `mu`, the last because Q42 has no infinite-dimensional spaces.

In practice it does not bite: **every non-combinator definition in every Q42
library is register-shaped**, across `gates.42`, `fib.42`, `deutsch.42`,
`teleport.42`, `grover.42`, `gsum.42`, `qft3.42` and `classical.42`, with none
rejected. Programs people actually write in this language are already circuits.

**Measurement.** *Terminal* measurement is part of the tooling today (§7.5):
run the unitary, then sample the result. It is the Born rule and a random
number, nothing more. It covers every algorithm whose last step is a single
measurement: Deutsch, Bernstein–Vazirani, Grover, and the quantum subroutine of
Shor.

```
$ 42q sample deutsch dnot "|01>" --bits 0
    |1_>  100.0%    100
```

*Mid-circuit* measurement is outside the language by design (§9.2), and by the
deferred measurement principle a compiler can always work without it: the circuit
it would emit is the one Q42 already describes, with quantum control where a
device might have used a classical wire. What that trade costs on real hardware,
and what a compiler could do about it, is the last paragraph below.

**An emitter, not a backend.** Q42 writes circuits; it does not drive machines,
and the distinction is smaller than "no backend" makes it sound. The hard parts
of getting a circuit onto a device are commodity. Those are **routing**, because
real hardware cannot apply a two-qubit gate to an arbitrary pair, and **rotation
synthesis**, because `omega` is only an eighth root of unity, so finer angles
must be approximated into many T gates. Any existing quantum compiler does them for
anything handed over as OpenQASM 3 or QIR. They are not Q42's to write.

What is Q42's own is the lowering, and it is short. Two parts:

- **wire assignment**: which physical qubit is which position in the nested pair,
  the width rule above read constructively, plus tracking `swapprod` as a
  permutation carried to the end so that it costs nothing instead of three CNOTs.
  That is exactly what `q42/emit.py` does, and it is why **seven of the ten
  primitives emit no gate at all**: `id`, `assocprod`, `unitprod` and `dist`
  re-bracket, `swapprod` is carried in the layout, and `assocsum` and `unitsum`
  cannot occur at a register type in the first place. Only `swapsum`, `omega` and
  `v` produce output.
- **depth bounding**: a circuit is finite, so a recursive definition must unroll
  to a fixed depth, and the emitter does not check that it does; it stops on a
  depth budget rather than proving termination.

Control needs no rule of its own, which is worth knowing: at a type `a + b` the
first qubit is the tag, and `f + g` means f under tag 0 and g under tag 1. From
that alone, `cx`, `ccx` and the Fredkin come out as single gates, and
`t = id + omega` derives as the T gate, a controlled global phase being a
relative one. The emitter never mentions `ctrl`, which is right, `ctrl`
being a library definition rather than a language feature.

Every definition in every Q42 library emits, and each is checked against Q42's own
matrix by a simulator in `tools/qasm_sim.py` that deliberately shares no code with
the evaluator. What comes out is unoptimised, with `z` leaving as four
eighth-turn phases, because correctness came first and the downstream transpiler
folds most of it.

There is also one piece that is not commodity, because no previous language
needed it. Q42 defers every measurement (§9.2), and on hardware deferral is not
free: it spends coherence time and forbids reusing a qubit. So a serious lowering
would want to run the deferred measurement principle backwards: recognise a
`ctrl` whose control qubit is never touched again, and emit measure-and-branch
where the term says quantum control. That is a rewrite over a program Q42 already
expresses, not a feature the language lacks.

In summary, Q42 is a plausible front end and not a plausible toolchain, which is
the shape to aim at rather than a shortfall. Its semantics are the right ones,
its plumbing is free, its libraries all describe genuine registers, and the
measurement it does not have is one a compiler can do without.

It translates into a circuit format the rest of the world already compiles, and
the emitter's own gaps are the two small ones named above. The remaining limit
is the gate set. `omega` is an eighth root of unity, so the unitaries Q42 can
write down are exactly those over `Z[1/√2, i]` — Clifford+T, and nothing finer.
That is not a limit on what Q42 can compute: Clifford+T is universal, and any
rotation is reachable to precision ε with a T-count logarithmic in 1/ε. It is a
limit on what Q42 can *name*. An `Rz(π/7)` must arrive already synthesised, where
a device with native rotations would have applied it as one pulse.

Against the machines this section opened with, that is not a shortfall at all:
on a surface code arbitrary rotations are the expensive thing, and being confined
to the distilled set is what makes T-count meaningful in the first place. It is a
shortfall only against today's devices, which are not the target.

Nor is that an artefact of the surface code. Eastin–Knill: for any code, the
operations that can be applied to each physical qubit independently — the only
ones that do not let one error breed into many — form a finite set, and a finite
set is never enough to compute with. Every protected machine therefore has a
limited cheap alphabet and a discrete expensive extra. A cheap continuum of
angles belongs to the unprotected era, not the mature one.

Lifting it would buy device-generality. It would not falsify §6 — (E1), (E2) and
(E3) go on holding — it would end their sufficiency: two constants would no longer
generate, and phases would become an indexed family rather than a primitive. A
cyclotomic Q42, one root of unity per level, would keep exact evaluation and
decidable equality and lose only the finite presentation. Going the whole way, to
a continuum of angles, loses exactness itself, and with it the property that a Q42
program *has* a matrix rather than an approximation to one. That last trade is the
one the language is made of.

Read beside §6.2, the three arguments this section has made turn out to be one.
The phases of Q42 form `Z₈`, a finite subgroup of the circle. A cyclotomic Q42 is
a larger finite subgroup, `Z₁₆` or `Z₃₂`. The continuum is the circle itself. And
Eastin–Knill is the statement that no machine which corrects its errors can offer
you the circle: its cheap alphabet is finite, so it sits somewhere on that ladder
and never at the top. So *why eight*, *what would lifting cost*, and *why is the
restriction not an artefact of one architecture* are one question asked three
times — **which finite subgroup of the phase group do you take, and what does the
choice buy** — and Q42's answer is the smallest rung at which the language is
universal at all, with `v` and the plumbing held fixed.

---

## 10. Reference

### Primitives

The rig-groupoid core, identical to 42's and unitary because each is a
permutation matrix:

| | |
|---|---|
| `id` | identity |
| `swapsum`, `assocsum`, `unitsum` | `a+b ↔ b+a`, `a+(b+c) ↔ (a+b)+c`, `0+a ↔ a` |
| `swapprod`, `assocprod`, `unitprod` | `a×b ↔ b×a`, `a×(b×c) ↔ (a×b)×c`, `1×a ↔ a` |
| `dist` | `(a+b)×c ↔ (a×c)+(b×c)` — and so every conditional |

plus the two generators:

| | |
|---|---|
| `omega` | `1 ↔ 1`, an 8th root of unity |
| `v` | `1+1 ↔ 1+1`, a square root of `swapsum` |

Absent, with reasons in §5: `zero`, `inl`, `inr`, `copy`, `join`, `|`, `^`.

### Gates in `q42/gates.42`

| | |
|---|---|
| `x`, `y`, `z` | the Pauli gates; `x` is `swapsum` |
| `h` | Hadamard — makes and unmakes superpositions |
| `s`, `t` | phase gates, `diag(1, i)` and `diag(1, e^{iπ/4})` |
| `v`, `vdg`, `sdg`, `tdg` | square root of NOT, and the adjoints |
| `swap` | `swapprod` |
| `ctrl m`, `nctrl m` | control on `\|1>`, control on `\|0>` |
| `cx`, `cz`, `ch`, `cv` | controlled one-qubit gates |
| `ccx`, `ccz` | Toffoli, controlled-Z-on-two |
| `cswap` | Fredkin |
| `bell`, `ghz` | the two standard entangled states |

### Commands

| | |
|---|---|
| `42q FILE GATE STATE` | apply a gate; `-b` for its adjoint |
| `42q sample FILE GATE STATE` | apply it and measure; `--shots`, `--seed`, `--bits` |
| `42q law FILE GATE STATE` | check that `!` is the adjoint |
| `42q unitary FILE [GATE]` | check `t ; t! = id` over the basis |
| `42q matrix FILE [GATE]` | print the matrix; `--qubits N` to fix a width |
| `42q equal FILE GATE GATE` | decide whether two definitions are the same gate |
| `42q emit FILE [GATE]` | write it out as OpenQASM 3; `--qubits N`, `--gates` |
| `42q type FILE [GATE]` | infer the type |
| `42q show FILE [GATE]` | print a definition and its adjoint |

### Source files

```
type qubit = 1 + 1                  -- a printing abbreviation
def  name   = gate
def  name m = gate                  -- m is a parameter, standing for a gate
-- comments run to end of line
```

`q42/classical.42` uses only primitives that 42 *also* has, so the same file runs
under either interpreter, which is one way to see that `omega` and `v` buy
nothing classical.

### Further reading

The gate libraries and worked examples named above are files in the 42
repository, at <https://github.com/ubrowz/42>, along with both interpreters.
Clone it and each one runs with the `42q` command of §7: `42q gates bell "|00>"`
reads `q42/gates.42`, finds `bell` in it, and applies it.

- [The 42 manual](MANUAL.md) — the language this one is built on. Read it
  first.
- [Related work](RELATED.md) — where 42 and Q42 sit in the literature.
- Carette, Heunen, Kaarsgaard & Sabry, *With a Few Square Roots, Quantum
  Computing is as Easy as Π*, POPL 2024 — the result §4.2 and §6 rest on.
- Eastin & Knill, *Restrictions on Transversal Encoded Quantum Gate Sets*,
  PRL 102 110502, 2009 — why the cheap gate set of §9.4 is finite on any
  machine that corrects at all.

---

## Appendix: a program and its circuit

§9.4 says a Q42 definition lowers to OpenQASM 3 and that most of the language
costs nothing to execute. This appendix does it once, in full, on the smallest
program worth the trouble.

### The program

`bell` prepares the entangled pair of §3.6. Two operators:

```
$ 42q show gates bell
bell   = h * id ; cx
bell!  = cx! ; h! * id!
```

Read it as: Hadamard the left qubit, leave the right one alone, then a
controlled-NOT. The adjoint was not written by anyone; it is the same
definition read backwards.

### The circuit

```
$ 42q emit gates bell
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;

gphase(0.78539816339744828);
x q[0];
p(0.78539816339744828) q[0];
p(0.78539816339744828) q[0];
gphase(2.3561944901923448);
p(1.5707963267948966) q[0];
h q[0];
p(1.5707963267948966) q[0];
p(0.78539816339744828) q[0];
p(0.78539816339744828) q[0];
x q[0];
cx q[0], q[1];
```

Twelve instructions for a two-operator program, and one qubit register of
exactly the width the type demands.

### Why twelve

Because `h` is not a primitive here. Q42 has ten primitives (§10), and the
Hadamard is a definition over two of them:

```
def hcore = x ; s ; v ; s ; x
def h     = unitprod! ; (omega * hcore) ; unitprod
```

with `s = id + (omega ; omega)`. Expand that and the emitted sequence reads off
in order:

| in the term | emitted |
|---|---|
| `omega` | `gphase(π/4)` |
| `x` | `x q[0]` |
| `s` | two `p(π/4)`, an eighth turn each |
| `v` | `gphase`, `p(π/2)`, `h`, `p(π/2)` — the square root of NOT |
| `s` | two more `p(π/4)` |
| `x` | `x q[0]` |
| `cx` | `cx q[0], q[1]` |

Nothing is looked up in a table of gate translations. The circuit is what the
term says once the definitions are expanded, which is why the T-count of a Q42
program is a property of the program rather than of the compiler.

### What did not emit

Three things in that term produce no instruction at all:

- the `id` in `h * id`, which is the right qubit being left alone;
- both halves of the `unitprod` sandwich, which change how the value is
  bracketed and not what any bit holds;
- the `ctrl` inside `cx`, which is `mat ; (id + m) ; mat!` and becomes the
  control structure of the `cx` line rather than an instruction of its own.

That is §9.4's claim about plumbing, visible: seven of the ten primitives emit
nothing, so the instruction count tracks the *quantum* content of a term and
not its size.

### Reading it against the language

The wire view drops the QASM boilerplate and says which qubits each gate lands
on:

```
$ 42q emit gates bell --gates
bell : 2 qubit(s), 12 gate(s)
  gphase(0.785398) 
  x 0
```

The output is deliberately unoptimised: the four `p(π/4)` instructions above are
two quarter turns written the long way, and any transpiler folds them. What the
emitter guarantees is not brevity but agreement. `tests/test_emit.py` takes every
definition in every library that is a circuit at all — a parameterised one like
`ctrl` is not, until it is applied — emits it, reads the result back with a
simulator in `tools/qasm_sim.py` that shares no code with the evaluator, and
checks that matrix against the one Q42 computes from the term. For `bell` that is the 4×4 matrix sending `|00>` to
`(|00> + |11>)/√2`.

A polymorphic definition needs its width supplied before it can be a circuit at
all, since `swap : a x b <-> b x a` is not a two-qubit gate until you say that
`a` and `b` are qubits:

```
$ 42q emit gates swap -q 2
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;

swap q[1], q[0];
```
