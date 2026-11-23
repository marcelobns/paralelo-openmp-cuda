"""Gera colab/tutoria_colab.ipynb a partir do kit original e de roofline_gpu.py.

O zip do kit entra no notebook byte a byte (base64), com sha256 conferido na
extracao, para que o Colab rode exatamente as fontes do professor.

O kit é material da disciplina e não está no repositório: coloque o zip em
docs/kit_paralelo_cuda_openmp.zip (ou passe --kit <caminho>).

Uso: python3 colab/gerar_notebook.py [--assistida] [--kit <zip do kit>]
"""
import base64
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
import sys
ZIP = Path(sys.argv[sys.argv.index("--kit") + 1]) if "--kit" in sys.argv else RAIZ / "docs" / "kit_paralelo_cuda_openmp.zip"
ROOFLINE = RAIZ / "colab" / "roofline_gpu.py"
SAIDA = RAIZ / "colab" / "tutoria_colab.ipynb"
# --assistida: variante para execucao conduzida pelo assistente; as predicoes
# ficam marcadas como registradas fora do notebook (o discente as escreve no relatorio).
import sys
ASSISTIDA = "--assistida" in sys.argv
if ASSISTIDA:
    SAIDA = RAIZ / "colab" / "tutoria_colab_assistida.ipynb"

zip_bytes = ZIP.read_bytes()
ZIP_B64 = base64.b64encode(zip_bytes).decode()
ZIP_SHA = hashlib.sha256(zip_bytes).hexdigest()

cells = []


def md(src):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": src.strip("\n")})


def code(src):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": src.strip("\n")})


md("""
# Tutoria — Processamento Paralelo: OpenMP e CUDA (execução no Google Colab)

Este notebook roda o kit **original** da tutoria (`kit_paralelo_cuda_openmp.zip`) numa GPU do Colab.

**Antes de começar**
1. `Ambiente de execução → Alterar o tipo de ambiente de execução → GPU T4` (o notebook já pede T4).
2. Preencha **a célula de predições** (logo abaixo) *antes* de rodar qualquer medição.
3. `Ambiente de execução → Executar tudo`. Leva poucos minutos. No fim, um `.zip` com todos os logs é baixado.

**Diferenças em relação ao roteiro (documente no relatório)**
- GPU do Colab (normalmente **Tesla T4**, Turing, PCIe 3.0) em vez da RTX 3090 (Ampere, PCIe 4.0).
  O `saxpy_cuda.cu` é compilado com `-arch=sm_XY` da GPU detectada, e não com o `sm_86` do Makefile.
- O Colab gratuito tem ~2 vCPUs: o **Bloco 2** daqui é só referência. O Bloco 2 que entra na tabela é o do Mac (`mac/coleta_mac.sh`).
- O `roofline.py` original (constantes da 3090) é executado sem alteração. Além dele, `roofline_gpu.py` refaz as mesmas contas para a GPU medida e confronta com as medições.
""")

code("""
# ===== PREDIÇÕES — preencha ANTES de executar qualquer medição =====
# (a/b/c conforme o roteiro; a Predição 4 é texto livre)
PREDICOES = {
    "P1 - race com 4 threads: (a) sempre correto (b) sempre errado (c) as vezes correto": "",
    "P2 - SAXPY OpenMP escala ate: (a) esgotar nucleos (b) saturar banda (c) sempre": "",
    "P3 - fracao do tempo em transferencia, N=1e8: (a) <10% (b) ~metade (c) >90%": "",
    "P4 - em FP64, o que acontece? (texto livre)": "",
}

import datetime, json, pathlib
RES = pathlib.Path('/content/resultados_colab'); RES.mkdir(parents=True, exist_ok=True)
faltando = [k for k, v in PREDICOES.items() if not str(v).strip()]
if faltando:
    raise ValueError('Preencha as predicoes antes de medir:\\n  - ' + '\\n  - '.join(faltando))
registro = {'registrado_em': datetime.datetime.now(datetime.timezone.utc).isoformat(), **PREDICOES}
(RES / 'predicoes.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2))
print(json.dumps(registro, ensure_ascii=False, indent=2))
""")

