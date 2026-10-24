"""Tabelas e gráficos reproduzíveis de um único lote de CSVs medidos."""

import argparse
from collections import defaultdict
import csv
from dataclasses import fields
import json
from math import isfinite
from pathlib import Path
from statistics import median

from coleta_experimentos import conferir_execucao, sha256
from experimentos import Resultado


ESTRUTURA = ("operacoes", "altura_inicial", "altura_final", "quantidade_final",
             "rotacoes", "recoloracoes", "media_nos_visitados", "valido")
ROTULOS = {
    "A_insercao_crescente": "A — Inserção crescente",
    "B_insercao_aleatoria": "B — Inserção aleatória",
    "C_busca_existente": "C — Busca existente",
    "C_busca_inexistente": "C — Busca inexistente",
    "D_remocao_10": "D — Remoção de 10%",
    "D_remocao_30": "D — Remoção de 30%",
    "D_remocao_50": "D — Remoção de 50%",
}
ARVORES = ("AVL", "Rubro-Negra")
OPCIONAIS = {"rotacoes", "recoloracoes", "media_nos_visitados"}
INTEIROS = {"quantidade_inicial", "operacoes", "seed", "altura_inicial",
            "altura_final", "quantidade_final", "rotacoes", "recoloracoes"}


def _ler_csv(caminho: Path) -> list[Resultado]:
    resultados = []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames != [c.name for c in fields(Resultado)]:
            raise ValueError(f"Esquema CSV incompatível: {caminho}")
        for linha in leitor:
            dados = {}
            for chave, valor in linha.items():
                if chave in OPCIONAIS and valor == "":
                    dados[chave] = None
                elif chave in INTEIROS:
                    dados[chave] = int(valor)
                elif chave in ("tempo_segundos", "media_nos_visitados"):
                    numero = float(valor)
                    if not isfinite(numero) or numero < 0:
                        raise ValueError(f"Métrica numérica inválida em {caminho}: {chave}")
                    dados[chave] = numero
                elif chave == "valido":
                    if valor != "True":
                        raise ValueError(f"Validação estrutural ausente ou falsa em {caminho}")
                    dados[chave] = True
                else:
                    dados[chave] = valor
            resultados.append(Resultado(**dados))
    return resultados


def carregar_lote(lote: str | Path) -> tuple[list[Resultado], dict]:
    """Usa apenas arquivos do manifesto, verificando integridade e completude."""
    lote = Path(lote)
    ambiente = json.loads((lote / "ambiente.json").read_text(encoding="utf-8"))
    execucoes = ambiente["execucoes"]
    if ambiente["estado"] != "concluido" or len(execucoes) != ambiente["repeticoes"]:
        raise ValueError("Lote incompleto; nenhuma análise estatística foi produzida.")
    if len({e["arquivo"] for e in execucoes}) != len(execucoes):
        raise ValueError("Manifesto repete o mesmo arquivo em execuções diferentes.")
    resultados = []
    for execucao in execucoes:
        nome = execucao["arquivo"]
        if Path(nome).name != nome:
            raise ValueError("O manifesto deve referenciar CSVs na própria pasta do lote.")
        caminho = lote / nome
        if execucao["estado"] != "concluida" or sha256(caminho) != execucao["sha256"]:
            raise ValueError(f"Execução incompleta ou hash divergente: {caminho}")
        linhas = _ler_csv(caminho)
        conferir_execucao(linhas, tuple(ambiente["tamanhos"]), ambiente["seed"])
        if len(linhas) != execucao["linhas"]:
            raise ValueError(f"Contagem de linhas divergente: {caminho}")
        resultados.extend(linhas)
    if len(resultados) != ambiente["linhas_totais"]:
        raise ValueError("Total de linhas incompatível com os metadados.")
    return resultados, ambiente


