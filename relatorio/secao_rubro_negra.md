# Árvore Rubro-Negra

A Árvore Rubro-Negra armazena os pacientes do sistema de Clínica / Atendimento
usando o número do prontuário como chave única. A implementação está em
[`rubro_negra.py`](../rubro_negra.py) e mantém os registros ordenados por essa
chave. Nome, data de nascimento e telefone acompanham o paciente, mas não
participam das comparações que determinam sua posição na árvore.

## Representação dos registros e dos nós

A classe `ArvoreRubroNegra` aceita objetos com o atributo `prontuario` inteiro
positivo. Na aplicação integrada, esses objetos são instâncias de `Paciente`,
definida em [`modelos.py`](../modelos.py). O modelo é imutável, o que impede
alterações na chave depois do cadastro. A árvore preserva o objeto recebido;
buscas e caminhamentos devolvem os pacientes, sem expor os nós como resultado.

A classe interna `_No` contém:

| Atributo | Função |
| --- | --- |
| `paciente` | Referência ao registro completo |
| `prontuario` | Cópia da chave usada na ordenação |
| `cor` | Uma das constantes `PRETO` ou `VERMELHO` |
| `esquerda` e `direita` | Referências aos filhos |
| `pai` | Referência usada nas rotações e correções |

Prontuários menores ficam na subárvore esquerda, e maiores, na direita. Uma
tentativa de inserir uma chave já existente retorna `False` e preserva o
registro original. Chaves booleanas, textos, valores fracionários, zero e
inteiros negativos são recusados. A árvore também recusa objetos sem prontuário.
A validação dos demais campos pertence ao modelo de pacientes.

Cada instância cria um sentinela preto `_nil`, compartilhado por todos os filhos
ausentes daquela árvore. O sentinela não contém paciente e representa também a
raiz da árvore vazia. Seus filhos apontam para ele próprio, e o pai da raiz real
é `_nil`. Árvores diferentes possuem sentinelas e contadores independentes.

Durante a remoção, o pai de `_nil` pode apontar temporariamente para o nó acima
da região em correção. Isso permite tratar a exclusão de uma folha preta usando
o mesmo algoritmo empregado para um substituto real. Ao terminar, o pai do
sentinela volta a apontar para ele próprio. Sua cor permanece preta.

## Propriedades de balanceamento

A estrutura deve satisfazer simultaneamente as seguintes propriedades:

1. Todo nó possui cor preta ou vermelha.
2. A raiz é preta, quando existe um nó real.
3. Todas as folhas ausentes, representadas por `NIL`, são pretas.
4. Um nó vermelho não possui filho vermelho.
5. Todos os caminhos de um mesmo nó até suas folhas `NIL` contêm a mesma
   quantidade de nós pretos.
6. A ordenação de árvore binária de busca é estrita, sem chaves duplicadas.

Nesta seção, a contagem de nós pretos de um caminho inclui o nó inicial, quando
preto, e o `NIL` final. Essa é a contagem comparada pelo método `validar()` nos
caminhos completos da raiz até as folhas ausentes. Ela é diferente da altura
retornada por `altura()`, que conta apenas os níveis de nós reais: uma árvore
vazia tem altura 0, e uma árvore com um paciente tem altura 1.

