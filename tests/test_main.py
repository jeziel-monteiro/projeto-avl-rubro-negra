"""Menu independente e coordenação de falhas parciais entre as estruturas."""

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
        from experimentos import exportar_csv

        fabricas, _ = fabricas_teste()
        clinica = Clinica(fabricas)
        paciente = gerar_pacientes(1, prontuario_inicial=90)[0]
        clinica.cadastrar(paciente)
        with TemporaryDirectory() as pasta:
            destino = Path(pasta) / "menu.csv"
            with patch("experimentos.exportar_csv", side_effect=lambda resultados: exportar_csv(resultados, destino)):
                saida = self.executar(["13", "4", "42", "0"], clinica)
            self.assertTrue(destino.exists())
        self.assertIn("Medições reais concluídas", saida)
        self.assertIn("Limitação:", saida)
        for arvore in clinica.arvores.values():
            self.assertEqual(arvore.em_ordem(), [paciente])


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
