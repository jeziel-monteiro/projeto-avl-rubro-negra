# projeto-avl-rubro-negra

Trabalho Prático I de **Algoritmos e Estruturas de Dados II (AED II)**.
Sistema de Clínica / Atendimento para cadastrar, buscar e remover pacientes
identificados pelo prontuário, comparando árvores AVL e Rubro-Negra.

## Responsabilidades e estado atual

| Integrante | Identificação no histórico Git | Responsabilidade | Estado neste repositório |
| --- | --- | --- | --- |
| 1 | Arthur Djan | AVL, operações, propriedades e instrumentação (`avl.py`) | Implementado e integrado |
| 2 | Jeziel Monteiro | Rubro-Negra, operações, propriedades e instrumentação (`rubro_negra.py`) | Implementado e integrado |
| 3 | Oliviê Kalil de Menezes Miranda | Pacientes, dados fictícios, menu, integração, experimentos e testes | Finalizado com coleta e análise |

Implementações registradas nos commits `cb5e5ca` (AVL), `0f02c25`
(Rubro-Negra) e `17efb6e` (modelo).

As três branches dos integrantes estão integradas. O menu cadastra e remove
pacientes nas duas árvores reais e permite selecionar uma delas para consultas
e inspeção. Os experimentos medem essas mesmas implementações em instâncias
independentes, com métricas de rotações, recolorações e visitas nas buscas.
Os dados dos pacientes são sintéticos; as medições são obtidas por execução.

## Estrutura

```text
modelos.py                 # Paciente e validação
gerar_dados.py             # Dados sintéticos reproduzíveis
avl.py                     # Árvore AVL e instrumentação
rubro_negra.py             # Árvore Rubro-Negra e instrumentação
integracao.py              # Contrato, importações protegidas e adaptação
main.py                    # Menu e coordenação entre as duas árvores
experimentos.py            # Cenários A–D, medição e exportação CSV
coleta_experimentos.py     # Repetições sequenciais, lotes exclusivos e ambiente
analise_experimentos.py    # Tabelas, conferência estrutural e gráficos opcionais
docs/
    avl.md
    rubro_negra.md
tests/
    __init__.py
    apoio.py               # Objetos exclusivos dos testes, sem árvores reais
    test_modelos.py
    test_gerar_dados.py
    test_main.py
    test_experimentos.py
    test_avl.py
    test_rubro_negra.py
    test_integracao_real.py # Clínica, métricas e CSV com as árvores reais
    test_coleta_analise.py  # Alturas, lotes, metadados, estatística e PNGs
resultados/
    .gitkeep
    resultados.csv         # Histórico preservado; não tem altura_inicial
    execucoes/             # Lote definitivo: 5 CSVs de 42 linhas e ambiente.json
    validacao/             # Coleta pequena de conferência, separada da análise
    tabelas/               # Resumo CSV, tabelas Markdown e verificacao.json
    graficos/              # Seis figuras PNG por lote analisado
relatorio/
    metodologia_resultados.md
README.md
.gitignore
```

Os detalhes das estruturas e de suas invariantes estão em
[`docs/avl.md`](docs/avl.md) e [`docs/rubro_negra.md`](docs/rubro_negra.md).

## Requisitos e execução

Python **3.10 ou superior**. Sistema, coleta e tabelas usam somente a biblioteca
padrão; apenas a geração de PNGs utiliza `matplotlib`, opcional. Execute os
comandos na raiz do repositório (no Windows,
também é possível substituir `python` por `py -3`).

```console
python main.py
```

O menu oferece cadastro (1), busca (2), remoção (3), listagem em ordem (4),
mínimo/máximo (5), três caminhamentos (6), altura/quantidade (7), estrutura (8),
estatísticas (9), validação (10), modo detalhado (11), geração fictícia (12)
e experimentos (13). Use `s` para selecionar AVL ou Rubro-Negra e `0` para sair.
O modo detalhado é controlado por árvore; cadastro e remoção afetam ambas.

A opção 1 valida os quatro campos e cadastra o paciente em ambas as árvores.
A opção 12 mostra uma amostra de até cinco pacientes e cadastra o lote inteiro
nas duas estruturas, usando prontuários acima do maior já cadastrado.
Entradas inválidas são informadas sem encerrar o menu. EOF ou Ctrl+C encerram
normalmente. Os dados do menu são mantidos apenas em memória e não persistem
entre execuções.

