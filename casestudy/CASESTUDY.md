# Case study: a modular adder

Shor's factoring algorithm spends almost all of its gates on one classical
operation, modular arithmetic, made reversible so that it can run on qubits.
Writing that arithmetic as a circuit is the most laborious part of
implementing the algorithm, and it is the kind of program Q42 ought to be good
at: classical, reversible, and in need of checking. This case study writes
the basic building block, the **modular adder**, in Q42 and asks three
questions:

1. Can Q42 show that the circuit computes what a readable specification says?
2. Is the circuit Q42 emits as small as the same circuit built in Qiskit?
3. What does writing it in Q42 buy, and what does it cost?

The short answers: yes; it is the same circuit, gate for gate; and the gain is
real but smaller than a "verified compiler" headline would suggest. The
details follow, and the last section says plainly what the study does and does
not support.

## 1. The operation

For a fixed modulus `N` and two numbers `a, b < N`:

```
(a, b)  ↦  (a, (a + b) mod N)
```

`a` is kept, because an operation that forgot it could not be reversed: from
the sum alone you cannot tell which `a` produced it. This is the adder that
Shor's modular multiplication is assembled from.

Numbers live in **registers**, a row of qubits each holding one bit. An `n`-bit
register holds `0 … 2ⁿ − 1`, least significant bit first, so the 3-bit register
`(b0, (b1, b2))` holds `b0 + 2·b1 + 4·b2`. The circuit also needs **ancillas**:
extra qubits that start at `|0>`, are used as scratch space, and must be back at
`|0>` at the end, since a qubit left holding garbage stays entangled with the
result and spoils it.

## 2. The three files

| file | language | what it is |
|---|---|---|
| `spec.42` | 42 | the specification, written to be read |
| `modadd.42` | Q42 | the circuit |
| `spec.42` | 42 | also the encoders: which basis state stands for which input |

`baseline.py` builds the same circuit in Qiskit; it is the only file that needs
Qiskit installed.

### The specification

The specification is ordinary 42 over the natural numbers: add, then subtract
`N` if the sum reached it.

```
def keep (s, n)  <->  lt (s, n)          -- s < n: leave it
def wrap (s, n)  <->  sub (s, n)         -- s >= n: subtract n
def reduce = keep | wrap

def modadd (a, (b, n))  <->
    let (a, n) = lt (a, n) in
    let (b, n) = lt (b, n) in
    (a, reduce (add (a, b), n))
```

`lt` is a filter that passes `(a, n)` through when `a < n` and gives no result
otherwise, so `modadd` is simply undefined outside `a, b < n`. It uses `a`
twice, which copies it; it takes `N` as an input rather than wiring it in; and
it works on unbounded numbers. None of that is a circuit, and none of it needs
to be. It is the definition you would write on a whiteboard, and 42 runs it:

```
$ 42 casestudy/spec.42 modadd "(3, (4, 5))"
modadd(3, (4, 5)) =
  (3, (2, 5))
  -- 1 result
```

### The circuit

The circuit is Vedral, Barenco & Ekert's construction (1996), the standard
one. With an extra top bit `z` on `b`, so that it can hold numbers up to
`2N`, it runs five additions:

1. `b := a + b`.
2. `b := b − N`. If the sum was below `N` this goes negative, and in the
   two's-complement representation, where the top bit marks a negative number,
   `z` becomes 1.
3. Copy `z` into an ancilla `s`, then `b := b + s·N`: add `N` back if, and only
   if, step 2 went negative. Now `b` holds `(a + b) mod N`.
4. `s` must be returned to `|0>`, but it still records whether step 2 went
   negative. That fact can be recovered from the result: it went negative
   exactly when the result is at least `a`. So compute `b := b − a`, read the
   sign into `s` (which clears it), and `b := b + a` to restore the result.

Each addition is Cuccaro, Draper, Kutin & Moulton's **ripple-carry adder**
(2004): the carry is passed bit by bit along the register, like column addition
on paper, using one ancilla `c` and two three-qubit blocks, `maj` (compute the
carry) and `uma` (uncompute it and leave the sum bit). Written as clauses, in
which a name is a wire (QMANUAL §7.3):

```
def maj (c, (b, a))  <->
    let (a, b)      = cx (a, b)        in
    let (a, c)      = cx (a, c)        in
    let (c, (b, a)) = ccx (c, (b, a))  in
    (c, (b, a))
```

`cx` is the controlled NOT, flipping its second qubit when the first is 1, and
`ccx` is the Toffoli gate, flipping its third when the first two are both 1.
They are defined in the same file, as clauses. The `n`-bit adder is one
`maj` … `uma` pair around the `(n−1)`-bit adder. The modular adder itself:

