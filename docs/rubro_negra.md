# Árvore Rubro-Negra — Pessoa 2

Implementação individual do cadastro de pacientes, ordenado exclusivamente pelo
número do prontuário. Os arquivos desta entrega são `rubro_negra.py`,
`tests/test_rubro_negra.py` e esta documentação. A pasta `tests/` contém um
`__init__.py` para permitir a descoberta dos testes pela biblioteca padrão.

## Executar os testes

Requer Python 3.10 ou superior. Não há dependências externas nem necessidade de
criar `requirements.txt` nesta etapa. Na raiz do repositório, execute:

```bash
python -m unittest discover -s tests -v
```

Para executar apenas um caso, por exemplo as rotações de inserção:

```bash
python -m unittest tests.test_rubro_negra.TestArvoreRubroNegra.test_quatro_casos_de_rotacao_na_insercao -v
```

Em ambientes onde o comando é `python3`, substitua `python` por `python3`.

## Exemplo independente do restante do sistema

Abra `python` na raiz do projeto e execute:

```python
from dataclasses import dataclass
from rubro_negra import ArvoreRubroNegra


@dataclass(frozen=True)
class PacienteExemplo:
    prontuario: int
    nome: str
    data_nascimento: str
    telefone: str


arvore = ArvoreRubroNegra(modo_detalhado=True)
for prontuario in (30, 10, 20):
    paciente = PacienteExemplo(
        prontuario, f"Paciente fictício {prontuario}", "2000-01-01", "92999990000"
    )
    assert arvore.inserir(paciente)

print(arvore.exibir())
print(arvore.buscar(20))
print(arvore.estatisticas())
assert arvore.validar()
assert arvore.remover(10)
assert arvore.validar()
arvore.definir_modo_detalhado(False)
```

A sequência `30, 10, 20` exige duas rotações simples: primeiro à esquerda no
prontuário 10, depois à direita no 30. A raiz resultante é 20, preta, com os filhos
10 e 30 vermelhos. As folhas ausentes aparecem como `NIL (preto)` na exibição.

`PacienteExemplo` serve apenas para a demonstração. Na integração, basta passar
os objetos da classe `Paciente` fornecida pela Pessoa 3. A árvore aceita qualquer
objeto com atributo `prontuario` válido e preserva o objeto original, incluindo
nome, data de nascimento e telefone. A validação desses outros campos pertence
ao modelo de pacientes.

## Contrato de integração

As duas árvores são implementadas separadamente e compartilham nomes de métodos,
tipos de retorno, convenções de altura e chaves das estatísticas.

| Método ou atributo | Resultado / comportamento |
| --- | --- |
| `inserir(paciente)` | `True` se inseriu; `False` se o prontuário é inválido ou duplicado |
| `buscar(prontuario)` | O paciente original ou `None` |
| `remover(prontuario)` | `True` se removeu; `False` se a chave é inválida ou inexistente |
| `minimo()` / `maximo()` | Paciente de menor / maior prontuário, ou `None` na árvore vazia |
| `pre_ordem()` | Nova lista de pacientes: raiz, esquerda, direita |
| `em_ordem()` | Nova lista de pacientes: esquerda, raiz, direita |
| `pos_ordem()` | Nova lista de pacientes: esquerda, direita, raiz |
| `altura()` | Níveis de nós reais: vazia 0 e folha 1 |
| `quantidade()` | Quantidade de pacientes armazenados |
| `exibir()` | Texto com prontuários, cores e lados E/D; use `print(arvore.exibir())` |
| `validar()` | `True` se todas as propriedades e referências são válidas; senão, `False` |
| `estatisticas()` | Cópia do dicionário de contadores descrito abaixo |
| `nos_visitados_ultima_busca` | Quantidade de nós reais visitados pelo último `buscar()` |
| `definir_modo_detalhado(ativo)` | Liga/desliga as mensagens de balanceamento |
| `reiniciar_estatisticas()` | Zera contadores e última busca; preserva os pacientes e o modo detalhado |

O prontuário deve ser um inteiro positivo; booleanos, zero, negativos, strings e
outros tipos são recusados. Não há conversão automática de strings em inteiros.
Pacientes sem o atributo `prontuario` também são recusados. A validação de nome,
data de nascimento e telefone cabe ao modelo do integrante 3.

Uma duplicata retorna `False` e preserva o paciente já cadastrado, sem atualizar
seus dados, a quantidade ou os contadores de rotação. Essa política deverá constar
também no README final do grupo.

A árvore preserva os objetos recebidos, inclusive todos os dados associados.
O prontuário de um paciente cadastrado deve permanecer imutável. Para trocar a
chave, remova o cadastro usando a chave antiga e insira o registro atualizado.
A rotina `validar()` detecta divergências entre a chave guardada e a do paciente.
Os nós internos e seus vínculos não devem ser alterados pelo menu ou experimentos.

## Nós, cores e folhas NIL

Cada nó real guarda o paciente, uma cópia de seu prontuário, a cor e as referências
`esquerda`, `direita` e `pai`. As cores são as constantes `PRETO` e `VERMELHO`.
Existe um sentinela preto `_nil` por árvore. Ele representa a árvore vazia e todos
os filhos ausentes. A raiz real tem `_nil` como pai.

