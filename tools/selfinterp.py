#!/usr/bin/env python3
"""`meta.42` interpreting `meta.42`, which is slow enough to want its own script.

THEOREM.md 7.5 quotes the numbers this prints.  It is not in the test suite
because a single run takes minutes, and a suite nobody waits for is a suite
nobody runs -- `TestSelfInterpretation` checks the same claims one level down,
where they are cheap.

    python3 tools/selfinterp.py            -- forwards, and the dagger
    python3 tools/selfinterp.py --quick    -- the forward case only
"""

from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rel42 import Inl, Pair, Prim, Ref, UNIT, dagger, run, show  # noqa: E402
from rel42.meta import (  # noqa: E402
    decode_value,
    encode_env,
    encode_state,
    encode_term,
    encode_value,
    load_meta,
    relation_names,
    size,
)


def main(quick: bool = False) -> int:
    meta = load_meta()
    names = relation_names(meta)
    envenc = encode_env(meta, names)
    evalenc = encode_term(Ref("eval"), names)

    print(f"meta.42: {len(names)} relations encoded to {size(envenc):,} nodes,")
    print("carried through every step of the outer interpreter.\n")

    def outer(t, v):
        inner = encode_state({}, t, v, [])
        return Pair(envenc, Pair(evalenc, encode_value(inner))), inner

    def go(label, t, v, inv=False):
        st, inner = outer(t, v)
        t0 = time.time()
        out = run(dagger(Ref("eval")) if inv else Ref("eval"), st, meta,
                  max_depth=400000, max_orbit=2000)
        dt = time.time() - t0
        once = run(dagger(Ref("eval")) if inv else Ref("eval"), inner, meta,
                   max_depth=60000, max_orbit=900)
        agree = {decode_value(s.b.b) for s in out} == once
        kept = all(s.a == envenc and s.b.a == evalenc for s in out)
        print(f"  {label:38s} {dt:7.1f}s  {len(out)} result(s)  "
              f"[{'two levels == one' if agree else 'MISMATCH'}; "
              f"{'state preserved' if kept else 'STATE CHANGED'}]")

    print("eval interpreting <eval>:")
    go("<eval> on <id, ()>", Prim("id"), UNIT)
    go("<eval> on <swapsum, L ()>", Prim("swapsum"), Inl(UNIT))
    if quick:
        return 0
    go("<eval> on <swapsum, L ()>, backwards", Prim("swapsum"), Inl(UNIT), inv=True)

    print("\nTheorem 19, two levels down:")
    st, _ = outer(Prim("swapsum"), Inl(UNIT))
    t0 = time.time()
    lhs = run(dagger(Ref("eval")), st, meta, max_depth=400000, max_orbit=2000)
    rhs = run(Ref("conj"), st, meta, max_depth=400000, max_orbit=2000)
    print(f"  eval! == (id*(dag*id));eval;(id*(dag*id))"
          f"  {time.time()-t0:7.1f}s  {'HOLDS' if lhs == rhs else 'FAILS'}")
    return 0 if lhs == rhs else 1


if __name__ == "__main__":
    sys.setrecursionlimit(400000)
    threading.stack_size(512 * 1024 * 1024)
    code = []
    th = threading.Thread(target=lambda: code.append(main("--quick" in sys.argv)))
    th.start()
    th.join()
    raise SystemExit(code[0] if code else 1)
