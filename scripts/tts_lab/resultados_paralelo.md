# Paralelismo de workers XTTS (cap. 349, 139 trechos, 714,6 s de audio, mesma seed)

| Workers | Tempo | Audio/s | RTF | Ganho | GPU util media | VRAM max | Reprovados QA |
|---|---|---|---|---|---|---|---|
| 1 | 585 s | 1,22 | 0,82 | 1,00x | 28% | 6,6 GB | 4 |
| 2 | 298 s | 2,40 | 0,42 | 1,96x | 79% | 9,1 GB | 4 |
| 3 | 237 s | 3,02 | 0,33 | 2,47x | 80% | 12,3 GB | 4 |

VRAM max inclui ~3,2 GB ja usados por outros programas. Escolhido: 3 workers.
