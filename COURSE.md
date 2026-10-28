# Learning to write a 42 program

A short course for people who already program — in Python, say — and have
bounced off 42 at least once. It assumes you have read §1–§3 of the
[manual](MANUAL.md) (values, and the one rule) and stalled somewhere around
"how do I actually *write* one of these."

The manual's §15 and §16 are the two-paragraph version of this course. If those
worked for you, you do not need this. If they did not, the problem is almost
always the same one, and it is not a lack of cleverness:

> In Python you write a program by naming the inputs and then saying what to do
> with them. **In 42 you cannot name anything.** So the entire method you have
> for turning an idea into code does not apply, and nothing has replaced it
> yet.

This course replaces it. The replacement is mechanical — it is closer to
solving a maze than to having an insight — and by the end you should be able to
sit down with an ordinary function and grind it into a 42 definition without
guessing.

Every code block that starts with `$` is a real command against files in the
repository. `course.42` ships alongside this document and holds every
definition below, in order.

## Contents

1. [Lesson 1 — there is no "hello, world", and that is the first lesson](#lesson-1--there-is-no-hello-world-and-that-is-the-first-lesson)
2. [Lesson 2 — the same program, backwards](#lesson-2--the-same-program-backwards)
3. [Lesson 3 — reading the output](#lesson-3--reading-the-output)
4. [Lesson 4 — reading a program: write the shape after every step](#lesson-4--reading-a-program-write-the-shape-after-every-step)
5. [Lesson 5 — writing your first definition: peel the target](#lesson-5--writing-your-first-definition-peel-the-target)
6. [Lesson 6 — acting on part of a value](#lesson-6--acting-on-part-of-a-value)
7. [Lesson 7 — choosing, and the recursion skeleton](#lesson-7--choosing-and-the-recursion-skeleton)
8. [Lesson 8 — two arguments, and `dist`](#lesson-8--two-arguments-and-dist)
9. [Lesson 9 — recursion, start to finish](#lesson-9--recursion-start-to-finish)
10. [Lesson 10 — a test is just `copy` and `copy!`](#lesson-10--a-test-is-just-copy-and-copy)
11. [Lesson 11 — if-then-else](#lesson-11--if-then-else)
12. [Lesson 12 — one real program, checked](#lesson-12--one-real-program-checked)
13. [Lesson 13 — when the shapes fight back](#lesson-13--when-the-shapes-fight-back)

[Appendix: a Python-idiom to 42-move phrasebook](#appendix-a-python-idiom-to-42-move-phrasebook)

---

## Lesson 1 — there is no "hello, world", and that is the first lesson

Every course for every language starts by printing `hello, world`. 42 cannot,
because **42 has no input and no output.** A program is not a thing that runs
and produces effects; it is a relation between a value going in and a value
coming out. What you "see" is the interpreter printing the value it computed.

So the nearest thing to a first program is the one that does *nothing* — the
identity relation. A program lives in a file, as a named definition, so put
this one line in a file. `course.42` (which ships with this document) already
has it:

```
def hello = id
```

and run it:

```
$ 42 course hello '"hello, world"'
hello("hello, world") =
  "hello, world"
  -- 1 result
```

The three words after `42` are the same three words every 42 command takes:

```
42   course   hello   '"hello, world"'
     ^^^^^^   ^^^^^   ^^^^^^^^^^^^^^^^
     the file  a def   the value to
     to read   in it   run it on
```

(`42` is a script in the repository root; run it as `./42` or put that
directory on your `PATH` — manual §19. Everything below writes it bare.)

You must name a **definition** — `id` on its own will not do, because the
command line resolves a name in a file, not an arbitrary expression. That is
why even the do-nothing program needs a `def`. Make your own file `first.42`
containing just `def hello = id` and `42 first hello '"hi"'` works the same
way.

What this already teaches:

- A 42 program is `file` + `definition` + `value`. Every command has this shape.
- There is no `print`. The value that comes out is the whole result.
- `"hello, world"` is not a string. 42 has no string type; it is a list of
  bytes, and the printer shows lists of printable bytes in quotes as a
  convenience (manual §10).

The Python you are comparing this to:

```python
def hello(x):
    return x
```

— except that in Python nobody would write that, because in Python the
interesting part is the `print`, and here there is no such part.

---

## Lesson 2 — the same program, backwards

This is the whole reason the language exists, so meet it early. Take `single`
from `course.42`, which wraps a value into a one-element list:

```
$ 42 course single 7
single(7) =
  [7]
  -- 1 result

$ 42 course single '[7]' --backward
single!([7]) =
  7
  -- 1 result
```

`--backward` (or `-b`) runs the *same definition* the other way. Nobody wrote
`single!`. There is no second implementation to keep in sync; there is one
definition and two directions to read it.

Backwards is not always single-valued. `append` glues two lists together;
run it backwards and it must offer every way the seam could have been placed:

```
$ 42 course split '[1,2,3]'
split([1, 2, 3]) =
  ([1, 2, 3], [])
  ([1, 2], [3])
  ([1], [2, 3])
  ([], [1, 2, 3])
  -- 4 results
```

(`split` is literally `def split = append!`.) A 42 program returns a **set** of
answers. It may be empty, one, or many. Which of those you get is not a
language wart — it is information-theoretic, and Lesson 7 makes it precise.

---

## Lesson 3 — reading the output

Three surprises in the printer, all worth getting out of the way now.

**`{}` is a normal answer, not an error.** It means "this program does not
relate that input to anything."

```
$ 42 course palin '[1,2,3]'
palin([1, 2, 3]) =
  {}   (empty: no result)
```

`[1,2,3]` is not a palindrome, so `palin` — which keeps palindromes and rejects
everything else — has nothing to return. That is the answer.

**`0`, `[]`, and `false` are the same value.** All three are `L ()` (manual
§3.6). The printer picks a spelling from the type it inferred, and when it
cannot tell, it guesses `0`:

```
$ 42 course not 'L ()'
not(0) =
  R ()
  -- 1 result
```

You passed `L ()` meaning "false"; the printer had no type saying "boolean" so
it wrote your input as `0`. The answer `R ()` is "true". Nothing went wrong.

**A stray `L` or `R` on a result** usually means you used `+` and forgot the
`join` that drops the label afterwards (Lesson 7).

---

## Lesson 4 — reading a program: write the shape after every step

Before you can write one, you have to be able to read one, and there is exactly
one technique. **After every step, write down the shape of the value.** Do it
on paper the first few times.

Here is `single`:

```
def single = unitprod! ; swapprod ; (id * inl) ; inr
```

(`course.42` writes the last two steps as `(id * nil) ; cons` — Lesson 5
introduces those names. They are the same `inl` and `inr`.)

`;` is "then" — a pipe, left to right. Feed it `7` and annotate each stage.
These traces are short enough to write in raw terms; once they get longer you
annotate in the sugar instead (Lesson 5, Notation 1):

```
                          7
    unitprod!         ((), 7)          -- conjure a unit, pair it on the left
    swapprod          (7, ())          -- swap, so 7 is on the left
    id * inl          (7, L ())        -- turn the () into L (), i.e. []
    inr               R (7, L ())      -- add an R label: that is [7]
```

Result `[7]`. Now read it backwards — same steps, reverse order, each one
individually reversed:

```
                          [7]  =  R (7, L ())
    inr!              (7, L ())
    (id * inl)!       (7, ())
    swapprod!         ((), 7)
    unitprod!!        7
```

It unwraps a one-element list. Fed `[7, 8]`, the `inl!` step would look for an
`L` and find an `R`, produce nothing, and the whole run returns `{}` —
correctly, because `[7,8]` is not a one-element list.

Two primitives worth pinning down, because they come up constantly:

| Primitive | Forwards | Backwards (`!`) |
|---|---|---|
| `unitprod` | `((), a)` becomes `a` | `a` becomes `((), a)` — conjures a `()` |
| `inl` / `inr` | `a` becomes `L a` / `R a` | strips the label; wrong label gives `{}` |

`unitprod!` making a `()` out of nothing is allowed because `()` carries no
information — run it backwards and there was only ever one thing it could have
been. This is how you build structure in a language that cannot invent data.

---

## Lesson 5 — writing your first definition: peel the target

The method is three steps, and the third is the maze-solving one. But first,
two pieces of notation, because without them the maze is unreadable.

### Notation 1 — derive in the printer's sugar, not in raw terms

The four building blocks are all there is, but writing a value out in them is
hopeless past toy size:

```
5        is   R R R R R L ()
[1,2]    is   R (R L (), R (R R L (), L ()))
[1,2,3]  is   R (R L (), R (R R L (), R (R R R L (), L ())))
```

The interpreter prints the *sugared* form — `5`, `[1,2]`, `"text"` — for
exactly this reason (`--raw` shows you the tree if you ever want it). Derive in
the sugar too. You only ever need to know how each sugared shape opens up by
**one layer**:

| Sugar | is | opens to |
|---|---|---|
| `[]` — also `0`, also `false` | `L ()` | `nil` applied to `()` |
| `x : xs` — a non-empty list | `R (x, xs)` | `cons` applied to the pair `(x, xs)` |
| `n + 1` — a non-zero nat | `R n` | `succ` applied to `n` |
| `true` | `R ()` | `inr` applied to `()` |
| `(a, b)` | a pair | `a` and `b`, side by side |
| `L a` / `R a` | a labelled value | `a`, with its tag |

That table *is* the peel step. Everything below is applying it.

### Notation 2 — name the constructors

`cons`, `nil` and `succ` are exact aliases for `inr`, `inl` and `inr`:

```
def nil  = inl        -- ()      |->  []          (the same value as 0 and false)
def cons = inr        -- (h, t)  |->  h : t
def succ = inr        -- n       |->  n + 1
```

They compute nothing new — `cons` *is* `inr`. But reading `cons` in a
derivation says "a list cell is being built here"; reading `inr` says only "an
`R` label goes on." `course.42` defines all three, they cost nothing, and any
`.42` file may declare its own. From here on the derivations use them.

### Step 1 — write it pointwise, with names

Just write the Python.

```
single(x) = [x]
```

### Step 2 — write both shapes, in the sugar

The shape you start with and the shape you want. Two shapes, not one.

```
start:  x
want:   [x]
```

For `single` the start is a bare `x` and there is nothing to peel there. For
recursion (Lesson 9) the start has structure of its own, and then you peel
*both*.

### Step 3 — peel the target from the outside in

Strip one layer off `want` at a time, using the table above. Each layer you
strip names the **last** step of the pipeline, so you are building it
back-to-front. Stop when a layer leaves you holding a shape you already have.

- `[x]` is a non-empty list → outer layer is `cons`. **Last step: `cons`.**
  Before it, the value is the pair `(x, [])`.
- `(x, [])` is a pair. Its left half is `x` — already what you have. Its right
  half is `[]`, which is `nil` applied to `()`. So act on the right half only:
  **`id * nil`.** Before it, `(x, ())`.
- `(x, ())` is a pair: `x` on the left, `()` on the right. `unitprod!` makes
  `((), x)` out of `x`, and `swapprod` flips it. **`unitprod! ; swapprod`.**
  Before them, just `x`.
- `x` is the start. Stop.

Read the steps back-to-front — the order you found them, reversed:

```
def single = unitprod! ; swapprod ; (id * nil) ; cons
```

Run it:

```
$ 42 course single 7
single(7) =
  [7]
  -- 1 result
```

> **The habit:** peel the target from the outside in, in the sugar. Each layer
> names one constructor. You write the pipeline last-step-first, and you stop
> when you reach a shape you already hold.

### When peeling the target isn't enough

`single` closes from the target alone because its input is a bare `x` — there
was nothing to meet. When the input has structure — a pair, a labelled value —
the target peel runs out before it reaches the start, and what is left in the
middle is pure *rearrangement*: `swapprod`, `assocprod`, `dist`. Then you also
peel the **start** shape forward, and the plumbing is whatever joins the two
open ends. Lesson 9 does this in full; the thing to carry there is that the two
peels are independent, and you meet in the middle.

---

## Lesson 6 — acting on part of a value

The thing you keep wanting to do — *"take the second element and reverse it"* —
is the thing 42 forbids, because "take the second element" names a part of a
value and throws the rest away. Here is what you do instead.

`f * g` runs `f` on the left half of a pair and `g` on the right half, at the
same time, without either half being named:

```
     (a, b)
   f * g
     (f a, g b)
```

The two idioms you will use most:

```
id * g        -- leave the left half alone, apply g to the right
f  * id       -- apply f to the left half, leave the right alone
```

`id` is the do-nothing program. So:

```
$ 42 course wrapright '(1, 2)'
wrapright(1, 2) =
  (1, [2])
  -- 1 result
```

where `def wrapright = id * single`. The `1` is untouched; `single` ran on the
`2` only. There was never a moment where `2` was pulled out and named — the
pair kept its shape throughout.

Compare the Python, and notice what disappears:

```python
def wrapright(pair):
    a, b = pair          # <- this line has no 42 equivalent
    return (a, [b])
```

The unpacking line is exactly what `*` lets you skip. You do not take the pair
apart; you reach into the half you care about and leave the rest in place.

---

## Lesson 7 — choosing, and the recursion skeleton

A value that is "either this or that" wears a label: `L _` or `R _`. Choosing
is `f + g`:

```
     L a                        R b
   f + g                      f + g
     L (f a)                    R (g b)
```

If the label is `L`, run `f` on the contents; if `R`, run `g`. **Nothing is
tested.** The value is already in one branch; `+` acts inside whichever one
that is. This is why the backward direction has no branch-condition to
re-evaluate — there was no condition.

The label survives: `f + g` puts its result back inside `L` or `R`. Almost
always you then want to forget which branch you were in, and that is `join`:

```
(f + g) ; join        -- switch on the label, handle each case, drop the label
```

Booleans are the smallest example. `false` is `L ()`, `true` is `R ()`, so
negation is "move the value to the sibling branch" — which is a primitive,
`swapsum`:

```
def not = swapsum
```

```
$ 42 course not 'R ()'
not(R ()) =
  0
  -- 1 result
```

(`0` is `L ()` is `false`; see Lesson 3.)

### The skeleton

Recursive data in 42 is always "a base case, **or** something one step bigger"
— which is to say, a labelled value. So a recursive program is always a switch
on that label, and it always has this shape:

```
(base + step) ; join
```

- `base` handles `L …` — the empty list, zero, the leaf.
- `step` handles `R …` and calls the program on the smaller piece inside.
- `join` drops the label once a branch has produced its answer.

Every recursive definition in this course is a filled-in copy of that line.

---

## Lesson 8 — two arguments, and `dist`

42 programs take one value. "Two arguments" means one pair, `(x, y)`, and the
program takes the pair apart itself.

The snag: you want to switch on `x` — say `x` is the list you are recursing on —
but `f + g` needs a *labelled value*, and what you have is a *pair* whose first
component is labelled: `(L …, y)` or `(R …, y)`. `dist` is the adapter.

```
dist  turns  (L a, y)  into  L (a, y)
      and    (R b, y)  into  R (b, y)
```

It pushes the pairing inside the label, so **each branch still has `y` in
hand**. The two-argument skeleton is therefore:

```
dist ; (base + step) ; join
```

That one extra primitive at the front is the only structural difference
between one-argument and two-argument recursion.

---

## Lesson 9 — recursion, start to finish

Take `append`. Pointwise Python:

```python
def append(xs, ys):
    if xs == []:
        return ys
    h, t = xs        # xs is [h, *t]
    return [h] + append(t, ys)
```

Two arguments, switching on `xs`, so the skeleton is `dist ; (base + step) ; join`.

**Base branch.** After `dist`, the `L` branch holds `((), ys)` — the leftover
unit from the empty `xs`, paired with `ys`. We must return `ys`. That is
`unitprod` (drops the `()` on the left of a pair).

**Step branch.** This is the case where one peel is not enough (Lesson 5's last
section), so peel both ends.

*Peel the target.* After `dist`, the step branch must produce
`[h] + append(t, ys)`, which is `h : append(t, ys)`.

- outer layer is `cons` → **last step `cons`**; before it, the pair
  `(h, append(t, ys))`.
- a pair: left half `h` is untouched, right half is `append` applied to
  `(t, ys)` → **`id * append`**; before it, `(h, (t, ys))`.
- `(h, (t, ys))` opens no further into anything you have yet. **Stop.**

*Peel the start.* After `dist`, the step branch is handed `((h, t), ys)`.

- that is a pair nested on the left; the target peel wants it nested on the
  right, `(h, (t, ys))`. One regroup: **`assocprod!`**.

The two open ends — `((h, t), ys)` from the start, `(h, (t, ys))` for the
target — are joined by that single `assocprod!`. Reading the step branch
front-to-back: `assocprod! ; (id * append) ; cons`. The whole definition:

```
def append = dist ; (unitprod + (assocprod! ; (id * append) ; cons)) ; join
```

Run it, and trace the step case on `([1,2], [3])`, which is `(R (1, t), [3])`
with `t = [2]`:

```
                          (R (1, t), [3])
  dist                R ((1, t), [3])           -- pair pushed inside the label
  ── R branch, step runs on ((1, t), [3]):
    assocprod!            (1, (t, [3]))          -- regroup: meet the target peel
    id * append          (1, [2, 3])            -- recurse on the right half
    cons                 R (1, [2, 3])          -- build the list cell
  ── back out, still labelled:
                      R (R (1, [2,3]))
  join                    R (1, [2, 3])   =  [1, 2, 3]
```

```
$ 42 course append '([1,2], [3])'
append([1, 2], [3]) =
  [1, 2, 3]
  -- 1 result
```

Now the payoff. Run it backwards and the final `join` becomes the *first*
step. `join!` cannot know which label the answer carried, so it tries both —
at every level of the recursion. That is precisely why `append!` enumerates
every split:

```
$ 42 course append '[1,2,3]' --backward
append!([1, 2, 3]) =
  ([1, 2, 3], [])
  ([1, 2], [3])
  ([1], [2, 3])
  ([], [1, 2, 3])
  -- 4 results
```

> **Every time a 42 program gives you more than one answer, a `join` was run
> backwards.** Nothing else in the language multiplies answers.

---

## Lesson 10 — a test is just `copy` and `copy!`

A *test* (Python's `if predicate(x): return x`) is a relation that returns its
input unchanged or returns nothing. 42 has no special construct for it. You
build one from two primitives:

| Primitive | Forwards | Backwards (`!`) |
|---|---|---|
| `copy` | `a` becomes `(a, a)` | `(a, a)` becomes `a`; a pair whose halves **differ** becomes `{}` |

`copy!` is the whole trick: it succeeds only when the two halves are equal.
So "keep `x` if `P(x)`" is *duplicate, do something to one copy, demand the
copies still match*:

```
def palin = copy ; (id * rev) ; copy!
```

Duplicate the list; reverse the right copy; require the two copies to still be
equal.

```
$ 42 course palin '[1,2,1]'
palin([1, 2, 1]) =
  [1, 2, 1]
  -- 1 result

$ 42 course palin '[1,2,3]'
palin([1, 2, 3]) =
  {}   (empty: no result)
```

The same pattern gives you guards, range checks, "is this even" — anything of
the form "leave it alone if a condition holds."

---

## Lesson 11 — if-then-else

There is no `if`. What there is: `f | g` runs **both** `f` and `g` and pools
their answers. Normally that gives you two results. But if `f` and `g` are each
fronted by a guard (Lesson 10) and the two guards can *never both* succeed,
then on any input exactly one side produces anything, and the union collapses
to a deterministic choice:

```
(guard ; then)  |  (complement-of-guard ; else)
```

> **That is if-then-else in 42.** Making the two guards disjoint is your job,
> not the language's. Overlap them and you silently get two answers; leave a
> gap and you get none.

The course file has a toy example on lists — give an empty list back untouched,
otherwise reverse it:

```
def isnil    = inl! ; inl          -- returns an L-value unchanged, {} on an R
def nonempty = inr! ; inr          -- returns an R-value unchanged, {} on an L
def emptyOrReverse = (isnil ; id) | (nonempty ; rev)
```

`isnil` and `nonempty` cannot both fire — a value is `L` or `R`, never both —
so the `|` is a real conditional:

```
$ 42 course emptyOrReverse '[1,2,3]'
emptyOrReverse([1, 2, 3]) =
  [3, 2, 1]
  -- 1 result

$ 42 course emptyOrReverse '[]'
emptyOrReverse([]) =
  []
  -- 1 result
```

For a full worked conditional over byte values — flip the case of letters only,
leaving punctuation alone — see manual §10.5.

---

## Lesson 12 — one real program, checked

Put the method together on `rev`. Pointwise:

```python
def rev(xs):
    if xs == []:
        return []
    h, t = xs
    return rev(t) + [h]
```

One argument, switching on `xs`, so the skeleton is `(base + step) ; join` —
no `dist`, because there is no second argument to carry.

**Base branch** gets `()` (the empty list's payload) and must produce `[]`.
By the table in Lesson 5, `[]` is `nil` applied to `()` — so the base branch
is just `nil`.

**Step branch** gets `(h, t)` and must produce `rev(t) + [h]`, which is
`append(rev(t), [h])`. So the last step is `append`, and just before it the
value must be the pair `(rev(t), [h])`. Get there from `(h, t)`, writing the
shape after each move:

```
                     (h, t)
  id * rev           (h, rev t)          -- recurse on the tail
  swapprod           (rev t, h)          -- move the head to the right
  id * single        (rev t, [h])        -- wrap the head into a list
  append             rev t ++ [h]        -- glue
```

So the step branch is `(id * rev) ; swapprod ; (id * single) ; append`, and:

```
def rev = (nil + ((id * rev) ; swapprod ; (id * single) ; append)) ; join
```

Run it:

```
$ 42 course rev '[1,2,3]'
rev([1, 2, 3]) =
  [3, 2, 1]
  -- 1 result
```

Now check it. `42 law` runs the program forwards, then runs each answer
backwards, and confirms the original input is among the preimages:

```
$ 42 law course rev '[1,2,3]'
rev([1, 2, 3]) has 1 result(s)
  [ok ] [3, 2, 1]: inv has 1 preimage(s), input in it
law holds
```

And `42 show` prints what the reverse actually is — you never wrote it, so it
is worth looking at:

```
$ 42 show course rev
rev   = nil + (id * rev ; swapprod ; id * single ; append) ; join
rev!  = join! ; nil! + (append! ; (id! * single! ; (swapprod! ; id! * rev!)))
```

(`nil!` there is `inl!` — the reverse strips the tag it built, and fails on a
non-empty list, which is how the base case rejects.)

`42 type` will tell you the shapes it inferred, which is the fastest way to
find a definition whose two ends do not line up:

```
$ 42 type course emptyOrReverse
emptyOrReverse  : list a <-> list a
```

---

## Lesson 13 — when the shapes fight back

You will spend most of your first week getting `{}` when you wanted an answer.
The causes, in order of how often they bite:

**1. Shape mismatch.** A primitive got the wrong shape — `swapprod` on a
non-pair, `unitprod` on a pair without a `()` on its left, `assocprod` where
the nesting was `((a,b),c)` and it wanted `(a,(b,c))`. The command line
type-checks first and refuses an argument that cannot fit, but a mismatch
*inside* a definition still just yields `{}`. Fix: `42 type course NAME` for
each piece, or walk the pipeline writing shapes (Lesson 4) until the shape you
wrote stops matching the primitive's table entry.

**2. A label went the wrong way.** `inl!` on an `R` value is `{}`, by design —
that is how case analysis rejects a branch.

**3. `copy!` on a mismatched pair.** It only succeeds when the halves are equal
(Lesson 10). If a test always returns `{}`, check what you did to the copy.

**4. Missing `dist`.** You wrote `(f + g)` where the value is a *pair* with a
labelled first component, not a labelled value. `+` needs a label on the
outside. Insert `dist` (Lesson 8).

**5. A stray `L` or `R` on the result.** The opposite problem: you used `+` and
forgot the `join`.

**6. Too many answers backwards.** Not a bug — every extra answer is a `join`
that ran in reverse (Lesson 9). If you want fewer, make the forward direction
destroy less: `copy` before an operation and `copy!` after is the standard
move. `double = copy ; add` reversed has at most one answer where `add!` alone
had many.

```
$ 42 course double 7 --backward
double!(7) =
  {}   (empty: no result)
```

Seven is odd, so there is no `n` with `n + n = 7`, and `copy!` rejects every
candidate `add!` offered.

---

## Appendix: a Python-idiom to 42-move phrasebook

| You want to… | In Python | In 42 |
|---|---|---|
| return the input unchanged | `return x` | `id` |
| name and use one input | `def f(x): …` | you cannot — go point-free |
| take two inputs | `def f(x, y): …` | one pair `(x, y)`; take it apart yourself |
| unpack a pair | `a, b = p` | you cannot — reach in with `f * g` |
| act on the second half only | `(a, g(b))` | `id * g` |
| act on the first half only | `(f(a), b)` | `f * id` |
| swap a pair | `(b, a)` | `swapprod` |
| regroup a pair | `(a, (b, c))` ↔ `((a, b), c)` | `assocprod` / `assocprod!` |
| build `[x]` | `[x]` | `unitprod! ; swapprod ; (id * nil) ; cons` (`single`) |
| an empty list / zero / false | `[]` / `0` / `False` | `L ()` — the same value for all three; built by `nil` |
| a cons cell | `[h, *t]` | `R (h, t)` — built by `cons` from `(h, t)` |
| a successor | `n + 1` | `R n` — built by `succ` from `n` |
| tag a value left / right | — | `inl` / `inr` (or `nil` / `cons` / `succ`, the named aliases) |
| `match` on a two-case value | `if tag == L: … else: …` | `(f + g) ; join` |
| drop the tag after a match | (implicit) | `join` |
| switch on the first of a pair | `if xs == []: …` | `dist ; (f + g) ; join` |
| duplicate a value | `x, x` | `copy` |
| assert two things are equal | `assert a == b` | `copy!` (on the pair `(a, b)`) |
| `if P(x): return x` | a guard | `copy ; (id * work) ; copy!` |
| if-then-else | `if C: a else: b` | `(guard ; a) \| (not-guard ; b)`, guards disjoint |
| genuine nondeterminism | — | `f \| g` |
| repeat until nothing new | `while` / fixpoint | `f^` |
| the inverse of `f` | write it by hand, keep in sync | `f!` — free, always |
| run `f` backwards, once | — | `--backward` on the command line |

### Opening a sugared shape by one layer (the peel table)

| Sugar | is | opens to |
|---|---|---|
| `[]` / `0` / `false` | `L ()` | `nil` on `()` |
| `x : xs` | `R (x, xs)` | `cons` on `(x, xs)` |
| `n + 1` | `R n` | `succ` on `n` |
| `true` | `R ()` | `inr` on `()` |
| `(a, b)` | a pair | `a`, `b` side by side |
| `L a` / `R a` | a labelled value | `a` with its tag |

Binding strength, loosest first: `|` then `;` then `+` then `*` then `!` `^`.
So `a ; b + c ; d` parses as `a ; (b + c) ; d`, and `f * g!` is `f * (g!)`.

The thirteen primitives — `id`, `zero`, `swapprod`, `assocprod`, `unitprod`,
`swapsum`, `assocsum`, `unitsum`, `inl`, `inr`, `join`, `copy`, `dist` — plus
`!` on any of them, are the entire vocabulary. `nil`, `cons` and `succ` are not
new primitives; they are one-line aliases (`inl`, `inr`, `inr`) that a `.42`
file declares for readability. Everything else is built from the thirteen with
the six combiners above.

---

*Next: [the manual](MANUAL.md) proper — §10 for more recursion, §11 for
arithmetic, §13–§14 for a Turing machine and 42 interpreting itself.*
