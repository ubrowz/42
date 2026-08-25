# 42 — User Manual

For a reader with a computer science background. No prior knowledge of
reversible computing is assumed, and no term is used before it is defined.

---

## Contents

1. [The five-minute version](#1-the-five-minute-version)
2. [The one rule](#2-the-one-rule-nothing-may-be-thrown-away)
3. [Values](#3-values)
4. [Programs are pipelines, not functions](#4-programs-are-pipelines-not-functions)
5. [The seven ways to combine programs](#5-the-seven-ways-to-combine-programs)
6. [Plumbing](#6-plumbing-rearranging-shapes-when-you-cannot-name-things)
7. [None, one, or many answers](#7-none-one-or-many-answers)
8. [How to read a program](#8-how-to-read-a-program)
9. [How to write a program](#9-how-to-write-a-program)
10. [Recursion](#10-recursion)
11. [Arithmetic](#11-arithmetic)
12. [Strings and text](#12-strings-and-text)
13. [A Turing machine](#13-a-turing-machine)
14. [42 interpreting itself](#14-42-interpreting-itself)
15. [Reference](#15-reference)
16. [Troubleshooting](#16-troubleshooting)
16. [Appendix: a program and its inverse](#appendix-a-program-and-its-inverse)

---

## 1. The five-minute version

A 42 program can be run in two directions. You write it once.

```
$ 42 prelude append "([1,2], [3])"
append([1, 2], [3]) =
  [1, 2, 3]                 -- forwards: glue two lists together

$ 42 prelude append "[1,2,3]" --backward
append!([1, 2, 3]) =
  ([], [1, 2, 3])           -- backwards: every way to cut a list in two
  ([1], [2, 3])
  ([1, 2], [3])
  ([1, 2, 3], [])
```

The three words after `42` are a file, a program in it, and an input:

```
42   prelude   append   "([1,2], [3])"
     ^^^^^^^   ^^^^^^   ^^^^^^^^^^^^^^
     the file  a        the value to
     to read   program  run it on
               in it
```

`prelude` is `prelude.42`, a file of worked examples that comes with 42. The
`.42` is optional, so you may write either. And `append` is not built in. It is
defined in that file, on one line:

```
def append = dist ; (unitprod + (assocprod! ; (id * append) ; inr)) ; join
```

which will mean nothing yet, and is meant to: unpacking that line is what §4
through §10 are for. The point for now is that **only thirteen primitives are
built in** (listed in §15); everything else, `append` included, is written in a
file you can open.

Both directions ran the *same* definition. Nobody wrote the second one.

Two consequences follow, and they are the whole language:

- **Running backwards can give more than one answer.** Gluing `[1,2]` to `[3]`
  loses the information about where the seam was, so running it backwards has
  to offer every possibility. A 42 program therefore returns a *set* of
  answers, which may be empty, a single answer, or many.
- **A program may never destroy information it cannot account for.** That is
  the price of admission, and it is why 42 has no assignment statement, no
  variables, and no way to simply drop a value on the floor.

Everything else in this manual is a consequence of those two facts.

---

## 2. The one rule: nothing may be thrown away

Suppose 42 had ordinary assignment:

```
x = 0
```

Run that backwards and you are stuck: `x` is `0`, but what was it before?
Unanswerable. The old value is gone.

So 42 has no assignment. It has no variables at all. Instead, a program is a
*sequence of reshapings applied to one value*. If a step turns `A` into `B`,
there must be enough information in `B` to get back to `A`; if there is not,
the backward direction must be allowed to return several candidates.

This is why the language looks unfamiliar. It is not stylistic. Variables are
absent because assigning to a variable is exactly the operation the language
cannot afford.

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
value itself. Three examples, and they are the whole story:

```
$ inl!  applied to  L ()   ->  ()
$ inl!  applied to  R ()   ->  {}   (nothing)
```

`inl!` removes an `L` label. It can *reject* `R ()` because the tag is right
there to inspect.

```
$ join  applied to  L ()   ->  ()
$ join  applied to  R ()   ->  ()
```

`join` deletes the tag. Going forwards that is harmless, since both cases
give `()`.

```
$ join!  applied to  ()    ->  L ()   and   R ()
```

Going backwards, the tag is gone and cannot be recovered, so `join!` must
offer **both**. This is where multiple answers come from, and it is the
mechanical reason `append!` enumerates every split (§10).

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

are **different values**, not two spellings of the same one. A program written
for one will produce nothing at all when handed the other:

```
$ assocprod   on  (1, (2, 3))   ->  ((1, 2), 3)
$ assocprod   on  ((1, 2), 3)   ->  {}   (nothing)
$ assocprod!  on  ((1, 2), 3)   ->  (1, (2, 3))
```

`assocprod` converts between the two groupings. Getting the nesting wrong is
one of the most common causes of an unexpected empty result (§16).

Pairs are how a program takes two arguments. 42 has no multi-argument
application. `add` does not take two numbers; it takes one pair `(m, n)`.

To work on part of a pair, use `f * g`. It applies `f` to the left half and
`g` to the right half at once:

```
$ id * succ   on  (1, 2)   ->  (1, 3)      -- leave the left, bump the right
$ succ * id   on  (1, 2)   ->  (2, 2)      -- bump the left, leave the right
```

`id` is the do-nothing program, so `id * g` is the idiom for "act on the
second component only."

#### You cannot take a pair apart

In every other language, this is the most basic operation there is:

```python
fst((a, b)) == a
```

42 does not have it and cannot have it. `fst` throws `b` away. Run it
backwards and you would have to invent a `b` out of nothing, with no way to
know what it was. Discarding is what §2 forbids.

So a pair is easy to build and impossible to reduce, unless you can show that
nothing is lost. There are two ways to do that:

```
$ unitprod  on  ((), 5)   ->  5           -- () carries no information, so
                                          -- dropping it loses nothing
$ copy      on  5         ->  (5, 5)
$ copy!     on  (5, 5)    ->  5           -- the halves agree, so one is
$ copy!     on  (5, 6)    ->  {}          -- redundant; if they differ, this
                                          -- was not a duplicated value
```

`unitprod` drops a `()`, which is safe because there was only ever one thing
it could have been. `copy!` drops a duplicate, which is safe because the
survivor tells you what the other one was.

That is the complete list. Everything else you can do to a pair merely
*rearranges* it:

| Want to | Use | Effect |
|---|---|---|
| swap the halves | `swapprod` | `(a, b)` → `(b, a)` |
| regroup | `assocprod` | `(a, (b, c))` → `((a, b), c)` |
| regroup the other way | `assocprod!` | `((a, b), c)` → `(a, (b, c))` |
| work on the halves | `f * g` | `(a, b)` → `(f a, g b)` |
| add a `()` | `unitprod!` | `a` → `((), a)` |
| remove a `()` | `unitprod` | `((), a)` → `a` |
| duplicate | `copy` | `a` → `(a, a)` |
| remove a duplicate | `copy!` | `(a, a)` → `a`, else nothing |
| push a pair inside a label | `dist` | `(L a, c)` → `L (a, c)` |

Cannot be done at all: `fst`, `snd`, or anything else that silently drops a
component.

This is the deep reason §4 says you must "rearrange the shape until the pieces
are in the right place." You are not choosing to program that way for style.
You cannot pull a piece out of a pair, so moving the pair around it is the
only option available.

Finally, a shape mismatch is never an error, just an absence of answers:

```
$ swapprod  on  5   ->  {}   (nothing)
```

`5` is not a pair, so `swapprod` does not apply to it. See §16.

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
def succ = inr        -- "put an R label on"
def pred = inr!       -- "take an R label off"
```

`succ` is not arithmetic. It is *attaching a label*, and reversing it is
*removing the label*. Nobody had to write a special case for zero either:
`pred 0` yields nothing automatically, because `L ()` has no `R` to remove.

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

Note also which half of the language this is. Section 4 says 42 has no names,
and that stands: `mu` binds a *shape*, never a value. There is still no way to
name the `3` inside a pair.

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

## 4. Programs are pipelines, not functions

In an ordinary language you write:

```python
def single(x):
    return [x]
```

You *name* the input `x`, then mention `x` where you want it. 42 has no names.

Instead, think of a Unix pipeline:

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

So how do you write a program that takes *two* inputs? You don't. The two
inputs arrive packed into one pair `(x, y)`, and it is the program's job to
take the pair apart.

One consequence is what makes 42 feel alien at first:

> Because you cannot name the parts of a value, you cannot say *"take the `h`
> out of that pair and put it next to `ys`."* Instead you **rearrange the
> shape of the value until the pieces are already in the right place.**

That rearranging is what most of 42's built-in programs are for. They do no
arithmetic or logic; they move parentheses around. They make more sense read as
plumbing than as computation.

---

## 5. The seven ways to combine programs

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
what `join` does (§6). This is why you constantly see:

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

One new name there: `not` is the built-in `swapsum`, which does nothing but
exchange the two labels. §6 tabulates it with the other rearrangements:

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
operator, so `ctrl not ; f` means `(ctrl not) ; f`. `!` binds tighter still, so
`ctrl m!` means `ctrl (m!)`, which is the reading you want: the argument is the
thing being reversed.

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
$ 42 q42/classical ctrl 3
error: `ctrl` is a combinator, not a relation -- it takes a parameter, so there
is nothing to apply to a value.
```

---

## 6. Plumbing: rearranging shapes when you cannot name things

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
keeping the other component available in both branches. See §10.

### Others

| Program | Meaning |
|---|---|
| `id` | do nothing |
| `zero` | the program with no answers, ever |
| `unitsum` | `R a` → `a` (the `L` side is a type with no values) |
| `assocsum` | regroups nested labels, like `assocprod` for pairs |

---

## 7. None, one, or many answers

A 42 program returns a set, which takes some getting used to.

No answers, written `{}`, is normal and is not an error. It means "this input
is not something I apply to."

```
$ 42 tour pred 0
pred(0) =
  {}   (empty: no result)
```

Zero has no predecessor, so there is nothing to return.

A **shape** mismatch is different, and the two are worth keeping apart. As a
matter of meaning, `swapprod` applied to something that isn't a pair also denotes
`{}`: the program does not apply there, rather than crashing. But you almost
never mean that, so the command line type-checks first and refuses:

```
$ 42 prelude swap 5
error: the argument does not fit the domain of `swap`
  swap expects : a x b
  you gave     : 5
```

`pred 0` above is not refused, because `0` is a perfectly good input to `pred`
that happens to have no image. Emptiness because a relation is partial is
normal; emptiness because the shapes never lined up was almost certainly a
typo.

Add `--untyped` to see the underlying relational answer anyway:

```
$ 42 prelude swap 5 --untyped
swap(5) =
  {}   (empty: no result)
```

**One answer** is the ordinary case.

**Many answers** happen when information was destroyed going the other way:

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

A useful thing to know: **composing can bring the answer count back down.**
`add` reversed has many answers, but

```
def double = copy ; add
```

reversed has at most one, because `copy!` at the end throws away every pair
whose halves differ. `double! 6` is `{3}`, and `double! 7` is `{}`.

---

## 8. How to read a program

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

---

## 9. How to write a program

Work backwards from ordinary code. Three steps.

### Step 1 — write it with names, as an equation

```
single(x) = [x]
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

## 10. Recursion

A definition may refer to itself by name.

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

## 11. Arithmetic

Everything here is in `arith.42`, and every example below is runnable.

- [11.1 The governing question](#111-the-governing-question)
- [11.2 Addition](#112-addition)
- [11.3 Multiplication, and what it must carry](#113-multiplication-and-what-it-must-carry)
- [11.4 Division is multiplication backwards](#114-division-is-multiplication-backwards)
- [11.5 Subtraction](#115-subtraction)
- [11.6 Division with remainder](#116-division-with-remainder)
- [11.7 A filter must be stated at both ends](#117-a-filter-must-be-stated-at-both-ends)
- [11.8 Exact rationals](#118-exact-rationals)
- [11.9 Limits](#119-limits)

### 11.1 The governing question

You cannot write an operation that throws its inputs away. But you can nearly
always write the same operation in a form that keeps just enough to reconstruct
them, and that form is usually only one component bigger.

So the question is never "can 42 compute this?" It is:

> **What is the smallest thing I have to carry along?**

Answer that, and the operation follows. Better still, the *inverse* operation
comes free, which is why `arith.42` contains algorithms for addition,
multiplication and comparison, and none at all for subtraction or division.

### 11.2 Addition

The recursion skeleton from §10, unchanged:

```
def add = dist ; (unitprod + (add ; inr)) ; join
```

```
$ add(2, 3)  =  5
$ add!(5)    =  (0, 5)  (1, 4)  (2, 3)  (3, 2)  (4, 1)  (5, 0)
```

`add` is allowed to discard how the total was split, because that information
is still recoverable *as a set*: running backwards enumerates every pair.
Nothing is truly lost, it is merely spread across six answers.

### 11.3 Multiplication, and what it must carry

Here the naive version fails. `(m, n) ↦ m × n` has base case `0 × n = 0`,
which must discard `n` outright, and §3.4 established that nothing in the
language can do that. Unlike `add`, you cannot even recover it as a set: `mul`
would have to work for every `n`, so the base case has nowhere to put it.

The fix is to carry the multiplier along:

```
mul : (m, n)  ↦  (n, m × n)
```

```
def mul = dist ; ( (swapprod ; (id * inl))                        -- (0, n)   -> (n, 0)
                 + (mul ; (copy * id) ; assocprod! ; (id * add))  -- (m+1, n) -> (n, p+n)
                 ) ; join
```

```
$ mul(4, 5)  =  (5, 20)
$ mul(0, 7)  =  (7, 0)
```

One extra component in the output, and the whole thing works. Note the `copy`
in the step branch: the recursive call returns `(n, p)`, and we need `n` both
to add to `p` and to hand back, so we duplicate it rather than trying (and
failing) to use it twice.

### 11.4 Division is multiplication backwards

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

### 11.5 Subtraction

Same trick, one line each. Make addition keep its second operand:

```
def addk = (id * copy) ; assocprod ; (add * id)     -- (c, b) -> (c + b, b)
def sub  = addk!                                    -- (a, b) -> (a - b, b)
```

```
$ addk(2, 3)  =  (5, 3)
$ sub(5, 3)   =  (2, 3)
$ sub(3, 5)   =  {}       -- no natural c has c + 5 = 3
```

Subtraction on naturals is partial, and that partiality arrives for free.

### 11.6 Division with remainder

The pattern generalises: **write whichever direction is easy, then invert it.**
Reassembling a dividend from a quotient, a remainder and a divisor is easy;
dividing is not. So write the easy one.

```
undivmod : ((q, r), b)  ↦  (q × b + r,  b)        provided r < b
```

The proviso matters. Without `r < b`, both `(q=0, r=5)` and `(q=2, r=1)`
rebuild 5 from divisor 2, and the inverse would be ambiguous. So we need a
comparison, written as a filter (§3.4, §7):

```
def lt = dist ; ( (id * (inr! ; inr))
                + ((id * inr!) ; lt ; (id * inr))
                ) ; dist!
```

```
$ lt(2, 5)  =  (2, 5)      -- passes through unchanged
$ lt(5, 2)  =  {}          -- rejected
```

Two idioms there worth stealing. `inr! ; inr` means "check this is nonzero and
put it back exactly as it was". And `dist ; (f + g) ; dist!` is the
case-analysis skeleton for a program that must hand back its input: `dist!`
rebuilds what `dist` took apart, where `join` would have discarded the label.

Now the easy direction, and its inverse:

```
def undivmod = assocprod!            -- ((q, r), b)  ->  (q, (r, b))
             ; (id * lt)             -- keep only r < b
             ; (id * swapprod)       --              ->  (q, (b, r))
             ; assocprod             --              ->  ((q, b), r)
             ; (mul * id)            --              ->  ((b, q*b), r)
             ; assocprod!            --              ->  (b, (q*b, r))
             ; (id * add)            --              ->  (b, q*b + r)
             ; swapprod              --              ->  (q*b + r, b)
             ; (id * nonzero)        -- see §11.7

def divmod = undivmod!
```

```
$ divmod(17, 5)  =  ((3, 2), 5)      -- 17 = 3*5 + 2
$ divmod(12, 4)  =  ((3, 0), 4)
$ divmod(3, 5)   =  ((0, 3), 5)
```

### 11.7 A filter must be stated at both ends

That last line of `undivmod` looks like dead code:

```
def nonzero = inr! ; inr        -- keeps n unchanged if n > 0, else nothing

... ; swapprod ; (id * nonzero)
```

`lt` has already forced `b > 0`, so going forwards this check can never reject
anything. **It is there for the backward direction, and it is essential.**

Here is the reasoning, and it is the one piece that does not carry over from
ordinary programming:

> Reversing a pipeline reverses the order of its stages. A filter written
> early, pruning as you go forwards, ends up running last going backwards,
> long after the expensive work it was meant to prevent.

In `undivmod`, `lt` sits near the front and guarantees `b > 0`. Reversed, it
fires at the very end. By then `divmod(7, 0)` has already asked `mul!` to
divide by zero, and since `mul(m, 0) = (0, 0)` for *every* `m`, that search
never terminates. Repeating the constraint at the far end of the pipeline puts
it *first* under reversal:

```
$ divmod(7, 0)  =  {}        -- immediately, with the guard
                             -- without it: runs forever
```

> **Rule of thumb: a constraint you rely on in both directions must be stated
> at both ends.** Forwards, one of the two statements is redundant. That
> redundancy is the price of a pipeline that prunes in both directions. It is
> not dead code; deleting it changes termination.

### 11.8 Exact rationals

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
def qmul = transpose ; (mul * mul) ; transpose
```

`transpose` swaps the two inner components of a pair of pairs, and is its own
inverse. Watch it work:

```
((p, q), (r, s))     transpose     ->  ((p, r), (q, s))    numerators together
((p, r), (q, s))     mul * mul     ->  ((r, pr), (s, qs))  mul hands back operand 2
((r, pr), (s, qs))   transpose     ->  ((r, s), (pr, qs))  kept operand, then product
```

```
$ qmul((1,2), (3,4))  =  ((3, 4), (3, 8))       -- 1/2 × 3/4 = 3/8
$ qdiv((3,4), (3,8))  =  ((1, 2), (3, 4))       -- and back
```

Addition is the same idea over `(ps + qr, qs)`, but longer: the operands are
used unevenly: `s` three times, `q` twice, `p` and `r` once each. Since `mul`
hands back its second operand, `s` threads from one product into the next and
only `q` needs a `copy`. See `rational.42`, where the steps are named.

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
def qeq = cross ; (id * copy!) ; withps!
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

Then `copy!` demands the two agree, and one of them is **recomputed backwards to
cancel it**: `withps` pairs a value with `p×s` injectively, so `withps!` removes a
`p×s`. Computing
something, using it, and then un-computing it is how you borrow a scratch
value in a language with no scratch space.

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

### 11.9 Limits

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

## 12. Strings and text

Everything here is in `strings.42`.

- [12.1 There is no string type](#121-there-is-no-string-type)
- [12.2 Writing text](#122-writing-text)
- [12.3 Every list program already works](#123-every-list-program-already-works)
- [12.4 Case conversion is one bit](#124-case-conversion-is-one-bit)
- [12.5 How to write if-then-else](#125-how-to-write-if-then-else)

### 12.1 There is no string type

Nothing was added to the language to support text. A string is a list, and
lists already existed:

```
bit    = 1 + 1                    L () = 0,  R () = 1
byte   = bit × (bit × ( … ))      eight of them, MSB first, nested right
string = μX. 1 + (byte × X)       exactly the list type from §3.5
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

### 12.2 Writing text

| Written | Is |
|---|---|
| `'a'` | one byte |
| `"hello"` | a list of bytes |
| `"héllo"` | its UTF-8 bytes — six of them |
| `"a\nb"` | escapes: `\n` `\t` `\r` `\\` `\0` `\"` `\'` `\xNN` |

A character literal must be exactly one byte, so `'é'` is rejected; write it
as a string. And `""` is `L ()`, which is also `0` and `[]` (§3.6).

### 12.3 Every list program already works

This is the part worth pausing on. Because a string *is* a list, the list
programs from §10 operate on text with no modification whatsoever:

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
$ split("abc")  =  (0, "abc")  ("a", "bc")  ("ab", "c")  ("abc", 0)
```

Every way to cut a string in two, and nobody wrote a string-splitting routine.

### 12.4 Case conversion is one bit

In ASCII, upper and lower case differ in one bit, the one worth 32. So changing
case is not arithmetic; it is reaching into the byte and flipping a single
boolean:

```
byte = (b7, (b6, (b5, (b4, (b3, (b2, (b1, b0)))))))
        skip  skip  flip  ←------ leave alone ------→

def flipcase = id * (id * (swapsum * id))
```

The `swapsum` does the work; the `id`s either side of it are pure navigation.
And being a single `swapsum`, it is its own inverse: running `flipcase`
backwards is `flipcase`.

### 12.5 How to write if-then-else

Flipping bit 5 of *every* byte would be wrong: it turns a space into a NUL and
a comma into a form feed. We want to flip it only for letters, which needs a
conditional, and 42 does not have one.

`|` is not if-then-else. It runs both branches and pools the answers, so `f | g`
normally returns two results (§5). But if the branches are guarded by filters
that can never both succeed, exactly one of them ever produces anything, and
the union collapses into an ordinary deterministic choice:

> ```
> (guard ; then)  |  (complement-of-guard ; else)
> ```
>
> **This is how you write if-then-else in 42.** Making the two guards
> disjoint is your job, not the language's. Get it wrong in one direction and
> you silently get two answers; get it wrong in the other and you get none.

ASCII letters all lie in 64..127, that is `b7 = 0` and `b6 = 1`:

```
def bit0 = inl! ; inl           -- keeps a bit unchanged if it is 0
def bit1 = inr! ; inr           -- keeps a bit unchanged if it is 1

def hi    = bit0 * (bit1 * id)                    -- b7=0, b6=1
def notHi = (bit1 * id) | (bit0 * (bit0 * id))    -- everything else

def swapbyte = (hi ; flipcase) | notHi
def swapcase = (inl + ((swapbyte * swapcase) ; inr)) ; join
```

```
$ swapcase("Hello, World!")   =  "hELLO, wORLD!"
$ swapcase("abc 123 XYZ")     =  "ABC 123 xyz"
```

Punctuation, spaces and digits now pass through untouched, and `swapcase` is
still its own inverse.

The residual inaccuracy, stated precisely rather than waved at: the sixteen
bytes ``@[\]^_`{|}~`` and DEL share the letters' top two bits, so they still get
mapped onto each other. Excluding them needs a range check on the low five
bits, which is real work for very little return. (There is a test asserting this
caveat is exactly true, so it cannot quietly become false.)

---

## 13. A Turing machine

Every program so far does one thing to a value and stops. This section builds a
machine that *runs*: it keeps changing a value until it is finished, and only
then gives an answer. That is the last thing a language has to be able to do,
and in 42 it needs no new construct, just `^` and `!` from section 5.

The file is `tm.42`. The machine adds one to a binary number.

### 13.1 The shape every machine takes

A Turing machine is a tape, a head, a control state, and a table saying what to
do next. In 42 the whole of it is three programs joined by `;`:

```
init ; step^ ; final
```

- `init` turns the input into a starting **configuration**: tape, head and
  state, all in one value.
- `step` is **one** move of the machine: `configuration <-> configuration`.
- `step^` is section 5's "repeat any number of times", so it relates the start
  to *every* configuration the machine can reach.
- `final` is a filter that lets through only configurations that have halted,
  and reads the answer off the tape.

There is no loop construct, no counter and no test for "am I done yet". `^`
does the repeating, and the machine stops on its own because the halted state
has no transition. `step` is empty there, and section 7 already told you what
an empty result means.

### 13.2 The tape is a list with a hole in it

The obvious way to store a tape is a list plus a number saying where the head
is. Don't: every move would then be arithmetic, and moving would have to be
undone by arithmetic too.

Instead split the list at the head and keep the two halves, with the left half
written backwards so that the cell nearest the head is at its front:

```
tape = bits x (sym x bits)
       left, reversed   head   right
```

Now moving the head one cell right is: take the head cell and put it on the
front of the left list, take the front of the right list and make it the new
head. Every part of that is `inr` or `inr!` from section 6, putting something
on the front of a list and taking it off:

```
def right = assocprod ; ((swapprod ; inr) * id) ; (id * inr!)
def left  = right!
```

**`left` is not written out.** Moving left *is* moving right backwards, so it is
one `!`. That is not a trick; it is what section 5 says `!` means, applied to
the one place in a machine where it obviously holds.

### 13.3 The state is a label, not a component

A machine with three control states and a tape looks like it should be a pair,
`state x tape`. Make it a labelled value instead:

```
conf = tape + (tape + tape)
```

with one branch per state:

```
def carry  = inl            -- still carrying a 1 leftward
def rewind = inl ; inr      -- carry done; walk the head back to the start
def halt   = inr ; inr      -- finished
```

This is the one design decision in the file worth copying. To behave differently
in each state you now write `f + g + h`, which is section 5's `+` doing exactly
what it is for. With a pair you would need `dist` to get at the state and more
plumbing to put it back, in every branch. Sections 3.4 and 6 both make the same
point in the small; here it is what keeps `step` down to one line.

### 13.4 Reading the head, and writing it backwards

To act on the symbol under the head you have to get at it. `focus` brings it to
the front, and `dist` then splits on it, exactly as in section 6:

```
def focus    = assocprod ; (swapprod * id) ; assocprod!
def readhead = focus ; dist ; (unitprod + unitprod)
```

`readhead` turns a tape into a labelled value: the `L` branch means the head was
`0`, the `R` branch means it was `1`. Run it backwards and it writes the head
instead, with the label choosing what to write:

```
def write0 = inl ; readhead!
def write1 = inr ; readhead!
```

One program, read in both directions, is the whole of reading and writing.

### 13.5 The table, one line per state

```
def carrystep  = readhead ; ((write1 ; rewind) + (write0 ; stepover ; carry)) ; join
def rewindstep = ((iscons * id) ; left ; rewind) | ((isnil * id) ; halt)

def step = (carrystep + (rewindstep + zero)) ; (id + join) ; join
```

Read `carrystep` as the table it is: head is `0`, so write `1` and start
rewinding; head is `1`, so write `0`, move right, and keep carrying. `rewindstep`
uses the partial identities `iscons` and `isnil` from the file to ask whether
there is any tape left, which is section 12.5's if-then-else with no condition
to evaluate. And `zero` in the third branch is the halted state: no transition,
so the machine stops.

`stepover` is where the tape has to grow, because a real tape is infinite and a
list is not:

```
def stepover = ((id * (id * iscons)) ; right) | (pad ; right)
```

If there is a cell to the right, move onto it; if there is not, add a `0` first.
Note that `|` is doing this with no requirement that the two branches be
distinct. They happen to be, because `iscons` and `isnil` cannot both apply, but
nothing made you prove it.

### 13.6 Running it

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

### 13.7 Running the machine backwards

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

So the machine is not one-to-one, and section 7 is why you get told rather than
being stopped from writing it. A language that insisted on one answer backwards
would have made you strip trailing zeros before this program could exist.

There is a lesson in here worth the detour. The first version of `init` was
just `carry`, which labels any configuration as a starting one, including ones
with the head halfway along the tape. Forwards that made no difference and
every test passed. Backwards it produced five answers instead of two, and the
three extra ones were half-finished machines. The fix is one filter:

```
def load = inr! ; unitprod! ; (inl * id)
```

which insists the head starts at the end. **`init` has to be as tight as
`final`**, and running the program backwards is how you find out that it is not.
That check does not exist in a language that only runs forwards.

### 13.8 What this does and does not show

It shows that a Turing machine fits in 42 with nothing added, and that the shape
it takes, `init ; step^ ; final`, needs only `;`, `^` and the plumbing of
section 6. The transition table is a `+` over states and a `|` over the rows in
each state, so a different machine is a different table in the same frame.

It does not prove that 42 can compute everything computable. That would need an
argument covering every machine, not one machine. `tm.42` is the evidence that
the encoding works, not the proof — the proof is
[THEOREM.md](THEOREM.md), which settles rather more than Turing completeness:
42 denotes *exactly* the relations a computer can enumerate, no fewer and no
more. Section 14 is the other half of the same question, asked about 42 itself.

---

## 14. 42 interpreting itself

Section 13 built a program that *runs*: it keeps changing a value until it is
finished. This section builds one that runs **42 programs**. The file is
`meta.42`, and it is an interpreter for 42, written in 42.

That sounds like a stunt, and half of it is. The other half is not, and it is
worth the section: **you write the interpreter once and get the backward one
for nothing**, the same way you have got every backward program in this manual.
Nobody writes a "reverse interpreter" here. It is `!` applied to the forward
one.

### 14.1 A program is a value, once you write it down

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

The other holds a written-down program, and it has one case per way of
combining programs from section 5, plus one for the built-ins and one for
naming a definition:

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
interpreter — sections 14.3 onwards never open it up — but it helps to know
that nothing is hidden in there.

### 14.2 Every construct interprets itself

Here is the part worth seeing. Ask how the interpreter runs `t^`, the hardest
of section 5's seven. This is the whole answer:

```
$ 42 show meta evstar
evstar   = toframe! ; eval^ ; toframe ; tagstar * id
```

Ignore the `toframe` plumbing, which just moves components into place — that is
section 6, and nothing more. What is left is `eval^`. **To interpret `^`, the
interpreter uses `^`.** There is no loop, no counter, no "have we finished yet",
for the same reason section 13's Turing machine needed none.

It goes the whole way down. `;` is interpreted by `;`, `|` by `|`, `+` by `+`,
`*` by `*`. Object-level `copy` is meta-level `copy`, so the "these agree" test
of section 7 is inherited rather than rebuilt, and object-level `join` is
meta-level `join`, so **every many-answered program in the interpreted language
still traces back to `join!`**, exactly as section 7 said it does in the
language itself.

One thing that is *not* there is worth naming too. A language whose `if` has to
be undone must record which branch it took, or the backward run cannot tell.
The union case here is `onleft | onright` and records nothing, because section 7
already allows two answers. Keeping both branches is cheaper than separating
them.

### 14.3 Running a program through it

To hand the interpreter a program you have to write that program down as a
value. `meta.42` has short names that build one — a **quotation**:

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
  R ()                      -- L () prints as 0; section 16 says why
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

### 14.4 It runs backwards, and nobody wrote that

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
could not be: section 5's `!` had already turned the forward one into it before
anything ran.

And the three cases of section 7 survive the trip. `metasink` interprets
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

### 14.5 Quoting your own

Two things to know and you can run your own programs through it.

**Build the quotation.** Compose the names from 14.3 exactly as you would
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
constructors of 14.1. That is the whole extension mechanism.

### 14.6 Programs that mention other programs

Everything so far quoted a program written out in full. Real files are not like
that: `arith.42`'s `mul` calls itself, `divmod` is `undivmod!` and `undivmod`
calls `mul`, `add` and `lt`. A quotation built by `runq` is read against an
*empty* set of definitions, so it cannot reach any of them.

For those there is a subcommand, which encodes the whole file and hands the
interpreter the definition you name:

```
$ 42 quote arith mul "(3, 4)"
eval mul(3, 4) =
  (4, 12)                   -- mul keeps the multiplier; see §11.3
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

Read that one twice. It divided 12 by 4. §11.4 makes the point that `arith.42`
contains no division algorithm, because `divexact` is `mul!` — and now there is
no division algorithm in the *interpreter* either. `meta.42` knows thirteen
built-ins and seven ways of combining them, and nothing else. The division came
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

And leaving the value off shows you the thing itself — the program of §11.3,
as a value of the shape §14.1 describes:

```
$ 42 quote arith mul
mul, as a value meta.42 can read:
```

which prints 174 nodes of `L`s, `R`s and pairs, read against an environment of
nine definitions. That is what "a program is a value" means when you cash it
out.

### 14.7 Two things it costs

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
failed; section 15 has the flag. `42 quote` needs no such thing — it checks the
*interpreted* program against the file it came from, which is an ordinary type
check on an ordinary file.

### 14.8 What this does and does not show

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
  which is 42's own `!` written *in* 42 — seven lines, one per case of 14.1.
  There are now two ways to run a program backwards: dagger the interpreter, or
  dagger the written-down program and run it forwards. The theorem says they
  agree.

That last one is the section's real content, and it is not the sort of thing
the defining law can tell you. `x ∈ P(y) ⟺ y ∈ P!(x)` holds for `eval` — but it
holds for *every* 42 program, including a badly written interpreter, so passing
it is no evidence of anything. Theorem 19 is where a wrong `dag` would be
caught, and it is the only place.

---

## 15. Reference

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
| `swapsum` | `L a` | `R a` |
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
'a'           one byte       (§12)
"hello"       text           (a list of bytes)
```

### Command line

```
42      FILE NAME VALUE [--backward]    apply a definition
42 law  FILE NAME VALUE                 check reversibility
42 show FILE [NAME]                     print a definition and its reverse
42 type FILE [NAME]                     report the shapes (section 3.7)
42 quote FILE NAME [VALUE]              run it through meta.42 (section 14)
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
`--orbit` bounds how far `^` will search before giving up.

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
def  name   = program
def  name p = program               -- p is a parameter, standing for a program
-- comments run to end of line
```

Definitions may refer to each other and to themselves, in any order.

---

## 16. Troubleshooting

### "I got `{}` and expected an answer"

`{}` means no answer. In order of likelihood:

1. **Shape mismatch.** The most common cause by far. A program got a value of
   the wrong shape: `swapprod` on something that isn't a pair, `unitprod` on
   something that isn't a pair-with-unit-on-the-left.

   *Diagnosis:* ask for the type. `42 type FILE` reports any
   definition whose shapes cannot line up at all, and `run` refuses an argument
   that does not fit the domain (§7), so this class of bug now announces itself
   rather than yielding `{}`. If you got `{}` in spite of that, the mismatch is
   *inside* a definition whose two ends still agree, and the type of each piece
   is the way in: `type FILE NAME` prints one.

   Failing that, run with `--raw` to see the true shape of your input, then walk
   the pipeline writing down shapes as in §8. The step where your written shape
   stops matching the table in §15 is the bug. If a pair is involved, check the
   nesting first: `(a, (b, c))` and `((a, b), c)` are different values (§3.4).

2. **A label was wrong.** `inl!` on an `R`-labelled value gives nothing, and
   vice versa. This is on purpose; it is how case analysis rejects.

3. **`copy!` on a mismatched pair.** It only succeeds when both halves are
   equal.

4. **Missing `dist`.** You wrote `(f + g)` where the value is a *pair* whose
   first component is labelled, rather than a labelled value. `+` needs a
   labelled value. Insert `dist` first.

### "I got a result with a stray `L` or `R` on it"

You used `f + g` and forgot the `join` afterwards. `+` preserves the label by
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
answer corresponds to a `join` that discarded which branch was taken. If you
want fewer, arrange for the forward direction to destroy less. `copy` before an
operation, then `copy!` after, is the standard trick (see `double` in §7).

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
each one runs with the `42` command of §15: `42 tour swap "(1, 2)"` reads
`tour.42`, finds `swap` in it, and applies it. Python 3.12 is the only
requirement.

- `tour.42` — the same ground as this manual, in runnable form. It should read
  easily once §§4–6 have sunk in.
- `arith.42` — the arithmetic of §11, heavily commented.
- `rational.42` — the exact rationals of §11.8.
- `strings.42` — the text of §12.
- `tm.42` — the Turing machine of §13.
- `meta.42` — the interpreter for 42 written in 42, of §14.
- `prelude.42` — shorter, denser examples.
- `qft.42` — a 42 program that writes *Q42* programs: a circuit family, generated.
  It uses nothing beyond §§4–9, and is the clearest example in the project of a
  recursive definition doing real work.
- [The Q42 manual](QMANUAL.md) — the same language over the complex numbers,
  which makes it a quantum one. Read this manual first; that one assumes it.
---

## Appendix: a program and its inverse

The claim this manual opens with is that you write a program once and get both
directions. Section 8 shows you reading a program backwards by hand. This
appendix shows the machine doing it, on a recursive definition, where the
backward direction is not the forward one run in reverse but a different
algorithm altogether.

### The program

Addition, from §11.2, is six operators:

```
$ 42 show prelude add
add   = dist ; unitprod + (add ; inr) ; join
add!  = join! ; (unitprod! + (inr! ; add!) ; dist!)
```

The second line is not in `prelude.42`. It was computed from the first.

### The derivation

Two rules produce it. Reversing a composite reverses the order of its parts,
`(f ; g)! = g! ; f!`, and reversing a part is reversing whatever it is made of.
Section 8 applies them by hand to a program that does not call itself; applied
to `add`, they give:

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
(§5). The operator that discards a `()` and the one that invents it trade
places.

### The two directions

Forwards, `add` is a function:

```
$ 42 prelude add "(2, 3)"
add(2, 3) =
  5
  -- 1 result
```

Backwards, it is a search, and it finds everything:

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

Those are different computations. One walks a number down to zero; the other
enumerates a set whose size depends on the input. No line of `prelude.42`
describes the second, and `arith.42` contains no subtraction (§11.1).

### Checking it

The defining law says that running forwards and then backwards returns a set
containing where you started. That is checkable on any input:

```
$ 42 law prelude add "(2, 3)"
add(2, 3) has 1 result(s)
  [ok ] 5: inv has 6 preimage(s), input in it
law holds
```

Six preimages, and `(2, 3)` is among them. The check is not that the answer is
unique, which it is not, but that nothing was lost: §7 is the section on why
those are different statements.

The type comes from the same definition, with no annotation anywhere in the
file:

```
$ 42 type prelude add
add  : nat x (mu Y. a + Y) <-> mu Y. a + Y
```

The `<->` is doing the same work as everything above. There is no domain and no
codomain, only two sides, and which one is the input depends on the direction
you ran it.

### What was not written

Not the inverse term, not the search, not a subtraction, not a second type, and
not a proof that the two agree. What was written is one line of `prelude.42`;
everything else on this page was derived from it mechanically.
