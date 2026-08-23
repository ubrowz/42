"""Q42 spike: 42's syntax, values and dagger -- evaluated over C instead of B.

Throwaway evidence for the claims in Q42.md, not a foundation to build on:
the bases are hand-specified, there are no types, and `omega`/`v` are shoved
into rel42.core.PRIMS so that 42's parser tags them as primitives rather than
references (see Q42.md, appendix -- the real fix is to inject the primitive
name set into the parser).

    python3 spike/q42_spike.py

Deliberately reuses from rel42:
  * the Value universe (Unit/Inl/Inr/Pair)
  * the Term type and the PARSER (so Q42 source is 42 surface syntax)
  * `dagger` ITSELF, unchanged

Only two things are new: the primitive table, and an evaluator whose columns
are Dict[Value, complex] instead of Set[Value].
"""

import cmath, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from rel42.core import UNIT, Inl, Inr, Pair, Prim, Ref, Seq, Sum, Prod, Union, Star, dagger, PRIMS
from rel42.syntax import parse_program

Vec = dict  # Value -> complex

# --- the Q42 primitive table -----------------------------------------------
# The rig-groupoid core: permutations, so each column is a single basis value
# with amplitude 1.  Then the two new generators.

QPRIMS = {}

def qprim(name, fwd, bwd):
    QPRIMS[name] = (fwd, bwd)
    PRIMS.setdefault(name, (None, None))   # so the parser tags it Prim, not Ref

def one(v):        return {v: 1+0j}
def none(v):       return {}

qprim("id", one, one)

def swapsum(v):
    if isinstance(v, Inl): return {Inr(v.v): 1+0j}
    if isinstance(v, Inr): return {Inl(v.v): 1+0j}
    return {}
qprim("swapsum", swapsum, swapsum)

def assocsum(v):
    match v:
        case Inl(x):      return {Inl(Inl(x)): 1+0j}
        case Inr(Inl(x)): return {Inl(Inr(x)): 1+0j}
        case Inr(Inr(x)): return {Inr(x): 1+0j}
    return {}
def assocsum_b(v):
    match v:
        case Inl(Inl(x)): return {Inl(x): 1+0j}
        case Inl(Inr(x)): return {Inr(Inl(x)): 1+0j}
        case Inr(x):      return {Inr(Inr(x)): 1+0j}
    return {}
qprim("assocsum", assocsum, assocsum_b)

qprim("unitsum", lambda v: {v.v: 1+0j} if isinstance(v, Inr) else {},
                 lambda v: {Inr(v): 1+0j})

def swapprod(v):
    return {Pair(v.b, v.a): 1+0j} if isinstance(v, Pair) else {}
qprim("swapprod", swapprod, swapprod)

def assocprod(v):
    match v:
        case Pair(a, Pair(b, c)): return {Pair(Pair(a, b), c): 1+0j}
    return {}
def assocprod_b(v):
    match v:
        case Pair(Pair(a, b), c): return {Pair(a, Pair(b, c)): 1+0j}
    return {}
qprim("assocprod", assocprod, assocprod_b)

qprim("unitprod", lambda v: {v.b: 1+0j} if isinstance(v, Pair) and v.a == UNIT else {},
                  lambda v: {Pair(UNIT, v): 1+0j})

def dist(v):
    match v:
        case Pair(Inl(a), c): return {Inl(Pair(a, c)): 1+0j}
        case Pair(Inr(b), c): return {Inr(Pair(b, c)): 1+0j}
    return {}
def dist_b(v):
    match v:
        case Inl(Pair(a, c)): return {Pair(Inl(a), c): 1+0j}
        case Inr(Pair(b, c)): return {Pair(Inr(b), c): 1+0j}
    return {}
qprim("dist", dist, dist_b)

# --- the two new generators -------------------------------------------------
W = cmath.exp(1j * cmath.pi / 4)                       # omega = e^{i pi/4}
qprim("omega", lambda v: {UNIT: W} if v == UNIT else {},
               lambda v: {UNIT: W.conjugate()} if v == UNIT else {})

# V = H . diag(-1, i) . H, in the basis |0> = Inl(()), |1> = Inr(())
VM = [[(-1+1j)/2, (-1-1j)/2],
      [(-1-1j)/2, (-1+1j)/2]]
ZERO, ONE = Inl(UNIT), Inr(UNIT)
BIT = [ZERO, ONE]

def _from_matrix(M, basis, adjoint=False):
    def go(v):
        if v not in basis: return {}
        j = basis.index(v)
        if adjoint:   # column j of M^dagger = conj of row j of M
            return {basis[i]: M[j][i].conjugate() for i in range(len(basis))}
        return {basis[i]: M[i][j] for i in range(len(basis))}
    return go
