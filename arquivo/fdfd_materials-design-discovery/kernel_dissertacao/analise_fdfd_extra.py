"""Verificações complementares de analise_fdfd.py (rodar depois dele: reaproveita o cache).

1. Perfil de um solve_window por frequência: montagem, construção de S, splu, solução.
2. Onde ficam os FLOP da LU: fração nas últimas k colunas (o bloco denso de Γ_I
   entra por último na ordenação?) e tempo de uma LU densa (LAPACK zgetrf) do
   mesmo tamanho do bloco de borda, como teto atingível por BLAS-3.
3. Teto de cômputo denso por thread (zgemm) com 1 thread confirmada.
4. Sensibilidade à precisão em ~20 geometrias sorteadas (faixas P1), nas 3
   frequências já pré-calculadas: complex64 e complex64 + 1 refinamento.

Uso: uv run --with numpy --with scipy python3 kernel_dissertacao/analise_fdfd_extra.py \
        --ml ~/Projects/materials-design-discovery/ml
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ml", required=True)
ap.add_argument("--res", type=int, default=20)
ap.add_argument("--freqs", default="92.5,94.5,96.5")
ap.add_argument("--n-geom", type=int, default=20)
ap.add_argument("--out", default="resultados/kernel_fdfd")
a = ap.parse_args()
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(v, "1")
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(a.ml).expanduser().resolve()))

import numpy as np                                   # noqa: E402
import scipy.linalg as sla                           # noqa: E402
import scipy.sparse as sp                            # noqa: E402
import scipy.sparse.linalg as spla                   # noqa: E402
from circulador.geometria import baseline, sample    # noqa: E402
from fdfd2d import Physics, rapido                   # noqa: E402
from fdfd2d.fisica import ferrite_nu                 # noqa: E402
from fdfd2d.layout import DEFAULT_DOMAIN             # noqa: E402
from fdfd2d.ports import reference                   # noqa: E402
from fdfd2d.solver import PERMC, assemble            # noqa: E402

OUT = Path(a.out); CACHE = str(OUT / "cache")
PH = Physics(eps_dielectric=12.5, kappa_sign=-1)
FREQS = [float(f) for f in a.freqs.split(",")]
ext = rapido.get_exterior(DEFAULT_DOMAIN, a.res)
res = {}


def med(fn, reps=5):
    t = []
    for _ in range(reps):
        t0 = time.perf_counter(); r = fn(); t.append(time.perf_counter() - t0)
    return statistics.median(t), r


def monta(ras, pre, f):
    nu = ferrite_nu(f, PH) if ras.ff_e.any() else None
    A_ext = assemble(ras, pre["k0"], PH.eps_dielectric, PH.eps_ferrite, nu, None)
    return A_ext


def constroi_S(A_ext, pre):
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


# ---------------- 1. perfil do solve_window ----------------
g0 = baseline()
f = FREQS[1]
ref = reference(DEFAULT_DOMAIN, ext.grid, ext.pg, f, PH.eps_dielectric, PH.a_mm, ext.ss, CACHE)
pre = rapido.load_precompute(ext, f, PH.eps_dielectric, PH.a_mm, CACHE)
t_ras, ras = med(lambda: rapido.window_raster(ext, g0), 3)
t_mon, A_ext = med(lambda: monta(ras, pre, f))
t_S, (S, rhs, gI) = med(lambda: constroi_S(A_ext, pre))
t_lu, lu = med(lambda: spla.splu(S, permc_spec=PERMC))
t_sol, EI = med(lambda: lu.solve(rhs))
t_pos, _ = med(lambda: rapido.s_power_from_monitors(ext, pre["uM"] - pre["K"] @ EI[gI], ref, pre["k0"]))
perfil = dict(raster_s=t_ras, montagem_s=t_mon, construcao_S_s=t_S, splu_s=t_lu, solucao_s=t_sol,
              pos_processamento_s=t_pos)
tot = sum(v for k, v in perfil.items() if k != "raster_s")
perfil["fracao_splu_por_frequencia"] = t_lu / tot
res["perfil_solve_window"] = perfil
print("perfil por frequência (ms): " + ", ".join(f"{k[:-2]}={1e3 * v:.1f}" for k, v in perfil.items() if k.endswith("_s")))
print(f"  splu = {100 * perfil['fracao_splu_por_frequencia']:.0f}% do tempo por frequência (raster é 1x por amostra)")

# ---------------- 2. onde ficam os FLOP ----------------
L, U = lu.L.tocsc(), lu.U.tocsr()
l = np.diff(L.indptr) - 1
u = np.diff(U.indptr) - 1
fl = 8.0 * l * u + 6.0 * l
n = S.shape[0]
dist = {}
for k in (486, 1000, 2000, 4000):
    dist[str(k)] = float(fl[-k:].sum() / fl.sum())
res["fracao_flop_ultimas_k_colunas"] = dist
print("fração dos FLOP nas últimas k colunas da LU: " + ", ".join(f"k={k}: {100 * v:.0f}%" for k, v in dist.items()))
nb = len(gI)
M = (np.random.default_rng(0).standard_normal((nb, nb)) + 1j * np.random.default_rng(1).standard_normal((nb, nb))
     + nb * np.eye(nb))
t_dense, _ = med(lambda: sla.lu_factor(M, check_finite=False))
flop_dense = 8.0 * nb ** 3 / 3
res["lu_densa_borda"] = dict(n=nb, t_s=t_dense, gflops=flop_dense / t_dense / 1e9, flop=flop_dense)
print(f"LU densa complexa {nb}x{nb} (zgetrf): {1e3 * t_dense:.2f} ms -> {flop_dense / t_dense / 1e9:.1f} GFLOP/s")
k = 2000
M2 = (np.random.default_rng(2).standard_normal((k, k)) + 1j + k * np.eye(k))
t2, _ = med(lambda: sla.lu_factor(M2, check_finite=False), 3)
res["lu_densa_2000"] = dict(n=k, gflops=8.0 * k ** 3 / 3 / t2 / 1e9)
print(f"LU densa complexa {k}x{k}: {8.0 * k ** 3 / 3 / t2 / 1e9:.1f} GFLOP/s")

# ---------------- 3. teto denso 1 thread ----------------
for nn in (512, 1024):
    X = (np.random.default_rng(3).standard_normal((nn, nn)) + 1j).astype(complex)
    tg, _ = med(lambda: X @ X)
    res[f"zgemm_{nn}_gflops"] = 8.0 * nn ** 3 / tg / 1e9
print(f"zgemm 512: {res['zgemm_512_gflops']:.0f}  1024: {res['zgemm_1024_gflops']:.0f} GFLOP/s "
      f"(Accelerate, VECLIB_MAXIMUM_THREADS={os.environ['VECLIB_MAXIMUM_THREADS']})")

# ---------------- 4. precisão em geometrias sorteadas ----------------
G = sample(a.n_geom, seed=123)
pres = {fq: (rapido.load_precompute(ext, fq, PH.eps_dielectric, PH.a_mm, CACHE),
             reference(DEFAULT_DOMAIN, ext.grid, ext.pg, fq, PH.eps_dielectric, PH.a_mm, ext.ss, CACHE))
        for fq in FREQS}
d32, dref, dsum, ok = [], [], [], 0
for gi_, g in enumerate(G):
    try:
        ras_g = rapido.window_raster(ext, g)
    except ValueError:
        continue
    ok += 1
    for fq, (p, r) in pres.items():
        S, rhs, gI = constroi_S(monta(ras_g, p, fq), p)
        x64 = spla.splu(S, permc_spec=PERMC).solve(rhs)
        lu32 = spla.splu(S.astype(np.complex64), permc_spec=PERMC)
        x32 = lu32.solve(rhs.astype(np.complex64)).astype(complex)
        xr = x32 + lu32.solve((rhs - S @ x32).astype(np.complex64)).astype(complex)
        s64 = rapido.s_power_from_monitors(ext, p["uM"] - p["K"] @ x64[gI], r, p["k0"])
        s32 = rapido.s_power_from_monitors(ext, p["uM"] - p["K"] @ x32[gI], r, p["k0"])
        sr = rapido.s_power_from_monitors(ext, p["uM"] - p["K"] @ xr[gI], r, p["k0"])
        d32.append(np.abs(s32 - s64).max()); dref.append(np.abs(sr - s64).max())
        dsum.append(np.abs(s64.sum(axis=0) - 1).max())
res["precisao_geometrias"] = dict(
    n_geometrias=ok, n_casos=len(d32), freqs=FREQS,
    max_dS2_c64=float(max(d32)), mediana_dS2_c64=float(np.median(d32)),
    max_dS2_c64_refinado=float(max(dref)),
    max_desvio_soma_S2_fp64=float(max(dsum)))
p = res["precisao_geometrias"]
print(f"\nprecisão em {ok} geometrias x {len(FREQS)} freq ({p['n_casos']} casos): "
      f"max|Δ|S|²| c64 = {p['max_dS2_c64']:.1e} (mediana {p['mediana_dS2_c64']:.1e}), "
      f"refinado = {p['max_dS2_c64_refinado']:.1e}; |Σ|S|²−1| em FP64 até {p['max_desvio_soma_S2_fp64']:.1e}")

(OUT / "kernel_fdfd_extra.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(f"\nresultados: {OUT / 'kernel_fdfd_extra.json'}")
