# LNCS source

`paper.tex` is the draft in Springer LNCS format, with `refs.bib` for the
bibliography. It needs `llncs.cls` (v2.26, 25-Feb-2025) and `splncs04.bst`,
which are Springer's own files and are not redistributed here: take them from
CTAN (<https://ctan.org/pkg/llncs>) into this directory, or build on Overleaf,
where the LNCS class is installed already.

```sh
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

**Status: compiles.** Built on Overleaf with no errors and one warning, *Package
amsmath Warning: Unable to redefine math accent \vec*, which is benign — llncs
deliberately defines `\vec` as bold rather than as an arrow accent, and amsmath
cannot override it. Nothing in the source uses `\vec`.

**Length: it fits.** 16 pages in total with the references beginning midway down
page 15, so the body is under the 15-page limit, which excludes references. There
is roughly half a page of headroom — enough for a real author block, not much
more.

## Choices worth knowing

- `\documentclass[runningheads,envcountsame]{llncs}`. **`envcountsame` puts every
  result on one counter**, which is what the text assumes when it refers to
  "Proposition 1 … Theorem 3" across section boundaries.
- Packages are kept to `fontenc`, `inputenc`, `amsmath`, `amssymb` and
  `listings` — all in any TeX Live — so nothing needs installing. In particular
  the inference rules are drawn with a local `\rul` macro built from `\dfrac`
  rather than `mathpartir`, and the denotation brackets are a local `\den` macro
  rather than `stmaryrd`.
- Code and semantic clauses are `lstlisting`, in ASCII. The denotation figure
  writes `[[t]]` for the brackets and `u` for union, because it is verbatim.
- **Widths are budgeted, not guessed.** LNCS `\textwidth` is 122mm = 346.4pt. At
  `\footnotesize`, `cmtt` gives 4pt per character, so about 86 fit on a line; no
  listing line exceeds 80. `xleftmargin` is deliberately unset — it costs width
  the listings have none of to spare. Figure 1 is `\footnotesize` rather than
  `\small` for the same reason: at `\small` its four columns come to 343.5pt
  against 346.4pt available, which is too close to trust. The related-work table
  gives its language column a fixed `p{5.8cm}` so the list wraps instead of
  running off the page.
- The combinators are given as a table rather than a grammar, because the union
  operator and BNF alternation are both `|`.

## Still to do

- `[AUTHORS]` in `paper.tex`: the author block is a placeholder. The 1993 language
  is credited to Joep Rous and Paul Jansen, and the paper listed as forthcoming in
  that thesis was to be joint; whether this paper is single- or joint-authored is
  not a decision the draft makes.
- No trimming needed, but the margin is thin. If anything is added, cut related
  work to 1.5pp first, then the simulation in Sec. 5.
- The bibliography is deliberately complete rather than trimmed, since references
  are not counted against the limit.