## Modelo Paciente

| Campo | Tipo | Validação |
| --- | --- | --- |
| `prontuario` | `int` | Positivo; valores booleanos não são aceitos |
| `nome` | `str` | Não pode ser vazio ou conter apenas espaços |
| `data_nascimento` | `str` | Data real no formato exato `AAAA-MM-DD` |
| `telefone` | `str` | Obrigatório; rejeita vazio e somente espaços, tabulações ou quebras de linha; preserva zeros iniciais |

```python
from modelos import Paciente

paciente = Paciente(1025, "Maria Oliveira", "1998-05-12", "01999998888")
print(paciente)
```

A dataclass é imutável para evitar mudanças na chave ou dados inválidos após
a criação. A igualdade considera os quatro campos. As árvores devem ordenar
explicitamente por `paciente.prontuario`, que é a chave única; a classe não
implementa ordenação nem um cadastro global de prontuários. A aplicação rejeita
duplicatas antes de alterar as estruturas.
O telefone é armazenado exatamente como informado, sem conversão para inteiro
nem imposição adicional de formato ou quantidade de dígitos.

## Dados fictícios

```console
python gerar_dados.py --quantidade 100 --seed 42
python gerar_dados.py --quantidade 1000 --seed 42 --aleatorio
```

```python
from gerar_dados import gerar_pacientes, ordenar_pacientes, embaralhar_pacientes

pacientes = gerar_pacientes(quantidade=1000, seed=42)
crescentes = ordenar_pacientes(pacientes)
aleatorios = embaralhar_pacientes(pacientes, seed=42)
# Para gerar outro lote sem colisões:
outro_lote = gerar_pacientes(10, seed=42, prontuario_inicial=1001)
```

Cada chamada gera prontuários consecutivos únicos a partir de 1 (configurável).
Listas geradas em chamadas diferentes podem repetir prontuários: combine os
lotes usando `prontuario_inicial`. A quantidade pode ser zero ou qualquer
inteiro positivo, incluindo 100, 1.000 e 10.000.

Os nomes levam a indicação “Fictício”, as datas ficam entre 1940-01-01 e
2020-12-31, e os telefones sintéticos começam com `00`; não representam contatos
reais. Intervalos de datas fixos evitam que a reprodução dependa do dia da execução.
O gerador usa `random.Random(seed)` local. Para a mesma semente inteira, versão
de Python e parâmetros, os dados e embaralhamentos são reproduzíveis; `seed=None`
solicita aleatoriedade sem reprodução garantida. Ordenar e embaralhar produzem
novas listas, preservando a original. Não utilize dados reais de pacientes.

## Contrato de integração

`integracao.py` carrega `avl.ArvoreAVL` e `rubro_negra.ArvoreRubroNegra`.
Ambas aceitam construção sem argumentos e produzem instâncias
**novas, vazias e independentes**, verificadas antes de iniciar as operações.

| Método | Retorno/efeito esperado |
| --- | --- |
| `inserir(paciente)` | `True` ao inserir, `False` se a chave já existir |
| `buscar(prontuario)` | O próprio `Paciente` armazenado ou `None` |
| `remover(prontuario)` | `True` ao remover, `False` se não existir |
| `minimo()`, `maximo()` | `Paciente` ou `None` se vazia |
| `pre_ordem()`, `em_ordem()`, `pos_ordem()` | Listas de `Paciente`; em ordem é crescente por prontuário |
| `altura()`, `quantidade()` | Inteiros; altura em níveis (vazia 0, folha 1); quantidade exclui sentinelas |
| `exibir()` | Texto com a estrutura; não imprime por conta própria |
| `validar()` | Booleano, `True` somente quando todas as propriedades forem satisfeitas |
| `estatisticas()` | Cópia dos contadores de balanceamento e das visitas da última busca |
| `definir_modo_detalhado(ativo)` | Ativa/desativa impressão detalhada por instância |
| `reiniciar_estatisticas()` | Zera contadores sem alterar pacientes ou propriedades |

As duas implementações fornecem estas chaves inteiras não negativas em
`estatisticas()`:

| Chave | Significado |
| --- | --- |
| `rotacoes_insercao` | Rotações simples acumuladas nas inserções |
| `rotacoes_remocao` | Rotações simples acumuladas nas remoções |
| `recoloracoes_insercao` | Mudanças de cor acumuladas nas inserções |
| `recoloracoes_remocao` | Mudanças de cor acumuladas nas remoções |
| `nos_visitados_ultima_busca` | Nós reais visitados apenas pela última chamada de `buscar()` |

Uma rotação dupla conta como duas rotações simples. Recolorações são sempre
zero na AVL. Na Rubro-Negra contam mudanças efetivas de cor em nós reais,
incluindo a raiz e excluindo o sentinela NIL. A contagem de visitas inclui
o nó encontrado e exclui filhos ausentes/sentinelas. A cada busca esse valor
é substituído, não acumulado. `reiniciar_estatisticas()` zera os contadores
e a última busca, preservando pacientes e modo detalhado.

O menu guarda os pacientes confirmados em um dicionário apenas para coordenação
e recuperação. Consultas e caminhamentos são feitos nas árvores reais. Se uma
alteração falhar após modificar uma estrutura, ambas são reconstruídas a partir
do último estado confirmado. Essa recuperação preserva os pacientes, mas pode
mudar a forma das árvores e substitui as estatísticas pelas da reconstrução.
Se a recuperação também falhar, consultas e alterações ficam bloqueadas com
mensagem explícita; não há garantia de persistência dos dados ao reiniciar.

## Experimentos comparativos

Execute os cenários com as árvores reais:

```console
python experimentos.py --tamanhos 100 1000 10000 --seed 42
python experimentos.py --tamanhos 10 --seed 42 --saida resultados/pequeno.csv
```

A sintaxe original foi mantida. Como o destino padrão já contém uma coleta
histórica, o primeiro comando recusa sobrescrevê-la. Para uma nova execução
isolada, informe `--saida resultados/nova_execucao.csv` com um nome ainda livre.
Para as cinco repetições, prefira o utilitário abaixo, que reserva um lote novo.

Também é possível usar a opção 13 do menu ou chamar `executar_experimentos`
e `exportar_csv` separadamente. As instâncias experimentais são independentes
das árvores usadas no menu. A execução é interrompida se faltar uma árvore,
houver incompatibilidade de contrato, propriedades inválidas ou retorno
incorreto de operações. A CLI não exporta CSV nesses casos.

| Experimento | Procedimento |
| --- | --- |
| A — Inserção crescente | Insere a mesma sequência crescente nas duas árvores vazias |
| B — Inserção aleatória | Embaralha o mesmo conjunto com semente fixa e usa novas árvores |
| C — Busca | Constrói com a sequência B; mede todas as chaves existentes e igual número de inexistentes em lotes separados |
| D — Remoção | Reconstrói para cada cenário de 10%, 30% e 50%; remove os mesmos prontuários nas duas estruturas |

Os percentuais são arredondados para baixo (`quantidade * percentual // 100`);
em conjuntos pequenos pode haver cenários com zero remoções. Os cenários usam
prefixos da ordem aleatória dos prontuários. As chaves inexistentes são maiores
que qualquer prontuário do conjunto. Cada lote é conferido contra os pacientes
originais, incluindo todos os campos, e as propriedades são validadas depois.

`time.perf_counter()` mede o lote de chamadas, incluindo o laço e a coleta dos
retornos. Geração, construção prévia de árvores para busca/remoção, validação,
leitura de estatísticas, impressão e gravação ficam fora do intervalo medido.
O modo detalhado permanece desativado. Contadores são reiniciados antes de cada
lote quando possível; diferenças entre leituras anteriores e posteriores
isolam as operações mesmo sem reinício. A e B usam os contadores com sufixo
`_insercao`; D usa aqueles com sufixo `_remocao`.

Para C, uma primeira passagem cronometra as buscas. Uma segunda passagem,
fora do intervalo medido, repete as mesmas chaves e soma
`nos_visitados_ultima_busca` imediatamente após cada busca. A média é essa
soma dividida pelo número de buscas do lote. Os retornos da segunda passagem
devem coincidir com os esperados e a coleção é conferida antes e depois dela.
As validações e leituras de estatísticas não entram no tempo das buscas.