qprim("v", _from_matrix(VM, BIT), _from_matrix(VM, BIT, adjoint=True))


# --- the evaluator.  `col(t, v)` is the column of [[t]] at basis index v. ---

def col(t, v, env, depth=200):
    if isinstance(t, Prim):
        f, b = QPRIMS[t.name]
        return (b if t.inv else f)(v)

    if isinstance(t, Ref):
        if depth <= 0: raise RecursionError(t.name)
        body = env[t.name]
        if t.inv: body = dagger(body)
        return col(body, v, env, depth - 1)

    if isinstance(t, Seq):                      # matrix product
        out = {}
        for w, zw in col(t.s, v, env, depth).items():
            for z, zz in col(t.t, w, env, depth).items():
                out[z] = out.get(z, 0) + zw * zz
        return out

    if isinstance(t, Sum):                      # direct sum
        if isinstance(v, Inl):
            return {Inl(w): z for w, z in col(t.s, v.v, env, depth).items()}
        if isinstance(v, Inr):
            return {Inr(w): z for w, z in col(t.t, v.v, env, depth).items()}
        return {}

    if isinstance(t, Prod):                     # tensor product
        if not isinstance(v, Pair): return {}
        L = col(t.s, v.a, env, depth)
        R = col(t.t, v.b, env, depth)
        return {Pair(a, b): za * zb for a, za in L.items() for b, zb in R.items()}

    if isinstance(t, (Union, Star)):
        raise TypeError(f"{type(t).__name__} needs an idempotent semiring; not in Q42")
    raise TypeError(t)


def apply_vec(t, psi, env):
    """Apply t to a superposition -- needed because Prod alone never entangles."""
    out = {}
    for v, amp in psi.items():
        for w, z in col(t, v, env).items():
            out[w] = out.get(w, 0) + amp * z
    return {k: z for k, z in out.items() if abs(z) > 1e-12}


def matrix(t, basis, env):
    return [[col(t, basis[j], env).get(basis[i], 0) for j in range(len(basis))]
            for i in range(len(basis))]


# --- Q42 source, in 42's actual surface syntax ------------------------------

SRC = """
def x     = swapsum
def t     = id + omega
def s     = id + (omega ; omega)
def z     = id + (omega ; omega ; omega ; omega)

def mat   = dist ; (unitprod + unitprod)
def cx    = mat ; (id + x) ; mat!
def ccx   = mat ; (id + cx) ; mat!

def hcore = x ; s ; v ; s ; x
def h     = unitprod! ; (omega * hcore) ; unitprod

def hxh   = h ; x ; h
def hzh   = h ; z ; h
def hh    = h ; h
def hhdag = h ; h!
def vv    = v ; v
def ss    = s ; s
def tt    = t ; t
def w8    = omega ; omega ; omega ; omega ; omega ; omega ; omega ; omega
def e3l   = v ; s ; v
def e3r   = s ; v ; s
def bell  = (h * id) ; cx
"""
ENV = parse_program(SRC)

# --- checks -----------------------------------------------------------------

TWO  = [Pair(a, b) for a in BIT for b in BIT]
THREE = [Pair(a, Pair(b, c)) for a in BIT for b in BIT for c in BIT]
I2 = [[1 if i == j else 0 for j in range(2)] for i in range(2)]
H_EXPECTED = [[1/2**.5, 1/2**.5], [1/2**.5, -1/2**.5]]
X_M = [[0, 1], [1, 0]]
Z_M = [[1, 0], [0, -1]]

def close(A, B, tol=1e-10):
    return all(abs(A[i][j] - B[i][j]) < tol for i in range(len(A)) for j in range(len(A)))

def ident(n):
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]

def fmt(z):
    r, i = round(z.real, 4) + 0.0, round(z.imag, 4) + 0.0
    if abs(i) < 1e-9: return f"{r:>7.4f}       "
    return f"{r:>7.4f}{i:+.4f}i"

def show(name, M):
    print(f"  {name} =")
    for row in M:
        print("      [ " + "  ".join(fmt(complex(z)) for z in row) + " ]")

results = []
def check(label, cond):
    results.append((label, cond))
    print(f"  [{'ok ' if cond else 'FAIL'}] {label}")

print("=" * 68)
print("AXIOMS  (E1) (E2) (E3)")
print("=" * 68)
check("E1  omega^8 = id                 (on type 1)",
      abs(col(ENV["w8"], UNIT, ENV).get(UNIT, 0) - 1) < 1e-12)
check("E2  v ; v = swapsum              (v is a square root of NOT)",
      close(matrix(ENV["vv"], BIT, ENV), X_M))
