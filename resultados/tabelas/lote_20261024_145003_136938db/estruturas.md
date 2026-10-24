# Métricas estruturais

Valores ausentes ou não aplicáveis: —. Tempos em milissegundos; métricas estruturais conferidas entre repetições.

## A — Inserção crescente

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 100 | 100 | 0 | 7 | 93 | 0 | — |
| 100 | Rubro-Negra | 100 | 100 | 0 | 11 | 89 | 445 | — |
| 1000 | AVL | 1000 | 1000 | 0 | 10 | 990 | 0 | — |
| 1000 | Rubro-Negra | 1000 | 1000 | 0 | 17 | 983 | 4909 | — |
| 10000 | AVL | 10000 | 10000 | 0 | 14 | 9986 | 0 | — |
| 10000 | Rubro-Negra | 10000 | 10000 | 0 | 24 | 9976 | 49877 | — |

## B — Inserção aleatória

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 100 | 100 | 0 | 8 | 65 | 0 | — |
| 100 | Rubro-Negra | 100 | 100 | 0 | 8 | 55 | 227 | — |
| 1000 | AVL | 1000 | 1000 | 0 | 12 | 689 | 0 | — |
| 1000 | Rubro-Negra | 1000 | 1000 | 0 | 12 | 577 | 2305 | — |
| 10000 | AVL | 10000 | 10000 | 0 | 16 | 6946 | 0 | — |
| 10000 | Rubro-Negra | 10000 | 10000 | 0 | 16 | 5806 | 23230 | — |

## C — Busca existente

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 100 | 100 | 8 | 8 | — | — | 5.840000 |
| 100 | Rubro-Negra | 100 | 100 | 8 | 8 | — | — | 5.940000 |
| 1000 | AVL | 1000 | 1000 | 12 | 12 | — | — | 9.179000 |
| 1000 | Rubro-Negra | 1000 | 1000 | 12 | 12 | — | — | 9.265000 |
| 10000 | AVL | 10000 | 10000 | 16 | 16 | — | — | 12.561100 |
| 10000 | Rubro-Negra | 10000 | 10000 | 16 | 16 | — | — | 12.645800 |

## C — Busca inexistente

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 100 | 100 | 8 | 8 | — | — | 7.000000 |
| 100 | Rubro-Negra | 100 | 100 | 8 | 8 | — | — | 6.000000 |
| 1000 | AVL | 1000 | 1000 | 12 | 12 | — | — | 10.000000 |
| 1000 | Rubro-Negra | 1000 | 1000 | 12 | 12 | — | — | 10.000000 |
| 10000 | AVL | 10000 | 10000 | 16 | 16 | — | — | 14.000000 |
| 10000 | Rubro-Negra | 10000 | 10000 | 16 | 16 | — | — | 13.000000 |

## D — Remoção de 10%

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 10 | 90 | 8 | 8 | 4 | 0 | — |
| 100 | Rubro-Negra | 10 | 90 | 8 | 8 | 6 | 22 | — |
| 1000 | AVL | 100 | 900 | 12 | 12 | 35 | 0 | — |
| 1000 | Rubro-Negra | 100 | 900 | 12 | 12 | 48 | 203 | — |
| 10000 | AVL | 1000 | 9000 | 16 | 16 | 476 | 0 | — |
| 10000 | Rubro-Negra | 1000 | 9000 | 16 | 16 | 405 | 1786 | — |

## D — Remoção de 30%

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 30 | 70 | 8 | 7 | 10 | 0 | — |
| 100 | Rubro-Negra | 30 | 70 | 8 | 8 | 13 | 67 | — |
| 1000 | AVL | 300 | 700 | 12 | 12 | 119 | 0 | — |
| 1000 | Rubro-Negra | 300 | 700 | 12 | 12 | 130 | 597 | — |
| 10000 | AVL | 3000 | 7000 | 16 | 15 | 1337 | 0 | — |
| 10000 | Rubro-Negra | 3000 | 7000 | 16 | 16 | 1273 | 5782 | — |

## D — Remoção de 50%

| Pacientes | Árvore | Operações | Restantes | Altura inicial | Altura final | Rotações | Recolorações | Média de visitas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | AVL | 50 | 50 | 8 | 7 | 13 | 0 | — |
| 100 | Rubro-Negra | 50 | 50 | 8 | 7 | 24 | 116 | — |
| 1000 | AVL | 500 | 500 | 12 | 11 | 209 | 0 | — |
| 1000 | Rubro-Negra | 500 | 500 | 12 | 12 | 245 | 1070 | — |
| 10000 | AVL | 5000 | 5000 | 16 | 15 | 2143 | 0 | — |
| 10000 | Rubro-Negra | 5000 | 5000 | 16 | 15 | 2187 | 10079 | — |

