"""Command line driver for 42.

    python -m rel42 run   FILE MAIN VALUE [--backward]
    python -m rel42 law   FILE MAIN VALUE          -- check the defining law
    python -m rel42 show  FILE [MAIN]              -- print each def and its dagger
    python -m rel42 type  FILE [MAIN]              -- infer  A <-> B  for each def
    python -m rel42 quote FILE MAIN [VALUE]        -- run it through meta.42
"""

from __future__ import annotations

import argparse
import sys

from .core import (
    DepthExceeded,
    NotARelation,
    Pair,
    Rel42Error,
    Ref,
    dagger,
    expand_env,
    is_combinator,
    run,
)
from .syntax import parse_program, parse_value, show_as, show_term
from .types import (
    conform,
    infer_program,
    infer_term,
    names_for,
    show_scheme,
    show_type,
)


def _call(name: str, value, raw: bool, backward: bool = False, ty=None) -> str:
    """Render an application the way you would write it: `append([1, 2], [3])`.

    A pair argument already prints with its own parentheses, so they are reused
    as the argument list rather than nested inside a second pair -- but only when
    it really did print that way, since a pair of eight bits prints as `'a'`.
    """
    shown = show_as(value, ty, raw)
    if isinstance(value, Pair) and shown.startswith("(") and shown.endswith(")"):
        shown = shown[1:-1]
    return f"{name}{'!' if backward else ''}({shown})"


def _load(path: str, reduce: bool = False):
    """Parse a file; optionally reduce every application away.

    `run` and `law` need the reduced form -- after `expand_env` no `App`
    survives, which is why the evaluator needed no case for one.  `show` and
    `type` want the source form, so that `cx` still reads as `ctrl x` and so
    that a combinator gets a type of its own.
    """
    with open(path, "r", encoding="utf-8") as fh:
        env = parse_program(fh.read())
    return expand_env(env) if reduce else env


def _resolve(env, main: str):
    if main not in env:
        raise Rel42Error(
            f"'{main}' is not defined in this file "
            f"(available: {', '.join(env) or 'nothing'})"
        )
    if is_combinator(env[main]):
        raise NotARelation(
            f"`{main}` is a combinator, not a relation -- it takes a parameter, "
            f"so there is nothing to apply to a value.  Apply it first, in a "
            f"definition: `def g = {main} <something>`."
        )
    return Ref(main)


def _check(env, name: str, term, value, args):
    """Reject an ill-typed definition, or an argument outside its domain.

    Returns the term's `Scheme` when it passes, so the caller can print values
    against it, or `None` under `--untyped`, where printing falls back to
    guessing.

    Only the CLI does this.  `core.run` stays untyped on purpose: in Rel the
    empty relation is a perfectly good morphism, so a shape mismatch really does
    *denote* nothing, and the library should keep saying so.  What the CLI adds
    is the judgement that you probably did not mean it -- which is a claim about
    the programmer, not about the semantics, and so belongs here.

    `--untyped` turns it off, and is how the manual's shape-mismatch examples
    are still reproducible.
    """
    if getattr(args, "untyped", False):
        return None

    schemes, errors = infer_program(env)
    if name in errors:
        raise Rel42Error(f"`{name}` is ill-typed: {errors[name]}")

    scheme = infer_term(term, schemes)
    bad = conform(value, scheme.dom)
    if bad is None:
        return scheme

    culprit, wanted = bad
    abbrevs = getattr(env, "types", ())
    names = names_for(scheme.dom, scheme.cod)
    pad = len(name) + 9  # width of "<name> expects ", so the colons line up
    detail = ""
    if culprit is not value:
        detail = (
            f"\n  {'the problem':<{pad}}: {show_as(culprit, None, args.raw)} "
            f"cannot have type {show_type(wanted, names, abbrevs=abbrevs)}"
        )
    raise Rel42Error(
        f"the argument does not fit the domain of `{name}`\n"
        f"  {name} expects : {show_type(scheme.dom, names, abbrevs=abbrevs)}\n"
        f"  {'you gave':<{pad}}: {show_as(value, None, args.raw)}{detail}\n"
        f"  (pass --untyped to run it anyway; in Rel this denotes the "
        f"empty relation)"
    )


def cmd_run(args) -> int:
    env = _load(args.file, reduce=True)
    term = _resolve(env, args.main)
    if args.backward:
        term = dagger(term)
    value = parse_value(args.value)
    scheme = _check(env, args.main, term, value, args)
    results = run(term, value, env, max_depth=args.limit, max_orbit=args.orbit)

    dom = scheme.dom if scheme else None
    cod = scheme.cod if scheme else None
    printed = sorted(show_as(r, cod, args.raw) for r in results)
    print(f"{_call(args.main, value, args.raw, args.backward, dom)} =")
    if not printed:
        print("  {}   (empty: no result)")
    else:
        for r in printed:
            print(f"  {r}")
        print(f"  -- {len(printed)} result{'s' if len(printed) != 1 else ''}")
    return 0


