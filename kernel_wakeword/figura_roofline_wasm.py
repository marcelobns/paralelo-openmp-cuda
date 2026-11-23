"""Roofline empírico do onnxruntime-web (wasm, 1 thread) em node:24.18-alpine, com a cadeia
do wake word. Tetos medidos na mesma imagem: MatMul 1024³ (bancada.mjs) e cópia nativa de 128 MB
(banda_copia.mjs, mediana de 9 execuções).
Cada etapa aparece como faixa de AI [sem reuso, compulsório] na altura do GFLOP/s medido.

Uso: uv run --with matplotlib --with numpy python3 kernel_wakeword/figura_roofline_wasm.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

R = Path("resultados/kernel_wakeword")
t = json.loads((R / "tempos_t1.json").read_text())
k = json.loads((R / "contagem_onnx.json").read_text())
pk = t["tetos"]["matmul_gflops_p50"]
# banda: cópia nativa (banda_copia.mjs). O Add do ORT (16 GB/s) inclui copiar as entradas
# para o heap do wasm e a saída de volta, e por isso não serve de teto de memória.
bw = json.loads((R / "banda_copia.json").read_text())["gbs_mediana"]
c = t["casos"]
TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"

fig, ax = plt.subplots(figsize=(3.5, 2.35), dpi=300)
ai = np.logspace(-1, 2.3, 300)
ax.loglog(ai, np.minimum(pk, bw * ai), color=TEXTO2, lw=1.6)
ax.text(0.105, bw * 0.105 * 1.9, f"cópia {bw:.0f} GB/s", rotation=36, fontsize=5.5, color=TEXTO2,
        rotation_mode="anchor")
ax.text(0.9, pk * 1.12, f"MatMul {pk:.0f} GFLOP/s", ha="left", fontsize=5.5, color=TEXTO2)


def faixa(chave, caso, cor, rot, dy, dx=0):
    r = k[chave]
    gf = r["flop"] / (c[caso]["p50_ms"] / 1e3) / 1e9
    lo, hi = r["ai_min"], r["ai_max"]
    ax.plot([lo, hi], [gf, gf], color=cor, lw=2, solid_capstyle="round")
    ax.plot([lo, hi], [gf, gf], "|", color=cor, ms=6, mew=1.5)
    ax.annotate(f"{rot} {gf:.0f}", (np.sqrt(lo * hi), gf), textcoords="offset points",
                xytext=(dx, dy), ha="center", fontsize=5.5, color=TEXTO)
    return gf


faixa("mel_janela_1.2s", "mel_janela", C2, "mel, janela 1,2 s", 4, 12)
faixa("embedding", "embedding", C2, "embedding", -8, 0)
faixa("mel_incremental", "mel_incremental", C1, "mel incremental", -9)
faixa("mel_incremental_b32", "mel_incremental_b32", C3, "mel incr., lote 32", -9, 0)
faixa("classificador", "classificador", C2, "classificador", 4)
ax.set_xlabel("intensidade aritmética (FLOP/byte)", fontsize=6.5, color=TEXTO)
ax.set_ylabel("GFLOP/s (FP32, wasm, 1 thread)", fontsize=6.5, color=TEXTO)
ax.set_ylim(3, 120)
ax.grid(which="major", color=GRADE, lw=0.4)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(TEXTO2)
ax.tick_params(colors=TEXTO2, labelsize=5.5)
fig.tight_layout(pad=0.3)
out = Path("relatorio/fig_roofline_wasm.pdf")
fig.savefig(out)
fig.savefig(out.with_suffix(".png"))
print(out, f"teto {pk:.1f} GFLOP/s, banda {bw:.1f} GB/s, equilíbrio {pk / bw:.2f} FLOP/B")
