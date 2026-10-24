"""Menu da clínica e operações coordenadas sobre as duas árvores reais."""

from collections.abc import Callable, Iterable

from gerar_dados import gerar_pacientes
from integracao import (
    Arvore, ErroIntegracao, FabricaArvore, MENSAGEM_INDISPONIVEL, MODULOS,
    carregar_fabricas, conferir_colecao, criar_arvores,
)
from modelos import Paciente


class Clinica:
    """Coordena ambas as árvores; o dicionário guarda o estado para recuperação."""

    def __init__(self, fabricas: dict[str, FabricaArvore] | None = None) -> None:
        self.avisos: list[str] = []
        if fabricas is None:
            fabricas, self.avisos = carregar_fabricas()
        self.fabricas = dict(fabricas)
        self.arvores: dict[str, Arvore] = {}
        self._pacientes: dict[int, Paciente] = {}
        self._consistente = True
        self.detalhado = dict.fromkeys(MODULOS, False)
        try:
            self.arvores = criar_arvores(self.fabricas)
        except Exception as erro:
            self.arvores = {}
            self.avisos.append(str(erro))

    @property
    def disponivel(self) -> bool:
        """Informa se as duas estruturas foram integradas e estão consistentes."""
        return len(self.arvores) == 2 and self._consistente

    def exigir_disponibilidade(self) -> None:
        """Bloqueia operações quando faltam módulos ou há recuperação pendente."""
        if not self._consistente:
            raise ErroIntegracao("Inconsistência nas árvores: operações bloqueadas. Reinicie o sistema.")
        if not self.disponivel:
            raise ErroIntegracao(MENSAGEM_INDISPONIVEL)

    def selecionar(self, nome: str) -> Arvore:
        """Obtém a árvore escolhida para inspeção."""
        self.exigir_disponibilidade()
        return self.arvores[nome]

    def _restaurar(self) -> None:
        """Reconstrói ambas em instâncias novas antes de trocar as referências."""
        restauradas = criar_arvores(self.fabricas)
        for nome, arvore in restauradas.items():
            for paciente in self._pacientes.values():
                if arvore.inserir(paciente) is not True:
                    raise ErroIntegracao("Falha ao restaurar paciente confirmado.")
            conferir_colecao(arvore, list(self._pacientes.values()))
            arvore.definir_modo_detalhado(self.detalhado[nome])
        self.arvores = restauradas

    def _alterar(self, novos: dict[int, Paciente], operacao: Callable[[Arvore], None]) -> None:
        """Confirma a alteração somente após verificar ambas as coleções."""
        try:
            for arvore in self.arvores.values():
                operacao(arvore)
                conferir_colecao(arvore, list(novos.values()))
        except Exception as erro:
            try:
                self._restaurar()
            except Exception as falha:
                self._consistente = False
                raise ErroIntegracao(
                    f"Falha parcial: {erro}. Restauração falhou: {falha}. "
                    "Operações bloqueadas; o último estado confirmado foi preservado em memória."
                ) from erro
            raise ErroIntegracao(
                f"Operação cancelada: {erro}. Ambas as árvores foram restauradas; "
                "estatísticas anteriores descartadas na reconstrução."
            ) from erro
        self._pacientes = novos

    def cadastrar(self, paciente: Paciente) -> None:
        """Insere um paciente nas duas estruturas sem aceitar duplicidade."""
        self.cadastrar_lote([paciente])

    def cadastrar_lote(self, pacientes: Iterable[Paciente]) -> None:
        """Insere um lote inteiro ou recupera o estado anterior nas duas árvores."""
        self.exigir_disponibilidade()
        lote = list(pacientes)
        novos = self._pacientes.copy()
        for paciente in lote:
            if not isinstance(paciente, Paciente):
                raise TypeError("O cadastro deve receber objetos Paciente.")
            if paciente.prontuario in novos:
                raise ValueError(f"Prontuário {paciente.prontuario} já cadastrado.")
            novos[paciente.prontuario] = paciente

        def inserir(arvore: Arvore) -> None:
            for paciente in lote:
                if arvore.inserir(paciente) is not True:
                    raise ErroIntegracao(f"Inserção recusada para {paciente.prontuario}.")

        self._alterar(novos, inserir)

    def remover(self, prontuario: int) -> None:
        """Remove de ambas ou restaura o estado anterior se houver falha."""
        self.exigir_disponibilidade()
        if prontuario not in self._pacientes:
            raise ValueError("Paciente não encontrado.")
        novos = self._pacientes.copy()
        del novos[prontuario]

        def remover(arvore: Arvore) -> None:
            if arvore.remover(prontuario) is not True:
                raise ErroIntegracao(f"Remoção recusada para {prontuario}.")

        self._alterar(novos, remover)

    def proximo_prontuario(self) -> int:
        """Evita colisões entre lotes fictícios e pacientes já cadastrados."""
        return max(self._pacientes, default=0) + 1


