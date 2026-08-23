#!/usr/bin/env python3
"""Render the project's Markdown into standalone HTML.

    python3 tools/render.py

Writes one docs/*.html per entry in DOCS.  No dependencies: the Markdown
subset used by these documents is small and fixed, so a converter for exactly
that subset is shorter and more predictable than a general one.

Heading slugs follow GitHub's rule, so the tables of contents already written
into the Markdown keep working.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"


# ---------------------------------------------------------------------------
# Inline markup.  Code spans are lifted out first and put back last, so that a
# `*` or `_` inside one is never mistaken for emphasis.
# ---------------------------------------------------------------------------


def inline(text: str) -> str:
    spans: list[str] = []

    def stash(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # `<https://…>` is Markdown's autolink.  The escaping above has already
    # turned the brackets into entities, so match those: without this the
    # bibliography's URLs render as literal text with `&lt;` around them.
    text = re.sub(
        r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1">\1</a>', text
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(
        r"\x00(\d+)\x00",
        lambda m: f"<code>{html.escape(spans[int(m.group(1))], quote=False)}</code>",
        text,
    )


def slug(text: str) -> str:
    """GitHub's heading slug: the links already in the Markdown depend on it."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)      # drops punctuation, keeps the spaces
    return re.sub(r"[\s_]", "-", text.strip()).strip("-")


# ---------------------------------------------------------------------------
# Block markup.
# ---------------------------------------------------------------------------


def render(md: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Return the body HTML and a flat table of contents."""
    lines = md.split("\n")
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # fenced code -------------------------------------------------------
        if line.startswith("```"):
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            code = html.escape("\n".join(body), quote=False)
            out.append(f'<div class="code"><pre><code>{code}</code></pre></div>')
            continue

        # heading -----------------------------------------------------------
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            anchor = slug(text)
            if level in (2, 3):
                toc.append((level, anchor, re.sub(r"`", "", text)))
            out.append(
                f'<h{level} id="{anchor}">'
                f'<a class="anchor" href="#{anchor}" aria-label="Link to this section">#</a>'
                f"{inline(text)}</h{level}>"
            )
            i += 1
            continue

        # horizontal rule ---------------------------------------------------
        if re.match(r"^-{3,}\s*$", line):
            out.append('<hr aria-hidden="true">')
            i += 1
            continue

        # table -------------------------------------------------------------
        if line.startswith("|") and i + 1 < len(lines) and re.match(
            r"^\|[\s:|-]+\|?\s*$", lines[i + 1]
        ):
            def cells(row: str) -> list[str]:
                # `\|` is an escaped pipe, not a column separator -- without
                # this, a cell containing `|P(y)|` silently becomes three cells
                # and the table renders with a ragged header.
                out, cell = [], ""
                it = iter(range(len(row := row.strip().strip("|"))))
                for i in it:
                    if row[i] == "\\" and i + 1 < len(row) and row[i + 1] == "|":
                        continue
                    if row[i] == "|" and (i == 0 or row[i - 1] != "\\"):
                        out.append(cell.strip())
                        cell = ""
                    else:
                        cell += row[i]
                out.append(cell.strip())
                return out

            head = cells(line)
            i += 2
            body_rows = []
            while i < len(lines) and lines[i].startswith("|"):
                body_rows.append(cells(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            trs = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                for r in body_rows
            )
            head_html = f"<thead><tr>{th}</tr></thead>" if any(head) else ""
            out.append(
                f'<div class="scroller"><table>{head_html}<tbody>{trs}</tbody>'
                f"</table></div>"
            )
            continue

        # blockquote --------------------------------------------------------
        if line.startswith(">"):
            body = []
            while i < len(lines) and lines[i].startswith(">"):
                body.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(body))}</p></blockquote>")
            continue

        # lists -------------------------------------------------------------
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            ordered = bool(re.match(r"\d+\.", m.group(2)))
            items: list[str] = []
            while i < len(lines):
                m2 = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not m2 or bool(re.match(r"\d+\.", m2.group(2))) != ordered:
                    # a continuation line belongs to the item above it
                    if items and lines[i].startswith("  ") and lines[i].strip():
                        items[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                items.append(m2.group(3))
                i += 1
            tag = "ol" if ordered else "ul"
            lis = "".join(f"<li>{inline(x)}</li>" for x in items)
            out.append(f"<{tag}>{lis}</{tag}>")
            continue

        # paragraph ---------------------------------------------------------
        if line.strip():
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|```|>|\||\s*([-*]|\d+\.)\s|-{3,}\s*$)", lines[i]
            ):
                para.append(lines[i].strip())
                i += 1
            if para:
                out.append(f"<p>{inline(' '.join(para))}</p>")
                continue

        i += 1

    return "\n".join(out), toc


# ---------------------------------------------------------------------------
# The page.
# ---------------------------------------------------------------------------

CSS = """
:root {
  --paper:      #fcfcfd;
  --raised:     #f4f6f8;
  --ink:        #16191f;
  --muted:      #5c6470;
  --faint:      #8b93a1;
  --rule:       #e2e5ea;
  --accent:     #0b6e6e;
  --accent-dim: #0b6e6e1a;
  --shadow:     0 1px 2px #16191f0d;
  --serif: "Iowan Old Style", "Charter", "Palatino Linotype", Palatino,
           "Book Antiqua", Georgia, serif;
  --mono:  ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas,
           "Cascadia Mono", "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #101317; --raised: #171b21; --ink: #e6e9ee; --muted: #98a2b0;
    --faint: #6d7788; --rule: #262c35; --accent: #4fd1c5;
    --accent-dim: #4fd1c522; --shadow: 0 1px 2px #00000040;
  }
}
:root[data-theme="dark"] {
  --paper: #101317; --raised: #171b21; --ink: #e6e9ee; --muted: #98a2b0;
  --faint: #6d7788; --rule: #262c35; --accent: #4fd1c5;
  --accent-dim: #4fd1c522; --shadow: 0 1px 2px #00000040;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 1.5rem; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.62;
  -webkit-font-smoothing: antialiased;
}

