"""Testes independentes da AVL; somente biblioteca padrão e pacientes fictícios."""

import io
import math
import random
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from types import SimpleNamespace

from avl import ArvoreAVL


@dataclass(frozen=True)
class PacienteTeste:
    prontuario: int
    nome: str
    data_nascimento: str = "2000-01-01"
    telefone: str = "92999990000"


def paciente(prontuario: int) -> PacienteTeste:
    return PacienteTeste(prontuario, f"Paciente fictício {prontuario}")


class TestArvoreAVL(unittest.TestCase):
    def construir(self, chaves):
        arvore = ArvoreAVL()
        for chave in chaves:
            self.assertTrue(arvore.inserir(paciente(chave)))
            self.conferir_invariantes(arvore)
        return arvore

    def conferir_invariantes(self, arvore):
        """Oráculo separado: recalcula ordem, alturas, equilíbrio e contagem."""
        vistos = set()

        def conferir(no, inferior=None, superior=None):
            if no is None:
                return 0, 0
            self.assertNotIn(id(no), vistos)
            vistos.add(id(no))
            self.assertEqual(no.prontuario, no.paciente.prontuario)
            if inferior is not None:
                self.assertGreater(no.prontuario, inferior)
            if superior is not None:
                self.assertLess(no.prontuario, superior)
            he, qe = conferir(no.esquerda, inferior, no.prontuario)
            hd, qd = conferir(no.direita, no.prontuario, superior)
            self.assertLessEqual(abs(he - hd), 1)
            altura = 1 + max(he, hd)
            self.assertEqual(no.altura, altura)
            return altura, qe + qd + 1

        altura, quantidade = conferir(arvore.raiz)
        self.assertEqual(arvore.altura(), altura)
        self.assertEqual(arvore.quantidade(), quantidade)
        self.assertTrue(arvore.validar())

    def test_arvore_vazia(self):
        arvore = self.construir([])
        self.assertIsNone(arvore.raiz)
        self.assertIsNone(arvore.buscar(1))
        self.assertFalse(arvore.remover(1))
        self.assertIsNone(arvore.minimo())
        self.assertIsNone(arvore.maximo())
        self.assertEqual(arvore.altura(), 0)
        self.assertEqual(arvore.quantidade(), 0)
        self.assertEqual(arvore.pre_ordem(), [])
        self.assertEqual(arvore.em_ordem(), [])
        self.assertEqual(arvore.pos_ordem(), [])
        self.assertEqual(arvore.nos_visitados_ultima_busca, 0)
        self.assertIn("vazia", arvore.exibir())

    def test_preserva_objeto_e_todos_os_atributos(self):
        arvore = ArvoreAVL()
        original = PacienteTeste(10, "Pessoa fictícia", "1995-07-20", "92911112222")
        self.assertTrue(arvore.inserir(original))
        self.assertIs(arvore.buscar(10), original)
        self.assertIs(arvore.minimo(), original)
        self.assertIs(arvore.maximo(), original)
        self.assertIs(arvore.em_ordem()[0], original)
        self.assertEqual(arvore.altura(), 1)
        self.conferir_invariantes(arvore)

    def test_aceita_modelo_independente_com_prontuario(self):
        arvore = ArvoreAVL()
        original = SimpleNamespace(prontuario=123, nome="Paciente de outro módulo")
        self.assertTrue(arvore.inserir(original))
        self.assertIs(arvore.buscar(123), original)
        self.conferir_invariantes(arvore)

    def test_ordena_exclusivamente_por_prontuario(self):
        arvore = ArvoreAVL()
        registros = [PacienteTeste(20, "A"), PacienteTeste(10, "Z"), PacienteTeste(30, "M")]
        for registro in registros:
            self.assertTrue(arvore.inserir(registro))
        self.assertEqual([p.nome for p in arvore.em_ordem()], ["Z", "A", "M"])
        self.conferir_invariantes(arvore)

    def test_duplicata_nao_sobrescreve_nem_altera_metricas(self):
        arvore = self.construir([30, 10, 20])
        original = arvore.buscar(20)
        antes = arvore.estatisticas()
        estrutura = arvore.exibir()
        self.assertFalse(arvore.inserir(PacienteTeste(20, "Substituição indevida")))
        self.assertEqual(arvore.estatisticas(), antes)
        self.assertEqual(arvore.exibir(), estrutura)
        self.assertEqual(arvore.quantidade(), 3)
        self.assertIs(arvore.buscar(20), original)
        self.conferir_invariantes(arvore)

    def test_rejeita_chaves_invalidas_sem_excecao(self):
        arvore = self.construir([1, 2, 3])
        estrutura = arvore.exibir()
        for chave in [None, True, False, 0, -1, 1.0, "1", [], {}, object()]:
            with self.subTest(chave=chave):
                self.assertFalse(arvore.inserir(SimpleNamespace(prontuario=chave)))
                self.assertIsNone(arvore.buscar(chave))
                self.assertEqual(arvore.nos_visitados_ultima_busca, 0)
                self.assertFalse(arvore.remover(chave))
                self.assertEqual(arvore.exibir(), estrutura)
                self.conferir_invariantes(arvore)
        for invalido in [None, object(), {}, 42]:
            self.assertFalse(arvore.inserir(invalido))

    def test_busca_existente_inexistente_e_contagem_de_visitas(self):
        arvore = self.construir([40, 20, 60, 10, 30, 50, 70])
        for chave, esperado, visitas in [(40, True, 1), (20, True, 2), (30, True, 3),
                                         (25, False, 3), (80, False, 3), (1, False, 3)]:
            with self.subTest(chave=chave):
                self.assertEqual(arvore.buscar(chave) is not None, esperado)
                self.assertEqual(arvore.nos_visitados_ultima_busca, visitas)
                self.assertEqual(arvore.estatisticas()["nos_visitados_ultima_busca"], visitas)

    def test_caminhamentos_e_extremos(self):
        arvore = self.construir([40, 20, 60, 10, 30, 50, 70])
        for metodo, esperado in [(arvore.pre_ordem, [40, 20, 10, 30, 60, 50, 70]),
                                  (arvore.em_ordem, [10, 20, 30, 40, 50, 60, 70]),
                                  (arvore.pos_ordem, [10, 30, 20, 50, 70, 60, 40])]:
            self.assertEqual([p.prontuario for p in metodo()], esperado)
        self.assertEqual(arvore.minimo().prontuario, 10)
        self.assertEqual(arvore.maximo().prontuario, 70)
        copia = arvore.em_ordem()
        copia.clear()
        self.assertEqual(arvore.quantidade(), 7)
        self.assertEqual(len(arvore.em_ordem()), 7)

    def test_quatro_casos_de_rotacao_na_insercao(self):
        for caso, chaves, rotacoes in [("LL", [30, 20, 10], 1),
                                       ("RR", [10, 20, 30], 1),
                                       ("LR", [30, 10, 20], 2),
                                       ("RL", [10, 30, 20], 2)]:
            with self.subTest(caso=caso):
                arvore = self.construir(chaves)
                self.assertEqual(arvore.raiz.prontuario, 20)
                self.assertEqual([p.prontuario for p in arvore.pre_ordem()], [20, 10, 30])
                self.assertEqual(arvore.altura(), 2)
                self.assertEqual(arvore.estatisticas()["rotacoes_insercao"], rotacoes)
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)

    def test_remocao_de_folha(self):
        arvore = self.construir([20, 10, 30])
        self.assertTrue(arvore.remover(10))
        self.assertIsNone(arvore.buscar(10))
        self.assertEqual([p.prontuario for p in arvore.em_ordem()], [20, 30])
        self.conferir_invariantes(arvore)

    def test_remocao_de_no_com_um_filho_em_ambos_os_lados(self):
        for chaves, removido in [([30, 20, 40, 10], 20), ([30, 20, 40, 25], 20),
                                 ([20, 10, 30, 25], 30), ([20, 10, 30, 40], 30)]:
            with self.subTest(chaves=chaves):
                arvore = self.construir(chaves)
                self.assertTrue(arvore.remover(removido))
                self.assertEqual([p.prontuario for p in arvore.em_ordem()],
                                 sorted(set(chaves) - {removido}))
                self.conferir_invariantes(arvore)

    def test_remocao_da_raiz_com_zero_ou_um_filho(self):
        for chaves in [[1], [2, 1], [1, 2]]:
            with self.subTest(chaves=chaves):
                arvore = self.construir(chaves)
                self.assertTrue(arvore.remover(chaves[0]))
                self.assertEqual(arvore.quantidade(), len(chaves) - 1)
                self.conferir_invariantes(arvore)

    def test_remocao_com_dois_filhos_e_sucessor_direto(self):
        arvore = self.construir([20, 10, 30, 40])
        originais = {p.prontuario: p for p in arvore.em_ordem()}
        self.assertTrue(arvore.remover(20))
        self.assertIsNone(arvore.buscar(20))
        for chave in [10, 30, 40]:
            self.assertIs(arvore.buscar(chave), originais[chave])
        self.conferir_invariantes(arvore)

    def test_remocao_com_sucessor_profundo_que_tem_filho_direito(self):
        chaves = [50, 25, 75, 10, 35, 60, 90, 5, 15, 30, 40, 55, 65, 80, 95, 57]
        arvore = self.construir(chaves)
        self.assertEqual(arvore.raiz.prontuario, 50)
        self.assertEqual(arvore.raiz.direita.esquerda.esquerda.prontuario, 55)
        self.assertEqual(arvore.raiz.direita.esquerda.esquerda.direita.prontuario, 57)
        originais = {p.prontuario: p for p in arvore.em_ordem()}
        self.assertTrue(arvore.remover(50))
        self.assertEqual(arvore.quantidade(), len(chaves) - 1)
        for chave in set(chaves) - {50}:
            self.assertIs(arvore.buscar(chave), originais[chave])
        self.conferir_invariantes(arvore)

    def test_quatro_casos_de_rotacao_na_remocao(self):
        casos = [("LL", [30, 20, 40, 10], 40, 20, 1),
                 ("RR", [20, 10, 30, 40], 10, 30, 1),
                 ("LR", [30, 10, 40, 20], 40, 20, 2),
                 ("RL", [10, 5, 30, 20], 5, 20, 2)]
        for caso, chaves, removido, raiz, rotacoes in casos:
            with self.subTest(caso=caso):
                arvore = self.construir(chaves)
                antes = arvore.estatisticas()["rotacoes_insercao"]
                self.assertTrue(arvore.remover(removido))
                self.assertEqual(arvore.raiz.prontuario, raiz)
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], rotacoes)
                self.assertEqual(arvore.estatisticas()["rotacoes_insercao"], antes)
                self.conferir_invariantes(arvore)

    def test_remocao_com_fator_zero_no_filho_exige_rotacao_simples(self):
        for chaves, removido, raiz in [([30, 20, 40, 10, 25], 40, 20),
                                       ([20, 10, 30, 25, 40], 10, 30)]:
            with self.subTest(chaves=chaves):
                arvore = self.construir(chaves)
                self.assertTrue(arvore.remover(removido))
                self.assertEqual(arvore.raiz.prontuario, raiz)
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 1)
                self.conferir_invariantes(arvore)

    def test_remocao_rebalanceia_em_dois_niveis(self):
        arvore = self.construir([50, 25, 75, 15, 40, 60, 80, 10, 20, 30, 45, 55, 5])
        self.assertEqual(arvore.raiz.prontuario, 50)
        arvore.definir_modo_detalhado(True)
        saida = io.StringIO()
        with redirect_stdout(saida):
            self.assertTrue(arvore.remover(80))
        self.assertEqual(arvore.raiz.prontuario, 25)
        self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 2)
        self.assertEqual(saida.getvalue().count("caso LL"), 2)
        self.conferir_invariantes(arvore)

    def test_remocao_inexistente_nao_muda_estrutura_ou_metricas(self):
        arvore = self.construir([10, 20, 30])
        arvore.buscar(10)
        antes = arvore.estatisticas()
        estrutura = arvore.exibir()
        self.assertFalse(arvore.remover(99))
        self.assertEqual(arvore.exibir(), estrutura)
        self.assertEqual(arvore.estatisticas(), antes)
        self.conferir_invariantes(arvore)

    def test_contadores_isolados_e_copia_das_estatisticas(self):
        arvore = self.construir([1, 2, 3])
        outra = ArvoreAVL()
        estatisticas = arvore.estatisticas()
        self.assertEqual(estatisticas, {"rotacoes_insercao": 1, "rotacoes_remocao": 0,
                                       "recoloracoes_insercao": 0, "recoloracoes_remocao": 0,
                                       "nos_visitados_ultima_busca": 0})
        estatisticas["rotacoes_insercao"] = 999
        self.assertEqual(arvore.estatisticas()["rotacoes_insercao"], 1)
        self.assertEqual(outra.estatisticas()["rotacoes_insercao"], 0)
        self.assertEqual(outra.quantidade(), 0)

    def test_somente_buscar_altera_visitas_da_ultima_busca(self):
        arvore = self.construir([30, 20, 40, 10])
        arvore.buscar(10)
        visitas = arvore.nos_visitados_ultima_busca
        arvore.inserir(paciente(25))
        arvore.remover(40)
        for consulta in [arvore.minimo, arvore.maximo, arvore.pre_ordem, arvore.em_ordem,
                         arvore.pos_ordem, arvore.altura, arvore.quantidade, arvore.exibir,
                         arvore.validar, arvore.estatisticas]:
            consulta()
        self.assertEqual(arvore.nos_visitados_ultima_busca, visitas)
        self.assertEqual(arvore.estatisticas()["recoloracoes_insercao"], 0)
        self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 0)

    def test_reiniciar_estatisticas_preserva_pacientes_e_modo(self):
        arvore = self.construir([1, 2, 3])
        arvore.buscar(1)
        originais = arvore.em_ordem()
        arvore.definir_modo_detalhado(True)
        arvore.reiniciar_estatisticas()
        self.assertTrue(all(valor == 0 for valor in arvore.estatisticas().values()))
        self.assertEqual(arvore.em_ordem(), originais)
        saida = io.StringIO()
        with redirect_stdout(saida):
            self.assertTrue(arvore.remover(1))
        self.assertIn("Remoção do prontuário 1", saida.getvalue())
        self.conferir_invariantes(arvore)

    def test_modo_detalhado_mostra_quatro_casos_e_estrutura(self):
        for caso, chaves in [("LL", [30, 20, 10]), ("RR", [10, 20, 30]),
                             ("LR", [30, 10, 20]), ("RL", [10, 30, 20])]:
            with self.subTest(caso=caso):
                arvore = ArvoreAVL(modo_detalhado=True)
                saida = io.StringIO()
                with redirect_stdout(saida):
                    for chave in chaves:
                        arvore.inserir(paciente(chave))
                texto = saida.getvalue()
                self.assertIn(f"Inserção do prontuário {chaves[-1]}", texto)
                self.assertIn(f"Desequilíbrio no prontuário {chaves[0]}", texto)
                self.assertIn(f"caso {caso}", texto)
                self.assertIn("Rotação à", texto)
                self.assertIn("Estrutura da árvore após a correção", texto)
                self.assertIn("Raiz: 20", texto)

    def test_modo_silencioso_e_exibir_nao_imprimem(self):
        arvore = ArvoreAVL()
        saida = io.StringIO()
        with redirect_stdout(saida):
            for chave in [30, 10, 20]:
                arvore.inserir(paciente(chave))
            arvore.remover(10)
            arvore.definir_modo_detalhado(True)
            texto = arvore.exibir()
            arvore.definir_modo_detalhado(False)
            arvore.inserir(paciente(40))
        self.assertEqual(saida.getvalue(), "")
        self.assertIn("Raiz:", texto)
        self.assertIn("E:", texto)
        self.assertIn("D:", texto)
        self.assertIn("h=", texto)
        self.assertIn("FB=", texto)

    def test_validacao_detecta_altura_quantidade_e_chaves_corrompidas(self):
        for campo, valor in [("altura", 999), ("altura", 2.0), ("altura", True),
                              ("prontuario", 0), ("prontuario", True),
                              ("prontuario", "20"), ("esquerda", object())]:
            with self.subTest(campo=campo, valor=valor):
                arvore = self.construir([20, 10, 30])
                setattr(arvore.raiz, campo, valor)
                self.assertFalse(arvore.validar())
        for quantidade in [0, 4, -1, True, 3.0]:
            arvore = self.construir([20, 10, 30])
            arvore._quantidade = quantidade
            self.assertFalse(arvore.validar())
        arvore = ArvoreAVL()
        arvore._quantidade = 1
        self.assertFalse(arvore.validar())

    def test_validacao_detecta_chave_alterada_no_paciente(self):
        arvore = ArvoreAVL()
        original = SimpleNamespace(prontuario=1)
        arvore.inserir(original)
        original.prontuario = 2
        self.assertFalse(arvore.validar())
        original.prontuario = True
        self.assertFalse(arvore.validar())

    def test_validacao_detecta_violacao_de_ancestral(self):
        arvore = self.construir([40, 20, 60, 10, 30, 50, 70])
        no = arvore.raiz.esquerda.direita
        no.paciente = paciente(45)
        no.prontuario = 45  # Maior que o pai 20, mas também maior que o ancestral 40.
        self.assertFalse(arvore.validar())

    def test_validacao_detecta_ciclos_e_nos_compartilhados(self):
        arvore = self.construir([20, 10, 30])
        arvore.raiz.esquerda = arvore.raiz
        self.assertFalse(arvore.validar())
        arvore = self.construir([20, 10, 30])
        arvore.raiz.direita = arvore.raiz.esquerda
        self.assertFalse(arvore.validar())

    def test_validacao_recalcula_equilibrio_em_estrutura_profunda(self):
        arvore = self.construir([1])
        tipo_no = type(arvore.raiz)
        raiz = None
        for chave in range(2000, 0, -1):
            no = tipo_no(paciente(chave))
            no.direita = raiz
            no.altura = 2001 - chave
            raiz = no
        arvore.raiz = raiz
        arvore._quantidade = 2000
        self.assertFalse(arvore.validar())  # Não lança RecursionError.

    def test_validacao_nao_modifica_estado_ou_metricas(self):
        arvore = self.construir([30, 10, 20])
        arvore.buscar(10)
        metricas, estrutura = arvore.estatisticas(), arvore.exibir()
        self.assertTrue(arvore.validar())
        self.assertEqual(arvore.estatisticas(), metricas)
        self.assertEqual(arvore.exibir(), estrutura)

    def test_insercoes_crescentes_decrescentes_e_aleatorias(self):
        crescente = list(range(1, 201))
        aleatoria = crescente.copy()
        random.Random(20261021).shuffle(aleatoria)
        for chaves in [crescente, crescente[::-1], aleatoria]:
            with self.subTest(inicio=chaves[:5]):
                arvore = self.construir(chaves)
                self.assertEqual([p.prontuario for p in arvore.em_ordem()], crescente)
                for chave in chaves:
                    self.assertTrue(arvore.remover(chave))
                    self.conferir_invariantes(arvore)
                self.assertIsNone(arvore.raiz)
                self.assertEqual(arvore.altura(), 0)
                self.assertTrue(arvore.inserir(paciente(1)))
                self.conferir_invariantes(arvore)

    def test_operacoes_mistas_contra_dicionario_de_referencia(self):
        for semente in [42, 20261021, 314159]:
            with self.subTest(semente=semente):
                rng = random.Random(semente)
                arvore, referencia = ArvoreAVL(), {}
                for _ in range(1200):
                    chave, operacao = rng.randint(1, 200), rng.randrange(3)
                    if operacao == 0:
                        novo = paciente(chave)
                        self.assertEqual(arvore.inserir(novo), chave not in referencia)
                        referencia.setdefault(chave, novo)
                    elif operacao == 1:
                        self.assertEqual(arvore.remover(chave), chave in referencia)
                        referencia.pop(chave, None)
                    else:
                        self.assertIs(arvore.buscar(chave), referencia.get(chave))
                    self.conferir_invariantes(arvore)
                    self.assertEqual([p.prontuario for p in arvore.em_ordem()], sorted(referencia))
                    for registro in arvore.em_ordem():
                        self.assertIs(registro, referencia[registro.prontuario])

    def test_dez_mil_registros_com_remocao_total(self):
        arvore = ArvoreAVL()
        n = 10000
        for chave in range(1, n + 1):
            self.assertTrue(arvore.inserir(paciente(chave)))
            if chave % 1000 == 0:
                self.conferir_invariantes(arvore)
        self.assertEqual(arvore.quantidade(), n)
        self.assertLessEqual(arvore.altura(), math.ceil(1.45 * math.log2(n + 2)))
        for chave in [1, n // 2, n, n + 1]:
            self.assertEqual(arvore.buscar(chave) is not None, chave <= n)
            self.assertLessEqual(arvore.nos_visitados_ultima_busca, arvore.altura())
        chaves = list(range(1, n + 1))
        random.Random(20261021).shuffle(chaves)
        for indice, chave in enumerate(chaves, 1):
            self.assertTrue(arvore.remover(chave))
            if indice % 1000 == 0:
                self.conferir_invariantes(arvore)
        self.assertEqual(arvore.quantidade(), 0)
        self.assertEqual(arvore.altura(), 0)
        self.assertIsNone(arvore.raiz)


if __name__ == "__main__":
    unittest.main()
