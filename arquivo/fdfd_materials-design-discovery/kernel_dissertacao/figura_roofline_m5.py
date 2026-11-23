"""Roofline empírico de 1 thread do Apple M5 com os pontos medidos do kernel FDFD.

Tetos medidos (não de datasheet):
  memória  = mediana do SAXPY OpenMP com 1 thread (resultados/mac_*/bloco2_resumo.csv, N=5e7)
  cômputo  = zgemm 1024 (Accelerate, 1 thread)  (resultados/kernel_fdfd/kernel_fdfd_extra.json)
Pontos: LU esparsa (SuperLU) da janela e da grade inteira, desenhados como intervalo de AI
[limite inferior efetivo: janela = vazão agregada de 6 workers / banda agregada medida
(teste_concorrencia.py); grade = GFLOP/s / banda de 1 thread; limite superior = tráfego compulsório];
solução triangular (3 lados direitos); LU densa (zgetrf) de 486 e 2000 (AI = n/12).

Uso: uv run --with matplotlib python3 kernel_dissertacao/figura_roofline_m5.py
"""
import csv
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

R = Path("resultados")
mac = sorted(glob.glob(str(R / "mac_*/bloco2_resumo.csv")))[-1]
bw1 = next(float(r["mediana"]) for r in csv.DictReader(open(mac))
           if r["N"] == "50000000" and r["threads"] == "1")
k = json.loads((R / "kernel_fdfd/kernel_fdfd.json").read_text())
x = json.loads((R / "kernel_fdfd/kernel_fdfd_extra.json").read_text())
peak = x["zgemm_1024_gflops"]
conc = json.loads((R / "kernel_fdfd/teste_concorrencia.json").read_text())["vazao_fat_por_s"]
bw_all = max(float(r["mediana"]) for r in csv.DictReader(open(mac)) if r["N"] == "50000000")

jan = k["janela"][1]
gi = k["grade_inteira"]
TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"

fig, ax = plt.subplots(figsize=(3.5, 2.45), dpi=300)
ai = np.logspace(-1.3, 2.5, 300)
ax.loglog(ai, np.minimum(peak, bw1 * ai), color=TEXTO2, lw=1.6)
ax.text(0.075, bw1 * 0.075 * 2.6, f"banda 1 thread {bw1:.0f} GB/s", rotation=31, fontsize=5.5,
        color=TEXTO2, rotation_mode="anchor")
ax.text(250, peak * 1.12, f"zgemm 1 thread {peak:.0f} GFLOP/s", ha="right", fontsize=5.5, color=TEXTO2)


def faixa(lo, hi, y, cor, rot, dy, dx=0):
    ax.plot([lo, hi], [y, y], color=cor, lw=2, solid_capstyle="round")
    ax.plot([lo, hi], [y, y], "|", color=cor, ms=6, mew=1.5)
    ax.annotate(rot, (np.sqrt(lo * hi), y), textcoords="offset points", xytext=(dx, dy),
                ha="center", fontsize=5.5, color=TEXTO)


ai_min_jan = max(conc.values()) * jan["flop"] / 1e9 / bw_all   # vazão agregada / banda agregada
faixa(ai_min_jan, jan["ai_max"], jan["gflops_fat"], C2,
      f"LU esparsa janela (SuperLU) {jan['gflops_fat']:.0f} GFLOP/s", -9, 34)
faixa(gi["gflops_fat"] / bw1, gi["ai_max"], gi["gflops_fat"], C2,
      f"LU esparsa grade inteira {gi['gflops_fat']:.0f}", 4)
ts = jan["flop_sol"] / jan["t_sol_s"] / 1e9
ax.plot(jan["ai_sol"], ts, "o", color=C1, ms=4, mec="white", mew=0.6)
ax.annotate(f"solução 3 RHS {ts:.0f}", (jan["ai_sol"], ts), textcoords="offset points",
            xytext=(3, -15), ha="left", fontsize=5.5, color=TEXTO)
for key, nn in (("lu_densa_borda", 486), ("lu_densa_2000", 2000)):
    gf = x[key]["gflops"]
    ax.plot(nn / 12, gf, "s", color=C3, ms=4, mec="white", mew=0.6)
    ax.annotate(f"LU densa {nn} {gf:.0f}", (nn / 12, gf), textcoords="offset points",
                xytext=(0, -9), ha="center", fontsize=5.5, color=TEXTO)
ax.set_xlabel("intensidade aritmética (FLOP/byte)", fontsize=6.5, color=TEXTO)
ax.set_ylabel("GFLOP/s (complex128)", fontsize=6.5, color=TEXTO)
ax.set_ylim(3, 900)
ax.grid(which="major", color=GRADE, lw=0.4)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(TEXTO2)
ax.tick_params(colors=TEXTO2, labelsize=5.5)
fig.tight_layout(pad=0.3)
out = Path("relatorio/fig_roofline_m5.pdf")
out.parent.mkdir(exist_ok=True)
fig.savefig(out)
fig.savefig(out.with_suffix(".png"))
print(out, f"(banda 1t {bw1:.1f} GB/s, teto {peak:.0f} GFLOP/s)")
