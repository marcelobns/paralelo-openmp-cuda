// Banda de memória na imagem: cópia nativa (TypedArray.set ≈ memcpy), 8 B por elemento FP32
// (lê 4, grava 4), fora do cache (2^25 elementos = 128 MB por vetor). 15 repetições.
const n = 1 << 25, src = new Float32Array(n).fill(1), dst = new Float32Array(n);
for (let i = 0; i < 3; i++) dst.set(src);
const ts = [];
for (let r = 0; r < 15; r++) { const t = performance.now(); dst.set(src); ts.push(performance.now() - t); }
ts.sort((a, b) => a - b);
const gb = (ms) => (8 * n) / (ms / 1e3) / 1e9;
console.log(JSON.stringify({ n, p50_ms: ts[7], gbs_p50: gb(ts[7]), gbs_max: gb(ts[0]) }));