/* ---- shell ---- */
.shell { display: grid; grid-template-columns: 16.5rem minmax(0, 1fr); gap: 3.5rem;
         max-width: 74rem; margin: 0 auto; padding: 0 2rem; align-items: start; }
@media (max-width: 60rem) {
  .shell { grid-template-columns: minmax(0, 1fr); gap: 0; padding: 0 1.25rem; }
}

/* ---- masthead ---- */
.mast { display: flex; flex-direction: column; gap: .5rem;
        padding: 2.75rem 0 1.5rem; border-bottom: 1px solid var(--rule);
        grid-column: 1 / -1; }
.mark { font-family: var(--mono); font-size: .8rem; letter-spacing: .12em;
        text-transform: uppercase; color: var(--accent); }
.mark b { font-weight: 500; }
.mast h1 { margin: 0; font-size: 2.1rem; line-height: 1.15; letter-spacing: -.015em;
           text-wrap: balance; font-weight: 600; }
.mast p { margin: 0; color: var(--muted); max-width: 46ch; }
.switch { display: flex; gap: .4rem; margin-top: .85rem; flex-wrap: wrap; }
.switch a { font-family: var(--mono); font-size: .78rem; letter-spacing: .02em;
            text-decoration: none; color: var(--muted); border: 1px solid var(--rule);
            border-radius: 2px; padding: .3rem .65rem; background: var(--paper); }
.switch a:hover { color: var(--accent); border-color: var(--accent); }
.switch a[aria-current="page"] { color: var(--paper); background: var(--ink);
                                 border-color: var(--ink); }

/* ---- table of contents ---- */
.rail { position: sticky; top: 1.5rem; max-height: calc(100vh - 3rem);
        overflow-y: auto; padding: 2rem 0 3rem; font-family: var(--mono);
        font-size: .8rem; line-height: 1.5; }
.rail h2 { font-size: .72rem; letter-spacing: .12em; text-transform: uppercase;
           color: var(--faint); margin: 0 0 .9rem; font-family: var(--mono);
           font-weight: 500; }
.rail ol { list-style: none; margin: 0; padding: 0;
           display: flex; flex-direction: column; gap: .12rem; }
.rail a { display: block; text-decoration: none; color: var(--muted);
          padding: .2rem .55rem; border-left: 2px solid transparent;
          border-radius: 0 2px 2px 0; }
.rail a:hover { color: var(--ink); background: var(--raised); }
.rail a.sub { padding-left: 1.5rem; color: var(--faint); font-size: .76rem; }
.rail a.here { color: var(--accent); border-left-color: var(--accent);
               background: var(--accent-dim); }
@media (max-width: 60rem) {
  .rail { position: static; max-height: none; border-bottom: 1px solid var(--rule);
          padding: 1.25rem 0; }
  .rail ol { display: grid; grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); }
  .rail a.sub { display: none; }
}

