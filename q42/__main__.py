"""Command line driver for Q42.

    python -m q42 run     FILE MAIN STATE [--backward]
    python -m q42 sample  FILE MAIN STATE   -- measure the result, as a device would
    python -m q42 law     FILE MAIN STATE   -- check  <x|P|y> = conj <y|P!|x>
    python -m q42 unitary FILE [MAIN]       -- check  t ; t! = id  over the basis
    python -m q42 emit    FILE [MAIN]       -- write it out as OpenQASM 3
    python -m q42 matrix  FILE [MAIN]       -- print the matrix
    python -m q42 type    FILE [MAIN]       -- infer  A <-> B  for each def
    python -m q42 show    FILE [MAIN]       -- print each def and its dagger
"""

from __future__ import annotations

import argparse
import sys

from rel42.core import NotARelation, Rel42Error, Ref, dagger, expand_env, is_combinator

from .core import (
    ONE_AMP,
    Exact,
    Q42Error,
    apply_vec,
    column,
    marginal,
    matrix,
    probabilities,
    sample,
    validate,
)
from .syntax import (
    bits_of,
    parse_program,
    parse_state,
    show_amplitude,
    show_ket,
    show_term,
)
from .types import (
    basis_of,
    conform,
    ground,
    infer,
    infer_all,
    names_for,
    show_scheme,
    show_type,
)

TOL = 1e-9


def _load(path: str):
    """Parse and validate, keeping the program as written.

    `show` and `type` use this form, so that `cx` still reads as `ctrl x` and a
    combinator gets a type of its own rather than being inlined away.
    """
    with open(path, "r", encoding="utf-8") as fh:
        env = parse_program(fh.read())
    for name, body in env.items():
        validate(body, f"`{name}`")
    return env


def _load_reduced(path: str):
    """As `_load`, with every application reduced away -- what evaluation needs.

    After this no `App` survives, which is why the evaluator needed no case for
    one.  The combinators remain, as `Fun`s, and are refused if you try to run
    them against a state.
    """
    env = _load(path)
    out = expand_env(env)
    out.general = getattr(env, "general", set())
    return out


def _resolve(env, main: str):
    if main not in env:
        raise Q42Error(
            f"'{main}' is not defined in this file "
            f"(available: {', '.join(env) or 'nothing'})"
        )
    if is_combinator(env[main]):
        raise NotARelation(
            f"`{main}` is a combinator, not a gate -- apply it first, as in "
            f"`def cx = ctrl x`."
        )
    return Ref(main)


def _typed(env, name: str, term):
    """The scheme for `term`, or a clear refusal.

    Unlike 42, Q42 cannot treat this as optional: an ill-shaped application
    denotes the zero column, and the zero matrix is not unitary, so a typo would
    silently take the program outside the intended semantics.
    """
    schemes, errors = infer_all(env)
    if name in errors:
        raise Q42Error(f"`{name}` is ill-typed: {errors[name]}")
    return infer(term, schemes)


def _state(args, scheme, env):
    """Parse the state on the command line and check it fits the domain."""
    psi = parse_state(args.state)
    for v in psi:
        bad = conform(v, scheme.dom)
        if bad is not None:
            names = names_for(scheme.dom, scheme.cod)
            raise Q42Error(
                f"that state is not in the domain of `{args.main}`\n"
                f"  expects : "
                f"{show_type(scheme.dom, names, abbrevs=getattr(env, 'types', ()))}\n"
                f"  given   : {show_ket({v: ONE_AMP})}"
            )
    return psi


def _identity(n):
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def _same(x, y) -> bool:
    """Are two amplitudes the same one?

    Exactly, when both are `Exact` -- which since `q42.exact` is the ordinary
    case, and it is what turns `P ; P! = id` from a numerical observation into a
    decision.  An `int` counts as exact, so the identity matrix below needs no
    special handling.  Anything else falls back to a tolerance.
    """
    exact = (Exact, int)
    if isinstance(x, exact) and isinstance(y, exact):
        return x == y
    return abs(x - y) < TOL


def _close(a, b) -> bool:
    return all(
        _same(a[i][j], b[i][j]) for i in range(len(a)) for j in range(len(a))
    )


