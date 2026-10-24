from __future__ import annotations

from typing import Generic, Protocol, TypeVar, cast


# ============= CORES DOS NÓS =================

PRETO = "preto"
VERMELHO = "vermelho"


# ============= CONTRATO DO PACIENTE =================


class RegistroPaciente(Protocol):
    """Contrato mínimo, compatível com a futura classe Paciente do grupo."""

    @property
    def prontuario(self) -> int:

        """Chave única de ordenação."""
        ...


PacienteT = TypeVar("PacienteT", bound=RegistroPaciente)


# ============= ESTRUTURA DOS NÓS =================


class _No(Generic[PacienteT]):
    """Nó interno; o sentinela é o único nó sem paciente."""

    def __init__(
        self, paciente: PacienteT | None = None, cor: str = PRETO
    ) -> None:
        self.paciente = paciente
        self.prontuario = paciente.prontuario if paciente is not None else 0
        self.cor = cor
        self.esquerda: _No[PacienteT] = self
        self.direita: _No[PacienteT] = self
        self.pai: _No[PacienteT] = self


# ============= ÁRVORE RUBRO-NEGRA =================


class ArvoreRubroNegra(Generic[PacienteT]):
    """
    Cadastro com busca, inserção e remoção em O(log n).

    As consultas retornam os pacientes, não os nós internos. Inserções
    duplicadas ou inválidas retornam False; buscas e remoções inexistentes
    retornam None e False, respectivamente. O modo detalhado imprime no terminal;
    ``exibir()`` apenas devolve a representação textual.
    """

    # ============= INICIALIZAÇÃO =================

    def __init__(self, modo_detalhado: bool = False) -> None:
        self._nil: _No[PacienteT] = _No()
        self.raiz = self._nil
        self._quantidade = 0
        self._modo_detalhado = bool(modo_detalhado)
        self.reiniciar_estatisticas()

    # ============= VALIDAÇÃO DO PRONTUÁRIO =================

    @staticmethod
    def _prontuario_valido(prontuario: object) -> bool:
        # bool é subclasse de int em Python, mas não é um prontuário válido.
        return (
            isinstance(prontuario, int)
            and not isinstance(prontuario, bool)
            and prontuario > 0
        )

    # ============= INSERÇÃO =================

    def inserir(self, paciente: PacienteT) -> bool:
        """Insere o objeto original, sem sobrescrever um prontuário duplicado."""
        prontuario = getattr(paciente, "prontuario", None)
        if not self._prontuario_valido(prontuario):
            return False

        pai = self._nil
        atual = self.raiz
        while atual is not self._nil:
            pai = atual
            if prontuario == atual.prontuario:
                self._registrar(f"Inserção recusada: prontuário {prontuario} duplicado.")
                return False
            atual = atual.esquerda if prontuario < atual.prontuario else atual.direita

        novo = _No(paciente, VERMELHO)
        novo.esquerda = novo.direita = self._nil
        novo.pai = pai
        if pai is self._nil:
            self.raiz = novo
        elif prontuario < pai.prontuario:
            pai.esquerda = novo
        else:
            pai.direita = novo

        self._quantidade += 1
        self._registrar(f"Inserção do prontuário {prontuario} como nó vermelho.")
        self._corrigir_insercao(novo)
        self._mostrar_resultado()
        return True

    # ============= BUSCA =================

    def buscar(self, prontuario: int) -> PacienteT | None:
        """Busca pela chave e registra nós reais visitados, incluindo o encontrado."""
        self.nos_visitados_ultima_busca = 0
        if not self._prontuario_valido(prontuario):
            return None
        no, visitas = self._localizar(prontuario)
        self.nos_visitados_ultima_busca = visitas
        return no.paciente

    # ============= REMOÇÃO =================

    def remover(self, prontuario: int) -> bool:
        """Remove pela chave, restaurando a altura negra quando necessário."""
        if not self._prontuario_valido(prontuario):
            return False
        removido, _ = self._localizar(prontuario)
        if removido is self._nil:
            return False

        self._registrar(f"Remoção do prontuário {prontuario} ({removido.cor}).")
        sucessor = removido
        cor_original = sucessor.cor
        if removido.esquerda is self._nil:
            substituto = removido.direita
            self._transplantar(removido, substituto)
        elif removido.direita is self._nil:
            substituto = removido.esquerda
            self._transplantar(removido, substituto)
        else:
            # Move o nó sucessor inteiro, preservando todos os dados do paciente.
            sucessor = self._no_minimo(removido.direita)
            cor_original = sucessor.cor
            substituto = sucessor.direita
            if sucessor.pai is removido:
                substituto.pai = sucessor
            else:
                self._transplantar(sucessor, substituto)
                sucessor.direita = removido.direita
                sucessor.direita.pai = sucessor
            self._transplantar(removido, sucessor)
            sucessor.esquerda = removido.esquerda
            sucessor.esquerda.pai = sucessor
            self._recolorir(sucessor, removido.cor, "remocao")

        self._quantidade -= 1
        if cor_original == PRETO:
            self._corrigir_remocao(substituto)

        # Durante a correção, NIL.pai identifica a região que perdeu um preto.
        # Depois dela o sentinela volta a apontar para si mesmo.
        
        self._nil.pai = self._nil
        self._mostrar_resultado()
        return True

    # ============= MÍNIMO =================

    def minimo(self) -> PacienteT | None:
        """Retorna o paciente de menor prontuário, ou None na árvore vazia."""
        return self._no_minimo(self.raiz).paciente

    # ============= MÁXIMO =================

    def maximo(self) -> PacienteT | None:
        """Retorna o paciente de maior prontuário, ou None na árvore vazia."""
        atual = self.raiz
        while atual is not self._nil and atual.direita is not self._nil:
            atual = atual.direita
        return atual.paciente

    # ============= CAMINHAMENTO EM PRÉ-ORDEM =================

    def pre_ordem(self) -> list[PacienteT]:
        """Percorre raiz, esquerda, direita."""
        return self._percorrer(0)

    # ============= CAMINHAMENTO EM ORDEM =================

    def em_ordem(self) -> list[PacienteT]:
        """Percorre esquerda, raiz, direita: prontuários em ordem crescente."""
        return self._percorrer(1)

    # ============= CAMINHAMENTO EM PÓS-ORDEM =================

    def pos_ordem(self) -> list[PacienteT]:
        """Percorre esquerda, direita, raiz."""
        return self._percorrer(2)

    # ============= ALTURA =================

    def altura(self) -> int:
        """Conta níveis de nós reais: árvore vazia 0 e folha 1. Custo O(n)."""
        def medir(no: _No[PacienteT]) -> int:
            if no is self._nil:
                return 0
            return 1 + max(medir(no.esquerda), medir(no.direita))

        return medir(self.raiz)

    # ============= QUANTIDADE DE NÓS =================

    def quantidade(self) -> int:
        """Quantidade de pacientes, sem percorrer a árvore: O(1)."""
        return self._quantidade

    # ============= EXIBIÇÃO DA ÁRVORE =================

    def exibir(self) -> str:
        """Representação com prontuários, cores, lados E/D e folhas NIL pretas."""
        if self.raiz is self._nil:
            return "Árvore vazia (NIL preto)."
        linhas = [f"Raiz: {self.raiz.prontuario} ({self.raiz.cor})"]

        def desenhar(
            no: _No[PacienteT], prefixo: str, lado: str, ultimo: bool
        ) -> None:
            ramo = "`-- " if ultimo else "|-- "
            rotulo = "NIL (preto)" if no is self._nil else f"{no.prontuario} ({no.cor})"
            linhas.append(f"{prefixo}{ramo}{lado}: {rotulo}")
            if no is not self._nil:
                proximo = prefixo + ("    " if ultimo else "|   ")
                desenhar(no.esquerda, proximo, "E", False)
                desenhar(no.direita, proximo, "D", True)

        desenhar(self.raiz.esquerda, "", "E", False)
        desenhar(self.raiz.direita, "", "D", True)
        return "\n".join(linhas)

    # ============= VALIDAÇÃO DA ÁRVORE =================

    def validar(self) -> bool:
        """
        Verifica cores, ordenação, altura negra, pais, ciclos e quantidade.

        Não modifica a árvore nem suas métricas. Usa pilha explícita para também
        rejeitar estruturas corrompidas profundas sem depender da recursão.
        """
        nil = self._nil
        if (
            nil.cor != PRETO
            or nil.paciente is not None
            or nil.esquerda is not nil
            or nil.direita is not nil
            or nil.pai is not nil
        ):
            return False
        if self.raiz is nil:
            return self._quantidade == 0
        if (
            not isinstance(self.raiz, _No)
            or self.raiz.cor != PRETO
            or self.raiz.pai is not nil
        ):
            return False

        visitados: set[int] = set()
        altura_negra: int | None = None
        pilha: list[
            tuple[_No[PacienteT], int | None, int | None, _No[PacienteT], int]
        ] = [(self.raiz, None, None, nil, 0)]
        while pilha:
            no, inferior, superior, pai, pretos = pilha.pop()
            if no is nil:
                # Todos os caminhos terminam no mesmo sentinela preto.
                if altura_negra is None:
                    altura_negra = pretos + 1
                elif altura_negra != pretos + 1:
                    return False
                continue
            if not isinstance(no, _No) or id(no) in visitados:
                return False
            visitados.add(id(no))
            prontuario_paciente = getattr(no.paciente, "prontuario", None)
            if (
                no.pai is not pai
                or no.cor not in (PRETO, VERMELHO)
                or not self._prontuario_valido(no.prontuario)
                or not self._prontuario_valido(prontuario_paciente)
                or prontuario_paciente != no.prontuario
            ):
                return False
            if inferior is not None and no.prontuario <= inferior:
                return False
            if superior is not None and no.prontuario >= superior:
                return False
            if not isinstance(no.esquerda, _No) or not isinstance(no.direita, _No):
                return False
            if no.cor == VERMELHO and (
                no.esquerda.cor == VERMELHO or no.direita.cor == VERMELHO
            ):
                return False
            pretos += int(no.cor == PRETO)
            pilha.append((no.direita, no.prontuario, superior, no, pretos))
            pilha.append((no.esquerda, inferior, no.prontuario, no, pretos))
        return len(visitados) == self._quantidade

    # ============= ESTATÍSTICAS =================

    def estatisticas(self) -> dict[str, int]:
        """Devolve uma cópia dos contadores; consultas não geram rebalanceamentos."""
        return {
            **self._metricas,
            "nos_visitados_ultima_busca": self.nos_visitados_ultima_busca,
        }

    # ============= REINICIALIZAÇÃO DAS ESTATÍSTICAS =================

    def reiniciar_estatisticas(self) -> None:
        """Zera métricas e última busca, preservando pacientes e modo detalhado."""
        self._metricas = {
            "rotacoes_insercao": 0,
            "rotacoes_remocao": 0,
            "recoloracoes_insercao": 0,
            "recoloracoes_remocao": 0,
        }
        self.nos_visitados_ultima_busca = 0

    # ============= CONFIGURAÇÃO DO MODO DETALHADO =================

    def definir_modo_detalhado(self, ativo: bool) -> None:
        """Ativa ou desativa a impressão dos casos, rotações e recolorações."""
        self._modo_detalhado = bool(ativo)

    # ============= BUSCA INTERNA =================

    def _localizar(self, prontuario: int) -> tuple[_No[PacienteT], int]:
        atual = self.raiz
        visitas = 0
        while atual is not self._nil:
            visitas += 1
            if prontuario == atual.prontuario:
                break
            atual = atual.esquerda if prontuario < atual.prontuario else atual.direita
        return atual, visitas

    # ============= MÍNIMO INTERNO =================

    def _no_minimo(self, no: _No[PacienteT]) -> _No[PacienteT]:
        while no is not self._nil and no.esquerda is not self._nil:
            no = no.esquerda
        return no

    # ============= CAMINHAMENTOS INTERNOS =================

    def _percorrer(self, posicao_raiz: int) -> list[PacienteT]:
        pacientes: list[PacienteT] = []

        def visitar(no: _No[PacienteT]) -> None:
            if no is self._nil:
                return
            if posicao_raiz == 0:
                pacientes.append(cast(PacienteT, no.paciente))
            visitar(no.esquerda)
            if posicao_raiz == 1:
                pacientes.append(cast(PacienteT, no.paciente))
            visitar(no.direita)
            if posicao_raiz == 2:
                pacientes.append(cast(PacienteT, no.paciente))

        visitar(self.raiz)
        return pacientes

    # ============= REGISTROS DO MODO DETALHADO =================

    def _registrar(self, mensagem: str) -> None:
        if self._modo_detalhado:
            print(mensagem)

    def _mostrar_resultado(self) -> None:
        if self._modo_detalhado:
            print("Estrutura da árvore após a correção:")
            print(self.exibir())

    # ============= RECOLORAÇÃO =================

    def _recolorir(self, no: _No[PacienteT], cor: str, operacao: str) -> None:
        if no is self._nil or no.cor == cor:
            return
        self._registrar(f"Recoloração do prontuário {no.prontuario}: {no.cor} -> {cor}.")
        no.cor = cor
        self._metricas[f"recoloracoes_{operacao}"] += 1

    # ============= ROTAÇÃO À ESQUERDA =================

    def _rotacionar_esquerda(self, no: _No[PacienteT], operacao: str) -> None:
        promovido = no.direita
        no.direita = promovido.esquerda
        if promovido.esquerda is not self._nil:
            promovido.esquerda.pai = no
        promovido.pai = no.pai
        if no.pai is self._nil:
            self.raiz = promovido
        elif no is no.pai.esquerda:
            no.pai.esquerda = promovido
        else:
            no.pai.direita = promovido
        promovido.esquerda = no
        no.pai = promovido
        self._metricas[f"rotacoes_{operacao}"] += 1
        self._registrar(f"Rotação à esquerda no prontuário {no.prontuario}.")

    # ============= ROTAÇÃO À DIREITA =================

    def _rotacionar_direita(self, no: _No[PacienteT], operacao: str) -> None:
        promovido = no.esquerda
        no.esquerda = promovido.direita
        if promovido.direita is not self._nil:
            promovido.direita.pai = no
        promovido.pai = no.pai
        if no.pai is self._nil:
            self.raiz = promovido
        elif no is no.pai.direita:
            no.pai.direita = promovido
        else:
            no.pai.esquerda = promovido
        promovido.direita = no
        no.pai = promovido
        self._metricas[f"rotacoes_{operacao}"] += 1
        self._registrar(f"Rotação à direita no prontuário {no.prontuario}.")

    # ============= CORREÇÃO APÓS INSERÇÃO =================

    def _corrigir_insercao(self, no: _No[PacienteT]) -> None:
        while no.pai.cor == VERMELHO:
            if no.pai is no.pai.pai.esquerda:
                tio = no.pai.pai.direita
                if tio.cor == VERMELHO:
                    # Caso 1: pai e tio vermelhos; sobe a violação para o avô.
                    self._registrar(
                        f"Inserção, caso 1: tio vermelho; avô {no.pai.pai.prontuario}."
                    )
                    self._recolorir(no.pai, PRETO, "insercao")
                    self._recolorir(tio, PRETO, "insercao")
                    self._recolorir(no.pai.pai, VERMELHO, "insercao")
                    no = no.pai.pai
                else:
                    if no is no.pai.direita:
                        # Caso 2: triângulo; transforma em linha.
                        self._registrar(
                            f"Inserção, caso 2 (LR): triângulo no pai {no.pai.prontuario}."
                        )
                        no = no.pai
                        self._rotacionar_esquerda(no, "insercao")
                    # Caso 3: linha; promove o pai e recolore pai/avô.
                    self._registrar(
                        f"Inserção, caso 3 (LL): linha no avô {no.pai.pai.prontuario}."
                    )
                    self._recolorir(no.pai, PRETO, "insercao")
                    self._recolorir(no.pai.pai, VERMELHO, "insercao")
                    self._rotacionar_direita(no.pai.pai, "insercao")
            else:
                # Casos espelhados: pai é filho direito do avô.
                tio = no.pai.pai.esquerda
                if tio.cor == VERMELHO:
                    self._registrar(
                        f"Inserção, caso 1 espelhado: tio vermelho; avô {no.pai.pai.prontuario}."
                    )
                    self._recolorir(no.pai, PRETO, "insercao")
                    self._recolorir(tio, PRETO, "insercao")
                    self._recolorir(no.pai.pai, VERMELHO, "insercao")
                    no = no.pai.pai
                else:
                    if no is no.pai.esquerda:
                        self._registrar(
                            f"Inserção, caso 2 (RL): triângulo no pai {no.pai.prontuario}."
                        )
                        no = no.pai
                        self._rotacionar_direita(no, "insercao")
                    self._registrar(
                        f"Inserção, caso 3 (RR): linha no avô {no.pai.pai.prontuario}."
                    )
                    self._recolorir(no.pai, PRETO, "insercao")
                    self._recolorir(no.pai.pai, VERMELHO, "insercao")
                    self._rotacionar_esquerda(no.pai.pai, "insercao")
        self._recolorir(self.raiz, PRETO, "insercao")

    # ============= TRANSPLANTE DE NÓS =================

    def _transplantar(self, antigo: _No[PacienteT], novo: _No[PacienteT]) -> None:
        if antigo.pai is self._nil:
            self.raiz = novo
        elif antigo is antigo.pai.esquerda:
            antigo.pai.esquerda = novo
        else:
            antigo.pai.direita = novo
        # Mesmo NIL precisa do pai temporariamente para a correção da remoção.
        novo.pai = antigo.pai

    # ============= CORREÇÃO APÓS REMOÇÃO =================

    def _corrigir_remocao(self, no: _No[PacienteT]) -> None:
        # O preto extra é conceitual: nenhuma terceira cor é armazenada no nó.
        while no is not self.raiz and no.cor == PRETO:
            if no is no.pai.esquerda:
                irmao = no.pai.direita
                if irmao.cor == VERMELHO:
                    # Caso 1: irmão vermelho; obtém um irmão preto.
                    self._registrar(
                        f"Remoção, caso 1: irmão {irmao.prontuario} vermelho; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, PRETO, "remocao")
                    self._recolorir(no.pai, VERMELHO, "remocao")
                    self._rotacionar_esquerda(no.pai, "remocao")
                    irmao = no.pai.direita
                if irmao.esquerda.cor == PRETO and irmao.direita.cor == PRETO:
                    # Caso 2: sobrinhos pretos; propaga o preto extra para o pai.
                    self._registrar(
                        f"Remoção, caso 2: sobrinhos pretos; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, VERMELHO, "remocao")
                    no = no.pai
                else:
                    if irmao.direita.cor == PRETO:
                        # Caso 3: sobrinho próximo vermelho; prepara o caso 4.
                        self._registrar(
                            f"Remoção, caso 3: sobrinho próximo vermelho; irmão {irmao.prontuario}."
                        )
                        self._recolorir(irmao.esquerda, PRETO, "remocao")
                        self._recolorir(irmao, VERMELHO, "remocao")
                        self._rotacionar_direita(irmao, "remocao")
                        irmao = no.pai.direita
                    # Caso 4: sobrinho distante vermelho; elimina o preto extra.
                    self._registrar(
                        f"Remoção, caso 4: sobrinho distante vermelho; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, no.pai.cor, "remocao")
                    self._recolorir(no.pai, PRETO, "remocao")
                    self._recolorir(irmao.direita, PRETO, "remocao")
                    self._rotacionar_esquerda(no.pai, "remocao")
                    no = self.raiz
            else:
                # Mesmos quatro casos, trocando esquerda e direita.
                irmao = no.pai.esquerda
                if irmao.cor == VERMELHO:
                    self._registrar(
                        f"Remoção, caso 1 espelhado: irmão {irmao.prontuario} vermelho; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, PRETO, "remocao")
                    self._recolorir(no.pai, VERMELHO, "remocao")
                    self._rotacionar_direita(no.pai, "remocao")
                    irmao = no.pai.esquerda
                if irmao.direita.cor == PRETO and irmao.esquerda.cor == PRETO:
                    self._registrar(
                        f"Remoção, caso 2 espelhado: sobrinhos pretos; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, VERMELHO, "remocao")
                    no = no.pai
                else:
                    if irmao.esquerda.cor == PRETO:
                        self._registrar(
                            f"Remoção, caso 3 espelhado: sobrinho próximo vermelho; irmão {irmao.prontuario}."
                        )
                        self._recolorir(irmao.direita, PRETO, "remocao")
                        self._recolorir(irmao, VERMELHO, "remocao")
                        self._rotacionar_esquerda(irmao, "remocao")
                        irmao = no.pai.esquerda
                    self._registrar(
                        f"Remoção, caso 4 espelhado: sobrinho distante vermelho; pai {no.pai.prontuario}."
                    )
                    self._recolorir(irmao, no.pai.cor, "remocao")
                    self._recolorir(no.pai, PRETO, "remocao")
                    self._recolorir(irmao.esquerda, PRETO, "remocao")
                    self._rotacionar_direita(no.pai, "remocao")
                    no = self.raiz
        self._recolorir(no, PRETO, "remocao")