```
def modadd add load cload (a, (b, (z, (c, (k, s)))))  <->
    let (c, (a, (b, z))) = add (c, (a, (b, z)))   in   -- b := a + b
    let k                = load k                 in
    let (c, (k, (b, z))) = add! (c, (k, (b, z)))  in   -- b := b - N
    let k                = load k                 in
    let (z, s)           = cx (z, s)              in   -- s := (a + b < N)
    let (s, k)           = cload (s, k)           in
    let (c, (k, (b, z))) = add (c, (k, (b, z)))   in   -- b := b + s N
    let (s, k)           = cload (s, k)           in
    let (c, (a, (b, z))) = add! (c, (a, (b, z)))  in   -- b := b - a
    let z                = x z                    in
    let (z, s)           = cx (z, s)              in   -- s := 0
    let z                = x z                    in
    let (c, (a, (b, z))) = add (c, (a, (b, z)))   in   -- b := b + a
    (a, (b, (z, (c, (k, s)))))
```

`add`, `load` and `cload` are **parameters**: programs passed in, so one
definition serves every width and every modulus. `load` writes the constant `N`
into an empty register `k` with `x` gates, and `cload` does the same under the
control of `s`. Subtraction is `add!`, the adder run backwards; no subtractor is
written anywhere. The instances are one line each:

```
def mod13 = modadd add4 load13 cload13
```

## 3. The checks

`42q check` (QMANUAL §7.7) tests four adders: `N = 3` (2 bits), `N = 5` and
`N = 7` (3 bits) and `N = 13` (4 bits). An encoder in `spec.42`, `enc3` for
`N = 3` and so on, says which basis state stands for which input, and the
command runs it backwards over every basis state to find the inputs. For each
input `a, b < N`:

- **The specification**, in 42, gives the expected answer.
- **The Q42 term** is applied to the corresponding basis state with every
  ancilla at `|0>`. The result must be exactly one basis state, with amplitude
  exactly 1, holding the expected answer and every ancilla back at `|0>`.
  Amplitudes are exact rather than floating point (QMANUAL §6.5), so this is
  equality, not closeness.
- **The emitted circuit**: `42q emit` turns the term into a list of gates on
  numbered qubits, and a simulator sharing no code with Q42 runs that list on
  the input bits. Because the circuit only permutes basis states, following one
  bit string through the gates is a complete simulation.

```
$ 42q check casestudy/modadd mod13 casestudy/spec modadd --encode enc13
mod13 against modadd, through enc13
  [ok ] the program: 169 input(s) agree, exactly
  [ok ] the circuit: 169 input(s) agree (141 gate(s) on 15 qubit(s))
  of 32768 basis states, 32512 encode no input and 87 encode one modadd does not answer; not compared
```

The other three are the same command with `mod3` and `enc3`, `mod5` and
`enc5`, `mod7` and `enc7`. The 4-bit adder takes about five seconds, most of
it running the encoder backwards over 32768 basis states.

Separately, `42q unitary` confirms that `mod3` composed with its inverse is the
identity on all `2⁹ = 512` basis states, not only the valid ones (9 seconds).

**What is not checked.** The specification has no answer for `a ≥ N` or
`b ≥ N`, or for ancillas not at `|0>`, while the circuit, being a permutation of
all basis states, still does something there. The two are compared only where
the specification speaks. That is the honest notion of correctness for this
circuit, since Shor's algorithm never feeds it anything else, but it is
narrower than the whole-matrix equality `42q equal` decides.

## 4. The counts

`42q emit --gates` lists the emitted gates; counted:

| adder | bits | qubits | Toffoli | CNOT | X |
|---|---|---|---|---|---|
| `mod3` | 2 | 9 | 20 | 51 | 6 |
| `mod5` | 3 | 12 | 30 | 71 | 6 |
| `mod7` | 3 | 12 | 30 | 73 | 8 |
| `mod13` | 4 | 15 | 40 | 93 | 8 |

These are exactly the hand counts: five adders of `2n` Toffolis and `4n + 1`
CNOTs each, plus two CNOTs and two X gates for `s`, plus the gates that load `N`.
Routing costs nothing: every `let` rearranges wires, and the emitter turns
rearrangement into relabelling, not gates.

`baseline.py` builds the same construction in Qiskit, from Qiskit's own
implementation of the Cuccaro adder (`CDKMRippleCarryAdder`), checks it on the
same inputs, and then reads Q42's emitted OpenQASM into Qiskit, so that both are
counted by the same code. Both then go through Qiskit's transpiler at its
highest optimisation level, once into Toffoli, CNOT and X, and once into
**Clifford+T**, the gate set of error-corrected machines (QMANUAL §9.4), where
the **T-count**, the number of T gates, is the usual measure of cost:

