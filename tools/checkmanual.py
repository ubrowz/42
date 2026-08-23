#!/usr/bin/env python3
"""Check that every result the manual claims is the result you actually get.

    python3 tools/checkmanual.py

The manual states results in two shorthands:

    $ inl!  applied to  L ()   ->  ()
    $ add(2, 3)  =  5
    $ add!(5)    =  (0, 5)  (1, 4)  (2, 3)

Both are parsed out of MANUAL.md and re-run.  This is deliberately not a
transcription into a test file: a transcription drifts when the manual is
edited and nobody notices, whereas this reads whatever the manual currently
says.
"""

from __future__ import annotations

import glob
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rel42 import parse_program, parse_value, run, show  # noqa: E402
from rel42.core import Ref, Rel42Error, dagger, expand_env  # noqa: E402
from rel42.syntax import parse_term  # noqa: E402

LIBS = {}
for path in sorted(glob.glob(str(ROOT / "*.42"))):
    LIBS[os.path.basename(path)] = expand_env(
        parse_program(pathlib.Path(path).read_text(encoding="utf-8"))
    )

# The program may itself contain spaces -- `id * succ` -- so it is whatever
# precedes "applied to" / " on ".
APPLIED = re.compile(
    r"^\$\s+(?P<prog>.+?)\s+(?:applied to|\bon)\s+(?P<arg>.+?)\s+->\s+(?P<want>.+?)$"
)
PRINTS = re.compile(r"^\$\s+(?P<val>.+?)\s+prints as\s+(?P<want>.+?)(?:\s+--.*)?$")
CALLED = re.compile(
    r"^\$\s+(?P<name>[a-zA-Z_][\w]*!?)\((?P<args>.*?)\)\s+=\s+(?P<want>.+?)"
    r"(?:\s+--.*)?$"
)


def _top_level_comma(text: str) -> bool:
    """Is there a comma outside any bracket or string? Then it is a pair."""
    depth, quoted = 0, False
    for ch in text:
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            elif ch == "," and depth == 0:
                return True
    return False


def env_defining(name: str):
    """The first library that defines `name`, so the claim can be run."""
    for lib, env in LIBS.items():
        if name in env:
            return lib, env
    return None, None


def split_results(text: str):
    """`(0, 5)  (1, 4)  L ()` -> the individual values claimed.

    Uses the real value parser one value at a time rather than splitting on
    punctuation, because `L ()` contains a space and `(0, 5)` contains a comma.
    """
    text = re.sub(r"\s+--.*$", "", text.strip())
    # A trailing gloss like "(nothing)" -- letters only, so that a real result
    # such as "(1, 4)" is never mistaken for one.
    text = re.sub(r"\s{2,}\([A-Za-z ]+\)\s*$", "", text)
    text = text.replace(" and ", " ").strip()
    if text in ("{}", "nothing", ""):
        return []
    from rel42.syntax import _Parser, lex

    p = _Parser(lex(text))
    out = []
    while p.peek()[0] != "eof":
        out.append(p.value())
    return out


def check(line: str, lineno: int):
    """Return (ok, detail) or None if the line makes no checkable claim."""
    m = APPLIED.match(line)
    if m:
        prog, arg, want = m.group("prog"), m.group("arg"), m.group("want")
        try:
            term, value = parse_term(prog), parse_value(arg)
        except Rel42Error as e:
            return False, f"{prog} on {arg}: {e}"
        # The program may name definitions (`id * succ`), so try each library
        # until one supplies them.
        last = None
        for env in [{}, *LIBS.values()]:
            try:
                return compare(run(term, value, env), want, f"{prog} applied to {arg}")
            except Rel42Error as e:
                last = e
        return False, f"{prog} on {arg}: {last}"

    m = CALLED.match(line)
    if m:
        name, args, want = m.group("name"), m.group("args"), m.group("want")
        back = name.endswith("!")
        base = name[:-1] if back else name
        lib, env = env_defining(base)
        if env is None:
            return None
        term = Ref(base)
        if back:
            term = dagger(term)
        arg = f"({args})" if _top_level_comma(args) else args
        try:
            got = run(term, parse_value(arg), env, max_depth=3000)
        except Rel42Error as e:
            return False, f"{name}({args}) [{lib}]: {e}"
        return compare(got, want, f"{name}({args}) [{lib}]")

    m = PRINTS.match(line)
    if m:
        try:
            val = parse_value(m.group("val"))
        except Rel42Error:
            return None
        want = m.group("want").strip()
        shown = show(val)
        return (shown == want,
                f"{m.group('val')} prints as {shown}, manual says {want}")
    return None


def compare(got, want_text, label):
    try:
        wanted = set(split_results(want_text))
    except Rel42Error:
        return None  # not a value expression; nothing to check
    if got == wanted:
        return True, label
    g = sorted(show(v) for v in got)
    w = sorted(show(v) for v in wanted)
    return False, f"{label}\n      manual says: {w}\n      actually:    {g}"


def main() -> int:
    text = pathlib.Path(ROOT / "MANUAL.md").read_text(encoding="utf-8")
    checked = failed = skipped = 0
    for lineno, line in enumerate(text.split("\n"), 1):
        if not line.startswith("$ "):
            continue
        result = check(line.rstrip(), lineno)
        if result is None:
            skipped += 1
            continue
        ok, detail = result
        checked += 1
        if not ok:
            failed += 1
            print(f"  MANUAL.md:{lineno}  {detail}")
    print(f"\n  {checked - failed}/{checked} claims verified"
          f"{f', {failed} WRONG' if failed else ''}"
          f"  ({skipped} lines not of a checkable form)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
