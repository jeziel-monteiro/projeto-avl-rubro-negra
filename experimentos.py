"""Cenários comparativos: medições reais somente com ambas as árvores válidas."""

import argparse
from collections.abc import Iterable
import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from time import perf_counter
from typing import Any

from gerar_dados import (
    TAMANHOS_PADRAO, embaralhar_pacientes, gerar_pacientes, ordenar_pacientes,
)
from integracao import (
    Arvore, ErroIntegracao, FabricaArvore, carregar_fabricas, conferir_colecao,
    criar_arvores, exigir_duas_arvores,
)
from modelos import Paciente


PERCENTUAIS_REMOCAO = (10, 30, 50)


@dataclass(frozen=True)
class Cenarios:
    """Sequências compartilhadas pelas duas árvores para um tamanho e semente."""

    crescente: tuple[Paciente, ...]
    aleatoria: tuple[Paciente, ...]
    buscas_existentes: tuple[int, ...]
    buscas_inexistentes: tuple[int, ...]
    remocoes: dict[int, tuple[int, ...]]


@dataclass(frozen=True)
class Resultado:
    """Uma medição; None indica métrica ausente ou não aplicável, nunca zero fictício."""

    arvore: str
    experimento: str
    quantidade_inicial: int
    operacoes: int
    seed: int
    altura_inicial: int
    altura_final: int
    quantidade_final: int
    tempo_segundos: float
    rotacoes: int | None
    recoloracoes: int | None
    media_nos_visitados: float | None
    valido: bool
    limitacoes: str