| | qubits | Toffoli | CNOT | optimised: Toffoli | CNOT | Clifford+T: T-count | CNOT | depth |
|---|---|---|---|---|---|---|---|---|
| `mod3` Q42 | 9 | 20 | 51 | 20 | 41 | 120 | 161 | 244 |
| `mod3` Qiskit | 9 | 20 | 51 | 20 | 41 | 120 | 161 | 244 |
| `mod5` Q42 | 12 | 30 | 71 | 30 | 57 | 180 | 237 | 364 |
| `mod5` Qiskit | 12 | 30 | 71 | 30 | 57 | 180 | 237 | 364 |
| `mod7` Q42 | 12 | 30 | 73 | 30 | 61 | 180 | 241 | 364 |
| `mod7` Qiskit | 12 | 30 | 73 | 30 | 61 | 180 | 241 | 364 |
| `mod13` Q42 | 15 | 40 | 93 | 40 | 77 | 240 | 317 | 484 |
| `mod13` Qiskit | 15 | 40 | 93 | 40 | 77 | 240 | 317 | 484 |

Identical on every row, which is the expected outcome: it is the same
construction, and Q42's emitter adds nothing. Two smaller observations:

- Qiskit's optimiser removes about a fifth of the CNOTs, from neighbouring
  adders whose gates cancel. Q42's emitter does no such optimisation and
  leaves it to the downstream compiler, as QMANUAL §9.4 intends. A Q42 user
  would run the same optimiser.
- Qiskit 2.6.1 was used (`qiskit_qasm3_import` 0.6 to read OpenQASM 3).

## 5. What this shows, and what it does not

**Q42 has no penalty.** A modular adder written in Q42 is the same circuit, gate
for gate, as the same construction built from Qiskit's library, before and after
optimisation. Writing it with names for wires was no harder than writing it in
Qiskit, and about as long: the modular adder is fourteen steps in Q42 and
eighteen lines in `baseline.py`, which loads `N` in loops rather than
definitions.

**The checks are real, but not unique.** Every valid input was checked three
ways, with exact amplitudes and an independent simulator, and the full `mod3`
term was checked unitary. But a Qiskit user could also test their circuit on
every valid input, by classical simulation in Python. What Q42 adds is smaller
than "verification": the specification is an executable program in a sibling
language rather than a hand-written test oracle, the inverse needs no
separate check, and equality is exact. Those are conveniences, not a different
kind of guarantee.

**The inverse is free, and so it is elsewhere.** Every subtraction here is
`add!`. In Qiskit it is `add.inverse()`, equally free. The difference
QMANUAL §9.5 describes, that `!` exists for every term with no condition, does
not show in a program that never measures anyway.

**The circuit is not derived from the specification; it is written separately
and checked against it.** `42q emit` turns Q42 definitions into circuits, but
`spec.42` breaks four of Q42's rules, and each is part of what makes it
readable:

- it works on unbounded numbers, and a circuit has a fixed number of qubits
  (QMANUAL §8.1);
- it uses `a` twice, which copies it, and copying is not unitary (§5.2);
- it is partial, with no result for `a ≥ N`, where a Q42 term must be defined
  and reversible on every input;
- it uses `|`, a union, which Q42 drops because it needs `1 + 1 = 1` (§5.1).

A specification Q42 *would* accept has to cover every fixed-width input exactly
once, out-of-range values and dirty ancillas included. That is in effect a table
of cases, and compiled as written it becomes a circuit that tests each case,
exponentially larger than the ripple-carry construction. Choosing the compact
construction is design work no compiler here does, and none in Qiskit does
either. Q42 does not close the gap between the specification and the circuit;
it makes checking one against the other cheap and exact.

**Families were written out by hand.** `add1` to `add4` are four definitions,
each wrapping the one below. A 42 program could generate them for any width,
as `qft.42` does for the quantum Fourier transform (RELATED.md §11.6); this study
did not, since four widths were enough to compare.

**The construction is not the state of the art.** Vedral–Barenco–Ekert with
Cuccaro adders is the standard textbook circuit, chosen because Qiskit has the
same pieces, so that the comparison is like for like. Cheaper adders exist.
The best known, Gidney's (2018), roughly halves the T-count of the adders
before it, and does so by
uncomputing its temporary values with a measurement and a correction chosen by
its outcome: exactly the mid-circuit measurement Q42 excludes (QMANUAL §9.2).
Q42 can express the measurement-free equivalent, but that gives up the saving.
This is the most concrete cost of Q42's design the study turned up.

**Verdict.** For the question of whether Q42 is a practical route to checked
reversible arithmetic: it works end to end, from a readable specification to an
OpenQASM circuit that matches Qiskit's gate for gate, with no penalty. It does
not beat the mainstream toolchain on any count, and the advantage it does have,
exact checking against an executable specification, is a matter of convenience. The case for Q42 as a research
language and a teaching tool is unaffected; the case for it as a better way to
build oracles is not made by this study.
