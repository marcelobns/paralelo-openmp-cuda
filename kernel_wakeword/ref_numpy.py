"""Interpretador mínimo, em numpy, dos 3 grafos do openWakeWord, em qualquer dtype.

Existe porque o onnxruntime não tem Conv em float64: sem ele não há referência FP64
para responder "FP32 é aceitável?". Cobre só os operadores destes três modelos e
recusa qualquer outro. Validado contra o onnxruntime FP32 (ver precisao.py).
"""
import functools

import numpy as np
import onnx
from numpy.lib.stride_tricks import sliding_window_view
from onnx import numpy_helper


def _attrs(n):
    return {a.name: onnx.helper.get_attribute_value(a) for a in n.attribute}


def _conv(x, w, b, at):
    nd = w.ndim - 2
    strides = at.get("strides", [1] * nd)
    dil = at.get("dilations", [1] * nd)
    assert all(d == 1 for d in dil) and at.get("group", 1) == 1
    pads = at.get("pads", [0] * (2 * nd))
    if at.get("auto_pad", b"NOTSET") not in (b"NOTSET", "NOTSET"):
        raise ValueError("auto_pad não suportado")
    pw = [(0, 0), (0, 0)] + [(pads[i], pads[i + nd]) for i in range(nd)]
    x = np.pad(x, pw)
    win = sliding_window_view(x, w.shape[2:], axis=tuple(range(2, 2 + nd)))
    sl = (slice(None), slice(None)) + tuple(slice(None, None, s) for s in strides)
    win = win[sl]                                   # N, Cin, *out, *k
    if nd == 1:
        y = np.einsum("ncok,dck->ndo", win, w, optimize=True)
    else:
        y = np.einsum("ncijkl,dckl->ndij", win, w, optimize=True)
    if b is not None:
        y = y + b.reshape((1, -1) + (1,) * nd)
    return y


def _maxpool(x, at):
    k = at["kernel_shape"]
    s = at.get("strides", k)
    pads = at.get("pads", [0] * 4)
    assert not any(pads)
    win = sliding_window_view(x, k, axis=(2, 3))[:, :, ::s[0], ::s[1]]
    return win.max(axis=(-1, -2))


class Grafo:
    def __init__(self, caminho, dtype):
        self.dt = dtype
        g = onnx.load(caminho).graph
        self.g = g
        self.init = {i.name: numpy_helper.to_array(i) for i in g.initializer}

    def run(self, x):
        dt = self.dt
        v = {k: (a.astype(dt) if a.dtype.kind == "f" else a) for k, a in self.init.items()}
        v[self.g.input[0].name] = np.asarray(x, dtype=dt)
        for n in self.g.node:
            at, op = _attrs(n), n.op_type
            i = [v[k] if k else None for k in n.input]
            if op == "Constant":
                a = numpy_helper.to_array(at["value"])
                y = a.astype(dt) if a.dtype.kind == "f" else a
            elif op == "Unsqueeze":
                y = np.expand_dims(i[0], tuple(int(a) for a in np.atleast_1d(i[1])))
            elif op == "Transpose":
                y = np.transpose(i[0], at["perm"])
            elif op == "Reshape":
                y = i[0].reshape([int(s) if s != 0 else i[0].shape[j] for j, s in enumerate(i[1])])
            elif op == "Flatten":
                ax = at.get("axis", 1)
                y = i[0].reshape(int(np.prod(i[0].shape[:ax])), -1)
            elif op == "Cast":
                y = i[0].astype(dt)
            elif op == "Conv":
                y = _conv(i[0], i[1], i[2] if len(i) > 2 else None, at)
            elif op == "MaxPool":
                y = _maxpool(i[0], at)
            elif op == "MatMul":
                y = i[0] @ i[1]
            elif op == "Gemm":
                a = i[0].T if at.get("transA", 0) else i[0]
                b = i[1].T if at.get("transB", 0) else i[1]
                y = at.get("alpha", 1.0) * (a @ b)
                if len(i) > 2 and i[2] is not None:
                    y = y + at.get("beta", 1.0) * i[2]
            elif op == "Pow":
                y = np.power(i[0], i[1])
            elif op == "Add":
                y = i[0] + i[1]
            elif op == "Sub":
                y = i[0] - i[1]
            elif op == "Mul":
                y = i[0] * i[1]
            elif op == "Div":
                y = i[0] / i[1]
            elif op == "Log":
                y = np.log(i[0])
            elif op == "Sqrt":
                y = np.sqrt(i[0])
            elif op == "Relu":
                y = np.maximum(i[0], 0)
            elif op == "Sigmoid":
                y = 1 / (1 + np.exp(-i[0]))
            elif op == "LeakyRelu":
                y = np.where(i[0] >= 0, i[0], at.get("alpha", 0.01) * i[0])
            elif op == "Max":
                y = functools.reduce(np.maximum, i)
            elif op == "Clip":
                lo = i[1] if len(i) > 1 and i[1] is not None else -np.inf
                hi = i[2] if len(i) > 2 and i[2] is not None else np.inf
                y = np.clip(i[0], lo, hi)
            elif op == "ReduceMax":
                axes = at.get("axes")
                y = np.max(i[0], axis=None if axes is None else tuple(axes),
                           keepdims=bool(at.get("keepdims", 1)))
            elif op == "ReduceMean":
                axes = at.get("axes", None)
                if axes is None and len(i) > 1 and i[1] is not None:
                    axes = list(i[1])
                y = np.mean(i[0], axis=None if axes is None else tuple(axes),
                            keepdims=bool(at.get("keepdims", 1)))
            else:
                raise ValueError(f"operador não suportado: {op}")
            y = np.asarray(y)
            if y.dtype.kind == "f":
                y = y.astype(dt, copy=False)
            v[n.output[0]] = y
        return v[self.g.output[0].name]
