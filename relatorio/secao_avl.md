# Árvore AVL

A Árvore AVL armazena os pacientes do sistema de Clínica / Atendimento usando
o número do prontuário como chave única. A implementação está em
[`avl.py`](../avl.py). Nome, data de nascimento e telefone acompanham o paciente,
mas não participam das comparações que determinam sua posição na árvore.
O balanceamento limita a diferença de altura entre os filhos de cada nó,
evitando que sequências crescentes de prontuários formem uma cadeia linear.

## Representação dos registros e dos nós

A classe `ArvoreAVL` aceita objetos com o atributo `prontuario` inteiro positivo.
Na aplicação integrada, os registros são instâncias de `Paciente`, definida em
[`modelos.py`](../modelos.py). Esse modelo é imutável, impedindo a alteração da
chave depois do cadastro. A árvore preserva o objeto recebido: busca, extremos
e caminhamentos retornam pacientes, sem expor os nós como resultado.

A classe interna `_No` contém:

| Atributo | Função |
| --- | --- |
| `paciente` | Referência ao registro completo |
| `prontuario` | Cópia da chave usada na ordenação |
| `esquerda` e `direita` | Referências aos filhos |
| `altura` | Altura da subárvore cuja raiz é o nó |

Os filhos ausentes e a raiz da árvore vazia são representados por `None`.
Não há referência ao pai: as operações recursivas retornam a nova raiz de cada
subárvore, permitindo reconectar os ramos após uma rotação. Cada instância
mantém seus próprios nós, quantidade de pacientes e contadores.

Prontuários menores ficam na subárvore esquerda, e maiores, na direita.
Uma duplicata retorna `False` sem sobrescrever o paciente existente. A árvore
recusa booleanos, textos, valores fracionários, zero, negativos e objetos sem
prontuário. A validação dos demais campos pertence ao modelo de pacientes.

## Propriedades de balanceamento e controle das alturas

A estrutura mantém simultaneamente três condições:

1. A ordenação binária é estrita em relação a todos os ancestrais.
2. A altura armazenada em cada nó corresponde à altura real de sua subárvore.
3. O fator de balanceamento de cada nó pertence ao intervalo de -1 a +1.

A altura conta níveis de nós reais: a árvore vazia tem altura 0, e uma folha
tem altura 1. Para um nó existente, as definições são:

```text
h(nó) = 1 + máximo(h(esquerda), h(direita))
FB(nó) = h(esquerda) - h(direita)
```

Um fator positivo indica maior altura à esquerda; um negativo, à direita.
Um fator zero indica alturas iguais. A função `_atualizar_altura()` calcula
a altura a partir dos filhos, e `_fator()` calcula a diferença. A consulta
pública `altura()` usa a altura mantida na raiz, sem percorrer toda a árvore.

O limite local do fator também limita a altura total. O menor número de nós
de uma AVL de altura `h` obedece à recorrência
`N(h) = 1 + N(h - 1) + N(h - 2)`, com `N(0) = 0` e `N(1) = 1`.
Seu crescimento é do tipo Fibonacci; consequentemente, a altura cresce de
forma logarítmica em relação à quantidade de pacientes.

## Inserção e suas correções

`inserir(paciente)` verifica o prontuário e chama `_inserir()`. As comparações
conduzem ao ramo esquerdo ou direito até alcançar um filho ausente, onde um
novo nó é criado com altura 1. Se a chave já existir, a operação termina sem
alterar a árvore, sua quantidade ou seus contadores de rotação.

Ao retornar da recursão, cada ancestral do novo nó passa por `_reequilibrar()`.
Esse método atualiza a altura, calcula o fator e, se necessário, aplica uma
rotação simples ou dupla. A nova raiz da subárvore é devolvida à chamada
anterior. No nível superior, `self.raiz` recebe a raiz resultante, inclusive
quando a correção muda a raiz de toda a árvore.

O contador de pacientes aumenta uma única vez, depois de confirmada a inserção.
As rotações reorganizam os nós existentes e não alteram esse contador.

## Busca, extremos e caminhamentos