São produzidas 14 linhas por tamanho: duas para A, duas para B, quatro para C
e seis para D. A altura inicial é medida imediatamente antes de cada lote,
fora do cronômetro: zero em A/B, altura da árvore construída em C/D. As buscas
preservam a altura. A altura final também é lida fora do cronômetro, usando
a convenção das duas árvores: vazia 0, folha 1.

### Cinco repetições e análise reproduzível

```console
python coleta_experimentos.py --tamanhos 100 1000 10000 --seed 42 --repeticoes 5
```

Cada chamada cria `resultados/execucoes/lote_DATA_HORA_IDENTIFICADOR/`, com
`execucao_01.csv` a `execucao_05.csv` e `ambiente.json`. Mantêm-se a semente,
os pacientes e as sequências; as instâncias são novas em cada execução.
Os CSVs guardam tempos reais em segundos: 42 linhas por execução, 210 no lote.
Pastas de lotes anteriores e arquivos existentes são preservados. Se uma
execução falhar, o manifesto registra a falha e os CSVs anteriores permanecem;
a análise recusa lotes incompletos. `--destino` permite escolher outra pasta.

Para gerar somente tabelas, substitua `CAMINHO_DO_LOTE` pela pasta impressa:

```console
python analise_experimentos.py CAMINHO_DO_LOTE --sem-graficos
```

Para gerar também os seis PNGs, instale a dependência opcional em um ambiente
virtual (versão usada nesta coleta: `matplotlib==3.11.2`):

```console
python -m venv env
env\Scripts\python -m pip install matplotlib==3.11.2
env\Scripts\python analise_experimentos.py CAMINHO_DO_LOTE
```

Em Linux/macOS, use `env/bin/python` nos dois últimos comandos. A análise
lê apenas os CSVs listados no manifesto e verifica seus hashes. Produz
`resultados/tabelas/NOME_DO_LOTE/{resumo.csv,estruturas.md,tempos.md,verificacao.json}`
e `resultados/graficos/NOME_DO_LOTE/*.png`. Não refaz a coleta dos tempos.
Para repetir uma análise já existente, use `--saida resultados/reanalise_01`;
diretórios ocupados são recusados. `--sem-graficos` também reserva sua pasta;
ao acrescentar PNGs depois, escolha uma nova saída.

As tabelas calculam mediana, mínimo, máximo e amplitude (máximo − mínimo) em
milissegundos para cada tamanho, árvore e cenário. Alturas, rotações,
recolorações e visitas são conferidas entre repetições; diferenças estruturais
interrompem a análise para investigação. Valores ausentes continuam vazios,
sem serem tratados como zero. As figuras de tempo mostram mediana e barras
de erro do mínimo ao máximo; cada painel explicita seu cenário e escala.

### CSV

Destino padrão: `resultados/resultados.csv`, UTF-8, vírgula como separador e
cabeçalho. A exportação usa criação exclusiva e recusa arquivos existentes;
use `--saida` com nome novo para preservar execuções anteriores. As colunas são:

```text
arvore,experimento,quantidade_inicial,operacoes,seed,altura_inicial,altura_final,quantidade_final,tempo_segundos,rotacoes,recoloracoes,media_nos_visitados,valido,limitacoes
```

`quantidade_inicial` identifica o tamanho do conjunto do cenário (nas inserções,
a árvore parte vazia). `operacoes` conta as inserções, buscas ou remoções do
lote cronometrado; a passagem adicional de coleta de visitas não aumenta esse
campo nem o tempo informado. O tempo é o total do lote, em segundos.
`valido` registra a validação estrutural bem-sucedida; casos inválidos abortam
a execução em vez de aparecerem como medições aprovadas.

Métricas ausentes ou não aplicáveis ficam **vazias**, nunca preenchidas com
zero por suposição. `limitacoes` explica contadores ausentes, inválidos ou
reinício indisponível. Rotações/recolorações são registradas para inserções e
remoções; visitas médias, para buscas. Recolorações da AVL são registradas como
`0`, assim como qualquer outro contador disponível cujo resultado seja zero.
As métricas aplicáveis das duas árvores reais são preenchidas e `limitacoes`
fica vazio quando a coleta é completa. Os objetos simulados dos testes também
exercitam contratos incompletos e métricas inválidas, que geram limitações
explícitas em vez de números artificiais.