def cmd_run(args) -> int:
    env = _load_reduced(args.file)
    term = _resolve(env, args.main)
    if args.backward:
        term = dagger(term)
    scheme = _typed(env, args.main, term)

    psi = _state(args, scheme, env)
    out = apply_vec(term, psi, env)
    print(f"{args.main}{'!' if args.backward else ''} {show_ket(psi)}")
    print(f"  = {show_ket(out, scheme.cod)}")
    return 0


def cmd_sample(args) -> int:
    """Run a gate, then measure -- the one thing a device does that `run` cannot.

    Both distributions are printed: the exact Born probabilities, which only a
    simulator can know, and a draw of `--shots` outcomes, which is what a real
    machine would hand you. Seeing them side by side is the point.
    """
    env = _load_reduced(args.file)
    term = _resolve(env, args.main)
    if args.backward:
        term = dagger(term)
    scheme = _typed(env, args.main, term)
    psi = _state(args, scheme, env)

    out = apply_vec(term, psi, env)
    exact = probabilities(out)
    if not exact:
        print("the zero vector: there is nothing to measure")
        return 1

    total = sum(exact.values())
    drawn = sample(out, args.shots, seed=args.seed)


    if args.bits is not None:
        keep = {int(i) for i in args.bits.replace(",", " ").split()}
        sizes = {len(bits_of(v) or "") for v in exact}
        if sizes == {0}:
            raise Q42Error("--bits needs a register of qubits; this state is not one")
        n = max(sizes)
        out_of_range = sorted(i for i in keep if not 0 <= i < n)
        if out_of_range:
            raise Q42Error(
                f"--bits {','.join(map(str, out_of_range))}: this register has "
                f"{n} qubit{'s' if n != 1 else ''}, numbered 0 to {n - 1}"
            )
        grouped = marginal(exact, keep, bits_of)
        if not grouped:
            raise Q42Error(
                "--bits needs a register of qubits; this state is not one"
            )
        drawn_bits: Dict[str, int] = {}
        for v, n in drawn.items():
            b = bits_of(v)
            k = "".join(b[i] if i in keep else "_" for i in range(len(b)))
            drawn_bits[k] = drawn_bits.get(k, 0) + n
        exact = {k: p for k, p in grouped.items()}
        drawn = drawn_bits
        label = {k: f"|{k}>" for k in exact}
    else:
        label = {v: show_ket({v: ONE_AMP}) for v in exact}
    shotw = max(len(str(args.shots)), 5)
    width = max(len(x) for x in label.values())
    print(f"{args.main}{'!' if args.backward else ''} {show_ket(psi)}")
    print(f"    {'outcome':>{width}}  {'exact':>6}  {'drawn':>{shotw}}")
    # Descending probability, then by label, so ties come out in a fixed order.
    for v in sorted(exact, key=lambda k: (-exact[k], label[k])):
        bar = "#" * round(30 * exact[v])
        print(
            f"    {label[v]:>{width}}  {exact[v] * 100:5.1f}%  "
            f"{drawn.get(v, 0):>{shotw}}  {bar}"
        )
    print(f"  -- {args.shots} shot{'s' if args.shots != 1 else ''}, seed {args.seed}")
    if abs(total - 1) > TOL:
        print(f"  -- warning: probabilities sum to {total:.6f}, not 1")
    return 0


def cmd_law(args) -> int:
    """<x|P|y> = conj(<y|P!|x>) -- the defining law of 42, upgraded to C.

    42 checks `x in P(y) <=> y in inv(P)(x)`.  The same statement over C
    replaces membership with amplitude equality, and says that `P!` denotes the
    adjoint of `P`.
    """
    env = _load_reduced(args.file)
    fwd = _resolve(env, args.main)
    scheme = _typed(env, args.main, fwd)
    bwd = dagger(fwd)

    psi = parse_state(args.state)
    (x, _), = psi.items()
    image = column(fwd, x, env)
    print(f"{args.main} {show_ket(psi)} has {len(image)} component(s)")

    ok = True
    for y, amp in sorted(image.items(), key=lambda kv: show_ket({kv[0]: 1})):
        back = column(bwd, y, env).get(x, 0)
        held = _same(back, amp.conjugate())
        ok &= held
        print(
            f"  [{'ok ' if held else 'FAIL'}] {show_ket({y: ONE_AMP})}: "
            f"<y|P|x> = {show_amplitude(amp)}, "
            f"<x|P!|y> = {show_amplitude(back)}"
        )
    print("law holds" if ok else "LAW VIOLATED")
    return 0 if ok else 1