A igualdade das contagens de pretos, junto da proibição de vermelhos
consecutivos, limita a altura a `h <= 2 * log2(n + 1)`, para `n` pacientes.
Assim, os caminhos de busca têm comprimento logarítmico mesmo quando os
prontuários são inseridos em ordem crescente. A relação entre essas propriedades
e o limite da altura é apresentada nas
[notas de Dartmouth sobre Árvores Rubro-Negras](https://cs.dartmouth.edu/cs10/notes10.html).

## Inserção e suas correções

O método `inserir()` primeiro percorre a árvore por comparação de prontuários.
Se encontra a chave, encerra a operação sem alterar o cadastro. Caso contrário,
conecta um novo nó vermelho na posição encontrada, com os dois filhos iguais a
`_nil`.

Adicionar um nó vermelho preserva a quantidade de pretos nos caminhos. O
possível conflito é a existência de um pai também vermelho. O método
`_corrigir_insercao()` examina o pai, o avô e o tio do novo nó para resolver esse
conflito. Para o pai situado à esquerda do avô, os casos são:

| Caso | Condição | Correção |
| --- | --- | --- |
| 1 | Pai e tio vermelhos | Pai e tio tornam-se pretos; o avô torna-se vermelho; a análise continua no avô |
| 2 | Tio preto e novo nó à direita do pai | Rotação à esquerda no pai, convertendo o triângulo LR em linha |
| 3 | Tio preto e configuração em linha LL | Pai torna-se preto, avô vermelho e ocorre rotação à direita no avô |

Quando o pai está à direita do avô, os casos são espelhados: a configuração RL
é convertida por uma rotação à direita no pai, e a configuração RR é corrigida
por uma rotação à esquerda no avô. A recoloração do tio vermelho pode levar o
conflito até um nível superior. Ao encerrar a correção, a raiz é tornada preta.

As rotações alteram as referências entre os nós, incluindo os pais, sem mudar a
ordem relativa dos prontuários. Uma rotação à esquerda promove o filho direito;
uma rotação à direita promove o filho esquerdo. Os pacientes permanecem
associados aos seus respectivos nós.

## Busca, extremos e caminhamentos

`buscar(prontuario)` compara a chave com a do nó atual e segue para a esquerda
ou para a direita até encontrar o paciente ou alcançar `NIL`. Retorna o objeto
armazenado, quando encontrado, e `None` em uma busca malsucedida. A busca não
realiza rotações ou recolorações.

`minimo()` segue pelos filhos esquerdos até o menor prontuário. `maximo()` usa os
filhos direitos para encontrar o maior. Ambos retornam `None` na árvore vazia.

Os três caminhamentos retornam novas listas de pacientes. A pré-ordem visita
raiz, esquerda e direita; a ordem simétrica visita esquerda, raiz e direita; a
pós-ordem visita esquerda, direita e raiz. O resultado de `em_ordem()` possui
prontuários em ordem crescente.

## Remoção e correção da altura negra

`remover(prontuario)` localiza o registro antes de modificar a estrutura. Uma
chave inválida ou inexistente resulta em `False`. Para um registro encontrado,
a remoção distingue três situações:

1. Sem filho esquerdo real: o filho direito ocupa a posição do nó.
2. Sem filho direito real: o filho esquerdo ocupa a posição do nó.
3. Com dois filhos reais: o sucessor em ordem, encontrado como o mínimo da
   subárvore direita, ocupa a posição do nó removido.

O transplante atualiza o vínculo com o pai e, quando necessário, a raiz. No
terceiro caso, o algoritmo move o nó sucessor inteiro, preservando seu paciente.
Se o sucessor não é filho direto do alvo, seu filho direito assume primeiro a
posição que ele ocupava. Depois, o sucessor recebe os filhos e a cor do alvo.

A necessidade de correção depende da cor original do nó retirado de sua posição.
Na remoção com dois filhos, essa é a cor original do sucessor, antes de ele
herdar a cor do alvo. Portanto, remover um alvo preto nem sempre exige executar
o laço de correção, como mostra o exemplo de transplante apresentado adiante.

Quando a exclusão elimina um preto de um caminho, o algoritmo representa esse
déficit como um "preto extra" associado conceitualmente ao substituto. Nenhuma
terceira cor é armazenada. Se o substituto é vermelho, torná-lo preto resolve o
déficit. Se ele é preto e ainda não é a raiz, `_corrigir_remocao()` aplica os
casos abaixo.

Para o substituto situado à esquerda do pai, o irmão é o filho direito do pai.
O sobrinho próximo é o filho esquerdo do irmão; o distante é seu filho direito.

| Caso | Condição | Tratamento |
| --- | --- | --- |
| 1 | Irmão vermelho | Torna o irmão preto e o pai vermelho; rotaciona o pai à esquerda e obtém um irmão preto |
| 2 | Irmão preto com os dois filhos pretos | Torna o irmão vermelho e leva o déficit para o pai |
| 3 | Irmão preto, sobrinho próximo vermelho e distante preto | Torna o próximo preto e o irmão vermelho; rotaciona o irmão à direita, preparando o caso 4 |
| 4 | Irmão preto com sobrinho distante vermelho | Irmão recebe a cor do pai; pai e sobrinho distante tornam-se pretos; uma rotação à esquerda no pai elimina o déficit |

O caso 1 prepara os casos com irmão preto; o caso 2 pode propagar o déficit por
vários níveis. O caso 3 transforma a configuração para permitir o caso 4, que
encerra a correção. Quando o substituto está à direita, esquerda e direita são
trocadas: o irmão fica à esquerda, o sobrinho próximo é seu filho direito, e o
distante, seu filho esquerdo. As rotações dos casos 1 e 4 passam a ser à direita,
e a do caso 3, à esquerda.

Ao terminar, o substituto é tornado preto, se necessário. A quantidade de
pacientes é reduzida uma única vez, e o pai do sentinela é restaurado.

## Validação da estrutura

O método `validar()` usa uma pilha explícita para percorrer os nós. Em cada
caminho, transporta os limites inferior e superior permitidos para a chave,
a referência esperada do pai e a quantidade de pretos acumulada. Ao chegar a
`NIL`, compara a contagem com a dos demais caminhos.

Além das propriedades Rubro-Negras, a validação confere:

- A cor e as referências do sentinela, bem como a ausência de paciente nele.
- A referência ao pai da raiz e aos pais dos demais nós.
- A ausência de ciclos e de nós reais compartilhados entre ramos.
- A validade dos prontuários e a correspondência entre a chave do nó e a do paciente.
- A quantidade de nós visitados em relação ao contador armazenado.

Os limites de ordenação são herdados dos ancestrais, permitindo detectar
violações que uma comparação apenas entre pai e filho não encontraria. O
conjunto de identificadores visitados detecta ciclos e referências repetidas.
A pilha evita depender da recursão ao examinar uma estrutura corrompida e
profunda. A validação retorna um booleano e não modifica os pacientes, a forma
da árvore ou as estatísticas.

## Estatísticas e modo detalhado

`estatisticas()` retorna uma cópia de um dicionário com cinco campos:

| Campo | Medida |
| --- | --- |
| `rotacoes_insercao` | Rotações simples acumuladas nas inserções |
| `rotacoes_remocao` | Rotações simples acumuladas nas remoções |
| `recoloracoes_insercao` | Mudanças efetivas de cor nas inserções |
| `recoloracoes_remocao` | Mudanças efetivas de cor nas remoções |
| `nos_visitados_ultima_busca` | Nós reais visitados pela última busca |

Uma rotação dupla corresponde a duas rotações simples. As recolorações contam
cada mudança de uma cor para outra, mesmo que um nó volte depois à sua cor
original. A criação de um nó vermelho não conta como recoloração; sua promoção
a raiz preta conta quando a cor muda. Na remoção, a herança de cor do sucessor
também conta quando produz mudança. Atribuir novamente a cor já existente não
incrementa o contador, e `NIL` nunca é recolorido.

O contador de busca inclui o nó encontrado e exclui `NIL`. Quando a chave não
existe, conta os nós reais percorridos até a folha ausente. Uma chave inválida
ou uma busca em árvore vazia registra zero. Somente `buscar()` atualiza essa
medida; inserções, remoções e outras consultas a preservam.

`reiniciar_estatisticas()` zera os cinco campos sem apagar pacientes ou alterar
o modo detalhado. Esse reinício permite isolar uma operação da preparação da
árvore. O total de recolorações é a soma dos contadores de inserção e remoção.

Com o modo detalhado ativo, as atualizações mostram a chave, os casos de
correção, as regiões afetadas, as rotações, as recolorações e a estrutura final.
`exibir()` retorna essa estrutura como texto; a impressão acontece por uma
chamada explícita ou pelo modo detalhado. Nas medições de desempenho, esse
modo permanece desativado para excluir a impressão dos tempos das operações.

## Exemplos executados

Os quatro exemplos utilizam registros fictícios do modelo real `Paciente`.
Os blocos Python podem ser executados em sequência no interpretador, iniciado
na raiz do repositório. A preparação comum é:

```python
from modelos import Paciente
from rubro_negra import ArvoreRubroNegra


def paciente(chave):
    return Paciente(chave, f"Paciente fictício {chave}", "2000-01-01", "00900000000")


def preparar(chaves):
    arvore = ArvoreRubroNegra()
    for chave in chaves:
        assert arvore.inserir(paciente(chave))
        assert arvore.validar()
    return arvore
```

Em cada exemplo, os contadores são reiniciados após a preparação e antes da
operação destacada. Assim, os números apresentados medem somente essa operação.
As estruturas abaixo são saídas de `exibir()`, que identifica os lados por
`E` e `D` e mostra as folhas `NIL` pretas.

### Inserção com rotação dupla

A árvore é preparada com `30, 10`, e a operação destacada insere `20`:

```python
arvore = preparar((30, 10))
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.inserir(paciente(20))
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [10, 20, 30]
assert arvore.estatisticas()["rotacoes_insercao"] == 2
assert arvore.estatisticas()["recoloracoes_insercao"] == 2
print(arvore.exibir())
```

Antes da inserção:

```text
Raiz: 30 (preto)
|-- E: 10 (vermelho)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: NIL (preto)
```

Depois da correção:

```text
Raiz: 20 (preto)
|-- E: 10 (vermelho)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 30 (vermelho)
    |-- E: NIL (preto)
    `-- D: NIL (preto)
```

O novo nó 20 fica à direita de seu pai vermelho 10, formando o triângulo LR.
Uma rotação à esquerda em 10 produz a configuração em linha. Depois, 20 muda
de vermelho para preto, 30 muda de preto para vermelho e uma rotação à direita
em 30 promove 20 à raiz. A altura permanece 2. A operação realiza duas rotações
e duas recolorações.

### Inserção com tio vermelho

Após preparar `10, 5, 15`, a inserção de `1` encontra pai 5 e tio 15 vermelhos:

```python
arvore = preparar((10, 5, 15))
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.inserir(paciente(1))
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [1, 5, 10, 15]
assert arvore.estatisticas()["rotacoes_insercao"] == 0
assert arvore.estatisticas()["recoloracoes_insercao"] == 4
print(arvore.exibir())
```

Antes:

```text
Raiz: 10 (preto)
|-- E: 5 (vermelho)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 15 (vermelho)
    |-- E: NIL (preto)
    `-- D: NIL (preto)
```

Depois:

```text
Raiz: 10 (preto)
|-- E: 5 (preto)
|   |-- E: 1 (vermelho)
|   |   |-- E: NIL (preto)
|   |   `-- D: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 15 (preto)
    |-- E: NIL (preto)
    `-- D: NIL (preto)
```

O caso 1 torna 5 e 15 pretos e o avô 10 vermelho. Como 10 é a raiz, ele volta
a preto ao terminar a correção. São quatro mudanças efetivas de cor e nenhuma
rotação. As duas mudanças em 10 contam separadamente. A altura passa de 2 para
3. A quantidade de pretos de cada caminho também aumenta, mas permanece igual
entre todos os caminhos, como exige a propriedade de altura negra.

### Remoção de folha preta com correção

A preparação `10, 5, 15, 12` deixa o prontuário 5 em uma folha preta. Sua
remoção exige os casos 3 e 4:

```python
arvore = preparar((10, 5, 15, 12))
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.remover(5)
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [10, 12, 15]
assert arvore.estatisticas()["rotacoes_remocao"] == 2
assert arvore.estatisticas()["recoloracoes_remocao"] == 3
print(arvore.exibir())
```

Antes:

```text
Raiz: 10 (preto)
|-- E: 5 (preto)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 15 (preto)
    |-- E: 12 (vermelho)
    |   |-- E: NIL (preto)
    |   `-- D: NIL (preto)
    `-- D: NIL (preto)
```

Depois:

```text
Raiz: 12 (preto)
|-- E: 10 (preto)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 15 (preto)
    |-- E: NIL (preto)
    `-- D: NIL (preto)
```

O substituto é `NIL`, e o irmão 15 é preto. O sobrinho próximo 12 é vermelho,
enquanto o distante é `NIL` preto. No caso 3, 12 torna-se preto, 15 vermelho
e uma rotação à direita em 15 prepara o caso 4. O novo irmão é 12, cujo filho
distante 15 está vermelho. Esse filho torna-se preto, e uma rotação à esquerda
em 10 elimina o déficit de pretos. A altura cai de 3 para 2; a correção realiza
duas rotações e três recolorações.

### Remoção com transplante do sucessor

Na preparação `10, 5, 15`, a remoção da raiz 10 utiliza o sucessor 15:

```python
arvore = preparar((10, 5, 15))
sucessor = arvore.buscar(15)
print(arvore.exibir())
arvore.reiniciar_estatisticas()
assert arvore.remover(10)
assert arvore.validar()
assert [p.prontuario for p in arvore.em_ordem()] == [5, 15]
assert arvore.raiz.paciente is sucessor
assert arvore.estatisticas()["rotacoes_remocao"] == 0
assert arvore.estatisticas()["recoloracoes_remocao"] == 1
print(arvore.exibir())
```

Antes:

```text
Raiz: 10 (preto)
|-- E: 5 (vermelho)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: 15 (vermelho)
    |-- E: NIL (preto)
    `-- D: NIL (preto)
```

Depois:

```text
Raiz: 15 (preto)
|-- E: 5 (vermelho)
|   |-- E: NIL (preto)
|   `-- D: NIL (preto)
`-- D: NIL (preto)
```

O sucessor é transplantado e herda a cor preta do alvo, produzindo uma
recoloração. Como sua cor original era vermelha, não é necessário executar o
laço de correção da remoção. O objeto do paciente 15 é preservado, e a altura
permanece 2.

### Síntese dos exemplos

| Preparação | Operação isolada | Altura antes/depois | Rotações | Recolorações |
| --- | --- | --- | ---: | ---: |
| `30, 10` | Inserir `20` | 2 / 2 | 2 | 2 |
| `10, 5, 15` | Inserir `1` | 2 / 3 | 0 | 4 |
| `10, 5, 15, 12` | Remover `5` | 3 / 2 | 2 | 3 |
| `10, 5, 15` | Remover `10` | 2 / 2 | 0 | 1 |

Em todos os estados finais, `validar()` retorna `True`, e o caminhamento em
ordem corresponde exatamente às chaves esperadas. Esses exemplos são
demonstrações de funcionamento; seus contadores isolados não são medições
comparativas de tempo.

## Complexidade das operações

Com o modo detalhado desligado e a estrutura válida, a altura logarítmica limita
o custo da busca, da inserção e da remoção. As rotações alteram um número
constante de referências. As correções percorrem uma cadeia de ancestrais,
sem reconstruir toda a árvore.

| Operação | Custo de tempo |
| --- | --- |
| Inserção, busca e remoção | `O(log n)` |
| Mínimo e máximo | `O(log n)` |
| Pré-ordem, em ordem e pós-ordem | `O(n)` |
| Altura | `O(n)`, calculada percorrendo os nós |
| Quantidade | `O(1)`, mantida em um contador |
| Validação | `O(n)` |
| Leitura ou reinício das estatísticas | `O(1)` |

A validação usa `O(n)` de memória auxiliar para a pilha e o conjunto de nós
visitados. Os caminhamentos produzem listas com `n` pacientes. A exibição visita
os nós e gera texto cujo tamanho depende também da indentação dos níveis.
Quando o modo detalhado imprime essa estrutura após uma atualização, o custo
da operação passa a incluir a geração e a impressão do texto.

## Testes e verificação dos resultados

A suíte de [`tests/test_rubro_negra.py`](../tests/test_rubro_negra.py) contém
26 testes automatizados. A execução da suíte específica foi concluída sem
falhas. Os testes conferem diretamente os nós, além de chamar `validar()`, para
que um defeito no validador não esconda um defeito no balanceamento.

| Grupo de verificações | Situações cobertas |
| --- | --- |
| Operações básicas | Árvore vazia, inserção única, busca, extremos e três caminhamentos |
| Ordenação e registros | Prontuários únicos, rejeição de entradas inválidas e preservação da identidade e dos dados dos pacientes |
| Inserção | Configurações LL, RR, LR, RL e recoloração com tio vermelho |
| Remoção | Folhas vermelhas e pretas, nó com um filho, dois filhos, mudança de raiz e remoção do último paciente |
| Correções da remoção | Irmão vermelho, sobrinhos pretos, sobrinho próximo ou distante vermelho e casos espelhados |
| Transplantes | Sucessor direto, sucessor profundo e sucessor com filho direito |
| Instrumentação | Valores de rotações e recolorações, visitas nas buscas, reinício e cópia das estatísticas |
| Integridade | Pais incorretos, ciclos, filhos ausentes indevidos, cores inválidas, altura negra desigual e quantidade incorreta |
| Estado das instâncias | Sentinelas independentes, modo silencioso e modo detalhado |

As sequências crescentes, decrescentes e aleatórias usam 150 prontuários e
conferem as invariantes após cada alteração. Os testes de operações mistas
executam 1.000 operações para cada uma das sementes `7`, `42` e `20261021`,
comparando os resultados com um dicionário de referência independente.

O cenário de maior tamanho insere e depois remove 10.000 registros. As ordens
de inserção e remoção usam as sementes `1984` e `2026`, respectivamente. A
validação completa ocorre a cada 1.000 alterações, evitando conferir toda a
árvore após cada operação desse conjunto.

Os testes de [`tests/test_integracao_real.py`](../tests/test_integracao_real.py)
complementam essas verificações usando o modelo real de pacientes e as árvores
reais no cadastro integrado e nos experimentos. Eles conferem equivalência dos
registros, retornos, métricas e exportação CSV. A média de visitas das buscas é
comparada com uma contagem independente dos caminhos nos nós.

Os comandos de verificação, executados na raiz do repositório, são:

```bash
python3 -m unittest tests.test_rubro_negra -v
python3 -m unittest tests.test_integracao_real -v
python3 -m unittest discover -s tests -v
```

A aprovação desses cenários fornece evidência para as operações e propriedades
exercitadas. A cobertura combina exemplos dirigidos, sequências reproduzíveis
e comparação com um estado de referência; não constitui uma prova de ausência
de defeitos para todas as sequências possíveis.