MENU = """
Clínica / Atendimento — árvore selecionada: {selecionada}
1 - Cadastrar paciente
2 - Buscar por prontuário
3 - Remover por prontuário
4 - Listar pacientes em ordem
5 - Consultar menor e maior prontuário
6 - Visualizar caminhamentos
7 - Consultar altura e quantidade de nós
8 - Visualizar estrutura
9 - Consultar rotações e recolorações
10 - Validar propriedades
11 - Ativar/desativar modo detalhado
12 - Gerar pacientes fictícios
13 - Executar experimentos comparativos
s - Selecionar AVL ou Rubro-Negra
0 - Encerrar
"""


class MenuClinica:
    """Agrupa entradas e ações para manter o laço principal pequeno."""

    def __init__(self, clinica: Clinica, entrada: Callable[[str], str],
                 saida: Callable[[str], None]) -> None:
        self.clinica = clinica
        self.entrada = entrada
        self.saida = saida
        self.selecionada = "AVL"

    def _inteiro(self, mensagem: str, minimo: int = 1) -> int:
        valor = int(self.entrada(mensagem))
        if valor < minimo:
            raise ValueError(f"Informe um inteiro maior ou igual a {minimo}.")
        return valor

    def _listar(self, pacientes: list[Paciente]) -> None:
        if not pacientes:
            self.saida("Nenhum paciente cadastrado.")
        for paciente in pacientes:
            self.saida(str(paciente))

    def cadastrar(self) -> None:
        """Valida os dados mesmo quando os módulos das árvores estão ausentes."""
        paciente = Paciente(self._inteiro("Prontuário: "), self.entrada("Nome: "),
                            self.entrada("Nascimento (AAAA-MM-DD): "),
                            self.entrada("Telefone: "))
        self.saida("Dados do paciente validados.")
        self.clinica.cadastrar(paciente)
        self.saida("Paciente cadastrado em ambas as árvores.")

    def buscar(self) -> None:
        arvore = self.clinica.selecionar(self.selecionada)
        paciente = arvore.buscar(self._inteiro("Prontuário: "))
        self.saida(str(paciente) if paciente is not None else "Paciente não encontrado.")

    def remover(self) -> None:
        self.clinica.exigir_disponibilidade()
        self.clinica.remover(self._inteiro("Prontuário: "))
        self.saida("Paciente removido de ambas as árvores.")

    def inspecionar(self, opcao: str) -> None:
        """Executa consultas somente na estrutura selecionada."""
        arvore = self.clinica.selecionar(self.selecionada)
        if opcao == "4":
            self._listar(arvore.em_ordem())
        elif opcao == "5":
            self.saida(f"Menor: {arvore.minimo()}\nMaior: {arvore.maximo()}")
        elif opcao == "6":
            for nome in ("pre_ordem", "em_ordem", "pos_ordem"):
                self.saida(nome.replace("_", " ") + ":")
                self._listar(getattr(arvore, nome)())
        elif opcao == "7":
            self.saida(f"Altura: {arvore.altura()} | Quantidade de nós: {arvore.quantidade()}")
        elif opcao == "8":
            estrutura = arvore.exibir()
            if estrutura is not None:
                self.saida(str(estrutura))
        elif opcao == "9":
            metodo = getattr(arvore, "estatisticas", None)
            self.saida(str(metodo()) if callable(metodo) else "Estatísticas indisponíveis.")
        elif opcao == "10":
            self.saida("Árvore válida." if arvore.validar() is True else "Árvore inválida.")
        elif opcao == "11":
            ativo = not self.clinica.detalhado[self.selecionada]
            arvore.definir_modo_detalhado(ativo)
            self.clinica.detalhado[self.selecionada] = ativo
            self.saida("Modo detalhado ativado." if ativo else "Modo detalhado desativado.")

    def gerar(self) -> None:
        """Gera e mostra amostra; cadastra o lote quando há integração disponível."""
        quantidade = self._inteiro("Quantidade de pacientes: ", minimo=0)
        seed = int(self.entrada("Semente aleatória (inteiro): "))
        pacientes = gerar_pacientes(quantidade, seed, self.clinica.proximo_prontuario())
        self.saida(f"{len(pacientes)} pacientes fictícios gerados; amostra de até 5:")
        self._listar(pacientes[:5])
        if self.clinica.disponivel:
            self.clinica.cadastrar_lote(pacientes)
            self.saida("Lote cadastrado em ambas as árvores.")
        else:
            self.saida("Dados apenas gerados, sem cadastro. " + MENSAGEM_INDISPONIVEL)

    def experimentar(self) -> None:
        """Executa as medições em instâncias separadas das árvores do menu."""
        from experimentos import executar_experimentos, exportar_csv

        self.clinica.exigir_disponibilidade()
        texto = self.entrada("Tamanhos separados por vírgula [100,1000,10000]: ")
        tamanhos = tuple(int(item.strip()) for item in texto.split(",")) if texto.strip() else (100, 1000, 10000)
        seed = int(self.entrada("Semente aleatória (inteiro): "))
        resultados = executar_experimentos(tamanhos, seed, self.clinica.fabricas)
        caminho = exportar_csv(resultados)
        self.saida(f"Medições reais concluídas: {caminho}")
        for aviso in sorted({r.limitacoes for r in resultados if r.limitacoes}):
            self.saida(f"Limitação: {aviso}")

    def escolher_arvore(self) -> None:
        escolha = self.entrada("Árvore (1 - AVL; 2 - Rubro-Negra): ").strip()
        nomes = {"1": "AVL", "2": "Rubro-Negra"}
        if escolha not in nomes:
            raise ValueError("Selecione 1 para AVL ou 2 para Rubro-Negra.")
        self.selecionada = nomes[escolha]

    def executar(self) -> None:
        """Mantém o menu ativo após erros de entrada e falhas das integrações."""
        for aviso in self.clinica.avisos:
            self.saida(aviso)
        acoes = {"1": self.cadastrar, "2": self.buscar, "3": self.remover,
                 "12": self.gerar, "13": self.experimentar, "s": self.escolher_arvore}
        while True:
            try:
                self.saida(MENU.format(selecionada=self.selecionada))
                opcao = self.entrada("Opção: ").strip().lower()
                if opcao == "0":
                    break
                if opcao in acoes:
                    acoes[opcao]()
                elif opcao in {str(numero) for numero in range(4, 12)}:
                    self.inspecionar(opcao)
                else:
                    self.saida("Opção inválida. Escolha uma das opções do menu.")
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as erro:
                self.saida(f"Não foi possível concluir: {erro}")
        self.saida("Sistema encerrado.")


def executar_menu(entrada: Callable[[str], str] | None = None,
                  saida: Callable[[str], None] = print,
                  clinica: Clinica | None = None) -> None:
    """Inicia o menu com entrada/saída substituíveis para testes automatizados."""
    MenuClinica(clinica if clinica is not None else Clinica(),
                entrada if entrada is not None else input, saida).executar()


if __name__ == "__main__":
    executar_menu()