def cmd_unitary(args) -> int:
    """Check `t ; t! = id` numerically over the whole basis.

    Q42.md section 5 argues this holds by construction, since every generator is
    unitary and composition, direct sum, tensor and adjoint all preserve
    unitarity.  This is the argument being audited rather than trusted.
    """
    env = _load_reduced(args.file)
    names = [args.main] if args.main else list(env)
    schemes, errors = infer_all(env)

    bad = skipped = 0
    for name in names:
        if name in errors:
            bad += 1
            print(f"  [FAIL] {name}: ill-typed -- {errors[name]}")
            continue
        body = env[name]
        try:
            b = basis_of(ground(schemes[name], args.qubits).dom)
        except Rel42Error as e:
            # A combinator, a polymorphic gate, or simply not a gate on this many
            # qubits.  All are reasons to skip, not to abandon the sweep.
            skipped += 1
            print(f"  [--  ] {name}: {e}")
            continue
        from rel42.core import Seq

        m = matrix(Seq(body, dagger(body)), b, env)
        held = _close(m, _identity(len(b)))
        bad += not held
        print(
            f"  [{'ok ' if held else 'FAIL'}] {name} ; {name}! = id "
            f"on {len(b)} dimension(s)"
        )
    print()
    print(
        f"-- {len(names) - bad - skipped}/{len(names)} unitary"
        + (f", {skipped} with no single matrix" if skipped else "")
        + (f", {bad} FAILED" if bad else "")
    )
    return 1 if bad else 0


def cmd_emit(args) -> int:
    """Gates for a device, and the OpenQASM to hand a toolchain."""
    from .emit import NotEmittable, emit, to_qasm

    env = _load_reduced(args.file)
    names = [args.main] if args.main else list(env)
    for name in names:
        term = _resolve(env, name)
        scheme = _typed(env, name, term)
        try:
            at = ground(scheme, args.qubits)
            gates, wires = emit(term, at.dom, env)
        except (NotEmittable, Rel42Error) as e:
            from .sugar import not_emittable

            why = not_emittable(name, env, getattr(env, "general", set()))
            print(f"{name}: {why or e}")
            continue
        if args.gates:
            print(f"{name} : {wires} qubit(s), {len(gates)} gate(s)")
            for g in gates:
                arg = f"({g[2]:.6g})" if len(g) > 2 else ""
                print(f"  {g[0]}{arg} {', '.join(str(q) for q in g[1])}")
            print()
        else:
            print(to_qasm(gates, wires, name))
    return 0


def cmd_matrix(args) -> int:
    env = _load_reduced(args.file)
    abbrevs = getattr(env, "types", ())
    names = [args.main] if args.main else list(env)
    for name in names:
        term = _resolve(env, name)
        scheme = _typed(env, name, term)
        try:
            at = ground(scheme, args.qubits)
            dom = basis_of(at.dom)
            cod = basis_of(at.cod)
        except Rel42Error as e:
            print(f"{name}: {e}")
            continue
        m = matrix(term, dom, env)
        labels = [show_ket({v: ONE_AMP}) for v in cod]
        width = max((len(show_amplitude(z)) for row in m for z in row), default=1)
        print(f"{name} : {show_scheme(at, abbrevs)}")
        for i, row in enumerate(m):
            cells = "  ".join(f"{show_amplitude(complex(z)):>{width}}" for z in row)
            print(f"  {labels[i]:>6}  [ {cells} ]")
        print()
    return 0


