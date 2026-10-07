#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/../.."

W=audiobook_work/finetune
E2A_PY="$PWD/tts_env/Scripts/python.exe"
BASE="$PWD/modelos/xtts_base"
WHISPER=$(ls -d ~/.cache/huggingface/hub/models--openai--whisper-large-v3/snapshots/*/ | head -1)
RUN1=$(ls -d $W/treino/*/ | head -1)
export PYTHONUTF8=1

estado() { echo "$(date +%H:%M:%S) $1" >> $W/pipeline_estado.log; }
falhou() { estado "FALHOU: $1"; exit 1; }

estado "aguardando download e treino v1"
until grep -q "Finished downloading playlist" $W/download2.log 2>/dev/null; do sleep 20; done
until grep -q "TREINO_CONCLUIDO\|Traceback" $W/treino.log; do sleep 20; done
grep -q "TREINO_CONCLUIDO" $W/treino.log || falhou "treino v1"
estado "download e treino v1 concluidos"

estado "transcrevendo videos novos e montando dataset v2"
$E2A_PY -u scripts/finetune/preparar_dataset.py --raw $W/raw --saida $W/prep --modelo "$WHISPER" --batch 16 \
  --horas 5.5 --forcar-interjeicoes --repeticoes 4 --nome-dataset dataset_v2 > $W/prep3.log 2>&1 || falhou "prep v2"
estado "dataset v2 pronto"

estado "treino v2"
$E2A_PY -u scripts/finetune/treinar.py --base "$BASE" --dataset $W/prep/dataset_v2 --saida $W/treino_v2 \
  --nome shadow_slave_v2 --epocas 6 --batch 1 --acumulo 4 > $W/treino_v2.log 2>&1
grep -q "TREINO_CONCLUIDO" $W/treino_v2.log || falhou "treino v2"
RUN2=$(ls -d $W/treino_v2/*/ | head -1)
estado "treino v2 concluido"

estado "avaliando checkpoints"
.venv/Scripts/python.exe -u scripts/finetune/avaliar.py --run "v1=$RUN1" --run "v2=$RUN2" --base "$BASE" \
  --dataset $W/prep/dataset_v2 --saida $W/avaliacao --epoca-min 3 > $W/avaliacao.log 2>&1 || falhou "avaliacao"
estado "avaliacao concluida: $(grep MELHOR $W/avaliacao.log)"

estado "gerando amostras"
.venv/Scripts/python.exe -u scripts/finetune/amostras.py --modelo "base=$BASE" --modelo "novo=$W/modelo_final" \
  --saida $W/amostras > $W/amostras.log 2>&1 || falhou "amostras"
estado "amostras prontas"

estado "lote de 20 capitulos do vol 1"
.venv/Scripts/python.exe -u scripts/finetune/lote_vol1.py --de 4 --ate 23 > $W/lote.log 2>&1 || falhou "lote"
estado "LOTE CONCLUIDO: $(grep LOTE_CONCLUIDO $W/lote.log)"
estado "PIPELINE_COMPLETO"
