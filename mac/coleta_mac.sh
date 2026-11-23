#!/bin/bash
# =====================================================================
# Coleta dos Blocos 1 e 2 da tutoria (OpenMP) num Mac Apple Silicon.
#
# Usa as fontes ORIGINAIS de kit_pp/ (race.c, saxpy_omp.c), sem alterar
# nada. A unica diferenca em relacao ao Makefile do kit e a linha de
# compilacao: no macOS "gcc" e o Apple clang, que precisa do libomp do
# Homebrew. A linha exata usada fica registrada em ambiente.txt.
#
# Uso:   ./mac/coleta_mac.sh            (REPS=9 por padrao)
#        REPS=15 ./mac/coleta_mac.sh
# Saida: resultados/mac_<data>/   (logs brutos, CSV, resumo, grafico)
#
# Antes de rodar: ligue o carregador, feche apps pesados e nao use o
# Mac durante a coleta (~3 min). Bateria e uso concorrente mexem na
# banda medida.
# =====================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
KIT="$RAIZ/kit_pp"
REPS="${REPS:-9}"
THREADS_LIST=(1 2 3 4 5 6 7 8 9 10 12 16)
N_LIST=(50000000 200000000)   # 5e7 = comando do roteiro; 2e8 = checagem de robustez
OUT="$RAIZ/resultados/mac_$(date +%Y%m%d_%H%M%S)"
BIN="$OUT/bin"
mkdir -p "$BIN"

[ -f "$KIT/race.c" ] || { echo "kit_pp/ nao encontrado em $RAIZ (descompacte o kit)"; exit 1; }
OMP_PREFIX="$(brew --prefix libomp 2>/dev/null || true)"
[ -n "$OMP_PREFIX" ] && [ -f "$OMP_PREFIX/include/omp.h" ] || { echo "libomp ausente: brew install libomp"; exit 1; }

CFLAGS="-O3 -mcpu=native -Xpreprocessor -fopenmp -I$OMP_PREFIX/include"
LDFLAGS="-L$OMP_PREFIX/lib -lomp"
CC=clang

# ---------------------------------------------------------------- ambiente
{
  echo "=== Ambiente da coleta (Mac) ==="
  echo "data ............ $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "macOS ........... $(sw_vers -productName) $(sw_vers -productVersion) ($(sw_vers -buildVersion))"
  echo "kernel .......... $(uname -srm)"
  echo "CPU ............. $(sysctl -n machdep.cpu.brand_string)"
  echo "nucleos logicos . $(sysctl -n hw.ncpu)"
  echo "nucleos P ....... $(sysctl -n hw.perflevel0.physicalcpu) ($(sysctl -n hw.perflevel0.name))"
  echo "nucleos E ....... $(sysctl -n hw.perflevel1.physicalcpu) ($(sysctl -n hw.perflevel1.name))"
  echo "L2 por cluster P  $(( $(sysctl -n hw.perflevel0.l2cachesize) / 1048576 )) MiB"
  echo "L2 por cluster E  $(( $(sysctl -n hw.perflevel1.l2cachesize) / 1048576 )) MiB"
  echo "memoria ......... $(( $(sysctl -n hw.memsize) / 1073741824 )) GiB (unificada)"
  echo "energia ......... $(pmset -g batt | head -1)"
  echo "compilador ...... $($CC --version | head -1)"
  echo "libomp .......... $(brew list --versions libomp)"
  echo "linha de compilacao: $CC $CFLAGS <fonte.c> $LDFLAGS -o <bin>"
  echo "(Makefile do kit: gcc -O3 -march=native -fopenmp)"
  echo "REPS=$REPS  THREADS=${THREADS_LIST[*]}  N=${N_LIST[*]}"
  echo ""
  echo "sha256 das fontes do kit usadas:"
  (cd "$KIT" && shasum -a 256 race.c saxpy_omp.c)
  echo ""
  echo "Obs.: o macOS nao permite fixar threads em nucleos (sem OMP_PROC_BIND"
  echo "efetivo). O escalonador costuma por ate 4 threads nos nucleos P, mas"
  echo "isso nao e garantido."
} | tee "$OUT/ambiente.txt"

# ---------------------------------------------------------------- build
$CC $CFLAGS "$KIT/race.c"      $LDFLAGS -o "$BIN/race"
$CC $CFLAGS "$KIT/saxpy_omp.c" $LDFLAGS -o "$BIN/saxpy_omp"
# assembly do laco com corrida, para explicar o padrao de erro no relatorio
$CC $CFLAGS -S "$KIT/race.c" -o "$OUT/race.s"

# ---------------------------------------------------------------- bloco 1
echo ""
echo "=== Bloco 1: condicao de corrida ==="
{
  echo "--- execucao unica, 4 threads (comando do roteiro) ---"
  OMP_NUM_THREADS=4 "$BIN/race"
} | tee "$OUT/bloco1_race.txt"

for T in 4 10; do
  RAW="$OUT/bloco1_naodet_${T}threads.txt"
  : > "$RAW"
  for i in $(seq 1 50); do OMP_NUM_THREADS=$T "$BIN/race" | grep corrida >> "$RAW"; done
  ERR=$(grep -c ERRADO "$RAW" || true)
  echo "--- $T threads, 50 execucoes: $ERR erradas ---  distribuicao dos valores:" | tee -a "$OUT/bloco1_race.txt"
  awk '{print $5}' "$RAW" | sort | uniq -c | sort -rn | tee -a "$OUT/bloco1_race.txt"
done

# ---------------------------------------------------------------- bloco 2
echo ""
echo "=== Bloco 2: SAXPY OpenMP (rodadas intercaladas para diluir deriva termica) ==="
CSV="$OUT/bloco2_saxpy_omp.csv"
RAW="$OUT/bloco2_saxpy_omp_raw.txt"
echo "N,threads,rep,tempo_s,gbs,gflops" > "$CSV"
: > "$RAW"
for N in "${N_LIST[@]}"; do
  for R in $(seq 1 "$REPS"); do
    printf "N=%s rodada %s/%s: " "$N" "$R" "$REPS"
    for T in "${THREADS_LIST[@]}"; do
      L=$(OMP_NUM_THREADS=$T "$BIN/saxpy_omp" "$N")
      echo "$L" >> "$RAW"
      # threads=%2d  N=%ld  tempo=%.4f s  %.2f GB/s  %.2f GFLOP/s  (y[0]=%.1f)
      echo "$L" | sed -E 's/threads= *([0-9]+) +N=([0-9]+) +tempo=([0-9.]+) s +([0-9.]+) GB\/s +([0-9.]+) GFLOP\/s.*/\2,\1,'"$R"',\3,\4,\5/' >> "$CSV"
      printf "."
    done
    echo ""
  done
done

# ---------------------------------------------------------------- resumo
echo ""
if command -v uv >/dev/null 2>&1; then
  uv run --quiet --with matplotlib python3 "$RAIZ/mac/resumo_mac.py" "$OUT"
else
  echo "(uv nao encontrado: resumo sem grafico)"
  python3 "$RAIZ/mac/resumo_mac.py" "$OUT"
fi
echo ""
echo "Resultados em: $OUT"
