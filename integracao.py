"""Contrato e ponto único de adaptação para os módulos dos integrantes 1 e 2."""

from collections.abc import Callable
from importlib import import_module
from typing import Any, Protocol

from modelos import Paciente


class Arvore(Protocol):
    """Interface prevista; estatísticas podem estar temporariamente ausentes."""

    def inserir(self, paciente: Paciente) -> bool: ...
    def buscar(self, prontuario: int) -> Paciente | None: ...
    def remover(self, prontuario: int) -> bool: ...
    def minimo(self) -> Paciente | None: ...
    def maximo(self) -> Paciente | None: ...
    def pre_ordem(self) -> list[Paciente]: ...
    def em_ordem(self) -> list[Paciente]: ...
    def pos_ordem(self) -> list[Paciente]: ...
    def altura(self) -> int: ...
    def quantidade(self) -> int: ...
    def exibir(self) -> str | None: ...
    def validar(self) -> bool: ...
    def estatisticas(self) -> dict[str, Any]: ...
    def definir_modo_detalhado(self, ativo: bool) -> None: ...
    def reiniciar_estatisticas(self) -> None: ...


FabricaArvore = Callable[[], Arvore]
MODULOS = {"AVL": ("avl", "ArvoreAVL"),
           "Rubro-Negra": ("rubro_negra", "ArvoreRubroNegra")}
METODOS_OBRIGATORIOS = (
    "inserir", "buscar", "remover", "minimo", "maximo", "pre_ordem",
    "em_ordem", "pos_ordem", "altura", "quantidade", "exibir", "validar",
    "definir_modo_detalhado",
)
MENSAGEM_INDISPONIVEL = (
    "Esta funcionalidade estará disponível após a integração das árvores "
    "AVL e Rubro-Negra."
)


class ErroIntegracao(RuntimeError):
    """Falha explícita de disponibilidade, contrato ou consistência das árvores."""


def carregar_fabricas() -> tuple[dict[str, FabricaArvore], list[str]]:
    """Importa as classes esperadas sem impedir a inicialização do menu."""
    fabricas = {}
    avisos = []
    for nome, (modulo, classe) in MODULOS.items():
        try:
            fabrica = getattr(import_module(modulo), classe)
            if not callable(fabrica):
                raise TypeError(f"{classe} não é uma fábrica de árvores.")
            fabricas[nome] = fabrica
        except Exception as erro:
            avisos.append(f"{nome} indisponível ({modulo}.{classe}): {erro}")
    return fabricas, avisos


def exigir_duas_arvores(fabricas: dict[str, FabricaArvore]) -> None:
    """Impede execução parcial com apenas uma estrutura disponível."""
    if set(fabricas) != set(MODULOS):
        raise ErroIntegracao(MENSAGEM_INDISPONIVEL)


def criar_arvore(fabrica: FabricaArvore) -> Arvore:
    """Cria uma instância vazia, válida e sem impressão detalhada."""
    arvore = fabrica()
    faltantes = [nome for nome in METODOS_OBRIGATORIOS
                 if not callable(getattr(arvore, nome, None))]
    if faltantes:
        raise ErroIntegracao("Métodos pendentes no contrato: " + ", ".join(faltantes))
    arvore.definir_modo_detalhado(False)
    if arvore.validar() is not True or arvore.quantidade() != 0 or arvore.em_ordem() != []:
        raise ErroIntegracao("A fábrica deve criar uma árvore vazia e válida.")
    return arvore


def criar_arvores(fabricas: dict[str, FabricaArvore]) -> dict[str, Arvore]:
    """Cria o par de árvores vazias, exigindo referências independentes."""
    exigir_duas_arvores(fabricas)
    arvores = {nome: criar_arvore(fabrica) for nome, fabrica in fabricas.items()}
    if arvores["AVL"] is arvores["Rubro-Negra"]:
        raise ErroIntegracao("As fábricas devem criar instâncias independentes.")
    return arvores


def conferir_colecao(arvore: Arvore, pacientes: list[Paciente]) -> None:
    """Confere propriedades, quantidade e todos os dados em ordem de chave."""
    esperados = sorted(pacientes, key=lambda paciente: paciente.prontuario)
    if (arvore.validar() is not True or arvore.quantidade() != len(esperados)
            or arvore.em_ordem() != esperados):
        raise ErroIntegracao("A árvore não preservou a coleção esperada ou suas propriedades.")
