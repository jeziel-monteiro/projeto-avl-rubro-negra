# Árvore AVL — Pessoa 1

Implementação individual do cadastro de pacientes, ordenado exclusivamente pelo
número do prontuário. Os arquivos desta entrega são `avl.py`, `tests/test_avl.py`
e esta documentação. A pasta `tests/` contém um `__init__.py` para permitir a
descoberta dos testes pela biblioteca padrão.

## Executar os testes

Requer Python 3.10 ou superior. Não há dependências externas nem necessidade de
criar `requirements.txt` nesta etapa. Na raiz do repositório, execute:

```bash
python -m unittest discover -s tests -v
```

Para executar apenas um caso, por exemplo as rotações de inserção:

```bash
python -m unittest tests.test_avl.TestArvoreAVL.test_quatro_casos_de_rotacao_na_insercao -v
```

Em ambientes onde o comando é `python3`, substitua `python` por `python3`, como
nos exemplos da documentação Rubro-Negra.

## Exemplo independente do restante do sistema

Abra `python` na raiz do projeto e execute:

```python
from dataclasses import dataclass
from avl import ArvoreAVL


@dataclass(frozen=True)
class PacienteExemplo:
    prontuario: int
    nome: str
    data_nascimento: str
    telefone: str


arvore = ArvoreAVL(modo_detalhado=True)
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

A sequência `30, 10, 20` provoca o caso LR: rotação à esquerda no 10, seguida de
rotação à direita no 30. A árvore resultante é:

```text
Raiz: 20 (h=2, FB=0)
|-- E: 10 (h=1, FB=0)
|   |-- E: vazio
|   `-- D: vazio
`-- D: 30 (h=1, FB=0)
    |-- E: vazio
    `-- D: vazio
```

`PacienteExemplo` é apenas um registro fictício de demonstração. Na integração,
passe diretamente os objetos `Paciente` do integrante 3. O módulo não importa
`modelos.py` nem `rubro_negra.py`.

## Contrato de integração

Os nomes, retornos, convenções e chaves das estatísticas correspondem à interface
da Rubro-Negra disponível na branch `origin/criacao-arvore-rubro-negra` no momento
da implementação. As estruturas são implementadas separadamente.

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
| `exibir()` | Texto com prontuários, alturas, fatores e lados E/D; use `print(arvore.exibir())` |
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

## Nós, alturas e filhos ausentes

Cada nó real guarda o paciente, uma cópia de seu prontuário, a altura da subárvore
e as referências `esquerda` e `direita`. Os filhos ausentes e a árvore vazia são
representados por `None`. Uma folha começa com altura 1; um filho ausente tem
altura 0. Cada instância tem seus próprios nós e estatísticas.

O fator de balanceamento é definido por
`FB = altura(esquerda) - altura(direita)`. Os detalhes internos, incluindo `raiz`,
são inspecionados nos testes, mas o menu e os experimentos devem usar os métodos
públicos.

## Balanceamento

Após modificar um ramo, a implementação atualiza a altura e corrige fatores fora
do intervalo de -1 a +1.

| Caso | Inserção de exemplo | Correção |
| --- | --- | --- |
| LL | 30, 20, 10 | Rotação à direita |
| RR | 10, 20, 30 | Rotação à esquerda |
| LR | 30, 10, 20 | Esquerda no filho; direita no nó desequilibrado |
| RL | 10, 30, 20 | Direita no filho; esquerda no nó desequilibrado |

As rotações preservam a ordem das chaves. A altura do nó rebaixado é atualizada
antes da altura do promovido, pois a segunda depende da primeira.

Na remoção, um nó sem filhos desaparece; um nó com um filho é substituído por
esse filho. Com dois filhos, o registro completo do sucessor em ordem (menor
chave da subárvore direita) substitui o registro removido, e a ocorrência antiga
do sucessor é excluída. A quantidade diminui somente uma vez.

A redução de altura pode exigir correções em vários ancestrais até a raiz. Se o
filho do nó desequilibrado tiver fator zero, a correção usa uma rotação simples.
Por exemplo, inserir `30, 20, 40, 10, 25` e remover `40` exige uma rotação à direita
no 30, promovendo o 20.

`validar()` recalcula alturas reais e confere:

- Ordenação binária estrita em relação a todos os ancestrais.
- Fator de balanceamento entre -1 e +1 em todos os nós.
- Alturas armazenadas iguais às alturas reais.
- Prontuários válidos e correspondência entre nó e paciente.
- Quantidade registrada igual ao número de nós alcançados.
- Ausência de ciclos, nós compartilhados e referências de filhos inválidas.

A validação usa uma pilha explícita, permitindo rejeitar inclusive uma estrutura
corrompida profunda sem depender do limite de recursão. Não altera pacientes,
vínculos, alturas ou métricas. As operações normais pressupõem uma árvore válida.

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

Cada rotação simples soma uma unidade no contador da operação correspondente.
Uma rotação dupla soma duas unidades. Os contadores são acumulados até chamar
`reiniciar_estatisticas()`. Recolorações permanecem em zero na AVL; essas chaves
facilitam a coleta das mesmas métricas nas duas estruturas.

A última busca conta cada nó real inspecionado, incluindo o encontrado. Uma busca
inválida ou em árvore vazia registra zero. Inserções, remoções e outras consultas
não mudam esse valor. Os experimentos devem coletá-lo imediatamente após cada
`buscar()` para calcular a média entre buscas presentes e ausentes.

O modo detalhado mostra a chave inserida/removida, o nó desequilibrado, seu fator,
o caso LL/RR/LR/RL, as rotações e a estrutura final. Começa desligado e deve ficar
desligado nas medições de tempo. `exibir()` apenas retorna texto; use `print()` no
menu para mostrá-lo.

## Complexidade e testes

Em uma árvore válida, inserção, busca, remoção, mínimo e máximo têm custo
O(log n). Altura e quantidade têm custo O(1). Caminhamentos e validação têm custo
O(n). A exibição percorre todos os nós e produz texto cujo tamanho depende também
da indentação. O modo detalhado acrescenta o custo de produzir e imprimir esse
texto às operações.

A suíte possui 32 testes, incluindo um oráculo independente que recalcula as
invariantes diretamente a partir dos nós. Cobre os quatro casos de rotação em
inserção e remoção, correções com filho de fator zero e remoção com desequilíbrios
em dois níveis. Também verifica todos os caminhamentos, identidade dos pacientes,
duplicatas, entradas inválidas, sucessores profundos, validação de corrupção,
contadores, exibição e modo detalhado.

Há sequências crescentes, decrescentes e aleatórias; 3.600 operações mistas
comparadas com um dicionário de referência; e 10.000 inserções seguidas de remoção
total em ordem aleatória. Os testes pequenos verificam invariantes a cada mudança;
o cenário de 10.000 registros faz verificações a cada 1.000 operações para evitar
custo quadrático. As sementes aleatórias são explícitas no código.

## Etapa posterior do grupo

Esta entrega está preparada para receber o modelo `Paciente`. A integração com a
Rubro-Negra, o menu, os experimentos comparativos, o CSV e o relatório final depende
dos outros módulos e permanece na etapa conjunta prevista no planejamento.
