"""AI, desempenho e sensibilidade à precisão do kernel do projeto de dissertação:
o solver FDFD 2D do circulador (materials-design-discovery/ml/fdfd2d).

O código do projeto é só IMPORTADO (nada é escrito no repositório dele). O cache
de pré-cálculo vai para resultados/kernel_fdfd/cache.

Kernel medido = o laço quente da geração da base (rapido.solve_window): por
amostra e por frequência, monta o sistema reduzido da janela da cavidade
S = A_II − D (esparso + bloco denso na borda Γ_I), fatora com SuperLU e
resolve 3 lados direitos (as 3 portas). Também é medida a fatoração da grade
inteira (method="direto"), para ver como a AI cresce com o tamanho.

Contagem (por fatoração LU, coluna k, complexo):
  l_k = nnz abaixo da diagonal na coluna k de L,  u_k = nnz à direita da
  diagonal na linha k de U.  Atualização de Schur: l_k·u_k FMA complexas
  (8 FLOP reais cada: 4 mul + 4 add) + l_k divisões pelo pivô (contadas como
  6 FLOP).  Bytes mínimos (tráfego compulsório): ler S e escrever L e U uma
  vez: (nnz(S) + nnz(L) + nnz(U)) × (16 B valor complex128 + 4 B índice int32).
  Isso dá um LIMITE SUPERIOR da AI (sem reuso perfeito o tráfego real é maior).
Solução triangular com m lados direitos: 8·m FLOP por não-zero de L+U, lendo
cada não-zero uma vez (20 B).

Uso (a partir da raiz deste repositório):
  uv run --with numpy --with scipy python3 kernel_dissertacao/analise_fdfd.py \
      --ml ~/Projects/materials-design-discovery/ml
"""
import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ml", required=True, help="pasta ml/ do materials-design-discovery")
ap.add_argument("--res", type=int, default=20)
ap.add_argument("--freqs", default="92.5,94.5,96.5")
ap.add_argument("--reps", type=int, default=5)
ap.add_argument("--out", default="resultados/kernel_fdfd")
a = ap.parse_args()

for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(v, "1")  # como o gerar_base do projeto: 1 thread por worker
sys.path.insert(0, str(Path(a.ml).expanduser().resolve()))

import numpy as np                                   # noqa: E402
import scipy                                         # noqa: E402
import scipy.sparse as sp                            # noqa: E402
import scipy.sparse.linalg as spla                   # noqa: E402
from circulador.geometria import baseline            # noqa: E402
from fdfd2d import Physics                           # noqa: E402
from fdfd2d import rapido                            # noqa: E402
from fdfd2d.fisica import ferrite_nu                 # noqa: E402
from fdfd2d.layout import DEFAULT_DOMAIN             # noqa: E402
from fdfd2d.ports import reference                   # noqa: E402
from fdfd2d.solver import PERMC, Operator, assemble  # noqa: E402
from fdfd2d.layout import rasterize, device_rods     # noqa: E402

OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
CACHE = str(OUT / "cache")
PH = Physics(eps_dielectric=12.5, kappa_sign=-1)     # produção (dataset-fdfd-eps12.5-P2)
FREQS = [float(f) for f in a.freqs.split(",")]
VAL, IDX = 16, 4                                     # bytes: complex128, int32


def contagem_lu(lu, nnz_a, val=VAL):
    L, U = lu.L.tocsc(), lu.U.tocsr()
    l = np.diff(L.indptr) - 1                        # sem a diagonal unitária
    u = np.diff(U.indptr) - 1                        # sem o pivô
    flop = float(np.sum(8.0 * l * u + 6.0 * l))
    nnz_lu = L.nnz + U.nnz
    by = float((nnz_a + nnz_lu) * (val + IDX))
    return dict(flop=flop, bytes_min=by, ai_max=flop / by, nnz_L=int(L.nnz), nnz_U=int(U.nnz),
                fill=nnz_lu / nnz_a)


def mede(fn, reps):
    t = []
    for _ in range(reps):
        t0 = time.perf_counter(); r = fn(); t.append(time.perf_counter() - t0)
    return statistics.median(t), min(t), max(t), r


