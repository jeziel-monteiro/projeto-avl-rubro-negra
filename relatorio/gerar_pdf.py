"""Gera o relatório PDF a partir da fonte Markdown e das figuras publicadas.

Dependência de autoria: pip install -r relatorio/requirements.txt
Execução na raiz: python relatorio/gerar_pdf.py
Não executa experimentos nem modifica as medições.
"""

from __future__ import annotations

import argparse
from html import escape
import os
from pathlib import Path
import re
import tempfile

try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
        Paragraph, Preformatted, Spacer, Table, TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
except ImportError as erro:
    raise SystemExit(
        "Instale a dependência do relatório: "
        "python -m pip install -r relatorio/requirements.txt"
    ) from erro


PASTA = Path(__file__).resolve().parent
AZUL = colors.HexColor("#173d59")
CINZA = colors.HexColor("#4b5965")
LARGURA, ALTURA = A4
MARGEM = 20 * mm
LARGURA_TEXTO = LARGURA - 2 * MARGEM
ALTURA_TEXTO = ALTURA - 42 * mm
PADRAO_INLINE = re.compile(
    r"`([^`]+)`|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|\*([^*]+)\*"
)


def registrar_fontes() -> None:
    """Usa fontes distribuídas com ReportLab, sem depender das fontes do SO."""
    fontes = Path(reportlab.__file__).resolve().parent / "fonts"
    for nome, arquivo in (
        ("Texto", "Vera.ttf"), ("TextoNegrito", "VeraBd.ttf"),
        ("TextoItalico", "VeraIt.ttf"), ("TextoNegritoItalico", "VeraBI.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(nome, str(fontes / arquivo)))
    pdfmetrics.registerFontFamily(
        "Texto", normal="Texto", bold="TextoNegrito", italic="TextoItalico",
        boldItalic="TextoNegritoItalico",
    )


def normalizar(texto: str) -> str:
    """Mantém fórmulas e pontuação legíveis nas fontes do PDF."""
    return (texto.replace("\u2011", "-").replace("\u2013", "-")
            .replace("\u2014", "-").replace("\u2212", "-")
            .replace("\u2192", "->").replace("\u2264", "<=")
            .replace("\u2265", ">=").replace("\u2082", "2"))


def inline(texto: str) -> str:
    partes = []
    fim = 0
    for trecho in PADRAO_INLINE.finditer(normalizar(texto)):
        partes.append(escape(normalizar(texto)[fim:trecho.start()]))
        codigo, negrito, rotulo, destino, italico = trecho.groups()
        if codigo is not None:
            partes.append(f'<font name="Courier">{escape(codigo)}</font>')
        elif negrito is not None:
            partes.append(f"<b>{escape(negrito)}</b>")
        elif rotulo is not None:
            if destino.startswith(("https://", "http://")):
                partes.append(
                    f'<link href="{escape(destino, quote=True)}" '
                    f'color="#173d59">{escape(rotulo)}</link>'
                )
            else:
                partes.append(escape(rotulo))
        else:
            partes.append(f"<i>{escape(italico)}</i>")
        fim = trecho.end()
    partes.append(escape(normalizar(texto)[fim:]))
    return "".join(partes)


def estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "Corpo", fontName="Texto", fontSize=10.5, leading=15.5,
        alignment=TA_JUSTIFY, spaceAfter=7, allowWidows=0, allowOrphans=0,
        textColor=colors.HexColor("#18232c"), splitLongWords=True,
    )
    return {
        "corpo": base,
        "titulo": ParagraphStyle(
            "Titulo", parent=base, fontName="TextoNegrito", fontSize=25,
            leading=32, textColor=AZUL, alignment=TA_LEFT, spaceAfter=22,
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo", parent=base, fontSize=12, leading=18,
            textColor=CINZA, alignment=TA_LEFT, spaceAfter=14,
        ),
        "secao": ParagraphStyle(
            "Secao", parent=base, fontName="TextoNegrito", fontSize=15,
            leading=21, textColor=AZUL, spaceBefore=16, spaceAfter=10,
            keepWithNext=True, alignment=TA_LEFT,
        ),
        "subsecao": ParagraphStyle(
            "Subsecao", parent=base, fontName="TextoNegrito", fontSize=11.5,
            leading=16, textColor=AZUL, spaceBefore=11, spaceAfter=6,
            keepWithNext=True, alignment=TA_LEFT,
        ),
        "lista": ParagraphStyle(
            "Lista", parent=base, leftIndent=15, bulletIndent=0,
            alignment=TA_LEFT, spaceAfter=5,
        ),
        "celula": ParagraphStyle(
            "Celula", parent=base, fontSize=8.4, leading=11.5,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "cabecalho": ParagraphStyle(
            "Cabecalho", parent=base, fontName="TextoNegrito", fontSize=8.4,
            leading=11.5, alignment=TA_LEFT, textColor=colors.white, spaceAfter=0,
        ),
        "legenda": ParagraphStyle(
            "Legenda", parent=base, fontSize=9, leading=12.5,
            alignment=TA_CENTER, textColor=CINZA, spaceAfter=10,
        ),
    }


class RelatorioPDF(BaseDocTemplate):
    def __init__(self, caminho: Path, estilos_pdf: dict[str, ParagraphStyle],
                 autores: str = ""):
        super().__init__(
            str(caminho), pagesize=A4, leftMargin=MARGEM, rightMargin=MARGEM,
            topMargin=22 * mm, bottomMargin=20 * mm,
            title="Árvores balanceadas no cadastro de pacientes - AED II",
            author=autores, subject="Comparação das implementações AVL e Rubro-Negra",
        )
        self.estilos_pdf = estilos_pdf
        quadro = Frame(
            MARGEM, 20 * mm, LARGURA_TEXTO, ALTURA_TEXTO,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate("Relatorio", [quadro], self.pagina))

    @staticmethod
    def pagina(tela, documento) -> None:
        tela.saveState()
        if documento.page > 1:
            tela.setFont("Texto", 8)
            tela.setFillColor(CINZA)
            tela.drawString(MARGEM, ALTURA - 13 * mm, "AED II | Clínica / Atendimento")
            tela.setStrokeColor(colors.HexColor("#d1dce4"))
            tela.line(MARGEM, ALTURA - 16 * mm, LARGURA - MARGEM, ALTURA - 16 * mm)
            tela.drawRightString(
                LARGURA - MARGEM, 11 * mm, f"Página {documento.page}"
            )
        tela.restoreState()

    def afterFlowable(self, elemento) -> None:
        if hasattr(elemento, "entrada_sumario"):
            nivel, titulo, chave = elemento.entrada_sumario
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(titulo, chave, level=nivel, closed=False)
            if nivel == 0:
                self.notify("TOCEntry", (0, titulo, self.page, chave))


def celulas(linha: str) -> list[str]:
    return [c.strip().replace("\\|", "|")
            for c in re.split(r"(?<!\\)\|", linha.strip().strip("|"))]


def tabela(linhas: list[str], css: dict[str, ParagraphStyle]) -> Table:
    valores = [celulas(linha) for linha in linhas]
    quantidade = len(valores[0])
    if any(len(linha) != quantidade for linha in valores):
        raise ValueError("Tabela Markdown contém linhas com quantidades diferentes de colunas.")
    pesos = []
    for coluna in range(quantidade):
        textos = [linha[coluna] for linha in valores]
        numerica = all(re.fullmatch(r"[\d.,% /+−-]+|—|–|", t) for t in textos[1:])
        pesos.append(9 if numerica else min(32, max(12, max(map(len, textos)) ** 0.8)))
    larguras = [LARGURA_TEXTO * peso / sum(pesos) for peso in pesos]
    dados = [
        [Paragraph(inline(valor), css["cabecalho" if indice == 0 else "celula"])
         for valor in linha]
        for indice, linha in enumerate(valores)
    ]
    elemento = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    elemento.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f1f5f8"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, AZUL),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#d4dee6")),
    ]))
    elemento.spaceAfter = 12
    return elemento


