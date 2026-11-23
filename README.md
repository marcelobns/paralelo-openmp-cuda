# Tutoria OpenMP + CUDA: medições, análise e relatório

Trabalho da tutoria "Processamento Paralelo: OpenMP e CUDA na RTX 3090" (Arquitetura e Organização de Computadores, PPCA/UFRR).

**O roteiro e o kit são material da disciplina e não estão neste repositório.** Para reproduzir, coloque `kit_paralelo_cuda_openmp.zip` em `docs/` e descompacte-o em `kit_pp/`, sem alterar as fontes. As duas pastas estão no `.gitignore`.

## Entrega (`entrega/`)

| Item pedido | Arquivo |
| --- | --- |
| Saída do `verifica_ambiente.sh` | `entrega/verifica_ambiente_saida.txt` (Colab, Tesla T4) |
| As 4 predições | quadro no topo do relatório (respostas do discente: P1 a, P2 a, P3 b, P4 "tudo fica igual") |
| Tabela do Bloco 5 | seção 6 do relatório |
| Relatório de 2 páginas | `entrega/relatorio_tutoria_paralelo.pdf` (fonte em `relatorio/relatorio.tex`) |

Resultados principais:

| Bloco 5 | Valor | Onde |
| --- | --- | --- |
| Ponto de saturação do OpenMP | 7 threads (95% da maior mediana; 84% já com 3) | Apple M5 |
| Banda máxima na CPU | 126,8 GB/s (mediana de 15) | Apple M5 |
| Fração em transferência, N=1e8, 1 repetição | 98,0% | Tesla T4 |
| Fração com 50 repetições | 50,2% | Tesla T4 |
| AI do kernel da dissertação | cadeia do wake word, FP32: 10–51 FLOP/B (mel 17–54, embedding 8–64, classificador 0,5) | `node:24.18-alpine` |
| Regime | cômputo: 44 GFLOP/s, 87% do teto de MatMul do runtime (wasm, 1 thread); equilíbrio 0,76 FLOP/B (banda de cópia nativa, 66 GB/s) | `node:24.18-alpine` |

## Máquinas (sem RTX 3090)

| Bloco | Onde | Script |
| --- | --- | --- |
| 1 – condição de corrida | Mac **e** Colab | `mac/coleta_mac.sh`, notebook gerado por `colab/gerar_notebook.py` |
| 2 – SAXPY OpenMP | Mac (Apple M5, 4P + 6E) | `mac/coleta_mac.sh` |
| 3 – SAXPY CUDA / PCIe | Colab (Tesla T4) | notebook gerado por `colab/gerar_notebook.py` |
| 4 – roofline | Colab (3090 original + T4 medida) | notebook gerado; `colab/roofline_gpu.py` |
| Kernel da dissertação | `node:24.18-alpine` (Node 24.18.1, Alpine 3.24.1/musl) sob OrbStack no M5, VM de 10 vCPU e 4,9 GB | `kernel_wakeword/*` |

Todo número da 3090 no relatório vem do **modelo do roteiro**; nenhum foi medido.

## Kernel da dissertação: o que foi validado

A dissertação usa o `diagrama-cloud` como instrumento (pré-projeto em `diagrama-cloud/docs/academico/pre-projeto.md`). O ambiente declarado é a imagem `node:24.18-alpine` dos estágios `deps` e `runner` de `web/Dockerfile.prod`. A conferência do código mostrou:

- `deps` só executa `npm ci`. Não roda código da aplicação.
- `runner` executa `node web/server.js`: SSR do Next e um BFF. As 76 rotas em `web/app/api/**/route.ts` repassam à `api`: 69 por `proxy`/`proxyBinary`, 6 de auth e do webhook do WhatsApp (`fetch` direto à `api` ou só cookies), e `editor-preview/fixtures` lê arquivos do disco. A engine só é importada pelas 4 páginas `"use client"`.
- A extração por LLM, que é o objeto da dissertação, roda na `api` (Django/Python) e no provedor remoto. Não há FLOP local a medir ali.
- O kernel do caminho quente da voz, executado a cada 80 ms, é a cadeia do openWakeWord de `web/lib/wakeword.ts`: melspectrograma → embedding → classificador, em onnxruntime-web 1.27 (wasm, FP32). **Em produção ela roda no navegador** (ADR-003), e o container só serve os `.onnx`. Rodá-la no `runner` exigiria mandar o áudio ocioso ao servidor, contra a regra do produto. O pacote é wasm puro e funciona sob musl, e foi medido na imagem declarada.
- No navegador o ORT roda com 1 thread: sem os cabeçalhos COOP/COEP (`web/next.config.mjs`), não há `SharedArrayBuffer`. Na imagem, 4 threads dão 2,25×.
- O VPS do Beta (Hostinger KVM 2, 2 vCPU) não foi medido.

Modelos medidos (sha256, os mesmos da corrida 0018 do projeto; commit `73430ae` do `diagrama-cloud`):

```text
ba2b0e0f…b176f  melspectrogram.onnx
70d16429…75c1f  embedding_model.onnx
017c26b1…5ddc   laudomiro.onnx
```