/* ---- prose ---- */
main { padding: 2rem 0 6rem; min-width: 0; max-width: 68ch; }
main > :first-child { margin-top: 0; }
h1, h2, h3, h4 { line-height: 1.22; letter-spacing: -.012em; text-wrap: balance;
                 font-weight: 600; position: relative; }
h1 { font-size: 1.9rem; margin: 3rem 0 1rem; }
h2 { font-size: 1.5rem; margin: 3.25rem 0 1rem; padding-bottom: .4rem;
     border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.15rem; margin: 2.25rem 0 .75rem; }
h4 { font-size: 1rem; margin: 1.75rem 0 .6rem; color: var(--muted); }
p { margin: 0 0 1.05rem; }
a { color: var(--accent); text-underline-offset: .18em;
    text-decoration-thickness: .06em; }
strong { font-weight: 650; }
ul, ol { margin: 0 0 1.05rem; padding-left: 1.35rem;
         display: flex; flex-direction: column; gap: .38rem; }
li { padding-left: .15rem; }
li::marker { color: var(--faint); }
hr { border: 0; height: 1px; background: var(--rule); margin: 2.75rem 0; }

.anchor { position: absolute; left: -1.1rem; width: 1.1rem; text-align: left;
          color: var(--faint); text-decoration: none; opacity: 0;
          font-family: var(--mono); font-weight: 400; }
h2:hover .anchor, h3:hover .anchor, h4:hover .anchor, .anchor:focus { opacity: 1; }
@media (max-width: 60rem) { .anchor { display: none; } }

blockquote { margin: 1.4rem 0; padding: .1rem 0 .1rem 1.15rem;
             border-left: 2px solid var(--accent); color: var(--muted); }
blockquote p { margin: 0; }

/* ---- code ---- */
code { font-family: var(--mono); font-size: .855em; }
p code, li code, td code, th code, blockquote code, h2 code, h3 code, h4 code {
  background: var(--raised); border: 1px solid var(--rule);
  border-radius: 3px; padding: .07em .32em; white-space: nowrap;
}
.code { margin: 0 0 1.3rem; background: var(--raised);
        border: 1px solid var(--rule); border-radius: 4px;
        overflow-x: auto; box-shadow: var(--shadow); }
.code pre { margin: 0; padding: .95rem 1.15rem; }
.code code { background: none; border: 0; padding: 0; white-space: pre;
             font-size: .83rem; line-height: 1.58; }

/* ---- tables ---- */
.scroller { overflow-x: auto; margin: 0 0 1.4rem; }
table { border-collapse: collapse; width: 100%; font-size: .9rem;
        font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: .5rem .8rem; border-bottom: 1px solid var(--rule);
         vertical-align: top; }
th { font-family: var(--mono); font-size: .74rem; letter-spacing: .06em;
     text-transform: uppercase; color: var(--faint); font-weight: 500;
     border-bottom-color: var(--ink); }
tbody tr:last-child td { border-bottom: 0; }

:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px;
                 border-radius: 2px; }
"""

SCRIPT = """
const links = [...document.querySelectorAll('.rail a')];
const byId = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
const seen = new Set();
const spy = new IntersectionObserver(entries => {
  for (const e of entries) e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id);
  const order = [...byId.keys()].filter(id => seen.has(id));
  links.forEach(a => a.classList.remove('here'));
  const active = byId.get(order[0]);
  if (active) active.classList.add('here');
}, { rootMargin: '0px 0px -70% 0px' });
document.querySelectorAll('h2[id], h3[id]').forEach(h => spy.observe(h));
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{blurb_plain}">
<style>{css}</style>
</head>
<body>
<div class="shell">
  <header class="mast">
    <div class="mark"><b>42</b> &nbsp;x &isin; P(y) &nbsp;&harr;&nbsp; y &isin; inv(P)(x)</div>
    <h1>{heading}</h1>
    <p>{blurb}</p>
    <nav class="switch">{switch}</nav>
  </header>
  <nav class="rail" aria-label="Contents">
    <h2>Contents</h2>
    <ol>{toc}</ol>
  </nav>
  <main>{body}</main>