code(f"""
# ===== Kit original (zip embutido byte a byte) + funcoes auxiliares =====
import base64, hashlib, io, os, re, shutil, statistics, subprocess, zipfile
KIT_ZIP_B64 = "{ZIP_B64}"
KIT_ZIP_SHA256 = "{ZIP_SHA}"

dados = base64.b64decode(KIT_ZIP_B64)
assert hashlib.sha256(dados).hexdigest() == KIT_ZIP_SHA256, 'zip do kit corrompido'
shutil.rmtree('/content/kit_pp', ignore_errors=True)
zipfile.ZipFile(io.BytesIO(dados)).extractall('/content')
KIT = pathlib.Path('/content/kit_pp')
for f in KIT.glob('*.sh'):
    f.chmod(0o755)
os.environ['PATH'] += ':/usr/local/cuda/bin'

def sh(cmd, log=None, check=True, env=None, quiet=False):
    \"\"\"Roda um comando bash no diretorio do kit, mostra e registra a saida.\"\"\"
    e = os.environ.copy(); e.update(env or {{}})
    p = subprocess.run(['bash', '-c', cmd], cwd=KIT, capture_output=True, text=True, env=e)
    out = p.stdout + p.stderr
    if log:
        with open(RES / log, 'a') as f:
            f.write(f'$ {{cmd}}\\n{{out}}\\n')
    if not quiet:
        print(out, end='')
    if check and p.returncode != 0:
        raise RuntimeError(f'falhou (codigo {{p.returncode}}): {{cmd}}')
    return out

print('kit extraido em', KIT, '| sha256 do zip OK:', KIT_ZIP_SHA256[:16], '...')
print(sh('ls -l && sha256sum *', quiet=True))
""")

code("%%writefile /content/roofline_gpu.py\n" + ROOFLINE.read_text())

md("""
## Passo 0 — Ambiente
""")

code("""
if shutil.which('nvidia-smi') is None:
    raise RuntimeError('Sem GPU: Ambiente de execucao -> Alterar o tipo -> GPU T4, e rode de novo.')
LOG = 'ambiente.txt'
sh('./verifica_ambiente.sh', log=LOG)
sh('echo; date -u; uname -a; echo; lscpu | head -20; echo; free -h; echo; gcc --version | head -1; nvcc --version | tail -2', log=LOG)
sh('echo; nvidia-smi', log=LOG)
sh('nvidia-smi --query-gpu=name,compute_cap,memory.total,driver_version,clocks.max.sm,clocks.max.memory,'
   'pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max --format=csv',
   log=LOG, check=False)   # diagnostico: um campo nao suportado nao pode abortar a coleta
GPU_NOME = sh('nvidia-smi --query-gpu=name --format=csv,noheader', quiet=True).strip().splitlines()[0]
print('\\nGPU detectada:', GPU_NOME)
""")

md("""
## Bloco 1 — Condição de corrida
O comando do roteiro, depois 50 execuções idênticas (5 rodadas do `naodet.sh`). Com ~2 vCPUs, 4 threads ficam *sobre-assinadas*: anote isso ao comparar a taxa de erro com a do roteiro.
""")

code("""
LOG = 'bloco1_race.txt'
sh('make 2>&1', log=LOG)
sh('OMP_NUM_THREADS=4 ./race', log=LOG)
# assembly do gcc: evidencia de COMO a corrida se manifesta (comparar com o clang do Mac)
sh(f'gcc -O3 -march=native -fopenmp -S race.c -o {RES}/race_gcc.s', log=LOG)
saida = ''.join(sh('./naodet.sh', log=LOG, quiet=True) for _ in range(5))
valores = [int(m) for m in re.findall(r'corrida\\)\\s+=\\s+(\\d+)', saida)]
ref = 5999995
errados = [v for v in valores if v != ref]
resumo = f'\\n{len(valores)} execucoes, 4 threads: {len(errados)} erradas ({100*len(errados)/len(valores):.0f}%)\\n'
resumo += 'distribuicao (valor: vezes): ' + ', '.join(f'{v}: {valores.count(v)}' for v in sorted(set(valores), key=valores.count, reverse=True))
print(resumo)
with open(RES / LOG, 'a') as f:
    f.write(resumo + '\\n')
""")

md("""
## Bloco 2 — SAXPY OpenMP (*somente referência, não vai para a tabela*)
O Colab gratuito tem poucos núcleos; o ponto de saturação vem do Mac (`mac/coleta_mac.sh`).
""")

code("""
LOG = 'bloco2_colab_referencia.txt'
sh('echo "nproc = $(nproc)"', log=LOG)
for rep in range(3):
    sh('for t in 1 2 4 8 16; do OMP_NUM_THREADS=$t ./saxpy_omp 50000000; done', log=LOG)
""")

