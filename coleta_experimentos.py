"""Coleta sequencial em lotes exclusivos, com rastreabilidade e sem sobrescrita."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
import platform
import subprocess
import sys
from time import get_clock_info
from uuid import uuid4

from experimentos import Resultado, executar_experimentos, exportar_csv
from gerar_dados import TAMANHOS_PADRAO


RAIZ = Path(__file__).resolve().parent
FUSO_MANAUS = timezone(timedelta(hours=-4), "America/Manaus")
EXPERIMENTOS = (
    "A_insercao_crescente", "B_insercao_aleatoria", "C_busca_existente",
    "C_busca_inexistente", "D_remocao_10", "D_remocao_30", "D_remocao_50",
)
ARQUIVOS_CODIGO = (
    "modelos.py", "gerar_dados.py", "avl.py", "rubro_negra.py",
    "integracao.py", "experimentos.py", "coleta_experimentos.py",
)


def agora() -> str:
    """Registra o instante com o deslocamento explícito de Manaus (UTC−04)."""
    return datetime.now(FUSO_MANAUS).isoformat(timespec="microseconds")


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _git(*argumentos: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *argumentos], cwd=RAIZ, text=True, stderr=subprocess.DEVNULL,
            encoding="utf-8",
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def coletar_ambiente(tamanhos: tuple[int, ...], seed: int, repeticoes: int) -> dict:
    """Obtém somente informações identificadas pelo sistema e pelo Git."""
    relogio = get_clock_info("perf_counter")
    return {
        "python": sys.version, "executavel_python": sys.executable,
        "sistema_operacional": platform.system(), "versao_sistema": platform.version(),
        "plataforma": platform.platform(), "arquitetura": platform.architecture()[0],
        "maquina": platform.machine(),
        "processador": platform.processor() or "Não pôde ser identificado",
        "inicio": agora(), "fuso_horario": "America/Manaus (UTC-04:00)",
        "comando": [sys.executable, *sys.argv],
        "procedimento": "executar_lote: chamadas sequenciais de executar_experimentos; "
                        "novas instâncias em cada repetição; modo detalhado desativado",
        "seed": seed, "tamanhos": list(tamanhos), "repeticoes": repeticoes,
        "commit_git": _git("rev-parse", "HEAD"),
        "branch_git": _git("branch", "--show-current"),
        "estado_git": _git("status", "--porcelain"),
        "sha256_codigo": {nome: sha256(RAIZ / nome) for nome in ARQUIVOS_CODIGO},
        "cronometro": {"implementacao": relogio.implementation,
                       "resolucao_segundos": relogio.resolution,
                       "monotonico": relogio.monotonic},
        "ordem_arvores": ["AVL", "Rubro-Negra"],
    }


def validar_resultado(resultado: Resultado) -> None:
    """Valida tipos, limites e coerência de uma medição, preservando None legítimo."""
    if (resultado.arvore not in ("AVL", "Rubro-Negra")
            or resultado.experimento not in EXPERIMENTOS):
        raise ValueError("Árvore ou cenário desconhecido na medição.")
    if type(resultado.seed) is not int or resultado.valido is not True:
        raise ValueError("Semente inteira e validação estrutural verdadeira são obrigatórias.")
    for campo in ("quantidade_inicial", "operacoes", "altura_inicial",
                  "altura_final", "quantidade_final"):
        valor = getattr(resultado, campo)
        if type(valor) is not int or valor < 0:
            raise ValueError(f"{campo} deve ser um inteiro não negativo, sem booleanos.")
    if resultado.quantidade_inicial == 0:
        raise ValueError("quantidade_inicial deve ser positiva nos experimentos.")
    for campo in ("rotacoes", "recoloracoes"):
        valor = getattr(resultado, campo)
        if valor is not None and (type(valor) is not int or valor < 0):
            raise ValueError(f"{campo} deve ser None ou um inteiro não negativo, sem booleanos.")
    for campo in ("tempo_segundos", "media_nos_visitados"):
        valor = getattr(resultado, campo)
        if campo == "media_nos_visitados" and valor is None:
            continue
        try:
            valido = type(valor) in (int, float) and isfinite(valor) and valor >= 0
        except OverflowError:
            valido = False
        if not valido:
            raise ValueError(f"{campo} deve ser um número finito não negativo, sem booleanos.")

    insercao = resultado.experimento.startswith(("A_", "B_"))
    quantidade_antes = 0 if insercao else resultado.quantidade_inicial
    for momento, quantidade in (("inicial", quantidade_antes),
                                ("final", resultado.quantidade_final)):
        altura = getattr(resultado, f"altura_{momento}")
        if ((quantidade == 0 and altura != 0)
                or (quantidade > 0 and not 1 <= altura <= quantidade)):
            raise ValueError(f"altura_{momento} incompatível com a quantidade de pacientes.")
    if insercao:
        if resultado.quantidade_final != resultado.quantidade_inicial:
            raise ValueError("Inserção deve partir de árvore vazia e inserir o lote todo.")
    elif resultado.experimento.startswith("C_"):
        if (resultado.altura_inicial != resultado.altura_final
                or resultado.quantidade_final != resultado.quantidade_inicial):
            raise ValueError("Busca alterou a altura ou a quantidade de pacientes.")
    else:
        percentual = int(resultado.experimento.rsplit("_", 1)[1])
        if (resultado.operacoes != resultado.quantidade_inicial * percentual // 100
                or resultado.quantidade_final != resultado.quantidade_inicial - resultado.operacoes):
            raise ValueError("Remoção incompatível com o conjunto original.")
    if (not resultado.experimento.startswith("D_")
            and resultado.operacoes != resultado.quantidade_inicial):
        raise ValueError("Quantidade de operações incompatível com o cenário.")


def conferir_execucao(resultados: list[Resultado], tamanhos: tuple[int, ...],
                      seed: int) -> None:
    """Exige todos os cenários e invariantes; campos ausentes não viram zeros."""
    if (not tamanhos or any(type(n) is not int or n <= 0 for n in tamanhos)
            or len(set(tamanhos)) != len(tamanhos) or type(seed) is not int):
        raise ValueError("Tamanhos positivos distintos e semente inteira são obrigatórios.")
    for resultado in resultados:
        validar_resultado(resultado)
        if resultado.seed != seed:
            raise ValueError("Semente incompatível com a coleta.")
    esperados = {(nome, experimento, n) for nome in ("AVL", "Rubro-Negra")
                 for experimento in EXPERIMENTOS for n in tamanhos}
    chaves = [(r.arvore, r.experimento, r.quantidade_inicial) for r in resultados]
    if len(chaves) != len(esperados) or set(chaves) != esperados:
        raise ValueError("Execução incompleta ou com cenários duplicados.")


def executar_lote(tamanhos=TAMANHOS_PADRAO, seed: int = 42, repeticoes: int = 5,
                  destino: str | Path = "resultados/execucoes") -> Path:
    """Reserva uma pasta única e preserva CSVs e registro de eventual falha."""
    tamanhos = tuple(tamanhos)
    if (not tamanhos or any(type(n) is not int or n <= 0 for n in tamanhos)
            or len(set(tamanhos)) != len(tamanhos)):
        raise ValueError("Informe tamanhos positivos distintos.")
    if type(seed) is not int or type(repeticoes) is not int or repeticoes <= 0:
        raise ValueError("Semente inteira e número positivo de repetições são obrigatórios.")
    identificador = datetime.now(FUSO_MANAUS).strftime("lote_%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    lote = Path(destino) / identificador
    lote.mkdir(parents=True, exist_ok=False)
    ambiente = coletar_ambiente(tamanhos, seed, repeticoes)
    ambiente.update(lote=identificador, estado="em_andamento", execucoes=[])
    metadados = lote / "ambiente.json"
    with metadados.open("x", encoding="utf-8") as arquivo:
        json.dump(ambiente, arquivo, ensure_ascii=False, indent=2)

    def atualizar():
        # Este arquivo pertence ao lote recém-reservado, nunca a uma coleta anterior.
        with metadados.open("w", encoding="utf-8") as arquivo:
            json.dump(ambiente, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")

    try:
        for indice in range(1, repeticoes + 1):
            execucao = {"id": f"execucao_{indice:02d}", "inicio": agora(),
                        "estado": "em_andamento"}
            ambiente["execucoes"].append(execucao)
            atualizar()
            resultados = executar_experimentos(tamanhos, seed)
            conferir_execucao(resultados, tamanhos, seed)
            destino_csv = exportar_csv(resultados, lote / f"{execucao['id']}.csv")
            execucao.update(arquivo=destino_csv.name, linhas=len(resultados), fim=agora(),
                            estado="concluida", sha256=sha256(destino_csv),
                            limitacoes=sorted({r.limitacoes for r in resultados if r.limitacoes}))
            atualizar()
        ambiente.update(estado="concluido", fim=agora(),
                        linhas_totais=sum(e["linhas"] for e in ambiente["execucoes"]))
    except BaseException as erro:
        if ambiente["execucoes"]:
            ambiente["execucoes"][-1].update(estado="falhou", erro=f"{type(erro).__name__}: {erro}")
        ambiente.update(estado="falhou", fim=agora(), erro=f"{type(erro).__name__}: {erro}")
        raise
    finally:
        atualizar()
    return lote


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tamanhos", nargs="+", type=int, default=TAMANHOS_PADRAO)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeticoes", type=int, default=5)
    parser.add_argument("--destino", default="resultados/execucoes")
    args = parser.parse_args()
    try:
        lote = executar_lote(args.tamanhos, args.seed, args.repeticoes, args.destino)
    except Exception as erro:
        parser.exit(1, f"Coleta não concluída: {erro}\n")
    print(f"Coleta concluída. CSVs e ambiente: {lote}")


if __name__ == "__main__":
    main()