def preparar_cenarios(quantidade: int, seed: int = 42) -> Cenarios:
    """Prepara dados fora da medição e usa prefixos da mesma ordem de remoção."""
    pacientes = gerar_pacientes(quantidade, seed)
    if not pacientes:
        raise ValueError("Os experimentos exigem pelo menos um paciente.")
    crescente = tuple(ordenar_pacientes(pacientes))
    aleatoria = tuple(embaralhar_pacientes(pacientes, seed))
    chaves = tuple(p.prontuario for p in aleatoria)
    maior = crescente[-1].prontuario
    return Cenarios(
        crescente, aleatoria, chaves,
        tuple(range(maior + 1, maior + quantidade + 1)),
        {percentual: chaves[:quantidade * percentual // 100]
         for percentual in PERCENTUAIS_REMOCAO},
    )


def _construir_par(fabricas: dict[str, FabricaArvore],
                   pacientes: tuple[Paciente, ...]) -> dict[str, Arvore]:
    """Constrói e valida ambas fora das medições de busca e remoção."""
    arvores = criar_arvores(fabricas)
    for arvore in arvores.values():
        for paciente in pacientes:
            if arvore.inserir(paciente) is not True:
                raise ErroIntegracao("Falha ao construir a coleção do experimento.")
        conferir_colecao(arvore, list(pacientes))
    return arvores


def _estatisticas(arvore: Arvore, avisos: list[str]) -> dict[str, Any]:
    """Lê uma cópia das métricas ou informa explicitamente sua indisponibilidade."""
    metodo = getattr(arvore, "estatisticas", None)
    if not callable(metodo):
        avisos.append("estatisticas() indisponível")
        return {}
    try:
        metricas = metodo()
        if not isinstance(metricas, dict):
            raise TypeError("o retorno deve ser um dicionário")
        return metricas.copy()
    except Exception as erro:
        avisos.append(f"Falha na leitura de estatísticas: {erro}")
        return {}


def _diferenca(antes: dict[str, Any], depois: dict[str, Any],
               chave: str, avisos: list[str]) -> int | None:
    """Obtém o incremento de um contador inteiro, sem inventar métricas ausentes."""
    inicial, final = antes.get(chave), depois.get(chave)
    if type(inicial) is int and type(final) is int and 0 <= inicial <= final:
        return final - inicial
    avisos.append(f"{chave} indisponível ou sem contador acumulado válido")
    return None


def _media_visitas(arvore: Arvore, chaves: tuple[int, ...],
                   esperados: list[Paciente | None], avisos: list[str]) -> float | None:
    """Repete as buscas fora do cronômetro, lendo as visitas de cada chamada."""
    total = 0
    completa = True
    for chave, esperado in zip(chaves, esperados):
        if arvore.buscar(chave) != esperado:
            raise ErroIntegracao("Retornos diferentes na coleta de visitas das buscas.")
        visitas = _estatisticas(arvore, avisos).get("nos_visitados_ultima_busca")
        if type(visitas) is int and visitas >= 0:
            total += visitas
        else:
            avisos.append("nos_visitados_ultima_busca indisponível ou sem inteiro não negativo válido")
            completa = False
    return total / len(chaves) if completa and chaves else None


def _medir(nome: str, arvore: Arvore, experimento: str, metodo: str,
           argumentos: Iterable[Any], esperados: list[Any],
           pacientes_finais: list[Paciente], quantidade_inicial: int,
           seed: int) -> Resultado:
    """Cronometra só as chamadas do lote; confere retornos e estrutura depois."""
    avisos: list[str] = []
    alternativa = "; usando diferenças de contadores" if metodo != "buscar" else ""
    reiniciar = getattr(arvore, "reiniciar_estatisticas", None)
    if callable(reiniciar):
        try:
            reiniciar()
        except Exception as erro:
            avisos.append(f"Não foi possível reiniciar estatísticas: {erro}{alternativa}")
    else:
        avisos.append("reiniciar_estatisticas() indisponível" + alternativa)
    antes = _estatisticas(arvore, avisos) if metodo != "buscar" else {}
    argumentos = tuple(argumentos)
    operacao = getattr(arvore, metodo)
    altura_inicial = arvore.altura()
    if type(altura_inicial) is not int:
        raise ErroIntegracao(f"{nome}: altura() deve retornar um inteiro.")
    inicio = perf_counter()
    retornos = [operacao(argumento) for argumento in argumentos]
    tempo = perf_counter() - inicio
    depois = _estatisticas(arvore, avisos) if metodo != "buscar" else {}
    if metodo in ("inserir", "remover"):
        corretos = all(retorno is True for retorno in retornos)
    else:
        corretos = retornos == esperados
    if not corretos:
        raise ErroIntegracao(f"{nome}: retornos incorretos no experimento {experimento}.")
    conferir_colecao(arvore, pacientes_finais)
    media = None
    if metodo == "buscar":
        media = _media_visitas(arvore, argumentos, esperados, avisos)
        conferir_colecao(arvore, pacientes_finais)
    altura = arvore.altura()
    if type(altura) is not int:
        raise ErroIntegracao(f"{nome}: altura() deve retornar um inteiro.")
    rotacoes = recoloracoes = None
    if metodo != "buscar":
        sufixo = "insercao" if metodo == "inserir" else "remocao"
        rotacoes = _diferenca(antes, depois, f"rotacoes_{sufixo}", avisos)
        recoloracoes = _diferenca(antes, depois, f"recoloracoes_{sufixo}", avisos)
    return Resultado(nome, experimento, quantidade_inicial, len(argumentos), seed,
                     altura_inicial, altura, arvore.quantidade(), tempo, rotacoes, recoloracoes,
                     media, True, "; ".join(dict.fromkeys(avisos)))


def _insercoes(fabricas: dict[str, FabricaArvore], cenarios: Cenarios,
               seed: int) -> list[Resultado]:
    """Executa A e B com a mesma coleção e instâncias novas para cada ordem."""
    resultados = []
    for experimento, sequencia in (("A_insercao_crescente", cenarios.crescente),
                                  ("B_insercao_aleatoria", cenarios.aleatoria)):
        for nome, arvore in criar_arvores(fabricas).items():
            resultados.append(_medir(nome, arvore, experimento, "inserir", sequencia,
                                      [], list(sequencia), len(sequencia), seed))
    return resultados


def _buscas(fabricas: dict[str, FabricaArvore], cenarios: Cenarios,
            seed: int) -> list[Resultado]:
    """Separa buscas existentes/inexistentes e compara com os pacientes originais."""
    resultados = []
    pacientes = {p.prontuario: p for p in cenarios.crescente}
    arvores = _construir_par(fabricas, cenarios.aleatoria)
    for experimento, chaves in (("C_busca_existente", cenarios.buscas_existentes),
                                ("C_busca_inexistente", cenarios.buscas_inexistentes)):
        esperados = [pacientes.get(chave) for chave in chaves]
        for nome, arvore in arvores.items():
            resultados.append(_medir(nome, arvore, experimento, "buscar", chaves,
                                      esperados, list(cenarios.crescente), len(pacientes), seed))
    return resultados


def _remocoes(fabricas: dict[str, FabricaArvore], cenarios: Cenarios,
              seed: int) -> list[Resultado]:
    """Reconstrói ambas as árvores para cada percentual, sem remoções acumuladas."""
    resultados = []
    for percentual, chaves in cenarios.remocoes.items():
        removidos = set(chaves)
        restantes = [p for p in cenarios.crescente if p.prontuario not in removidos]
        for nome, arvore in _construir_par(fabricas, cenarios.aleatoria).items():
            resultados.append(_medir(nome, arvore, f"D_remocao_{percentual}", "remover",
                                      chaves, [], restantes, len(cenarios.crescente), seed))
    return resultados


def executar_experimentos(tamanhos: Iterable[int] = TAMANHOS_PADRAO, seed: int = 42,
                          fabricas: dict[str, FabricaArvore] | None = None) -> list[Resultado]:
    """Executa A–D; aborta diante de árvores ausentes, inválidas ou não equivalentes."""
    tamanhos = tuple(tamanhos)
    if not tamanhos or any(type(n) is not int or n <= 0 for n in tamanhos):
        raise ValueError("Informe tamanhos inteiros positivos para os experimentos.")
    if type(seed) is not int:
        raise TypeError("A semente dos experimentos deve ser um inteiro.")
    if fabricas is None:
        fabricas, avisos = carregar_fabricas()
        if avisos:
            raise ErroIntegracao("Experimentos indisponíveis: " + "; ".join(avisos))
    exigir_duas_arvores(fabricas)
    resultados = []
    for quantidade in tamanhos:
        cenarios = preparar_cenarios(quantidade, seed)
        resultados.extend(_insercoes(fabricas, cenarios, seed))
        resultados.extend(_buscas(fabricas, cenarios, seed))
        resultados.extend(_remocoes(fabricas, cenarios, seed))
    return resultados


def exportar_csv(resultados: Iterable[Resultado],
                  caminho: str | Path = "resultados/resultados.csv") -> Path:
    """Cria CSV sem sobrescrever; None vira campo vazio, zero é preservado."""
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise FileExistsError(f"O arquivo {destino} já existe; escolha outro destino para preservá-lo.")
    with destino.open("x", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[campo.name for campo in fields(Resultado)])
        escritor.writeheader()
        for resultado in resultados:
            escritor.writerow(asdict(resultado))
    return destino


def main() -> None:
    """Oferece execução configurável sem gerar CSV quando faltam árvores reais."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tamanhos", nargs="+", type=int, default=TAMANHOS_PADRAO)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--saida", default="resultados/resultados.csv")
    argumentos = parser.parse_args()
    try:
        resultados = executar_experimentos(argumentos.tamanhos, argumentos.seed)
        destino = exportar_csv(resultados, argumentos.saida)
    except Exception as erro:
        parser.exit(1, f"Experimentos não concluídos: {erro}\n")
    print(f"{len(resultados)} medições reais exportadas para {destino}.")
    for aviso in sorted({r.limitacoes for r in resultados if r.limitacoes}):
        print(f"Limitação: {aviso}")


if __name__ == "__main__":
    main()