md("""
## Bloco 3 — A GPU e o pedágio do PCIe
**Compilação.** O `saxpy_cuda.cu` nunca foi compilado pelo autor do kit (veja o aviso no topo do arquivo). Se esta célula falhar, o erro do `nvcc` fica em `compile.log`. Registre qualquer correção como diff no relatório.
""")

code("""
cc = sh('nvidia-smi --query-gpu=compute_cap --format=csv,noheader', quiet=True, check=False).strip()
cc = cc.splitlines()[0] if cc else ''
if not re.fullmatch(r'\\d+\\.\\d+', cc):
    try:
        import torch
        cc = '%d.%d' % torch.cuda.get_device_capability(0)
    except Exception:
        cc = {'T4': '7.5', 'L4': '8.9', 'A100': '8.0', 'RTX 3090': '8.6'}.get(
            next((k for k in ('T4', 'L4', 'A100', 'RTX 3090') if k in GPU_NOME), ''), '')
if not re.fullmatch(r'\\d+\\.\\d+', cc):
    raise RuntimeError(f'nao consegui descobrir a compute capability de {GPU_NOME}')
ARCH = 'sm_' + cc.replace('.', '')
cmd = f'nvcc -O3 -arch={ARCH} saxpy_cuda.cu -o saxpy_cuda'
print('Makefile do kit: nvcc -O3 -arch=sm_86 ...  |  usado aqui:', cmd)
sh(cmd + ' 2>&1', log='compile.log')
print('compilou OK')
""")

md("""
**Medições.** `./saxpy_cuda 100000000 1` e `./saxpy_cuda 100000000 50`, 5 vezes cada, em rodadas intercaladas.
Cada configuração roda também com `CUDA_MODULE_LOADING=EAGER`: se o kernel com 1 repetição sair bem mais lento que (tempo com 50)/50, a diferença é custo de primeira chamada (carga preguiçosa do módulo), não do SAXPY.
""")

code("""
import pandas as pd
PADROES = {
    'gpu':     r'GPU: (.+?) \\| SMs=(\\d+) \\| cc (\\d+)\\.(\\d+)',
    'h2d':     r'envio\\s+H->D\\s*:\\s*([\\d.]+) ms\\s+\\(([\\d.]+) GB/s',
    'kernel':  r'kernel\\s+\\(\\s*(\\d+)x\\)\\s*:\\s*([\\d.]+) ms\\s+\\(([\\d.]+) GB/s',
    'd2h':     r'retorno\\s+D->H\\s*:\\s*([\\d.]+) ms\\s+\\(([\\d.]+) GB/s',
    'total':   r'TOTAL\\s*:\\s*([\\d.]+) ms',
    'fracao':  r'fracao gasta em transferencia:\\s*([\\d.]+)%',
    'verif':   r'y\\[0\\] = ([\\d.]+) \\(esperado ([\\d.]+)\\)',
}

def parse_saxpy(txt):
    m = {k: re.search(p, txt) for k, p in PADROES.items()}
    faltou = [k for k, v in m.items() if v is None]
    if faltou:
        raise RuntimeError(f'saida inesperada do saxpy_cuda (faltou {faltou}):\\n{txt}')
    return dict(
        gpu=m['gpu'][1], sms=int(m['gpu'][2]),
        rep=int(m['kernel'][1]),
        h2d_ms=float(m['h2d'][1]), h2d_gbs=float(m['h2d'][2]),
        kernel_ms=float(m['kernel'][2]), kernel_gbs=float(m['kernel'][3]),
        d2h_ms=float(m['d2h'][1]), d2h_gbs=float(m['d2h'][2]),
        total_ms=float(m['total'][1]), fracao_pct=float(m['fracao'][1]),
        y0=float(m['verif'][1]), y0_esperado=float(m['verif'][2]),
    )

N = 100_000_000
linhas = []
for rodada in range(1, 6):
    for modo, env in (('padrao', {}), ('EAGER', {'CUDA_MODULE_LOADING': 'EAGER'})):
        for rep in (1, 50):
            txt = sh(f'./saxpy_cuda {N} {rep}', log='bloco3_saxpy_cuda_raw.txt', env=env, quiet=True)
            r = parse_saxpy(txt); r.update(rodada=rodada, carga_modulo=modo)
            assert r['y0'] == r['y0_esperado'], f'resultado errado: {r}'
            linhas.append(r)
    print(f'rodada {rodada}/5 ok')

df = pd.DataFrame(linhas)
df.to_csv(RES / 'bloco3_saxpy_cuda.csv', index=False)
cols = ['h2d_ms', 'kernel_ms', 'd2h_ms', 'total_ms', 'fracao_pct', 'h2d_gbs', 'd2h_gbs', 'kernel_gbs']
med = df.groupby(['carga_modulo', 'rep'])[cols].median()
faixa = df.groupby(['carga_modulo', 'rep'])['fracao_pct'].agg(['min', 'max'])
with pd.option_context('display.float_format', '{:.3f}'.format, 'display.width', 200,
                       'display.max_columns', None):
    print('\\nMEDIANAS (5 execucoes por configuracao):'); print(med)
    print('\\nfaixa da fracao em transferencia (%):'); print(faixa)

print('\\nChecagem de custo de primeira chamada (kernel 1x vs kernel 50x / 50):')
for modo in ('padrao', 'EAGER'):
    k1 = med.loc[(modo, 1), 'kernel_ms']; k50 = med.loc[(modo, 50), 'kernel_ms'] / 50
    print(f'  {modo:>6}: 1x = {k1:.3f} ms | 50x/50 = {k50:.3f} ms | razao = {k1/k50:.2f}')
med.to_csv(RES / 'bloco3_medianas.csv')
""")

