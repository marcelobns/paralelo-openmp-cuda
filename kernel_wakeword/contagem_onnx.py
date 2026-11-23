"""Contagem de FLOP e bytes da cadeia do wake word (openWakeWord) direto dos grafos ONNX.

Para cada modelo, expõe todo tensor intermediário como saída, roda uma inferência
no onnxruntime (CPU) com a forma real de entrada e lê a forma de cada tensor.
FLOP por nó:
  Conv    2 * N * Cout * prod(saída espacial) * (Cin/group) * prod(kernel)  (+ bias)
  MatMul  2 * M * N * K (com lote);  Gemm  2 * M * N * K + M * N (bias)
  elemento a elemento (Add, Mul, Pow, Log, Clip, LeakyRelu, Max, Relu, Sigmoid, ...)
          1 FLOP por elemento de saída (transcendentais contam como 1)
  Reduce* 1 FLOP por elemento de entrada;  MaxPool não conta (comparação, não FLOP)
Bytes por inferência (float32, 4 B):
  compulsório = pesos + entrada + saída        -> AI máxima
  sem reuso   = pesos + Σ (entradas + saídas de cada nó)  -> AI mínima
                (cada operador lê e escreve seus tensores na memória)

Uso: uv run --with onnx --with onnxruntime --with numpy python3 kernel_wakeword/contagem_onnx.py \
        --modelos ~/Projects/diagrama-cloud/web/public/wakeword
"""
import argparse
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import numpy_helper

ELEM = {"Add", "Sub", "Mul", "Div", "Pow", "Log", "Clip", "LeakyRelu", "Max", "Relu",
        "Sigmoid", "Sqrt"}
SEM_FLOP = {"Constant", "Unsqueeze", "Transpose", "Reshape", "Flatten", "Cast", "MaxPool"}


