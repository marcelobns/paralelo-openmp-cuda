"""Prepara as entradas da bancada do wake word (roda no host; não escreve no diagrama-cloud).

1. Áudio: os 48 clipes de metrics/datasets/vozes.v1 (24 kHz, int16) reamostrados para
   16 kHz float32, com 1,5 s de ruído de fundo antes (aquece o fluxo, como a escuta
   armada) e 1 s depois. Ruído gaussiano σ = 1e-3 (≈ −60 dBFS), semente fixa.
   Frase 0 de cada voz contém "Laudomiro" (positivo); frases 1–5 não (negativos).
2. Variante int8 dos modelos (onnxruntime.quantization.quantize_dynamic, pesos int8,
   ativações quantizadas por chamada).
3. Modelos sintéticos dos tetos no MESMO runtime: MatMul 1024³ (cômputo) e Add de
   2²² elementos (memória: 48 MB por chamada).

Uso: uv run --with onnx --with onnxruntime --with numpy --with scipy python3 \
        kernel_wakeword/prep.py --dc ~/Projects/diagrama-cloud --out <dir de trabalho>
"""
import argparse
import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper
from onnxruntime.quantization import QuantType, quantize_dynamic
from scipy.io import wavfile
from scipy.signal import resample_poly

ap = argparse.ArgumentParser()
ap.add_argument("--dc", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
dc = Path(a.dc).expanduser()
out = Path(a.out)
(out / "modelos").mkdir(parents=True, exist_ok=True)

# 1. áudio
rng = np.random.default_rng(20261122)
clipes, blocos, pos = [], [], 0
for w in sorted((dc / "metrics/datasets/vozes.v1").glob("*.wav")):
    sr, x = wavfile.read(w)
    assert sr == 24000 and x.dtype == np.int16
    y = resample_poly(x.astype(np.float64) / 32768.0, 2, 3)
    y = np.concatenate([rng.normal(0, 1e-3, 24000), y + rng.normal(0, 1e-3, y.size),
                        rng.normal(0, 1e-3, 16000)]).astype(np.float32)
    voz, frase = w.stem.rsplit("-", 1)
    clipes.append(dict(arquivo=w.name, voz=voz, frase=int(frase), positivo=frase == "0",
                       inicio=pos, n=int(y.size)))
    blocos.append(y)
    pos += y.size
np.concatenate(blocos).tofile(out / "audio.f32")
(out / "audio.json").write_text(json.dumps(clipes, indent=1))
print(f"{len(clipes)} clipes, {pos / 16000:.0f} s de áudio, {sum(c['positivo'] for c in clipes)} positivos")

# 2. int8
for m in ("melspectrogram", "embedding_model", "laudomiro"):
    quantize_dynamic(str(dc / f"web/public/wakeword/{m}.onnx"), str(out / f"modelos/{m}.int8.onnx"),
                     weight_type=QuantType.QInt8)
    g = onnx.load(str(out / f"modelos/{m}.int8.onnx")).graph
    ops = sorted({n.op_type for n in g.node})
    print(f"int8 {m}: {', '.join(o for o in ops if 'Integer' in o or 'Quant' in o) or 'NADA quantizado'}")

# 3. tetos
def salva(nome, nos, entradas, saida):
    g = helper.make_graph(nos, nome, entradas, [saida])
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 8
    onnx.save(m, str(out / f"modelos/{nome}.onnx"))

N = 1024
salva("teto_matmul", [helper.make_node("MatMul", ["A", "B"], ["C"])],
      [helper.make_tensor_value_info("A", TensorProto.FLOAT, [N, N]),
       helper.make_tensor_value_info("B", TensorProto.FLOAT, [N, N])],
      helper.make_tensor_value_info("C", TensorProto.FLOAT, [N, N]))
M = 1 << 22
salva("teto_add", [helper.make_node("Add", ["X", "Y"], ["Z"])],
      [helper.make_tensor_value_info("X", TensorProto.FLOAT, [M]),
       helper.make_tensor_value_info("Y", TensorProto.FLOAT, [M])],
      helper.make_tensor_value_info("Z", TensorProto.FLOAT, [M]))
print("modelos:", sorted(p.name for p in (out / "modelos").iterdir()))