def resumir(resultados: list[Resultado], repeticoes: int) -> list[dict]:
    """Resume tempos em ms; exige métricas estruturais idênticas, inclusive None."""
    grupos = defaultdict(list)
    for resultado in resultados:
        grupos[(resultado.experimento, resultado.quantidade_inicial,
                resultado.arvore, resultado.seed)].append(resultado)
    resumo = []
    for (experimento, tamanho, arvore, seed), medicoes in sorted(grupos.items()):
        if len(medicoes) != repeticoes:
            raise ValueError("Quantidade de repetições divergente para um cenário.")
        for campo in ESTRUTURA:
            if len({getattr(r, campo) for r in medicoes}) != 1:
                raise ValueError(f"Métrica estrutural inconsistente: {experimento}, "
                                 f"{tamanho}, {arvore}, {campo}. Investigue as execuções.")
        tempos = [r.tempo_segundos * 1000 for r in medicoes]
        if any(not isfinite(t) or t < 0 for t in tempos):
            raise ValueError("Os tempos devem ser finitos e não negativos.")
        estrutura = {campo: getattr(medicoes[0], campo) for campo in ESTRUTURA}
        resumo.append({
            "experimento": experimento, "quantidade_inicial": tamanho,
            "arvore": arvore, "seed": seed,
            "ordem_insercao": "crescente" if experimento.startswith("A_") else "aleatoria",
            "percentual_remocao": int(experimento.rsplit("_", 1)[1])
                                  if experimento.startswith("D_") else None,
            **estrutura, "repeticoes": repeticoes,
            "mediana_ms": median(tempos), "minimo_ms": min(tempos),
            "maximo_ms": max(tempos), "variacao_absoluta_ms": max(tempos) - min(tempos),
            "limitacoes": "; ".join(sorted({r.limitacoes for r in medicoes if r.limitacoes})),
        })
    return resumo