def sistema_janela(ext, ras, pre, f):
    """Igual a rapido.solve_window até a fatoração (devolve S e o lado direito)."""
    has_f = ras.ff_e.any()
    nu = ferrite_nu(f, PH) if has_f else None
    A_ext = assemble(ras, pre["k0"], PH.eps_dielectric, PH.eps_ferrite, nu, None)
    sg = ext.sub_ext
    jj, ii = np.meshgrid(np.arange(1, sg.ny - 1), np.arange(1, sg.nx - 1), indexing="ij")
    inner = (jj * sg.nx + ii).ravel()
    A_II = A_ext[inner][:, inner]
    gI = pre["gI"]
    rr, cc = np.meshgrid(gI, gI, indexing="ij")
    n = inner.size
    S = (A_II - sp.csc_matrix((pre["D"].ravel(), (rr.ravel(), cc.ravel())), shape=(n, n))).tocsc()
    rhs = np.zeros((n, 3), complex)
    rhs[gI] = pre["r"]
    return S, rhs, gI


def s2(ext, pre, ref, EI, gI):
    EM = pre["uM"] - pre["K"] @ EI[gI].astype(complex)
    return rapido.s_power_from_monitors(ext, EM, ref, pre["k0"])


res = {"ambiente": dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                        maquina=platform.platform(), threads_blas=os.environ["OPENBLAS_NUM_THREADS"],
                        res=a.res, eps=PH.eps_dielectric, kappa_sign=PH.kappa_sign, permc=PERMC),
       "janela": [], "grade_inteira": None}

ext = rapido.get_exterior(DEFAULT_DOMAIN, a.res)
g = baseline()
ras = rapido.window_raster(ext, g)
print(f"grade {ext.grid.nx}x{ext.grid.ny} = {ext.grid.nx * ext.grid.ny:,} nós | janela {ext.I.size:,} nós")

for f in FREQS:
    t0 = time.perf_counter()
    ref = reference(DEFAULT_DOMAIN, ext.grid, ext.pg, f, PH.eps_dielectric, PH.a_mm, ext.ss, CACHE)
    pre = rapido.load_precompute(ext, f, PH.eps_dielectric, PH.a_mm, CACHE)
    t_pre = time.perf_counter() - t0
    S, rhs, gI = sistema_janela(ext, ras, pre, f)

    tf, tf_min, tf_max, lu = mede(lambda: spla.splu(S, permc_spec=PERMC), a.reps)
    ts, _, _, EI = mede(lambda: lu.solve(rhs), a.reps)
    c = contagem_lu(lu, S.nnz)
    flop_s = 8.0 * 3 * (c["nnz_L"] + c["nnz_U"])
    by_s = (c["nnz_L"] + c["nnz_U"]) * (VAL + IDX) + 2 * rhs.size * VAL

    # --- mesma conta em precisão simples (complex64) ---
    S32 = S.astype(np.complex64)
    tf32, _, _, lu32 = mede(lambda: spla.splu(S32, permc_spec=PERMC), a.reps)
    ts32, _, _, EI32 = mede(lambda: lu32.solve(rhs.astype(np.complex64)), a.reps)
    # um passo de refinamento iterativo: resíduo em complex128, correção em complex64
    r = rhs - S @ EI32.astype(complex)
    EIr = EI32.astype(complex) + lu32.solve(r.astype(np.complex64)).astype(complex)

    S2_64, S2_32, S2_r = s2(ext, pre, ref, EI, gI), s2(ext, pre, ref, EI32, gI), s2(ext, pre, ref, EIr, gI)
    db = lambda x: 10 * np.log10(np.maximum(x, 1e-12))
    rel = lambda x: float(np.linalg.norm(x - EI) / np.linalg.norm(EI))
    linha = dict(
        f_GHz=f, n=int(S.shape[0]), nnz_S=int(S.nnz), t_precalc_s=t_pre,
        t_fat_s=tf, t_fat_min_s=tf_min, t_fat_max_s=tf_max, t_sol_s=ts, **c,
        gflops_fat=c["flop"] / tf / 1e9, gbs_min_fat=c["bytes_min"] / tf / 1e9,
        flop_sol=flop_s, bytes_sol=by_s, ai_sol=flop_s / by_s,
        t_fat32_s=tf32, t_sol32_s=ts32, speedup_fat32=tf / tf32,
        erro_rel_campo_c64=rel(EI32), erro_rel_campo_c64_refinado=rel(EIr),
        max_dS2_c64=float(np.max(np.abs(S2_32 - S2_64))),
        max_dS2_c64_refinado=float(np.max(np.abs(S2_r - S2_64))),
        max_ddB_c64=float(np.max(np.abs(db(S2_32) - db(S2_64)))),
        soma_S2_coluna1=float(S2_64[:, 0].sum()),
    )
    res["janela"].append(linha)
    print(f"\n[janela] f={f} GHz  n={linha['n']:,}  nnz(S)={linha['nnz_S']:,}  fill={c['fill']:.1f}x  "
          f"(pré-cálculo {t_pre:.0f} s)")
    print(f"  fatoração: {tf * 1e3:.1f} ms (faixa {tf_min * 1e3:.1f}-{tf_max * 1e3:.1f})  "
          f"{c['flop'] / 1e9:.2f} GFLOP  AI<= {c['ai_max']:.1f} FLOP/B  -> {linha['gflops_fat']:.2f} GFLOP/s")
    print(f"  solução 3 RHS: {ts * 1e3:.2f} ms  AI = {linha['ai_sol']:.2f} FLOP/B")
    print(f"  complex64: fatoração {tf32 * 1e3:.1f} ms ({linha['speedup_fat32']:.2f}x)  "
          f"erro rel. campo {linha['erro_rel_campo_c64']:.1e} -> refinado {linha['erro_rel_campo_c64_refinado']:.1e}")
    print(f"  max |Δ|S|²|: c64 {linha['max_dS2_c64']:.1e}  refinado {linha['max_dS2_c64_refinado']:.1e}  "
          f"(max Δ dB c64 {linha['max_ddB_c64']:.2e})")

