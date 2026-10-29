# 42 — User Manual

For a reader with a computer science background. No prior knowledge of
reversible computing is assumed, and no term is used before it is defined.

The manual has two parts. **Part I** is how to write 42: definitions made of
clauses, with names. **Part II** is the language those clauses compile to,
which has no names at all; it is what `42 show` prints, and what to read when
a result surprises you.

---

## Contents

**Part I — Writing 42**

1. [The five-minute version](#1-the-five-minute-version)
2. [The one rule](#2-the-one-rule-nothing-may-be-thrown-away)
3. [Values](#3-values)
4. [Clauses](#4-clauses)
5. [Running backwards](#5-running-backwards)
6. [None, one, or many answers](#6-none-one-or-many-answers)
7. [`let`](#7-let)
8. [Recursion](#8-recursion)
9. [Arithmetic](#9-arithmetic)
10. [Strings and text](#10-strings-and-text)
11. [A Turing machine](#11-a-turing-machine)

**Part II — The language underneath**

12. [Programs are pipelines, not functions](#12-programs-are-pipelines-not-functions)
13. [The seven ways to combine programs](#13-the-seven-ways-to-combine-programs)
14. [Plumbing](#14-plumbing-rearranging-shapes-when-you-cannot-name-things)
15. [How to read a program](#15-how-to-read-a-program)
16. [How to write a program](#16-how-to-write-a-program)
17. [Recursion, point-free](#17-recursion)
18. [42 interpreting itself](#18-42-interpreting-itself)
19. [Reference](#19-reference)
20. [Troubleshooting](#20-troubleshooting)

[Where to go next](#where-to-go-next) &middot; [Appendix: a program and its inverse](#appendix-a-program-and-its-inverse)

---

## 1. The five-minute version

A 42 program can be run in two directions. You write it once.

```
$ 42 tour append "([1,2], [3])"
append([1, 2], [3]) =
  [1, 2, 3]                 -- forwards: glue two lists together

$ 42 tour append "[1,2,3]" --backward
append!([1, 2, 3]) =
  ([1, 2, 3], [])          -- backwards: every way to cut a list in two
  ([1, 2], [3])
  ([1], [2, 3])
  ([], [1, 2, 3])
```

The three words after `42` are a file, a program in it, and an input:

```
42   tour      append   "([1,2], [3])"
     ^^^^      ^^^^^^   ^^^^^^^^^^^^^^
     the file  a        the value to
     to read   program  run it on
               in it
```

`tour` is `tour.42`, a file of worked examples that comes with 42 and follows
this manual. The `.42` is optional. `append` is not built in. It is defined in
that file, in two lines:

```
def append ([], ys)    <->  ys
def append (x:xs, ys)  <->  x : append (xs, ys)
```

Each line is a **clause**. The left side describes an input and names its
pieces; the right side builds the output from them. Read them as you would in
any language with pattern matching: appending `ys` to the empty list gives
`ys`; appending `ys` to a list with head `x` and tail `xs` gives `x` in front of
`xs` appended to `ys`.

Both directions ran that *same* definition. Nobody wrote the second one. Ask
42 to show the definition, and it prints the clauses, then the same clauses
turned round, which is what ran backwards:

```
$ 42 show tour append
append   ([], ys) <-> ys
append   (x : xs, ys) <-> x : append (xs, ys)
append!  ys <-> ([], ys)
append!  (x : append (xs, ys)) <-> (x : xs, ys)
append   = dist ; unitprod + (assocprod! ; id * append ; inr) ; join
append!  = join! ; unitprod! + (inr! ; id * append! ; assocprod) ; dist!
```

The last two lines are what the clauses compile to. 42 underneath has no
clauses and no names: a program is a pipeline of steps, built from
only thirteen primitives (listed in §19). You do not need that language to write 42, and
Part II of this manual is where it is explained, for when you want to read
those lines.

Two consequences of running both ways follow, and they are the whole language:

- **Running backwards can give more than one answer.** Gluing `[1,2]` to `[3]`
  loses the information about where the seam was, so running it backwards has
  to offer every possibility. A 42 program therefore returns a *set* of
  answers, which may be empty, a single answer, or many.
- **A program may never destroy information it cannot account for.** That is
  the price of admission. It is why 42 has no assignment statement and no way
  to simply drop a value on the floor.

Everything else in this manual is a consequence of those two facts.

---

## 2. The one rule: nothing may be thrown away

Suppose 42 had ordinary assignment:

```
x = 0
```

Run that backwards and you are stuck: `x` is `0`, but what was it before?
Unanswerable. The old value is gone.

So 42 has no assignment. That is not the same as having no names. What made
`x = 0` impossible to run backwards was not the name `x`. It was that the
statement *overwrote* a value and kept nothing of it. A name that is given a
value once and never changed loses nothing. 42 has names of exactly that kind.

A definition is written as one or more clauses. Each clause says which shape
of value it accepts and which value it gives back:

```
def swap (a, b)  <->  (b, a)
```

The left side is a **pattern**. It takes the value apart and names its pieces,
here `a` and `b`. The right side is a **term**. It builds the answer out of
those pieces. The arrow points both ways because the clause reads both ways.
Read from the right, it says how to get `(a, b)` back from `(b, a)`, and that
is the program run backwards. You never write the backward version.
`42 show` reads it off for you:

```
swap   (a, b) <-> (b, a)
swap!  (b, a) <-> (a, b)
```

`swap!` is the clause turned round. Turning it round needs no cleverness and no
second program, and that is the whole reason names are allowed. Every name is
bound once, on one side, and used on the other. Swap the sides, and the names
are still bound once and used once.

### What the rule forbids

That last sentence is where the one rule bites. Turning a clause round only
works if every name bound on one side is used on the other. Try to write the
most ordinary function in any other language:

```
def fst (a, b)  <->  a
```

and 42 refuses it:

```
error: line 1: in `fst (a, b) <-> a`, the variable `b` is bound and never used.
42 cannot forget a value: run backwards, nothing would say what `b` was.
Return it, or consume it in a call.
```

Turned round, `fst` would have to produce `(a, b)` from `a` alone, and nothing
says what `b` was. The mirror-image mistake is refused for the mirror-image
reason:

```
def make x  <->  (x, y)
```

```
error: line 1: in `make x <-> (x, y)`, `y` is used but never bound.  42 cannot
invent a value: run backwards, it would have to be thrown away.  Bind it in the
pattern.
```

Using a name *twice* is allowed:

```
def pair x  <->  (x, x)
```

Turned round, `pair!` takes `(x, x)` and gives back `x`, which is safe because
the two halves must agree. Given `(3, 4)` it gives no answer at all, because
`(3, 4)` is not something `pair` could have produced.

### Where information can go

So a single clause never loses anything. Information can still be lost, but
only in one place, and only visibly: in the choice *between* clauses.

```
def drop (L ())  <->  ()
def drop (R ())  <->  ()
```

Each clause is fine on its own. Together they forget which of the two labels
was there. Turn them round and both clauses match `()`:

```
drop!  ()  <->  L ()
drop!  ()  <->  R ()
```

So `drop!` on `()` gives **two** answers, `L ()` and `R ()`. That is the
general pattern. When a program forgets, running it backwards does not fail. It
offers every candidate. §6 is about this.

### Names on the surface, none underneath

The names exist only in what you write. 42 compiles every clause to a program
with no names in it at all: a pipeline of steps, each of which reshapes one
value. `swap` above compiles to the single built-in step `swapprod`, and `pair`
compiles to `copy`. Part II of this manual is about that underlying language,
which is what 42 was before it had clauses and what it still is underneath.

The core language has exactly one way to run a program backwards, and it works
on every program without exception, because there is nothing in it to un-name.
Clauses do not weaken that. Turning a clause round always gives the same
result as running its compiled program backwards. You can write with names and
still never write a backward program.

---

## 3. Values

- [3.1 The four building blocks](#31-the-four-building-blocks)
- [3.2 You already use this — it just has names](#32-you-already-use-this--it-just-has-names)
- [3.3 Why the labels are visible](#33-why-the-labels-are-visible)
- [3.4 How pairs work](#34-how-pairs-work)
- [3.5 Numbers and lists](#35-numbers-and-lists)
- [3.6 What the encoding costs](#36-what-the-encoding-costs)
- [3.7 Asking what shape a program works on](#37-asking-what-shape-a-program-works-on)

### 3.1 The four building blocks

Every value in 42 is built from four things. If you write Rust or Haskell or
C, this is a tagged union and it is the whole data model:

```rust
enum Value {
    Unit,                     //  ()          carries no information
    L(Box<Value>),            //  L x         x, labelled "left"
    R(Box<Value>),            //  R x         x, labelled "right"
    Pair(Box<Value>, Box<Value>), // (a, b)   two values side by side
}
```

Written in 42's syntax:

| Written | Meaning |
|---|---|
| `()` | the unit value — one single value that carries no information |
| `L x` | the value `x`, wearing a label that says "left" |
| `R x` | the value `x`, wearing a label that says "right" |
| `(a, b)` | a pair |

`L` and `R` are how 42 does *choice*. A value that is either "a number" or "a
string" would be `L <number>` or `R <string>`, and the label tells you which.
They are the two constructors of a two-case enum.

That is the entire data model. There are no built-in integers, no strings, no
booleans.

### 3.2 You already use this — it just has names

Coming from a language with integers and booleans as primitives, `L ()` looks
bizarre. But your familiar types are already built from exactly two ideas, and
42 simply declines to give them names:

| Idea | Meaning | C | Rust | Haskell | 42 |
|---|---|---|---|---|---|
| **AND** | this *and* that | `struct` | `struct` | `(a, b)` | `(a, b)` |
| **OR** | this *or* that | tagged `union` | `enum` | `Either a b` | `L a` / `R b` |
| **nothing** | carries no information | `void` | `()` | `()` | `()` |

Haskell's `Either` is the closest match, with two constructors literally
called `Left` and `Right`. 42's entire value model is one declaration:

```haskell
data Value = Unit | L Value | R Value | Pair Value Value
```

A boolean is a two-case choice carrying no data, which is what `enum Bool {
False, True }` says. Your language names those cases and hides the tag inside the
compiler. 42 names nothing, so you see the tag:

```
false = L ()
true  = R ()
```

That assignment is arbitrary. `L` and `R` mean nothing beyond "case one" and
"case two". Which one you call `true` is a convention you impose from
outside; the language has no opinion. (This manual uses `false = L ()`
throughout, matching `prelude.42`.)

A value in 42 is still one thing. `L ()` is one thing, with a visible label
on it. You already work with tagged values; Python attaches
a type tag to every object at runtime. 42 just makes the tag part of the
value's structure instead of hiding it in the runtime.

### 3.3 Why the labels are visible

Minimalism is only half the reason. The other half is specific to 42.

In C, `if (b) { ... } else { ... }` tests `b`, branches, and then **`b` is
gone**. Nothing downstream records which way you went. That is fine when you
only ever run forwards.

42 must be able to run backwards, which means that at every branch it has to
answer *which case was this?* The label is that answer, stored inside the
value itself. A pattern can test it:

```
def not (L x)  <->  R x
def not (R x)  <->  L x
```

The first clause applies only to values labelled `L`, the second only to
values labelled `R`. The label is right there in the value to look at, so
nothing has to remember which clause ran: the answer's label says it.

```
$ not  applied to  L ()   ->  R ()
$ pred  applied to  0   ->  {}   (nothing)
```

`pred`'s only clause has the pattern `n + 1`, which is `R n`. Zero is `L ()`,
so no clause applies and there is no answer.

The one way to lose a label is to write clauses that give the same answer for
both, as `drop` did in §2. Then the label is gone, and running backwards has
to offer both. This is where multiple answers come from, and it is why
`append!` enumerates every split (§6).

> An ordinary language discards the tag the moment it has finished branching.
> 42 cannot afford to, so the tag has to live inside the value. **That is why
> `L`/`R` are visible in 42 and invisible in C.**

### 3.4 How pairs work

A pair `(a, b)` holds two values at once. It is a struct, a tuple, a record.

There are no triples. You nest instead, and the nesting is part of the
value:

```
(1, (2, 3))        and        ((1, 2), 3)
```

are **different values**, not two spellings of the same one. A pattern for one
does not match the other:

```
$ rot3  applied to  (1, (2, 3))   ->  (3, (1, 2))
$ rot3  applied to  ((1, 2), 3)   ->  {}   (nothing)
```

`rot3`'s clause is `rot3 (a, (b, c)) <-> (c, (a, b))`, and `((1, 2), 3)` has
its pair on the wrong side. Getting the nesting wrong is one of the most common
causes of an unexpected empty result (§20).

Pairs are how a program takes two arguments. 42 has no multi-argument
application. `append` does not take two lists; it takes one pair `(xs, ys)`.

A pattern takes a pair apart and names both halves. §2 showed the catch: both
names must be used. So a pair is easy to build and cannot be reduced to one of
its halves, unless nothing is lost by it. There are two ways for that to be
true:

```
def dropunit ((), a)  <->  a          -- () carries no information
def same (x, x)       <->  x          -- the halves agree, so one is redundant
```

`dropunit` drops a `()`, which is safe because there was only ever one thing
it could have been. `same` drops a duplicate, which is safe because the
survivor tells you what the other one was; given a pair whose halves differ,
it has no answer. Everything else you can do to a pair keeps both halves:
rearranging them, or working on each.

### 3.5 Numbers and lists

The same reasoning explains why integers are not primitive either. If `3` were
an opaque machine word, `+1` would be a built-in whose inverse you would have
to supply — and it would not even *be* reversible, since incrementing the
largest representable value overflows and destroys information.

Instead a number is a stack of labels:

**Numbers.** Zero, or one-more-than a number. This is a unary counter:

```
0 = L ()
1 = R (L ())
2 = R (R (L ()))
3 = R (R (R (L ())))
```

You may write `3` and 42 will build that for you.

Which makes the successor and predecessor programs almost embarrassingly
simple:

```
def succ n        <->  n + 1      -- "put an R label on"
def pred (n + 1)  <->  n          -- "take an R label off"
```

`succ` is not arithmetic. It is *attaching a label*, and reversing it is
*removing the label*. Nobody had to write a special case for zero either:
`pred 0` yields nothing automatically, because `L ()` has no `R` to remove.
Each compiles to a single primitive, `inr` and `inr!`.

> This is the design principle behind every encoding in the language: **choose
> the representation so that the operations are reversible by construction,
> rather than reversible because you checked.**

**Lists.** Empty, or a head paired with a tail:

```
[]      = L ()
[1]     = R (1, L ())
[1,2]   = R (1, R (2, L ()))
```

You may write `[1, 2]` and 42 will build that for you.

Notice that a list is built from *both* ideas at once: a label to say
empty-or-not, and a pair to hold the head beside the tail. That combination is
all any data structure ever is.

### 3.6 What the encoding costs

Three real prices, worth knowing up front:

- **Unary numbers are absurdly slow.** `1000` is a thousand nested labels, and
  arithmetic walks them one at a time. This is inherent to the encoding.
- **Everything is verbose.** `[1, 2]` is really `R (1, R (2, L ()))`. The
  display sugar hides it; `--raw` shows you the truth.
- **Encodings collide.** `0`, `[]` and `L ()` are the same value: both numbers
  and lists use `L ()` for their base case, so the value alone cannot say which
  was meant. This is real, not a display bug.

The first is intrinsic and will not go away.

The second and third are helped by the *shapes* of section 3.7. 42 works out
what shape each program expects and produces, and prints values against it, so
an empty list shows as `[]` and not as `0`:

```
$ 42 prelude append "[1,2]" --backward
append!([1, 2]) =
  ([1, 2], [])
  ([1], [2])
  ([], [1, 2])
```

It is not a complete cure. Under `--raw` there is no shape to consult, and where
a program's shape is vaguer than what you had in mind (`succ` works on
anything with a label on it, not only numbers), 42 falls back to guessing, and
guesses "number".

---

### 3.7 Asking what shape a program works on

A **shape** is a description of a set of values: "a pair", "a label with a
number inside", "a list of anything". Every 42 program works on values of one
shape and produces values of another, and 42 can work out which without being
told. Ask it:

```
$ 42 type prelude swap
swap  : a x b <-> b x a
```

Read that as "in, out". The `<->` separates the shape `swap` accepts from the
shape it produces. It is a double-headed arrow because 42 programs run both
ways, so which side is "in" depends on which direction you ran it.

The notation has five parts:

| written | means |
|---|---|
| `a`, `b`, `c` | *any* shape at all — a placeholder |
| `a x b` | a **pair**: an `a` beside a `b` |
| `a + b` | a **label**: either `L` of an `a`, or `R` of a `b` |
| `1` | just `()`, carrying no information |
| `0` | nothing at all — a shape with no values in it |

So `swap : a x b <-> b x a` says: *hand me a pair of anything and anything, and
I hand back a pair of those two, swapped.* Which is exactly what `swapprod`
does, now stated rather than demonstrated.

Some shapes refer to themselves. Section 3.5 described a list in English:
*empty, or a head paired with a tail.* That sentence mentions lists twice, so a
list is defined in terms of itself. Writing it down needs a way to say "and here
the shape starts over", which is what `mu` is for:

```
mu X. 1 + (a x X)
      |    |   |
      |    |   `- ...and then another one of ME: the rest of the list
      |    `- ...or a head, which is one a, beside...
      `- either nothing at all, which is the empty list...
```

`mu X.` means "call this shape `X` while I describe it", and the `X` inside is
where the shape refers back to itself. Compare it to the English and it is the
same sentence. A number, *zero or one-more-than a number*, is `mu X. 1 + X`.

If you know the lambda calculus, `mu X.` binds `X` the way `λx.` binds `x`: the
name is local, it means nothing outside the shape it heads, and renaming it
changes nothing — which is why the report below can come back with `X` on one
side and `Y` on the other and mean the same shape.

The resemblance stops there. `λ` builds a function you can apply; `mu` does not.
`mu X. 1 + X` is not a function from shapes to shapes, it is the shape that *is*
`1 + X` once you put itself back in for the `X` — a fixed point rather than an
abstraction.

Note also which half of the language this is. `mu` binds a *shape*, never a
value. Names for values are the clause variables of §4, and they belong to a
definition; a shape's names belong to the shape.

`mu X. 1 + X` is correct and unreadable. A list of numbers is a list whose
heads are themselves `mu`, and comes out as `mu X. 1 + (mu Y. 1 + Y) x X`, so a
file may give its shapes names:

```
type nat    = mu X. 1 + X
type list a = mu X. 1 + (a x X)
```

after which reports use the names:

```
$ 42 type tour rev
rev  : list a <-> list a          -- was: mu X. 1 + a x X <-> mu Y. 1 + a x Y
```

`list a` takes a parameter, so `list nat` is a list of numbers and `list b` a
list of whatever `b` turns out to be.

Two things to know. Inside a shape, `x` means "pair", so it cannot also be used
as a name: write `a x b`, never `x x b`.

And a `type` line changes nothing but the printing. It does not define a new
kind of value; 42 has no such thing, and every value is still built from the
same four pieces of section 3.1. It is a nickname for a shape 42 had already
worked out on its own. Delete every `type` line from a file and the same
programs are accepted and rejected. The reports just get harder to read.

---

## 4. Clauses

- [4.1 What a clause is](#41-what-a-clause-is)
- [4.2 Every name used, every name bound](#42-every-name-used-every-name-bound)
- [4.3 Calling other programs](#43-calling-other-programs)
- [4.4 Names and what they may not be](#44-names-and-what-they-may-not-be)

### 4.1 What a clause is

A clause is `def`, a name, a pattern, `<->`, and a term:

```
def single x  <->  [x]
```

A definition is one or more clauses with the same name, written together. The
pattern and the term are written in **the same notation**. Whatever builds a
value in a term takes it apart in a pattern:

| Written | In a term it builds | In a pattern it matches |
|---|---|---|
| `x` | the value named `x` | anything, and names it `x` |
| `()`, `(t, u)`, `L t`, `R t` | the four building blocks of §3.1 | exactly that shape |
| `0`, `3`, `'a'`, `"hi"`, `[]`, `[t, u]` | that value | exactly that value |
| `t : u` | a list cell, `R (t, u)` | a non-empty list |
| `t + 1` | the number after `t`, `R t` | any number but zero |
| `f t` | run the program `f` on `t` | a value `f` could produce from `t` (§5.2) |

`[x]` is `x : []`, which is `R (x, L ())`, so `single` puts a label and an
empty list round its input. Run backwards, it accepts exactly the one-element
lists and returns the element:

```
$ single(7)  =  [7]
$ single!([7])  =  7
$ single!([7, 8])  =  {}
```

### 4.2 Every name used, every name bound

The rule of §2 in full. Count how often each name appears in the pattern and in
the term:

| In the pattern | In the term | What happens |
|---|---|---|
| once | once | the ordinary case: the value moves to its new place |
| once | twice or more | the value is copied |
| twice or more | once | **an equality test**: the clause matches only when the places agree |
| at least once | never | refused: the value would be forgotten |
| never | at least once | refused: the value would have to be invented |

The rule is symmetric, because turning a clause round swaps pattern and term.
A name used twice in a term becomes a name used twice in a pattern, so copying
and testing for equality are the same thing read in opposite directions.

A test is therefore a name used twice. `palin` in `tour.42` keeps a list only
if it reads the same backwards:

```
def palin l  <->  let (m, m) = (l, rev l) in m
```

`l` is used twice, so it is copied; one copy is reversed (`let` is §7); the
pattern `(m, m)` matches only if the two agree.

```
$ palin([1, 2, 1])  =  [1, 2, 1]
$ palin([1, 2, 3])  =  {}
```

### 4.3 Calling other programs

`f t` in a term runs the program `f` on the value `t`. The program can be any
definition, including the one being defined, which is how recursion is written
(§8). It can also be a definition run backwards, written `f!`:

```
def initlast2 zs  <->  let (xs, [x]) = append! zs in (xs, x)
```

Where a program is more than one name, put it in brackets, as in
`(swap ; swap) x`; Part II explains what can go inside.

There is no way to call a program on *some* of the values in hand and quietly
drop its answer. A call's answer is a value like any other, and the rule of
§4.2 applies to it.

### 4.4 Names and what they may not be

A name in a pattern may not be the name of a definition. Inside a clause, `f t`
and a variable are told apart only by their names, so `rev` in a pattern
would be ambiguous: a value named `rev`, or a call to `rev` run backwards
(§5.2)? 42 refuses rather than guesses:

```
error: line 2: the pattern variable `rev` has the name of a definition.  In a
pattern, `rev t` runs `rev` backwards, so a variable may not reuse the name.
Rename the variable.
```

The words `L`, `R`, `let`, `in` and `def` are reserved.

---

## 5. Running backwards

- [5.1 Turning clauses round](#51-turning-clauses-round)
- [5.2 A call in a pattern](#52-a-call-in-a-pattern)
- [5.3 Checking the law](#53-checking-the-law)

### 5.1 Turning clauses round

To run a definition backwards, 42 turns every clause round: pattern and term
change places. `42 show` prints the result. For `single`:

```
$ 42 show tour single
single   x <-> [x]
single!  [x] <-> x
```

The second line is `single!`, the program that takes a one-element list apart.
Nobody wrote it. For `append`, §1 showed the turned-round clauses:

```
append!  ys <-> ([], ys)
append!  (x : append (xs, ys)) <-> (x : xs, ys)
```

The first says: any list `ys` can be split as `([], ys)`. The second says: a
non-empty list `x : rest` can be split as `(x : xs, ys)` wherever `rest` can be
split as `(xs, ys)`. Both clauses match every non-empty list, so both
contribute, and that is why `append!` gives every split. It can be given a
name of its own:

```
def split = append!
```

`split` is not a second implementation that must be kept in step with
`append`. It *is* `append`, read the other way.

### 5.2 A call in a pattern

Turning `append` round put a call, `append (xs, ys)`, into a pattern. A call in
a pattern means: a value that this program could have produced, and the input
it would have produced it from. Matching it runs the program backwards.

You can write such patterns yourself:

```
def initlast (append (xs, [x]))  <->  (xs, x)
```

`initlast` matches any list that `append` could have made from some `xs` and a
one-element list. Running `append` backwards offers every split; only the one
whose second half has one element matches `[x]`:

```
$ 42 tour initlast "[1,2,3]"
initlast([1, 2, 3]) =
  ([1, 2], 3)
  -- 1 result

$ 42 tour initlast "([1, 2], 3)" --backward
initlast!([1, 2], 3) =
  [1, 2, 3]
  -- 1 result
```

`initlast2` in §4.3, written with `let`, compiles to exactly the same program.

### 5.3 Checking the law

The defining law of 42 is that running a program backwards on one of its
answers gets back to where it started:

> if `y` is an answer of `f` on `x`, then `x` is an answer of `f!` on `y`.

`42 law` runs a program forwards, runs every answer backwards, and checks:

```
$ 42 law tour rev "[1,2,3]"
rev([1, 2, 3]) has 1 result(s)
  [ok ] [3, 2, 1]: inv has 1 preimage(s), input in it
law holds
```

It always holds. That is not because each program was checked, but because
running backwards is built so that it must.

---

## 6. None, one, or many answers

- [6.1 No answer](#61-no-answer)
- [6.2 Many answers](#62-many-answers)
- [6.3 A definition is the union of its clauses](#63-a-definition-is-the-union-of-its-clauses)
- [6.4 Overlapping clauses warn](#64-overlapping-clauses-warn)

### 6.1 No answer

A 42 program returns a set. No answers, written `{}`, is normal and is not an
error. It means "this input is not something I apply to":

```
$ 42 tour pred 0
pred(0) =
  {}   (empty: no result)
```

No clause of `pred` matches `0`, so there is nothing to return.

A **shape** mismatch is different, and the two are worth keeping apart. As a
matter of meaning, a program given a value of the wrong shape also has no
answers. But you almost never mean that, so the command line checks the shape
first (§3.7) and refuses:

```
$ 42 prelude swap 5
error: the argument does not fit the domain of `swap`
  swap expects : a x b
  you gave     : 5
```

`pred 0` above is not refused, because `0` is a perfectly good input to `pred`
that happens to have no answer. Emptiness because no clause applies is normal;
emptiness because the shapes never lined up was almost certainly a typo. Add
`--untyped` to see the underlying answer anyway:

```
$ 42 prelude swap 5 --untyped
swap(5) =
  {}   (empty: no result)
```

### 6.2 Many answers

Many answers happen when information was lost going the other way:

```
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

Adding throws away how the total was split up, so the reverse offers every
split.

Composing can bring the number of answers back down. `add` reversed has many
answers, but

```
def double n  <->  add (n, n)
```

reversed has at most one, because `n` is used twice: turned round, the two
halves of the pair `add!` produces must agree, and only one split of an even
number has equal halves.

```
$ double!(6)  =  3
$ double!(7)  =  {}
```

### 6.3 A definition is the union of its clauses

Where do several answers come from in a definition made of clauses? From
several clauses applying at once. A definition means **every answer of every
clause that matches**. It is not "the first clause that matches", as it would
be in Haskell or in a `match` statement.

Running forwards, the clauses of most definitions cover different shapes, as
`[]` and `x : xs` do, so at most one applies. Running backwards, the turned
round clauses of `append` both match any non-empty list, and both contribute.
That is §5.1's `split`, and §2's `drop!`.

The union can also be written explicitly. `|` joins two programs, and the
result has every answer of either:

```
def near = pred | succ
```

```
$ 42 tour near 5
near(5) =
  4
  6
  -- 2 results
```

### 6.4 Overlapping clauses warn

Because a definition is a union, two clauses whose patterns match the same
input both apply to it. That is sometimes meant and often a mistake carried
over from first-match languages, so 42 warns:

```
warning: line 2: clauses 1 and 2 of 'f' both match `0` (which is also `[]` and
`false`):
    def f [] <-> []
    def f xs <-> xs
42 takes the union of matching clauses, not the first match, so both give
answers there.  If that is meant, give each its own name and write the union:
`def f = ... | ...`.
```

When the overlap is meant, write it as `near` is written: each case under its
own name, joined with `|`. Then there is nothing to warn about, and the source
says that both answers are wanted.

Only patterns are compared, never terms: two clauses that can produce the same
answer are how a backward run gets several answers, and that is not a mistake.
A pattern containing a call counts as matching anything, so the warning can
appear where the call would in fact rule the overlap out. Turned-round
definitions often have overlapping patterns, since their patterns were terms.

---

## 7. `let`

A term may be `let q = t in e`. It builds `t` from some of the names in hand,
matches the answer against the pattern `q`, and continues with the names `q`
binds plus the ones not yet used:

```
def palin l  <->  let (m, m) = (l, rev l) in m
```

A `let` gives an intermediate answer a name. Without it, everything a clause
computes would have to be one term. `let`s chain:

```
let q1 = t1 in let q2 = t2 in e
```

and the rule of §4.2 applies across the whole chain: every name is used once
after it is bound, counting copies.

A name may be bound again once its value has been used. `mul` in `arith.42`
hands its multiplier back (§9.3), so a value can be threaded through two
multiplications under one name:

```
def twoproducts (n, (a, b))  <->  let (n, p) = mul (a, n) in
                                  let (n, q) = mul (b, n) in
                                  (n, (p, q))
```

Each `let` consumes `n` and binds a new `n` in its place, so nothing is lost and
the clause turns round as usual. What is refused is binding a name whose value
is still in hand, since that would make the earlier value unreachable:

```
error: line 1: in `g (x, y) <-> let x = g y in x`, `x` is bound again while its
value is still in hand.  A name may be reused once its value has been consumed;
here that would lose the earlier value, so use a new name.
```

A `let` is a small clause inside a clause, so it turns round the same way:
`42 show` prints the chain reversed, each `let`'s two sides swapped.

```
$ 42 show tour palin
palin   l <-> let (m, m) = (l, rev l) in m
palin!  m <-> let (l, rev l) = (m, m) in l
```

Turned round, the pattern `(l, rev l)` contains a call: it matches a pair whose
second half is the first half reversed, and names the first half `l`.

---

## 8. Recursion

- [8.1 One clause per shape](#81-one-clause-per-shape)
- [8.2 Running a recursion backwards](#82-running-a-recursion-backwards)

### 8.1 One clause per shape

A definition may call itself. Recursive data in 42 is always "a base case, or
something bigger", a label on the outside, so a recursive definition has a
clause for each label:

```
def append ([], ys)    <->  ys
def append (x:xs, ys)  <->  x : append (xs, ys)

def rev []      <->  []
def rev (x:xs)  <->  append (rev xs, [x])
```

The recursive call is on a smaller value, the tail, so forwards it reaches the
base case and stops. Following one input through `append`:

```
append ([1, 2], [3])
  = 1 : append ([2], [3])          -- second clause
  = 1 : 2 : append ([], [3])       -- second clause
  = 1 : 2 : [3]                    -- first clause
  = [1, 2, 3]
```

Numbers recurse the same way, on `0` and `n + 1`:

```
def add (0, n)      <->  n
def add (m + 1, n)  <->  add (m, n) + 1
```

### 8.2 Running a recursion backwards

Backwards, the turned-round clauses recurse instead. `append!` on `[1, 2, 3]`
offers `([], [1, 2, 3])` from the first clause, and from the second, `1` in
front of every split of `[2, 3]`, and so on down. Each step is on a shorter
list, so it stops too.

That is not automatic. A backward run stops only if every recursive call it
makes is on something smaller, and that depends on the order in which a clause
does its work. In `rev`'s second clause, `append (rev xs, [x])`, the backward
run first splits the list with `append!`, then needs `rev!` on the first half
and a one-element check on the second. Done in that order, one of the splits
is `(whole list, [])`, and `rev!` would be asked to reverse a list as long as
the one it started with, forever. Done the other way round, the check rejects
that split first.

42 chooses the order for you: in every pair it builds, the half whose checks
are cheapest is taken apart first. You do not write anything for this. It is
mentioned because it explains why a backward run can occasionally fail to stop
where the forward run does: when no order puts a check before the recursion,
`42` reports that the call depth was exhausted rather than running forever.

```
$ 42 tour rev "[3,2,1]" --backward
rev!([3, 2, 1]) =
  [1, 2, 3]
  -- 1 result
```

---

## 9. Arithmetic

Everything here is in `arith.42`, and every example below is runnable.

- [9.1 The governing question](#91-the-governing-question)
- [9.2 Addition](#92-addition)
- [9.3 Multiplication, and what it must carry](#93-multiplication-and-what-it-must-carry)
- [9.4 Division is multiplication backwards](#94-division-is-multiplication-backwards)
- [9.5 Subtraction](#95-subtraction)
- [9.6 Division with remainder](#96-division-with-remainder)
- [9.7 A filter must be stated at both ends](#97-a-filter-must-be-stated-at-both-ends)
- [9.8 Exact rationals](#98-exact-rationals)
- [9.9 Limits](#99-limits)

### 9.1 The governing question

You cannot write an operation that throws its inputs away. But you can nearly
always write the same operation in a form that keeps just enough to reconstruct
them, and that form is usually only one component bigger.

So the question is never "can 42 compute this?" It is:

> **What is the smallest thing I have to carry along?**

Answer that, and the operation follows. Better still, the *inverse* operation
comes free, which is why `arith.42` contains algorithms for addition,
multiplication and comparison, and none at all for subtraction or division.

### 9.2 Addition

One clause for zero, one for every other number:

```
def add (0, n)      <->  n
def add (m + 1, n)  <->  add (m, n) + 1
```

```
$ add(2, 3)  =  5
$ add!(5)    =  (0, 5)  (1, 4)  (2, 3)  (3, 2)  (4, 1)  (5, 0)
```

`add` is allowed to discard how the total was split, because that information
is still recoverable *as a set*: running backwards enumerates every pair.
Nothing is truly lost, it is merely spread across six answers. In clause terms:
the two clauses can produce the same number, so turned round, both apply.

### 9.3 Multiplication, and what it must carry

Here the naive version fails. `(m, n) ↦ m × n` has base case `0 × n = 0`,
which would be the clause `mul (0, n) <-> 0`, and §4.2 refuses it: `n` is bound
and never used. Unlike `add`, you cannot even recover it as a set: `mul` would
have to work for every `n`, so the base case has nowhere to put it.

The fix is to carry the multiplier along:

```
mul : (m, n)  ↦  (n, m × n)
```

```
def mul (0, n)      <->  (n, 0)
def mul (m + 1, n)  <->  let (k, p) = mul (m, n) in (k, add (k, p))
```

```
$ mul(4, 5)  =  (5, 20)
$ mul(0, 7)  =  (7, 0)
```

One extra component in the output, and the whole thing works. In the step,
the recursive call hands the multiplier back as `k`, and `k` is used twice: once
to add to the product, once to hand back. Using a name twice is a copy (§4.2).

### 9.4 Division is multiplication backwards

Because `mul` keeps its multiplier, it is injective, and therefore:

```
def divexact = mul!
```

That is the entire implementation of exact division.

```
$ divexact(3, 12)  =  (4, 3)      -- 12 / 3 = 4
$ divexact(5, 20)  =  (4, 5)
$ divexact(3, 7)   =  {}          -- 3 does not divide 7
```

The "does not divide" case needs no handling either. There is no `m` with
`m × 3 = 7`, so the set of answers is empty, which is exactly the right
answer.

### 9.5 Subtraction

Same trick. Make addition keep its second operand:

```
def addk (c, b)  <->  (add (c, b), b)      -- (c, b) -> (c + b, b)
def sub = addk!                            -- (a, b) -> (a - b, b)
```

```
$ addk(2, 3)  =  (5, 3)
$ sub(5, 3)   =  (2, 3)
$ sub(3, 5)   =  {}       -- no natural c has c + 5 = 3
```

Subtraction on naturals is partial, and that partiality arrives for free.

### 9.6 Division with remainder

The pattern generalises: **write whichever direction is easy, then invert it.**
Reassembling a dividend from a quotient, a remainder and a divisor is easy;
dividing is not. So write the easy one.

```
undivmod : ((q, r), b)  ↦  (q × b + r,  b)        provided r < b
```

The proviso matters. Without `r < b`, both `(q=0, r=5)` and `(q=2, r=1)`
rebuild 5 from divisor 2, and the inverse would be ambiguous. So we need a
comparison, written as a filter: a definition that hands back its input
unchanged, or gives no answer.

```
def lt (0, n + 1)      <->  (0, n + 1)
def lt (m + 1, n + 1)  <->  let (a, b) = lt (m, n) in (a + 1, b + 1)
```

```
$ lt(2, 5)  =  (2, 5)      -- passes through unchanged
$ lt(5, 2)  =  {}          -- rejected
```

Both clauses take the pair apart and build it again. The first applies only
when the first number is `0` and the second is not; the second counts both
down together. No clause applies when the second number reaches `0` first, so
those pairs get no answer.

Now the easy direction, and its inverse:

```
def undivmod ((q, r), b)  <->  let (r1, b1)  = lt (r, b)   in
                               let (b2, qb)  = mul (q, b1) in
                               (add (qb, r1), nonzero b2)

def divmod = undivmod!
```

```
$ divmod(17, 5)  =  ((3, 2), 5)      -- 17 = 3*5 + 2
$ divmod(12, 4)  =  ((3, 0), 4)
$ divmod(3, 5)   =  ((0, 3), 5)
```

### 9.7 A filter must be stated at both ends

That `nonzero` in the last line of `undivmod` looks like dead code:

```
def nonzero (n + 1)  <->  n + 1        -- keeps n unchanged if n > 0, else nothing
```

`lt` has already forced `b > 0`, so going forwards this check can never reject
anything. **It is there for the backward direction, and it is essential.**

Here is the reasoning, and it is the one piece that does not carry over from
ordinary programming:

> Turning a clause round reverses its `let` chain. A filter written early,
> pruning as you go forwards, ends up running last going backwards, long after
> the expensive work it was meant to prevent.

`42 show` prints `undivmod` turned round, and the order is plain to see:

```
undivmod!  (add (qb, r1), nonzero b2) <-> let mul (q, b1) = (b2, qb) in let lt (r, b) = (r1, b1) in ((q, r), b)
```

In `undivmod`, `lt` comes first and guarantees `b > 0`. Turned round, it comes
last. By then `divmod(7, 0)` has already asked `mul!` to divide by zero, and
since `mul(m, 0) = (0, 0)` for *every* `m`, that search never terminates.
Repeating the constraint in the result puts it *first* when turned round:

```
$ divmod(7, 0)  =  {}        -- immediately, with the guard
                             -- without it: runs forever
```

> **Rule of thumb: a constraint you rely on in both directions must be stated
> at both ends.** Forwards, one of the two statements is redundant. That
> redundancy is the price of a definition that prunes in both directions. It
> is not dead code; deleting it changes termination.

42 orders the work inside a single term for you (§8.2). It does not reorder a
`let` chain, because the chain is the order you wrote down.

### 9.8 Exact rationals

Everything here is in `rational.42`. A rational is a pair `(numerator,
denominator)`, and every operation is exact. Nothing is ever rounded, because
rounding is discarding and this language cannot discard.

The same carrying rule as before gives the inverses free:

```
qadd : (a, b) ↦ (b, a + b)          so   qsub = qadd!
qmul : (a, b) ↦ (b, a × b)          so   qdiv = qmul!
```

#### Multiplication is one line

```
def transpose ((a, b), (c, d))  <->  ((a, c), (b, d))

def qmul = transpose ; (mul * mul) ; transpose
```

`transpose` swaps the two inner components of a pair of pairs; turned round,
its clause is the same clause with the names changed, so it is its own
inverse. `qmul` is written without clauses on purpose, as a pipeline of three
steps (`;` runs one program after another, and `f * g` runs `f` on the left of
a pair and `g` on the right; §13 has both). Watch it work:

```
((p, q), (r, s))     transpose     ->  ((p, r), (q, s))    numerators together
((p, r), (q, s))     mul * mul     ->  ((r, pr), (s, qs))  mul hands back operand 2
((r, pr), (s, qs))   transpose     ->  ((r, s), (pr, qs))  kept operand, then product
```

```
$ qmul((1,2), (3,4))  =  ((3, 4), (3, 8))       -- 1/2 × 3/4 = 3/8
$ qdiv((3,4), (3,8))  =  ((1, 2), (3, 4))       -- and back
```

Addition is the same idea over `(ps + qr, qs)`, but the operands are used
unevenly: `s` three times, `q` twice, `p` and `r` once each. Since `mul` hands
back its second operand, `s` threads from one product into the next and only
`q` is used twice:

```
def qadd ((p, q), (r, s))  <->  let (s1, ps) = mul (p, s)  in
                                let (r1, qr) = mul (q, r)  in
                                let (s2, qs) = mul (q, s1) in
                                ((r1, s2), (add (ps, qr), qs))
```

```
$ qadd((1,2), (1,3))  =  ((1, 3), (5, 6))       -- 1/2 + 1/3 = 5/6
$ qsub((1,3), (5,6))  =  ((1, 2), (1, 3))
```

#### There is no `reduce`, and there cannot be one

This is the part worth understanding, because it is the language dictating the
design rather than a choice.

Putting a fraction in lowest terms means dividing by the gcd. Computing a gcd
means Euclid's algorithm, and **every step of Euclid throws away a quotient
and keeps only a remainder.** 42 cannot throw anything away. So a gcd program
written here is forced to hand back the quotients it generated, and that
sequence is the continued-fraction expansion, from which the original fraction
can be rebuilt.

Reduction cannot lose the thing it exists to lose, so `rational.42` keeps
fractions unreduced and compares them with cross-multiplication instead:

```
def qeq x  <->  let (y, (n, n)) = cross x in withps! (y, n)
```

```
$ qeq((1,2), (2,4))  =  ((1, 2), (2, 4))     -- equal, passed through
$ qeq((1,2), (3,4))  =  {}                   -- not equal
```

Note the shape of that definition, because the pattern is reusable: `qeq` is a
filter, so it must return its input untouched, yet it needs two cross products
to do its job. `cross` is what computes them, handing back the two
fractions with `p×s` and `q×r` attached:

```
$ cross((1,2),(3,4))  =  (((1, 2), (3, 4)), (4, 6))
```

Then the pattern `(n, n)` demands the two agree, and one of them is
**recomputed backwards to cancel it**: `withps` pairs a value with `p×s`
injectively, so `withps!` removes a `p×s`. Computing something, using it, and
then un-computing it is how you borrow a scratch value in a language that will
not let you forget one.

For scaling you supply the factor yourself, and keeping it makes the operation
invertible:

```
$ reduceby((6,8), 2)  =  ((3, 4), 2)
$ scaleby((3,4), 2)   =  ((6, 8), 2)
$ reduceby((6,8), 4)  =  {}              -- 4 does not divide 6
```

#### The price of unreduced fractions

`qsub` is exact on **representations**, not on values. `qadd` produces
denominator `q×s`, so its inverse recognises that denominator and no other:

```
$ qadd((1,2), (1,2))  =  ((1, 2), (4, 4))
$ qsub((1,2), (4,4))  =  ((1, 2), (1, 2))     -- fine
$ qsub((1,2), (1,1))  =  {}                   -- nothing, even though 4/4 = 1/1
```

There is no `p/q` with `q×2 = 1`, so the answer really is empty. If you want
to subtract at the level of rational *values*, scale to a compatible
denominator first. This is the honest cost of a representation the language
forced on us, and it is worth knowing before you rely on `qsub`.

### 9.9 Limits

- **`mul!(0, 0)` does not terminate**, and correctly so: every number divides
  zero, so there are infinitely many answers. `mul` is injective for every
  multiplier except `0`. Guard with `nonzero` before running it backwards.
- **Unary numbers are slow** (§3.6). `divmod(40, 6)` takes a noticeable
  fraction of a second; `divmod(400, 6)` is not worth attempting. For
  rationals this bites sooner, since cross-multiplication builds products:
  `qeq((19,30), (95,150))` has to construct 2850 as a stack of 2850 labels,
  and does not finish in reasonable time.
- **`(m, n) ↦ m × n` remains unwritable** in its discarding form. Carrying the
  multiplier is not a workaround you may skip; it is the only version that
  exists.
- **Rationals here are non-negative.** `qsub` is partial in the same way
  natural subtraction is. Signed rationals would need a sign bit and a
  canonical treatment of zero.

---

## 10. Strings and text

Everything here is in `strings.42`.

- [10.1 There is no string type](#101-there-is-no-string-type)
- [10.2 Writing text](#102-writing-text)
- [10.3 Every list program already works](#103-every-list-program-already-works)
- [10.4 Case conversion is one bit](#104-case-conversion-is-one-bit)
- [10.5 How to write if-then-else](#105-how-to-write-if-then-else)

### 10.1 There is no string type

Nothing was added to the language to support text. A string is a list, and
lists already existed:

```
bit    = 1 + 1                    L () = 0,  R () = 1
byte   = bit x (bit x ( … ))      eight of them, MSB first, nested right
string = mu X. 1 + (byte x X)     exactly the list type from §3.5
```

So a character is a byte, and a byte is eight booleans:

```
'a'  =  (0, (1, (1, (0, (0, (0, (0, 1)))))))      -- 97 = 0b01100001
```

Why binary and not unary? Numbers in 42 are unary (§3.5), so consistency would
have made `'a'` a stack of 97 labels. Binary is faster, and it also keeps the
encodings distinguishable. A byte is a nest of pairs; a number is a chain of
labels. Nothing can be read as both. So unlike `0`/`[]`
(§3.6), text collides with nothing:

```
$ [72, 105]   prints as   [72, 105]        -- still a list of numbers
$ "Hi"        prints as   "Hi"
```

That was the deciding factor in the encoding. An ambiguous printer is a
constant low-level tax on reading output, and here it was avoidable.

### 10.2 Writing text

| Written | Is |
|---|---|
| `'a'` | one byte |
| `"hello"` | a list of bytes |
| `"héllo"` | its UTF-8 bytes — six of them |
| `"a\nb"` | escapes: `\n` `\t` `\r` `\\` `\0` `\"` `\'` `\xNN` |

A character literal must be exactly one byte, so `'é'` is rejected; write it
as a string. And `""` is `L ()`, which is also `0` and `[]` (§3.6).

### 10.3 Every list program already works

This is the part worth pausing on. Because a string *is* a list, the list
programs of §8 operate on text with no modification whatsoever:

```
$ concat("foo", "bar")   =  "foobar"
$ reverse("stressed")    =  "desserts"
$ palin("racecar")       =  "racecar"
$ palin("apple")         =  {}
```

and `split` is not an implementation at all. It is `concat` read backwards:

```
def concat = append
def split  = append!
```

```
$ split("abc")  =  ("a", "bc")  ("ab", "c")  ("abc", [])  ([], "abc")
```

Every way to cut a string in two, and nobody wrote a string-splitting routine.

### 10.4 Case conversion is one bit

In ASCII, upper and lower case differ in one bit, the one worth 32. So changing
case is not arithmetic; it is reaching into the byte and flipping a single
boolean:

```
byte = (b7, (b6, (b5, (b4, (b3, (b2, (b1, b0)))))))
        keep  keep  flip  ←------ leave alone ------→

def not (L x)  <->  R x
def not (R x)  <->  L x

def flipcase (b7, (b6, (b5, rest)))  <->  (b7, (b6, (not b5, rest)))
```

The pattern names the bits it needs and lumps the other five together as
`rest`. `not` compiles to the single primitive `swapsum`, so `flipcase` is its
own inverse: running it backwards is running it forwards.

### 10.5 How to write if-then-else

Flipping bit 5 of *every* byte would be wrong: it turns a space into a NUL and
a comma into a form feed. We want to flip it only for letters, which needs a
conditional.

A conditional in 42 is **clauses whose patterns cannot both match**. ASCII
letters all lie in 64..127, that is `b7 = 0` and `b6 = 1`, so one clause takes
exactly those bytes and two more take the rest:

```
def swapbyte (L (), (R (), rest))  <->  flipcase (L (), (R (), rest))   -- 64..127
def swapbyte (R (), rest)          <->  (R (), rest)                    -- 128..255
def swapbyte (L (), (L (), rest))  <->  (L (), (L (), rest))            -- 0..63

def swapcase []        <->  []
def swapcase (c : cs)  <->  swapbyte c : swapcase cs
```

```
$ swapcase("Hello, World!")   =  "hELLO, wORLD!"
$ swapcase("abc 123 XYZ")     =  "ABC 123 xyz"
```

Punctuation, spaces and digits now pass through untouched, and `swapcase` is
still its own inverse.

Two things are worth knowing about writing a conditional this way:

- **Overlap is checked.** A definition is the union of its clauses (§6.3), so
  if two of these patterns could match the same byte, that byte would get two
  answers. 42 compares the patterns and warns when they overlap (§6.4). Here
  they do not, so it says nothing.
- **Gaps are not.** Leave out a case and the bytes it covered get no answer at
  all. That is a legitimate thing to want, a filter is exactly that, so 42
  does not warn about it. These three clauses do cover all 256 bytes, and a
  test checks it.

The residual inaccuracy, stated precisely rather than waved at: the sixteen
bytes ``@[\]^_`{|}~`` and DEL share the letters' top two bits, so they still get
mapped onto each other. Excluding them needs a range check on the low five
bits, which is real work for very little return. (There is a test asserting this
caveat is exactly true, so it cannot quietly become false.)

---

## 11. A Turing machine

Every program so far does one thing to a value and stops. This section builds a
machine that *runs*: it keeps changing a value until it is finished, and only
then gives an answer. That is the last thing a language has to be able to do,
and in 42 it needs one construct beyond clauses: `^`, "repeat any number of
times".

The file is `tm.42`. The machine adds one to a binary number.

- [11.1 The shape every machine takes](#111-the-shape-every-machine-takes)
- [11.2 The tape is a list with a hole in it](#112-the-tape-is-a-list-with-a-hole-in-it)
- [11.3 The state is a label, not a component](#113-the-state-is-a-label-not-a-component)
- [11.4 The table, one clause per row](#114-the-table-one-clause-per-row)
- [11.5 Running it](#115-running-it)
- [11.6 Running the machine backwards](#116-running-the-machine-backwards)
- [11.7 What this does and does not show](#117-what-this-does-and-does-not-show)

### 11.1 The shape every machine takes

A Turing machine is a tape, a head, a control state, and a table saying what to
do next. In 42 the whole of it is three programs run one after another:

```
init ; step^ ; final
```

- `init` turns the input into a starting **configuration**: tape, head and
  state, all in one value.
- `step` is **one** move of the machine: `configuration <-> configuration`.
- `step^` repeats `step` any number of times, so it relates the start to
  *every* configuration the machine can reach.
- `final` is a filter that lets through only configurations that have halted,
  and reads the answer off the tape.

`;` runs one program after another, and `^` is the repeat (§13 has both). This
line is written without clauses because it is not about values at all: it is
about running a program over and over.

There is no loop construct, no counter and no test for "am I done yet". `^`
does the repeating, and the machine stops on its own because the halted state
has no transition. `step` has no clause for it, and §6.1 already told you what
no answer means.

`init`, `step` and `final` are the roles, not the identifiers you will find in
the file. `tm.42` spells the same three-part shape as `def inc = load ; run ;
unload`, with `def run = carry ; step^ ; halt!`: `load` and `carry` together do
the job of `init`, and `halt!` and `unload` together do the job of `final`.

### 11.2 The tape is a list with a hole in it

The obvious way to store a tape is a list plus a number saying where the head
is. Don't: every move would then be arithmetic, and moving would have to be
undone by arithmetic too.

Instead split the list at the head and keep the two halves, with the left half
written backwards so that the cell nearest the head is at its front:

```
tape = bits x (sym x bits)
       left, reversed   head   right
```

Now moving the head one cell right is: the head cell goes on the front of the
left list, and the front of the right list becomes the new head. As a clause:

```
def right (l, (h, c : r))  <->  (h : l, (c, r))
def left = right!
```

**`left` is not written out.** Moving left *is* moving right backwards, so it is
one `!`. Turned round, `right`'s clause says exactly that: take the front of
the left list as the head, and push the old head onto the right.

### 11.3 The state is a label, not a component

A machine with three control states and a tape looks like it should be a pair,
`state x tape`. Make it a labelled value instead:

```
conf = tape + (tape + tape)
```

with one label per state:

```
def carry t   <->  L t          -- still carrying a 1 leftward
def rewind t  <->  R (L t)      -- carry done; walk the head back to the start
def halt t    <->  R (R t)      -- finished
```

This is the one design decision in the file worth copying. To behave
differently in each state, `step` has one clause per state's label, and nothing
has to take the state out of a pair and put it back.

```
def step (L t)      <->  carrystep t
def step (R (L t))  <->  rewindstep t
```

No clause matches `R (R t)`, the halted state, so a halted machine has no next
step.

### 11.4 The table, one clause per row

The table for the carrying state has two rows: head is `0`, so write `1` and
start rewinding; head is `1`, so write `0`, move right, and keep carrying.

```
def carrystep (l, (L (), r))  <->  rewind (l, (R (), r))
def carrystep (l, (R (), r))  <->  carry (stepover (l, (L (), r)))
```

Reading the head is a pattern, and writing it is a term. `(l, (L (), r))` on
the left reads a `0`; `(l, (R (), r))` on the right writes a `1`. It is the
same notation in both places, which is §4.1's point that a pattern is a term
read backwards.

Rewinding has two rows too, chosen by whether there is any tape left:

```
def rewindstep (c : l, hr)  <->  rewind (left (c : l, hr))
def rewindstep ([], hr)     <->  halt ([], hr)
```

`stepover` is where the tape has to grow, because a real tape is infinite and a
list is not:

```
def stepover (l, (h, c : r))  <->  right (l, (h, c : r))
def stepover (l, (h, []))     <->  right (l, (h, [L ()]))
```

If there is a cell to the right, move onto it; if there is not, add a `0` first.
Each of these is an if-then-else in the sense of §10.5: two clauses whose
patterns cannot both match.

### 11.5 Running it

The number is written least significant bit first, so `[R (), R ()]` is `1,1`,
which is 3. `value` reads a bit list as a number, `inc` is the machine, and
`incval` is the two composed:

```
$ 42 tm inc "[R (), R ()]"
inc([R (), R ()]) =
  [L (), L (), R ()]
  -- 1 result
```

`0,0,1` is 4. Reading it as a number instead:

```
$ 42 tm incval "[R (), R ()]"
incval([R (), R ()]) =
  4
  -- 1 result
```

Zero is `[L ()]`, a list of one `0` bit, not the empty list: the head has to have
a cell to sit on.

### 11.6 Running the machine backwards

`dec` is `inc!`. Feed it 4:

```
$ 42 tm dec "[L (), L (), R ()]"
dec([L (), L (), R ()]) =
  [R (), R (), L ()]
  [R (), R ()]
  -- 2 results
```

Two answers, and both are right. `1,1` is 3, and `1,1,0` is also 3: the same
number with a trailing zero, which is a different list but the same value:

```
$ 42 tm value "[R (), R (), L ()]"
value([R (), R (), L ()]) =
  3
  -- 1 result
```

So the machine is not one-to-one, and §6 is why you get told rather than
being stopped from writing it. A language that insisted on one answer backwards
would have made you strip trailing zeros before this program could exist.

There is a lesson in here worth the detour. Suppose `init` were just
`carry`, which labels any configuration as a starting one, including ones
with the head halfway along the tape. Forwards that would make no difference
and every test would pass. Backwards it would produce five answers instead of
two, and the three extra ones would be half-finished machines. The fix is to say where the head
starts:

```
def load (h : r)  <->  ([], (h, r))
```

The `[]` on the right insists that nothing lies to the left of the head. Turned
round, it is a pattern, and it rejects every tape whose head is not at the
start. **`init` has to be as tight as `final`**, and running the program
backwards is how you find out that it is not. That check does not exist in a
language that only runs forwards.

### 11.7 What this does and does not show

It shows that a Turing machine fits in 42 with nothing added but `^`, and that
the shape it takes, `init ; step^ ; final`, needs nothing else. The transition
table is one clause per row, so a different machine is a different table in the
same frame.

It does not prove that 42 can compute everything computable. That would need an
argument covering every machine, not one machine. `tm.42` is the evidence that
the encoding works, not the proof — the proof is
[THEOREM.md](THEOREM.md), which settles rather more than Turing completeness:
42 denotes *exactly* the relations a computer can enumerate, no fewer and no
more. §18 is the other half of the same question, asked about 42 itself.

---

# Part II — The language underneath

Everything in Part I compiles to the language described here. It has no
clauses and no names: a program is a pipeline of steps, each reshaping one
value, built from thirteen primitives and seven ways of combining programs.
It is what 42 was before it had clauses, and what it still is underneath.

You need it to read what `42 show` prints, and to see why a definition gives
an answer you did not expect. You can also write in it directly, and
`prelude.42` is written that way.

---

## 12. Programs are pipelines, not functions

In an ordinary language you write:

```python
def single(x):
    return [x]
```

You *name* the input `x`, then mention `x` where you want it, and Part I's
`def single x <-> [x]` does the same. The program that clause compiles to has
no names at all.

Think of a Unix pipeline:

```
cat file | sort | uniq
```

Each stage receives the whole stream and produces a whole stream. Nothing is
named; data just flows through. A 42 program works exactly that way, except
that what flows through is a single value:

```
unitprod! ; swapprod ; (id * inl) ; inr
```

`;` is the pipe. At every point in that pipeline **exactly one value is in
flight**, and each stage rewrites the whole of it.

That style has a name of its own: **point-free**. "Point" is the mathematician's
word for an argument — a point of the domain — so a definition that names its
argument, `f(x) = …`, is *pointwise*, and one that never does is *point-free*.
The pipeline above is the everyday example: nothing in `cat file | sort | uniq`
names the lines passing between the stages, and nothing needs to.

In most languages going point-free is a style you may adopt. In 42's core it is
the only option: the core has no way to bind a name to a value, and the names
in clauses are compiled away. Sections 13 and 14 are the core's vocabulary, and
section 15 is how to read it, including what a clause becomes.

It is also part of why `!` works on every program without exception. There is no
conditional whose branches would have to be told apart when the program runs
backwards — branching is `+`, and both branches are simply kept — and there is
no variable whose value has to be tracked in reverse. Nothing was named, so
nothing has to be un-named.

So how do you write a program that takes *two* inputs? You don't. The two
inputs arrive packed into one pair `(x, y)`, and it is the program's job to
take the pair apart.

One consequence is what makes 42 feel alien at first:

> In the core you cannot name the parts of a value, so you cannot say *"take
> the `h` out of that pair and put it next to `ys`."* Instead a program
> **rearranges the shape of the value until the pieces are already in the
> right place.**

That rearranging is what most of 42's built-in programs are for. They do no
arithmetic or logic; they move parentheses around. They make more sense read as
plumbing than as computation. When you write clauses, the compiler works out
the rearranging for you, and §15.2 shows where it puts it.

---

## 13. The seven ways to combine programs

If `f` and `g` are programs, so are all of these.

### `f ; g` — do `f`, then `g`

The pipe. Left to right, in the order written.

```
swapprod ; inr        -- swap the pair, then tag the result "right"
```

### `f * g` — the value is a pair; run `f` on the left half, `g` on the right

```
     (a, b)
   f * g
     (f a, g b)
```

This is how you operate on part of a value without naming it, and by §3.4 it is
the only way, since you cannot pull a component out of a pair. The idiom to
memorise:

```
id * g        -- leave the left component alone, apply g to the right one
f  * id       -- apply f to the left component, leave the right alone
```

`id` is the do-nothing program. `id * rev` means "reverse the second component
of the pair, leave the first."

### `f + g` — the value is labelled; switch on the label

```
     L a                        R b
   f + g                      f + g
     L (f a)                    R (g b)
```

This is 42's `switch` / `match`. If the value is labelled left, run `f` on
what's inside; if labelled right, run `g` on what's inside.

The label survives: `f + g` puts the result back inside `L` or `R`. Almost always you then want to forget which branch you took, which is
what `join` does (§14). This is why you constantly see:

```
(f + g) ; join
```

Read that as: *switch on the label, handle each case, then discard the label.*

### `f | g` — try both, collect all answers

```
pred | succ           -- relates 5 to both 4 and 6
```

Genuine choice. The results of `f` and `g` are pooled.

### `f^` — repeat `f` any number of times

Collects everything reachable, including the starting value (zero
repetitions). `pred^` applied to `3` gives `{3, 2, 1, 0}`.

This only works if the process runs out of new values. `succ^` never does, and
42 will tell you so rather than hanging.

### `f!` — run `f` backwards

The reverse of `f`. `append!` splits lists. `inr!` removes an `R` label.
Applying it twice gets you back where you started: `f!!` is `f`.

You can name a reversed program:

```
def split = append!
```

### `f a` — a program that takes another program

A definition may take **parameters**, written after its name. They stand for
*programs*, not values, and let you write a pattern once instead of once per use:

```
def not    = swapsum                    -- L () becomes R (), R () becomes L ()
def mat    = dist ; (unitprod + unitprod)
def ctrl m = mat ; (id + m) ; mat!      -- "if the label is R, do m"

def flip   = ctrl not
def flip2  = ctrl flip
```

In clauses, parameters come between the name and the pattern:

```
def ctrl m (L (), a)  <->  (L (), a)
def ctrl m (R (), a)  <->  (R (), m a)
```

which compiles to the definition above with `mat` written out.

One new name there: `not` is the built-in `swapsum`, which does nothing but
exchange the two labels. §14 tabulates it with the other rearrangements:

```
$ not  on  L ()   ->  R ()
$ not  on  R ()   ->  L ()
```

`dist` and `unitprod` are the ones from §3, and `id` does nothing at all.

It is worth walking through `ctrl` once, because the definition is four
operators and none of them is a conditional. Feed `flip` a pair
whose label is `R` and whose payload is `L ()`:

```
$ dist                applied to  (R (), L ())  ->  R ((), L ())
$ mat                 applied to  (R (), L ())  ->  R L ()
$ mat ; (id + not)    applied to  (R (), L ())  ->  R R ()
$ flip(R (), L ())    =  (R (), R ())
```

Read down the middle column of that:

| after | the value | what happened |
|---|---|---|
| `dist` | `R ((), L ())` | the pair became a *labelled* thing: the label moved outside, and the payload came with it |
| `unitprod + unitprod` | `R L ()` | the leftover `()` is dropped from whichever branch we are in; the label is now the tag of a sum |
| `id + not` | `R R ()` | we are in the `R` branch, so `not` runs — and it runs on the *payload only* |
| `mat!` | `(R (), R ())` | the tag becomes a label again, and the pair is rebuilt |

Now the same input with the label `L`:

```
$ mat                 applied to  (L (), L ())  ->  L L ()
$ mat ; (id + not)    applied to  (L (), L ())  ->  L L ()
$ flip(L (), L ())    =  (L (), L ())
```

Nothing happens, because `id + not` runs `id` on the `L` branch.

Two things to take from this. The middle step does the work of an if-then-else,
and it is the `f + g` of a few pages back: you are not testing anything, you are
acting on whichever branch the value was already in. And at no point can the
label change. `dist` turns it into a tag, `id + not` can act inside a branch but
cannot move a value between branches, and `mat!` puts back the tag it finds.
That last fact is what the paragraphs on reversing below rest on.

Application is juxtaposition, as in `ctrl not`, and it binds tighter than every
*infix* operator, so `ctrl not ; f` means `(ctrl not) ; f`. The postfix `!` and
`^` bind tighter still, so `ctrl m!` means `ctrl (m!)`, which is the reading you
want: the argument is the thing being reversed.

Reversing works through a parameter without your doing anything:

```
ctrl! m   is   ctrl m!
```

Read that carefully, because it is easy to read as something it does not say, and
the something it does not say would be false.

It does **not** mean "test R, and if it held, undo `m`". That reading raises a
fair objection: running forwards, `m` might have changed things so that R no
longer holds, and then running backwards there would be nothing left to test.
Languages whose conditionals really do test a predicate over the state have
exactly that problem and pay for it. Janus makes the programmer supply a second
predicate at the end of every conditional, purely so that backward execution can
tell which branch it came from, and a program whose second
predicate is wrong has no defined meaning at all.

What saves `ctrl` is that **the label is never touched**. `mat` lifts it out to
become the tag of a sum, `id + m` acts inside a branch without being able to
change which branch it is in, and `mat!` puts the same label back. And `m` could
not interfere even if it tried, because the label is not part of what it is
handed:

```
$ 42 type prelude ctrl
ctrl  : (a <-> a) -> ((1 + 1) x a <-> (1 + 1) x a)
```

`m : a <-> a` receives the payload and nothing else. So R is *invariant*: "R held
before" and "R holds after" are the same statement, and there is nothing for a
backward run to have lost. `prelude.42` defines `cdouble = ctrl double` so you can
watch it:

```
$ cdouble(R (), 3)   =  (R (), 6)
$ cdouble(L (), 3)   =  (L (), 3)
$ cdouble!(R (), 6)  =  (R (), 3)
```

The payload doubles; the label comes through untouched in every case, in both
directions.

More generally, 42 has **no test operator at all**. Branching here is not "evaluate
a predicate and choose"; it is the sum functor, acting on whichever branch the data
was already in. That is why there is no assertion to supply and nothing that can
be got wrong: the question Janus answers with a proof obligation, this language
does not raise.

And a parameter may be used more than once, or reversed in one place and not
another:

```
def there_and_back m = m ; m!
```

Two rules. A parameter stands for a program, never for another parameterised
program, so you cannot pass `ctrl` itself as an argument. And a parameterised
definition is not a program until you supply the argument, so you cannot run it:

```
$ 42 prelude ctrl 3
error: `ctrl` is a combinator, not a relation -- it takes a parameter, so there
is nothing to apply to a value.
```

---

## 14. Plumbing: rearranging shapes when you cannot name things

These are 42's built-in programs. Read the table as *shape in → shape out*.
None of them compute anything; they move data around.

### Pairs

| Program | Turns | Into |
|---|---|---|
| `swapprod` | `(a, b)` | `(b, a)` |
| `assocprod` | `(a, (b, c))` | `((a, b), c)` |
| `assocprod!` | `((a, b), c)` | `(a, (b, c))` |
| `unitprod` | `((), a)` | `a` |
| `unitprod!` | `a` | `((), a)` |

`unitprod!` is worth dwelling on: it conjures a `()` out of nowhere. That is
allowed because `()` carries no information. Running it backwards, there was
only ever one thing that `()` could have been, so nothing is guessed. This is how you create structure in a language that cannot invent
data.

### Labels

| Program | Turns | Into |
|---|---|---|
| `inl` | `a` | `L a` |
| `inr` | `a` | `R a` |
| `inl!` | `L a` | `a` — and `R a` into **nothing** |
| `inr!` | `R a` | `a` — and `L a` into **nothing** |
| `swapsum` | `L a` / `R a` | `R a` / `L a` |
| `join` | `L a` *or* `R a` | `a` (drops the label) |
| `join!` | `a` | **both** `L a` and `R a` |

`join` and `join!` deserve attention, because they are where multiple answers
come from:

> `join` throws away one bit of information, namely which label was there. Run it
> backwards and that bit cannot be recovered, so `join!` has to return both
> possibilities. **Every time a 42 program gives you more than one answer, it
> is because a `join` was run backwards.**

### Copying

| Program | Turns | Into |
|---|---|---|
| `copy` | `a` | `(a, a)` |
| `copy!` | `(a, a)` | `a` — and a pair whose halves *differ* into **nothing** |

`copy!` is how you write a test. Duplicate a value, do something to one copy,
then demand the two copies still match.

### Mixing pairs and labels

| Program | Turns | Into |
|---|---|---|
| `dist` | `(L a, c)` | `L (a, c)` |
| | `(R b, c)` | `R (b, c)` |
| `dist!` | `L (a, c)` | `(L a, c)` |

`dist` is the one people trip over. In words: *you have a labelled value
paired with something else; push the pairing inside the label so that each
branch keeps its own copy of the extra thing.*

You need it whenever you want to switch on one component of a pair while
keeping the other component available in both branches. See §17.

### Others

| Program | Meaning |
|---|---|
| `id` | do nothing |
| `zero` | the program with no answers, ever |
| `unitsum` | `R a` → `a` (the `L` side is a type with no values) |
| `assocsum` | regroups nested labels, like `assocprod` for pairs |

---

## 15. How to read a program

- [15.1 Shape by shape](#151-shape-by-shape)
- [15.2 What a clause compiles to](#152-what-a-clause-compiles-to)
- [15.3 Several clauses: case trees](#153-several-clauses-case-trees)
- [15.4 Steps you did not write](#154-steps-you-did-not-write)

### 15.1 Shape by shape

The technique is to write the shape of the value after each step. That is all
of it; do it on paper the first few times.

Take:

```
def single = unitprod! ; swapprod ; (id * inl) ; inr
```

Feed it `7`, and annotate:

```
                          7
    unitprod!         ((), 7)          -- conjure a unit, pair it on the left
    swapprod          (7, ())          -- swap so 7 is on the left
    id * inl          (7, L ())        -- turn the () into L (), which is []
    inr               R (7, L ())      -- add an R label: that is [7]
```

Result: `[7]`. The program wraps a value into a one-element list.

Now read it backwards. Same steps, reverse order, each one reversed:

```
                          [7]  =  R (7, L ())
    inr!              (7, L ())
    (id * inl)!       (7, ())
    swapprod!         ((), 7)
    unitprod!!        7
```

It unwraps a one-element list. Fed `[7, 8]`, the `inl!` step would find `R (8, ...)`
where it wanted `L`, produce nothing, and the whole thing would return `{}`,
correctly, since `[7,8]` is not a one-element list.

That is the skill. Everything else is vocabulary.

### 15.2 What a clause compiles to

The pipeline above is exactly what `def single x <-> [x]` compiles to. Every
clause compiles in three parts, in this order:

1. **Match.** Take the input apart according to the pattern. This is the
   pattern *built backwards*: `x` needs nothing, `L t` needs `inl!`, a pair
   needs `*`.
2. **Route.** Rearrange the named pieces into the places the term needs them.
   This is the plumbing of §14: `swapprod`, `assocprod`, `unitprod!` where a
   constant like `[]` needs a `()` to be built from, `copy` where a name is used
   twice, `copy!` where a pattern names the same thing twice.
3. **Build.** Construct the answer: `inl`, `inr`, `*`, and the programs the
   term calls.

For `single`, the match is nothing, the route is `unitprod! ; swapprod` (make
room for the `[]`), and the build is `(id * inl) ; inr`. For the second clause
of `append`, `(x:xs, ys) <-> x : append (xs, ys)`:

```
    inr! * id           ((x, xs), ys)       -- match: x:xs is R (x, xs)
    assocprod!          (x, (xs, ys))       -- route: where the term wants them
    id * append         (x, zs)             -- build: the call
    inr                 x : zs              -- build: the cons cell
```

The names are gone, but every step is one you could have written by hand
(§16). Using a name twice shows up as a `copy`, and a pattern that names
something twice as a `copy!`:

```
def pair x  <->  (x, x)          -- compiles to  copy
def same (x, x)  <->  x          -- compiles to  copy!
```

### 15.3 Several clauses: case trees

A definition is the union of its clauses (§6.3), and could compile to exactly
that: each clause compiled on its own, joined with `|`. Usually it compiles to
something better. When every clause's pattern has an `L` or an `R` at the same
place, 42 splits on that label instead of trying every clause:

```
$ 42 show tour append
append   ([], ys) <-> ys
append   (x : xs, ys) <-> x : append (xs, ys)
append!  ys <-> ([], ys)
append!  (x : append (xs, ys)) <-> (x : xs, ys)
append   = dist ; unitprod + (assocprod! ; id * append ; inr) ; join
append!  = join! ; unitprod! + (inr! ; id * append! ; assocprod) ; dist!
```

Read the compiled line as §17's skeleton: `dist` pushes the pair inside the
first component's label, `+` handles the empty-list clause on the left and the
cons clause on the right, and `join` forgets which one ran. The two are the
same relation; the case tree is just quicker.

When the outputs also carry a label at one place, sorted the same way as the
inputs, the last step is `dist!` instead of `join`, and nothing is forgotten:

```
$ 42 show arith lt
lt   (0, n + 1) <-> (0, n + 1)
lt   (m + 1, n + 1) <-> let (a, b) = lt (m, n) in (a + 1, b + 1)
lt!  (0, n + 1) <-> (0, n + 1)
lt!  (a + 1, b + 1) <-> let lt (m, n) = (a, b) in (m + 1, n + 1)
lt   = dist ; (id * inr! ; unitprod ; inr ; unitprod!) + (id * inr! ; lt ; id * inr) ; dist!
lt!  = dist ; (unitprod ; inr! ; inr ; unitprod!) + (id * inr! ; lt! ; id * inr) ; dist!
```

A `join` in compiled output is a place where running backwards will have to
try both branches. A `dist!` is a place where it will not.

When the patterns do not split on a label, as with `split`'s turned-round
clauses `ys` and `x : append (xs, ys)`, the clauses are joined with `|`.

### 15.4 Steps you did not write

Two kinds of step appear in compiled output that correspond to nothing you
wrote.

**Unit checks.** A constant in a pattern, like `[]`, is matched by building it
backwards, and that leaves a `()` behind which must really be `()`. Usually the
plumbing that removes it checks it as a side effect. Where nothing else would,
42 adds `unitprod! ; swapprod ; unitprod`, which lets `()` through and nothing
else:

```
$ 42 show strings swapcase
swapcase   [] <-> []
swapcase   (c : cs) <-> swapbyte c : swapcase cs
swapcase!  [] <-> []
swapcase!  (swapbyte c : swapcase cs) <-> c : cs
swapcase   = (unitprod! ; swapprod ; unitprod) + swapbyte * swapcase
swapcase!  = (unitprod! ; swapprod ; unitprod) + swapbyte! * swapcase!
```

Where the types already guarantee the `()`, the check is left out: `rev`'s
empty-list branch compiles to plain `inl`. The rule is that a check is dropped
only if dropping it changes no definition's type, so on every input the command
line accepts, the result is the same.

**Order.** In a pair whose halves both need work, 42 decides which half is
built first, so that run backwards the cheaper half is checked first (§8.2).
That is why `rev` compiles to `rev * id` followed by `id * (…)` rather than one
`rev * (…)`: the two are the same relation, but backwards only one of them
stops.

---

## 16. How to write a program

You do not need this section to write 42: a clause is the program, and §15.2
is what the compiler does with it. Writing point-free by hand is for when you
want to choose every step yourself, as `prelude.42` does, or to understand what
the compiler chose. It is the method the compiler runs, done on paper. Three
steps.

### Step 1 — write it as a clause

```
def single x  <->  [x]
```

### Step 2 — write out the shape you start with and the shape you want

```
start:   x
want:    R (x, L ())
```

### Step 3 — get from one to the other using plumbing, one move at a time

Look at what you want: `R (x, L ())`. Peel it:

- Outermost is an `R` label → the last step is `inr`.
- Inside is a pair `(x, L ())`. You have `x`; you need `L ()` next to it.
- `L ()` comes from `()` via `inl`. So if you had `(x, ())` you could do `id * inl`.
- Where does a `()` come from? `unitprod!` turns `a` into `((), a)`.
- That gives `((), x)`, but you want `x` on the left → `swapprod`.

Read those in order and you have the program:

```
unitprod! ; swapprod ; (id * inl) ; inr
```

The general habit: **peel the target shape from the outside in, and each layer
tells you the next step to write, in reverse.**

---

## 17. Recursion

This is the shape §8's recursive clauses compile to, and the shape to use when
writing a recursion point-free.

Recursive data in 42 is always "base case, or something bigger", which is to
say a labelled value. So a recursive program is always a switch on that label, and
it always has the same skeleton.

### For a program taking one argument

```
(base + step) ; join
```

- `base` handles `L ...` (empty list, zero, …)
- `step` handles `R ...` and calls the program on the smaller piece
- `join` drops the label afterwards

### For a program taking two arguments

The value is a pair `(xs, ys)` where `xs` is the one you want to switch on.
`f + g` needs a *labelled* value, but you have a *pair*. That is exactly what
`dist` fixes:

```
dist ; (base + step) ; join
```

`dist` turns `(L a, ys)` into `L (a, ys)` and `(R b, ys)` into `R (b, ys)`, so
after it each branch still has `ys` in hand.

### Worked example: append

```
def append = dist ; (unitprod + (assocprod! ; (id * append) ; inr)) ; join
```

Fed `([1,2], [3])`, that is `(R (1, R (2, L ())), [3])`. Annotate:

```
                              (R (1, tail), [3])          tail = [2]
  dist                    R ((1, tail), [3])              -- push pair inside label
  ...  R branch, so the step program runs on ((1, tail), [3]):
    assocprod!              (1, (tail, [3]))              -- regroup
    id * append             (1, [2, 3])                   -- recurse on the right half
    inr                     R (1, [2, 3])                 -- rebuild a cons cell
  ...  back out, still labelled:
                          R (R (1, [2,3]))
  join                      R (1, [2, 3])   =  [1, 2, 3]
```

And the base case: fed `([], [3])`, that is `(L (), [3])`.

```
                              (L (), [3])
  dist                    L ((), [3])
  ...  L branch, so unitprod runs on ((), [3]):
    unitprod                [3]
                          L [3]
  join                      [3]
```

Correct: appending anything to the empty list gives it back.

Now notice what running this backwards does. The final `join` becomes the
*first* step, and `join!` cannot know which branch the answer came from, so it
tries both. That is precisely why `append!` enumerates every split: each `join!`
offers "the seam could have been here, or further along."

---

## 18. 42 interpreting itself

Section 11 built a program that *runs*: it keeps changing a value until it is
finished. This section builds one that runs **42 programs**. The file is
`meta.42`, and it is an interpreter for 42, written in 42.

That sounds like a stunt, and half of it is. The other half is not, and it is
worth the section: **you write the interpreter once and get the backward one
for nothing**, the same way you have got every backward program in this manual.
Nobody writes a "reverse interpreter" here. It is `!` applied to the forward
one.

### 18.1 A program is a value, once you write it down

Section 3 said every value is built from four things: the unit `()`, the two
tags `L` and `R`, and the pair. A *program* is not a value — but a written-down
description of one is. So the first job is to pick shapes.

There are two. One holds any 42 value at all:

```
type val = mu V. 1 + (V + (V + (V x V)))
```

Read it as "a value is a unit, or an `L` of one, or an `R` of one, or a pair of
two" — which is exactly what section 3 says a value is. Four constructors, one
per line, and `meta.42` gives them names: `vunit`, `vinl`, `vinr`, `vpair`.

The other holds a written-down program. It has one case for each structural way
of combining programs — `;`, `|`, `+`, `*` and `^` — plus one for the built-ins
and one for naming a definition. Two of section 13's seven do not need a case of
their own: a `!` rides along as a flag on the built-in or the reference it was
written on, and parameters are expanded away before a program is ever quoted.

| case | what it describes |
|---|---|
| a primitive | `copy`, `join`, `swapsum`, … and whether a `!` was written on it |
| a reference | "the definition at slot *n*", so recursion works |
| `t ; u` | the two parts |
| `t \| u` | the two parts |
| `t + u` | the two parts |
| `t * u` | the two parts |
| `t^` | the one part |

That is the whole language. You do not have to read the encoding to use the
interpreter — sections 18.3 onwards never open it up — but it helps to know
that nothing is hidden in there.

### 18.2 Every construct interprets itself

Here is the part worth seeing. Ask how the interpreter runs `t^`, the hardest
of section 13's seven. This is the whole answer:

```
$ 42 show meta evstar
evstar   = toframe! ; eval^ ; toframe ; tagstar * id
```

Ignore the `toframe` plumbing, which just moves components into place — that is
section 14, and nothing more. What is left is `eval^`. **To interpret `^`, the
interpreter uses `^`.** There is no loop, no counter, no "have we finished yet",
for the same reason section 11's Turing machine needed none.

It goes the whole way down. `;` is interpreted by `;`, `|` by `|`, `+` by `+`,
`*` by `*`. Object-level `copy` is meta-level `copy`, so the "these agree" test
of section 6 is inherited rather than rebuilt, and object-level `join` is
meta-level `join`, so **every many-answered program in the interpreted language
still traces back to `join!`**, exactly as section 6 said it does in the
language itself.

One thing that is *not* there is worth naming too. A language whose `if` has to
be undone must record which branch it took, or the backward run cannot tell.
The union case here is `onleft | onright` and records nothing, because section 6
already allows two answers. Keeping both branches is cheaper than separating
them.

### 18.3 Running a program through it

`42 quote` does this for you, for any definition in a file, clause definitions
included: it quotes what the clauses compiled to, which is a core program like
any other.

```
$ 42 quote tour rev "[1,2]"
eval rev([1, 2]) =
  [2, 1]
  -- 1 result
```

To hand the interpreter a program yourself, you have to write that program down
as a value. `meta.42` has short names that build one — a **quotation**:

| you write | you get |
|---|---|
| `qid`, `qnot`, `qcopy`, `qjoin`, `qinl`, `qinr`, `qswap`, `qdist`, `qzero` | that built-in, quoted |
| `qinv n12` | `copy!`, quoted — any built-in with a `!` on it |
| `qseq a b` | `a ; b`, quoted |
| `qalt a b` | `a \| b`, quoted |
| `qsum a b`, `qprod a b` | `a + b` and `a * b`, quoted |
| `qstar a` | `a^`, quoted |

and `runq` wraps one up so you can run it on an ordinary value:

```
def metanot = runq qnot
```

`metanot` is `not`, reached the long way round: the bit is encoded, paired with
the quotation, handed to `eval`, and unpacked again. It behaves like `not`
because it *is* `not`, one level up:

```
$ 42 meta metanot "L ()" --untyped
metanot(0) =
  R ()                      -- L () prints as 0; section 20 says why
  -- 1 result
```

Bigger ones work the same way. `runq (qseq qnot qnot)` is `not ; not`, and
`runq (qstar qnot)` is prelude.42's `toggle = not^` — many-answered, through
two levels of interpretation:

```
$ 42 meta metatoggle "L ()" --untyped
metatoggle(0) =
  0
  R ()
  -- 2 results
```

### 18.4 It runs backwards, and nobody wrote that

Everything in this manual so far has run both ways. So does this:

```
$ 42 meta metanot "R ()" --backward --untyped
metanot!(R ()) =
  0
  -- 1 result
```

Look at what that is. `--backward` daggered `metanot`, which is
`load q ; eval ; (load q)!` — so the dagger is `load q ; eval! ; (load q)!`.
**The same interpreter, reading the same quotation, run the other way.** There
is no second definition anywhere in `meta.42` for the backward direction. There
could not be: section 13's `!` had already turned the forward one into it before
anything ran.

And the three cases of section 6 survive the trip. `metasink` interprets
`join ; inl`, which throws the bit away:

```
$ 42 meta metasink "L ()" --untyped
metasink(0) =
  0                         -- forwards: both bits go to the same answer
  -- 1 result

$ 42 meta metasink "L ()" --backward --untyped
metasink!(0) =
  0                         -- backwards: both bits that could have led here
  R ()
  -- 2 results

$ 42 meta metasink "R ()" --backward --untyped
metasink!(R ()) =
  {}   (empty: no result)   -- and nothing at all for the answer it never gives
```

None, one, or many — at the interpreted level, coming out of an interpreter
that was never told about any of it.

### 18.5 Quoting your own

Two things to know and you can run your own programs through it.

**Build the quotation.** Compose the names from 18.3 exactly as you would
compose the programs. `copy ; copy!` becomes:

```
def metaeq = runq (qseq qcopy quncopy)
```

**Say which values you mean.** `val` holds every 42 value, so something has to
say whether a given value is a bit, a pair of bits or a list. That is the
*encoder*, and it is a parameter:

```
def encbool  = (vunit + vunit) ; vsum          -- values of  1 + 1
def encpair  = (encbool * encbool) ; vpair     -- values of  (1+1) x (1+1)
def runq q   = runw encbool q                  -- the bit version, for short
```

`runw` takes the encoder and the quotation. So interpreting `swapprod` on a
pair of bits is one line —

```
def metaswap = runw encpair qswap
```

```
$ 42 meta metaswap "(L (), R ())" --untyped
metaswap(0, R ()) =
  (R (), 0)
  -- 1 result
```

— and an encoder for any other shape is written the same way, out of the four
constructors of 18.1. That is the whole extension mechanism.

### 18.6 Programs that mention other programs

Everything so far quoted a program written out in full. Real files are not like
that: `arith.42`'s `mul` calls itself, `divmod` is `undivmod!` and `undivmod`
calls `mul`, `add` and `lt`. A quotation built by `runq` is read against an
*empty* set of definitions, so it cannot reach any of them.

For those there is a subcommand, which encodes the whole file and hands the
interpreter the definition you name:

```
$ 42 quote arith mul "(3, 4)"
eval mul(3, 4) =
  (4, 12)                   -- mul keeps the multiplier; see §9.3
  -- 1 result
```

`--backward` daggers the **interpreter** — the program it is reading is still
`mul`, which is why only the `eval` gets the `!`:

```
$ 42 quote arith mul "(4, 12)" --backward
eval! mul(4, 12) =
  (3, 4)
  -- 1 result
```

Read that one twice. It divided 12 by 4. §9.4 makes the point that `arith.42`
contains no division algorithm, because `divexact` is `mul!` — and now there is
no division algorithm in the *interpreter* either. `meta.42` knows thirteen
built-ins and five ways of combining them, and nothing else. The division came
out of `!`.

The whole file is reachable the same way:

```
$ 42 quote arith divmod "(7, 2)"
eval divmod(7, 2) =
  ((3, 1), 2)               -- 7 = 3x2 + 1
  -- 1 result

$ 42 quote arith sub "(5, 2)"
eval sub(5, 2) =
  (3, 2)
  -- 1 result
```

`42 quote` reaches `prelude.42` too, which means the example this manual opens
with can be run through an interpreter written in the language it is
interpreting:

```
$ 42 quote prelude add 5 --backward
eval! add(5) =
  (0, 5)
  (1, 4)
  (2, 3)
  (3, 2)
  (4, 1)
  (5, 0)
  -- 6 results
```

Every one of those six answers came out of `join!`, two levels down.

And leaving the value off shows you the thing itself — the program of §9.3,
as a value of the shape §18.1 describes:

```
$ 42 quote arith mul
mul, as a value meta.42 can read:
```

which prints 174 nodes of `L`s, `R`s and pairs, read against an environment of
nine definitions. That is what "a program is a value" means when you cash it
out.

### 18.7 Two things it costs

**It is slow.** Every step of the interpreted program is many steps of the
interpreter, and the state it carries is a deep tree. For a quotation with no
definitions in it, reckon on about a hundredfold. Once a file's definitions are
encoded too, it is three to four orders of magnitude: `mul (3, 4)` takes about
a tenth of a millisecond run directly and about two thirds of a second through
`42 quote`, and `divmod (7, 2)` about a millisecond against about eight
seconds. This is an interpreter to think with, not one to compute with.

**Pass `--untyped` when running `meta.42` itself.** Every `42 meta` transcript
above carries it, and the reason is worth a sentence. `meta.42` type-checks
perfectly well —

```
$ 42 type meta
-- 97/97 typed
```

— but `42 run` infers types over the program *after* combinators have been
substituted away, and `meta.42` substitutes one combinator in thirteen places.
The types it then has to solve get very large. The check is skipped, not
failed; section 19 has the flag. `42 quote` needs no such thing — it checks the
*interpreted* program against the file it came from, which is an ordinary type
check on an ordinary file.

### 18.8 What this does and does not show

It shows that 42 can interpret 42 with nothing added to the language, and that
the interpreter's backward direction costs nothing to obtain, because it is not
a separate program.

It also closes. `meta.42` is a 42 program, so it is one of the programs
`meta.42` interprets — and it does, if you are patient: `eval` reading its own
encoding takes about forty seconds to work out what `not` does to a bit, and
about eighty to work it out backwards. `tools/selfinterp.py` runs it. That is
useless as computation and is the whole point as a demonstration, because the
thing being interpreted two levels down is the interpreter itself.

It does not show the interpreter is *correct* — that it interprets every
program rather than the ones tried here. That claim, the encoding in full, and
a second one that does not follow from it are in
[THEOREM.md section 7](THEOREM.md#7-self-interpretation):

- **Proposition 17** is the correctness claim, and is checked rather than
  proved; section 8 there says so plainly.
- **Corollary 18** is 14.4 stated properly: given the forward interpreter is
  right, the backward one is too, with nothing further to prove.
- **Theorem 19** is the one worth the trip. `meta.42` also contains `dag`,
  which is 42's own `!` written *in* 42 — seven lines, one per case of 18.1.
  There are now two ways to run a program backwards: dagger the interpreter, or
  dagger the written-down program and run it forwards. The theorem says they
  agree.

That last one is the section's real content, and it is not the sort of thing
the defining law can tell you. `x ∈ P(y) ⟺ y ∈ P!(x)` holds for `eval` — but it
holds for *every* 42 program, including a badly written interpreter, so passing
it is no evidence of anything. Theorem 19 is where a wrong `dag` would be
caught, and it is the only place.

---

## 19. Reference

### Clauses

```
def NAME PARAM* PATTERN  <->  TERM          -- one clause; several make a definition
```

| Written | In a term | In a pattern |
|---|---|---|
| `x` | the value named `x` | anything; names it `x` |
| `()`, `(t, u)`, `L t`, `R t` | builds it | matches exactly that shape |
| `0`, `'a'`, `"hi"`, `[]`, `[t, u]` | that value | exactly that value |
| `t : u` | `R (t, u)`, a list cell | a non-empty list |
| `t + k` | `R` applied `k` times | a number at least `k` |
| `P t` | runs `P` on `t` | a value `P` could produce from `t` (runs `P!`) |
| `let q = t in e` | builds `t`, matches it against `q`, continues with `e` | — |

`P` is a definition (with its program arguments, if it takes any), a
parameter, a built-in, any of these followed by `!`, or any program in
brackets.

Rules: every name a clause binds is used, and every name it uses is bound
(§4.2). A name used twice is copied; a name bound twice in one pattern is an
equality test; a name may be bound again by a later `let` once its value has
been used (§7). A
pattern variable may not have the name of a definition, parameter or built-in.
`L`, `R`, `let`, `in` and `def` are reserved. A definition's clauses are written
together and share their parameters. A definition means the union of its
clauses (§6.3); a definition and its clauses turned round are each other's
reverse (§5).

### Combining programs

| Syntax | Name | Meaning |
|---|---|---|
| `f ; g` | sequence | do `f`, then `g` |
| `f * g` | pair-wise | value is a pair: `f` on the left half, `g` on the right |
| `f + g` | switch | value is labelled: `f` on `L`, `g` on `R`, label kept |
| `f \| g` | choice | do both, pool the answers |
| `f^` | repeat | apply `f` zero or more times, collect everything reachable |
| `f!` | reverse | run `f` backwards |
| `(...)` | grouping | |

Binding strength, loosest first: `|` then `;` then `+` then `*` then `!` `^`.
So `a ; b + c ; d` means `a ; (b + c) ; d`.

### Built-in programs

| Program | In | Out |
|---|---|---|
| `id` | `a` | `a` |
| `zero` | anything | nothing |
| `swapprod` | `(a, b)` | `(b, a)` |
| `assocprod` | `(a, (b, c))` | `((a, b), c)` |
| `unitprod` | `((), a)` | `a` |
| `swapsum` | `L a` / `R a` | `R a` / `L a` |
| `assocsum` | `L a`, `R (L b)`, `R (R c)` | `L (L a)`, `L (R b)`, `R c` |
| `unitsum` | `R a` | `a` |
| `inl` | `a` | `L a` |
| `inr` | `a` | `R a` |
| `join` | `L a` or `R a` | `a` |
| `copy` | `a` | `(a, a)` |
| `dist` | `(L a, c)` / `(R b, c)` | `L (a, c)` / `R (b, c)` |

Add `!` to any of them to get the reverse.

### Writing values on the command line

```
()            unit
L x   R x     labelled
(a, b)        pair
0  1  2  3    numbers        (unary)
[]  [1, 2]    lists
'a'           one byte       (§10)
"hello"       text           (a list of bytes)
```

### Command line

```
42      FILE NAME VALUE [--backward]    apply a definition
42 law  FILE NAME VALUE                 check reversibility
42 show FILE [NAME]                     print a definition, its reverse, and what it compiles to
42 type FILE [NAME]                     report the shapes (section 3.7)
42 quote FILE NAME [VALUE]              run it through meta.42 (section 18)
```

`42` is shorthand. It assumes `run` when you do not name a subcommand, and the
`.42` on a file name is optional, so `42 prelude append "([1,2], [3])"` is the
whole thing.

It is a script in the repository root, so either put that directory on your
`PATH` (`export PATH="/path/to/42:$PATH"`) or run it in place as `./42`. The long
form `python3 -m rel42 run prelude.42 append "..."` does exactly the same and
needs no setup at all.

Options: `--raw` turns off number/list display sugar (useful when you are not
sure what shape you actually have), `--limit` bounds recursion depth,
`--orbit` bounds how far `^` will search before giving up, and `--untyped`
skips the domain check and prints the bare relational answer (§6, §18).

`show` is handy for building intuition. It prints what a program's reverse
is:

```
$ 42 show prelude double
double   = copy ; add
double!  = add! ; copy!
```

### Source files

A file holds definitions, and it is the `FILE` in every command above. The
project ships several: `prelude.42` and `tour.42` are the ones this manual draws
on, and `arith.42`, `strings.42`, `rational.42` and `cipher.42` go further.

```
type name   = shape                 -- optional; a printing abbreviation (3.7)
def  name pattern <-> term          -- a clause (Part I)
def  name   = program               -- a point-free definition (Part II)
def  name p = program               -- p is a parameter, standing for a program
-- comments run to end of line
```

Definitions may refer to each other and to themselves, in any order, and the
two kinds mix freely.

### Errors and warnings from clauses

| Message begins | Meaning | See |
|---|---|---|
| `the variable x is bound and never used` | the clause would forget `x` | §2, §4.2 |
| `x is used but never bound` | the clause would have to invent `x` | §2, §4.2 |
| `the pattern variable x has the name of a definition` | rename the variable | §4.4 |
| `x is a definition, so here it must be applied` | a definition's name used as a value | §4.4 |
| `x is bound again while its value is still in hand` | a `let` reused a name before its value was used | §7 |
| `the clauses of f must be written together` | another definition sits between them | §4.1 |
| `every clause of f must have the same parameters` | parameter lists differ | §13 |
| `a clause's pattern must be a single term` | put brackets round the pattern | §4.1 |
| warning: `clauses i and j of f both match` | two patterns overlap; both clauses apply there | §6.4 |

---

## 20. Troubleshooting

### "I got `{}` and expected an answer"

`{}` means no answer. In order of likelihood:

1. **No clause matched.** For a definition written in clauses, check each
   pattern against your input. A constant in a pattern matches only that
   value (`0` does not match `1`), nesting must agree (§3.4), and a pattern
   that uses a name twice matches only when both places hold the same value.
   Running backwards, it is the turned-round clauses that must match: `42 show`
   prints them.

2. **Shape mismatch.** The most common cause by far. A program got a value of
   the wrong shape: `swapprod` on something that isn't a pair, `unitprod` on
   something that isn't a pair-with-unit-on-the-left.

   *Diagnosis:* ask for the type. `42 type FILE` reports any
   definition whose shapes cannot line up at all, and `run` refuses an argument
   that does not fit the domain (§6), so this class of bug announces itself
   rather than yielding `{}`. If you got `{}` in spite of that, the mismatch is
   *inside* a definition whose two ends still agree, and the type of each piece
   is the way in: `type FILE NAME` prints one.

   Failing that, run with `--raw` to see the true shape of your input, then walk
   the pipeline writing down shapes as in §15. The step where your written shape
   stops matching the table in §19 is the bug. If a pair is involved, check the
   nesting first: `(a, (b, c))` and `((a, b), c)` are different values (§3.4).

3. **A label was wrong.** `inl!` on an `R`-labelled value gives nothing, and
   vice versa. This is on purpose; it is how case analysis rejects.

4. **`copy!` on a mismatched pair.** It only succeeds when both halves are
   equal.

5. **Missing `dist`** (point-free only). You wrote `(f + g)` where the value is a *pair* whose
   first component is labelled, rather than a labelled value. `+` needs a
   labelled value. Insert `dist` first.

### "42 refused my clause"

Each message says what the clause would have done wrong, and the table at the
end of §19 says where it is explained. The two most common are a name bound and
never used, which would forget a value, and a name used and never bound, which
would invent one. Both have the same cure: decide where the value comes from or
goes to, and say so in the clause (§2, §4.2).

### "I got a warning that two clauses both match"

Two of a definition's patterns can match the same value, and since a definition
is the union of its clauses, both apply to it (§6.4). If you meant the first to
win, as it would in Haskell, make the patterns disjoint. If you meant both,
give each its own name and join them with `|`. A pattern that contains a call
counts as matching anything, so this warning can appear where the call would in
fact keep the patterns apart.

### "It works forwards, but backwards the call depth is exhausted"

A backward run stops only if every recursive call it makes is on something
smaller. 42 orders the work inside each term so that cheap checks come first
(§8.2), but it does not reorder a `let` chain, and it cannot invent a check that
is not there. Look at the turned-round clauses with `42 show`: if a recursive
call can be reached with an input no smaller than the original, add a filter
that rules that input out, and state it at the end of the clause as well as the
beginning (§9.7).

### "I got a result with a stray `L` or `R` on it"

In point-free code: you used `f + g` and forgot the `join` afterwards. `+` preserves the label by
design; `join` removes it.

### "It runs forever, or says the closure did not saturate"

You used `^` on something that keeps producing new values. `pred^` terminates
because it hits zero; `succ^` does not, because there is always a bigger
number. 42 reports this rather than hanging, but it cannot predict it in
advance.

Note that a program can be fine in one direction and not the other:
`downfrom = pred^` works forwards and diverges backwards.

### "The backward direction gives loads of answers"

Expected, and it is information-theoretic rather than a bug: every extra
answer corresponds to clauses whose results overlap, which in compiled form is
a `join` that discarded which branch was taken. If you
want fewer, arrange for the forward direction to destroy less. `copy` before an
operation, then `copy!` after, is the standard trick (see `double` in §6).

### "Empty list prints as `0`"

They really are the same value: `L ()` is the empty list, the nat zero, and
`false` all at once (§3.6). What tells them apart is the type, so `run` and
`law` print using the type they inferred and get this right:

```
$ 42 prelude append "[1,2,3]" -b
append!([1, 2, 3]) =
  ([], [1, 2, 3])
  ...
```

Two cases still print `0`. Under `--raw` and `--untyped` there is no type to
consult, by design. And where the inferred type is more general than the one you
had in mind, there may be nothing to consult either: `succ = inr` has type
`a <-> b + a`, which does not say "nat", so the printer falls back to guessing
and guesses `0`.

---

## Where to go next

The programs below are files in the 42 repository, at
<https://github.com/ubrowz/42>, along with the interpreter itself. Clone it and
each one runs with the `42` command of §19: `42 tour swap "(1, 2)"` reads
`tour.42`, finds `swap` in it, and applies it. Python 3.12 is the only
requirement.

- `tour.42` — the ground of Part I, in runnable form, written in clauses.
  `42 show tour NAME` prints any definition three ways.
- `arith.42` — the arithmetic of §9, heavily commented.
- `rational.42` — the exact rationals of §9.8.
- `strings.42` — the text of §10.
- `tm.42` — the Turing machine of §11.
- `meta.42` — the interpreter for 42 written in 42, of §18.
- `prelude.42` — shorter, denser examples, written point-free.
- [The course](COURSE.md) — writing point-free 42 by hand, step by step: the
  long form of §15–§17.
- `qft.42` — a 42 program that writes *Q42* programs: a circuit family, generated.
  It uses nothing beyond §§12–16, and is the clearest example in the project of a
  recursive definition doing real work.
- [The Q42 manual](QMANUAL.md) — the same language over the complex numbers,
  which makes it a quantum one. Read this manual first; that one assumes it.
---

## Appendix: a program and its inverse

The claim this manual opens with is that you write a program once and get both
directions. This appendix shows the machine doing it on a recursive definition,
where the backward direction is not the forward one run in reverse but a
different algorithm altogether, and shows it at both levels: the clauses, and
the core program they compile to.

### The program

Addition, from §9.2, is two clauses in `arith.42`:

```
$ 42 show arith add
add   (0, n) <-> n
add   (m + 1, n) <-> add (m, n) + 1
add!  n <-> (0, n)
add!  (add (m, n) + 1) <-> (m + 1, n)
add   = dist ; unitprod + (add ; inr) ; join
add!  = join! ; unitprod! + (inr! ; add!) ; dist!
```

Only the first two lines are in the file. The other four were computed from
them.

### The derivation, twice

**In clauses**, the reverse is the clauses turned round (§5.1). The first
turned-round clause says any `n` is `0 + n`. The second says a number of the
form `add (m, n) + 1`, that is, any number above zero split by running `add`
backwards on its predecessor, is `(m + 1, n)`. Both match every number above
zero, so both contribute, and that is why `add!` finds every split.

**In the core**, two rules produce the reverse. Reversing a composite reverses
the order of its parts, `(f ; g)! = g! ; f!`, and reversing a part is reversing
whatever it is made of. Section 15.1 applies them by hand to a program that does
not call itself; applied to `add`, they give:

| in `add`, in order | in `add!`, in order |
|---|---|
| `dist` | `join!` |
| `unitprod + (add ; inr)` | `unitprod! + (inr! ; add!)` |
| `join` | `dist!` |

Three things are worth noticing in that table.

The first column read downwards is the second column read upwards. That is
contravariance, and it is what keeps the pipeline fitting together: `join`
produced the value that `join!` now consumes.

Inside the sum, `add ; inr` becomes `inr! ; add!`. The same reversal applies at
every depth, including to the recursive call, which is what makes `add!`
recursive too.

And `unitprod!` becomes `unitprod`, not `unitprod!!`, because `f!!` is `f`
(§13). The operator that discards a `()` and the one that invents it trade
places.

The two derivations agree, and must: turning clauses round always gives the
same result as running their compiled program backwards (§2).

### The two directions

Forwards, `add` is a function:

```
$ 42 arith add "(2, 3)"
add(2, 3) =
  5
  -- 1 result
```

Backwards, it is a search, and it finds everything:

```
$ 42 arith add 5 --backward
add!(5) =
  (0, 5)
  (1, 4)
  (2, 3)
  (3, 2)
  (4, 1)
  (5, 0)
  -- 6 results
```

Those are different computations. One walks a number down to zero; the other
enumerates a set whose size depends on the input. No line of `arith.42`
describes the second, and `arith.42` contains no subtraction (§9.1).

### Checking it

The defining law says that running forwards and then backwards returns a set
containing where you started. That is checkable on any input:

```
$ 42 law arith add "(2, 3)"
add(2, 3) has 1 result(s)
  [ok ] 5: inv has 6 preimage(s), input in it
law holds
```

Six preimages, and `(2, 3)` is among them. The check is not that the answer is
unique, which it is not, but that nothing was lost: §6 is the section on why
those are different statements.

The type comes from the same definition, with no annotation anywhere in the
file:

```
$ 42 type arith add
add  : nat x (mu Y. a + Y) <-> mu Y. a + Y
```

The `<->` is doing the same work as everything above. There is no domain and no
codomain, only two sides, and which one is the input depends on the direction
you ran it.

### What was not written

Not the inverse clauses, not the inverse term, not the search, not a
subtraction, not a second type, and not a proof that the two agree. What was
written is two lines of `arith.42`; everything else on this page was derived
from them mechanically.

### A second example: Towers of Hanoi

`add` loses information forwards, so its backward direction is a search. Towers
of Hanoi loses none, and the contrast is worth seeing.

The textbook Python is four lines:

```python
def hanoi(n, src=0, aux=1, dst=2):
    if n == 0: return []
    return (hanoi(n-1, src, dst, aux)
            + [(src, dst)]
            + hanoi(n-1, aux, src, dst))
```

It never transforms a value: its whole method is to hand the three pegs to each
sub-call *in a different order*. A 42 definition takes one value, not a list of
arguments to reorder, so that reordering becomes data — an explicit rewrite of
every move a sub-call returns. A peg is `1 + (1 + 1)`, a move a pair of pegs;
`swap01` and `swap12` exchange two pegs. `tour.42` writes it:

```
def relabelA []             <->  []
def relabelA ((a, b) : ms)  <->  (swap12 a, swap12 b) : relabelA ms

def relabelB []             <->  []
def relabelB ((a, b) : ms)  <->  (swap01 a, swap01 b) : relabelB ms

def hanoi 0      <->  []
def hanoi (n+1)  <->  append (relabelA (hanoi n), (L (), R (R ())) : relabelB (hanoi n))
```

`n` is used twice, once per recursive call, so it is copied; `relabelA` and
`relabelB` are the map that replaces Python's argument reordering; and
`(L (), R (R ()))` is the one move the largest disk makes, from peg 0 to peg 2.

```
$ 42 tour hanoi 3
hanoi(3) =
  [(0, R R ()), (0, 1), (R R (), 1), (0, R R ()), (1, 0), (1, R R ()), (0, R R ())]
  -- 1 result
```

The seven-move solution, `0→2, 0→1, 2→1, 0→2, 1→0, 1→2, 0→2`. Read `R R ()` as
peg 2: the printer knows the first two values of `1 + (1 + 1)` as 0 and 1 and
has no name for the third (§3.6, §20).

Backwards, `hanoi!` reads a move list and returns the number of disks it solves,
or nothing if the list is not the optimal solution for any `n`:

```
$ 42 tour hanoi "[(0, 1), (0, R R ()), (1, R R ())]" --backward
hanoi!([(0, 1), (0, R R ()), (1, R R ())]) =
  2
  -- 1 result

$ 42 tour hanoi "[(0, R R ()), (1, R R ())]" --backward
hanoi!([(0, R R ()), (1, R R ())]) =
  {}   (empty: no result)
```

So `hanoi!` is a solution checker nobody wrote. Turned round, the two uses of
`n` become a pattern that names `n` twice, so both halves of the move list must
be solutions for the same number of disks. `add!` was subtraction, a different
algorithm; `hanoi!` is the same recursion the other way, admitting a list only
when it is exactly what `hanoi` produces.

This is also the definition that taught the compiler its order rule (§8.2):
both halves of its pair call something, and backwards the half with the cons
cell's check has to be taken apart first, or `hanoi!` never stops.