def cmd_equal(args) -> int:
    """Decide whether two definitions denote the same matrix.

    This is a *decision*, not a comparison to a tolerance, and it is one for the
    reason QMANUAL §6.1 gives: `omega` and `v` are discrete, so every amplitude
    lies in `Z[1/sqrt2, i]` and `q42.exact` evaluates in that ring.  Where a
    complete axiomatisation would prove the two equal by rewriting one into the
    other, Q42 computes both and looks.  The cost is the size of the matrix,
    which is exponential; see QMANUAL §9.3.
    """
    env = _load_reduced(args.file)
    abbrevs = getattr(env, "types", ())

    terms, schemes = {}, {}
    for name in (args.main, args.other):
        terms[name] = _resolve(env, name)
        schemes[name] = _typed(env, name, terms[name])

    try:
        at = {n: ground(schemes[n], args.qubits) for n in terms}
    except Rel42Error as e:
        print(f"no matrix to compare: {e}")
        return 2

    left, right = args.main, args.other
    if show_scheme(at[left], abbrevs) != show_scheme(at[right], abbrevs):
        print(f"{left} : {show_scheme(at[left], abbrevs)}")
        print(f"{right} : {show_scheme(at[right], abbrevs)}")
        print("different types, so not the same matrix")
        return 1

    dom = basis_of(at[left].dom)
    a = matrix(terms[left], dom, env)
    b = matrix(terms[right], dom, env)
    held = _close(a, b)

    exact = all(isinstance(z, (Exact, int)) for m in (a, b) for row in m for z in row)
    print(f"{left} : {show_scheme(at[left], abbrevs)}")
    print(f"{right} : {show_scheme(at[right], abbrevs)}")
    if held:
        print(f"  equal on {len(dom)} dimension(s)"
              + ("" if exact else "  (to within a tolerance: not every amplitude "
                                 "is exact)"))
        return 0

    # Name the first disagreement rather than only denying the equality: on a
    # 2^n matrix "they differ" is not a useful answer on its own.
    for i in range(len(a)):
        for j in range(len(a)):
            if not _same(a[i][j], b[i][j]):
                cod = basis_of(at[left].cod)
                print(f"  differ at row {show_ket({cod[i]: ONE_AMP})}, "
                      f"column {show_ket({dom[j]: ONE_AMP})}: "
                      f"{show_amplitude(complex(a[i][j]))} "
                      f"vs {show_amplitude(complex(b[i][j]))}")
                return 1
    return 1


def _leaves(v) -> list:
    """A basis value's qubits in wire order, whatever the nesting: 0 or 1 each."""
    from rel42.core import Inl, Pair

    if isinstance(v, Pair):
        return _leaves(v.a) + _leaves(v.b)
    return [0 if isinstance(v, Inl) else 1]


def _ket(v) -> str:
    return "|" + "".join(map(str, _leaves(v))) + ">"


def _kets(col, bits: bool = False) -> str:
    """A column as kets, with each amplitude shown unless it is exactly 1."""
    if not col:
        return "nothing (the zero vector)"
    out = []
    for k, a in sorted(col.items(), key=lambda kv: kv[0] if bits else _leaves(kv[0])):
        ket = "|" + "".join(map(str, k)) + ">" if bits else _ket(k)
        one = _same(a, ONE_AMP) if not bits else abs(a - 1) < 1e-9
        out.append(ket if one else f"{show_amplitude(complex(a))} {ket}")
    return " + ".join(out)


#: Gates that only permute basis states, so a bit string can be followed through
#: them one gate at a time, at any width.
_CLASSICAL = {"x", "cx", "ccx", "swap", "cswap"}


def _run_bits(gates, bits: list) -> list:
    w = list(bits)
    for g in gates:
        name, qs = g[0], list(g[1])
        if name in ("swap", "cswap"):
            if name == "swap" or w[qs[0]]:
                a, b = qs[-2:]
                w[a], w[b] = w[b], w[a]
        elif all(w[q] for q in qs[:-1]):
            w[qs[-1]] ^= 1
    return w


def _circuit_columns(gates, n: int):
    """A function from an input bit list to the output column, as {bits: amp}.

    Classical gates are followed bit by bit.  Anything else goes through
    `tools/qasm_sim.py`, which shares no code with this evaluator, one gate
    matrix at a time on a state vector: exponential in `n`, so refused past
    `_SIM_LIMIT` qubits.
    """
    if all(g[0] in _CLASSICAL for g in gates):
        return lambda bits: {tuple(_run_bits(gates, bits)): 1}
    if n > _SIM_LIMIT:
        return None
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "tools"))
    import cmath

    from qasm_sim import gate_matrix

    # A global phase is a scalar, not a matrix, as in `qasm_sim.unitary_of`.
    phase, mats = 1 + 0j, []
    for g in gates:
        angle = g[2] if len(g) > 2 else None
        if g[0] == "gphase":
            phase *= cmath.exp(1j * float(angle))
        else:
            mats.append(gate_matrix(g[0], g[1], n, angle))

    def col(bits):
        vec = [0j] * (1 << n)
        vec[sum(b << (n - 1 - i) for i, b in enumerate(bits))] = phase
        for m in mats:
            vec = [sum(m[r][c] * vec[c] for c in range(len(vec)) if vec[c])
                   for r in range(len(vec))]
        return {tuple((r >> (n - 1 - i)) & 1 for i in range(n)): a
                for r, a in enumerate(vec) if abs(a) > 1e-9}
    return col


