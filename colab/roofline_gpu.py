"""Roofline e modelo de transferencia do kit (roofline.py), generalizado para a
GPU em que o experimento rodou de fato.

O roofline.py original do kit continua sendo executado sem alteracao (ele traz
as constantes da RTX 3090). Este script refaz as MESMAS contas com as
constantes da GPU medida e confronta o modelo com os numeros medidos.

Uso:
  python3 roofline_gpu.py --gpu "Tesla T4" [--sms 40] [--pcie-medido 6.1]
                          [--kernel-bw-medido 250] [--plot roofline.png]

Se a GPU nao estiver na tabela, o script para: nao ha chute de constantes.
"""
import argparse
import sys

# FP32, banda e clock: datasheets/paginas de produto da NVIDIA.
# FP64 = FP32 x razao da arquitetura. Fonte da razao em "fp64_fonte":
#   3090: o proprio kit (1/64). T4: 1/32 = 254 GFLOP/s (Dell HPC brief;
#   Microway mediu 253 GFLOP/s). A100: datasheet NVIDIA (9.7 TF, 1/2).
#   L4: 1/64 e a razao tipica de Ada, NAO confirmada em datasheet.
# PCIe: geracao x16 da placa, com a vazao pratica usada pelo kit
# (24 GB/s em 4.0) e a metade dela em 3.0.
GPUS = {
    "RTX 3090": dict(nome="GeForce RTX 3090", sms=82, cuda_cores=10496, clock=1.695e9,
                     bw=936.2e9, fp64_razao=1 / 64, fp64_fonte="kit", pcie="4.0 x16", pcie_pratico=24e9),
    "T4":       dict(nome="Tesla T4", sms=40, cuda_cores=2560, clock=1.590e9,
                     bw=320e9, fp64_razao=1 / 32, fp64_fonte="Dell/Microway", pcie="3.0 x16", pcie_pratico=12e9),
    "L4":       dict(nome="NVIDIA L4", sms=58, cuda_cores=7424, clock=2.040e9,
                     bw=300e9, fp64_razao=1 / 64, fp64_fonte="NAO CONFIRMADA (razao tipica Ada)", pcie="4.0 x16", pcie_pratico=24e9),
    "A100-SXM4-40GB": dict(nome="A100 SXM4 40GB", sms=108, cuda_cores=6912, clock=1.410e9,
                           bw=1555e9, fp64_razao=1 / 2, fp64_fonte="datasheet NVIDIA", pcie="4.0 x16", pcie_pratico=24e9),
}

# Mesmos kernels e mesma contagem (FLOP, bytes) por elemento do roofline.py do kit
KERNELS_FP32 = [
    ("SAXPY  y=a*x+y", 2, 12),
    ("soma vetorial c=a+b", 1, 12),
    ("produto interno", 2, 8),
    ("stencil 5 pontos", 9, 12),
    ("matmul ingenuo (sem reuso)", 2, 8),
    ("matmul com tile 32x32", 2, 8 / 32),
]
KERNELS_FP64 = [
    ("SAXPY  y=a*x+y", 2, 24),
    ("stencil 5 pontos", 9, 24),
    ("matmul com tile 32x32", 2, 16 / 32),
]