O sentinela nunca muda de cor. Durante a remoção, seu pai pode apontar
temporariamente para a região em correção; depois, volta a apontar para o próprio
sentinela. Cada instância tem seus próprios nós, sentinela e estatísticas.

Os detalhes internos, incluindo `raiz` e `_nil`, são inspecionados nos testes,
mas o menu e os experimentos devem usar os métodos públicos.

## Balanceamento

A inserção começa como uma busca binária e cria um nó vermelho. Se pai e filho
ficarem vermelhos, o algoritmo examina o tio:

1. Tio vermelho: torna pai e tio pretos, avô vermelho e continua a correção no avô.
2. Tio preto com configuração em triângulo: rotaciona o pai para formar uma linha.
3. Tio preto com configuração em linha: recolore pai/avô e rotaciona o avô.

Os casos têm versões espelhadas. Ao terminar, a raiz é tornada preta.

Na remoção, um nó com até um filho real é substituído diretamente pelo filho.
Quando existem dois filhos, o sucessor em ordem ocupa sua posição. O nó do
sucessor inteiro é movido, preservando todos os dados do paciente. A cor original
do sucessor determina se será necessária uma correção de altura negra.

Se a exclusão retirar um preto de um caminho, o algoritmo trata esse déficit como
um "preto extra" conceitual. Não existe uma terceira cor armazenada. Os quatro
casos, também espelhados, são:

1. Irmão vermelho: recolore e rotaciona o pai para obter um irmão preto.
2. Irmão preto com filhos pretos: recolore o irmão e leva o déficit para o pai.
3. Irmão preto com sobrinho próximo vermelho e distante preto: rotaciona o irmão
   para preparar o caso seguinte.
4. Irmão preto com sobrinho distante vermelho: recolore e rotaciona o pai,
   eliminando o déficit.

`validar()` verifica a raiz preta, cores válidas, ausência de vermelhos
consecutivos, alturas negras iguais até NIL e ordenação binária estrita. Também
confere referências aos pais, ausência de ciclos/nós compartilhados, quantidade
armazenada e correspondência entre prontuário do nó e do paciente. A verificação
é iterativa para conseguir rejeitar estruturas corrompidas profundas.

## Política das métricas

`estatisticas()` retorna estas cinco chaves inteiras:

```python
{
    "rotacoes_insercao": 0,
    "rotacoes_remocao": 0,
    "recoloracoes_insercao": 0,
    "recoloracoes_remocao": 0,
    "nos_visitados_ultima_busca": 0,
}
```

Cada rotação simples conta uma vez. Portanto, uma rotação dupla conta duas.
As recolorações contam cada mudança efetiva de uma cor para outra: atribuir
a mesma cor novamente não conta. Criar o nó vermelho não conta; torná-lo preto
como raiz conta. Na remoção, a mudança de cor do sucessor ao herdar a posição
do removido também conta. NIL nunca entra nos contadores. O total de
recolorações é a soma das duas chaves de recolorações.

A última busca conta o nó encontrado, quando houver, mas nunca conta NIL. Uma
busca na árvore vazia ou com chave inválida registra zero. Inserções, remoções e
outras consultas não modificam a métrica da última busca. Para calcular a média,
os experimentos devem coletá-la imediatamente após cada chamada a `buscar()`.

O modo detalhado começa desativado. Quando ligado, imprime a chave da operação,
o caso de correção, a região envolvida, as rotações, as mudanças de cor e a
estrutura final. Deixe-o desativado durante medições de tempo. O método
`exibir()` sempre retorna texto, sem imprimir por conta própria.

## Complexidade e testes

Busca, inserção, remoção, mínimo e máximo têm custo O(log n) em uma árvore válida.
A quantidade tem custo O(1). Caminhamentos, cálculo da altura e validação visitam
O(n) nós. A exibição visita os nós e produz um texto cujo tamanho também depende
da indentação.

Os testes usam pacientes fictícios locais, verificam as invariantes diretamente
nos nós e também chamam `validar()`. Cobrem árvores vazias, duplicatas, entradas
inválidas, percursos, buscas, métricas, isolamento de instâncias, modo detalhado,
casos espelhados de inserção/remoção, mudanças de raiz e sucessores profundos.
Há sequências crescentes, decrescentes e aleatórias; operações mistas comparadas
com um dicionário de referência; e 10.000 inserções seguidas de remoções, com
validação amostrada para evitar custo quadrático. As sementes ficam explícitas
no código dos testes.

## Etapa posterior do grupo

Esta entrega está preparada para receber o modelo `Paciente`. A integração com a
AVL, o menu, os experimentos comparativos, o CSV e o relatório final depende dos
outros módulos e permanece na etapa conjunta prevista no planejamento.

Referências para estudo: [aula do MIT sobre Rubro-Negras e rotações](https://ocw.mit.edu/courses/6-046j-introduction-to-algorithms-sma-5503-fall-2005/resources/lecture-10-red-black-trees-rotations-insertions-deletions/)
e [notas de Dartmouth sobre balanceamento, inserção e remoção](https://cs.dartmouth.edu/cs10/notes10.html).