</div>
<script>{script}</script>
</body>
</html>
"""


#: A document links to its siblings by file name -- `[...](QMANUAL.md)` -- which
#: is right in the repository and a 404 on the site.  Rewrite the ones that have
#: a page here to that page, and send the rest to the source on GitHub.
SITE_PAGE = {
    "MANUAL.md": "manual.html",
    "QMANUAL.md": "qmanual.html",
    "RELATED.md": "related.html",
    "THEOREM.md": "theorem.html",
}


def target_for(name: str) -> str:
    """Where a reference to a file in the repository should point."""
    return SITE_PAGE.get(name, f"{REPO}/blob/main/{name}")


def relink(body: str) -> str:
    """Point a link at the published page for its target.

    The site is meant to stand on its own, so the documents name each other in
    prose rather than by file name; what is left to rewrite is the handful of
    real links between them.  A link to a file with no page here falls back to
    the source on GitHub.
    """
    def fix(m: re.Match) -> str:
        anchor = m.group(2) or ""
        return f'href="{target_for(m.group(1))}{anchor}"'

    return re.sub(r'href="([\w.-]+\.(?:md|42|py|tex|bib))(#[\w-]*)?"', fix, body)


def page(title: str, heading: str, blurb: str, body: str, toc, current: str) -> str:
    items = "".join(
        f'<li><a class="{"sub" if lvl == 3 else ""}" href="#{a}">{html.escape(t)}</a></li>'
        for lvl, a, t in toc
        if t.lower() != "contents"
    )
    # Absolute, so the two pages cross-link both as local files and as the
    # published copies, which live at unrelated URLs.
    tabs = [
        (HOSTED["index.html"], "home"),
        (HOSTED["manual.html"], "42 manual"),
        (HOSTED["qmanual.html"], "Q42 manual"),
        (HOSTED["related.html"], "related work"),
        (HOSTED["theorem.html"], "the theorem"),
        (REPO, "source"),
    ]
    def tab(href: str, label: str) -> str:
        mark = ' aria-current="page"' if href == current else ""
        return f'<a href="{href}"{mark}>{label}</a>'

    switch = "".join(tab(h, l) for h, l in tabs)
    return PAGE.format(
        title=title, heading=heading, blurb=blurb, body=relink(body),
        blurb_plain=html.escape(re.sub(r"&[a-z]+;", "", blurb), quote=True),
        toc=items, switch=switch, css=CSS, script=SCRIPT,
    )


#: The site is served from this directory, so the pages link to each other by
#: file name and work identically opened locally and published on Pages.
HOSTED = {
    "index.html":   "index.html",
    "manual.html":  "manual.html",
    "qmanual.html": "qmanual.html",
    "related.html": "related.html",
    "theorem.html": "theorem.html",
}

REPO = "https://github.com/ubrowz/42"

DOCS = [
    (
        "MANUAL.md", "manual.html", "42 Manual",
        "42 &mdash; User Manual",
        "A ground-up guide to a programming language whose programs run in two "
        "directions. No prior knowledge of reversible computing is assumed.",
    ),
    (
        "QMANUAL.md", "qmanual.html", "Q42 Manual",
        "Q42 &mdash; User Manual",
        "The same language over the complex numbers, which makes it a quantum "
        "one. The physics is developed from scratch, and the parts Q42 does not "
        "model are named as such.",
    ),
    (
        "RELATED.md", "related.html", "42 Related Work",
        "42 &mdash; Related Work",
        "Where 42 sits in the literature on reversible programming: what it "
        "shares with Inv, PisoLang and the &Pi; branch, what in it is new, and "
        "what the others have that it does not.",
    ),
    (
        "THEOREM.md", "theorem.html", "42 Expressiveness Theorem",
        "42 &mdash; What 42 Can Compute",
        "A proof that the relations denotable in 42 are exactly the recursively "
        "enumerable ones, with Turing completeness as the single-valued case.",
    ),
]



# ---------------------------------------------------------------------------
# The landing page.  Hand-written rather than rendered from Markdown: it is the
# one page whose job is orientation rather than prose, so it needs a layout the
# document template does not have.  It shares the stylesheet, so the site stays
# one design.
# ---------------------------------------------------------------------------

HOME_CSS = """
body.home { font-size: 17px; }
.home .shell { display: block; max-width: 62rem; }
.home main { max-width: none; padding: 0 0 5rem; }

.hero { padding: 4.5rem 0 2.5rem; border-bottom: 1px solid var(--rule); }
.hero .mark { font-family: var(--mono); font-size: .8rem; letter-spacing: .12em;
              text-transform: uppercase; color: var(--accent); }