def inicia_bloco(linha: str) -> bool:
    return bool(
        re.match(r"^#{1,4} |^```|^!\[|^\s*[-*] |^\s*\d+\. |^<!-- quebra-de-pagina -->$", linha)
        or linha.lstrip().startswith("|")
    )


def corpo_markdown(linhas: list[str], fonte: Path, css: dict) -> list:
    historia = []
    indice = 0
    while indice < len(linhas):
        linha = linhas[indice].strip()
        if not linha or linha in ("---", "***"):
            indice += 1
            continue
        if linha == "<!-- quebra-de-pagina -->":
            historia.append(PageBreak())
            indice += 1
            continue
        titulo = re.match(r"^(#{2,4})\s+(.+)", linha)
        if titulo:
            nivel = 0 if len(titulo[1]) == 2 else 1
            estilo = css["secao" if nivel == 0 else "subsecao"]
            paragrafo = Paragraph(inline(titulo[2]), estilo)
            paragrafo.entrada_sumario = (
                nivel, normalizar(titulo[2]), f"secao-{indice}"
            )
            historia.append(paragrafo)
            indice += 1
            continue
        if linha.startswith("```"):
            indice += 1
            codigo = []
            while indice < len(linhas) and not linhas[indice].startswith("```"):
                codigo.append(normalizar(linhas[indice].rstrip()))
                indice += 1
            if indice == len(linhas):
                raise ValueError("Bloco de código sem fechamento na fonte Markdown.")
            maior = max((len(item) for item in codigo), default=1)
            tamanho = min(9, (LARGURA_TEXTO - 18) / (0.6 * maior))
            if tamanho < 7:
                raise ValueError("Linha de código longa demais; divida-a na fonte Markdown.")
            estilo_codigo = ParagraphStyle(
                "Codigo", fontName="Courier", fontSize=tamanho,
                leading=tamanho * 1.35, backColor=colors.HexColor("#f1f5f8"),
                borderPadding=8, spaceBefore=5, spaceAfter=12,
            )
            bloco = [Preformatted("\n".join(codigo), estilo_codigo)]
            if historia and isinstance(historia[-1], Paragraph):
                bloco.insert(0, historia.pop())
            while (historia and isinstance(historia[-1], Paragraph)
                   and historia[-1].getKeepWithNext()):
                bloco.insert(0, historia.pop())
            historia.append(KeepTogether(bloco))
            indice += 1
            continue
        imagem = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", linha)
        if imagem:
            caminho = (fonte.parent / imagem[2]).resolve()
            if not caminho.is_file():
                raise FileNotFoundError(f"Figura não encontrada: {caminho}")
            figura = Image(str(caminho))
            escala = min(LARGURA_TEXTO / figura.imageWidth,
                         (ALTURA_TEXTO - 55) / figura.imageHeight)
            figura.drawWidth = figura.imageWidth * escala
            figura.drawHeight = figura.imageHeight * escala
            legenda = Paragraph(inline(imagem[1]), css["legenda"])
            historia.append(KeepTogether([figura, Spacer(1, 7), legenda]))
            indice += 1
            continue
        if linha.startswith("|"):
            trechos = [linhas[indice]]
            indice += 1
            if indice >= len(linhas) or not re.fullmatch(r"[\s|:\-]+", linhas[indice]):
                raise ValueError("Tabela sem linha de separação do cabeçalho.")
            indice += 1
            while indice < len(linhas) and linhas[indice].lstrip().startswith("|"):
                trechos.append(linhas[indice])
                indice += 1
            bloco = [tabela(trechos, css)]
            if historia and isinstance(historia[-1], Paragraph):
                bloco.insert(0, historia.pop())
            while (historia and isinstance(historia[-1], Paragraph)
                   and historia[-1].getKeepWithNext()):
                bloco.insert(0, historia.pop())
            historia.append(KeepTogether(bloco))
            continue
        item = re.match(r"^(?:([-*])|(\d+)\.)\s+(.+)", linha)
        if item:
            texto = [item[3]]
            indice += 1
            while indice < len(linhas) and linhas[indice].strip() and not inicia_bloco(linhas[indice]):
                texto.append(linhas[indice].strip())
                indice += 1
            historia.append(Paragraph(
                inline(" ".join(texto)), css["lista"],
                bulletText=f"{item[2]}." if item[2] else "-",
            ))
            continue
        texto = [linha]
        indice += 1
        while indice < len(linhas) and linhas[indice].strip() and not inicia_bloco(linhas[indice]):
            texto.append(linhas[indice].strip())
            indice += 1
        paragrafo = Paragraph(inline(" ".join(texto)), css["corpo"])
        if texto[-1].endswith(":"):
            paragrafo.keepWithNext = True
        historia.append(paragrafo)
    return historia