# --- grade inteira (method="direto"), uma frequência, para ver a AI crescer com n ---
f = FREQS[len(FREQS) // 2]
rods = device_rods(g, DEFAULT_DOMAIN)
ras_full = rasterize(rods, ext.grid, ext.ss)
op = Operator(ras_full, DEFAULT_DOMAIN, rapido.k0_of(f, PH.a_mm), PH.eps_dielectric, PH.eps_ferrite,
              ferrite_nu(f, PH))
A = op.A
tf, tf_min, tf_max, lu = mede(lambda: spla.splu(A, permc_spec=PERMC), 3)
c = contagem_lu(lu, A.nnz)
A32 = A.astype(np.complex64)
tf32, _, _, lu32 = mede(lambda: spla.splu(A32, permc_spec=PERMC), 3)
b = np.random.default_rng(0).standard_normal((A.shape[0], 3)).astype(complex)
x = lu.solve(b); x32 = lu32.solve(b.astype(np.complex64)).astype(complex)
xr = x32 + lu32.solve((b - A @ x32).astype(np.complex64)).astype(complex)
res["grade_inteira"] = dict(
    f_GHz=f, n=int(A.shape[0]), nnz_A=int(A.nnz), t_fat_s=tf, t_fat_min_s=tf_min, t_fat_max_s=tf_max, **c,
    gflops_fat=c["flop"] / tf / 1e9, gbs_min_fat=c["bytes_min"] / tf / 1e9,
    t_fat32_s=tf32, speedup_fat32=tf / tf32,
    erro_rel_c64=float(np.linalg.norm(x32 - x) / np.linalg.norm(x)),
    erro_rel_c64_refinado=float(np.linalg.norm(xr - x) / np.linalg.norm(x)))
gi = res["grade_inteira"]
print(f"\n[grade inteira] n={gi['n']:,}  nnz(A)={gi['nnz_A']:,}  fill={gi['fill']:.1f}x")
print(f"  fatoração: {tf:.2f} s  {gi['flop'] / 1e9:.1f} GFLOP  AI<= {gi['ai_max']:.1f} FLOP/B  "
      f"-> {gi['gflops_fat']:.2f} GFLOP/s")
print(f"  complex64: {tf32:.2f} s ({gi['speedup_fat32']:.2f}x)  erro rel. {gi['erro_rel_c64']:.1e} "
      f"-> refinado {gi['erro_rel_c64_refinado']:.1e}")

# --- tetos práticos desta CPU, 1 thread (mesma condição do kernel) ---
n = 1024
X = (np.random.default_rng(1).standard_normal((n, n)) + 1j).astype(complex)
tg, _, _, _ = mede(lambda: X @ X, 5)
res["teto_zgemm_1t_gflops"] = 8.0 * n ** 3 / tg / 1e9
X32 = X.astype(np.complex64)
tg32, _, _, _ = mede(lambda: X32 @ X32, 5)
res["teto_cgemm_1t_gflops"] = 8.0 * n ** 3 / tg32 / 1e9
print(f"\nteto prático 1 thread: zgemm {res['teto_zgemm_1t_gflops']:.1f} GFLOP/s | "
      f"cgemm {res['teto_cgemm_1t_gflops']:.1f} GFLOP/s")

(OUT / "kernel_fdfd.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(f"\nresultados: {OUT / 'kernel_fdfd.json'}")
