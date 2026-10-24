"""Menu independente e coordenação de falhas parciais entre as estruturas."""

import csv
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gerar_dados import gerar_pacientes
from integracao import ErroIntegracao, carregar_fabricas, criar_arvore
from main import Clinica, executar_menu
from tests.apoio import ArvoreTeste, fabricas_teste


class TestMenu(unittest.TestCase):
    def executar(self, respostas, clinica=None):
        saidas = []
        entradas = iter(respostas)
        executar_menu(lambda _: next(entradas), saidas.append,
                      clinica if clinica is not None else Clinica({}))
        return "\n".join(saidas)

    def test_inicializa_sem_modulos(self):
        with patch("integracao.import_module", side_effect=ModuleNotFoundError("ausente")):
            fabricas, avisos = carregar_fabricas()
            self.assertEqual(fabricas, {})
            self.assertEqual(len(avisos), 2)
            saida = self.executar(["0"], Clinica())
        self.assertIn("AVL indisponível", saida)
        self.assertIn("Sistema encerrado", saida)

    def test_entradas_invalidas_e_opcoes_indisponiveis(self):
        saida = self.executar(["abc", "1", "texto", "2", "13", "0"])
        self.assertIn("Opção inválida", saida)
        self.assertIn("Não foi possível concluir", saida)
        self.assertIn("após a integração", saida)

    def test_geracao_e_validacao_independentes(self):
        saida = self.executar(["12", "3", "42", "1", "1", "Ana", "2000-02-29",
                               "00123", "0"])
        self.assertIn("3 pacientes fictícios gerados", saida)
        self.assertIn("sem cadastro", saida)
        self.assertIn("Dados do paciente validados", saida)

    def test_todas_as_consultas_e_selecao(self):
        fabricas, _ = fabricas_teste()
        clinica = Clinica(fabricas)
        clinica.cadastrar_lote(gerar_pacientes(2))
        saida = self.executar(["s", "2", "2", "1", "4", "5", "6", "7", "8",
                               "9", "10", "11", "11", "3", "1", "0"], clinica)
        self.assertIn("árvore selecionada: Rubro-Negra", saida)
        self.assertIn("Árvore válida", saida)
        self.assertIn("Quantidade de nós: 2", saida)
        self.assertIn("Modo detalhado ativado", saida)
        self.assertIn("removido de ambas", saida)
        self.assertEqual([a.quantidade() for a in clinica.arvores.values()], [1, 1])

    def test_geracao_integrada_e_fim_de_entrada(self):
        fabricas, _ = fabricas_teste()
        clinica = Clinica(fabricas)
        clinica.cadastrar(gerar_pacientes(1)[0])
        saida = self.executar(["12", "2", "42", "0"], clinica)
        self.assertIn("Lote cadastrado", saida)
        self.assertEqual(clinica.proximo_prontuario(), 4)
        saidas = []
        executar_menu(lambda _: (_ for _ in ()).throw(EOFError()), saidas.append, clinica)
        self.assertIn("Sistema encerrado.", saidas)

    def test_experimentos_do_menu_nao_alteram_pacientes_cadastrados(self):
        fabricas, _ = fabricas_teste()
        clinica = Clinica(fabricas)
        paciente = gerar_pacientes(1, prontuario_inicial=90)[0]
        clinica.cadastrar(paciente)
        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / "menu"
            with patch("main.PASTA_RESULTADOS_MENU", destino):
                saida = self.executar(["13", "4", "42", "0"], clinica)
            self.assertEqual(len(list(destino.glob("execucao_*.csv"))), 1)
        self.assertIn("Medições reais concluídas", saida)
        self.assertIn("Limitação:", saida)
        for arvore in clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), [paciente])

    def test_experimentos_reais_repetidos_preservam_historico_e_estado_do_menu(self):
        historico = Path(__file__).resolve().parents[1] / "resultados" / "resultados.csv"
        bytes_historico = historico.read_bytes()
        hash_historico = hashlib.sha256(bytes_historico).hexdigest()
        clinica = Clinica()
        pacientes = gerar_pacientes(3, prontuario_inicial=90)
        clinica.cadastrar_lote(pacientes)
        clinica.detalhado["Rubro-Negra"] = True
        clinica.arvores["Rubro-Negra"].definir_modo_detalhado(True)
        for arvore in clinica.arvores.values():
            arvore.buscar(91)
        originais = dict(clinica.arvores)
        estruturas = {nome: a.exibir() for nome, a in originais.items()}
        metricas = {nome: a.estatisticas() for nome, a in originais.items()}
        modos = dict(clinica.detalhado)
        cadastro = dict(clinica._pacientes)

        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / "resultados" / "menu"
            destino.mkdir(parents=True)
            anterior = destino / "execucao_anterior.csv"
            anterior.write_bytes(bytes_historico)
            with patch("main.PASTA_RESULTADOS_MENU", destino):
                saida = self.executar(
                    ["s", "2", "13", "10", "42", "13", "10", "42", "0"], clinica
                )
            novos = [c for c in destino.glob("execucao_*.csv") if c != anterior]
            self.assertEqual(len(novos), 2)
            self.assertNotEqual(novos[0].name, novos[1].name)
            for caminho in novos:
                self.assertRegex(caminho.name, r"^execucao_[0-9a-f]{32}\.csv$")
                self.assertIn(str(caminho), saida)
                with caminho.open(encoding="utf-8", newline="") as arquivo:
                    leitor = csv.DictReader(arquivo)
                    linhas = list(leitor)
                    self.assertIn("altura_inicial", leitor.fieldnames)
                self.assertEqual(len(linhas), 14)
                self.assertEqual({linha["arvore"] for linha in linhas}, {"AVL", "Rubro-Negra"})
                self.assertEqual({linha["seed"] for linha in linhas}, {"42"})
                for linha in linhas:
                    self.assertEqual(linha["valido"], "True")
                    self.assertEqual(linha["limitacoes"], "")
                    self.assertGreaterEqual(float(linha["tempo_segundos"]), 0)
                    self.assertEqual(int(linha["quantidade_inicial"]), 10)
                    removidos = (int(linha["operacoes"])
                                 if linha["experimento"].startswith("D_") else 0)
                    self.assertEqual(int(linha["quantidade_final"]), 10 - removidos)
            self.assertEqual(anterior.read_bytes(), bytes_historico)

        self.assertEqual(saida.count("Medições reais concluídas:"), 2)
        self.assertNotIn("Não foi possível concluir", saida)
        self.assertIn("árvore selecionada: Rubro-Negra", saida)
        self.assertEqual(historico.read_bytes(), bytes_historico)
        self.assertEqual(hashlib.sha256(historico.read_bytes()).hexdigest(), hash_historico)
        self.assertTrue(clinica.disponivel)
        self.assertEqual(clinica._pacientes, cadastro)
        self.assertEqual(clinica.detalhado, modos)
        for nome, arvore in clinica.arvores.items():
            self.assertIs(arvore, originais[nome])
            self.assertEqual(arvore.em_ordem(), pacientes)
            for paciente_atual, original in zip(arvore.em_ordem(), pacientes):
                self.assertIs(paciente_atual, original)
            self.assertEqual(arvore.exibir(), estruturas[nome])
            self.assertEqual(arvore.estatisticas(), metricas[nome])
            self.assertTrue(arvore.validar())

    def test_falha_na_exportacao_do_menu_nao_anuncia_sucesso(self):
        clinica = Clinica()
        pacientes = gerar_pacientes(2, prontuario_inicial=90)
        clinica.cadastrar_lote(pacientes)
        originais = dict(clinica.arvores)
        metricas = {nome: a.estatisticas() for nome, a in originais.items()}
        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / "menu"
            with patch("main.PASTA_RESULTADOS_MENU", destino), patch(
                "experimentos.exportar_csv", side_effect=OSError("falha controlada na gravação")
            ) as exportar:
                saida = self.executar(["13", "10", "42", "0"], clinica)
            self.assertEqual(exportar.call_count, 1)
            self.assertEqual(exportar.call_args.args[1].parent, destino)
            self.assertFalse(destino.exists())
        self.assertIn("Não foi possível concluir: falha controlada na gravação", saida)
        self.assertNotIn("Medições reais concluídas", saida)
        self.assertIn("Sistema encerrado.", saida)
        for nome, arvore in clinica.arvores.items():
            self.assertIs(arvore, originais[nome])
            self.assertEqual(arvore.em_ordem(), pacientes)
            self.assertEqual(arvore.estatisticas(), metricas[nome])