.hero h1 { font-size: clamp(2.2rem, 5.5vw, 3.2rem); margin: .7rem 0 0;
           letter-spacing: -.022em; max-width: 20ch; }
.hero .lede { font-size: 1.14rem; color: var(--muted); max-width: 56ch;
              margin: 1.1rem 0 0; }
.law { display: inline-block; font-family: var(--mono); font-size: 1rem;
       margin: 1.8rem 0 0; padding: .75rem 1.1rem; background: var(--raised);
       border: 1px solid var(--rule); border-radius: 4px; color: var(--ink);
       box-shadow: var(--shadow); overflow-x: auto; max-width: 100%; }
.law b { color: var(--accent); font-weight: 500; }

.eyebrow { font-family: var(--mono); font-size: .72rem; letter-spacing: .12em;
           text-transform: uppercase; color: var(--faint); margin: 3.25rem 0 1.1rem;
           font-weight: 500; }

.cards { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); }
.card { display: block; text-decoration: none; color: inherit; background: var(--raised);
        border: 1px solid var(--rule); border-radius: 5px; padding: 1.5rem 1.6rem;
        box-shadow: var(--shadow); transition: border-color .12s, transform .12s; }
.card:hover { border-color: var(--accent); transform: translateY(-1px); }
.card h3 { margin: 0; font-size: 1.3rem; letter-spacing: -.015em; }
.card .kicker { font-family: var(--mono); font-size: .72rem; letter-spacing: .1em;
                text-transform: uppercase; color: var(--accent); }
.card p { margin: .6rem 0 0; color: var(--muted); font-size: .95rem; }
.card .more { display: block; margin-top: 1rem; font-family: var(--mono);
              font-size: .78rem; color: var(--accent); }

.minor { display: grid; gap: .55rem; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); }
.minor a { text-decoration: none; color: inherit; border: 1px solid var(--rule);
           border-radius: 4px; padding: .85rem 1.05rem; background: var(--paper);
           display: block; }
.minor a:hover { border-color: var(--accent); }
.minor b { display: block; font-weight: 600; }
.minor span { color: var(--muted); font-size: .88rem; }

.split { display: grid; gap: 2rem; grid-template-columns: repeat(auto-fit, minmax(21rem, 1fr));
         align-items: start; }
.split p { color: var(--muted); }
.split h3 { margin-top: 0; }

.tree { font-family: var(--mono); font-size: .8rem; line-height: 1.75; }
.tree dt { color: var(--accent); }
.tree dd { margin: 0 0 .5rem; color: var(--muted); }

footer.site { border-top: 1px solid var(--rule); margin-top: 3.5rem; padding: 1.75rem 0 3rem;
              display: flex; flex-wrap: wrap; gap: .4rem 1.5rem; align-items: baseline;
              font-family: var(--mono); font-size: .78rem; color: var(--faint); }