def cmd_quote(args) -> int:
    """Run a definition through `meta.42` rather than directly.

    `meta.42`'s own quoting combinators build a state against the *empty*
    environment, so from a `.42` file they reach only the definitions that
    mention no others.  This encodes the whole environment, which is what a
    recursive program needs, and is why `42 quote arith mul` is possible and
    `runq` is not.

    The type check is the object program's, against the file it came from --
    which is worth having and is cheap.  What cannot be checked is `meta.42`
    itself after its combinators are substituted away; MANUAL section 14.7 says
    why, and it is the reason `42 meta ...` wants `--untyped` while this does
    not.
    """
    from . import meta as M

    env = _load(args.file, reduce=True)
    term = _resolve(env, args.main)
    names = M.relation_names(env)

    if args.value is None:
        body = M.encode_term(env[args.main], names)
        print(f"{args.main}, as a value meta.42 can read:")
        print(f"  {show_as(body, None, True)}")
        print(f"  -- {M.size(body)} nodes, against an environment of "
              f"{len(names)} definition{'s' if len(names) != 1 else ''} "
              f"({M.size(M.encode_env(env, names))} nodes)")
        return 0

    value = parse_value(args.value)
    scheme = _check(env, args.main, dagger(term) if args.backward else term,
                    value, args)
    dom = scheme.dom if scheme else None
    cod = scheme.cod if scheme else None

    meta = M.load_meta()
    state = M.encode_state(env, term, value, names)
    ev = dagger(Ref("eval")) if args.backward else Ref("eval")
    results = run(ev, state, meta, max_depth=args.limit, max_orbit=args.orbit)

    # The `!` goes on `eval`, not on the program: `--backward` daggers the
    # *interpreter*, and the encoded program it reads is unchanged -- which is
    # THEOREM.md 7.4's point, so the printing should not blur it.
    printed = sorted(show_as(M.decode_state(s), cod, args.raw) for s in results)
    shown = _call(args.main, value, args.raw, False, dom)
    print(f"eval{'!' if args.backward else ''} {shown} =")
    if not printed:
        print("  {}   (empty: no result)")
    else:
        for r in printed:
            print(f"  {r}")
        print(f"  -- {len(printed)} result{'s' if len(printed) != 1 else ''}")
    return 0


def cmd_law(args) -> int:
    """Check  x in P(y)  <=>  y in inv(P)(x)  for the given input."""
    env = _load(args.file, reduce=True)
    fwd = _resolve(env, args.main)
    bwd = dagger(fwd)
    x = parse_value(args.value)
    scheme = _check(env, args.main, fwd, x, args)
    dom = scheme.dom if scheme else None
    cod = scheme.cod if scheme else None

    image = run(fwd, x, env, max_depth=args.limit, max_orbit=args.orbit)
    print(f"{_call(args.main, x, args.raw, ty=dom)} has {len(image)} result(s)")
    ok = True
    for y in sorted(image, key=lambda v: show_as(v, cod, args.raw)):
        pre = run(bwd, y, env, max_depth=args.limit, max_orbit=args.orbit)
        held = x in pre
        ok &= held
        mark = "ok " if held else "FAIL"
        print(
            f"  [{mark}] {show_as(y, cod, args.raw)}: "
            f"inv has {len(pre)} preimage(s), input {'in' if held else 'NOT in'} it"
        )
    print("law holds" if ok else "LAW VIOLATED")
    return 0 if ok else 1


def cmd_show(args) -> int:
    env = _load(args.file)
    names = [args.main] if args.main else list(env)
    width = max((len(n) for n in names), default=0) + 1  # room for the '!'
    for name in names:
        if name not in env:
            raise Rel42Error(f"'{name}' is not defined in this file")
        body = env[name]
        print(f"{name:<{width}}  = {show_term(body)}")
        print(f"{name + '!':<{width}}  = {show_term(dagger(body))}")
        print()
    return 0


def cmd_type(args) -> int:
    """Infer `A <-> B` for each definition."""
    env = _load(args.file)
    if args.main and args.main not in env:
        raise Rel42Error(f"'{args.main}' is not defined in this file")

    schemes, errors = infer_program(env)
    abbrevs = getattr(env, "types", ())
    names = [args.main] if args.main else list(env)
    width = max((len(n) for n in names), default=0)

    bad = 0
    for name in names:
        if name in schemes:
            print(f"{name:<{width}}  : {show_scheme(schemes[name], abbrevs)}")
        else:
            bad += 1
            print(f"{name:<{width}}  : ILL-TYPED -- {errors[name]}")

    print()
    print(
        f"-- {len(names) - bad}/{len(names)} typed"
        + (f", {bad} ILL-TYPED" if bad else "")
    )
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rel42", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    # Shared options live on each subcommand rather than on the top-level
    # parser, so that they may be written after the arguments -- `run f g v
    # --raw` is the form everyone reaches for.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--raw", action="store_true",
                        help="print values without number/list sugar")
    common.add_argument("--limit", type=int, default=5000, help="maximum call depth")
    common.add_argument("--orbit", type=int, default=1000,
                        help="maximum size of a '^' search before declaring it infinite")

    p = sub.add_parser("run", parents=[common], help="apply a definition to a value")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("value")
    p.add_argument("-b", "--backward", action="store_true", help="run it backwards")
    p.add_argument("--untyped", action="store_true",
                   help="skip the type check and evaluate in Rel regardless")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("law", parents=[common],
                       help="check that running backwards recovers the input")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("value")
    p.add_argument("--untyped", action="store_true",
                   help="skip the type check and evaluate in Rel regardless")
    p.set_defaults(fn=cmd_law)

    p = sub.add_parser("quote", parents=[common],
                       help="run a definition through meta.42, the 42 "
                            "interpreter written in 42")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("value", nargs="?",
                   help="omit it to print the program encoded as a value")
    p.add_argument("-b", "--backward", action="store_true",
                   help="dagger the interpreter, which runs the program backwards")
    p.add_argument("--untyped", action="store_true",
                   help="skip the type check and evaluate in Rel regardless")
    p.set_defaults(fn=cmd_quote)

    p = sub.add_parser("show", parents=[common],
                       help="print definitions alongside their reverses")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("type", parents=[common],
                       help="infer the type of each definition")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.set_defaults(fn=cmd_type)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except DepthExceeded as e:
        print(f"depth exceeded: {e}", file=sys.stderr)
        return 2
    except Rel42Error as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"error: no such file: {e.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    raise SystemExit(main())