class TestCoordenacao(unittest.TestCase):
    def setUp(self):
        self.fabricas, _ = fabricas_teste()
        self.clinica = Clinica(self.fabricas)
        self.pacientes = gerar_pacientes(3)

    def test_cadastro_remocao_e_duplicidade(self):
        self.clinica.cadastrar_lote(self.pacientes)
        with self.assertRaisesRegex(ValueError, "já cadastrado"):
            self.clinica.cadastrar(self.pacientes[0])
        self.clinica.remover(2)
        for arvore in self.clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), [self.pacientes[0], self.pacientes[2]])
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            self.clinica.remover(99)

    def test_falha_apos_insercao_parcial_reconstroi_ambas(self):
        self.clinica.cadastrar(self.pacientes[0])
        arvore = self.clinica.arvores["Rubro-Negra"]
        inserir = arvore.inserir

        def falhar(paciente):
            inserir(paciente)
            raise RuntimeError("falha após alterar")

        arvore.inserir = falhar
        with self.assertRaisesRegex(ErroIntegracao, "restauradas"):
            self.clinica.cadastrar_lote(self.pacientes[1:])
        for arvore in self.clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), self.pacientes[:1])
        self.assertTrue(self.clinica.disponivel)

    def test_remocao_parcial_e_recusa_explicita(self):
        self.clinica.cadastrar_lote(self.pacientes)
        self.clinica.arvores["Rubro-Negra"].remover = lambda _: False
        with self.assertRaisesRegex(ErroIntegracao, "restauradas"):
            self.clinica.remover(1)
        for arvore in self.clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), self.pacientes)

    def test_recuperacao_falha_bloqueia_operacoes(self):
        self.clinica.arvores["Rubro-Negra"].inserir = lambda _: False
        self.clinica.fabricas["AVL"] = lambda: (_ for _ in ()).throw(RuntimeError("falha"))
        with self.assertRaisesRegex(ErroIntegracao, "Restauração falhou"):
            self.clinica.cadastrar(self.pacientes[0])
        self.assertFalse(self.clinica.disponivel)
        with self.assertRaisesRegex(ErroIntegracao, "bloqueadas"):
            self.clinica.remover(1)

    def test_arvore_unica_nao_permite_cadastro(self):
        clinica = Clinica({"AVL": ArvoreTeste})
        with self.assertRaisesRegex(ErroIntegracao, "após a integração"):
            clinica.cadastrar(self.pacientes[0])

    def test_instancia_compartilhada_nao_e_aceita(self):
        arvore = ArvoreTeste()
        clinica = Clinica(dict.fromkeys(("AVL", "Rubro-Negra"), lambda: arvore))
        self.assertFalse(clinica.disponivel)
        self.assertIn("independentes", clinica.avisos[0])

    def test_contrato_incompativel_nao_impede_menu(self):
        clinica = Clinica({"AVL": object, "Rubro-Negra": object})
        self.assertFalse(clinica.disponivel)
        self.assertIn("Métodos pendentes", clinica.avisos[0])
        with self.assertRaises(ErroIntegracao):
            arvore = ArvoreTeste()
            arvore.inserir(self.pacientes[0])
            criar_arvore(lambda: arvore)


if __name__ == "__main__":
    unittest.main()