footer.site a { color: var(--muted); text-decoration: none; }
footer.site a:hover { color: var(--accent); }
"""

HOME = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>42 &mdash; a language that runs in two directions</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="42 is a point-free reversible programming language interpreted in Rel, the category of sets and relations. Q42 is the same language over the complex numbers, which makes it a quantum one.">
<style>{css}{home_css}</style>
</head>
<body class="home">
<div class="shell">
  <main>
    <header class="hero">
      <div class="mark">42 &amp; Q42</div>
      <h1>A programming language whose programs run in two directions</h1>
      <p class="lede">A program in 42 denotes a <em>relation</em> rather than a
      function. Run it forwards and it computes. Run the same definition
      backwards and it gives you every input the answer could have come from,
      without your having written that direction yourself.</p>
      <div class="law">x &isin; P(y) &nbsp;<b>&harr;</b>&nbsp; y &isin; inv(P)(x)</div>
      <nav class="switch" style="margin-top:1.6rem">
        <a href="manual.html">42 manual</a>
        <a href="qmanual.html">Q42 manual</a>
        <a href="{repo}">source on GitHub</a>
      </nav>
    </header>

    <p class="eyebrow">Start here</p>
    <div class="cards">
      <a class="card" href="manual.html">
        <div class="kicker">The language</div>
        <h3>42 &mdash; User Manual</h3>
        <p>A guide from the ground up, assuming no prior knowledge of
        reversible computing. Thirteen primitives and seven ways of combining
        them, then worked programs: arithmetic, exact rationals, text, and a
        Turing machine.</p>
        <span class="more">Read the manual &rarr;</span>
      </a>
      <a class="card" href="qmanual.html">
        <div class="kicker">The quantum one</div>
        <h3>Q42 &mdash; User Manual</h3>
        <p>The same language with complex numbers in place of set membership,
        which is enough to make it quantum. The physics is developed from
        scratch, and the manual is explicit about what Q42 does not model.</p>
        <span class="more">Read the manual &rarr;</span>
      </a>
    </div>

    <p class="eyebrow">In one minute</p>
    <div class="split">
      <div>
        <div class="code"><pre><code>$ 42 prelude add "(2, 3)"
add(2, 3) =
  5
  -- 1 result

$ 42 prelude add 5 --backward
add!(5) =
  (0, 5)
  (1, 4)
  (2, 3)
  (3, 2)
  (4, 1)
  (5, 0)
  -- 6 results</code></pre></div>
      </div>
      <div>
        <h3>The same definition, both ways</h3>
        <p>Forwards, <code>add</code> is a function. Backwards, it lists every
        pair that sums to 5. You do not write that second direction or any
        search to go with it: it is the <em>dagger</em> of the first, computed
        from the definition you already gave.</p>
        <p>Q42 runs the same machinery over the complex numbers, where it
        produces quantum circuits and <code>!</code> is the adjoint
        <code>&dagger;</code> instead of the converse.</p>
        <div class="code"><pre><code>$ 42q gates hh "|0&gt;"
hh |0&gt;
  = |0&gt;</code></pre></div>
      </div>
    </div>

    <p class="eyebrow">Going deeper</p>
    <div class="minor">
      <a href="theorem.html"><b>What 42 can compute</b>
        <span>A proof that the relations 42 can denote are the recursively
        enumerable ones.</span></a>
      <a href="related.html"><b>Related work</b>
        <span>Where 42 sits among Inv, PisoLang, Janus, RFUN and the
        &Pi; branch.</span></a>
    </div>

    <p class="eyebrow">Running it</p>
    <div class="split">
      <div>
        <p>Python 3.12 or later, and nothing else. Clone the repository and the
        two interpreters are scripts in its root.</p>
        <div class="code"><pre><code>$ git clone {repo}.git
$ cd 42
$ ./42 tour swap "(1, 2)"
$ ./42q gates bell "|00&gt;"</code></pre></div>
        <p>The repository holds both interpreters, the OpenQASM&nbsp;3 emitter
        and a separate circuit simulator to check it against, the example
        libraries the manuals draw on, and a test suite that re-runs the claims
        the documentation makes.</p>
      </div>
      <div>
        <dl class="tree">
          <dt>rel42/</dt><dd>the 42 interpreter: values, terms, types, dagger</dd>
          <dt>q42/</dt><dd>the same over &#8450;, plus the OpenQASM 3 emitter</dd>
          <dt>*.42</dt><dd>libraries: arithmetic, rationals, text, a Turing machine</dd>
          <dt>tools/</dt><dd>the renderer for this site, and a circuit simulator</dd>
          <dt>tests/</dt><dd>one of which executes every transcript in the manuals</dd>
        </dl>
      </div>
    </div>

    <footer class="site">
      <span>MIT licensed</span>
      <a href="{repo}">github.com/ubrowz/42</a>
      <span>x &isin; P(y) &harr; y &isin; inv(P)(x)</span>
    </footer>
  </main>
</div>
</body>
</html>
"""


def home() -> str:
    return HOME.format(css=CSS, home_css=HOME_CSS, repo=REPO)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for src, dest, title, heading, blurb in DOCS:
        md = (ROOT / src).read_text(encoding="utf-8")
        # The first heading and the hand-written Contents list become the
        # masthead and the rail, so drop them from the body.
        md = re.sub(r"\A#\s+.*?\n", "", md, count=1)
        md = re.sub(r"^## Contents\n(?:.*\n)*?\n(?=---|\#\#)", "", md, flags=re.M)
        body, toc = render(md)
        (OUT / dest).write_text(
            page(title, heading, blurb, body, toc, dest), encoding="utf-8"
        )
        print(f"  {src:12} -> docs/{dest}  ({len(toc)} sections)")
    (OUT / "index.html").write_text(home(), encoding="utf-8")
    # GitHub Pages runs Jekyll unless told not to, which would swallow any file
    # whose name begins with an underscore.
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print("  (landing)    -> docs/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
