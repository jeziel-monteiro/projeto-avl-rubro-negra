"""Integração de pacientes, clínica, experimentos e CSV com as duas árvores reais."""

import csv
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from avl import ArvoreAVL
from rubro_negra import ArvoreRubroNegra
from experimentos import executar_experimentos, exportar_csv, preparar_cenarios
from gerar_dados import gerar_pacientes
from integracao import criar_arvores
from main import Clinica, executar_menu


FABRICAS = {"AVL": ArvoreAVL, "Rubro-Negra": ArvoreRubroNegra}


class TestIntegracaoReal(unittest.TestCase):
    def conferir_metricas(self, resultado):
        self.assertTrue(resultado.valido)
        self.assertEqual(resultado.limitacoes, "")
        self.assertGreaterEqual(resultado.tempo_segundos, 0)
        self.assertGreaterEqual(resultado.altura_final, 0)
        self.assertLessEqual(resultado.altura_final,
                             2 * math.log2(resultado.quantidade_final + 1))
        if resultado.experimento.startswith("C_"):
            self.assertIsNone(resultado.rotacoes)
            self.assertIsNone(resultado.recoloracoes)
            self.assertIsNotNone(resultado.media_nos_visitados)
            self.assertGreater(resultado.media_nos_visitados, 0)
        else:
            self.assertIsNone(resultado.media_nos_visitados)
            for valor in (resultado.rotacoes, resultado.recoloracoes):
                self.assertIs(type(valor), int)
                self.assertGreaterEqual(valor, 0)
            if resultado.arvore == "AVL":
                self.assertEqual(resultado.recoloracoes, 0)

    def test_operacoes_com_os_mesmos_pacientes(self):
        for quantidade in (10, 30, 100):
            with self.subTest(quantidade=quantidade):
                arvores = criar_arvores(FABRICAS)
                self.assertIsNot(arvores["AVL"], arvores["Rubro-Negra"])
                pacientes = gerar_pacientes(quantidade)
                for arvore in arvores.values():
                    self.assertEqual(arvore.altura(), 0)
                    self.assertEqual(arvore.quantidade(), 0)
                    self.assertTrue(arvore.validar())
                    for indice, paciente in enumerate(pacientes, 1):
                        self.assertTrue(arvore.inserir(paciente))
                        self.assertTrue(arvore.validar())
                        self.assertEqual(arvore.quantidade(), indice)
                        self.assertGreater(arvore.altura(), 0)
                        self.assertLessEqual(arvore.altura(), 2 * math.log2(indice + 1))
                    self.assertFalse(arvore.inserir(pacientes[0]))
                    self.assertEqual(arvore.em_ordem(), pacientes)
                    for paciente in pacientes:
                        self.assertIs(arvore.buscar(paciente.prontuario), paciente)
                    self.assertIsNone(arvore.buscar(quantidade + 1))
                    self.assertFalse(arvore.remover(quantidade + 1))
                    for indice, paciente in enumerate(pacientes):
                        self.assertTrue(arvore.remover(paciente.prontuario))
                        self.assertTrue(arvore.validar())
                        self.assertEqual(arvore.quantidade(), quantidade - indice - 1)
                        self.assertEqual(arvore.em_ordem(), pacientes[indice + 1:])
                    self.assertEqual(arvore.altura(), 0)

    def test_clinica_e_menu_carregam_as_arvores_reais(self):
        clinica = Clinica()
        self.assertTrue(clinica.disponivel)
        self.assertEqual(clinica.avisos, [])
        for nome, classe in FABRICAS.items():
            self.assertIsInstance(clinica.arvores[nome], classe)
        entradas = iter(["12", "10", "42", "s", "2", "2", "1", "10", "3", "1", "0"])
        saidas = []
        executar_menu(lambda _: next(entradas), saidas.append, clinica)
        self.assertFalse(any("Não foi possível concluir" in texto for texto in saidas))
        self.assertIn("Árvore válida.", saidas)
        pacientes = gerar_pacientes(10)[1:]
        executar_experimentos((10,), fabricas=FABRICAS)
        for arvore in clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), pacientes)
            self.assertEqual(arvore.quantidade(), 9)
            self.assertTrue(arvore.validar())

    def test_experimentos_com_metricas_completas(self):
        resultados = executar_experimentos((10, 30, 100, 1000), seed=42)
        self.assertEqual(len(resultados), 56)
        for resultado in resultados:
            with self.subTest(arvore=resultado.arvore, experimento=resultado.experimento,
                              quantidade=resultado.quantidade_inicial):
                self.conferir_metricas(resultado)
                quantidade = resultado.quantidade_inicial
                if resultado.experimento.startswith("D_"):
                    percentual = int(resultado.experimento.rsplit("_", 1)[1])
                    self.assertEqual(resultado.operacoes, quantidade * percentual // 100)
                    quantidade -= resultado.operacoes
                else:
                    self.assertEqual(resultado.operacoes, quantidade)
                self.assertEqual(resultado.quantidade_final, quantidade)

    def test_contadores_correspondem_as_operacoes_reais(self):
        cenarios = preparar_cenarios(30, seed=42)
        for resultado in executar_experimentos((30,), seed=42, fabricas=FABRICAS):
            if resultado.experimento.startswith("C_"):
                continue
            with self.subTest(arvore=resultado.arvore, experimento=resultado.experimento):
                arvore = FABRICAS[resultado.arvore]()
                operacao = "insercao"
                sequencia = (cenarios.crescente if resultado.experimento.startswith("A_")
                             else cenarios.aleatoria)
                if resultado.experimento.startswith("D_"):
                    for paciente in sequencia:
                        self.assertTrue(arvore.inserir(paciente))
                    antes = arvore.estatisticas()
                    percentual = int(resultado.experimento.rsplit("_", 1)[1])
                    for chave in cenarios.remocoes[percentual]:
                        self.assertTrue(arvore.remover(chave))
                    operacao = "remocao"
                else:
                    antes = arvore.estatisticas()
                    for paciente in sequencia:
                        self.assertTrue(arvore.inserir(paciente))
                depois = arvore.estatisticas()
                self.assertEqual(resultado.rotacoes,
                                 depois[f"rotacoes_{operacao}"] - antes[f"rotacoes_{operacao}"])
                self.assertEqual(resultado.recoloracoes,
                                 depois[f"recoloracoes_{operacao}"] - antes[f"recoloracoes_{operacao}"])
                self.assertEqual(resultado.altura_final, arvore.altura())
                self.assertEqual(resultado.quantidade_final, arvore.quantidade())
                self.assertTrue(arvore.validar())

    def test_media_de_visitas_contra_contagem_independente_dos_caminhos(self):
        for quantidade in (10, 30, 100):
            cenarios = preparar_cenarios(quantidade, seed=42)
            for resultado in executar_experimentos((quantidade,), fabricas=FABRICAS):
                if not resultado.experimento.startswith("C_"):
                    continue
                with self.subTest(arvore=resultado.arvore, experimento=resultado.experimento,
                                  quantidade=quantidade):
                    arvore = FABRICAS[resultado.arvore]()
                    for paciente in cenarios.aleatoria:
                        arvore.inserir(paciente)
                    chaves = (cenarios.buscas_existentes if resultado.experimento == "C_busca_existente"
                              else cenarios.buscas_inexistentes)
                    visitas = []
                    for chave in chaves:
                        no = arvore.raiz
                        total = 0
                        # Conta diretamente os caminhos, sem usar buscar() nem estatisticas().
                        while no is not None and no.paciente is not None:
                            total += 1
                            if chave == no.prontuario:
                                break
                            no = no.esquerda if chave < no.prontuario else no.direita
                        visitas.append(total)
                    if resultado.experimento == "C_busca_existente":
                        self.assertGreater(len(set(visitas)), 1)
                    self.assertEqual(resultado.media_nos_visitados, sum(visitas) / len(chaves))

    def test_zero_e_preservado_nas_metricas_aplicaveis(self):
        for resultado in executar_experimentos((1,), fabricas=FABRICAS):
            self.conferir_metricas(resultado)
            self.assertEqual(resultado.altura_final, 1)
            if not resultado.experimento.startswith("C_"):
                self.assertEqual(resultado.rotacoes, 0)
                if resultado.arvore == "AVL" or resultado.experimento.startswith("D_"):
                    self.assertEqual(resultado.recoloracoes, 0)
            else:
                self.assertEqual(resultado.media_nos_visitados, 1)

    def test_exportacao_csv_completa(self):
        resultados = executar_experimentos((10, 30), fabricas=FABRICAS)
        with TemporaryDirectory() as pasta:
            destino = exportar_csv(resultados, Path(pasta) / "reais.csv")
            with destino.open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo))
        self.assertEqual(len(linhas), 28)
        for linha, resultado in zip(linhas, resultados):
            self.assertEqual(linha["limitacoes"], "")
            self.assertEqual(linha["valido"], "True")
            self.assertEqual(int(linha["quantidade_final"]), resultado.quantidade_final)
            self.assertEqual(int(linha["altura_final"]), resultado.altura_final)
            if linha["experimento"].startswith("C_"):
                self.assertEqual(float(linha["media_nos_visitados"]), resultado.media_nos_visitados)
                self.assertEqual(linha["rotacoes"], "")
                self.assertEqual(linha["recoloracoes"], "")
            else:
                self.assertEqual(int(linha["rotacoes"]), resultado.rotacoes)
                self.assertEqual(int(linha["recoloracoes"]), resultado.recoloracoes)
                self.assertEqual(linha["media_nos_visitados"], "")


if __name__ == "__main__":
    unittest.main()