def _formatar(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def _tabela_markdown(resumo: list[dict], colunas: dict[str, str], titulo: str) -> str:
    texto = [f"# {titulo}", "", "Valores ausentes ou não aplicáveis: —. "
             "Tempos em milissegundos; métricas estruturais conferidas entre repetições.", ""]
    for experimento, rotulo in ROTULOS.items():
        texto.extend([f"## {rotulo}", "", "| " + " | ".join(colunas.values()) + " |",
                      "| " + " | ".join("---" for _ in colunas) + " |"])
        for linha in resumo:
            if linha["experimento"] == experimento:
                texto.append("| " + " | ".join(_formatar(linha[c]) for c in colunas) + " |")
        texto.append("")
    return "\n".join(texto) + "\n"


def gerar_graficos(resumo: list[dict], destino: Path) -> list[Path]:
    """Importa matplotlib somente aqui; barras de erro representam mínimo–máximo."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cenarios = list(ROTULOS)
    configuracoes = (
        ("01_alturas_finais.png", "Alturas finais", "altura_final", cenarios, "Altura (níveis)"),
        ("02_rotacoes.png", "Rotações simples", "rotacoes", cenarios[:2] + cenarios[4:],
         "Rotações (contagem)"),
        ("03_recoloracoes.png", "Recolorações — AVL não utiliza recoloração (0)",
         "recoloracoes", cenarios[:2] + cenarios[4:], "Recolorações (contagem)"),
        ("04_visitas_buscas.png", "Nós visitados nas buscas", "media_nos_visitados",
         cenarios[2:4], "Média de nós por busca"),
        ("05_tempos_insercao.png", "Tempos de inserção — mediana e mínimo–máximo",
         "mediana_ms", cenarios[:2], "Tempo total do lote (ms)"),
        ("06_tempos_busca_remocao.png", "Tempos de busca e remoção — mediana e mínimo–máximo",
         "mediana_ms", cenarios[2:], "Tempo total do lote (ms)"),
    )
    caminhos = []
    for nome, titulo, metrica, experimentos, unidade in configuracoes:
        colunas = min(2, len(experimentos))
        linhas = (len(experimentos) + colunas - 1) // colunas
        figura, eixos = plt.subplots(linhas, colunas, figsize=(13, linhas * 3.8),
                                    squeeze=False)
        try:
            for eixo, experimento in zip(eixos.flat, experimentos):
                tamanhos = sorted({r["quantidade_inicial"] for r in resumo
                                   if r["experimento"] == experimento})
                for indice, arvore in enumerate(ARVORES):
                    pontos = [next(r for r in resumo if r["experimento"] == experimento
                                   and r["arvore"] == arvore and r["quantidade_inicial"] == n)
                              for n in tamanhos]
                    presentes = [(i, r) for i, r in enumerate(pontos) if r[metrica] is not None]
                    if not presentes:
                        continue
                    posicoes = [i + (indice - 0.5) * 0.36 for i, _ in presentes]
                    valores = [r[metrica] for _, r in presentes]
                    erros = None
                    if metrica == "mediana_ms":
                        erros = [[r[metrica] - r["minimo_ms"] for _, r in presentes],
                                 [r["maximo_ms"] - r[metrica] for _, r in presentes]]
                    eixo.bar(posicoes, valores, width=0.36, label=arvore, yerr=erros,
                             capsize=4, color=("#176b96", "#bc3b43")[indice])
                eixo.set_title(ROTULOS[experimento])
                eixo.set_xticks(range(len(tamanhos)), [f"{n:,}".replace(",", ".") for n in tamanhos])
                eixo.set_xlabel("Quantidade inicial de pacientes")
                eixo.set_ylabel(unidade)
                eixo.set_ylim(bottom=0)
                eixo.grid(axis="y", alpha=0.25)
                eixo.set_axisbelow(True)
                eixo.legend()
            for eixo in list(eixos.flat)[len(experimentos):]:
                eixo.set_visible(False)
            figura.suptitle(titulo, fontsize=14)
            figura.tight_layout(rect=(0, 0, 1, 0.96))
            caminho = destino / nome
            with caminho.open("xb") as arquivo:
                figura.savefig(arquivo, format="png", dpi=160)
            caminhos.append(caminho)
        finally:
            plt.close(figura)
    return caminhos


def gerar_analise(lote: str | Path, destino: str | Path = "resultados",
                  graficos: bool = True) -> tuple[Path, Path]:
    """Gera artefatos novos; recusa diretórios de análise previamente existentes."""
    lote, destino = Path(lote), Path(destino)
    resultados, ambiente = carregar_lote(lote)
    resumo = resumir(resultados, ambiente["repeticoes"])
    tabelas = destino / "tabelas" / lote.name
    imagens = destino / "graficos" / lote.name
    if tabelas.exists() or imagens.exists():
        raise FileExistsError("Análise já existente. Use --saida com outra pasta para preservá-la.")
    if graficos:
        try:
            import matplotlib
        except ImportError as erro:
            raise RuntimeError("Instale matplotlib para gerar PNGs, ou use --sem-graficos.") from erro
    tabelas.mkdir(parents=True, exist_ok=False)
    imagens.mkdir(parents=True, exist_ok=False)
    with (tabelas / "resumo.csv").open("x", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(resumo[0]))
        escritor.writeheader()
        escritor.writerows(resumo)
    comum = {"quantidade_inicial": "Pacientes", "arvore": "Árvore"}
    estrutura = comum | {"operacoes": "Operações", "quantidade_final": "Restantes",
                         "altura_inicial": "Altura inicial", "altura_final": "Altura final",
                         "rotacoes": "Rotações", "recoloracoes": "Recolorações",
                         "media_nos_visitados": "Média de visitas"}
    tempos = comum | {"repeticoes": "Repetições", "mediana_ms": "Mediana (ms)",
                      "minimo_ms": "Mínimo (ms)", "maximo_ms": "Máximo (ms)",
                      "variacao_absoluta_ms": "Amplitude (ms)"}
    for nome, colunas, titulo in (("estruturas.md", estrutura, "Métricas estruturais"),
                                  ("tempos.md", tempos, "Tempos das execuções")):
        with (tabelas / nome).open("x", encoding="utf-8") as arquivo:
            arquivo.write(_tabela_markdown(resumo, colunas, titulo))
    caminhos = gerar_graficos(resumo, imagens) if graficos else []
    verificacao = {
        "lote": lote.name, "linhas_brutas": len(resultados), "grupos": len(resumo),
        "repeticoes": ambiente["repeticoes"], "metricas_estruturais_consistentes": True,
        "execucoes": [{"arquivo": e["arquivo"], "sha256": e["sha256"]}
                      for e in ambiente["execucoes"]],
        "campos_ausentes_por_metrica": {c: sum(getattr(r, c) is None for r in resultados)
                                       for c in OPCIONAIS},
        "limitacoes": sorted({r.limitacoes for r in resultados if r.limitacoes}),
        "graficos": [c.name for c in caminhos],
        "matplotlib": matplotlib.__version__ if graficos else None,
        "sha256_analise": sha256(Path(__file__)),
    }
    with (tabelas / "verificacao.json").open("x", encoding="utf-8") as arquivo:
        json.dump(verificacao, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")
    return tabelas, imagens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lote", type=Path)
    parser.add_argument("--saida", type=Path, default=Path("resultados"))
    parser.add_argument("--sem-graficos", action="store_true")
    args = parser.parse_args()
    try:
        tabelas, imagens = gerar_analise(args.lote, args.saida, not args.sem_graficos)
    except Exception as erro:
        parser.exit(1, f"Análise não concluída: {erro}\n")
    print(f"Tabelas: {tabelas}")
    if not args.sem_graficos:
        print(f"Gráficos PNG: {imagens}")


if __name__ == "__main__":
    main()
