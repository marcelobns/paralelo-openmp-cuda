"""Teste discriminante do regime da LU esparsa: workers concorrentes (condição de produção).

Se a vazão agregada (fatorações/s) escala ~linearmente com 1, 2, 4 workers, a LU não
é limitada pela banda compartilhada (o Bloco 2 mostra que a banda agregada satura em
~2x a de 1 thread). Se estagna em ~2x, é limitada por memória.
Também confere se zgemm/zgetrf do Accelerate respeitam 1 thread (tempo de CPU vs parede).

Uso: uv run --with numpy --with scipy python3 kernel_dissertacao/teste_concorrencia.py \
        --ml ~/Projects/materials-design-discovery/ml
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(v, "1")
sys.dont_write_bytecode = True

DUR = 6.0  # segundos de medição por worker


def worker(path, barrier, q):
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    S = sp.load_npz(path).tocsc()
    spla.splu(S, permc_spec="MMD_AT_PLUS_A")  # aquecimento
    barrier.wait()
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < DUR:
        spla.splu(S, permc_spec="MMD_AT_PLUS_A"); n += 1
    q.put(n / (time.perf_counter() - t0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ml", required=True)
    ap.add_argument("--out", default="resultados/kernel_fdfd")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.ml).expanduser().resolve()))
    import numpy as np
    import scipy.linalg as sla
    import scipy.sparse as sp
    from circulador.geometria import baseline
    from fdfd2d import Physics, rapido
    from fdfd2d.fisica import ferrite_nu
    from fdfd2d.layout import DEFAULT_DOMAIN
    from fdfd2d.solver import assemble

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    scratch = Path(os.environ.get("TMPDIR", "/tmp")) / "S_janela.npz"
    PH = Physics(eps_dielectric=12.5, kappa_sign=-1)
    f = 94.5
    ext = rapido.get_exterior(DEFAULT_DOMAIN, 20)
    pre = rapido.load_precompute(ext, f, PH.eps_dielectric, PH.a_mm, str(out / "cache"))
    ras = rapido.window_raster(ext, baseline())
    A_ext = assemble(ras, pre["k0"], PH.eps_dielectric, PH.eps_ferrite, ferrite_nu(f, PH), None)
    sg = ext.sub_ext
    jj, ii = np.meshgrid(np.arange(1, sg.ny - 1), np.arange(1, sg.nx - 1), indexing="ij")
    inner = (jj * sg.nx + ii).ravel()
    gI = pre["gI"]; rr, cc = np.meshgrid(gI, gI, indexing="ij"); n = inner.size
    S = (A_ext[inner][:, inner] - sp.csc_matrix((pre["D"].ravel(), (rr.ravel(), cc.ravel())), shape=(n, n))).tocsc()
    sp.save_npz(scratch, S)

    res = {"vazao_fat_por_s": {}}
    ctx = mp.get_context("spawn")
    for w in (1, 2, 4, 6):
        q, b = ctx.Queue(), ctx.Barrier(w)
        ps = [ctx.Process(target=worker, args=(str(scratch), b, q)) for _ in range(w)]
        for p in ps: p.start()
        taxas = [q.get() for _ in ps]
        for p in ps: p.join()
        res["vazao_fat_por_s"][w] = sum(taxas)
        print(f"{w} worker(s): {sum(taxas):6.1f} fatorações/s "
              f"({sum(taxas) / res['vazao_fat_por_s'][1]:.2f}x)  por worker {min(taxas):.1f}-{max(taxas):.1f}")

    # Accelerate respeita 1 thread?  razão tempo de CPU / parede ~1 => 1 thread
    for nome, fn in (("zgemm 1024", lambda X: X @ X), ("zgetrf 2000", lambda X: sla.lu_factor(X, check_finite=False))):
        nn = 1024 if "zgemm" in nome else 2000
        X = np.random.default_rng(0).standard_normal((nn, nn)) + 1j + nn * np.eye(nn)
        fn(X)
        c0, t0 = time.process_time(), time.perf_counter()
        for _ in range(5): fn(X)
        razao = (time.process_time() - c0) / (time.perf_counter() - t0)
        res[f"cpu_por_parede_{nome}"] = razao
        print(f"{nome}: tempo de CPU / parede = {razao:.2f}")
    (out / "teste_concorrencia.json").write_text(json.dumps(res, indent=2))
    scratch.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