def gerar_pdf(fonte: Path, saida: Path) -> Path:
    if saida.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de saída deve ter extensão .pdf.")
    registrar_fontes()
    css = estilos()
    linhas = fonte.read_text(encoding="utf-8").splitlines()
    inicio_corpo = next((i for i, linha in enumerate(linhas) if linha.startswith("## ")), None)
    if inicio_corpo is None:
        raise ValueError("A fonte precisa conter seções com títulos de nível 2.")
    titulo = next((linha[2:] for linha in linhas[:inicio_corpo] if linha.startswith("# ")),
                  "Árvores balanceadas no cadastro de pacientes")
    linha_autores = next(
        (linha.removeprefix("Autores:").strip() for linha in linhas[:inicio_corpo]
         if linha.startswith("Autores:")), ""
    )
    autores = [nome.strip() for nome in linha_autores.split(";") if nome.strip()]
    prefacio = " ".join(linha.strip() for linha in linhas[1:inicio_corpo]
                        if linha.strip() and not linha.startswith("Autores:"))
    historia = [
        Spacer(1, 30 * mm),
        Paragraph("RELATÓRIO TÉCNICO", css["subtitulo"]),
        Spacer(1, 12 * mm), Paragraph(inline(titulo), css["titulo"]),
        Paragraph(inline(prefacio), css["subtitulo"]),
    ]
    if autores:
        historia.extend([
            Spacer(1, 18 * mm), Paragraph("Autores", css["subsecao"]),
            Paragraph("<br/>".join(inline(nome) for nome in autores), css["subtitulo"]),
        ])
    historia.extend([PageBreak(), Paragraph("Sumário", css["secao"])])
    sumario = TableOfContents()
    sumario.levelStyles = [ParagraphStyle(
        "Sumario", parent=css["corpo"], alignment=TA_LEFT,
        leading=22, spaceBefore=6, spaceAfter=6,
    )]
    historia.extend([sumario, PageBreak()])
    historia.extend(corpo_markdown(linhas[inicio_corpo:], fonte, css))
    saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = tempfile.NamedTemporaryFile(
        prefix=".relatorio_", suffix=".pdf", dir=saida.parent, delete=False
    )
    caminho_temporario = Path(temporario.name)
    temporario.close()
    try:
        documento = RelatorioPDF(caminho_temporario, css, "; ".join(autores))
        documento.multiBuild(historia)
        os.replace(caminho_temporario, saida)
    finally:
        caminho_temporario.unlink(missing_ok=True)
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonte", type=Path, default=PASTA / "relatorio_final.md")
    parser.add_argument("--saida", type=Path, default=PASTA / "relatorio_final.pdf")
    args = parser.parse_args()
    try:
        saida = gerar_pdf(args.fonte.resolve(), args.saida.resolve())
    except (OSError, ValueError) as erro:
        parser.exit(1, f"Não foi possível gerar o relatório: {erro}\n")
    print(f"Relatório gerado: {saida}")


if __name__ == "__main__":
    main()
