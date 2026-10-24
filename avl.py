"""Árvore AVL de pacientes, ordenada somente pelo número do prontuário.

Não depende do modelo de pacientes nem da implementação Rubro-Negra.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar


class RegistroPaciente(Protocol):
    """Contrato mínimo para receber a futura classe Paciente do grupo."""

    @property
    def prontuario(self) -> int:
        """Chave única, inteira e positiva, que não deve mudar após a inserção."""
        ...


PacienteT = TypeVar("PacienteT", bound=RegistroPaciente)


class _No(Generic[PacienteT]):
    """Nó interno: mantém o paciente completo, sua chave e a altura local."""

    def __init__(self, paciente: PacienteT) -> None:
        self.paciente = paciente
        self.prontuario = paciente.prontuario
        self.esquerda: _No[PacienteT] | None = None
        self.direita: _No[PacienteT] | None = None
        self.altura = 1


class ArvoreAVL(Generic[PacienteT]):
    """Cadastro balanceado com inserção, busca e remoção em O(log n).

    Preserva os objetos recebidos. Duplicatas e chaves inválidas são recusadas;
    consultas retornam pacientes, nunca nós. A altura conta níveis (vazia 0,
    folha 1). Uma rotação dupla conta como duas rotações simples.
    """

    def __init__(self, modo_detalhado: bool = False) -> None:
        self.raiz: _No[PacienteT] | None = None
        self._quantidade = 0
        self._modo_detalhado = bool(modo_detalhado)
        self.reiniciar_estatisticas()

    @staticmethod
    def _prontuario_valido(prontuario: object) -> bool:
        # bool herda de int, mas não representa um número de prontuário.
        return (
            isinstance(prontuario, int)
            and not isinstance(prontuario, bool)
            and prontuario > 0
        )

    def inserir(self, paciente: PacienteT) -> bool:
        """Insere o paciente original; não sobrescreve prontuários duplicados."""
        if not self._prontuario_valido(getattr(paciente, "prontuario", None)):
            return False
        self._registrar(f"Inserção do prontuário {paciente.prontuario}.")
        self.raiz, inserido = self._inserir(self.raiz, paciente)
        if inserido:
            self._quantidade += 1
            self._mostrar_resultado()
        else:
            self._registrar("Inserção recusada: prontuário duplicado.")
        return inserido

    def buscar(self, prontuario: int) -> PacienteT | None:
        """Conta os nós visitados, incluindo o encontrado; None não conta."""
        self.nos_visitados_ultima_busca = 0
        if not self._prontuario_valido(prontuario):
            return None
        atual = self.raiz
        while atual is not None:
            self.nos_visitados_ultima_busca += 1
            if prontuario == atual.prontuario:
                return atual.paciente
            atual = atual.esquerda if prontuario < atual.prontuario else atual.direita
        return None

    def remover(self, prontuario: int) -> bool:
        """Remove pela chave; devolve False para chave inválida ou inexistente."""
        if not self._prontuario_valido(prontuario):
            return False
        self._registrar(f"Remoção do prontuário {prontuario}.")
        self.raiz, removido = self._remover(self.raiz, prontuario)
        if removido:
            self._quantidade -= 1
            self._mostrar_resultado()
        return removido

    def minimo(self) -> PacienteT | None:
        """Paciente de menor prontuário, ou None na árvore vazia."""
        return None if self.raiz is None else self._no_minimo(self.raiz).paciente

    def maximo(self) -> PacienteT | None:
        """Paciente de maior prontuário, ou None na árvore vazia."""
        atual = self.raiz
        if atual is None:
            return None
        while atual.direita is not None:
            atual = atual.direita
        return atual.paciente

    def pre_ordem(self) -> list[PacienteT]:
        """Nova lista de pacientes na ordem raiz, esquerda, direita."""
        return self._percorrer(0)

    def em_ordem(self) -> list[PacienteT]:
        """Nova lista de pacientes por prontuário crescente."""
        return self._percorrer(1)

    def pos_ordem(self) -> list[PacienteT]:
        """Nova lista de pacientes na ordem esquerda, direita, raiz."""
        return self._percorrer(2)

    def altura(self) -> int:
        """Altura mantida nas atualizações: consulta em O(1)."""
        return self._altura(self.raiz)

    def quantidade(self) -> int:
        """Quantidade de pacientes em O(1)."""
        return self._quantidade

    def exibir(self) -> str:
        """Texto com raiz, lados E/D, alturas e fatores; use print para exibir."""
        if self.raiz is None:
            return "Árvore vazia."

        def rotulo(no: _No[PacienteT]) -> str:
            return f"{no.prontuario} (h={no.altura}, FB={self._fator(no)})"

        linhas = [f"Raiz: {rotulo(self.raiz)}"]

        def desenhar(
            no: _No[PacienteT] | None, prefixo: str, lado: str, ultimo: bool
        ) -> None:
            ramo = "`-- " if ultimo else "|-- "
            linhas.append(f"{prefixo}{ramo}{lado}: " + ("vazio" if no is None else rotulo(no)))
            if no is not None:
                proximo = prefixo + ("    " if ultimo else "|   ")
                desenhar(no.esquerda, proximo, "E", False)
                desenhar(no.direita, proximo, "D", True)

        desenhar(self.raiz.esquerda, "", "E", False)
        desenhar(self.raiz.direita, "", "D", True)
        return "\n".join(linhas)

    def validar(self) -> bool:
        """Verifica ordenação global, balanceamento, alturas, chaves e quantidade.

        Usa pós-ordem com pilha explícita e recalcula as alturas sem confiar nas
        armazenadas. Também rejeita ciclos/nós compartilhados e chaves alteradas
        no paciente, sem modificar a estrutura ou as métricas.
        """
        if type(self._quantidade) is not int or self._quantidade < 0:
            return False
        if self.raiz is None:
            return self._quantidade == 0
        visitados: set[int] = set()
        alturas: dict[int, int] = {}
        pilha: list[tuple[_No[PacienteT] | None, int | None, int | None, bool]] = [
            (self.raiz, None, None, False)
        ]
        while pilha:
            no, inferior, superior, processado = pilha.pop()
            if no is None:
                continue
            if not isinstance(no, _No):
                return False
            if processado:
                esquerda = alturas.get(id(no.esquerda), 0)
                direita = alturas.get(id(no.direita), 0)
                altura_real = 1 + max(esquerda, direita)
                if (
                    type(no.altura) is not int
                    or no.altura != altura_real
                    or abs(esquerda - direita) > 1
                ):
                    return False
                alturas[id(no)] = altura_real
                continue
            if id(no) in visitados:
                return False
            visitados.add(id(no))
            chave_paciente = getattr(no.paciente, "prontuario", None)
            if (
                not self._prontuario_valido(no.prontuario)
                or not self._prontuario_valido(chave_paciente)
                or chave_paciente != no.prontuario
            ):
                return False
            if inferior is not None and no.prontuario <= inferior:
                return False
            if superior is not None and no.prontuario >= superior:
                return False
            pilha.append((no, inferior, superior, True))
            pilha.append((no.direita, no.prontuario, superior, False))
            pilha.append((no.esquerda, inferior, no.prontuario, False))
        return len(visitados) == self._quantidade

    def estatisticas(self) -> dict[str, int]:
        """Cópia das métricas, com as mesmas chaves da Rubro-Negra.

        Recolorações são sempre zero na AVL. Somente buscar() atualiza a
        quantidade de nós visitados na última busca.
        """
        return {
            **self._metricas,
            "nos_visitados_ultima_busca": self.nos_visitados_ultima_busca,
        }

    def reiniciar_estatisticas(self) -> None:
        """Zera métricas sem apagar pacientes nem alterar o modo detalhado."""
        self._metricas = {
            "rotacoes_insercao": 0,
            "rotacoes_remocao": 0,
            "recoloracoes_insercao": 0,
            "recoloracoes_remocao": 0,
        }
        self.nos_visitados_ultima_busca = 0

    def definir_modo_detalhado(self, ativo: bool) -> None:
        """Ativa/desativa mensagens sobre operações e rebalanceamentos."""
        self._modo_detalhado = bool(ativo)

    @staticmethod
    def _altura(no: _No[PacienteT] | None) -> int:
        return 0 if no is None else no.altura

    def _atualizar_altura(self, no: _No[PacienteT]) -> None:
        no.altura = 1 + max(self._altura(no.esquerda), self._altura(no.direita))

    def _fator(self, no: _No[PacienteT]) -> int:
        return self._altura(no.esquerda) - self._altura(no.direita)

    def _rotacionar_direita(self, no: _No[PacienteT], operacao: str) -> _No[PacienteT]:
        promovido = no.esquerda
        assert promovido is not None
        no.esquerda = promovido.direita
        promovido.direita = no
        # Atualiza primeiro o rebaixado: a altura do promovido depende dele.
        self._atualizar_altura(no)
        self._atualizar_altura(promovido)
        self._metricas[f"rotacoes_{operacao}"] += 1
        self._registrar(f"Rotação à direita no prontuário {no.prontuario}.")
        return promovido

    def _rotacionar_esquerda(self, no: _No[PacienteT], operacao: str) -> _No[PacienteT]:
        promovido = no.direita
        assert promovido is not None
        no.direita = promovido.esquerda
        promovido.esquerda = no
        self._atualizar_altura(no)
        self._atualizar_altura(promovido)
        self._metricas[f"rotacoes_{operacao}"] += 1
        self._registrar(f"Rotação à esquerda no prontuário {no.prontuario}.")
        return promovido

    def _reequilibrar(self, no: _No[PacienteT], operacao: str) -> _No[PacienteT]:
        self._atualizar_altura(no)
        fator = self._fator(no)
        if fator > 1:
            assert no.esquerda is not None
            duplo = self._fator(no.esquerda) < 0
            caso = "LR" if duplo else "LL"
            self._registrar(f"Desequilíbrio no prontuário {no.prontuario} (FB={fator}): caso {caso}.")
            if duplo:
                no.esquerda = self._rotacionar_esquerda(no.esquerda, operacao)
            return self._rotacionar_direita(no, operacao)
        if fator < -1:
            assert no.direita is not None
            duplo = self._fator(no.direita) > 0
            caso = "RL" if duplo else "RR"
            self._registrar(f"Desequilíbrio no prontuário {no.prontuario} (FB={fator}): caso {caso}.")
            if duplo:
                no.direita = self._rotacionar_direita(no.direita, operacao)
            return self._rotacionar_esquerda(no, operacao)
        return no

    def _inserir(
        self, no: _No[PacienteT] | None, paciente: PacienteT
    ) -> tuple[_No[PacienteT], bool]:
        if no is None:
            return _No(paciente), True
        if paciente.prontuario == no.prontuario:
            return no, False
        if paciente.prontuario < no.prontuario:
            no.esquerda, inserido = self._inserir(no.esquerda, paciente)
        else:
            no.direita, inserido = self._inserir(no.direita, paciente)
        return (self._reequilibrar(no, "insercao"), True) if inserido else (no, False)

    def _remover(
        self, no: _No[PacienteT] | None, prontuario: int
    ) -> tuple[_No[PacienteT] | None, bool]:
        if no is None:
            return None, False
        if prontuario < no.prontuario:
            no.esquerda, removido = self._remover(no.esquerda, prontuario)
        elif prontuario > no.prontuario:
            no.direita, removido = self._remover(no.direita, prontuario)
        else:
            if no.esquerda is None:
                return no.direita, True
            if no.direita is None:
                return no.esquerda, True
            sucessor = self._no_minimo(no.direita)
            # Substitui o registro inteiro, mantendo todos os dados associados.
            no.paciente, no.prontuario = sucessor.paciente, sucessor.prontuario
            no.direita, _ = self._remover(no.direita, sucessor.prontuario)
            removido = True
        # Na remoção, a redução da altura pode propagar-se até a raiz.
        return (self._reequilibrar(no, "remocao"), True) if removido else (no, False)

    @staticmethod
    def _no_minimo(no: _No[PacienteT]) -> _No[PacienteT]:
        while no.esquerda is not None:
            no = no.esquerda
        return no

    def _percorrer(self, posicao_raiz: int) -> list[PacienteT]:
        pacientes: list[PacienteT] = []

        def visitar(no: _No[PacienteT] | None) -> None:
            if no is None:
                return
            if posicao_raiz == 0:
                pacientes.append(no.paciente)
            visitar(no.esquerda)
            if posicao_raiz == 1:
                pacientes.append(no.paciente)
            visitar(no.direita)
            if posicao_raiz == 2:
                pacientes.append(no.paciente)

        visitar(self.raiz)
        return pacientes

    def _registrar(self, mensagem: str) -> None:
        if self._modo_detalhado:
            print(mensagem)

    def _mostrar_resultado(self) -> None:
        if self._modo_detalhado:
            print("Estrutura da árvore após a correção:")
            print(self.exibir())