## Como reproduzir

```bash
# Blocos 1 e 2 (Mac; ~5 min na tomada, sem outros apps pesados). Requer: brew install libomp
REPS=15 ./mac/coleta_mac.sh

# Blocos 0, 1, 3 e 4: gerar o notebook, abrir colab/tutoria_colab.ipynb no Colab, GPU T4, preencher as
# predições e "Executar tudo"; descompactar o resultados_colab.zip baixado em resultados/.
python3 colab/gerar_notebook.py            # gera o notebook a partir de docs/kit_paralelo_cuda_openmp.zip (embute o zip, com sha256)

# Kernel da dissertação (lê ../diagrama-cloud sem escrever nele; W = diretório de trabalho)
DC=~/Projects/diagrama-cloud; W=$(mktemp -d)
uv run --with onnx --with onnxruntime --with numpy python3 kernel_wakeword/contagem_onnx.py --modelos $DC/web/public/wakeword
uv run --with onnx --with onnxruntime --with numpy --with scipy python3 kernel_wakeword/prep.py --dc $DC --out $W
for f in "--fase tempos --threads 1" "--fase tempos --threads 4" "--fase fluxo"; do
  docker run --rm -v $DC:/dc:ro -v $PWD:/p -v $W:/w node:24.18-alpine node /p/kernel_wakeword/bancada.mjs $f
done
uv run --with onnx --with numpy python3 kernel_wakeword/precisao.py --modelos $DC/web/public/wakeword --w $W
uv run --with matplotlib --with numpy python3 kernel_wakeword/figura_roofline_wasm.py

# Relatório
cd relatorio && pdflatex relatorio.tex
```

## Dados brutos (`resultados/`)

- `mac_20261122_180758/`: ambiente, assembly do clang (`race.s`), 2 × 50 execuções do `race`, CSV bruto e resumo do SAXPY, gráfico.
- `colab_t4_20261122/`: ambiente e `nvidia-smi`, assembly do gcc (`race_gcc.s`), 50 execuções do `race`, 20 execuções do `saxpy_cuda` (CSV e log bruto), rooflines.
- `kernel_wakeword/`:
  - `contagem_onnx.json`: FLOP e bytes por nó.
  - `tempos_t1.json` e `tempos_t4.json`: latências, tetos e ambiente; 5 rodadas intercaladas, 300 amostras por etapa. O `teto_add` (16 GB/s) inclui as cópias para o heap do wasm e **não** é usado como teto de memória.
  - `banda_copia.json`: teto de memória usado no relatório; cópia nativa de 128 MB, 9 execuções, mediana 66 GB/s (faixa 41–83).
  - `fluxo_scores.json`: score de cada passo de 80 ms nos 48 clipes, em 4 variantes.
  - `precisao.json`: comparação com a referência FP64.
  - Logs em `*_log.txt`.

## Observações

- **Predições.** A execução no Colab foi conduzida pelo assistente com `colab/tutoria_colab_assistida.ipynb`. Nessa variante, as predições vêm marcadas como "registrada pelo discente fora do notebook", texto escrito pelo assistente e não pelo discente. As predições reais, escolhidas pelo discente, estão no quadro do relatório. O notebook normal (`tutoria_colab.ipynb`) recusa rodar com as predições vazias. Os dois notebooks embutem o kit e por isso não estão no repositório; `gerar_notebook.py` (com `--assistida` para a variante) os recria.
- **Diferença da corrida 0018, sem explicação.** Com os mesmos modelos (sha256 iguais), a 0018 registrou mel 3,5 ms e embedding 1,9 ms no host (Node 22.23, carga 0,23). Aqui deram 1,35 e 2,02 ms na imagem (Node 24.18). O embedding bate, mas o mel ficou 2,6× mais rápido. Não investiguei a causa.
- **Referência FP64.** O onnxruntime não tem Conv em float64. `kernel_wakeword/ref_numpy.py` interpreta os três grafos em numpy e, em FP32, reproduz o ORT com erro de 1e-6 (mel) e 1e-7 (score).
- **Áudio.** Os clipes são os 48 do `metrics/datasets/vozes.v1` (frase 0 contém "Laudomiro"), reamostrados de 24 kHz para 16 kHz, com 1,5 s de ruído antes e 1 s depois (σ = 1e-3, semente fixa). O áudio derivado fica no diretório de trabalho, fora do repositório.
- **Análise anterior arquivada.** A primeira versão analisava a LU esparsa do solver FDFD de `materials-design-discovery`, que não é o kernel da dissertação. Ela está em `arquivo/fdfd_materials-design-discovery/` e não entra no relatório.
- **Desvios do roteiro.** CPU: Apple M5 com clang + libomp em vez de gcc, e o macOS não fixa threads em núcleos. GPU: Tesla T4 (Turing, PCIe 3.0, FP64 a 1/32), compilada com `sm_75`. Kernel: medido sob OrbStack (VM arm64) no M5, não no VPS de produção. Repetições: cada caso foi repetido, e o relatório traz a mediana e a faixa.
