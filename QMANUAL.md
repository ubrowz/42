# Q42 — User Manual

For a reader with a computer science background who has read
[the 42 manual](MANUAL.md): its Part I, which writes definitions as clauses
(Q42's clauses follow stricter rules, §7.3), and its Part II, the point-free
core that 42 and Q42 share. No prior knowledge of quantum mechanics is assumed;
the physics is developed here from scratch, but only as far as Q42 actually
needs it, and the parts Q42 does *not* model are named as such.

**What Q42 is.** 42 computes with *sets*: a program relates
inputs to outputs, and running it backwards gives the set of everything an
answer could have come from. Q42 is the same language computing with *complex
numbers*: each input–output pairing carries a number, those numbers can cancel,
and that makes it a language for quantum computers. §1 says why such a language
has to be reversible, §2 gives the physics, and §3 and §4 show how little of 42
had to change.

---

## Contents

1. [Why reversibility is forced](#1-why-reversibility-is-forced)
2. [The physics you need](#2-the-physics-you-need)
3. [One change, and everything follows](#3-one-change-and-everything-follows)
4. [Why 42 already fitted](#4-why-42-already-fitted)
5. [What Q42 drops](#5-what-q42-drops)
6. [What Q42 adds](#6-what-q42-adds)
7. [Writing programs](#7-writing-programs)
8. [Worked examples](#8-worked-examples)
9. [What Q42 is, and is not, for](#9-what-q42-is-and-is-not-for)
10. [Reference](#10-reference)

[Appendix: a program and its circuit](#appendix-a-program-and-its-circuit)

---

## 1. Why reversibility is forced

Before the physics, the engineering reason a computer scientist should care.

### Erasing a bit costs energy

**Landauer's principle** (1961): erasing one bit of information in a computer at
temperature `T` must turn at least `kT ln 2` joules of energy into heat. `T` is
the absolute temperature, in kelvin, and `k` is Boltzmann's constant, a fixed
number from physics that converts temperature into energy. At room temperature
the product is about `2.9 × 10⁻²¹` joules, negligible per bit today, and a floor
that no cleverness removes.

The point is *why* there is a floor. Information that is destroyed does not
vanish: it is pushed out into the computer's surroundings as disorder, which
physicists call entropy, and producing entropy costs heat. A computation that
never destroys information has no such floor. Bennett showed in 1973 that any
computation can be rearranged into one that destroys nothing, by keeping a
record of whatever an ordinary program would have thrown away: the same trick
as `mul` keeping its multiplier in the 42 manual's §9.3. That is the origin of
reversible computing as a field, and of 42.

### Quantum mechanics has no choice at all

A quantum computer stores information in **qubits**, the quantum counterpart of
bits, which §2.1 introduces. Like a classical computer it works by applying a
sequence of elementary operations to them, and these are called **gates**, as
in a classical logic circuit; a drawing of the sequence is a **circuit**, in
which each qubit is a horizontal line, a **wire**, and each gate a box on the
wires it acts on.

For a quantum computer, reversibility stops being an efficiency argument and
becomes a constraint. Physics says that an isolated quantum system changes in a
way described by a particular kind of matrix, a **unitary** one (§2.3 defines
it), and every unitary matrix has an inverse. So every quantum gate can be
undone. There is no such thing as an irreversible quantum gate, in the way that
there is no such thing as a triangle with four sides. It is not a design
decision anyone made.

So the familiar irreversible operations are simply unavailable:

```
c = a AND b
```

destroys information, since knowing `c = 0` tells you almost nothing about `a`
and `b`, so there is no two-input AND gate. What exists instead is the **Toffoli**
gate, which keeps its two inputs and writes the answer into a third wire, by
exclusive-or (`XOR`, addition mod 2):

```
(a, b, c)  |->  (a, b, c XOR (a AND b))
```

Set `c = 0` and the third component becomes `a AND b`, with `a` and `b` still
there. Nothing is lost, so the gate can be undone: in fact it undoes itself,
since applying it twice XORs the same value in twice. This is the padding trick
of the 42 manual's §9.3 again; the same pressure produces the same answer in
both places.

### Uncomputation

Padding has a cost: the kept-around values pile up. If you compute an
intermediate `x`, use it, and no longer want it, you cannot drop it, since that
would be erasing information. You must **uncompute** it by running its producer
backwards.

The pattern is `P ; Q ; P!`: do the work, use it, undo the work. In Q42 that
is an ordinary term, because `!` is part of the language, and because every Q42
term is invertible `P!` really is `P`'s inverse. Some quantum languages decide
for you where the undo goes: Silq (Bichsel et al., 2020) infers it, so that the
programmer never has to. Q42 does not infer: you decide, and then writing it
costs three characters. What the language gives you is that what you wrote is
exact.

---

## 2. The physics you need

- [2.1 A state is a vector of amplitudes](#21-a-state-is-a-vector-of-amplitudes)
- [2.2 Amplitudes are not probabilities](#22-amplitudes-are-not-probabilities)
- [2.3 A gate is a unitary matrix](#23-a-gate-is-a-unitary-matrix)
- [2.4 Superposition](#24-superposition)
- [2.5 Interference — the one that matters](#25-interference--the-one-that-matters)
- [2.6 Entanglement](#26-entanglement)
- [2.7 What Q42 does not model](#27-what-q42-does-not-model)

Enough to read Q42 programs, and no more. Everything here is finite-dimensional
linear algebra over the complex numbers; nothing requires an understanding of
physics.

**Complex numbers, in one paragraph.** A complex number is `c = a + bi`, with
`a` and `b` real and `i² = −1`. Its **magnitude** `|c|` is its distance from 0
in the plane, `√(a² + b²)`, so `|c|² = a² + b²`. Its **conjugate** is
`a − bi`, written `conj(c)` or `c*`; and `c × conj(c) = |c|²`. A complex number
of magnitude 1 lies on the unit circle and can be written `e^{iθ} = cos θ +
i sin θ`, the point at angle `θ` (in radians) from the positive real axis.
Multiplying by such a number rotates by `θ` and changes no magnitude; it is
called a **phase**. Four of them recur below: `1` (angle 0), `i` (a quarter
turn, `π/2`), `−1` (a half turn, `π`), and `e^{iπ/4} = (1 + i)/√2`, an eighth
of a turn.

### 2.1 A state is a vector of amplitudes

A classical bit is `0` or `1`. A **qubit** is a pair of complex numbers, one
attached to each of those two possibilities.

Physicists write this with *kets*. `|x>` means "the basis state labelled `x`",
so `|0>` and `|1>` are a qubit's two basis states, the quantum counterparts of
the bit values 0 and 1. A qubit's state in general is written:

```
|psi>  =  c0 |0>  +  c1 |1>          c0, c1 in C
```

Read it as: *the state called psi consists of the basis state 0 with weight
`c0`, plus the basis state 1 with weight `c1`, where `c0` and `c1` are complex
numbers* (`C` is the complex numbers). `psi`, the Greek letter ψ, is only the
customary name for "some state", the way `x` is for "some number"; nothing
depends on it. The weights `c0` and `c1` are the **amplitudes**, and §2.2 says
what they mean. When `c1` is 0 the state is just `|0>`, and when `c0` is 0 it is
just `|1>`. When both are nonzero, the qubit is in both basis states at once,
in proportions the amplitudes give: a *superposition*, which §2.4 takes up.

As a computer scientist would store it, the state is the array `[c0, c1]`, a
vector of length two. That is all a ket is: `|0>` is `[1, 0]`, `|1>` is
`[0, 1]`, and `c0 |0> + c1 |1>` is `[c0, c1]`.

For `n` qubits there are `2ⁿ` basis states, `|000…>` through `|111…>`, one for
each `n`-bit string, and a state is a vector of `2ⁿ` amplitudes, one per string.
That exponential is the whole reason simulating quantum computers is expensive,
and the whole reason building them might be worth it.

### 2.2 Amplitudes are not probabilities

You cannot read the amplitudes off a real qubit. What you can do is **measure**
it: a measurement returns a classical bit string, one of the basis states, at
random, and afterwards the qubits are left in exactly the basis state that was
returned, so measuring again gives the same answer. The probability of each
outcome comes from its amplitude: you see outcome `x` with probability `|cₓ|²`,
the squared magnitude. This is the **Born rule**, and it is where the physics
enters; the rest is linear algebra.

Two consequences a computer scientist should internalise:

- Probabilities must sum to `1`, so `Σ |cᵢ|² = 1`: the squared magnitudes of a
  state's amplitudes add up to one. In other words a state is a vector of length
  1, a **unit vector**.
- Amplitudes can be **negative**, or complex. Probabilities cannot. This is the
  entire difference between a quantum computer and a randomised classical one,
  and everything interesting comes from it.

### 2.3 A gate is a unitary matrix

A gate on `n` qubits is a `2ⁿ × 2ⁿ` matrix of complex numbers, and applying it
to a state is ordinary matrix–vector multiplication. For one qubit, name the
gate's four entries by row and column, `u00` to `u11`, and take the state
`[c0, c1]` of §2.1:

```
  [ u00  u01 ]     [ c0 ]     [ u00 × c0  +  u01 × c1 ]     new amplitude of |0>
  [ u10  u11 ]  x  [ c1 ]  =  [ u10 × c0  +  u11 × c1 ]     new amplitude of |1>
```

Each new amplitude is one row of the matrix, multiplied entry by entry with the
state and summed. Applied to `|0>`, which is `[1, 0]`, the result is
`[u00, u10]`, the matrix's first column; applied to `|1>` it is the second column.
So **column `k` of the matrix is what the basis state `|k>` turns into**, and a
gate is fully described by what it does to each basis state.

An example with numbers, using a matrix chosen because its arithmetic comes out
round, applied to the state `0.6|0> + 0.8|1>`:

```
  [ 0.6   0.8 ]     [ 0.6 ]     [ 0.6 × 0.6  +  0.8 × 0.8 ]     [ 0.36 + 0.64 ]     [ 1 ]
  [ 0.8  -0.6 ]  x  [ 0.8 ]  =  [ 0.8 × 0.6  -  0.6 × 0.8 ]  =  [ 0.48 - 0.48 ]  =  [ 0 ]
```

The result is `|0>` exactly: in the second row the two products cancel, a first
glimpse of §2.5. Physicists write the result of applying gate `U` to state
`|ψ>` as `U|ψ>`.

The simplest example is **NOT**, written `X` and in Q42 called `x`. It swaps the
two amplitudes, so `|0>` becomes `|1>` and `|1>` becomes `|0>`:

```
$ 42q matrix gates x
x : qubit <-> qubit
     |0>  [ 0  1 ]
     |1>  [ 1  0 ]
```

Read the column for `|0>` (the first): its 1 is in the row for `|1>`.
(`42q matrix gates x` prints the matrix of the definition `x` in the Q42 library
file `q42/gates.42`; §7.4 lists the commands.)

Not every matrix is allowed. A gate must satisfy

```
U† U  =  U U†  =  I
```

where `I` is the identity matrix, 1 on the diagonal and 0 elsewhere, and `U†`
("U dagger") is the **adjoint** of `U`: swap rows and columns (transpose) and
replace every entry by its conjugate. Such a matrix is called **unitary**.

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
and every way of combining them preserves unitarity (§6). You can audit the
claim anyway. For a definition `t`, `42q unitary` builds the matrix of `t ; t!`,
`t` followed by its own adjoint, which is `U† U` from the equation above, and
checks that it is the identity: that every basis state comes back exactly as it
went in. Run on a whole file, it does this for every definition in it:

```
$ 42q unitary gates
  [ok ] h ; h! = id on 2 dimension(s)
  [ok ] ccx ; ccx! = id on 8 dimension(s)
  ...
-- 24/26 unitary, 2 with no single matrix
```

`gates.42` is the library of standard gates that §6 introduces; what each one
does does not matter here, only that the check passes. Each `[ok ]` line names
one definition and the size of the space it was checked on: `2ⁿ` dimensions for
a gate on `n` qubits, so 2 for a gate on one qubit and 8 for one on three. The
last line counts them. The two "with no single matrix" are definitions that take
another gate as a parameter, such as "the controlled version of a gate `m`"
(§6.4). Until `m` is given there is no single matrix to check, so they are
listed but not counted as failures.

### 2.4 Superposition

A state with more than one nonzero amplitude is in **superposition**. The gate
that makes one is the **Hadamard** gate, written `H` and in Q42 called `h`. Its
matrix is

```
H  =  1/√2 × [ 1   1 ]          H|0>  =  ( |0> + |1> ) / √2
             [ 1  -1 ]          H|1>  =  ( |0> - |1> ) / √2
```

so it sends `|0>` to an equal superposition of both basis states, and `|1>` to
the same with a minus sign on the second. Applied to `|0>`:

```
$ 42q gates h "|0>"
h |0>
  = 0.707107|0>  +  0.707107|1>
```

(`42q gates h "|0>"` runs `h` from `q42/gates.42` on the state `|0>` and prints
the resulting state.) `0.707107` is `1/√2`, so both outcomes have probability
`(1/√2)² = 1/2`: measure this qubit and you get 0 or 1, each half the time.

It is tempting, and wrong, to read this as "the qubit is secretly 0 or 1 and we
don't know which". The next section is why.

### 2.5 Interference — the one that matters

Apply `h` a second time. Classically, randomising a coin twice leaves it random.
Here (`hh` is defined in `gates.42` as `h ; h`):

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

Each line follows one route: the amplitude the first `H` gave a basis state,
times the amplitude the second `H` sends it on with (the `-0.7071` is the
`H|1>` minus sign). Two routes lead to `|1>` and they arrive with **opposite
signs**, so they cancel. This is **destructive interference**, and it has no
classical counterpart: probabilities are non-negative and adding more routes to
an outcome can only make it likelier. Amplitudes are not so constrained.

Every quantum algorithm that beats its classical rival does it this way, by
arranging for the wrong answers' amplitudes to cancel and the right answer's to
reinforce. The two famous ones are both this, elaborately: Grover's algorithm,
which searches `N` unsorted items in about `√N` steps instead of `N`, and Shor's
algorithm, which factors integers in polynomial time, where no classical
algorithm is known to.

This is what 42 cannot express. Over the booleans the two routes to `|1>` would
be `1 ∨ 1 = 1`, still possible, and there is no `−1` to cancel with.
42 tells you which outcomes are *reachable*; it cannot tell you that two ways of
reaching one annihilate.

### 2.6 Entanglement

Two qubits have four basis states, `|00>`, `|01>`, `|10>` and `|11>`, so a state
of the pair is four amplitudes, `c00`, `c01`, `c10` and `c11`. Sometimes those
four come from two separate qubits, "this one is in state `ψ` and that one in
state `φ`" (`φ`, phi, is just a second name for a state). Sometimes they do not, and then the qubits are **entangled**: the
pair has a state, but neither qubit has one of its own.

The standard example is `bell`, two gates in a row: the Hadamard of §2.4 on the
first qubit, then a **controlled-NOT**, which flips the second qubit when the
first is `1` and leaves it alone when the first is `0`. Started on `|00>`:

```
$ 42q gates bell "|00>"
bell |00>
  = 0.707107|00>  +  0.707107|11>
```

**The arithmetic, step by step.** Write a two-qubit state as a column of its
four amplitudes, in the order `|00>, |01>, |10>, |11>`, and a gate as the 4×4
matrix that acts on it: the column for each input holds the amplitudes that
input produces. With `r = 1/√2 ≈ 0.7071`, the starting state `|00>` is the
column `(1, 0, 0, 0)`.

The Hadamard on the first qubit sends `|0x>` to `r|0x> + r|1x>` and `|1x>` to
`r|0x> − r|1x>`, whatever `x` is. Multiplying:

```
   H on the first qubit         |00>         after step 1

  [ r   0   r   0 ]            [ 1 ]          [ r ]    |00>
  [ 0   r   0   r ]     x      [ 0 ]    =     [ 0 ]    |01>
  [ r   0  -r   0 ]            [ 0 ]          [ r ]    |10>
  [ 0   r   0  -r ]            [ 0 ]          [ 0 ]    |11>
```

So after step 1 the state is `r|00> + r|10>`: the first qubit is in
superposition and the second is still plainly `0`. That much is a product, as
§2.4's `h` would lead you to expect.

The controlled-NOT exchanges `|10>` and `|11>` and leaves `|00>` and `|01>` where
they are. As a matrix that is a permutation:

```
      CNOT                   after step 1      after step 2

  [ 1   0   0   0 ]            [ r ]            [ r ]    |00>
  [ 0   1   0   0 ]     x      [ 0 ]    =       [ 0 ]    |01>
  [ 0   0   0   1 ]            [ r ]            [ 0 ]    |10>
  [ 0   0   1   0 ]            [ 0 ]            [ r ]    |11>
```

The amplitude that was on `|10>` has moved to `|11>`, and the result is
`r|00> + r|11>`, which is what Q42 printed.

**Why that cannot be two separate qubits.** Suppose it were: the first qubit in
`a0|0> + a1|1>`, the second in `b0|0> + b1|1>`. Then each two-qubit amplitude is a
product of one from each, because the first qubit has to be in its part and the
second in its:

```
c00 = a0 b0      c01 = a0 b1      c10 = a1 b0      c11 = a1 b1
```

The Bell state needs `c01 = a0 b1 = 0`, so `a0 = 0` or `b1 = 0`. But `a0 = 0` would
make `c00 = 0`, and `b1 = 0` would make `c11 = 0`, and both of those are `r`. No
choice of the four numbers works, so the state is not a product.

The same argument gives a test that works on any two-qubit state. For a product,
`c00 c11 = a0 b0 a1 b1 = c01 c10`, so

```
c00 c11  -  c01 c10  =  0
```

always, and conversely when this is zero the state does factor. (It is the
determinant of the amplitudes arranged as a 2×2 grid, rows for the first qubit
and columns for the second.) For the Bell state:

```
c00 c11 - c01 c10  =  0.7071 x 0.7071 - 0 x 0  =  0.5
```

which is not zero, so it does not factor.

**What it means.** Measure the pair and you get `00` or `11`, each half the
time, and never `01` or `10` (§7.6 shows `42q sample` doing this). Each qubit on
its own is a fair coin; together they always agree. So far that is no stranger
than two sealed envelopes holding copies of one randomly chosen card. The
strangeness appears when, before measuring, each side applies its own one-qubit
gate that mixes `|0>` and `|1>` by some angle (a *rotation* of the qubit, of
which the Hadamard is one). How often the two answers then agree depends on the
angle between the two rotations, and for some pairs of angles the agreement is
stronger than any envelopes, prepared in any way, could produce. That is Bell's
theorem, which the state is named after. It does not let either side send a message to the other, but it is a
resource quantum algorithms use, and §8.5's teleportation is built on exactly
this state.

Entanglement is why Q42 needs one piece of machinery 42 did not (§7.5): a state
of a compound system is not in general a pair of states.

### 2.7 What Q42 does not model

Stated plainly, because a manual that quietly omits these would be misleading.

- **Measurement, except at the end.** Q42 computes the unitary. You may measure
  the *result* (§7.6), which is the Born rule applied to a finished state, but
  nothing collapses mid-program, so there is no measuring, branching on the
  outcome, and carrying on. §9.2 is precise about the difference.
- **Normalisation.** Q42 does not enforce `Σ|cᵢ|² = 1`. It does not need to: a
  ket you type in is a unit vector, and unitary maps preserve length, so a
  well-formed program cannot leave that set.
- **Noise, decoherence, error correction.** Real qubits are disturbed by their
  surroundings and gradually lose their state, which is called *decoherence*;
  real gates are slightly inaccurate, which is *noise*; and *error correction*
  spreads each logical qubit over many physical ones so that such errors can be
  detected and repaired. None of this is modelled: Q42's qubits and gates are
  perfect.
- **Global phase.** Multiplying an *entire* state by a phase, a complex number
  `e^{iθ}` of magnitude 1, changes no squared magnitude and so no measurement
  outcome: the two states are physically indistinguishable. Q42 tracks such a
  factor faithfully anyway, which is why some gate identities hold only "up to
  phase", that is, only up to such a factor (§6.3).

---

## 3. One change, and everything follows

- [3.1 A program is a grid](#31-a-program-is-a-grid)
- [3.2 Running backwards is reading the other way](#32-running-backwards-is-reading-the-other-way)
- [3.3 Composing is combining grids](#33-composing-is-combining-grids)
- [3.4 Q42 puts numbers in the cells](#34-q42-puts-numbers-in-the-cells)
- [3.5 The whole difference, in one table](#35-the-whole-difference-in-one-table)

With the physics in hand, here is the whole difference between 42 and Q42, made
concrete. The way to see it is to draw a 42 program as a grid and then change
what sits in the cells: marks in 42, the amplitudes of §2 in Q42.

### 3.1 A program is a grid

Take a shape with finitely many values, say the two-value shape `1 + 1`, whose
values are `L ()` and `R ()` (the 42 manual, §3.1). A program from that shape to
itself either can or cannot turn each input into each output, so you can write
the whole program down as a grid: one row per input, one column per output, and a
mark where the program can get from one to the other.

Here is `not`, which is the primitive `swapsum`: it moves a value from one label
to the other (the 42 manual's §14 lists the primitives used in this section):

```
        to  L ()  R ()
  from
  L ()        .     *
  R ()        *     .
```

Read a **row** as "what this input can produce". `L ()` produces only `R ()`,
which is what negation does.

A program need not have exactly one mark per row. `inl!`, the primitive `inl`
run backwards, removes an `L` label and rejects anything else, so its row for
`R ()` is empty. That is 42's `{}`,
drawn:

```
        to    ()
  from
  L ()        *
  R ()        .
```

And `join!` has two marks in one row. `join` removes a label and forgets which
one it was; run backwards, it cannot know which to put back, so it offers both. That is a set of two answers, drawn:

```
        to  L ()  R ()
  from
    ()        *     *
```

Nothing new has been said yet. This is the same "a program returns a set" from
the 42 manual's §6, written as a picture instead of as a list.

### 3.2 Running backwards is reading the other way

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

### 3.3 Composing is combining grids

`f ; g` means "do `f`, then `g`". So `f ; g` can get from `x` to `z` exactly when
there is some middle value `y` with `f` reaching `y` and `g` reaching `z` from
it. In grid terms: to fill in cell `(x, z)`, walk along row `x` of `f` and down
column `z` of `g`, and look for a position where **both** have a mark.

That rule, *for each middle value take AND, and across all middle values take
OR*, is what mathematicians call **matrix multiplication**, with `and` in place
of `×` and `or` in place of `+`. So 42's grids are matrices whose entries are
`0` and `1`, and `;` is matrix multiplication over those. That is all that "42
is matrices over the booleans" means.

### 3.4 Q42 puts numbers in the cells

Q42 changes one thing: a cell holds a **complex number** instead of a mark: the
amplitude of §2.2.

Here is `h`, the Hadamard gate, whose grid Q42 will print for you:

```
$ 42q matrix gates h
h : qubit <-> qubit
     |0>  [  0.707107   0.707107 ]
     |1>  [  0.707107  -0.707107 ]
```

Same 2×2 grid as `not`, but with numbers, and one of them is negative. That is
the point.

One wrinkle before going on. The grids in §3.1 put inputs in rows, which reads
naturally as "from, to". `42q matrix` prints them the other way up: its **rows are
outputs and its columns are inputs**. That is the universal convention in physics,
because a gate is written as acting on a column of amplitudes, `U|ψ>`. The two
pictures hold the same information, one being the other transposed, and the
difference does not show on `h`, whose grid happens to be symmetric. It does
show on `x ; s`: `x` is NOT, and `s` is a gate §6.2 defines that leaves `|0>`
alone and multiplies `|1>` by `i`. So `x ; s` takes `|0>` to `|1>` and then to
`i|1>`, and its matrix has its lone `i` in row `|1>`, column `|0>`.

Composition works exactly as in §3.3, with the OR and AND becoming ordinary `+`
and `×`, since that is what they were standing in for. So compose `h` with itself
and fill in the `|1>` cell of the first row: walk along `h`'s row for `|0>` and
down `h`'s column for `|1>`, multiplying and adding.

```
    via |0> :  +0.7071 x +0.7071  =  +0.5000
    via |1> :  +0.7071 x -0.7071  =  -0.5000
    total   :                        0.0000
```

The two routes **cancel**: this is §2.5's interference, now seen as arithmetic on
grids. With marks it could not have happened: `* or *` is `*`, and more ways of
reaching an answer only ever makes it more reachable. With numbers, one route can
undo another.

### 3.5 The whole difference, in one table

With §§3.1–3.4 in hand, the summary is readable:

| | 42 | Q42 |
|---|---|---|
| a cell holds | a mark: reachable or not | a complex number |
| a row says | the **set** of answers | the answers, each with an amplitude |
| `;` combines grids by | AND down the middle, then OR | `×` down the middle, then `+` |
| `!` is | the grid flipped (§3.2) | flipped, and each entry conjugated |
| `+` and `*` | build a bigger grid out of two | the same, unchanged |
| more routes to an answer | only ever helps | can cancel out |

The last row is the only one that is a real difference, and every other
difference follows from it. Numbers have negatives; marks do not.

Two names for the record, since the literature uses them. A system with an
addition and a multiplication but no need for subtraction is a **semiring**;
`{0,1}` with `or`/`and` is one, and ℂ is another, so "Q42 is 42 over a different
semiring" is a one-line way to say all of the above. And flipping-and-conjugating
a matrix is its **adjoint** `M†`, from §2.3. So `!` denotes the
converse of a relation in 42 and the adjoint of a matrix in Q42, which §4.1
shows is the same operation twice.

## 4. Why 42 already fitted

- [4.1 `inv` and `†` are the same operation](#41-inv-and--are-the-same-operation)
- [4.2 42's primitives were the right ones already](#42-42s-primitives-were-the-right-ones-already)

Q42 differs from 42 in very little, and the reason is structural rather than
accidental.

### 4.1 `inv` and `†` are the same operation

Mathematicians call a collection of things that can be composed, with an
identity for composition, a **category**: programs with `;` and `id` are one,
and so are matrices with multiplication and the identity matrix. Both settings
here are **dagger categories**, categories with an extra operation `†` that
turns each thing around and satisfies

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

`inv(P)` is 42's `P!`. `<x| P |y>` is the matrix entry of `P` in row `x`,
column `y`: the amplitude with which `P` takes `|y>` to `|x>`. So the second line
says that the amplitude for `P` to go from `y` to `x` is the conjugate of the
amplitude for `P!` to go back. It is the same law as the first, with membership
replaced by amplitude equality. You can check it; `42q law` runs a gate on a
state and compares each such pair of entries:

```
$ 42q law gates h "|0>"
h |0> has 2 component(s)
  [ok ] |0>: <y|P|x> = 0.707107, <x|P!|y> = 0.707107
  [ok ] |1>: <y|P|x> = 0.707107, <x|P!|y> = 0.707107
law holds
```

### 4.2 42's primitives were the right ones already

42's types obey the laws of arithmetic: `a + b` has as many values as
`b + a`, `1 × a` as many as `a`, `(a + b) × c` as many as `a×c + b×c`, and so
on. 42's primitives are exactly the conversions between the two sides of these
laws: `swapsum` converts `a + b` into `b + a`, `unitprod` converts `1 × a` into
`a`, `dist` converts `(a + b) × c` into `a×c + b×c`. Each is a bijection, an
**isomorphism** in the mathematician's word. Types with these conversions form
what is called a **rig groupoid** ("rig" because the laws are those of a ring
without subtraction, "groupoid" because every conversion can be undone). The
reversible programming language **Π** of James & Sabry (2012) is built from
exactly these conversions; 42 arrived at the same set independently.

This matters because of a result of Carette, Heunen, Kaarsgaard & Sabry
(POPL 2024): a rig groupoid extended with **two maps and three equations** is
computationally universal for quantum computing, that is, it can approximate
any quantum computation as closely as you like. Those two maps are §6. Q42 is
that construction, given 42's syntax: the point-free core, and clauses that
compile to it (§7.3).

So the whole of the difference is: the semiring changes, the primitives that are
not unitary go, and two unitary ones arrive. The evaluator, the type system and
`dagger` are 42's, unchanged.

---

## 5. What Q42 drops

- [5.1 `|` and `^` need `1 + 1 = 1`](#51--and--need-1--1--1)
- [5.2 `copy` is not the no-cloning theorem](#52-copy-is-not-the-no-cloning-theorem)
- [5.3 Where the restriction actually bites](#53-where-the-restriction-actually-bites)
- [5.4 What it means for clauses](#54-what-it-means-for-clauses)

Five primitives and two combining forms. Each is dropped for a reason you can
check, not by taste, and §5.4 says what that changes for definitions written as
clauses.

### 5.1 `|` and `^` need `1 + 1 = 1`

This one is exact. Over the booleans `x ∨ x = x`, so adding is **idempotent**.
Over ℂ, `1 + 1 = 2`.

`f | g` means "either", which as a matrix is `⟦f⟧ + ⟦g⟧`, where `⟦f⟧` is the
matrix of `f`. Over the booleans `f | f` is `f`; over ℂ it would be `2f`, which
is not the same relation and not even unitary. And `f^` collects everything
reachable by repeating `f` any number of times, stopping when nothing new
appears (the 42 manual's §13); over ℂ, repeating adds amplitudes that never
settle.

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

Write `|ψ> ⊗ |φ>` for the two-qubit state in which the first qubit is in state
`ψ` and the second in state `φ`: the product state of §2.6, whose amplitudes are
products of the two. The **no-cloning theorem** says there is no unitary `U`
with `U(|ψ> ⊗ |0>) = |ψ> ⊗ |ψ>` for *every* `ψ`: no gate copies an unknown
state onto a blank qubit. 42's `copy` does not attempt that. It maps each
*basis* state `|x>` to `|x,x>`, and like every gate it acts on a superposition
by acting on each basis state and adding the results with the same amplitudes.
So it sends `|0>+|1>` to `|00>+|11>`, which is the Bell state of §2.6, not
`(|0>+|1>)⊗(|0>+|1>)`. That is a perfectly legitimate quantum operation. In the
categorical literature such a copying map is called a **classical structure**,
and Coecke and Pavlović showed that each one amounts to choosing a
*measurement basis*: the set of states a measurement tells apart, of which `|0>`
and `|1>` is the standard one.

So why is it out? Because it is not **square**. It maps a space of dimension `n`
into one of dimension `n²`, one qubit's 2 amplitudes into two qubits' 4, and a
unitary must map a space to itself. A
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

`inl`, `inr` and `zero` go for the same dimensional reason. Writing `ℂⁿ` for
the space of states of a type with `n` values, `inl : a ↔ a + b` embeds `ℂⁿ` in
the bigger `ℂⁿ⁺ᵐ`, and `zero` is the zero matrix, which inverts nothing.
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

### 5.4 What it means for clauses

A 42 clause definition compiles to the primitives above, so the ones Q42 drops
take some of the clause rules with them. Each change is one of §5.1–5.3 again:

- **A name is used exactly once on each side.** In 42 a name used twice in a
  term is a `copy`, and a name used twice in a pattern is an equality test, its
  `copy!`. Neither is unitary (§5.2), so in Q42 both are errors.
- **The patterns cover every input exactly once, and the terms every output.**
  In 42 a definition is the union of its clauses, overlap merely warns, and a
  missing case means no answer. In Q42 a definition is the *sum* of its
  clauses, which is §5.1's `1 + 1 = 2`: overlap would add two matrices, and a
  gap would leave a partial map. Both are errors.
- **A `let` pattern cannot fail.** A call's result may be a superposition, and a
  pattern that kept part of it and dropped the rest would not be unitary.

§7.3 shows what is left, which is most of what one wants.

---

## 6. What Q42 adds

- [6.1 The generators](#61-the-generators)
- [6.2 Phases are the sum functor](#62-phases-are-the-sum-functor)
- [6.3 Hadamard, and "up to phase"](#63-hadamard-and-up-to-phase)
- [6.4 Control is `dist`, which you have already met](#64-control-is-dist-which-you-have-already-met)
- [6.5 Which equations hold, and how Q42 decides](#65-which-equations-hold-and-how-q42-decides)

Two primitives. Everything else in `q42/gates.42` is built from them and from
42's existing plumbing.

### 6.1 The generators

```
omega : 1 <-> 1            a scalar; an 8th root of 1
v     : 1+1 <-> 1+1        a square root of `swapsum`
```

`omega` acts on the unit type `1`, which has a single value `()` and so a
one-dimensional space: its "matrix" is a single number. That number is
`e^{iπ/4} = (1 + i)/√2`, the eighth of a turn from the complex-number primer of
§2. It is called an **eighth root of 1** because multiplying it by itself eight
times gives 1. On its own `omega` does nothing visible; combined with another
gate (§6.2) it multiplies part of a state by that phase.

`v` acts on one qubit, and doing it twice is NOT: `v ; v = swapsum`, which is
the gate `x` of §2.3. So it is "half a NOT", which has no classical meaning at
all; no operation on bits, done twice, flips a bit. Its matrix is

```
V  =  1/2 × [ -1+i   -1-i ]
            [ -1-i   -1+i ]
```

and multiplying it by itself does give `[[0, 1], [1, 0]]`. (You never write
these numbers in a Q42 program; you write `omega` and `v`, and Q42 knows their
values.)

They satisfy three equations. Here `omega^8` means `omega` composed with itself
eight times, `S` is the gate `id + (omega ; omega)` that §6.2 explains (it
multiplies `|1>` by `i`), and `omega^2 . t` means the gate `t` with its whole
matrix multiplied by the number `omega²`:

```
(E1)  omega^8   =  id
(E2)  v ; v     =  swapsum
(E3)  v ; S ; v =  omega^2 . (S ; v ; S)
```

(E1) and (E2) only say what the two generators are: an eighth root of 1 and a
square root of NOT. **(E3) is the one that does the work**: it is the one
equation that ties `v` and `omega` together. Without it, `omega = 1` would
satisfy everything, and since a phase of 1 changes nothing, the language would
collapse to classical reversible computing. With it, the Hadamard gate becomes
expressible (§6.3), and that is what makes the language quantum.

And eighth is not a choice among many. Read (E3) as an equation in `omega`, with
`v` the matrix above, and it has exactly two solutions: `e^{iπ/4}` and
`−e^{iπ/4}`. Both are eighth roots of 1 and of no smaller root: the first power
of either that equals 1 is the eighth (its *order* is 8). No solution has order
16, and no solution fails to be a root of 1 at all. (The two other eighth roots
of order 8 satisfy (E3) only for the other square root of NOT, `V`'s conjugate.)
So a finer angle than an eighth of a turn cannot be had by relaxing an equation;
it needs a further generator, which is the ladder §9.4 ends on.

### 6.2 Phases are the sum functor

A **phase gate** multiplies `|1>` by a phase and leaves `|0>` alone. In 42's
notation that is `id + <something>`, the sum functor acting on the right branch
only: on `L ()`, which is `|0>`, do `id`; on `R ()`, which is `|1>`, do the
something. Here the something is a power of `omega`:

```
def t = id + omega                              -- diag(1, e^{i pi/4})
def s = id + (omega ; omega)                    -- diag(1, i)
def z = id + (omega ; omega ; omega ; omega)    -- diag(1, -1)
```

`diag(a, b)` is the matrix with `a` and `b` on the diagonal and 0 elsewhere:
`|0>` is multiplied by `a` and `|1>` by `b`. So `t` turns `|1>` an eighth of a
turn, `s` a quarter (`omega` twice is `i`), and `z` half (`omega` four times is
`−1`); `z` is the gate usually written `Z`.

```
$ 42q matrix gates s
s : qubit <-> qubit
     |0>  [  1   0 ]
     |1>  [  0  1i ]
```

Nothing was added to the language to express this. `+` already meant "switch on
the label", and a phase gate is a switch that does nothing on one branch.

**The three are one group.** Look at what `t`, `s` and `z` have in common. Each
is `id +` some power of `omega`, and by (E1) there are only eight such powers.
Under multiplication they form a *group*: multiplying two of them gives another,
and each has an inverse among them. It is a *cyclic* group of order eight,
meaning all eight are powers of a single one, `omega`. A *subgroup* is a subset
that is itself closed under multiplication, and the three gates above generate
its three nontrivial subgroups:

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
that single choice carries the physical content of the language.

Two names from the field make the point sharper. The **Clifford** gates are the
ones built from `h` (§6.3), `s` and the controlled-NOT of §2.6. Their phases are
exactly the order-four subgroup: `s`, `z`, and nothing finer. By the
**Gottesman–Knill theorem**, any circuit made of Clifford gates can be simulated
efficiently on an ordinary computer, entanglement and interference included
(§9.3). **Clifford+T** adds `t`, and with it the order-eight phases, and it can
not, as far as anyone knows. **The step from `s` to `t` is the step from a theory
a laptop can simulate to one it cannot**, and in group terms it is one rung of
that chain.

The idea has a name in the research literature. Coecke & Duncan attach to each
*observable*, each quantity one can measure, the group of phases available to
it, its *phase group*, and show that this one invariant is sharp enough to tell
physical theories apart. Their example: quantum mechanics restricted to Clifford
operations, and a classical model built by Spekkens to imitate it, agree about
nearly everything, yet their phase groups differ, `Z₄` (the four phases
`1, i, −1, −i`) against `Z₂ × Z₂` (four elements, each its own inverse), and that
difference is exactly where they disagree about the three-qubit version of the
Bell state, `(|000> + |111>)/√2` (`ghz` in `gates.42`): the real theory shows
correlations, of the kind §2.6 described, that the imitation cannot. Q42's
phase group is `Z₈`. RELATED §11.4 sets the two calculi side by side generator
for generator.

### 6.3 Hadamard, and "up to phase"

The Hadamard gate of §2.4 is built from `x`, `s` and `v`:

```
def hcore = x ; s ; v ; s ; x
def h     = unitprod! ; (omega * hcore) ; unitprod
```

`hcore` is already the Hadamard, except that its whole matrix is the Hadamard's
multiplied by the phase `omega⁻¹`, an eighth of a turn backwards. `h` corrects
that: `unitprod!` pairs the qubit with a `()`, `omega * hcore` multiplies by
`omega` on the `()` side while running `hcore` on the qubit, and `unitprod` drops
the `()` again. (`x ; s ; v ; s ; x` is a palindrome, so for once it reads the
same in either direction.)

That extra factor is a **global phase** (§2.7): physically undetectable, since a
phase on the whole state changes no measurement, which is why many gate
identities in the literature hold only "up to phase", up to such a factor. Q42
tracks it exactly anyway, which is why `h` comes out as the textbook matrix on
the nose rather than nearly:

```
$ 42q matrix gates h
h : qubit <-> qubit
     |0>  [  0.707107   0.707107 ]
     |1>  [  0.707107  -0.707107 ]
```

### 6.4 Control is `dist`, which you have already met

A **controlled** gate applies its target gate only when the control qubit is
`|1>`. That is a conditional, and 42's core does conditionals with `dist` (the
42 manual, §13). So:

```
def mat    = dist ; (unitprod + unitprod)       -- (1+1) x A  <->  A + A
def ctrl m = mat ; (id + m) ; mat!
```

`mat` turns a pair (control qubit, rest) into a labelled value: the rest, under
the control's label. `ctrl m` then applies `m` on the `R` branch only, the one
where the control was `|1>`, and `mat!` puts the pair back together. Every
controlled gate is one line:

```
def cx    = ctrl x                              -- CNOT
def ccx   = ctrl cx                             -- Toffoli
def cswap = ctrl swap                           -- Fredkin
```

`cx` is the controlled-NOT of §2.6. `ccx` controls a controlled-NOT, so it flips
its third qubit when *both* of the others are `|1>`: the Toffoli gate of §1.
`swap` is `swapprod`, which exchanges two qubits, so `cswap`, the **Fredkin**
gate, exchanges its second and third qubits when the first is `|1>`.

Written as clauses (§7.3), a controlled gate is two lines, one for each value
of the control, and `cx` compiles to exactly `ctrl x` with `mat` written out:

```
def cx (L (), q)  <->  (L (), q)
def cx (R (), q)  <->  (R (), x q)
```

The inferred type says what control requires and nothing more:

```
ctrl : (a <-> a) -> (qubit x a <-> qubit x a)
```

the target must have the same type in and out (an *endo*-relation, in the
jargon), because both branches of `id + m` have to meet the `A + A` that `mat`
produces.

And its adjoint needs no definition. `ctrl! m` is `ctrl m!`, which in physics is
`(Ctrl U)† = Ctrl U†`: the adjoint of a controlled gate is the controlled
adjoint. That falls out of how `!` treats a parameter and is not arranged.

### 6.5 Which equations hold, and how Q42 decides

The three equations of §6.1 are rules for proving two programs equal, the way
`x + 0 = x` is a rule of algebra. Two properties matter, and they are the ones
a computer scientist asks of any proof system:

- **Sound**: whatever the rules prove equal really is equal. That holds: two
  terms (E1)–(E3) prove equal always denote the same matrix.
- **Complete**: whatever really is equal, the rules can prove equal. That holds
  only for some families of circuits, of which the best known are the Clifford
  gates of §6.2 and Clifford+T on at most two qubits. Beyond those, two Q42
  terms can denote the same matrix with nothing derivable from (E1)–(E3) saying
  so. `ccz`, the Z gate controlled by two qubits (`ctrl cz`, with `cz = ctrl z`),
  is an example of where that starts.

What the language offers in place of a complete proof system is evaluation, and
exact evaluation. Because the generators are fixed numbers, every amplitude a
Q42 program can produce is built from integers, `i` and `1/√2` by adding,
subtracting and multiplying: mathematicians write that set `Z[1/√2, i]`. Such a
number can be stored exactly, as a few integers, the way a fraction can be
stored as two. `q42/exact.py` evaluates in that set rather than in floating
point, so comparing two terms *decides* whether they are equal instead of
approximating: `h ; h` and `id` are the same matrix, not the same to twelve
places, and an amplitude that cancels is absent rather than small. That is what
`42q equal` does:

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

`s` and `t` differ exactly where §6.2 says: on `|1>`, a quarter turn against an
eighth.

RELATED §11 sets this against the ZX-calculus, a graphical language for quantum
circuits which has rules complete for all of Clifford+T, and makes the opposite
trade to get them.

---

## 7. Writing programs

- [7.1 A qubit is `1 + 1`](#71-a-qubit-is-1--1)
- [7.2 Registers and kets](#72-registers-and-kets)
- [7.3 Writing gates as clauses](#73-writing-gates-as-clauses)
- [7.4 The commands](#74-the-commands)
- [7.5 Superpositions in, and why that needed new machinery](#75-superpositions-in-and-why-that-needed-new-machinery)
- [7.6 Measuring the result](#76-measuring-the-result)
- [7.7 From a problem to a circuit](#77-from-a-problem-to-a-circuit)

### 7.1 A qubit is `1 + 1`

There is no qubit type. As in 42, a two-case choice carrying no data is `1 + 1`,
and the two cases are `L ()` and `R ()`. Q42 calls them `|0>` and `|1>` when
printing, and a file may name the type:

```
type qubit = 1 + 1
```

which is a printing abbreviation and changes nothing (the 42 manual, §3.7).

### 7.2 Registers and kets

Several qubits together are called a **register**, and in Q42 a register is a
nested pair, to the right:

```
|abc>   is   (a, (b, c))
```

You write states as kets on the command line: `"|0110>"`, or just `"0110"`.
Only *basis* states can be written down, which is deliberate. You make
superpositions by applying a gate.

### 7.3 Writing gates as clauses

A Q42 definition can be written as clauses, as in the 42 manual's Part I, and
it compiles to the point-free core. In Q42 **a name is a wire**: a pattern
names the qubits it takes apart, and a call names the qubits a gate acts on.
The compiler routes them together and back, and routing costs no gates (§9.4).
The first stage of `teleport.42` (teleportation is §8.5; only this stage
matters here):

```
def bell (q0, (q1, q2))  <->
    let q1       = h q1        in
    let (q1, q2) = cx (q1, q2) in
    (q0, (q1, q2))
```

reads as the circuit: Hadamard on `q1`, then a CNOT from `q1` to `q2`. A name
may be bound again once a gate has consumed it, so the wires keep their names
through the circuit.

A controlled gate is a definition with one clause per value of the control:

```
$ 42q show teleport cx
cx   (L (), q) <-> (L (), q)
cx   (R (), q) <-> (R (), x q)
cx!  (L (), q) <-> (L (), q)
cx!  (R (), x q) <-> (R (), q)
```

The two `cx!` lines are the clauses turned round, which is the adjoint (the 42
manual, §5). Matching a qubit like this is **quantum control**, not a classical
branch: a control in superposition matches both clauses, and both run, weighted
by its amplitudes. That is §6.4's `dist`, written with names.

A classical function is its truth table. To use a function `f` from bits to
bits inside a quantum program it has to be made reversible, and the standard way
is a gate `(x, y) ↦ (x, y XOR f(x))`, called an **oracle** for `f`. For
`f(x) = not x`, from Deutsch's algorithm (§8.4):

```
def orcnot (L (), y)  <->  (L (), x y)       -- f(0) = 1: flip y
def orcnot (R (), y)  <->  (R (), y)         -- f(1) = 0: leave y
```

The rules are 42's, tightened as §5.4 explains, and each has a message:

```
error: line 2: in `dup a <-> (a, a)`, `a` is used twice.  Q42 cannot copy a value: copying maps a space into a bigger one, so it is not unitary (QMANUAL section 5.2).
```

The others refuse a name matched twice, two clauses whose patterns (or terms)
overlap, an input (or output) no clause covers, a `let` pattern that can fail,
and a call inside a pattern. Every definition the rules accept is unitary.

Two things clauses do not do. They do not make superpositions: a definition
built from clauses alone permutes basis states, and every genuinely quantum
step, `h`, `v`, `omega` and what is built from them, enters as a call. And not
every definition they accept can yet be emitted as a circuit: when a
definition's inputs and outputs cannot be split the same way, it is compiled by
a construction that rearranges labelled values whose branches hold different
numbers of qubits, and no fixed set of wires can hold those (§9.4). It runs in the evaluator, and `42q emit` says why it will not emit it.
The design, and the proof that the compiled term means what the clauses say and
is unitary, are in `QSUGAR.md`.

### 7.4 The commands

```
42q FILE GATE STATE [-b]     apply a gate to a state
42q sample  FILE GATE STATE  apply it, then measure -- see section 7.6
42q law     FILE GATE STATE  check that `!` really is the adjoint
42q unitary FILE [GATE]      check `t ; t! = id` over the whole basis
42q matrix  FILE [GATE]      print the matrix
42q equal   FILE GATE GATE   decide whether two gates are the same -- 6.5
42q check   FILE GATE SPECFILE SPEC --encode ENC
                             check a gate against a 42 specification -- 7.7
42q emit    FILE [GATE]      write it out as OpenQASM 3 -- see section 9.4
42q type    FILE [GATE]      infer the type
42q show    FILE [GATE]      print a definition, its adjoint, and what it compiles to
```

`matrix` and `unitary` need to know how big the space is, and the *type* is what
tells them. Most gates are *polymorphic*, defined at many types rather than at
"n qubits": `x` is just `swapsum`, so its type is `a + b <-> b + a`, for any
`a` and `b`. Those two commands therefore
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

### 7.5 Superpositions in, and why that needed new machinery

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

### 7.6 Measuring the result

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

Two columns, deliberately. **exact** is the Born probability `|amplitude|²`
(§2.2), which only a simulator can know. **drawn** counts the outcomes of 100
*shots*: a shot is one run of the program followed by a measurement, and counts
of shots are all a real machine would give you. Seeing them together is the point: it shows
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

The `_` marks a qubit that was not measured. This is §8.4's algorithm, Deutsch's,
answering its question: **one query, one qubit, and the answer is certain.**

Measurement is *terminal*: it happens after the program, never inside it. That
is a deliberate line rather than a limitation of the command, and §9.2 explains
what it costs and why.

### 7.7 From a problem to a circuit

The commands above take a gate that already exists. A real task starts further
back, with a problem stated in ordinary terms, and ends with a circuit a quantum
computer can run. Getting from one to the other takes five steps, and the
running example here is the **modular adder**, `(a, b) ↦ (a, (a + b) mod N)`
for a fixed `N` and `a, b < N`, the arithmetic that Shor's factoring algorithm
(§9.1) is built from. The files are in `casestudy/`, and
[the case study](casestudy/CASESTUDY.md) gives the whole program and its results.

**1. State the problem in 42.** Write down what the answer should be, as a 42
program. The language is 42, not Q42, on purpose. A specification may work on
unbounded numbers, use a value twice, give no answer for inputs it does not care
about, and combine cases with `|`, and Q42 forbids all four (§5). Those
freedoms are what keep a specification short enough to be obviously right:

```
def reduce = keep | wrap                 -- keep s if s < n, else subtract n

def modadd (a, (b, n))  <->
    let (a, n) = lt (a, n) in
    let (b, n) = lt (b, n) in
    (a, reduce (add (a, b), n))
```

`lt` passes a pair through when its first number is the smaller and gives no
answer otherwise, so `modadd` is simply undefined unless `a, b < n`. 42 runs it:

```
$ 42 casestudy/spec modadd "(3, (4, 5))"
modadd(3, (4, 5)) =
  (3, (2, 5))
  -- 1 result
```

**2. Write the program in Q42.** Now decide *how* the answer is computed on a
fixed number of qubits. This is design work, and nothing derives it from step 1.
It means choosing how numbers are laid out in registers (§7.2), choosing a
construction (here the standard one, built from ripple-carry adders that pass a
carry bit along the register as column addition does), and choosing the
**ancillas**: extra qubits that start at `|0>`, serve as scratch space, and must
be returned to `|0>` at the end, since a qubit left holding a leftover value
stays entangled with the result and spoils it (§2.6). A Q42 program that simply
listed the specification's cases would also be correct, but compiled as written
it becomes a circuit that tests every case separately, exponentially larger than
a good construction.

The program's type says exactly how many qubits it needs, before anything runs.
`42q type casestudy/modadd mod3` reports nine `qubit`s for `N = 3`: two for each
of `a` and `b`, and five ancillas.

**3. Check the program against the specification.** On every input the
specification answers, run both: 42 runs the specification, Q42 runs the
program, and the two must agree. Q42's amplitudes are exact (§6.5), so the
check is that the program's output is *exactly one* basis state, with amplitude
exactly 1, holding the specification's answer, with every ancilla back at `|0>`.
Inputs the specification does not answer are not compared, which is the right
notion of correctness when nothing else will ever be fed in. Separately,
`42q unitary` confirms that the program is reversible on its whole space.

To compare, the two need a common language for their values: the specification
speaks of numbers, the program of qubits. An **encoder** says which basis state
stands for which value, and it is one more 42 definition, written beside the
specification:

```
def halve 0        <->  (L (), 0)              -- n  as  (n mod 2, n div 2)
def halve 1        <->  (R (), 0)
def halve (n + 2)  <->  let (b, h) = halve n in (b, h + 1)

def bits1 n  <->  let (b, 0) = halve n in b
def bits2 n  <->  let (b, h) = halve n in (b, bits1 h)

def enc3 (a, (b, 3))  <->  (bits2 a, (bits2 b, (L (), (L (), (bits2 0, L ())))))
```

`bits2` writes a number below 4 as two qubits, least significant first, and
`enc3` lays out `a`, `b` and the five ancillas, all `|0>`, in the order `mod3`
takes them. `42q check` then does the comparison:

```
$ 42q check casestudy/modadd mod3 casestudy/spec modadd --encode enc3
mod3 against modadd, through enc3
  [ok ] the program: 9 input(s) agree, exactly
  [ok ] the circuit: 9 input(s) agree (77 gate(s) on 9 qubit(s))
  of 512 basis states, 496 encode no input and 7 encode one modadd does not answer; not compared
```

It goes through every basis state of the program's input, and runs the encoder
*backwards* on it, which is where 42's two directions earn their keep: a state
that encodes no value at all, such as one with an ancilla set, is skipped, and
so is a value the specification gives no answer for, such as `a = 3`. For each
of the nine that remain, it runs the specification, encodes the answer
*forwards*, and requires the program to produce exactly that basis state. The
second line is step 5, below.

Nothing in `42q check` is about adders: the program, the specification and the
encoder are all arguments, and `--decode` takes a second encoder when the
answers are laid out differently from the inputs. What is specific to a problem
is the encoder, which fixes which qubits hold which value. The command has one
real limit, and it follows from what a 42 specification can say. A
specification speaks of values, not amplitudes, so the check applies to
programs that behave classically on the inputs it covers, taking each one to a
single basis state: arithmetic, oracles, and the other reversible classical
parts of a quantum algorithm. A genuinely quantum program, such as the Hadamard
gate or the quantum Fourier transform, produces a superposition, which no 42
specification can describe. Q42 writes such programs perfectly well (§9.1 lists
them); it is only this way of checking them that does not apply. They are
checked instead with `42q matrix`, `42q unitary`, and `42q equal` against
another version (§6.5). The command also reports two conditions when they fail: the encoder
must not give two values for one basis state, and the specification must give
one answer per input, since a program produces only one.

**4. Emit the circuit.** `42q emit` turns the program into OpenQASM 3, the
standard text format for circuits (§9.4), and `--gates` lists the same gates in
a form that is easier to read:

```
$ 42q emit casestudy/modadd mod3 --gates
mod3 : 9 qubit(s), 77 gate(s)
  cx 0, 2
  cx 0, 5
  ccx 5, 2, 0
  ...
```

`cx` is the controlled NOT and `ccx` the Toffoli gate, which flips its third
qubit when the first two are both 1 (§6.4); the numbers are qubit positions.

**5. Check the circuit against the specification.** Run the emitted gate list
on the same inputs, with a simulator that shares no code with Q42, and compare
with the specification again. `42q check` does this in the same run, and it is
the second line of its report. For arithmetic like this, whose gates only
permute basis states, following one bit string through the gates is a complete
simulation, and it works at any width. A circuit with genuinely quantum gates in
it goes through `tools/qasm_sim.py` instead, one gate matrix at a time, which
is exponential in the number of qubits, so `42q check` does that only up to ten
qubits and says so when it skips the circuit.

**Why two checks.** They catch different mistakes. Step 3 catches a wrong
*program*: the construction does not compute what the specification says.
Step 5 catches a wrong *translation*: the program is right, but emitting it
changed its meaning. Step 5 alone would not tell you which of the two had
failed, and step 3 alone would trust the emitter.

**Is the specification necessary?** No. Nothing requires steps 1, 3 and 5:
a Q42 program can be written, emitted and run without a specification, and most
programs, quantum or not, are written without a formal one. What takes its
place in ordinary programming is testing, and Q42 has the lighter-weight
versions of that too: `42q FILE GATE STATE` on a few inputs, `42q unitary` for
reversibility, `42q equal` against a version already trusted. The specification
is the exhaustive form of something done informally anyway.

The balance tips further towards writing one here than in ordinary programming,
for three reasons:

- **The check is complete, not a sample.** For an ordinary program an
  executable specification still only allows testing, since the inputs never
  run out. A Q42 program has a register of fixed size, so `42q check` covers
  *every* input the specification answers. The same effort buys a proof over
  the valid inputs rather than evidence.
- **Some quantum mistakes do not show in the answer.** An ancilla left at `|1>`
  can leave the result register exactly right, so trying a few inputs and
  reading the result finds nothing wrong. But the stray qubit is entangled with
  the result (§2.6), and once the program is part of a larger algorithm it
  silently destroys the interference the algorithm depends on (§2.5).
  `42q check` requires every ancilla back at `|0>`, so it catches the mistake.
- **Debugging on a quantum computer is much harder.** A running machine cannot
  be paused to look at its state, a measurement gives one random outcome and
  destroys the rest (§7.6), and every run costs time and money. The habits of
  ordinary debugging, printing a value or stepping through, have no equivalent
  there, so a mistake caught before the circuit leaves the simulator is worth
  more.

The specification applies only where it can: to the parts of a program that
behave classically. For the genuinely quantum parts there is no 42
specification to write.

After step 5 the OpenQASM goes to a standard toolchain such as Qiskit, which
fits it to a particular machine's qubits and connections (§9.4). For the
modular adder the case study compares the result with the same construction
built in Qiskit: the two circuits are identical, gate for gate.

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

becomes a *permutation* of the `2ⁿ × 2ⁿ` basis states: no two registers go to
the same place, because the step can be undone, `a` being recovered as
`(a + b) − b` mod `2ⁿ`. (Algebraically, the step is the matrix `[[0,1],[1,1]]`,
which has determinant `−1`, a number with an inverse mod `2ⁿ`.) A permutation of
basis states is a matrix of 0s and 1s with one 1 in each row and column, which
is unitary, and therefore expressible. `q42/fib.42` does it on two 2-bit registers,
`|x0 x1 y0 y1>`, writing each step as the circuit it is (§7.3):

```
def add4 (x0, (x1, (y0, y1)))  <->               -- (x, y) -> (x, x+y mod 4)
    let (x0, (y0, y1)) = ccx (x0, (y0, y1)) in     -- Toffoli: x0, y0 -> y1
    let (x0, y0)       = cx (x0, y0)        in     -- CNOT:    x0 -> y0
    let (x1, y1)       = cx (x1, y1)        in     -- CNOT:    x1 -> y1
    (x0, (x1, (y0, y1)))

def swapregs (x0, (x1, (y0, y1)))  <->  (y0, (y1, (x0, x1)))

def fib = swapregs ; add4
```

In the comments, `x0, y0 -> y1` means controls `x0` and `y0`, target `y1`.
`add4` is three gates because `y += x` is "if `x₀` then `y += 1`" followed by
"if `x₁` then `y += 2`". Adding 1 to the two-bit `y = (y0, y1)`, low bit first,
flips `y0` and, if `y0` was 1, carries into `y1`; controlled on `x0`, that is the
Toffoli (carry: flip `y1` if `x0` and `y0`) followed by a CNOT (flip `y0` if
`x0`). Adding 2 flips `y1` alone: the second CNOT. The Toffoli comes first
because the carry depends on the old `y0`. `swapregs` is no gates at all:
its clause only rearranges, and rearranging emits nothing.

Iterating gives the Fibonacci numbers mod 4:

```
step  0: register = (0, 1)     F_0  = 0
step  3: register = (2, 3)     F_3  = 2
step  5: register = (1, 0)     F_5  = 5,  mod 4 = 1
step 10: register = (3, 1)     F_10 = 55, mod 4 = 3
```

and since it is unitary, running it backwards recovers the seed exactly, rather
than "a set containing the seed", which is what 42 would give you. Applying `fib`
six times brings every register back to where it started, and no fewer times
does (its *order* is 6). That matches number theory: the Fibonacci numbers mod
`m` repeat with a fixed period, called the Pisano period of `m`, and the
Pisano period of 4 is 6.

### 8.3 The quantum part

Everything above is a permutation, so it is reversible *classical* computing and
42 could do it too. What Q42 adds is that the seed may be a superposition:

```
def hy0 (x0, (x1, (y0, y1)))  <->  let y0 = h y0 in (x0, (x1, (y0, y1)))
def qfib = hy0 ; fib
```

puts one bit of the seed through a Hadamard first. The register then holds two
seeds at once, in superposition, and every later step advances both: two
*orbits*, the sequences of registers each seed runs through, computed together. The whole
thing still inverts exactly.

### 8.4 Deutsch's algorithm, and what Q42 shows you

Fibonacci is arithmetic. Deutsch's algorithm is a real quantum algorithm, the
smallest one there is and the first found to beat its classical rival.

The problem: you are handed a black box computing an unknown one-bit function
`f`, and asked whether `f` is **constant** (`f(0) = f(1)`) or **balanced**
(`f(0) ≠ f(1)`). Classically you must evaluate `f` twice, since one evaluation
tells you nothing about the other. Deutsch's algorithm answers after one.

The black box has to be reversible like everything else, so it is an oracle in
the sense of §7.3, `(x, y) ↦ (x, y XOR f(x))`: it keeps `x` and XORs `f(x)` into
a second qubit. That is the Toffoli trick from §1,
which is also `mul` keeping its multiplier in the 42 manual's §9.3. There are only
four one-bit functions, so `q42/deutsch.42` writes all four out, each as its
truth table (§7.3):

```
def orc0 (a, y)     <->  (a, y)              -- f(x) = 0       constant

def orc1 (a, y)     <->  (a, x y)            -- f(x) = 1       constant

def orcid (L (), y)   <->  (L (), y)         -- f(x) = x       balanced
def orcid (R (), y)   <->  (R (), x y)

def orcnot (L (), y)  <->  (L (), x y)       -- f(x) = not x   balanced
def orcnot (R (), y)  <->  (R (), y)
```

**The algorithm** is three steps: superpose both inputs, query the oracle once,
and interfere the results back together. `h * h` applies a Hadamard to each of
the two qubits, and `h * id` to the first only:

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

And it will say so outright if you measure the first qubit (§7.6):

```
$ 42q sample deutsch dnot "|01>" --bits 0
    outcome   exact  drawn
    |1_>  100.0%    100  ##############################
```

**Why it works.** Follow the amplitudes from the input `|01>`. The two
Hadamards give

```
1/2 ( |0> + |1> ) ( |0> - |1> )  =  0.5|00> - 0.5|01> + 0.5|10> - 0.5|11>
```

Now the oracle XORs `f(x)` into the second qubit. XORing 1 into `|0> − |1>` gives
`|1> − |0>`, the same with its sign flipped; XORing 0 leaves it alone. So the
second qubit is unchanged *except for a sign*, `−1` exactly when `f(x) = 1`, and
that sign ends up on the first qubit's term for that `x`:

```
1/2 ( s0 |0> + s1 |1> ) ( |0> - |1> )        s0 = (-1)^f(0),  s1 = (-1)^f(1)
```

If `f` is constant, `s0 = s1` and the first qubit is `±(|0> + |1>)/√2`; the last
Hadamard turns that into `±|0>` (§2.4 read backwards). If `f` is balanced,
`s0 = −s1`, the first qubit is `±(|0> − |1>)/√2`, and the Hadamard turns it into
`±|1>`. One query decided a property of both values of `f`, because the query
was made on a superposition of both inputs and the answer came back as a sign,
which the final Hadamard turns into a bit by interference (§2.5).

That is why the *state* is the more instructive output. A device hands you one
bit and hides the mechanism. Q42 shows you the amplitudes, so you can see the
second qubit's `+/-0.707107`, the `|0> − |1>` that carried the sign, and the
first qubit holding the answer. For understanding *why* an
algorithm works, as opposed to what it returns, that is worth more than a
sample. §9.1 returns to this.

### 8.5 Teleportation, without measuring in the middle

**Teleportation** moves the state of one qubit to another qubit, possibly far
away, without sending the qubit itself, using a shared entangled pair and two
classical bits. The protocol: Alice holds a qubit `q0` in some state she wants
to send, which she need not know. Alice and Bob each hold one half of a Bell
pair (§2.6), `q1` and `q2`. Alice applies a CNOT from `q0` to `q1` and a
Hadamard to `q0`, measures both her qubits, and sends Bob the two bits she got.
Bob applies `X` (NOT) to `q2` if the second bit is 1, and `Z` (§6.2: multiply
`|1>` by `−1`) if the first is 1. After that, `q2` holds exactly the state `q0`
started in.

It is the textbook example of an algorithm that *requires* measuring half way
through, and Q42 has no mid-circuit measurement (§9.2), so this ought to be
impossible.

It is not, and the reason is a theorem. The **principle of deferred measurement**
(Nielsen & Chuang §4.4; their *Quantum Computation and Quantum Information* is
the standard textbook) says that any circuit with mid-circuit measurements and
classically-controlled gates can be rewritten with every measurement moved to the
*end*, each classical control replaced by a **quantum** control. Q42 has quantum
control, a clause that matches on a qubit (§7.3), so the rewritten circuit is an
ordinary Q42 definition.

`q42/teleport.42` is that circuit, on `(q0, (q1, q2))`, and the deferral is
visible in one stage:

```
def bell (q0, (q1, q2))  <->                       -- entangle q1 with q2
    let q1       = h q1        in
    let (q1, q2) = cx (q1, q2) in
    (q0, (q1, q2))

def alice (q0, (q1, q2))  <->                      -- CNOT q0->q1, then H on q0
    let (q0, q1) = cx (q0, q1) in
    let q0       = h q0        in
    (q0, (q1, q2))

def bob (q0, (q1, q2))  <->                        -- CNOT q1->q2, CZ q0->q2
    let (q1, q2) = cx (q1, q2) in
    let (q0, q2) = cz (q0, q2) in
    (q0, (q1, q2))

def tele = bell ; alice ; bob
```

`cz` is `z` controlled on its first qubit. `bob` is where "if Alice's bit is 1,
apply X" became a CNOT, and "if the other bit is 1, apply Z" a controlled-Z: the
same conditionals, controlled by the qubit rather than by a bit read out of it.

It is unitary like everything else:

```
$ 42q unitary teleport tele --qubits 3
  [ok ] tele ; tele! = id on 8 dimension(s)
```

Sending `|0>` proves little, so `check` prepares a real state on `q0`, a
superposition with a phase (`prep = h ; t`), teleports it, and applies `prep!`,
the preparing gate's inverse, to `q2`. If the state genuinely arrived,
amplitudes and phase intact, `q2` must return to `|0>` with certainty:

```
$ 42q sample teleport check "|000>" --bits 2
    |__0>  100.0%    100  ##############################
```

It does. The deferred measurements have not vanished: they are the other two
qubits, which end up spread evenly over all four outcomes, exactly the four
results Alice would have read. (`checkh` is `check` with `h` as the preparing
gate, so that the amplitudes print simply.)

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
- [9.5 Q42 beside other quantum languages](#95-q42-beside-other-quantum-languages)

### 9.1 What it is for

A fair reading of a list of limitations is "then what use is it?", so the useful
part first.

**Expressiveness.** `omega` and `v` generate Clifford+T (§6.2). That gate set is
*universal*: any unitary can be approximated by a Clifford+T circuit to any
precision you like, and Clifford+T circuits themselves are represented exactly.
The building blocks of the famous algorithms are all writable: the step of
Grover's search (§2.5) that amplifies the right answer, the arithmetic modulo
`N` inside Shor's factoring algorithm, and the quantum Fourier transform, the
quantum version of the discrete Fourier transform and the core of Shor's. §8.4 writes out
Deutsch's algorithm in six lines.

These are genuinely quantum programs, using superposition, interference and
entanglement, not classical ones run on qubits, and the repository has them as
files: the Hadamard gate `h` and the entangling `bell` and `ghz` in
`q42/gates.42`, Deutsch's algorithm in `q42/deutsch.42`, teleportation in
`q42/teleport.42`, Grover's search in `q42/grover.42`, and the quantum Fourier
transform on three qubits, exactly, in `q42/qft3.42`. What Q42 leaves out is
measuring in the middle of a program (§9.2), not quantum behaviour.

The Fourier transform shows the one qualification. Q42's phases are eighth
turns (§6.2), and the transform on four or more qubits also wants a
sixteenth turn, and finer ones as it grows, which no single Q42 gate gives.
`qft.42`, a 42 program that generates the transform for any width, therefore
leaves those small rotations out, giving the *approximate* transform, which is
also what hardware usually runs. Where the exact one is needed, a finer
rotation can be approximated by a longer sequence of Q42 gates to whatever
precision is wanted, about a hundred gates for one part in 10¹⁰, which is the
universality above at work. So every quantum program can be written: some
angles exactly, the rest to a chosen precision, which is the trade-off
error-corrected hardware makes too (§9.4).

**Gate identities, checked mechanically.** What Carette et al.'s calculus (§4.2;
they call it `√Π`) contributes is an *equational theory*, a set of rules for
proving two circuits equal (§6.5), and Q42 makes it executable. `42q law` checks that `!` really is the adjoint; `42q unitary` checks
`t ; t! = id` across a whole library; `42q matrix` prints the matrix so you can
compare. Gate identities like `H ; H = id`, `H ; X ; H = Z`, `S ; S = Z` and
`(Ctrl U)† = Ctrl U†`: all of these can be run, and each is a test in
`tests/test_q42.py`.

**Amplitudes and samples, side by side.** `42q sample` measures a result as a
device would, and prints the exact Born probabilities next to the draw (§7.6).
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
on, the one where you trigger it yourself — as Quipper (a quantum language
embedded in Haskell) does with `with_computed`, and Q# (Microsoft's quantum
language) with `within … apply`. Those two derive the inverse from the forward
code as well, so that is not what separates them. What Q42 adds is that the
inverse exists for *every* term, with no declaration and no check that the term
happens to avoid measurement, because no term can contain one (§9.5 says this
more carefully). That is a smaller claim than Silq's, and a different one.

**Evidence for a claim about language design.** `q42/` shares the data types for
values and programs (`Value`, `Term`), the parser and the whole type checker
with `rel42/`, and `q42.dagger is
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

Q42 is a language for the **unitary layer** of quantum computing, the part made
of gates, with measurement at its edge. That sentence is the boundary, and it is chosen rather
than unfinished: it is what buys every property in §9.1.

**Inside the line.** Every term denotes a unitary, so `!` is defined on every
term with no side conditions, `t ; t! = id` holds by construction, and
`42q unitary` can assert it over a whole file. Measurement sits at the end:
`42q sample` applies the Born rule to the state the program produced (§7.6).
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
term, `measure_Z = copy_Z ≫ fst`: copy in the standard basis (§5.2's `copy`),
then keep only the first copy (`≫` is their composition). Keeping one copy
needs a way to `discard` the other, and that arrives only with a further layer
of their construction, which hides what is thrown away. And the resulting model
is one of **partial maps**, landing not among unitaries but among *contractions*,
linear maps on the spaces of states of §2 that never make a vector longer. The authors are candid about the
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
by one measurement, and what comes after (a classical calculation, the
continued-fraction step, that turns the measured value into a factor, and a
retry if it fails) is ordinary classical code *around* that subroutine. Q42 hands you the measured
value and a script does the rest.

What is genuinely on the far side of the line is narrower than it first looks:
**error correction** (§2.7), where an error's signature, its *syndrome*, is
measured and acted on repeatedly while the computation continues;
**measurement-based computing**, a model in which the whole computation is done
by measuring qubits of a large entangled state, each measurement chosen from the
results of earlier ones; and **qubit reuse**, measuring a qubit to reset it for
another use, which matters when hardware has a fixed qubit budget and not at
all in a simulator. None of these is what Q42 is for.

Three smaller boundaries follow from the same place:

- **No mid-program state preparation.** A Q42 program is a unitary on a fixed
  space, so there is no conjuring a fresh `|0>` half way through; that would
  change the dimension. Inputs come from the command line instead.
- **No noise.** No decoherence, no gate fidelities, no error model. Everything
  here is the idealised unitary layer.
- **No recursion that does anything.** A definition may call itself, but a call
  that is ever reached never stops. A unitary reaches every basis value of its
  output, so a call that is reached at all receives every value of its input
  type. Inside its own body a definition has one type, so that is the
  definition's own type, and the call receives again the very inputs that led
  to it. A definition whose unfolding stops therefore never makes its call.
  Recursion over a register, one qubit per call, would need the call at a
  smaller type, and the type checker rejects it. Loops over widths are written
  in 42, which generates the Q42 terms (§9.5).

### 9.3 The comparison that is not the right one

An `n`-qubit gate is a `2ⁿ × 2ⁿ` matrix, so running Q42 costs exponential time
and memory. It is worth being precise about what that does and does not mean.

It does **not** distinguish Q42 from other quantum languages. Every classical
simulator of quantum circuits pays this, including those of Qiskit, IBM's
widely used quantum toolkit; it is a fact about simulating quantum mechanics on a
classical machine, not about this implementation. A quantum *language* is not in
competition with quantum *hardware*: Q42's peers are Silq, Π and Quipper, not a
chip.

There is one genuine nuance. By the **Gottesman–Knill theorem**, circuits built
only from Clifford gates (`h`, `s`, `cx`) are efficiently simulable classically,
despite looking thoroughly quantum, entanglement and interference included. So
"quantum-looking" and "hard to simulate" are not the same property. It is `t`
that takes a circuit beyond Clifford, and Q42 has `t`. §6.2 says the same thing
as a fact about groups rather than about simulation: `s` generates the
order-four phase group and `t` the order-eight one, and the boundary
Gottesman–Knill draws falls between them.

**What a quantum computer is fast at: the Fourier transform as an example.**
Simulation is the cost on a classical machine. The opposite question, what a
quantum computer does cheaply, has an answer that is easy to state too
generously, and the quantum Fourier transform shows why.

The classical Fast Fourier Transform on `N` numbers takes about `N log N`
operations. The quantum Fourier transform on `n` qubits acts on all `N = 2ⁿ`
amplitudes at once, and takes about `n²/2` gates: a Hadamard on each qubit and
a controlled rotation for each pair. Leaving out the smallest rotations, the
approximate transform of §9.1, brings that down to about `n log n` gates with
negligible error. For thirty qubits, about a billion amplitudes, that is some
`3 × 10¹⁰` operations classically against roughly five hundred gates.

It is nonetheless **not a faster FFT**, because the data cannot get in or out.
Loading a billion arbitrary numbers into amplitudes costs, in general, about a
billion operations, which spends the whole saving before the transform starts.
And the result cannot be read: a measurement gives *one* basis state, chosen
with probability `|amplitude|²` (§7.6), so recovering all the coefficients
would take exponentially many runs. For transforming data you already have, a
sound file or an image, a quantum computer is no help.

Where it pays is *inside* an algorithm, when the state is produced by the
computation itself and only a global property of the result is wanted. In
Shor's algorithm the modular arithmetic (the case study's adder is its
building block) produces a state whose amplitudes repeat with an unknown
period. The Fourier transform turns that period into sharp peaks, a single
measurement lands near one of them with good probability, and a little
classical arithmetic recovers the period from it. Nothing is loaded and almost
nothing is read, so the exponential gap survives. Phase estimation, the other
large user of the transform, works the same way. That is the general shape of a
quantum speedup: the gain lives in what stays inside the machine.

Two refinements matter on real hardware:

- **On error-corrected machines the rotations dominate the cost.** Only a
  finite set of gates is cheap there (§9.4), so each small-angle rotation is
  assembled from a sequence of T gates, longer the more precisely it must be
  right. That is why the approximate transform is standard: the smallest
  rotations cost the most and matter the least. Q42's eighth turns (§6.2) are
  the same constraint, in plain view.
- **When the transform is followed at once by a measurement,** as in Shor's
  algorithm, it can be done one qubit at a time: measure a qubit, then choose
  the next rotations from the outcome (Griffiths & Niu, 1996). That replaces
  every two-qubit gate with a one-qubit gate chosen by a classical bit, a real
  saving on hardware. It needs measurement in the middle of the program, which
  Q42 excludes (§9.2), so Q42 runs the version in which every rotation is under
  quantum control instead.

**Could a quantum computer run a large language model?** The question is
natural, because the visible input and output, a prompt and its answer, are a
few thousand tokens each, which looks like exactly the narrow interface the
Fourier transform needs. It is not, because in a language model the data that
matters is not the prompt but the model:

- **The weights are the input.** A modern model has tens to hundreds of billions
  of parameters, and every token it produces passes through essentially all of
  them. They would have to be loaded into the machine, which is the loading
  problem above on an enormous scale. The hardware proposed for it, "quantum
  RAM", does not exist in practical form, and whether it can be built cheaply is
  doubtful.
- **The work is dense matrix multiplication** of numbers already held in
  memory, which is what GPUs are built for, and for which no general quantum
  speedup is known.
- **The network is nonlinear and the machine is not.** A neural network depends
  on nonlinear steps, its activation functions and the softmax of attention,
  while every quantum gate is a matrix applied to amplitudes (§2.3), so linear.
  Nonlinearity needs measurement or costly workarounds.
- **Every token is a measurement.** Producing a token means reading one out,
  which collapses the state (§7.6), so it must be rebuilt for the next token,
  hundreds of times per answer.
- **The scales are far apart.** A GPU performs on the order of 10¹⁴ operations a
  second, and a large model needs roughly that much per token; an
  error-corrected quantum gate takes microseconds to milliseconds, and the
  machines in prospect have tens to hundreds of reliable qubits, against the
  gigabytes of state a model holds.

The history of the field is a caution here. Several "quantum machine learning"
algorithms proposed between about 2008 and 2016 claimed exponential speedups.
In 2018 Ewin Tang showed that the best known of them, for recommendation
systems, could be matched by a classical algorithm given the same assumptions
about access to the data, and others followed: the speedups had been hidden in
the assumption that the data was already loaded.

Where quantum computing and machine learning do meet is elsewhere. When the
data is itself quantum, coming from experiments, sensors or quantum
simulations, there are proven advantages: a quantum computer can learn
properties of quantum states from far fewer experiments (Huang et al., 2022),
because the input is already in the machine and nothing has to be loaded. And
the other direction is real and growing: machine learning is used to decode
the errors of quantum error correction, to calibrate hardware, and to design
circuits.

So a language model is close to the worst workload for a quantum computer: a
large body of classical data, multiplied by dense matrices. That is also the
general picture. A quantum computer is a specialised accelerator, driven by a
classical one throughout, for problems with the structure the Fourier
transform example shows, and not a replacement for ordinary computers.

In summary: Q42 is a language and a proof-checker for the unitary
layer of quantum computing, complete for that layer, with measurement at its
edge (§9.2) and simulation cost as the price everybody pays.

### 9.4 Could a Q42 program run on real hardware?

It can, once machines are stable and large enough: `42q emit` writes any
definition out as OpenQASM 3, a standard text format for quantum circuits, which
every mainstream toolchain reads. This
section says why the language sits well for that, what the emitter does, and
where the real limit is.

The language is well placed for it. The machines that will run long computations
must correct their own errors (§2.7), and the leading scheme for that, the
*surface code*, makes Clifford gates cheap and the `t` gate expensive. Such
machines are therefore built around Clifford+T, and the cost of a program on
them is counted by its *T-count*, the number of `t` gates. A Q42 program already
is a circuit in exactly that gate set, since `omega` and `v` generate
Clifford+T. Nothing needs translating into another model of
computation.

Better, most of the language costs nothing to execute. Classifying each primitive
by what it does to the underlying bits:

| primitive | effect on the bits | on hardware |
|---|---|---|
| `id`, `assocsum`, `assocprod`, `unitsum`, `unitprod`, `dist` | nothing at all | **free** |
| `swapprod` | permutes them | a relabelling, or a SWAP |
| `swapsum` | flips one | NOT, the gate `X` |
| `omega` | nothing, but multiplies by a phase | a phase gate |
| `v` | superposes them | √X, half a NOT (§6.1) |

Only **three of the ten** are physical operations, and they are exactly X, phase
and √X. Everything else is the semiring plumbing of §3.5, and plumbing is
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

**Measurement.** *Terminal* measurement is part of the tooling today (§7.6):
run the unitary, then sample the result. It is the Born rule and a random
number, nothing more. It covers every algorithm whose last step is a single
measurement: Deutsch (§8.4), Bernstein–Vazirani (which finds a hidden bit string
with a single query), Grover, and the quantum subroutine of Shor.

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
anything handed over as OpenQASM 3 or QIR (Quantum Intermediate Representation,
another exchange format). They are not Q42's to write.

What is Q42's own is the lowering, and it is short. Two parts:

- **wire assignment**: which physical qubit is which position in the nested pair,
  the width rule above read constructively, plus tracking `swapprod` as a
  permutation carried to the end so that it costs nothing instead of three CNOTs.
  That is exactly what `q42/emit.py` does, and it is why **seven of the ten
  primitives emit no gate at all**: `id`, `assocprod`, `unitprod` and `dist`
  re-bracket, `swapprod` is carried in the layout, and `assocsum` and `unitsum`
  cannot occur at a register type in the first place. Only `swapsum`, `omega` and
  `v` produce output.
- **depth bounding**: the emitter unrolls definitions on a depth budget. A
  recursive call that is reached never stops (§9.2), so the budget catches
  exactly such a definition and reports it.

Control needs no rule of its own, which is worth knowing: at a type `a + b` the
first qubit is the tag, and `f + g` means f under tag 0 and g under tag 1. From
that alone, `cx`, `ccx` and the Fredkin come out as single gates, and
`t = id + omega` derives as the T gate, a controlled global phase being a
relative one. The emitter never mentions `ctrl`, which is right, `ctrl`
being a library definition rather than a language feature.

Every definition in every Q42 library emits, and each is checked against Q42's own
matrix by a simulator in `tools/qasm_sim.py` that deliberately shares no code with
the evaluator. What comes out is unoptimised, with `z` leaving as four
eighth-turn phases, because correctness came first and the *transpiler*, the
optimising pass of the downstream compiler, folds most of it.

There is also one piece that is not commodity, because no previous language
needed it. Q42 defers every measurement (§9.2), and on hardware deferral is not
free: it spends *coherence time*, the short while a qubit keeps its state before
decoherence (§2.7) spoils it, and forbids reusing a qubit. So a serious lowering
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
limit on what Q42 can *name*. A phase gate turning `|1>` by `π/7`, written
`Rz(π/7)` in the literature, must arrive already approximated by Clifford+T,
where a device with native rotations would have applied it as one control
pulse.

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
Q42 with a 16th, 32nd, … root of 1 added at each level (a *cyclotomic* Q42, in
the number theorist's word) would keep exact evaluation and decidable equality
and lose only the finite presentation: the fixed, finite list of generators and
equations. Going the whole way, to
a continuum of angles, loses exactness itself, and with it the property that a Q42
program *has* a matrix rather than an approximation to one. That last trade is the
one the language is made of.

Read beside §6.2, the three arguments this section has made turn out to be one.
The phases of Q42 form `Z₈`, the cyclic group of the eight eighth-turns, a finite
subgroup of the circle of all phases. A cyclotomic Q42 is a larger finite
subgroup, `Z₁₆` or `Z₃₂`. The continuum is the circle itself. And
Eastin–Knill is the statement that no machine which corrects its errors can offer
you the circle: its cheap alphabet is finite, so it sits somewhere on that ladder
and never at the top. So *why eight*, *what would lifting cost*, and *why is the
restriction not an artefact of one architecture* are one question asked three
times — **which finite subgroup of the phase group do you take, and what does the
choice buy** — and Q42's answer is the smallest rung at which the language is
universal at all, with `v` and the plumbing held fixed.

### 9.5 Q42 beside other quantum languages

Several languages exist for programming quantum computers. They differ less in
which gates they offer, since nearly all reach a universal set, than in **what a
program is**, and that one difference explains most of the others. Six are worth
knowing:

- **Qiskit** (IBM) and **Cirq** (Google) are Python libraries. A program is an
  ordinary Python program whose calls append gates to a circuit object, which is
  then sent to a simulator or a device. They are the most widely used, and they
  run on real hardware today.
- **Q#** (Microsoft) is a standalone language with its own compiler. A quantum
  routine is an `operation`; qubits are allocated with `use`, and measuring one
  is an ordinary operation, `M`, whose result the program can branch on.
- **Quipper** (Green, Lumsdaine, Ross, Selinger & Valiron, 2013) is embedded in
  Haskell. A program is a Haskell function that generates a circuit, which lets
  it describe circuits far too large to run and count what they would cost.
- **Silq** (Bichsel, Baader, Gehr & Vechev, ETH Zürich, 2020) is a standalone
  language whose type system works out where temporary qubits must be
  uncomputed (§1), so that the programmer never writes the undo.
- **Guppy** (Quantinuum) is embedded in Python and designed for measuring in the
  middle of a program and branching on the result while the qubits are still
  live, which Quantinuum's trapped-ion machines support.
- **OpenQASM 3** is not a language you would write algorithms in but a text
  format for circuits, gate by gate: the common output of the others, and what
  `42q emit` writes (§9.4).

Set beside them, Q42 differs on four points.

| | Qiskit, Cirq, Guppy | Q# | Quipper | Silq | Q42 |
|---|---|---|---|---|---|
| a program is | Python code that builds a circuit | a sequence of operations | Haskell code that builds a circuit | a sequence of statements | a term that denotes a matrix |
| measure mid-program | yes | yes | yes | yes | no (§9.2) |
| the inverse | derived, if no measurement | derived, if declared `is Adj` | derived, if no measurement | derived, if no measurement | defined on every term |
| two programs equal? | simulate, compare approximately | simulate, compare approximately | simulate, compare approximately | simulate, compare approximately | decided exactly (§6.5) |
| runs on hardware | directly | via QIR, Microsoft's compiler format | not the aim | simulator only | via OpenQASM 3 (§9.4) |
| a circuit for every width is generated in | Python | Q# itself | Haskell | Silq itself | 42 (`qft.42`) |

**What a program is.** In Qiskit, Cirq, Guppy and Quipper there are two
languages at once: the host language (Python or Haskell), which runs on your
computer and decides which gates to emit, and the circuit it emits, which is
what runs on the quantum machine. Loops, recursion and conditionals belong to the
first; only a flat list of gates reaches the second. Q# and Silq have loops of
their own, and their compilers turn a program into the gates that run. In Q42 a
term *is* the circuit, `;` and `*` and `+` are its only ways of combining
things, and its meaning is a single matrix (§3.4). A loop that produces circuits
of every width (a *family*) is not a Q42 term, any more than it is a Qiskit
circuit. In Q42 the loop is written in 42: `qft.42` is a recursive 42 program
that takes a width and produces the quantum Fourier transform at that width as
data, and `tools/unquote.py` turns that data into Q42 source, which
`42q unitary` then checks like any other library. So Q42 has a host language
like the others, and it is the language Q42 was made from. RELATED.md §11.6
discusses this.

**Measurement.** Every other language here can measure a qubit half way through
and choose what to do next from the result; for Guppy that is the point. Q42
measures only at the end, with `42q sample` (§7.6), which also shows the exact
probabilities beside the draw. It cannot measure half way through, by design, and §9.2 gives the reason (a term that measures has no
inverse) and the theorem that makes the omission cost no computing power.

**The inverse.** Most of these languages can produce the inverse of a quantum
routine for you: Qiskit's `inverse()`, Q#'s `Adjoint`, Quipper's
`reverse_generic`. But each must first make sure the routine has no
measurement in it, or no other step without an inverse, and refuses
otherwise; in Q# you declare `is Adj` and the compiler holds you to it. In Q42
`!` applies to every term without a declaration, because no term can contain
such a step. The same holds for control: Q#'s `Controlled` turns an operation
into its controlled version when the operation permits it, Q42's `ctrl` (§6.4)
does so for every term.

**Deciding equality.** To learn whether two Qiskit circuits do the same thing,
you simulate both in floating point and compare the matrices up to a tolerance,
so "equal" means "equal to twelve places". Q42's generators are fixed numbers,
so its amplitudes can be stored exactly, and `42q equal` *decides* the question,
with no tolerance (§6.5). Q42 also has equations for proving two terms equal
without computing their matrices, but §6.5 is candid that they are complete only
for some families of circuits. A complete set for all of Clifford+T belongs to
the ZX-calculus, a graphical notation in which circuit diagrams are rewritten
into one another; ZX is a notation for reasoning, though, not a language you
run.

In short, the mainstream languages are built to run programs on the machines
that exist, with every convenience a host language gives. Q42 is built so that
every program has a single meaning that can be inverted, controlled and
compared exactly, and it pays for that with no mid-program measurement.
RELATED.md §8 and §11 place it against these languages, and
against verification languages like QWIRE and Qunity, in more detail.

To see the comparison on a real program, [the case study](casestudy/CASESTUDY.md)
writes the modular adder at the heart of Shor's algorithm in Q42, checks it on
every valid input against a readable specification in 42, and builds the same
circuit in Qiskit. The two come out identical, gate for gate, before and after
Qiskit's optimiser. The case study is also candid about what that does not
show: Q42's checks are exact, but a Qiskit user can test the same inputs, and
the cheapest known adder relies on measuring mid-circuit, which Q42 excludes.

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
| `x`, `y`, `z` | the Pauli gates: `x` is NOT (`swapsum`), `z` multiplies `\|1>` by `−1`, and `y` is `x ; z`, up to a global phase |
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
| `42q check FILE GATE SPECFILE SPEC` | check a gate, and its emitted circuit, against a 42 specification, through `--encode ENC` (§7.7) |
| `42q emit FILE [GATE]` | write it out as OpenQASM 3; `--qubits N`, `--gates` |
| `42q type FILE [GATE]` | infer the type |
| `42q show FILE [GATE]` | print a definition, its adjoint, and what it compiles to |

### Source files

```
type qubit = 1 + 1                  -- a printing abbreviation
def  name pattern <-> term          -- a clause (§7.3)
def  name   = gate                  -- a point-free definition
def  name m = gate                  -- m is a parameter, standing for a gate
-- comments run to end of line
```

Clauses follow the 42 manual's §4 and §19, with §5.4's changes: every name used
exactly once on each side; patterns covering each input exactly once and terms
each output exactly once; `let` patterns of names, pairs and `()` only; no calls
in patterns. `QSUGAR.md` §6 lists every message.

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

`bell` prepares the entangled pair of §2.6. Two operators:

```
$ 42q show gates bell
bell   = h * id ; cx
bell!  = cx! ; h! * id!
```

Read it as: Hadamard the left qubit, leave the right one alone, then a
controlled-NOT. The adjoint was not written by anyone; it is the same
definition read backwards. Written as clauses, `bell (a, b) <-> let a = h a in
cx (a, b)` compiles to exactly this term.

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
exactly the width the type demands. To read them: `qubit[2] q` declares two
qubits, `q[0]` and `q[1]`; `x` is NOT and `h` the Hadamard; `p(θ)` is the phase
gate `diag(1, e^{iθ})` of §6.2; `gphase(θ)` multiplies the whole state by
`e^{iθ}`, a global phase (§2.7); and `cx q[0], q[1]` is a CNOT with control
`q[0]` and target `q[1]`. Angles are in radians, so `0.785…` is `π/4`, an eighth
of a turn, and `1.570…` is `π/2`, a quarter.

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