def acha_gpu(nome):
    for chave, spec in GPUS.items():
        if chave.lower() in nome.lower():
            return spec
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", required=True, help="nome reportado por nvidia-smi")
    ap.add_argument("--sms", type=int, help="SMs reportados pelo saxpy_cuda (checagem)")
    ap.add_argument("--pcie-medido", type=float, help="GB/s H->D medido (mediana)")
    ap.add_argument("--kernel-bw-medido", type=float, help="GB/s do kernel medido (mediana)")
    ap.add_argument("--plot", help="arquivo PNG do roofline")
    a = ap.parse_args()

    g = acha_gpu(a.gpu)
    if g is None:
        print(f"GPU '{a.gpu}' fora da tabela de constantes verificadas "
              f"({', '.join(GPUS)}). Adicione os dados do datasheet antes de continuar.")
        sys.exit(2)
    if a.sms is not None and a.sms != g["sms"]:
        print(f"ATENCAO: o dispositivo reporta {a.sms} SMs, a tabela diz {g['sms']}. "
              "Confira o modelo exato antes de usar estes numeros.")

    fp32 = g["cuda_cores"] * 2 * g["clock"]
    fp64 = fp32 * g["fp64_razao"]
    bw = g["bw"]

    print(f"=== Roofline: {g['nome']} (FP32/banda de datasheet) ===")
    print(f"FP32 pico ........ {fp32 / 1e12:7.2f} TFLOP/s  ({g['cuda_cores']} nucleos x 2 x {g['clock'] / 1e9:.3f} GHz)")
    print(f"FP64 pico ........ {fp64 / 1e12:7.2f} TFLOP/s  (1/{round(1 / g['fp64_razao'])} do FP32; fonte: {g['fp64_fonte']})")
    print(f"Banda de memoria . {bw / 1e9:7.1f} GB/s")
    print(f"PCIe ............. {g['pcie']}")
    print("\nEquilibrio da maquina (FLOP por byte para saturar a ALU):")
    print(f"  FP32: {fp32 / bw:6.1f} FLOP/byte")
    print(f"  FP64: {fp64 / bw:6.2f} FLOP/byte")

    pontos = []

    def analisa(nome, flop, by, dp=False):
        pico = fp64 if dp else fp32
        ai = flop / by
        teto = bw * ai
        alc = min(pico, teto)
        regime = "MEMORIA" if teto < pico else "COMPUTO"
        print(f"  {nome:<34} AI={ai:6.3f}  limite={alc / 1e12:7.2f} TF  "
              f"({100 * alc / pico:6.2f}% do pico)  {regime}")
        pontos.append((nome, ai, alc, dp))

    print("\nKernels em FP32 (float):")
    for k in KERNELS_FP32:
        analisa(*k)
    print("\nOs MESMOS kernels em FP64 (double):")
    for k in KERNELS_FP64:
        analisa(*k, dp=True)

    # ---------- modelo de transferencia, como no kit ----------
    pcie = g["pcie_pratico"]
    print(f"\n{'=' * 66}\n MODELO DO PCIe ({g['pcie']}, {pcie / 1e9:.0f} GB/s supostos)\n{'=' * 66}")
    N = 100_000_000
    trans = 12 * N / pcie
    kern = 12 * N / bw
    print(f"  N=1e8: transferencia={1e3 * trans:7.2f} ms  kernel={1e3 * kern:6.3f} ms  razao={trans / kern:5.1f}x")
    for rep in (1, 50):
        print(f"  fracao prevista em transferencia, {rep:>2} repeticao(oes): "
              f"{100 * trans / (trans + rep * kern):5.1f}%")
    print(f"  FLOP/elemento para a transferencia se pagar: {fp32 * 12 / pcie:,.0f}")

    if a.pcie_medido or a.kernel_bw_medido:
        print(f"\n{'=' * 66}\n MODELO x MEDIDO\n{'=' * 66}")
        pm = (a.pcie_medido or pcie / 1e9) * 1e9
        km = (a.kernel_bw_medido or bw / 1e9) * 1e9
        if a.pcie_medido:
            print(f"  PCIe medido (H->D)  {a.pcie_medido:6.1f} GB/s = {100 * pm / pcie:5.1f}% do suposto")
        if a.kernel_bw_medido:
            print(f"  kernel medido       {a.kernel_bw_medido:6.1f} GB/s = {100 * km / bw:5.1f}% do pico de datasheet")
        t2, k2 = 12 * N / pm, 12 * N / km
        print(f"  com as taxas medidas: razao transferencia/kernel = {t2 / k2:.1f}x")
        for rep in (1, 50):
            print(f"  fracao recalculada, {rep:>2} repeticao(oes): {100 * t2 / (t2 + rep * k2):5.1f}%")
        print(f"  FLOP/elemento para pagar a transferencia medida: {fp32 * 12 / pm:,.0f}")

    if a.plot:
        plota(a.plot, g, fp32, fp64, bw, pontos, a.kernel_bw_medido)


def plota(arq, g, fp32, fp64, bw, pontos, kernel_bw_medido):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
    C32, C64, CMED = "#2a78d6", "#eb6834", "#1baf7a"
    ai = np.logspace(-2, 2, 400)
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
    ax.loglog(ai, np.minimum(fp64, bw * ai) / 1e9, color=C64, lw=2, ls="--", label="teto FP64")
    ax.loglog(ai, np.minimum(fp32, bw * ai) / 1e9, color=C32, lw=2, label="teto FP32")
    # (rotulo, deslocamento em pontos, alinhamento) por (kernel, precisao)
    rotulos = {
        ("SAXPY  y=a*x+y", False): ("SAXPY FP32", (-6, 6), "right"),
        ("SAXPY  y=a*x+y", True): ("SAXPY FP64", (6, -9), "left"),
        ("stencil 5 pontos", False): ("stencil FP32", (-6, 6), "right"),
        ("stencil 5 pontos", True): ("stencil FP64", (6, -9), "left"),
        ("matmul com tile 32x32", False): ("matmul tile FP32", (-6, 6), "right"),
        ("matmul com tile 32x32", True): ("matmul tile FP64", (0, -11), "center"),
    }
    for nome, x, y, dp in pontos:
        ax.plot(x, y / 1e9, "o", ms=5, color=C64 if dp else C32, mec="white", mew=1, zorder=3)
        if (nome, dp) in rotulos:
            txt, off, ha = rotulos[(nome, dp)]
            ax.annotate(txt, (x, y / 1e9), textcoords="offset points", xytext=off,
                        ha=ha, fontsize=6.5, color=TEXTO2)
    if kernel_bw_medido:
        x = 2 / 12
        ax.plot(x, kernel_bw_medido * x, "*", ms=11, color=CMED, mec="white", mew=0.8,
                label=f"SAXPY medido ({kernel_bw_medido * x:.0f} GFLOP/s)")
    ax.set_xlabel("intensidade aritmética (FLOP/byte)", fontsize=8, color=TEXTO)
    ax.set_ylabel("desempenho (GFLOP/s)", fontsize=8, color=TEXTO)
    ax.set_title(f"Roofline — {g['nome']}", fontsize=9, color=TEXTO, loc="left")
    ax.grid(which="major", color=GRADE, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(TEXTO2)
    ax.tick_params(colors=TEXTO2, labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(arq)
    print(f"\nGrafico: {arq}")


if __name__ == "__main__":
    main()