[`resultados/resultados.csv`](resultados/resultados.csv) contém a execução
histórica de 42 linhas, anterior à medição da altura inicial. Seu conteúdo foi
preservado; nenhuma altura inicial foi preenchida retroativamente. Esse CSV
não participa da estatística do lote definitivo.

### Coleta definitiva verificada

O lote [`lote_20261024_145003_136938db`](resultados/execucoes/lote_20261024_145003_136938db/ambiente.json)
foi coletado em **24/10/2026, 14:50:03–14:50:08 (America/Manaus, UTC−04)**,
com Python **3.15.0**, Windows 11 **10.0.26200**, arquitetura **AMD64/64 bits**.
O processador foi identificado por `platform.processor()` como
`Intel64 Family 6 Model 183 Stepping 1, GenuineIntel`; o nome comercial não
foi identificado. O cronômetro usa `QueryPerformanceCounter()`, resolução
informada de `1e-7 s`. O manifesto contém versão completa, comando, horários
por execução, commit `138a4bf`, estado Git e hashes do código e dos CSVs.

Foram verificadas cinco execuções, 210 linhas, todas as validações estruturais
aprovadas e métricas aplicáveis completas. Os 42 grupos apresentaram métricas
estruturais idênticas entre repetições. Consulte:

- [Tempos: medianas, extremos e amplitudes](resultados/tabelas/lote_20261024_145003_136938db/tempos.md).
- [Alturas, rotações, recolorações e visitas](resultados/tabelas/lote_20261024_145003_136938db/estruturas.md).
- [Tabela completa em CSV](resultados/tabelas/lote_20261024_145003_136938db/resumo.csv).
- [Gráficos PNG](resultados/graficos/lote_20261024_145003_136938db).
- [Metodologia, resultados e limitações](relatorio/metodologia_resultados.md).

As buscas inexistentes usam chaves acima do maior prontuário e percorrem o
caminho à direita; seus resultados não representam todos os padrões possíveis
de buscas malsucedidas. Tempos dependem do ambiente e da carga concorrente.
Uma única semente e cinco repetições não permitem afirmar superioridade geral
de uma estrutura nem inferir velocidade somente pela altura.

## Testes

```console
python -m unittest discover -s tests -v
```

Para executar uma etapa isolada:

```console
python -m unittest tests.test_modelos -v
python -m unittest tests.test_gerar_dados -v
python -m unittest tests.test_main -v
python -m unittest tests.test_experimentos -v
python -m unittest tests.test_avl -v
python -m unittest tests.test_rubro_negra -v
python -m unittest tests.test_integracao_real -v
python -m unittest tests.test_coleta_analise -v
```

A suíte verifica validação, tipos, unicidade, reprodução, preservação das
listas e do estado aleatório global, menu sem módulos, erros de entrada,
coordenação entre estruturas, recuperação de falhas parciais, cenários
independentes, equivalência de sequências e retornos, isolamento das métricas
e exportação CSV. Os objetos de `tests/apoio.py` servem apenas para testar o
contrato; seus valores não são resultados experimentais. Os CSVs de teste
são gravados em diretórios temporários e removidos ao terminar.

Os testes de AVL e Rubro-Negra verificam operações, balanceamento, propriedades,
contadores e corrupção de estruturas. `test_integracao_real.py` usa diretamente
as duas classes, sem mocks, para conferir pacientes equivalentes, menu,
quantidades, alturas, experimentos e CSV. A média de visitas é comparada com
uma contagem independente dos caminhos nos nós. Os conjuntos incluem 10, 30,
100 e 1.000 pacientes. Testes com objetos simulados continuam verificando
falhas parciais, métricas incompletas, retornos divergentes e isolamento do tempo.

A verificação final executou **123 testes com sucesso**, incluindo os seis PNGs
com a dependência opcional instalada. Sem `matplotlib`, somente esse teste
de PNGs é pulado; os testes do sistema e das tabelas continuam independentes
dela. Os novos testes usam conjuntos pequenos, separados da coleta definitiva.
Neste ambiente, os testes precisaram executar fora do sandbox por restrições
de acesso aos diretórios temporários do Windows; isso não exigiu alterar testes
antigos ou implementações das árvores.