def conta(caminho, forma_entrada):
    m = onnx.load(caminho)
    g = m.graph
    pesos = {i.name: numpy_helper.to_array(i) for i in g.initializer}
    consts = {}
    for n in g.node:
        if n.op_type == "Constant":
            consts[n.output[0]] = numpy_helper.to_array(n.attribute[0].t)
    # expõe todos os intermediários
    existentes = {o.name for o in g.output}
    for n in g.node:
        for o in n.output:
            if o and o not in existentes:
                g.output.append(onnx.ValueInfoProto(name=o))
    s = ort.InferenceSession(m.SerializeToString(), providers=["CPUExecutionProvider"])
    x = np.random.default_rng(0).uniform(-1, 1, forma_entrada).astype(np.float32)
    nomes = [o.name for o in s.get_outputs()]
    outs = dict(zip(nomes, s.run(None, {s.get_inputs()[0].name: x})))
    forma = {k: np.asarray(v).shape for k, v in outs.items()}
    forma[g.input[0].name] = x.shape
    for k, v in pesos.items():
        forma[k] = v.shape
    for k, v in consts.items():
        forma[k] = v.shape

    def tam(nome):
        return int(np.prod(forma[nome])) if nome in forma else 0

    flop, io, por_op, convs = 0, 0, {}, []
    for n in g.node:
        op = n.op_type
        f = 0
        if op == "Conv":
            w = forma[n.input[1]]                      # Cout, Cin/g, kH, kW
            y = forma[n.output[0]]                     # N, Cout, *espacial
            f = 2 * y[0] * y[1] * int(np.prod(y[2:])) * int(np.prod(w[1:]))
            if len(n.input) > 2:
                f += int(np.prod(y))
            at = {a.name: onnx.helper.get_attribute_value(a) for a in n.attribute}
            convs.append(dict(peso=list(w), saida=list(y), strides=at.get("strides"),
                              pads=at.get("pads"), group=at.get("group", 1)))
        elif op == "MatMul":
            a, b = forma[n.input[0]], forma[n.input[1]]
            y = forma[n.output[0]]
            f = 2 * int(np.prod(y)) * a[-1]
        elif op == "Gemm":
            y = forma[n.output[0]]
            a = forma[n.input[0]]
            at = {a_.name: onnx.helper.get_attribute_value(a_) for a_ in n.attribute}
            k = a[0] if at.get("transA", 0) else a[1]
            f = 2 * int(np.prod(y)) * k + (int(np.prod(y)) if len(n.input) > 2 else 0)
        elif op in ELEM:
            f = tam(n.output[0])
        elif op.startswith("Reduce"):
            f = tam(n.input[0])
        elif op not in SEM_FLOP:
            raise ValueError(f"operador sem regra de contagem: {op}")
        flop += f
        por_op[op] = por_op.get(op, 0) + f
        if op != "Constant":
            io += sum(tam(i) for i in n.input if i and i not in pesos and i not in consts)
            io += sum(tam(o) for o in n.output if o)
    n_pesos = sum(v.size for v in pesos.values()) + sum(v.size for v in consts.values())
    b_pesos = 4 * n_pesos
    b_comp = b_pesos + 4 * (tam(g.input[0].name) + sum(tam(o.name) for o in s.get_outputs()[:1]))
    b_sem_reuso = b_pesos + 4 * io
    return dict(entrada=list(forma_entrada), flop=flop, parametros=int(n_pesos),
                bytes_pesos=b_pesos, bytes_compulsorio=b_comp, bytes_sem_reuso=b_sem_reuso,
                ai_max=flop / b_comp, ai_min=flop / b_sem_reuso,
                flop_por_operador=por_op, convs=convs,
                saida=list(forma[nomes[0]]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", required=True)
    ap.add_argument("--out", default="resultados/kernel_wakeword/contagem_onnx.json")
    a = ap.parse_args()
    d = Path(a.modelos).expanduser()
    casos = {
        "mel_janela_1.2s": ("melspectrogram.onnx", (1, 19200)),
        "mel_incremental": ("melspectrogram.onnx", (1, 1632)),
        "mel_incremental_b8": ("melspectrogram.onnx", (8, 1632)),
        "mel_incremental_b32": ("melspectrogram.onnx", (32, 1632)),
        "embedding": ("embedding_model.onnx", (1, 76, 32, 1)),
        "embedding_b8": ("embedding_model.onnx", (8, 76, 32, 1)),
        "embedding_b32": ("embedding_model.onnx", (32, 76, 32, 1)),
        "classificador": ("laudomiro.onnx", (1, 16, 96)),
    }
    res = {k: conta(str(d / arq), f) for k, (arq, f) in casos.items()}
    for k, r in res.items():
        print(f"{k:22s} FLOP {r['flop'] / 1e6:8.2f} M  pesos {r['bytes_pesos'] / 1e6:5.2f} MB  "
              f"compulsório {r['bytes_compulsorio'] / 1e6:5.2f} MB  sem reuso {r['bytes_sem_reuso'] / 1e6:6.2f} MB  "
              f"AI {r['ai_min']:.2f}–{r['ai_max']:.2f}  saída {r['saida']}")
    print("convs do mel:", res["mel_janela_1.2s"]["convs"])
    cad = ("mel_janela_1.2s", "embedding", "classificador")
    tot = {c: sum(res[k][c] for k in cad) for c in ("flop", "bytes_compulsorio", "bytes_sem_reuso")}
    tot["ai_max"] = tot["flop"] / tot["bytes_compulsorio"]
    tot["ai_min"] = tot["flop"] / tot["bytes_sem_reuso"]
    res["cadeia_atual"] = tot
    cad2 = ("mel_incremental", "embedding", "classificador")
    tot2 = {c: sum(res[k][c] for k in cad2) for c in ("flop", "bytes_compulsorio", "bytes_sem_reuso")}
    tot2["ai_max"] = tot2["flop"] / tot2["bytes_compulsorio"]
    tot2["ai_min"] = tot2["flop"] / tot2["bytes_sem_reuso"]
    res["cadeia_mel_incremental"] = tot2
    for k in ("cadeia_atual", "cadeia_mel_incremental"):
        t = res[k]
        print(f"{k:22s} FLOP {t['flop'] / 1e6:8.2f} M  compulsório {t['bytes_compulsorio'] / 1e6:5.2f} MB  "
              f"AI {t['ai_min']:.2f}–{t['ai_max']:.2f}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
