"""Verificação dos cenários com objetos exclusivos dos testes, sem resultados publicados."""

from contextlib import redirect_stderr
import csv
from dataclasses import fields
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experimentos import (
    Resultado, executar_experimentos, exportar_csv, main, preparar_cenarios,
)
from integracao import ErroIntegracao
from modelos import Paciente
from tests.apoio import ArvoreTeste, fabricas_teste


class TestExperimentos(unittest.TestCase):
    def test_preparacao_reproduzivel_e_mesmo_conjunto(self):
        cenarios = preparar_cenarios(10, seed=7)
        self.assertEqual(cenarios, preparar_cenarios(10, seed=7))
        self.assertEqual([p.prontuario for p in cenarios.crescente], list(range(1, 11)))
        self.assertEqual(set(cenarios.crescente), set(cenarios.aleatoria))
        self.assertEqual(set(cenarios.buscas_existentes), set(range(1, 11)))
        self.assertTrue(set(cenarios.buscas_inexistentes).isdisjoint(cenarios.buscas_existentes))
        for percentual, chaves in cenarios.remocoes.items():
            self.assertEqual(len(chaves), 10 * percentual // 100)
        with self.assertRaises(ValueError):
            preparar_cenarios(0)

    def test_mesmas_sequencias_e_instancias_independentes(self):
        fabricas, instancias = fabricas_teste()
        resultados = executar_experimentos((10,), seed=7, fabricas=fabricas)
        self.assertEqual(len(resultados), 14)
        self.assertEqual(len(instancias["AVL"]), 6)
        todas = instancias["AVL"] + instancias["Rubro-Negra"]
        self.assertEqual(len({id(a) for a in todas}), 12)
        for avl, rn in zip(instancias["AVL"], instancias["Rubro-Negra"]):
            self.assertEqual(avl.chamadas, rn.chamadas)
            self.assertFalse(avl.detalhado)
            self.assertFalse(rn.detalhado)
        self.assertEqual(instancias["AVL"][0].chamadas,
                         [("inserir", chave) for chave in range(1, 11)])
        for indice, removidos in ((3, 1), (4, 3), (5, 5)):
            arvore = instancias["AVL"][indice]
            self.assertEqual(sum(acao == "inserir" for acao, _ in arvore.chamadas), 10)
            self.assertEqual(sum(acao == "remover" for acao, _ in arvore.chamadas), removidos)
            self.assertEqual(arvore.quantidade(), 10 - removidos)

    def test_metricas_isoladas_e_tempos_do_cronometro(self):
        fabricas, _ = fabricas_teste()
        with patch("experimentos.perf_counter", side_effect=range(28)):
            resultados = executar_experimentos((10,), fabricas=fabricas)
        for resultado in resultados:
            self.assertEqual(resultado.tempo_segundos, 1)
            self.assertTrue(resultado.valido)
            self.assertIsNone(resultado.recoloracoes)
            if resultado.experimento.startswith("C_"):
                self.assertEqual(resultado.media_nos_visitados, 2)
                self.assertIsNone(resultado.rotacoes)
            else:
                self.assertEqual(resultado.rotacoes, resultado.operacoes)
                self.assertIsNone(resultado.media_nos_visitados)
                operacao = "remocao" if resultado.experimento.startswith("D_") else "insercao"
                self.assertIn(f"recoloracoes_{operacao} indisponível", resultado.limitacoes)

    def test_contadores_da_validacao_ficam_fora_da_metrica(self):
        class ValidacaoComContagem(ArvoreTeste):
            def validar(self):
                self.contadores["nos_visitados_ultima_busca"] += 10000
                return True

        resultados = executar_experimentos((4,), fabricas=dict.fromkeys(
            ("AVL", "Rubro-Negra"), ValidacaoComContagem))
        for resultado in resultados:
            if resultado.experimento.startswith("C_"):
                self.assertEqual(resultado.media_nos_visitados, 2)

    def test_estatisticas_ausentes_ficam_em_branco(self):
        class SemEstatisticas(ArvoreTeste):
            estatisticas = None
            reiniciar_estatisticas = None

        resultados = executar_experimentos((3,), fabricas=dict.fromkeys(
            ("AVL", "Rubro-Negra"), SemEstatisticas))
        for resultado in resultados:
            self.assertIsNone(resultado.rotacoes)
            self.assertIsNone(resultado.recoloracoes)
            self.assertIsNone(resultado.media_nos_visitados)
            self.assertIn("estatisticas() indisponível", resultado.limitacoes)

    def test_sem_reset_usa_incrementos_em_vez_de_acumulados(self):
        class SemReset(ArvoreTeste):
            reiniciar_estatisticas = None

        resultados = executar_experimentos((10,), fabricas=dict.fromkeys(
            ("AVL", "Rubro-Negra"), SemReset))
        for resultado in resultados:
            self.assertIn("reiniciar_estatisticas() indisponível", resultado.limitacoes)
            if not resultado.experimento.startswith("C_"):
                self.assertIn("usando diferenças", resultado.limitacoes)
            if resultado.experimento.startswith("D_"):
                self.assertEqual(resultado.rotacoes, resultado.operacoes)
            elif resultado.experimento.startswith("C_"):
                self.assertEqual(resultado.media_nos_visitados, 2)

    def test_metricas_invalidas_nao_viram_numeros(self):
        class MetricasInvalidas(ArvoreTeste):
            def estatisticas(self):
                return {"rotacoes_insercao": True, "rotacoes_remocao": True,
                        "recoloracoes_insercao": "0", "recoloracoes_remocao": "0",
                        "nos_visitados_ultima_busca": -1}

        resultados = executar_experimentos((2,), fabricas=dict.fromkeys(
            ("AVL", "Rubro-Negra"), MetricasInvalidas))
        for resultado in resultados:
            self.assertIsNone(resultado.rotacoes)
            self.assertIsNone(resultado.recoloracoes)
            self.assertIsNone(resultado.media_nos_visitados)
            if resultado.experimento.startswith("C_"):
                self.assertIn("inteiro não negativo válido", resultado.limitacoes)
            else:
                self.assertIn("contador acumulado válido", resultado.limitacoes)

    def test_exportacao_csv(self):
        fabricas, _ = fabricas_teste()
        resultados = executar_experimentos((4,), fabricas=fabricas)
        with TemporaryDirectory() as pasta:
            destino = exportar_csv(resultados, Path(pasta) / "resultados" / "teste.csv")
            with destino.open(encoding="utf-8", newline="") as arquivo:
                leitor = csv.DictReader(arquivo)
                linhas = list(leitor)
                self.assertEqual(leitor.fieldnames, [campo.name for campo in fields(Resultado)])
            self.assertEqual(len(linhas), 14)
            self.assertEqual(linhas[0]["recoloracoes"], "")
            self.assertEqual(linhas[0]["media_nos_visitados"], "")
            self.assertEqual(linhas[0]["valido"], "True")
            self.assertIn("indisponível", linhas[0]["limitacoes"])

    def test_coleta_de_visitas_e_validacao_ficam_fora_do_cronometro(self):
        estado = {"medindo": False, "tempo": 0}
        fases_busca = []
        teste = self

        def cronometro():
            estado["medindo"] = not estado["medindo"]
            estado["tempo"] += 1
            return estado["tempo"]

        class Instrumentada(ArvoreTeste):
            def buscar(self, prontuario):
                fases_busca.append(estado["medindo"])
                return super().buscar(prontuario)

            def estatisticas(self):
                teste.assertFalse(estado["medindo"])
                return super().estatisticas()

            def validar(self):
                teste.assertFalse(estado["medindo"])
                return super().validar()

        with patch("experimentos.perf_counter", side_effect=cronometro):
            resultados = executar_experimentos((3,), fabricas=dict.fromkeys(
                ("AVL", "Rubro-Negra"), Instrumentada))
        self.assertEqual(fases_busca.count(True), 12)
        self.assertEqual(fases_busca.count(False), 12)
        self.assertTrue(all(r.tempo_segundos == 1 for r in resultados))

    def test_segunda_passagem_rejeita_retornos_diferentes(self):
        class Instavel(ArvoreTeste):
            def __init__(self):
                super().__init__()
                self.buscas = 0

            def buscar(self, prontuario):
                self.buscas += 1
                paciente = super().buscar(prontuario)
                return paciente if self.buscas <= len(self.dados) else None

        with self.assertRaisesRegex(ErroIntegracao, "Retornos diferentes"):
            executar_experimentos((3,), fabricas=dict.fromkeys(
                ("AVL", "Rubro-Negra"), Instavel))

    def test_segunda_passagem_rejeita_alteracao_da_colecao(self):
        class AlteraNoFim(ArvoreTeste):
            def __init__(self):
                super().__init__()
                self.buscas = 0

            def buscar(self, prontuario):
                self.buscas += 1
                paciente = super().buscar(prontuario)
                if self.buscas == 2 * len(self.dados):
                    self.dados[prontuario] = Paciente(prontuario, "Alterado", "2000-01-01", "00")
                return paciente

        with self.assertRaisesRegex(ErroIntegracao, "coleção esperada"):
            executar_experimentos((3,), fabricas=dict.fromkeys(
                ("AVL", "Rubro-Negra"), AlteraNoFim))

    def test_visita_invalida_em_uma_busca_invalida_toda_a_media(self):
        for valor in (None, True, -1, "2", 2.0):
            with self.subTest(valor=valor):
                class VisitaInvalida(ArvoreTeste):
                    def buscar(self, prontuario):
                        paciente = super().buscar(prontuario)
                        if prontuario in (1, 4):
                            self.contadores["nos_visitados_ultima_busca"] = valor
                        return paciente

                resultados = executar_experimentos((3,), fabricas=dict.fromkeys(
                    ("AVL", "Rubro-Negra"), VisitaInvalida))
                for resultado in resultados:
                    if resultado.experimento.startswith("C_"):
                        self.assertIsNone(resultado.media_nos_visitados)
                        self.assertIn("nos_visitados_ultima_busca", resultado.limitacoes)

    def test_ausencia_de_modulos_e_cli_sem_csv(self):
        with patch("integracao.import_module", side_effect=ModuleNotFoundError("ausente")):
            with self.assertRaisesRegex(ErroIntegracao, "Experimentos indisponíveis"):
                executar_experimentos((3,))
            with TemporaryDirectory() as pasta:
                destino = Path(pasta) / "resultado.csv"
                with patch("sys.argv", ["experimentos.py", "--tamanhos", "3", "--saida", str(destino)]):
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as erro:
                        main()
                    self.assertEqual(erro.exception.code, 1)
                    self.assertFalse(destino.exists())
        with self.assertRaises(ErroIntegracao):
            executar_experimentos((3,), fabricas={"AVL": ArvoreTeste})

    def test_rejeita_arvore_invalida_apos_operacoes(self):
        class InvalidaDepoisDeInserir(ArvoreTeste):
            def validar(self):
                return not self.dados

        with self.assertRaisesRegex(ErroIntegracao, "propriedades"):
            executar_experimentos((3,), fabricas=dict.fromkeys(
                ("AVL", "Rubro-Negra"), InvalidaDepoisDeInserir))

    def test_busca_incorreta_rejeitada_mesmo_com_mesma_chave(self):
        class BuscaIncorreta(ArvoreTeste):
            def buscar(self, prontuario):
                paciente = super().buscar(prontuario)
                if paciente is not None:
                    return Paciente(prontuario, "Outro nome", paciente.data_nascimento, "00")
                return None

        with self.assertRaisesRegex(ErroIntegracao, "retornos incorretos"):
            executar_experimentos((3,), fabricas={"AVL": ArvoreTeste,
                                                  "Rubro-Negra": BuscaIncorreta})

    def test_rejeita_fabricas_que_compartilham_instancia(self):
        arvore = ArvoreTeste()
        with self.assertRaisesRegex(ErroIntegracao, "independentes"):
            executar_experimentos((3,), fabricas=dict.fromkeys(
                ("AVL", "Rubro-Negra"), lambda: arvore))

    def test_tamanhos_e_semente_invalidos(self):
        for tamanhos in ((), (0,), (-1,), (True,), (1.5,)):
            with self.subTest(tamanhos=tamanhos), self.assertRaises(ValueError):
                executar_experimentos(tamanhos, fabricas={})
        with self.assertRaises(TypeError):
            executar_experimentos((3,), seed=True, fabricas={})


if __name__ == "__main__":
    unittest.main()