md("""
## Bloco 4 — Roofline
Primeiro o `roofline.py` original (RTX 3090, sem alteração). Depois as mesmas contas para a GPU medida, com o modelo do PCIe confrontado com as taxas medidas no Bloco 3.
""")

code("""
sh('python3 roofline.py', log='bloco4_roofline_3090_original.txt')
pcie = med.loc[('padrao', 1), 'h2d_gbs']
kbw = med.loc[('padrao', 50), 'kernel_gbs']   # 50 repeticoes: sem custo de primeira chamada diluir
sms = int(df['sms'].iloc[0])
sh(f'python3 /content/roofline_gpu.py --gpu "{GPU_NOME}" --sms {sms} --pcie-medido {pcie:.2f} '
   f'--kernel-bw-medido {kbw:.1f} --plot {RES}/bloco4_roofline_gpu.png',
   log='bloco4_roofline_gpu_medida.txt', check=False)
from IPython.display import Image, display
if (RES / 'bloco4_roofline_gpu.png').exists():
    display(Image(str(RES / 'bloco4_roofline_gpu.png'), width=640))
""")

md("""
## Bloco 5 — Síntese e pacote de resultados
""")

code("""
f1 = med.loc[('padrao', 1), 'fracao_pct']; f50 = med.loc[('padrao', 50), 'fracao_pct']
sintese = f'''
=== Bloco 5 (medido no Colab, {GPU_NOME}) ===
Ponto de saturacao medido no OpenMP (threads) ...... ver mac/coleta_mac.sh
Banda maxima observada na CPU (GB/s) ............... ver mac/coleta_mac.sh
Fracao do tempo em transferencia, N=1e8, 1 rep ..... {f1:.1f}%  (mediana de 5; faixa {faixa.loc[('padrao', 1), 'min']:.1f}-{faixa.loc[('padrao', 1), 'max']:.1f}%)
Fracao com 50 repeticoes ........................... {f50:.1f}%  (mediana de 5; faixa {faixa.loc[('padrao', 50), 'min']:.1f}-{faixa.loc[('padrao', 50), 'max']:.1f}%)
PCIe H->D medido ................................... {pcie:.1f} GB/s (memoria do host paginavel: malloc)
Banda do kernel medida (50 rep) .................... {kbw:.1f} GB/s
'''
print(sintese)
(RES / 'bloco5_sintese.txt').write_text(sintese)

arq = shutil.make_archive('/content/resultados_colab', 'zip', RES)
print('pacote:', arq)
for f in sorted(RES.iterdir()):
    print(f'  {f.name:<40} {f.stat().st_size:>8} bytes')
try:
    from google.colab import files
    files.download(arq)
except Exception as e:
    print('(download automatico indisponivel:', e, ') -> baixe pelo painel de arquivos')
""")

if ASSISTIDA:
    for c in cells:
        if "PREDICOES = {" in c["source"]:
            c["source"] = c["source"].replace('": "",', '": "registrada pelo discente fora do notebook (ver relatorio)",')
nb = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}
for c in nb["cells"]:   # formato .ipynb: lista de linhas
    linhas = c["source"].split("\n")
    c["source"] = [l + "\n" for l in linhas[:-1]] + [linhas[-1]]
SAIDA.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
print(f"gerado: {SAIDA} ({len(cells)} celulas, kit sha256 {ZIP_SHA[:16]}...)")
