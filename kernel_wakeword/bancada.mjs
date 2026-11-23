/**
 * Bancada da cadeia do wake word (web/lib/wakeword.ts) no runtime da imagem
 * node:24.18-alpine: onnxruntime-web, backend wasm, como no navegador.
 *
 *   docker run --rm -v ~/Projects/diagrama-cloud:/dc:ro -v $PWD:/p -v $W:/w \
 *     node:24.18-alpine node /p/kernel_wakeword/bancada.mjs --fase tempos --threads 1
 *
 * Fases:
 *   tempos  latência de cada etapa (FP32 e int8), da cadeia e do mel incremental,
 *           mais os tetos medidos no MESMO runtime (MatMul 1024³, Add 2²²) e o
 *           SAXPY em JS puro (Float32Array e Float64Array). Rodadas intercaladas.
 *   fluxo   reproduz o laço de wakeword.ts sobre os 48 clipes do vozes.v1 e grava o
 *           score de cada passo de 80 ms em 4 variantes: produção (FP32, mel sobre
 *           a janela de 1,2 s), mel incremental (FP32), embedding int8, tudo int8.
 *
 * Diferenças do caminho real, nenhuma muda o custo: o modelo entra por readFileSync e
 * o wasm vem de node_modules, não do CDN (as mesmas da bancada 0018 do projeto).
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
import os from "node:os";

const arg = (k, d) => {
  const i = process.argv.indexOf(`--${k}`);
  return i > 0 ? process.argv[i + 1] : d;
};
const FASE = arg("fase", "tempos");
const THREADS = +arg("threads", "1");
const RODADAS = +arg("rodadas", "5");
const ORT = "/dc/node_modules/onnxruntime-web/";
const WW = "/dc/web/public/wakeword/";
const W = "/w/";
const OUT = "/p/resultados/kernel_wakeword/";
mkdirSync(OUT, { recursive: true });

const mod = await import(pathToFileURL(ORT + "dist/ort.all.bundle.min.mjs").href);
const ort = mod.default ?? mod;
ort.env.wasm.wasmPaths = ORT + "dist/";
ort.env.wasm.numThreads = THREADS;
ort.env.logLevel = "error";
const OPC = { executionProviders: ["wasm"], graphOptimizationLevel: "all" };
const sessao = (p) => ort.InferenceSession.create(new Uint8Array(readFileSync(p)), OPC);
const T = (d, dims) => new ort.Tensor("float32", d, dims);

const ambiente = () => ({
  node: process.versions.node, v8: process.versions.v8, arch: process.arch,
  ort_web: ort.env.versions?.web, cpus: os.cpus().length, cpu_modelo: os.cpus()[0]?.model || "n/d",
  mem_gb: +(os.totalmem() / 2 ** 30).toFixed(1), carga_1min_por_nucleo: +(os.loadavg()[0] / os.cpus().length).toFixed(2),
  threads_ort: THREADS, wasm_simd: ort.env.wasm.simd ?? "padrão",
  alpine: (() => { try { return readFileSync("/etc/alpine-release", "utf8").trim(); } catch { return null; } })(),
});

const rnd = (n, s = 1) => { const a = new Float32Array(n); for (let i = 0; i < n; i++) a[i] = (Math.random() * 2 - 1) * s; return a; };
const pct = (xs, p) => xs.slice().sort((a, b) => a - b)[Math.min(xs.length - 1, Math.floor(xs.length * p))];

// ── constantes de wakeword.ts ────────────────────────────────────────────────
const MEL_BINS = 32, EMB_MEL_FRAMES = 76, WW_EMB_FRAMES = 16, STEP = 1280, RAW_WINDOW = 19200;
const HOP = 160, WIN = 512, INC = WIN + (STEP / HOP - 1) * HOP; // 1632: os 8 quadros novos do passo

if (FASE === "tempos") {
  const s = {
    mel: await sessao(WW + "melspectrogram.onnx"), emb: await sessao(WW + "embedding_model.onnx"),
    clf: await sessao(WW + "laudomiro.onnx"),
    mel8: await sessao(W + "modelos/melspectrogram.int8.onnx"), emb8: await sessao(W + "modelos/embedding_model.int8.onnx"),
    clf8: await sessao(W + "modelos/laudomiro.int8.onnx"),
    mm: await sessao(W + "modelos/teto_matmul.onnx"), add: await sessao(W + "modelos/teto_add.onnx"),
  };
  const run = (k, x, dims) => s[k].run({ [s[k].inputNames[0]]: T(x, dims) });
  const audio = rnd(RAW_WINDOW), audioInc = rnd(INC), quadros = rnd(EMB_MEL_FRAMES * MEL_BINS, 2), embs = rnd(WW_EMB_FRAMES * 96);
  const audioInc8 = rnd(8 * INC), audioInc32 = rnd(32 * INC);
  const quadros8 = rnd(8 * EMB_MEL_FRAMES * MEL_BINS, 2), quadros32 = rnd(32 * EMB_MEL_FRAMES * MEL_BINS, 2);
  const A = rnd(1024 * 1024), B = rnd(1024 * 1024), X = rnd(1 << 22), Y = rnd(1 << 22);
  const casos = {
    mel_janela: [() => run("mel", audio, [1, RAW_WINDOW]), 1],
    mel_incremental: [() => run("mel", audioInc, [1, INC]), 5],
    embedding: [() => run("emb", quadros, [1, 76, 32, 1]), 1],
    classificador: [() => run("clf", embs, [1, 16, 96]), 50],
    mel_janela_int8: [() => run("mel8", audio, [1, RAW_WINDOW]), 1],
    embedding_int8: [() => run("emb8", quadros, [1, 76, 32, 1]), 1],
    classificador_int8: [() => run("clf8", embs, [1, 16, 96]), 50],
    // lote de B fluxos simultâneos (servidor): pesos lidos 1x por lote
    mel_incremental_b8: [() => run("mel", audioInc8, [8, INC]), 2],
    mel_incremental_b32: [() => run("mel", audioInc32, [32, INC]), 1],
    embedding_b8: [() => run("emb", quadros8, [8, 76, 32, 1]), 1],
    embedding_b32: [() => run("emb", quadros32, [32, 76, 32, 1]), 1],
    teto_matmul_1024: [() => s.mm.run({ A: T(A, [1024, 1024]), B: T(B, [1024, 1024]) }), 1],
    teto_add_4M: [() => s.add.run({ X: T(X, [1 << 22]), Y: T(Y, [1 << 22]) }), 1],
  };
  const amostras = Object.fromEntries(Object.keys(casos).map((k) => [k, []]));
  const N = +arg("n", "60");
  for (const [, [f]] of Object.entries(casos)) for (let i = 0; i < 10; i++) await f();
  for (let r = 0; r < RODADAS; r++) {
    for (const [k, [f, lote]] of Object.entries(casos)) {
      const n = k.startsWith("teto_matmul") || k.endsWith("_b32") ? 10 : N;
      for (let i = 0; i < n; i++) {
        const t = performance.now();
        for (let j = 0; j < lote; j++) await f();
        amostras[k].push((performance.now() - t) / lote);
      }
    }
  }
  // SAXPY em JS puro: y = a·x + y, 12 B/elemento em FP32, 24 B em FP64
  const saxpy = {};
  for (const [nome, C, b] of [["js_saxpy_f32", Float32Array, 12], ["js_saxpy_f64", Float64Array, 24]]) {
    const n = 1 << 25, x = new C(n).fill(1), y = new C(n).fill(2), a = 1.5, ts = [];
    const f = () => { for (let i = 0; i < n; i++) y[i] = a * x[i] + y[i]; };
    f(); f();
    for (let r = 0; r < 15; r++) { const t = performance.now(); f(); ts.push(performance.now() - t); }
    saxpy[nome] = { n, p50_ms: pct(ts, 0.5), gbs_p50: (b * n) / (pct(ts, 0.5) / 1e3) / 1e9, gbs_max: (b * n) / (Math.min(...ts) / 1e3) / 1e9 };
  }
  const res = { ambiente: ambiente(), rodadas: RODADAS, casos: {} };
  for (const [k, xs] of Object.entries(amostras)) {
    res.casos[k] = { n: xs.length, p50_ms: +pct(xs, 0.5).toFixed(4), p95_ms: +pct(xs, 0.95).toFixed(4), min_ms: +Math.min(...xs).toFixed(4) };
  }
  const c = res.casos;
  res.tetos = {
    matmul_gflops_p50: 2 * 1024 ** 3 / (c.teto_matmul_1024.p50_ms / 1e3) / 1e9,
    matmul_gflops_max: 2 * 1024 ** 3 / (c.teto_matmul_1024.min_ms / 1e3) / 1e9,
    add_gbs_p50: 12 * (1 << 22) / (c.teto_add_4M.p50_ms / 1e3) / 1e9,
    add_gbs_max: 12 * (1 << 22) / (c.teto_add_4M.min_ms / 1e3) / 1e9,
    ...saxpy,
  };
  res.cadeia = {
    atual_p50_ms: c.mel_janela.p50_ms + c.embedding.p50_ms + c.classificador.p50_ms,
    mel_incremental_p50_ms: c.mel_incremental.p50_ms + c.embedding.p50_ms + c.classificador.p50_ms,
    int8_embedding_p50_ms: c.mel_janela.p50_ms + c.embedding_int8.p50_ms + c.classificador.p50_ms,
    lote8_por_fluxo_ms: (c.mel_incremental_b8.p50_ms + c.embedding_b8.p50_ms) / 8 + c.classificador.p50_ms,
    lote32_por_fluxo_ms: (c.mel_incremental_b32.p50_ms + c.embedding_b32.p50_ms) / 32 + c.classificador.p50_ms,
  };
  for (const [k, v] of Object.entries(c)) console.log(`${k.padEnd(22)} p50 ${String(v.p50_ms).padStart(9)} ms  p95 ${String(v.p95_ms).padStart(9)}  min ${String(v.min_ms).padStart(9)}  n=${v.n}`);
  console.log(JSON.stringify({ tetos: res.tetos, cadeia: res.cadeia, ambiente: res.ambiente }, null, 1));
  writeFileSync(OUT + `tempos_t${THREADS}.json`, JSON.stringify(res, null, 1));
} else {
  // ── fluxo: o laço de wakeword.ts, passo a passo ───────────────────────────
  const clipes = JSON.parse(readFileSync(W + "audio.json", "utf8"));
  const buf = readFileSync(W + "audio.f32");
  const todo = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const S = {
    fp32: [await sessao(WW + "melspectrogram.onnx"), await sessao(WW + "embedding_model.onnx"), await sessao(WW + "laudomiro.onnx")],
    int8emb: [null, await sessao(W + "modelos/embedding_model.int8.onnx"), null],
    int8: [await sessao(W + "modelos/melspectrogram.int8.onnx"), await sessao(W + "modelos/embedding_model.int8.onnx"), await sessao(W + "modelos/laudomiro.int8.onnx")],
  };
  const variantes = {
    producao: { mel: S.fp32[0], emb: S.fp32[1], clf: S.fp32[2], inc: false },
    mel_incremental: { mel: S.fp32[0], emb: S.fp32[1], clf: S.fp32[2], inc: true },
    embedding_int8: { mel: S.fp32[0], emb: S.int8emb[1], clf: S.fp32[2], inc: false },
    tudo_int8: { mel: S.int8[0], emb: S.int8[1], clf: S.int8[2], inc: false },
  };
  const rodaMel = async (mel, x) => {
    const o = await mel.run({ [mel.inputNames[0]]: T(x, [1, x.length]) });
    const t = o[mel.outputNames[0]];
    return { n: t.dims[t.dims.length - 2], d: t.data };
  };
  const res = { ambiente: ambiente(), clipes: [] };
  for (const c of clipes) {
    const audio = todo.subarray(c.inicio, c.inicio + c.n);
    const linha = { ...c, scores: {} };
    for (const [nome, v] of Object.entries(variantes)) {
      let raw = new Float32Array(0), total = 0, embs = [], quadros = [];
      const scores = [];
      for (let p = 0; p + STEP <= audio.length; p += STEP) {
        const chunk = audio.subarray(p, p + STEP);
        const m = new Float32Array(raw.length + STEP); m.set(raw, 0); m.set(chunk, raw.length);
        raw = m.length > RAW_WINDOW ? m.slice(m.length - RAW_WINDOW) : m;
        total += STEP;
        let janela;
        if (!v.inc) {
          if (raw.length < RAW_WINDOW * 0.6) { scores.push(null); continue; }
          const { n, d } = await rodaMel(v.mel, raw);
          if (n < EMB_MEL_FRAMES) { scores.push(null); continue; }
          janela = new Float32Array(EMB_MEL_FRAMES * MEL_BINS);
          const ini = (n - EMB_MEL_FRAMES) * MEL_BINS;
          for (let i = 0; i < janela.length; i++) janela[i] = d[ini + i] / 10 + 2;
        } else {
          // quadros novos deste passo, na MESMA grade (início em múltiplo de 160 desde o começo do fluxo)
          const kMax = Math.floor((total - WIN) / HOP), kMin = Math.max(0, Math.floor((total - STEP - WIN) / HOP) + 1);
          if (kMax >= kMin) {
            const a0 = kMin * HOP, a1 = kMax * HOP + WIN;          // índices globais
            const off = total - raw.length;                         // índice global de raw[0]
            const { n, d } = await rodaMel(v.mel, raw.slice(a0 - off, a1 - off));
            for (let q = 0; q < n; q++) quadros.push(d.slice(q * MEL_BINS, (q + 1) * MEL_BINS));
            if (quadros.length > EMB_MEL_FRAMES) quadros = quadros.slice(quadros.length - EMB_MEL_FRAMES);
          }
          // mesma partida da produção: só pontua quando ela pontuaria
          if (raw.length < RAW_WINDOW * 0.6 || Math.floor((raw.length - WIN) / HOP) + 1 < EMB_MEL_FRAMES || quadros.length < EMB_MEL_FRAMES) { scores.push(null); continue; }
          janela = new Float32Array(EMB_MEL_FRAMES * MEL_BINS);
          for (let q = 0; q < EMB_MEL_FRAMES; q++) for (let b = 0; b < MEL_BINS; b++) janela[q * MEL_BINS + b] = quadros[q][b] / 10 + 2;
        }
        const eo = await v.emb.run({ [v.emb.inputNames[0]]: T(janela, [1, 76, 32, 1]) });
        embs.push(Float32Array.from(eo[v.emb.outputNames[0]].data));
        if (embs.length > WW_EMB_FRAMES) embs.shift();
        if (embs.length < WW_EMB_FRAMES) { scores.push(null); continue; }
        const flat = new Float32Array(WW_EMB_FRAMES * 96);
        for (let i = 0; i < WW_EMB_FRAMES; i++) flat.set(embs[i], i * 96);
        const so = await v.clf.run({ [v.clf.inputNames[0]]: T(flat, [1, 16, 96]) });
        scores.push(so[v.clf.outputNames[0]].data[0]);
      }
      linha.scores[nome] = scores;
    }
    res.clipes.push(linha);
    const mx = Object.fromEntries(Object.entries(linha.scores).map(([k, s]) => [k, Math.max(...s.filter((x) => x !== null)).toFixed(4)]));
    console.log(`${c.arquivo.padEnd(14)} ${c.positivo ? "POS" : "neg"} max ${JSON.stringify(mx)}`);
  }
  writeFileSync(OUT + "fluxo_scores.json", JSON.stringify(res));
}