_SIM_LIMIT = 10


def cmd_check(args) -> int:
    """Check a Q42 program against a specification written in 42.

    QMANUAL §7.7 steps 3 and 5.  The encoder, a 42 definition in the
    specification's file, says which basis state stands for which value.  Every
    basis state of the program's domain is run backwards through it: a state
    that encodes nothing, or an input the specification gives no answer for, is
    not compared.  For the rest, the specification's answer is encoded, and
    the program -- and then its emitted circuit -- must produce exactly that
    basis state, with amplitude 1.
    """
    from rel42.core import run
    from rel42.syntax import parse_program as parse42, show
    from .emit import NotEmittable, emit

    env = _load_reduced(args.file)
    term = _resolve(env, args.main)
    at = ground(_typed(env, args.main, term), args.qubits)

    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (args.spec_file, args.spec_file + ".42",
                 os.path.join(root, args.spec_file),
                 os.path.join(root, args.spec_file + ".42")):
        if os.path.isfile(path):
            args.spec_file = path
            break
    with open(args.spec_file, "r", encoding="utf-8") as fh:
        spec = expand_env(parse42(fh.read()))
    for name in (args.spec, args.encode, args.decode or args.encode):
        if name not in spec:
            raise Q42Error(f"'{name}' is not defined in {args.spec_file}")
    enc, dec = Ref(args.encode), Ref(args.decode or args.encode)

    try:
        gates, wires = emit(term, at.dom, env)
        circuit = _circuit_columns(gates, wires)
        why_not = None if circuit else f"{wires} qubits and non-classical gates"
    except (NotEmittable, Rel42Error) as e:
        circuit, why_not = None, f"it does not emit: {e}"

    # One state at a time, never a matrix, so a larger space than `matrix` or
    # `unitary` would accept is affordable: about a millisecond a state.
    basis = basis_of(at.dom, limit=1 << 18)
    print(f"{args.main} against {args.spec}, through {args.encode}"
          + (f" and {args.decode}" if args.decode else ""))
    compared = unencoded = unanswered = 0
    for v in basis:
        xs = run(dagger(enc), v, spec)
        if not xs:
            unencoded += 1
            continue
        if len(xs) > 1:
            print(f"  [FAIL] {args.encode} is ambiguous: {_ket(v)} encodes "
                  + " and ".join(sorted(show(x) for x in xs)))
            return 1
        (x,) = xs
        ys = run(Ref(args.spec), x, spec)
        if not ys:
            unanswered += 1
            continue
        want = set()
        for y in ys:
            want |= run(dec, y, spec)
        if len(want) != 1:
            print(f"  [FAIL] {args.spec} {show(x)} gives "
                  f"{', '.join(sorted(show(y) for y in ys))}, which encodes to "
                  f"{len(want)} basis states; a program can produce only one")
            return 1
        (w,) = want
        got = {u: a for u, a in column(term, v, env).items() if not _same(a, 0)}
        if set(got) != {w} or not _same(got[w], ONE_AMP):
            print(f"  [FAIL] the program, on {_ket(v)} ({show(x)}):")
            print(f"         the spec says {_ket(w)} ({show(next(iter(ys)))})")
            print(f"         the program gives {_kets(got)}")
            return 1
        if circuit:
            out = circuit(_leaves(v))
            key = tuple(_leaves(w))
            if set(out) != {key} or abs(out[key] - 1) > 1e-9:
                print(f"  [FAIL] the emitted circuit, on {_ket(v)} ({show(x)}):")
                print(f"         the spec says {_ket(w)}")
                print("         the circuit gives "
                      + _kets({k: a for k, a in out.items()}, bits=True))
                return 1
        compared += 1

    print(f"  [ok ] the program: {compared} input(s) agree, exactly")
    if circuit:
        print(f"  [ok ] the circuit: {compared} input(s) agree "
              f"({len(gates)} gate(s) on {wires} qubit(s))")
    else:
        print(f"  [-- ] the circuit was not checked: {why_not}")
    print(f"  of {len(basis)} basis states, {unencoded} encode no input and "
          f"{unanswered} encode one {args.spec} does not answer; not compared")
    if compared == 0:
        print("  nothing was compared: does the encoder fit the program's register?")
        return 1
    return 0