`buscar(prontuario)` percorre os nós de forma iterativa. A cada nó real
inspecionado, compara a chave e escolhe o próximo ramo. Retorna o paciente
armazenado quando encontra a chave, ou `None` ao alcançar um filho ausente.
A busca não modifica alturas nem provoca rotações.

`minimo()` segue pelos filhos esquerdos até a menor chave; `maximo()` segue
pelos direitos até a maior. Ambos retornam `None` na árvore vazia.

Os três caminhamentos retornam novas listas com os objetos dos pacientes:

| Caminhamento | Ordem das visitas |
| --- | --- |
| Pré-ordem | Raiz, esquerda, direita |
| Em ordem | Esquerda, raiz, direita |
| Pós-ordem | Esquerda, direita, raiz |

O caminhamento em ordem produz prontuários estritamente crescentes. Ele permite
conferir os registros e a ordenação, mas não verifica sozinho o balanceamento;
essa verificação depende também das alturas de todos os nós.

## Remoção e suas correções

`remover(prontuario)` rejeita uma chave inválida e chama `_remover()` para
localizar o nó. Uma chave inexistente retorna `False`, preservando o cadastro.
Quando a chave existe, há três situações:

| Situação | Tratamento |
| --- | --- |
| Nó sem filhos | Retorna `None` para retirar o vínculo com o nó |
| Nó com um filho | Retorna esse filho como nova raiz do ramo |
| Nó com dois filhos | Substitui o registro pelo sucessor em ordem e remove sua ocorrência antiga na subárvore direita |

O sucessor é o nó de menor prontuário da subárvore direita. A implementação
atribui ao nó-alvo a referência ao paciente completo do sucessor e sua chave,
preservando todos os atributos associados. Em seguida, exclui a ocorrência
antiga do sucessor. O objeto do paciente sobrevivente mantém sua identidade,
e o contador de pacientes diminui uma única vez na operação pública.

Durante o retorno recursivo, `_reequilibrar()` atualiza as alturas e corrige
os ancestrais afetados. A exclusão pode reduzir a altura de um ramo e exigir
correções em vários níveis até a raiz. Por isso, o algoritmo não encerra o
processo depois da primeira rotação encontrada.

Um caso relevante da remoção ocorre quando o nó desequilibrado possui um filho
mais alto com fator zero. A correção usa uma rotação simples. O exemplo de
remoção apresentado adiante reproduz exatamente essa situação.

## Rotações LL, RR, LR e RL

As letras descrevem a configuração dos ramos que produzem o desequilíbrio.
Quando `FB > 1`, o ramo esquerdo está mais alto; quando `FB < -1`, o direito
está mais alto. O fator do filho determina a correção:

| Caso | Condição no nó e no filho | Correção | Inserção ilustrativa |
| --- | --- | --- | --- |
| LL | `FB > 1` e fator do filho esquerdo `>= 0` | Rotação à direita no nó | `30, 20, 10` |
| RR | `FB < -1` e fator do filho direito `<= 0` | Rotação à esquerda no nó | `10, 20, 30` |
| LR | `FB > 1` e fator do filho esquerdo `< 0` | Esquerda no filho; direita no nó | `30, 10, 20` |
| RL | `FB < -1` e fator do filho direito `> 0` | Direita no filho; esquerda no nó | `10, 30, 20` |

Uma rotação à direita promove o filho esquerdo. O antigo filho direito do
promovido passa a ser o filho esquerdo do nó rebaixado. Na rotação à esquerda,
os lados são espelhados. Essa transferência preserva a ordenação dos prontuários
entre os dois nós envolvidos e a subárvore transferida.

Após alterar os vínculos, a implementação atualiza primeiro a altura do nó
rebaixado e depois a do promovido, porque a segunda depende da primeira.
Cada rotação simples altera uma quantidade constante de referências e alturas.
As correções duplas combinam duas dessas operações.

## Validação da estrutura

`validar()` percorre a árvore com uma pilha explícita em pós-ordem. Para cada
nó, transporta os limites inferior e superior herdados dos ancestrais e
recalcula sua altura depois de verificar os filhos. Assim, não depende da
correção das alturas armazenadas para decidir se o equilíbrio é válido.

