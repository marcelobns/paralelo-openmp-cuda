"""Resumo do Bloco 2 (SAXPY OpenMP) coletado por coleta_mac.sh.

Le bloco2_saxpy_omp.csv, calcula mediana/min/max por (N, threads), define o
ponto de saturacao e gera o grafico (se matplotlib estiver disponivel).

Uso: python3 mac/resumo_mac.py resultados/mac_<data>
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PICO_TEORICO_GBS = 153.0   # Apple, anuncio do M5 (out/2025): banda da memoria unificada
NUCLEOS_P = 4
LIMIAR_SATURACAO = 0.95    # menor nº de threads cuja mediana atinge 95% da maior mediana

out = Path(sys.argv[1])
dados = defaultdict(list)
with open(out / "bloco2_saxpy_omp.csv") as f:
    for r in csv.DictReader(f):
        dados[(int(r["N"]), int(r["threads"]))].append(float(r["gbs"]))

linhas = []
for (n, t), v in sorted(dados.items()):
    linhas.append(dict(N=n, threads=t, reps=len(v), mediana=statistics.median(v),
                       minimo=min(v), maximo=max(v),
                       cv=100 * statistics.pstdev(v) / statistics.mean(v)))

with open(out / "bloco2_resumo.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0]))
    w.writeheader()
    w.writerows(linhas)

txt = []
p = txt.append
for n in sorted({l["N"] for l in linhas}):
    sub = [l for l in linhas if l["N"] == n]
    p(f"\nN = {n:,}  ({12 * n / 1e9:.1f} GB movidos por execucao)")
    p(f"  {'threads':>7} {'mediana GB/s':>13} {'min':>8} {'max':>8} {'CV%':>6} {'speedup':>8}")
    base = sub[0]["mediana"]
    for l in sub:
        tag = "  (P)" if l["threads"] <= NUCLEOS_P else ""
        p(f"  {l['threads']:>7} {l['mediana']:>13.1f} {l['minimo']:>8.1f} {l['maximo']:>8.1f}"
          f" {l['cv']:>6.1f} {l['mediana'] / base:>7.2f}x{tag}")
    melhor = max(sub, key=lambda l: l["mediana"])
    sat = next(l for l in sub if l["mediana"] >= LIMIAR_SATURACAO * melhor["mediana"])
    p(f"  -> maior mediana: {melhor['mediana']:.1f} GB/s com {melhor['threads']} threads "
      f"({100 * melhor['mediana'] / PICO_TEORICO_GBS:.0f}% dos {PICO_TEORICO_GBS:.0f} GB/s anunciados)")
    p(f"  -> saturacao (>= {LIMIAR_SATURACAO:.0%} da maior mediana): {sat['threads']} threads")
    p(f"  -> maior execucao individual: {max(l['maximo'] for l in sub):.1f} GB/s")

    um = dados[(n, 1)]
    if max(um) > 1.5 * min(um):
        p(f"  ATENCAO: 1 thread variou de {min(um):.1f} a {max(um):.1f} GB/s (bimodal?)."
          " Provavel alternancia entre nucleo P e E: use a mediana e cite a faixa.")

n0 = min(l["N"] for l in linhas)
sub0 = [l for l in linhas if l["N"] == n0]
melhor0 = max(sub0, key=lambda l: l["mediana"])
sat0 = next(l for l in sub0 if l["mediana"] >= LIMIAR_SATURACAO * melhor0["mediana"])
p("\n=== Linhas do Bloco 5 (N = 5e7, comando do roteiro) ===")
p(f"  Ponto de saturacao medido no OpenMP (threads): {sat0['threads']}")
p(f"  Banda maxima observada na CPU (GB/s):          {melhor0['mediana']:.1f} (mediana; pico individual "
  f"{max(l['maximo'] for l in sub0):.1f})")
p("  Cuidado ao interpretar: ate 4 threads o ganho vem dos nucleos P; depois entram os")
p("  nucleos E, mais lentos, e o schedule static divide o laco em partes iguais. Um")
p("  plato logo apos 4 threads pode ser desbalanceamento, nao so banda de memoria.")
p("  Compare a maior mediana com os 153 GB/s teoricos para sustentar o argumento.")

resumo = "\n".join(txt)
print(resumo)
(out / "bloco2_resumo.txt").write_text(resumo + "\n")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("\n(matplotlib ausente: grafico nao gerado)")
    sys.exit(0)

TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
CORES = ["#2a78d6", "#eb6834"]
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
for i, n in enumerate(sorted({l["N"] for l in linhas})):
    sub = [l for l in linhas if l["N"] == n]
    t = [l["threads"] for l in sub]
    ax.fill_between(t, [l["minimo"] for l in sub], [l["maximo"] for l in sub],
                    color=CORES[i], alpha=0.15, linewidth=0)
    ax.plot(t, [l["mediana"] for l in sub], color=CORES[i], lw=2, marker="o", ms=4,
            label=f"N = {n:.0e} (mediana; faixa = min–max)".replace("e+0", "e"))
ax.axhline(PICO_TEORICO_GBS, color=TEXTO2, lw=1, ls="--")
ax.text(16, PICO_TEORICO_GBS + 2, f"pico teórico {PICO_TEORICO_GBS:.0f} GB/s", ha="right",
        va="bottom", fontsize=7, color=TEXTO2)
ax.axvspan(0.5, NUCLEOS_P + 0.5, color=GRADE, alpha=0.5, linewidth=0)
ax.text(2.5, 4, "núcleos P", ha="center", fontsize=7, color=TEXTO2)
ax.set_xlabel("threads (OMP_NUM_THREADS)", color=TEXTO, fontsize=8)
ax.set_ylabel("banda efetiva (GB/s)", color=TEXTO, fontsize=8)
ax.set_title("SAXPY OpenMP no Apple M5 (4P + 6E)", color=TEXTO, fontsize=9, loc="left")
ax.set_xticks(sorted({l["threads"] for l in linhas}))
ax.set_ylim(0, PICO_TEORICO_GBS * 1.12)
ax.set_xlim(0.5, 16.5)
ax.grid(axis="y", color=GRADE, lw=0.6)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(TEXTO2)
ax.tick_params(colors=TEXTO2, labelsize=7)
ax.legend(fontsize=7, frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(out / "bloco2_saxpy_omp.png")
print(f"\nGrafico: {out / 'bloco2_saxpy_omp.png'}")