e3l, e3r = matrix(ENV["e3l"], BIT, ENV), matrix(ENV["e3r"], BIT, ENV)
w2 = W * W
check("E3  v;S;v = omega^2 . (S;v;S)",
      close(e3l, [[w2 * e3r[i][j] for j in range(2)] for i in range(2)]))

print()
print("=" * 68)
print("THE SPIKE:  h ; h = id")
print("=" * 68)
HM = matrix(ENV["h"], BIT, ENV)
show("h", HM)
check("h matches (1/sqrt 2)[[1,1],[1,-1]] exactly (no stray phase)",
      close(HM, H_EXPECTED))
show("h ; h", matrix(ENV["hh"], BIT, ENV))
check("h ; h = id", close(matrix(ENV["hh"], BIT, ENV), I2))
check("h ; h! = id                     (rel42's OWN dagger, unchanged)",
      close(matrix(ENV["hhdag"], BIT, ENV), I2))

print()
print("=" * 68)
print("DERIVED GATES")
print("=" * 68)
check("s ; s = z                        (Prop 8: S.S = Z = id + omega^4)",
      close(matrix(ENV["ss"], BIT, ENV), matrix(ENV["z"], BIT, ENV)))
check("t ; t = s                        (T.T = S)",
      close(matrix(ENV["tt"], BIT, ENV), matrix(ENV["s"], BIT, ENV)))
check("h ; x ; h = z                    (Lemma 11)",
      close(matrix(ENV["hxh"], BIT, ENV), Z_M))
check("h ; z ; h = x                    (Lemma 11)",
      close(matrix(ENV["hzh"], BIT, ENV), X_M))
show("t  (expect diag(1, e^{i pi/4}))", matrix(ENV["t"], BIT, ENV))

print()
print("=" * 68)
print("UNITARITY BY CONSTRUCTION  (sec 5) -- t ; t! = id for every def")
print("=" * 68)
for name in ["x", "t", "s", "z", "v", "omega", "h", "mat", "cx", "ccx", "bell"]:
    body = ENV.get(name) or Prim(name)   # `v` and `omega` are primitives, not defs
    basis = {"ccx": THREE, "cx": TWO, "bell": TWO,
             "mat": TWO, "omega": [UNIT]}.get(name, BIT)
    M  = matrix(Seq(body, dagger(body)), basis, ENV)
    check(f"{name:>5} ; {name}! = id", close(M, ident(len(basis))))

print()
print("=" * 68)
print("CLASSICAL GATES STILL CLASSICAL")
print("=" * 68)
def bits(v, n):
    out = []
    for _ in range(n - 1):
        out.append("1" if isinstance(v.a, Inr) else "0"); v = v.b
    out.append("1" if isinstance(v, Inr) else "0")
    return "".join(out)
for label, name, basis, n in [("cx ", "cx", TWO, 2), ("ccx", "ccx", THREE, 3)]:
    rows = []
    for b in basis:
        c = col(ENV[name], b, ENV)
        (out, amp), = c.items()
        rows.append(f"{bits(b,n)}->{bits(out,n)}" + ("" if abs(amp-1) < 1e-12 else "?"))
    print(f"  {label}: " + "  ".join(rows))

print()
print("=" * 68)
print("INTERFERENCE AND ENTANGLEMENT  (what B could not express)")
print("=" * 68)
def ket(psi, n):
    parts = [f"{fmt(complex(z)).strip()}|{bits(v,n)}>" for v, z in sorted(psi.items(), key=lambda kv: bits(kv[0],n))]
    return "  +  ".join(parts) if parts else "0"
print("  h|0>            = " + ket(col(ENV["h"], ZERO, ENV), 1))
print("  h|1>            = " + ket(col(ENV["h"], ONE, ENV), 1))
print("  h(h|0>)         = " + ket(apply_vec(ENV["h"], col(ENV["h"], ZERO, ENV), ENV), 1)
      + "     <- the |1> paths cancelled")
print("  bell|00>        = " + ket(col(ENV["bell"], Pair(ZERO, ZERO), ENV), 2))
psi = col(ENV["h"], ZERO, ENV)
plus0 = {Pair(k, ZERO): z for k, z in psi.items()}
print("  cx(|+>(x)|0>)   = " + ket(apply_vec(ENV["cx"], plus0, ENV), 2)
      + "     <- needed apply_vec; not a product state")

print()
print("=" * 68)
bad = [l for l, c in results if not c]
print(f"{len(results) - len(bad)}/{len(results)} checks passed" + ("" if not bad else f";  FAILED: {bad}"))
print("=" * 68)