A rotina confere:

- Prontuários inteiros positivos e igualdade entre chave do nó e do paciente.
- Ordenação binária estrita em relação a todos os ancestrais.
- Alturas armazenadas inteiras e iguais às alturas recalculadas.
- Diferença de altura entre os filhos de no máximo um em todos os nós.
- Ausência de ciclos, nós compartilhados e referências inválidas de filhos.
- Quantidade de nós alcançados igual ao contador de pacientes armazenado.

O conjunto de identificadores visitados detecta vínculos repetidos. A pilha
explícita permite rejeitar uma estrutura corrompida profunda sem depender do
limite de recursão. A validação retorna um booleano e não altera pacientes,
alturas, vínculos ou estatísticas. As operações normais pressupõem que os
detalhes internos da árvore não sejam modificados externamente.

## Estatísticas e modo detalhado

`estatisticas()` retorna uma cópia de um dicionário com cinco campos:

| Campo | Medida |
| --- | --- |
| `rotacoes_insercao` | Rotações simples acumuladas nas inserções |
| `rotacoes_remocao` | Rotações simples acumuladas nas remoções |
| `recoloracoes_insercao` | Sempre zero, pois a AVL não utiliza cores |
| `recoloracoes_remocao` | Sempre zero, pois a AVL não utiliza cores |
| `nos_visitados_ultima_busca` | Nós reais visitados pela última busca |

Uma rotação simples acrescenta uma unidade ao contador da operação que a
provocou. LR e RL acrescentam duas unidades. Os campos de recoloração mantêm
a mesma interface de coleta da Rubro-Negra, embora não representem eventos
da AVL. As métricas são independentes entre instâncias.

O contador da busca inclui o nó encontrado, quando houver. Uma busca ausente
conta somente os nós reais percorridos até o filho `None`. Uma chave inválida
ou uma busca em árvore vazia registra zero. Somente `buscar()` atualiza essa
medida; inserções, remoções e outras consultas a preservam.

`reiniciar_estatisticas()` zera os cinco campos sem apagar os pacientes nem
alterar o modo detalhado. Os experimentos devem coletar as visitas logo após
cada busca e calcular a média sobre as buscas do cenário.

Com o modo detalhado ativo, as atualizações mostram a chave da operação, o nó
desequilibrado, seu fator, o caso LL/RR/LR/RL, as rotações e a estrutura final.
`exibir()` retorna essa estrutura como texto; a impressão ocorre por chamada
explícita ou pelo modo detalhado. Nas medições de tempo, o modo permanece
desligado para excluir esse custo.

## Exemplos executados

Os exemplos utilizam o modelo real `Paciente` e foram executados na raiz do
repositório. Os blocos Python podem ser executados em sequência no interpretador.
A preparação comum é:

```python
from avl import ArvoreAVL
from modelos import Paciente


def paciente(chave):
    return Paciente(chave, f"Paciente fictício {chave}", "2000-01-01", "00900000000")


def preparar(chaves):
    arvore = ArvoreAVL()
    for chave in chaves:
        assert arvore.inserir(paciente(chave))
        assert arvore.validar()
    return arvore
```

Os contadores são reiniciados após a preparação, isolando a operação destacada.
As árvores antes e depois são saídas reais de `exibir()`: `h` indica a altura,
`FB` o fator de balanceamento, e `E`/`D` identificam os filhos esquerdo/direito.

### Inserção com rotação dupla LR

A preparação insere `30, 10`; a operação destacada insere `20`:

```python
arvore = preparar((30, 10))
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.inserir(paciente(20))
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [10, 20, 30]
assert arvore.altura() == 2
assert arvore.estatisticas()["rotacoes_insercao"] == 2
assert arvore.estatisticas()["rotacoes_remocao"] == 0
print(arvore.exibir())
```

Antes da inserção:

```text
Raiz: 30 (h=2, FB=1)
|-- E: 10 (h=1, FB=0)
|   |-- E: vazio
|   `-- D: vazio
`-- D: vazio
```

Depois da correção:

```text
Raiz: 20 (h=2, FB=0)
|-- E: 10 (h=1, FB=0)
|   |-- E: vazio
|   `-- D: vazio
`-- D: 30 (h=1, FB=0)
    |-- E: vazio
    `-- D: vazio
```

A inserção coloca 20 à direita de 10. O fator de 30 chega a +2, enquanto o de
seu filho esquerdo 10 é -1: trata-se do caso LR. A rotação à esquerda em 10
promove 20 dentro desse ramo. A rotação à direita em 30 promove 20 à raiz.
A quantidade passa de dois para três pacientes, a altura permanece 2 e a
operação contabiliza duas rotações de inserção.

### Remoção com rebalanceamento e filho de fator zero

A preparação insere `30, 20, 40, 10, 25`; a operação destacada remove `40`:

```python
arvore = preparar((30, 20, 40, 10, 25))
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.remover(40)
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [10, 20, 25, 30]
assert arvore.altura() == 3
assert arvore.quantidade() == 4
assert arvore.estatisticas()["rotacoes_insercao"] == 0
assert arvore.estatisticas()["rotacoes_remocao"] == 1
print(arvore.exibir())
```

Antes da remoção:

```text
Raiz: 30 (h=3, FB=1)
|-- E: 20 (h=2, FB=0)
|   |-- E: 10 (h=1, FB=0)
|   |   |-- E: vazio
|   |   `-- D: vazio
|   `-- D: 25 (h=1, FB=0)
|       |-- E: vazio
|       `-- D: vazio
`-- D: 40 (h=1, FB=0)
    |-- E: vazio
    `-- D: vazio
```

Depois da correção:

```text
Raiz: 20 (h=3, FB=-1)
|-- E: 10 (h=1, FB=0)
|   |-- E: vazio
|   `-- D: vazio
`-- D: 30 (h=2, FB=1)
    |-- E: 25 (h=1, FB=0)
    |   |-- E: vazio
    |   `-- D: vazio
    `-- D: vazio
```

A remoção elimina a folha 40 e reduz a altura do ramo direito de 30 para zero.
Seu ramo esquerdo mantém altura 2, produzindo fator +2. O filho 20 tem fator
zero; a implementação identifica o caso LL e rotaciona 30 à direita.
O prontuário 20 torna-se raiz, e seu antigo filho direito 25 passa a ser o
filho esquerdo de 30. A ordenação permanece correta. A altura total continua
3, a quantidade diminui para quatro e ocorre uma rotação de remoção.

Na árvore resultante, as visitas de busca também podem ser reproduzidas:

```python
assert arvore.buscar(20).prontuario == 20
assert arvore.nos_visitados_ultima_busca == 1
assert arvore.buscar(25).prontuario == 25
assert arvore.nos_visitados_ultima_busca == 3
assert arvore.buscar(99) is None
assert arvore.nos_visitados_ultima_busca == 2
```

Os caminhos são `20`, `20 -> 30 -> 25` e `20 -> 30 -> None`, respectivamente.
O filho ausente da última busca não é contado. Cada chamada substitui a medida
da busca anterior.

### Síntese dos exemplos

| Preparação | Operação isolada | Altura antes/depois | Quantidade antes/depois | Rotações |
| --- | --- | --- | --- | ---: |
| `30, 10` | Inserir `20` | 2 / 2 | 2 / 3 | 2 na inserção |
| `30, 20, 40, 10, 25` | Remover `40` | 3 / 3 | 5 / 4 | 1 na remoção |

Nos dois estados finais, `validar()` retorna `True`. As recolorações são zero.
Para acompanhar as mensagens de correção na defesa, ative
`arvore.definir_modo_detalhado(True)` antes da operação destacada. Os exemplos
são demonstrações de funcionamento; seus contadores isolados não medem o
desempenho comparativo das estruturas.

## Complexidade das operações

Com a árvore válida e o modo detalhado desligado, a altura logarítmica limita
o número de ancestrais percorridos. As rotações corrigem os ramos sem
reconstruir toda a árvore.

