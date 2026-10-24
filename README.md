# projeto-avl-rubro-negra

Trabalho Prático I de **Algoritmos e Estruturas de Dados II (AED II)**.
Sistema de Clínica / Atendimento para cadastrar, buscar e remover pacientes
identificados pelo prontuário, comparando árvores AVL e Rubro-Negra.

## Responsabilidades e estado atual

| Integrante | Responsabilidade | Estado neste repositório |
| --- | --- | --- |
| 1 | AVL, operações, propriedades e instrumentação (`avl.py`) | Aguardando módulo |
| 2 | Rubro-Negra, operações, propriedades e instrumentação (`rubro_negra.py`) | Aguardando módulo |
| 3 | Pacientes, dados fictícios, menu, integração, experimentos e testes | Implementado |

O menu inicia sem os módulos das árvores. A validação dos dados de um paciente
e a geração de registros sintéticos funcionam independentemente deles.
Cadastro, consultas, remoção e medições reais dependem da integração **de ambas**
as árvores. Nenhuma árvore alternativa é usada pela aplicação e nenhum resultado
experimental foi coletado ou incluído nesta etapa.

O PDF do enunciado não estava disponível nos locais consultados. Esta entrega
segue os requisitos fornecidos para o Integrante 3; requisitos adicionais do
professor devem ser conferidos quando o documento estiver disponível.

## Estrutura

```text
modelos.py                 # Paciente e validação
gerar_dados.py             # Dados sintéticos reproduzíveis
integracao.py              # Contrato, importações protegidas e adaptação
main.py                    # Menu e coordenação entre as duas árvores
experimentos.py            # Cenários A–D, medição e exportação CSV
tests/
    __init__.py
    apoio.py               # Objetos exclusivos dos testes, sem árvores reais
    test_modelos.py
    test_gerar_dados.py
    test_main.py
    test_experimentos.py
resultados/
    .gitkeep
README.md
.gitignore
```

Os arquivos `avl.py` e `rubro_negra.py` serão fornecidos pelos integrantes 1 e 2.
Não foram criados arquivos vazios para substituí-los. As alterações do sistema
da clínica são desenvolvidas na branch `feature/sistema-clinica`.

## Requisitos e execução

Python **3.10 ou superior**, somente com a biblioteca padrão. Não é necessário
instalar dependências. Execute os comandos na raiz do repositório (no Windows,
também é possível substituir `python` por `py -3`).

```console
python main.py
```

O menu oferece cadastro (1), busca (2), remoção (3), listagem em ordem (4),
mínimo/máximo (5), três caminhamentos (6), altura/quantidade (7), estrutura (8),
estatísticas (9), validação (10), modo detalhado (11), geração fictícia (12)
e experimentos (13). Use `s` para selecionar AVL ou Rubro-Negra e `0` para sair.
O modo detalhado é controlado por árvore; cadastro e remoção afetam ambas.

Sem integração, a opção 1 ainda valida os quatro campos, mas informa que não
houve cadastro. A opção 12 gera uma amostra de até cinco pacientes e informa
que os dados não foram armazenados. Com as árvores disponíveis, essa opção
cadastra o lote inteiro em ambas, usando prontuários acima do maior já cadastrado.
Entradas inválidas são informadas sem encerrar o menu. EOF ou Ctrl+C encerram
normalmente. Os dados do menu são mantidos apenas em memória e não persistem
entre execuções.

## Modelo Paciente

| Campo | Tipo | Validação |
| --- | --- | --- |
| `prontuario` | `int` | Positivo; valores booleanos não são aceitos |
| `nome` | `str` | Não pode ser vazio ou conter apenas espaços |
| `data_nascimento` | `str` | Data real no formato exato `AAAA-MM-DD` |
| `telefone` | `str` | Preserva zeros iniciais, sem conversão de números |

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

## Contrato previsto para integração

Por padrão, `integracao.py` procura `avl.ArvoreAVL` e
`rubro_negra.ArvoreRubroNegra`. Ambas devem ter construtores sem argumentos e
produzir instâncias **novas, vazias e independentes**. Nomes de classes,
construtores ou retornos diferentes deverão ser adaptados nessa camada, sem
alterar o código dos colegas. O contrato ainda precisa ser confirmado com eles.

| Método | Retorno/efeito esperado |
| --- | --- |
| `inserir(paciente)` | `True` ao inserir, `False` se a chave já existir |
| `buscar(prontuario)` | O próprio `Paciente` armazenado ou `None` |
| `remover(prontuario)` | `True` ao remover, `False` se não existir |
| `minimo()`, `maximo()` | `Paciente` ou `None` se vazia |
| `pre_ordem()`, `em_ordem()`, `pos_ordem()` | Listas de `Paciente`; em ordem é crescente por prontuário |
| `altura()`, `quantidade()` | Inteiros; quantidade conta pacientes, excluindo sentinelas |
| `exibir()` | Texto a apresentar, ou impressão própria com retorno `None` |
| `validar()` | Booleano, `True` somente quando todas as propriedades forem satisfeitas |
| `estatisticas()` | Dicionário de contadores acumulados, conforme abaixo |
| `definir_modo_detalhado(ativo)` | Ativa/desativa impressão detalhada por instância |
| `reiniciar_estatisticas()` | Zera contadores sem alterar pacientes ou propriedades |

