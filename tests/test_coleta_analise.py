"""Coletas pequenas e artefatos temporários; sem medições definitivas na suíte."""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from analise_experimentos import _ler_csv, carregar_lote, gerar_analise, resumir
from avl import ArvoreAVL
from coleta_experimentos import (
    coletar_ambiente, conferir_execucao, executar_lote, sha256, validar_resultado,
)
from experimentos import executar_experimentos, exportar_csv, preparar_cenarios
from rubro_negra import ArvoreRubroNegra


class TestAlturasReais(unittest.TestCase):
    def test_alturas_em_todos_os_cenarios_e_csv(self):
        resultados = executar_experimentos((20,), seed=42)
        cenarios = preparar_cenarios(20, 42)
        fabricas = {"AVL": ArvoreAVL, "Rubro-Negra": ArvoreRubroNegra}
        for r in resultados:
            with self.subTest(arvore=r.arvore, experimento=r.experimento):
                if r.experimento.startswith(("A_", "B_")):
                    self.assertEqual(r.altura_inicial, 0)
                    self.assertGreater(r.altura_final, 0)
                    continue
                arvore = fabricas[r.arvore]()
                for paciente in cenarios.aleatoria:
                    arvore.inserir(paciente)
                self.assertEqual(r.altura_inicial, arvore.altura())
                if r.experimento.startswith("C_"):
                    self.assertEqual(r.altura_final, r.altura_inicial)
                else:
                    percentual = int(r.experimento.rsplit("_", 1)[1])
                    for chave in cenarios.remocoes[percentual]:
                        arvore.remover(chave)
                    self.assertEqual(r.altura_final, arvore.altura())
                    self.assertEqual(r.quantidade_final, 20 - 20 * percentual // 100)
        with TemporaryDirectory() as pasta:
            caminho = exportar_csv(resultados, Path(pasta) / "alturas.csv")
            texto = caminho.read_text(encoding="utf-8")
            self.assertIn("altura_inicial,altura_final", texto.splitlines()[0])
            self.assertEqual(_ler_csv(caminho), resultados)

    def test_exportacao_recusa_sobrescrita_preservando_bytes(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "anterior.csv"
            anterior = b"resultado historico\n"
            caminho.write_bytes(anterior)
            with self.assertRaises(FileExistsError):
                exportar_csv([], caminho)
            self.assertEqual(caminho.read_bytes(), anterior)


class TestColeta(unittest.TestCase):
    def test_cinco_execucoes_separadas_metadados_e_novo_lote(self):
        with TemporaryDirectory() as pasta:
            lote = executar_lote((10,), 42, 5, pasta)
            resultados, ambiente = carregar_lote(lote)
            self.assertEqual(len(resultados), 70)
            self.assertEqual(ambiente["linhas_totais"], 70)
            self.assertEqual(ambiente["seed"], 42)
            self.assertEqual(ambiente["tamanhos"], [10])
            self.assertEqual(ambiente["repeticoes"], 5)
            self.assertEqual(len(list(lote.glob("execucao_*.csv"))), 5)
            anteriores = {p.name: p.read_bytes() for p in lote.iterdir()}
            outro = executar_lote((10,), 42, 1, pasta)
            self.assertNotEqual(lote, outro)
            self.assertEqual(anteriores, {p.name: p.read_bytes() for p in lote.iterdir()})
            for campo in ("python", "sistema_operacional", "versao_sistema", "arquitetura",
                          "processador", "inicio", "fim", "comando", "commit_git",
                          "branch_git", "sha256_codigo", "cronometro"):
                self.assertIn(campo, ambiente)
            for indice, execucao in enumerate(ambiente["execucoes"], 1):
                self.assertEqual(execucao["arquivo"], f"execucao_{indice:02d}.csv")
                self.assertEqual(execucao["linhas"], 14)
                self.assertEqual(execucao["sha256"], sha256(lote / execucao["arquivo"]))
            resumo = resumir(resultados, 5)
            self.assertEqual(len(resumo), 14)

    def test_instancias_nao_compartilham_estado_entre_repeticoes(self):
        originais = executar_experimentos
        registros = []

        class AVLRegistrada(ArvoreAVL):
            def __init__(self):
                super().__init__()
                registros.append(self)

        def executar(tamanhos, seed):
            return originais(tamanhos, seed,
                             {"AVL": AVLRegistrada, "Rubro-Negra": ArvoreRubroNegra})

        with TemporaryDirectory() as pasta, patch(
                "coleta_experimentos.executar_experimentos", side_effect=executar):
            executar_lote((10,), 42, 5, pasta)
        self.assertEqual(len(registros), 30)
        self.assertEqual(len({id(a) for a in registros}), 30)

    def test_hardware_ausente_e_explicitado(self):
        with patch("coleta_experimentos.platform.processor", return_value=""):
            ambiente = coletar_ambiente((10,), 42, 5)
        self.assertEqual(ambiente["processador"], "Não pôde ser identificado")

    def test_falha_fica_registrada_e_preserva_execucao_anterior(self):
        pequeno = executar_experimentos((10,), 42)
        with TemporaryDirectory() as pasta:
            with patch("coleta_experimentos.executar_experimentos",
                       side_effect=[pequeno, RuntimeError("falha controlada")]):
                with self.assertRaisesRegex(RuntimeError, "falha controlada"):
                    executar_lote((10,), 42, 5, pasta)
            lote = next(Path(pasta).iterdir())
            ambiente = json.loads((lote / "ambiente.json").read_text(encoding="utf-8"))
            self.assertEqual(ambiente["estado"], "falhou")
            self.assertEqual(ambiente["execucoes"][0]["estado"], "concluida")
            self.assertEqual(ambiente["execucoes"][1]["estado"], "falhou")
            self.assertEqual(len(list(lote.glob("execucao_*.csv"))), 1)
            with self.assertRaisesRegex(ValueError, "incompleto"):
                carregar_lote(lote)

    def test_rejeita_dados_adulterados(self):
        with TemporaryDirectory() as pasta:
            lote = executar_lote((10,), 42, 1, pasta)
            caminho = lote / "execucao_01.csv"
            with caminho.open("a", encoding="utf-8") as arquivo:
                arquivo.write("adulterado\n")
            with self.assertRaisesRegex(ValueError, "hash divergente"):
                carregar_lote(lote)

    def test_confere_completude_operacoes_e_invariantes(self):
        resultados = executar_experimentos((10,), 42)
        conferir_execucao(resultados, (10,), 42)
        for alterado in (resultados[:-1], [resultados[0]] * 14,
                         [replace(resultados[0], altura_inicial=1), *resultados[1:]],
                         [replace(resultados[0], tempo_segundos=float("nan")), *resultados[1:]]):
            with self.subTest(), self.assertRaises(ValueError):
                conferir_execucao(alterado, (10,), 42)

    def test_parametros_invalidos_nao_criam_lote(self):
        with TemporaryDirectory() as pasta:
            for tamanhos, seed, repeticoes in (((), 42, 5), ((10, 10), 42, 5),
                                              ((0,), 42, 5), ((10,), True, 5),
                                              ((10,), 42, 0), ((10,), 42, True)):
                with self.subTest(), self.assertRaises(ValueError):
                    executar_lote(tamanhos, seed, repeticoes, pasta)
            self.assertEqual(list(Path(pasta).iterdir()), [])


class TestAnalise(unittest.TestCase):
    def test_mediana_extremos_variacao_e_ausentes(self):
        original = executar_experimentos((1,), 42)[0]
        medicoes = [replace(original, tempo_segundos=t, recoloracoes=None)
                    for t in (0.003, 0.001, 0.005, 0.002, 0.004)]
        resumo = resumir(medicoes, 5)[0]
        self.assertEqual(resumo["mediana_ms"], 3)
        self.assertEqual(resumo["minimo_ms"], 1)
        self.assertEqual(resumo["maximo_ms"], 5)
        self.assertEqual(resumo["variacao_absoluta_ms"], 4)
        self.assertIsNone(resumo["recoloracoes"])
        self.assertEqual(resumo["rotacoes"], 0)
        self.assertIsNone(resumo["media_nos_visitados"])
        self.assertIsNone(resumo["percentual_remocao"])

    def test_inconsistencia_nao_e_ocultada_com_media(self):
        original = executar_experimentos((1,), 42)[0]
        for campo, valor in (("altura_final", 9), ("rotacoes", None), ("recoloracoes", 1)):
            with self.subTest(campo=campo), self.assertRaisesRegex(
                    ValueError, "Métrica estrutural inconsistente"):
                resumir([original, replace(original, **{campo: valor})], 2)
        with self.assertRaisesRegex(ValueError, "Quantidade de repetições"):
            resumir([original], 5)

    def test_tabelas_geradas_dos_csvs_e_sem_sobrescrita(self):
        with TemporaryDirectory() as pasta:
            lote = executar_lote((10,), 42, 5, Path(pasta) / "execucoes")
            saida = Path(pasta) / "analise"
            tabelas, _ = gerar_analise(lote, saida, graficos=False)
            texto = (tabelas / "tempos.md").read_text(encoding="utf-8")
            self.assertIn("Mediana (ms)", texto)
            self.assertIn("C — Busca inexistente", texto)
            self.assertIn("—", (tabelas / "estruturas.md").read_text(encoding="utf-8"))
            dados = json.loads((tabelas / "verificacao.json").read_text(encoding="utf-8"))
            self.assertEqual(dados["linhas_brutas"], 70)
            self.assertTrue(dados["metricas_estruturais_consistentes"])
            self.assertEqual(dados["campos_ausentes_por_metrica"]["rotacoes"], 20)
            anteriores = {p.name: p.read_bytes() for p in tabelas.iterdir()}
            with self.assertRaises(FileExistsError):
                gerar_analise(lote, saida, graficos=False)
            self.assertEqual(anteriores, {p.name: p.read_bytes() for p in tabelas.iterdir()})

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib opcional ausente")
    def test_seis_pngs_reais_a_partir_dos_csvs(self):
        with TemporaryDirectory() as pasta:
            lote = executar_lote((10, 20), 42, 1, Path(pasta) / "execucoes")
            _, imagens = gerar_analise(lote, Path(pasta) / "analise")
            graficos = list(imagens.glob("*.png"))
            self.assertEqual(len(graficos), 6)
            for grafico in graficos:
                dados = grafico.read_bytes()
                self.assertEqual(dados[:8], b"\x89PNG\r\n\x1a\n")
                largura, altura = struct.unpack(">II", dados[16:24])
                self.assertGreater(largura, 1000)
                self.assertGreater(altura, 500)


class TestValidacaoMetricas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultados = executar_experimentos((10,), 42)
        cls.original = cls.resultados[0]

    def conferir_rejeicao(self, **alteracoes):
        adulterado = replace(self.original, **alteracoes)
        with self.assertRaises(ValueError):
            conferir_execucao([adulterado, *self.resultados[1:]], (10,), 42)
        # Valores igualmente inválidos não podem passar pela checagem de consistência.
        with self.assertRaises(ValueError):
            resumir([adulterado, adulterado], 2)

    def test_alturas_quantidades_e_operacoes_exigem_inteiros_nao_negativos(self):
        for campo in ("altura_inicial", "altura_final", "quantidade_inicial",
                      "quantidade_final", "operacoes"):
            for valor in (-1, True, False, 1.0, "1", None, []):
                with self.subTest(campo=campo, valor=valor):
                    self.conferir_rejeicao(**{campo: valor})

    def test_contadores_opcionais_rejeitam_sinal_e_tipos_invalidos(self):
        for campo in ("rotacoes", "recoloracoes"):
            for valor in (-1, True, False, 0.0, "0", []):
                with self.subTest(campo=campo, valor=valor):
                    self.conferir_rejeicao(**{campo: valor})

    def test_tempo_e_visitas_exigem_numeros_finitos_nao_negativos(self):
        for campo in ("tempo_segundos", "media_nos_visitados"):
            for valor in (-0.1, True, False, "0", [], float("nan"),
                          float("inf"), -float("inf"), 10 ** 400):
                with self.subTest(campo=campo, valor=valor):
                    self.conferir_rejeicao(**{campo: valor})
        self.conferir_rejeicao(tempo_segundos=None)

    def test_alturas_e_quantidades_precisam_corresponder_ao_cenario(self):
        for alteracoes in ({"quantidade_inicial": 0}, {"altura_inicial": 1},
                           {"altura_final": 0}, {"altura_final": 11},
                           {"quantidade_final": 0}, {"quantidade_final": 9},
                           {"quantidade_final": 11}, {"operacoes": 0}):
            with self.subTest(alteracoes=alteracoes):
                self.conferir_rejeicao(**alteracoes)
        for experimento, alteracoes in (
            ("C_busca_existente", {"altura_inicial": 0, "altura_final": 0}),
            ("C_busca_existente", {"altura_final": 1}),
            ("C_busca_inexistente", {"quantidade_final": 9}),
            ("D_remocao_10", {"altura_inicial": 11}),
            ("D_remocao_10", {"operacoes": 0, "quantidade_final": 10}),
            ("D_remocao_50", {"quantidade_final": 0, "altura_final": 0}),
        ):
            original = next(r for r in self.resultados if r.experimento == experimento)
            adulterado = replace(original, **alteracoes)
            with self.subTest(experimento=experimento, alteracoes=alteracoes):
                with self.assertRaises(ValueError):
                    validar_resultado(adulterado)
                with self.assertRaises(ValueError):
                    resumir([adulterado, adulterado], 2)

    def test_none_e_zero_legitimos_preservados_inclusive_em_csv(self):
        original = executar_experimentos((1,), 42)[0]
        ausente = replace(original, rotacoes=None, recoloracoes=None,
                          media_nos_visitados=None, tempo_segundos=0)
        zero = replace(original, rotacoes=0, recoloracoes=0,
                       media_nos_visitados=0, tempo_segundos=0.0)
        for resultado in (ausente, zero):
            validar_resultado(resultado)
            resumo = resumir([resultado, resultado], 2)[0]
            for campo in ("rotacoes", "recoloracoes", "media_nos_visitados"):
                self.assertEqual(resumo[campo], getattr(resultado, campo))
            self.assertEqual(resumo["mediana_ms"], 0)
        with TemporaryDirectory() as pasta:
            caminho = exportar_csv([ausente, zero], Path(pasta) / "opcionais.csv")
            self.assertEqual(_ler_csv(caminho), [ausente, zero])

    def test_seed_negativa_e_remocoes_sem_operacoes_sao_validas(self):
        resultados = executar_experimentos((1,), -42)
        conferir_execucao(resultados, (1,), -42)
        resumo = resumir(resultados, 1)
        self.assertTrue(all(r["seed"] == -42 for r in resumo))
        remocoes = [r for r in resultados if r.experimento.startswith("D_")]
        self.assertEqual(len(remocoes), 6)
        self.assertTrue(all(r.operacoes == 0 and r.quantidade_final == 1
                            and r.altura_inicial == r.altura_final == 1 for r in remocoes))
        with TemporaryDirectory() as pasta:
            caminho = exportar_csv(resultados, Path(pasta) / "seed_negativa.csv")
            self.assertEqual(_ler_csv(caminho), resultados)

    def test_semente_validacao_e_repeticoes_rejeitam_tipos_enganosos(self):
        for seed in (True, 42.0, "42", None):
            with self.subTest(seed=seed):
                self.conferir_rejeicao(seed=seed)
        for valido in (False, 1, "True", None):
            with self.subTest(valido=valido):
                self.conferir_rejeicao(valido=valido)
        for repeticoes in (True, 0, -1, 2.0):
            with self.subTest(repeticoes=repeticoes), self.assertRaises(ValueError):
                resumir([self.original, self.original], repeticoes)
        for tamanhos, seed in (((True,), 42), ((10.0,), 42), ((10,), True),
                               ((0,), 42), ((10, 10), 42)):
            with self.subTest(tamanhos=tamanhos, seed=seed), self.assertRaises(ValueError):
                conferir_execucao(self.resultados, tamanhos, seed)

    def test_leitura_csv_rejeita_metricas_invalidas_antes_de_resumir(self):
        with TemporaryDirectory() as pasta:
            casos = (("altura_inicial", -1), ("altura_final", 0),
                     ("quantidade_inicial", -10), ("quantidade_final", -1),
                     ("operacoes", -1), ("rotacoes", -1), ("recoloracoes", -1),
                     ("media_nos_visitados", -0.5), ("media_nos_visitados", float("nan")),
                     ("tempo_segundos", -0.1), ("tempo_segundos", float("inf")),
                     ("rotacoes", True), ("altura_final", 1.0), ("seed", True))
            for indice, (campo, valor) in enumerate(casos):
                caminho = exportar_csv([replace(self.original, **{campo: valor})],
                                      Path(pasta) / f"invalido_{indice}.csv")
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    _ler_csv(caminho)

    def test_hash_correto_nao_legitima_metrica_negativa(self):
        with TemporaryDirectory() as pasta:
            lote = Path(pasta)
            adulterado = replace(self.original, rotacoes=-1)
            caminho = exportar_csv([adulterado, *self.resultados[1:]], lote / "execucao_01.csv")
            ambiente = {
                "estado": "concluido", "repeticoes": 1, "tamanhos": [10], "seed": 42,
                "linhas_totais": 14,
                "execucoes": [{"arquivo": caminho.name, "estado": "concluida",
                               "sha256": sha256(caminho), "linhas": 14}],
            }
            (lote / "ambiente.json").write_text(json.dumps(ambiente), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rotacoes"):
                carregar_lote(lote)


if __name__ == "__main__":
    unittest.main()