def cmd_type(args) -> int:
    env = _load(args.file)
    if args.main and args.main not in env:
        raise Q42Error(f"'{args.main}' is not defined in this file")
    schemes, errors = infer_all(env)
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
    print(f"-- {len(names) - bad}/{len(names)} typed" + (f", {bad} ILL-TYPED" if bad else ""))
    return 1 if bad else 0


def cmd_show(args) -> int:
    from rel42.sugar import simplify, turned_round
    from rel42.syntax import show_clause

    env = _load(args.file)
    names = [args.main] if args.main else list(env)
    width = max((len(n) for n in names), default=0) + 1
    for name in names:
        if name not in env:
            raise Q42Error(f"'{name}' is not defined in this file")
        body = env[name]
        clauses = getattr(env, "clauses", {})
        if name in clauses:
            # As `42 show`: the clauses, the same clauses turned round (the
            # adjoint, read off the page), then what they compile to.
            params, group = clauses[name]
            for c in group:
                print(f"{name:<{width}}  {show_clause(name, params, c)[len(name) + 1:]}")
            for c in group:
                turned = show_clause(name, params, turned_round(c))
                print(f"{name + '!':<{width}}  {turned[len(name) + 1:]}")
            print(f"{name:<{width}}  = {show_term(body)}")
            print(f"{name + '!':<{width}}  = {show_term(simplify(dagger(body)))}")
            print()
            continue
        print(f"{name:<{width}}  = {show_term(body)}")
        print(f"{name + '!':<{width}}  = {show_term(dagger(body))}")
        print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="q42", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="apply a definition to a state")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("state", help="a basis state, e.g. |01> or 01")
    p.add_argument("-b", "--backward", action="store_true", help="run the adjoint")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("sample", help="run a gate and measure the result")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("state", help="a basis state, e.g. |01> or 01")
    p.add_argument("-b", "--backward", action="store_true", help="run the adjoint")
    p.add_argument("-n", "--shots", type=int, default=100,
                   help="how many outcomes to draw (default 100)")
    p.add_argument("--seed", type=int, default=0,
                   help="fix the draw, so a transcript stays reproducible")
    p.add_argument("--bits", metavar="N[,N...]",
                   help="measure only these qubits, counting from 0")
    p.set_defaults(fn=cmd_sample)

    p = sub.add_parser("law", help="check that the dagger is the adjoint")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("state")
    p.set_defaults(fn=cmd_law)

    p = sub.add_parser("unitary", help="check t ; t! = id over the basis")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.add_argument("-q", "--qubits", type=int,
                   help="read polymorphic types at this many qubits")
    p.set_defaults(fn=cmd_unitary)

    p = sub.add_parser("matrix", help="print the matrix of a definition")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.add_argument("-q", "--qubits", type=int,
                   help="read polymorphic types at this many qubits")
    p.set_defaults(fn=cmd_matrix)

    p = sub.add_parser("emit", help="write a definition out as OpenQASM 3")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.add_argument("-q", "--qubits", type=int,
                   help="read polymorphic types at this many qubits")
    p.add_argument("--gates", action="store_true",
                   help="list the gates and wires instead of writing QASM")
    p.set_defaults(fn=cmd_emit)

    p = sub.add_parser("equal", help="decide whether two definitions agree")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("other")
    p.add_argument("-q", "--qubits", type=int,
                   help="width to ground a polymorphic type at")
    p.set_defaults(fn=cmd_equal)

    p = sub.add_parser("check", help="check a definition against a 42 specification")
    p.add_argument("file")
    p.add_argument("main")
    p.add_argument("spec_file", metavar="SPECFILE", help="a 42 file")
    p.add_argument("spec", metavar="SPEC", help="the specification in it")
    p.add_argument("-e", "--encode", default="encode",
                   help="the 42 definition taking a value to its basis state "
                        "(default: encode)")
    p.add_argument("-d", "--decode",
                   help="a different encoder for the answers, if they differ")
    p.add_argument("-q", "--qubits", type=int,
                   help="width to ground a polymorphic type at")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("type", help="infer the type of each definition")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.set_defaults(fn=cmd_type)

    p = sub.add_parser("show", help="print definitions alongside their adjoints")
    p.add_argument("file")
    p.add_argument("main", nargs="?")
    p.set_defaults(fn=cmd_show)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except Rel42Error as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"error: no such file: {e.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    raise SystemExit(main())