Os métodos funcionais e `definir_modo_detalhado` são exigidos para integração.
Os métodos de instrumentação podem faltar temporariamente: o menu e os
experimentos informam a limitação em vez de inventar valores. Precisam ser
confirmados antes da coleta definitiva:

- Nomes e construtores das classes, retornos e representação dos pacientes.
- Convenção de altura (arestas ou níveis) e altura da árvore vazia. A comparação
  de alturas só terá sentido após padronizar essa convenção.
- Dicionário `estatisticas()`: as chaves reconhecidas são `rotacoes`,
  `recoloracoes` e `nos_visitados`, com contadores inteiros não negativos.
  `nos_visitados` deve ser o total acumulado das visitas nas buscas. Outras
  chaves requerem adaptação explícita em `experimentos.py`.
- Contagem das rotações duplas e das recolorações, incluindo o tratamento
  de sentinelas, para que as métricas sejam comparáveis.
- Reinício de estatísticas e desativação completa das impressões detalhadas.

O menu guarda os pacientes confirmados em um dicionário apenas para coordenação
e recuperação. Consultas e caminhamentos são feitos nas árvores reais. Se uma
alteração falhar após modificar uma estrutura, ambas são reconstruídas a partir
do último estado confirmado. Essa recuperação preserva os pacientes, mas pode
mudar a forma das árvores e substitui as estatísticas pelas da reconstrução.
Se a recuperação também falhar, consultas e alterações ficam bloqueadas com
mensagem explícita; não há garantia de persistência dos dados ao reiniciar.

## Experimentos comparativos

Após integrar as duas árvores reais:

```console
python experimentos.py --tamanhos 100 1000 10000 --seed 42
python experimentos.py --tamanhos 10 --seed 42 --saida resultados/pequeno.csv
```

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
isolam as operações mesmo sem reinício. A média de visitas usa a diferença de
`nos_visitados` dividida pelo número de buscas, quando esse contador existir.
As visitas feitas pela validação não entram nessa média.

São produzidas 14 linhas por tamanho: duas para A, duas para B, quatro para C
e seis para D. Cada cenário é medido uma vez nesta infraestrutura inicial;
repetições e análise estatística da coleta definitiva ficam para a etapa conjunta.

### CSV

Destino padrão: `resultados/resultados.csv`, UTF-8, vírgula como separador e
cabeçalho. Uma nova exportação substitui o arquivo de destino; use `--saida`
para preservar execuções anteriores. As colunas são:

```text
arvore,experimento,quantidade_inicial,operacoes,seed,altura_final,quantidade_final,tempo_segundos,rotacoes,recoloracoes,media_nos_visitados,valido,limitacoes
```

`quantidade_inicial` identifica o tamanho do conjunto do cenário (nas inserções,
a árvore parte vazia). `operacoes` conta as inserções, buscas ou remoções
efetivamente chamadas. O tempo é o total desse lote, em segundos.
`valido` registra a validação estrutural bem-sucedida; casos inválidos abortam
a execução em vez de aparecerem como medições aprovadas.

Métricas ausentes ou não aplicáveis ficam **vazias**, nunca preenchidas com
zero por suposição. `limitacoes` explica contadores ausentes, inválidos ou
reinício indisponível. Rotações/recolorações são registradas para inserções e
remoções; visitas médias, para buscas. Recolorações podem não se aplicar à AVL.
Sem os módulos reais, a limitação é exibida no terminal e nenhum arquivo de
medições é criado. CSVs só devem ser versionados quando forem resultados reais
que o grupo pretende analisar; `.gitignore` não os oculta.

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
```

A suíte verifica validação, tipos, unicidade, reprodução, preservação das
listas e do estado aleatório global, menu sem módulos, erros de entrada,
coordenação entre estruturas, recuperação de falhas parciais, cenários
independentes, equivalência de sequências e retornos, isolamento das métricas
e exportação CSV. Os objetos de `tests/apoio.py` servem apenas para testar o
contrato; seus valores não são resultados experimentais. Os CSVs de teste
são gravados em diretórios temporários e removidos ao terminar.

Ainda dependem dos integrantes 1 e 2: integração das implementações reais,
validação conjunta do contrato, coleta definitiva e análise comparativa.
Os testes desta etapa não certificam o balanceamento de AVL ou Rubro-Negra.
