# Checklist do trabalho — acompanhamento do integrante 1

Revisão em **22/10/2026**. Branch de trabalho: `feature/arvore-avl`.

Base dos requisitos: [enunciado do professor](<../../Especificações do trabalho/Trabalho_Prático_I___AED_II.pdf>)
e [divisão do grupo](https://chatgpt.com/share/6ad8cf2d-9964-83e9-b8f3-de7374e778bd).
O integrante 1 é responsável pela AVL e pelos testes desse módulo. As marcações
concluídas abaixo se referem ao que foi implementado e verificado nesta branch.

O código AVL revisado é o do commit `cb5e5ca`; os testes foram introduzidos em
`9bc495b`. A comparação de organização e interface usa a Rubro-Negra da referência
`origin/criacao-arvore-rubro-negra`, commit `1506624`, após atualizar as referências
remotas. Essa consulta não integra branches nem publica alterações.

| Parte da entrega | Situação verificada | Responsabilidade |
| --- | --- | --- |
| AVL, testes e documentação técnica | Concluídos nesta branch | Integrante 1 |
| Rubro-Negra, testes e documentação técnica | Arquivos disponíveis na branch própria; correção não auditada nesta revisão | Integrante 2 |
| Modelo real, gerador, menu e experimentos | Ausentes nesta branch; integração pendente | Integrante 3 e grupo |
| README geral | Contém apenas o título; ainda insuficiente para a entrega | Integrante 3 e grupo |
| Comparação, resultados, relatório e defesa | Pendentes da etapa conjunta | Grupo |

## Operações obrigatórias da AVL

Fonte: seções 1.1 e 2.1 do enunciado. Implementação: [avl.py](../avl.py).

- [x] Armazenar o registro completo, preservando o objeto do paciente.
- [x] Ordenar exclusivamente pelo número do prontuário.
- [x] Manter chaves menores à esquerda e maiores à direita.
- [x] Inserir pacientes por `inserir(paciente)`.
- [x] Buscar pelo prontuário em `buscar(prontuario)`.
- [x] Remover pelo prontuário em `remover(prontuario)`.
- [x] Retornar o registro de menor chave em `minimo()`.
- [x] Retornar o registro de maior chave em `maximo()`.
- [x] Percorrer em pré-ordem, em ordem e pós-ordem.
- [x] Informar a altura atual da árvore.
- [x] Informar a quantidade de nós.
- [x] Fornecer representação textual compreensível, com raiz e filhos E/D.

## Balanceamento e validação da AVL

Fonte: seção 2.2 do enunciado e atividades 1.1 a 1.4 da divisão do grupo.

- [x] Cada nó mantém paciente, prontuário, filhos esquerdo/direito e altura.
- [x] Atualizar alturas após inserções, remoções e rotações.
- [x] Implementar rotação simples à direita, caso LL.
- [x] Implementar rotação simples à esquerda, caso RR.
- [x] Implementar rotação dupla LR.
- [x] Implementar rotação dupla RL.
- [x] Rebalancear após inserções.
- [x] Rebalancear após remoções, inclusive em mais de um ancestral.
- [x] Tratar a remoção quando o filho do nó desequilibrado tem fator zero.
- [x] Contabilizar separadamente rotações de inserção e de remoção.
- [x] Contar cada rotação dupla como duas rotações simples, conforme o contrato.
- [x] Validar a ordenação binária em relação a todos os ancestrais.
- [x] Recalcular alturas reais e verificar `|FB| <= 1` em todos os nós.
- [x] Conferir alturas armazenadas e quantidade de nós.
- [x] Detectar ciclos, nós compartilhados e referências inválidas de filhos.
- [x] Detectar alteração do prontuário no objeto já cadastrado.

As verificações adicionais de corrupção reforçam a robustez; o professor exige
explicitamente a ordenação binária e o limite do fator de balanceamento. Vazia
com altura 0 e folha com altura 1 são convenções do contrato do grupo.

## Robustez, minimundo e modo detalhado

Fonte: seções 2.4, 3 e 8 do enunciado.

- [x] Rejeitar duplicatas sem sobrescrever o paciente existente.
- [x] Retornar `None` para busca inexistente e `False` para remoção inexistente.
- [x] Rejeitar prontuários inválidos sem encerrar o programa.
- [x] Preservar nome, nascimento e telefone junto ao prontuário nos pacientes fictícios.
- [x] Aceitar objetos com atributo `prontuario`, sem depender de `modelos.py`.
- [x] Implementar as estruturas da AVL sem bibliotecas prontas de árvores.
- [x] Oferecer opção de ativar/desativar o modo detalhado.
- [x] Mostrar a chave inserida ou removida no modo detalhado.
- [x] Mostrar o nó desequilibrado, seu fator e o caso LL/RR/LR/RL.
- [x] Mostrar as rotações e a estrutura final após a correção.
- [x] Manter o modo detalhado desligado por padrão.
- [ ] Integrar e testar com a classe `Paciente` real do integrante 3.
- [ ] Registrar a política de duplicatas também no README geral, como exige o professor.

A convenção adotada aceita apenas inteiros positivos e rejeita booleanos. A
validação de nome, nascimento e telefone cabe ao modelo de pacientes. A AVL não
utiliza cores ou recolorações; essa exigência pertence à Rubro-Negra.

## Resultado e alcance dos testes

- [x] Executar os 32 testes automatizados da AVL: todos aprovados, sem falhas ou erros.
- [x] Conferir as invariantes diretamente nos nós por uma rotina independente de `validar()`.
- [x] Comparar operações mistas com um dicionário de referência.
- [x] Usar sementes explícitas e reproduzíveis.

Comando executado na raiz do repositório:

```bash
python -m unittest discover -s tests -v
```

| Grupo de verificações | Evidência em [test_avl.py](../tests/test_avl.py) | Resultado |
| --- | --- | --- |
| Árvore vazia, registros completos e chave de ordenação | Testes de árvore vazia, preservação de atributos, modelo independente e ordenação por prontuário | Aprovado |
| Duplicatas e entradas inválidas | `test_duplicata_nao_sobrescreve_nem_altera_metricas` e `test_rejeita_chaves_invalidas_sem_excecao` | Aprovado |
| Busca presente/ausente e nós visitados | `test_busca_existente_inexistente_e_contagem_de_visitas` | Aprovado |
| Mínimo, máximo e três caminhamentos | `test_caminhamentos_e_extremos` | Aprovado |
| LL, RR, LR e RL após inserção e remoção | `test_quatro_casos_de_rotacao_na_insercao` e `test_quatro_casos_de_rotacao_na_remocao` | Aprovado |
| Remoção de folha, raiz e nós com um ou dois filhos | Testes específicos, incluindo sucessor profundo com filho direito | Aprovado |
| Casos delicados da remoção | Testes de filho com fator zero e de rebalanceamento em dois níveis | Aprovado |
| Métricas, isolamento de instâncias, reinicialização e modo detalhado | Testes específicos de estatísticas, última busca, saída textual e silêncio | Aprovado |
| Rejeição de estruturas corrompidas | Testes de altura, quantidade, chave alterada, ancestral, ciclos e estrutura profunda | Aprovado |
| Sequências crescentes, decrescentes e aleatórias | 200 inserções e remoção total por cenário; invariantes após cada mudança | Aprovado |
| Operações mistas | 3.600 operações; sementes 42, 20261021 e 314159; comparação com dicionário | Aprovado |
| Volume maior | 10.000 inserções crescentes e remoção total aleatória; invariantes a cada 1.000 operações | Aprovado |

**A estrutura verificada corresponde a uma AVL:** é uma árvore binária de busca,
as alturas são consistentes e a diferença de altura entre os filhos é de no
máximo um em cada nó. As rotações preservam essas propriedades nos cenários
testados. A suíte finita não representa uma prova de todos os casos possíveis.

Os testes automatizados do módulo passaram. Os experimentos comparativos A–D
do professor ainda estão pendentes; testar 10.000 registros na AVL não conclui
a comparação entre as duas estruturas.

## Padronização com a Rubro-Negra

- [x] Usar módulos na raiz: `avl.py` / `rubro_negra.py`.
- [x] Usar `tests/test_avl.py` / `tests/test_rubro_negra.py` com `unittest`.
- [x] Usar `docs/avl.md` / `docs/rubro_negra.md` com estrutura equivalente.
- [x] Padronizar o título do guia como “Árvore … — Pessoa …”.
- [x] Alinhar as seções, a ordem dos assuntos, o exemplo e a tabela do contrato.
- [x] Conferir nomes e assinaturas dos 15 métodos públicos: iguais entre as classes.
- [x] Manter os mesmos tipos de retorno e convenções documentados.
- [x] Usar as mesmas cinco chaves nas estatísticas; recolorações são zero na AVL.
- [x] Usar altura 0 na árvore vazia, 1 na folha e rotação dupla contada como duas.
- [x] Manter `.gitignore` igual ao da branch Rubro-Negra.
- [x] Alinhar o conteúdo de `tests/__init__.py` com o arquivo da Rubro-Negra.
- [x] Usar somente a biblioteca padrão e Python 3.10 ou superior nesta etapa.
- [ ] Validar o comportamento conjunto das duas implementações na integração.
- [ ] Completar o README geral e revisar a organização da aplicação integrada.

| Ordem | Guia AVL | Guia Rubro-Negra |
| --- | --- | --- |
| 1 | Executar os testes | Executar os testes |
| 2 | Exemplo independente do restante do sistema | Exemplo independente do restante do sistema |
| 3 | Contrato de integração | Contrato de integração |
| 4 | Nós, alturas e filhos ausentes | Nós, cores e folhas NIL |
| 5 | Balanceamento | Balanceamento |
| 6 | Política das métricas | Política das métricas |
| 7 | Complexidade e testes | Complexidade e testes |
| 8 | Etapa posterior do grupo | Etapa posterior do grupo |

A quarta seção explica a representação própria de cada árvore. A AVL apresenta
alturas e fatores; a Rubro-Negra apresenta cores e folhas NIL. Os comandos usam
`python` no guia AVL para o ambiente Windows; `python3` é o nome utilizado no
guia Rubro-Negra, com uma nota de equivalência no guia AVL.

A correspondência de interface foi conferida por leitura do código e comparação
das assinaturas. Isso prepara a integração, cuja execução continua pendente.

## Itens do trabalho que dependem do grupo

Fonte: seções 1, 2.3, 4, 5, 6 e 7 do enunciado. Estes itens não estão concluídos
pela entrega individual da AVL.

- [ ] Disponibilizar a aplicação integrada com AVL e Rubro-Negra independentes.
- [ ] Manter a mesma coleção de pacientes nas duas árvores.
- [ ] Integrar o modelo `Paciente` com prontuário, nome, nascimento e telefone.
- [ ] Integrar o gerador de pacientes fictícios com chaves únicas.
- [ ] Validar as propriedades, rotações, recolorações e correções da Rubro-Negra na aplicação integrada.
- [ ] Disponibilizar menu para selecionar AVL ou Rubro-Negra.
- [ ] Disponibilizar cadastro, busca, remoção e listagem em ordem no menu.
- [ ] Disponibilizar altura, quantidade, estatísticas e validação no menu.
- [ ] Disponibilizar modo detalhado e experimentos automáticos na aplicação.
- [ ] Usar as mesmas sequências de chaves para as duas árvores em cada experimento.
- [ ] Registrar tamanhos, sementes/sequências e condições de execução.

### Experimentos comparativos

| Experimento | O que o professor pede | Situação |
| --- | --- | --- |
| A — Inserção crescente | Tamanhos de referência 100, 1.000 e 10.000; altura final, tempo total e eventos de rebalanceamento | Pendente nas duas estruturas em conjunto |
| B — Inserção aleatória | Mesmos tamanhos e medições, mesma sequência nas duas árvores e semente registrada | Pendente nas duas estruturas em conjunto |
| C — Busca | Chaves presentes e ausentes; tempo total e média de nós visitados/comparações | Pendente como experimento comparativo |
| D — Remoção | Subconjuntos sugeridos de 10%, 30% e 50%; alturas antes/depois, tempo, rotações e recolorações da Rubro-Negra | Pendente como experimento comparativo |

Os tamanhos e percentuais são referências/sugestões do enunciado; podem ser
ajustados pelo professor. A coleta comparativa pertence à etapa conjunta.

### Tabela obrigatória de resultados

| Métrica | O que a AVL já disponibiliza | Pendência para a entrega |
| --- | --- | --- |
| Altura final | `altura()` | Medir os cenários das duas árvores |
| Rotações na inserção | `rotacoes_insercao` | Coletar e comparar |
| Rotações na remoção | `rotacoes_remocao` | Coletar e comparar |
| Recolorações | Zero na AVL, por não usar cores | Coletar as mudanças efetivas na Rubro-Negra |
| Média de nós visitados na busca | `nos_visitados_ultima_busca` | Coletar após cada busca e calcular a média |
| Tempo total de inserção | Operação disponível para medição externa | Medir no módulo de experimentos |
| Tempo total de busca | Operação disponível para medição externa | Medir no módulo de experimentos |
| Tempo total de remoção | Operação disponível para medição externa | Medir no módulo de experimentos |

### Análise escrita exigida

- [ ] Identificar qual árvore teve menor altura nos cenários medidos.
- [ ] Comparar rotações de inserção e de remoção.
- [ ] Explicar como as recolorações aparecem nos experimentos da Rubro-Negra.
- [ ] Verificar se menor altura sempre significou menor tempo.
- [ ] Analisar o efeito da ordem de inserção.
- [ ] Identificar em quais operações as diferenças foram mais evidentes.
- [ ] Discutir as limitações metodológicas da comparação.

### Entregáveis e defesa

- [ ] Código-fonte completo e executável da aplicação integrada.
- [ ] README com execução, dependências, minimundo e política de duplicatas.
- [ ] Conjunto de dados ou script gerador dos dados dos experimentos.
- [ ] Arquivo de resultados brutos, como CSV ou TXT.
- [ ] Relatório PDF com solução, resultados, tabelas/gráficos e análise comparativa.
- [ ] Incorporar a seção da AVL ao relatório final; o guia técnico já está disponível.
- [ ] Revisar o sistema final e praticar operações e explicações das duas árvores.
- [ ] Preparar interpretação de resultados e pequenas alterações de código/testes para a defesa.
- [ ] Enviar o link do repositório no Google Classroom, na etapa de entrega do grupo.

## Commits e manutenção na branch

- [x] Manter o trabalho do integrante 1 na branch `feature/arvore-avl`.
- [x] Usar nos novos commits do integrante 1 o formato `:emoji: prefixo: frase única`.
- [x] Consultar a branch Rubro-Negra sem integrá-la à branch AVL.
- [x] Manter a `main` sem alterações nesta revisão.

O histórico anterior do repositório contém `first commit`, sem o padrão completo,
e um commit da Rubro-Negra com `:spakles:`, que difere de `:sparkles:`. Os commits
novos da AVL seguem o padrão solicitado. O histórico dos demais autores não foi
reescrito; o padrão deve orientar os próximos commits da equipe.

**Etapas adiadas por orientação expressa do usuário:**

- [ ] Abrir pull request somente após nova ordem.
- [ ] Integrar/mesclar na `main` somente após autorização para essa etapa.

Esta revisão registra alterações apenas na branch local. Não publica branch,
abre pull request nem realiza merge.