| Operação | Custo de tempo |
| --- | --- |
| Inserção, busca e remoção | `O(log n)` |
| Mínimo e máximo | `O(log n)` |
| Pré-ordem, em ordem e pós-ordem | `O(n)` |
| Altura e quantidade | `O(1)`, mantidas nas atualizações |
| Validação | `O(n)` |
| Leitura ou reinício das estatísticas | `O(1)` |

As operações recursivas usam `O(log n)` de pilha em uma árvore válida.
A validação usa `O(n)` de memória auxiliar para as estruturas de visita e
alturas. Os caminhamentos produzem listas com `n` pacientes. A exibição visita
os nós e gera texto cujo tamanho depende também da indentação. Com o modo
detalhado ativo, o custo de gerar e imprimir esse texto soma-se ao da atualização.

## Testes e verificação dos resultados

A suíte de [`tests/test_avl.py`](../tests/test_avl.py) contém 32 testes
automatizados, executados sem falhas. A rotina `conferir_invariantes()` dos
testes inspeciona diretamente os nós e recalcula alturas, ordenação, equilíbrio
e quantidade, além de chamar `validar()`. Dessa forma, a verificação dos
resultados não depende exclusivamente do validador da implementação.

| Grupo de verificações | Situações cobertas |
| --- | --- |
| Operações básicas | Árvore vazia, busca presente/ausente, extremos, caminhamentos e novas listas |
| Ordenação e registros | Chave de prontuário, identidade e atributos dos pacientes, modelo independente e duplicatas |
| Entradas inválidas | Booleanos, zero, negativos, strings, outros tipos e ausência de prontuário |
| Inserção | Rotações LL, RR, LR e RL, mudanças de raiz e alturas |
| Remoção | Folhas, nós com um ou dois filhos, raiz, último paciente e chave inexistente |
| Sucessores | Sucessor direto, sucessor profundo com filho direito e preservação dos pacientes |
| Rebalanceamento da remoção | Quatro casos de rotação, filho de fator zero e correções em dois níveis |
| Instrumentação | Rotações separadas, visitas, reinício, cópia das estatísticas e instâncias independentes |
| Integridade | Alturas e quantidades incorretas, chave alterada, violação de ancestral, ciclos e nós compartilhados |
| Exibição | Modo silencioso, modo detalhado, identificação das rotações e estrutura textual |

As sequências crescentes, decrescentes e aleatórias usam 200 prontuários,
com verificação das invariantes após cada inserção e remoção. A ordem aleatória
usa a semente `20261021`. Ao final, os testes também reinserem um paciente na
estrutura esvaziada.

As operações mistas executam 1.200 inserções, buscas ou remoções para cada uma
das sementes `42`, `20261021` e `314159`, totalizando 3.600 operações. Um
dicionário independente fornece os resultados esperados, incluindo a identidade
dos registros que devem permanecer cadastrados.

O cenário de maior tamanho insere 10.000 prontuários em ordem crescente e
remove todos em ordem aleatória, com semente `20261021`. As invariantes são
conferidas a cada 1.000 alterações para evitar custo quadrático de verificação.
Um teste adicional monta uma estrutura corrompida de profundidade 2.000 para
conferir que o validador retorna `False` sem depender da recursão.

Os testes de [`tests/test_integracao_real.py`](../tests/test_integracao_real.py)
complementam a suíte usando o modelo real e as duas árvores nos cadastros e
experimentos. Eles verificam registros equivalentes, métricas, exportação e
visitas de busca por uma contagem independente dos caminhos.

Os comandos de verificação, executados na raiz do repositório, são:

```bash
python -m unittest tests.test_avl -v
python -m unittest tests.test_integracao_real -v
python -m unittest discover -s tests -v
```

Em ambientes onde o executável é `python3`, substitua `python` por `python3`.
Na versão utilizada para esta seção, a execução completa concluiu 123 testes
sem falhas, incluindo os 32 testes específicos da AVL.
Os testes combinam casos dirigidos, sequências reproduzíveis e comparação com
um estado de referência. Sua aprovação fornece evidência para os cenários
exercitados, sem constituir prova de ausência de defeitos para todas as
sequências possíveis. A metodologia e os resultados comparativos estão na
[seção de metodologia e resultados](metodologia_resultados.md).
