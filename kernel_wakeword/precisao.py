"""FP32 é aceitável? Compara os scores do fluxo medidos no container (onnxruntime-web,
wasm, FP32 e int8) com uma referência FP64 do MESMO laço, calculada pelo interpretador
numpy (ref_numpy.py), porque o onnxruntime não tem Conv em float64.

Uso (depois de prep.py e da fase fluxo da bancada):
  uv run --with onnx --with numpy python3 kernel_wakeword/precisao.py \
     --modelos ~/Projects/diagrama-cloud/web/public/wakeword --w <dir de trabalho>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from ref_numpy import Grafo  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--modelos", required=True)
ap.add_argument("--w", required=True)
ap.add_argument("--res", default="resultados/kernel_wakeword")
a = ap.parse_args()
D = Path(a.modelos).expanduser()
W = Path(a.w)
R = Path(a.res)
LIMIAR = 0.5
STEP, RAW, EMB_F, WW_F = 1280, 19200, 76, 16

mel, emb, clf = (Grafo(str(D / f), np.float64) for f in
                 ("melspectrogram.onnx", "embedding_model.onnx", "laudomiro.onnx"))
clipes = json.loads((W / "audio.json").read_text())
todo = np.fromfile(W / "audio.f32", dtype=np.float32)
medido = json.loads((R / "fluxo_scores.json").read_text())["clipes"]

ref, err_emb = [], []
for c, m in zip(clipes, medido):
    assert c["arquivo"] == m["arquivo"]
    audio = todo[c["inicio"]:c["inicio"] + c["n"]].astype(np.float64)
    raw = np.zeros(0)
    embs, sc = [], []
    for p in range(0, audio.size - STEP + 1, STEP):
        raw = np.concatenate([raw, audio[p:p + STEP]])[-RAW:]
        if raw.size < RAW * 0.6:
            sc.append(None); continue
        mo = mel.run(raw[None, :])
        n = mo.shape[-2]
        if n < EMB_F:
            sc.append(None); continue
        jan = mo.reshape(n, 32)[-EMB_F:] / 10 + 2
        embs.append(emb.run(jan[None, :, :, None]).ravel())
        embs = embs[-WW_F:]
        if len(embs) < WW_F:
            sc.append(None); continue
        sc.append(float(clf.run(np.stack(embs)[None]).ravel()[0]))
    ref.append(sc)
    print(f"{c['arquivo']:14s} FP64 max {max(s for s in sc if s is not None):.4f}  "
          f"FP32 {max(s for s in m['scores']['producao'] if s is not None):.4f}", flush=True)

res = {"limiar": LIMIAR, "n_clipes": len(clipes), "n_positivos": sum(c["positivo"] for c in clipes)}
for var in ("producao", "mel_incremental", "embedding_int8", "tudo_int8"):
    d, flips, det, n = [], 0, {"vp": 0, "fn": 0, "fp": 0, "vn": 0}, 0
    for c, m, r in zip(clipes, medido, ref):
        s = m["scores"][var]
        assert len(s) == len(r)
        pares = [(x, y) for x, y in zip(s, r) if x is not None and y is not None]
        n += len(pares)
        d += [abs(x - y) for x, y in pares]
        flips += sum((x >= LIMIAR) != (y >= LIMIAR) for x, y in pares)
        dispara = max(x for x, _ in pares) >= LIMIAR
        det[("vp" if dispara else "fn") if c["positivo"] else ("fp" if dispara else "vn")] += 1
    res[var] = dict(passos=n, max_abs_dscore_vs_fp64=max(d), mediana_abs_dscore=float(np.median(d)),
                    passos_que_cruzam_limiar_diferente=int(flips), deteccao_por_clipe=det)
    print(f"{var:16s} vs FP64: max|Δscore| {max(d):.2e}  mediana {np.median(d):.1e}  "
          f"passos com decisão diferente {flips}/{n}  clipes {det}")
# referência FP64 sozinha
det = {"vp": 0, "fn": 0, "fp": 0, "vn": 0}
for c, r in zip(clipes, ref):
    dispara = max(x for x in r if x is not None) >= LIMIAR
    det[("vp" if dispara else "fn") if c["positivo"] else ("fp" if dispara else "vn")] += 1
res["fp64_deteccao_por_clipe"] = det
(R / "precisao.json").write_text(json.dumps(res, indent=2))
print("FP64:", det)
