from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
import math
import random
import unittest
import unicodedata

from rubro_negra import ArvoreRubroNegra, PRETO, VERMELHO


@dataclass
class PacienteTeste:
    prontuario: int
    nome: str = "Paciente de teste"
    data_nascimento: str = "2000-01-01"
    telefone: str = "(92) 99999-0000"


CAMPOS_ESTATISTICAS = {
    "rotacoes_insercao",
    "rotacoes_remocao",
    "recoloracoes_insercao",
    "recoloracoes_remocao",
    "nos_visitados_ultima_busca",
}


class TestArvoreRubroNegra(unittest.TestCase):
    def criar_arvore(self, chaves=()):
        arvore = ArvoreRubroNegra()
        pacientes = {}
        for chave in chaves:
            paciente = PacienteTeste(chave, nome=f"Paciente {chave}")
            self.assertTrue(arvore.inserir(paciente))
            pacientes[chave] = paciente
        return arvore, pacientes

    def conferir_invariantes(self, arvore, esperados):
        """Confere ordenação, cores, altura negra e referências sem o validador."""
        nil = arvore._nil
        self.assertEqual(nil.cor, PRETO)
        self.assertIs(nil.esquerda, nil)
        self.assertIs(nil.direita, nil)
        self.assertIs(nil.pai, nil)
        vistos = set()
        chaves_em_ordem = []

        def percorrer(no, pai, limite_inferior, limite_superior):
            if no is nil:
                return 1, 0
            self.assertNotIn(id(no), vistos, "Um nó não pode ser visitado duas vezes")
            vistos.add(id(no))
            self.assertIs(no.pai, pai)
            self.assertIn(no.cor, (PRETO, VERMELHO))
            self.assertGreater(no.prontuario, limite_inferior)
            self.assertLess(no.prontuario, limite_superior)
            self.assertIs(type(no.prontuario), int)
            self.assertEqual(no.paciente.prontuario, no.prontuario)
            self.assertIs(no.paciente, esperados[no.prontuario])
            if no.cor == VERMELHO:
                self.assertEqual(no.esquerda.cor, PRETO)
                self.assertEqual(no.direita.cor, PRETO)
            negra_esquerda, altura_esquerda = percorrer(
                no.esquerda, no, limite_inferior, no.prontuario
            )
            chaves_em_ordem.append(no.prontuario)
            negra_direita, altura_direita = percorrer(
                no.direita, no, no.prontuario, limite_superior
            )
            self.assertEqual(negra_esquerda, negra_direita)
            return (
                negra_esquerda + (no.cor == PRETO),
                1 + max(altura_esquerda, altura_direita),
            )

        if arvore.raiz is not nil:
            self.assertEqual(arvore.raiz.cor, PRETO)
            self.assertIs(arvore.raiz.pai, nil)
        _, altura = percorrer(arvore.raiz, nil, -math.inf, math.inf)
        self.assertEqual(chaves_em_ordem, sorted(esperados))
        self.assertEqual(arvore.quantidade(), len(esperados))
        self.assertEqual(len(vistos), len(esperados))
        self.assertEqual(arvore.altura(), altura)
        self.assertEqual(
            [paciente.prontuario for paciente in arvore.em_ordem()],
            sorted(esperados),
        )
        if esperados:
            self.assertLessEqual(altura, 2 * math.log2(len(esperados) + 1))
            self.assertIs(arvore.minimo(), esperados[min(esperados)])
            self.assertIs(arvore.maximo(), esperados[max(esperados)])
        else:
            self.assertIsNone(arvore.minimo())
            self.assertIsNone(arvore.maximo())
        self.assertTrue(arvore.validar())

    def test_arvore_vazia_e_estatisticas_iniciais(self):
        arvore, pacientes = self.criar_arvore()
        self.conferir_invariantes(arvore, pacientes)
        self.assertEqual(arvore.pre_ordem(), [])
        self.assertEqual(arvore.pos_ordem(), [])
        self.assertIsNone(arvore.buscar(1))
        self.assertFalse(arvore.remover(1))
        self.assertEqual(arvore.nos_visitados_ultima_busca, 0)
        estatisticas = arvore.estatisticas()
        self.assertEqual(set(estatisticas), CAMPOS_ESTATISTICAS)
        self.assertTrue(all(type(valor) is int for valor in estatisticas.values()))
        self.assertTrue(all(valor == 0 for valor in estatisticas.values()))
        self.assertIsInstance(arvore.exibir(), str)
        self.assertTrue(arvore.exibir().strip())

    def test_insercao_unica_e_remocao_da_ultima_raiz(self):
        arvore, pacientes = self.criar_arvore([42])
        self.conferir_invariantes(arvore, pacientes)
        self.assertEqual(arvore.altura(), 1)
        self.assertIs(arvore.buscar(42), pacientes[42])
        self.assertEqual(arvore.nos_visitados_ultima_busca, 1)
        self.assertEqual(arvore.estatisticas()["recoloracoes_insercao"], 1)
        self.assertTrue(arvore.remover(42))
        self.conferir_invariantes(arvore, {})
        self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)
        self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 0)
        self.assertFalse(arvore.remover(42))

    def test_quatro_casos_de_rotacao_na_insercao(self):
        casos = (
            ((30, 20, 10), 1),  # Esquerda-esquerda.
            ((10, 20, 30), 1),  # Direita-direita.
            ((30, 10, 20), 2),  # Esquerda-direita.
            ((10, 30, 20), 2),  # Direita-esquerda.
        )
        for chaves, rotacoes in casos:
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                self.conferir_invariantes(arvore, pacientes)
                self.assertEqual(arvore.raiz.prontuario, 20)
                self.assertEqual(arvore.raiz.esquerda.prontuario, 10)
                self.assertEqual(arvore.raiz.direita.prontuario, 30)
                self.assertEqual(arvore.raiz.esquerda.cor, VERMELHO)
                self.assertEqual(arvore.raiz.direita.cor, VERMELHO)
                self.assertEqual(arvore.estatisticas()["rotacoes_insercao"], rotacoes)
                self.assertEqual(arvore.estatisticas()["recoloracoes_insercao"], 3)

    def test_tio_vermelho_recolore_sem_rotacionar(self):
        for chaves in ([10, 5, 15, 1], [10, 5, 15, 20]):
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                self.conferir_invariantes(arvore, pacientes)
                self.assertEqual(arvore.estatisticas()["rotacoes_insercao"], 0)
                # Raiz inicial + pai + tio + avô + raiz novamente.
                self.assertEqual(arvore.estatisticas()["recoloracoes_insercao"], 5)

    def test_duplicata_preserva_paciente_original_e_metricas(self):
        arvore, pacientes = self.criar_arvore([20, 10, 30])
        original = pacientes[10]
        estatisticas_antes = arvore.estatisticas()
        substituto = PacienteTeste(10, "Outro nome", "1999-12-31", "outro telefone")
        self.assertFalse(arvore.inserir(substituto))
        self.assertEqual(arvore.estatisticas(), estatisticas_antes)
        self.assertIs(arvore.buscar(10), original)
        self.assertEqual(original.nome, "Paciente 10")
        self.assertEqual(original.data_nascimento, "2000-01-01")
        self.assertEqual(original.telefone, "(92) 99999-0000")
        self.conferir_invariantes(arvore, pacientes)

    def test_prontuarios_invalidos_sao_rejeitados(self):
        arvore, pacientes = self.criar_arvore([10])
        for chave in (True, False, 0, -1, 1.0, 10.0, "10", None):
            with self.subTest(chave=chave, tipo=type(chave)):
                antes = arvore.estatisticas()
                self.assertFalse(arvore.inserir(PacienteTeste(chave)))
                self.assertFalse(arvore.remover(chave))
                self.assertEqual(arvore.estatisticas(), antes)
                arvore.buscar(10)
                self.assertIsNone(arvore.buscar(chave))
                self.assertEqual(arvore.nos_visitados_ultima_busca, 0)
                self.assertEqual(
                    arvore.estatisticas()["nos_visitados_ultima_busca"], 0
                )
        for objeto in (None, object(), 10, "paciente", {}):
            with self.subTest(objeto=objeto):
                self.assertFalse(arvore.inserir(objeto))
        self.conferir_invariantes(arvore, pacientes)

    def test_percursos_minimo_maximo_e_identidade(self):
        arvore, pacientes = self.criar_arvore([10, 5, 15, 2, 7, 12, 18])
        casos = (
            (arvore.pre_ordem, [10, 5, 2, 7, 15, 12, 18]),
            (arvore.em_ordem, [2, 5, 7, 10, 12, 15, 18]),
            (arvore.pos_ordem, [2, 7, 5, 12, 18, 15, 10]),
        )
        for percurso, chaves in casos:
            resultado = percurso()
            self.assertIsInstance(resultado, list)
            self.assertEqual([paciente.prontuario for paciente in resultado], chaves)
            for paciente, chave in zip(resultado, chaves):
                self.assertIs(paciente, pacientes[chave])
        self.assertIs(arvore.minimo(), pacientes[2])
        self.assertIs(arvore.maximo(), pacientes[18])
        self.assertEqual(arvore.altura(), 3)
        self.assertTrue(arvore.remover(2))
        self.assertTrue(arvore.remover(18))
        del pacientes[2], pacientes[18]
        self.assertIs(arvore.minimo(), pacientes[5])
        self.assertIs(arvore.maximo(), pacientes[15])
        self.conferir_invariantes(arvore, pacientes)

    def test_busca_conta_apenas_nos_reais_visitados(self):
        arvore, pacientes = self.criar_arvore([20, 10, 30, 5, 15, 25, 35])
        for chave, visitas in ((20, 1), (10, 2), (5, 3), (12, 3), (100, 3)):
            with self.subTest(chave=chave):
                self.assertIs(arvore.buscar(chave), pacientes.get(chave))
                self.assertEqual(arvore.nos_visitados_ultima_busca, visitas)
                self.assertEqual(
                    arvore.estatisticas()["nos_visitados_ultima_busca"], visitas
                )
        arvore.buscar(5)
        self.assertTrue(arvore.inserir(PacienteTeste(40)))
        self.assertFalse(arvore.inserir(PacienteTeste(20)))
        self.assertTrue(arvore.remover(25))
        self.assertFalse(arvore.remover(99))
        arvore.minimo()
        arvore.maximo()
        arvore.pre_ordem()
        arvore.em_ordem()
        arvore.pos_ordem()
        arvore.altura()
        arvore.exibir()
        arvore.validar()
        self.assertEqual(arvore.nos_visitados_ultima_busca, 3)

    def test_remocao_de_folha_vermelha_nao_exige_balanceamento(self):
        arvore, pacientes = self.criar_arvore([10, 5, 15])
        arvore.reiniciar_estatisticas()
        self.assertTrue(arvore.remover(5))
        del pacientes[5]
        self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)
        self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 0)
        self.conferir_invariantes(arvore, pacientes)

    def test_remocao_de_no_preto_com_filho_vermelho(self):
        for chaves, removido in (([10, 5], 10), ([10, 15], 10), ([20, 10, 30, 5], 10)):
            with self.subTest(chaves=chaves, removido=removido):
                arvore, pacientes = self.criar_arvore(chaves)
                arvore.reiniciar_estatisticas()
                self.assertTrue(arvore.remover(removido))
                del pacientes[removido]
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)
                self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 1)
                self.conferir_invariantes(arvore, pacientes)

    def test_remocao_de_folha_preta_com_sobrinho_distante_vermelho(self):
        for chaves, removido in (([10, 5, 15, 20], 5), ([10, 5, 15, 1], 15)):
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                arvore.reiniciar_estatisticas()
                self.assertTrue(arvore.remover(removido))
                del pacientes[removido]
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 1)
                self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 1)
                self.conferir_invariantes(arvore, pacientes)

    def test_remocao_com_sobrinho_proximo_vermelho_e_seu_espelho(self):
        for chaves, removido in (([10, 5, 15, 12], 5), ([10, 5, 15, 7], 15)):
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                arvore.reiniciar_estatisticas()
                self.assertTrue(arvore.remover(removido))
                del pacientes[removido]
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 2)
                self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 3)
                self.conferir_invariantes(arvore, pacientes)

    def test_remocao_com_irmao_preto_sem_filhos_vermelhos(self):
        for chaves, primeira, segunda in (
            ([10, 5, 15, 1], 1, 5),
            ([10, 5, 15, 20], 20, 15),
        ):
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                self.assertTrue(arvore.remover(primeira))
                del pacientes[primeira]
                arvore.reiniciar_estatisticas()
                self.assertTrue(arvore.remover(segunda))
                del pacientes[segunda]
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)
                self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 1)
                self.conferir_invariantes(arvore, pacientes)

    def test_remocao_com_irmao_vermelho_e_seu_espelho(self):
        base = [7, 3, 18, 10, 22, 8, 11, 26]
        for chaves, removido in ((base, 3), ([40 - chave for chave in base], 37)):
            with self.subTest(chaves=chaves):
                arvore, pacientes = self.criar_arvore(chaves)
                arvore.reiniciar_estatisticas()
                self.assertTrue(arvore.remover(removido))
                del pacientes[removido]
                self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 2)
                self.conferir_invariantes(arvore, pacientes)

    def test_remocao_de_dois_filhos_preserva_objetos_e_conta_heranca_de_cor(self):
        # O sucessor vermelho (15) assume a cor preta da raiz removida (10).
        arvore, pacientes = self.criar_arvore([10, 5, 15])
        arvore.reiniciar_estatisticas()
        self.assertTrue(arvore.remover(10))
        del pacientes[10]
        self.assertIs(arvore.raiz.paciente, pacientes[15])
        self.assertEqual(arvore.estatisticas()["recoloracoes_remocao"], 1)
        self.assertEqual(arvore.estatisticas()["rotacoes_remocao"], 0)
        self.conferir_invariantes(arvore, pacientes)

    def test_remocao_da_raiz_com_sucessor_profundo(self):
        chaves = [20, 10, 40, 5, 15, 30, 50, 25, 35, 23, 27, 24]
        arvore, pacientes = self.criar_arvore(chaves)
        # Garante que este cenário realmente exercita um sucessor não imediato.
        alvo = arvore.raiz
        sucessor = alvo.direita
        self.assertIsNot(sucessor.esquerda, arvore._nil)
        while sucessor.esquerda is not arvore._nil:
            sucessor = sucessor.esquerda
        chave_removida = alvo.prontuario
        self.assertTrue(arvore.remover(chave_removida))
        del pacientes[chave_removida]
        self.conferir_invariantes(arvore, pacientes)
        for chave, paciente in pacientes.items():
            self.assertIs(arvore.buscar(chave), paciente)

    def test_remocao_com_sucessor_profundo_que_possui_filho_direito(self):
        chaves = [20, 10, 40, 5, 15, 30, 50, 25, 35, 23, 27, 24]
        arvore, pacientes = self.criar_arvore(chaves)
        alvo = arvore.raiz.esquerda
        self.assertEqual(alvo.prontuario, 20)
        sucessor = alvo.direita.esquerda
        self.assertEqual(sucessor.prontuario, 23)
        self.assertEqual(sucessor.direita.prontuario, 24)
        self.assertTrue(arvore.remover(20))
        del pacientes[20]
        self.conferir_invariantes(arvore, pacientes)
        self.assertIs(arvore.buscar(23), pacientes[23])
        self.assertIs(arvore.buscar(24), pacientes[24])

    def test_reiniciar_estatisticas_preserva_arvore_e_modo_detalhado(self):
        arvore, pacientes = self.criar_arvore([30, 20, 10, 5, 15])
        arvore.buscar(5)
        antes = arvore.exibir()
        arvore.definir_modo_detalhado(True)
        arvore.reiniciar_estatisticas()
        self.assertTrue(all(valor == 0 for valor in arvore.estatisticas().values()))
        self.assertEqual(arvore.nos_visitados_ultima_busca, 0)
        self.assertEqual(arvore.exibir(), antes)
        self.conferir_invariantes(arvore, pacientes)
        saida = StringIO()
        with redirect_stdout(saida):
            self.assertTrue(arvore.inserir(PacienteTeste(1)))
        self.assertTrue(saida.getvalue().strip())

    def test_estatisticas_retornam_copia_e_instancias_sao_independentes(self):
        primeira, pacientes = self.criar_arvore([30, 20, 10])
        segunda = ArvoreRubroNegra()
        self.assertIsNot(primeira._nil, segunda._nil)
        copia = primeira.estatisticas()
        copia["rotacoes_insercao"] = 999
        self.assertEqual(primeira.estatisticas()["rotacoes_insercao"], 1)
        self.assertTrue(all(valor == 0 for valor in segunda.estatisticas().values()))
        self.assertTrue(segunda.inserir(PacienteTeste(20, "Segunda árvore")))
        self.assertTrue(segunda.remover(20))
        self.conferir_invariantes(primeira, pacientes)
        self.conferir_invariantes(segunda, {})

    def test_saida_padrao_silenciosa_e_exibir_retorna_texto(self):
        saida = StringIO()
        with redirect_stdout(saida):
            arvore, pacientes = self.criar_arvore([10, 5, 15, 1])
            arvore.buscar(5)
            representacao = arvore.exibir()
            arvore.validar()
            self.assertTrue(arvore.remover(15))
        self.assertEqual(saida.getvalue(), "")
        self.assertIsInstance(representacao, str)
        for chave in pacientes:
            self.assertRegex(representacao, rf"\b{chave}\b")
        self.assertGreater(len(representacao.splitlines()), 1)

    def test_modo_detalhado_mostra_contexto_rotacoes_cores_e_estrutura(self):
        saida = StringIO()
        with redirect_stdout(saida):
            arvore = ArvoreRubroNegra(modo_detalhado=True)
            for chave in (10, 5, 15, 1):
                self.assertTrue(arvore.inserir(PacienteTeste(chave)))
            self.assertTrue(arvore.remover(15))
        texto_original = saida.getvalue()
        texto = "".join(
            caractere
            for caractere in unicodedata.normalize("NFD", texto_original.lower())
            if unicodedata.category(caractere) != "Mn"
        )
        for chave in (10, 5, 15, 1):
            self.assertRegex(texto, rf"\b{chave}\b")
        self.assertRegex(texto, r"inser")
        self.assertRegex(texto, r"remo")
        self.assertIn("caso", texto)
        self.assertRegex(texto, r"esquerda|direita")
        self.assertRegex(texto, r"rotac|rotacion")
        self.assertRegex(texto, r"preto|vermelho")
        self.assertRegex(texto, r"arvore|estrutura")
        arvore.definir_modo_detalhado(False)
        saida = StringIO()
        with redirect_stdout(saida):
            arvore.inserir(PacienteTeste(20))
            arvore.remover(1)
        self.assertEqual(saida.getvalue(), "")

    def test_validar_detecta_corrupcoes_sem_travar(self):
        def corromper_contagem(arvore):
            arvore._quantidade += 1

        def trocar_filhos(arvore):
            raiz = arvore.raiz
            raiz.esquerda, raiz.direita = raiz.direita, raiz.esquerda

        corrupcoes = {
            "raiz vermelha": lambda a: setattr(a.raiz, "cor", VERMELHO),
            "cor inexistente": lambda a: setattr(a.raiz.esquerda, "cor", "azul"),
            "ordenacao": trocar_filhos,
            "altura negra": lambda a: setattr(a.raiz.direita, "cor", VERMELHO),
            "vermelhos consecutivos": lambda a: setattr(a.raiz.esquerda, "cor", VERMELHO),
            "pai incorreto": lambda a: setattr(a.raiz.esquerda, "pai", a._nil),
            "pai da raiz": lambda a: setattr(a.raiz, "pai", a.raiz),
            "ciclo": lambda a: setattr(a.raiz, "esquerda", a.raiz),
            "filho ausente": lambda a: setattr(a.raiz, "direita", None),
            "sentinela vermelha": lambda a: setattr(a._nil, "cor", VERMELHO),
            "contagem": corromper_contagem,
            "prontuario do paciente alterado": lambda a: setattr(
                a.raiz.paciente, "prontuario", 999
            ),
        }
        for descricao, corromper in corrupcoes.items():
            with self.subTest(corrupcao=descricao):
                arvore, _ = self.criar_arvore([10, 5, 15, 1])
                self.assertTrue(arvore.validar())
                corromper(arvore)
                self.assertFalse(arvore.validar())

    def test_validar_rejeita_tipo_invalido_mesmo_com_igualdade_numerica(self):
        # Python considera 1 == 1.0 == True; isso não os torna chaves válidas.
        for prontuario in (1.0, True):
            with self.subTest(campo="paciente.prontuario", prontuario=prontuario):
                arvore, pacientes = self.criar_arvore([1])
                pacientes[1].prontuario = prontuario
                self.assertFalse(arvore.validar())
        for prontuario in (0, -1, True, 1.0, "1", None):
            with self.subTest(campo="no.prontuario", prontuario=prontuario):
                arvore, _ = self.criar_arvore([1])
                arvore.raiz.prontuario = prontuario
                self.assertFalse(arvore.validar())

    def test_sequencias_crescente_decrescente_e_aleatoria(self):
        aleatorias = list(range(1, 151))
        random.Random(20261021).shuffle(aleatorias)
        sequencias = (
            list(range(1, 151)),
            list(range(150, 0, -1)),
            aleatorias,
        )
        for indice, chaves in enumerate(sequencias):
            with self.subTest(sequencia=indice):
                arvore = ArvoreRubroNegra()
                pacientes = {}
                for chave in chaves:
                    paciente = PacienteTeste(chave)
                    self.assertTrue(arvore.inserir(paciente))
                    pacientes[chave] = paciente
                    self.conferir_invariantes(arvore, pacientes)
                remocoes = chaves.copy()
                random.Random(91 + indice).shuffle(remocoes)
                for chave in remocoes:
                    self.assertTrue(arvore.remover(chave))
                    del pacientes[chave]
                    self.conferir_invariantes(arvore, pacientes)

    def test_operacoes_mistas_contra_dicionario_de_referencia(self):
        for semente in (7, 42, 20261021):
            with self.subTest(semente=semente):
                aleatorio = random.Random(semente)
                arvore = ArvoreRubroNegra()
                referencia = {}
                for passo in range(1000):
                    chave = aleatorio.randint(1, 120)
                    operacao = aleatorio.choice(("inserir", "remover", "buscar"))
                    with self.subTest(passo=passo, operacao=operacao, chave=chave):
                        if operacao == "inserir":
                            paciente = PacienteTeste(chave, f"Paciente do passo {passo}")
                            novo = chave not in referencia
                            self.assertEqual(arvore.inserir(paciente), novo)
                            if novo:
                                referencia[chave] = paciente
                        elif operacao == "remover":
                            existia = chave in referencia
                            self.assertEqual(arvore.remover(chave), existia)
                            referencia.pop(chave, None)
                        else:
                            self.assertIs(arvore.buscar(chave), referencia.get(chave))
                            self.assertLessEqual(
                                arvore.nos_visitados_ultima_busca, arvore.altura()
                            )
                        self.conferir_invariantes(arvore, referencia)

    def test_dez_mil_prontuarios_com_validacao_amostrada(self):
        quantidade = 10_000
        chaves = list(range(1, quantidade + 1))
        random.Random(1984).shuffle(chaves)
        arvore = ArvoreRubroNegra()
        referencia = {}
        # Somente dez verificações completas por fase: evita custo quadrático.
        for indice, chave in enumerate(chaves, start=1):
            paciente = PacienteTeste(chave)
            self.assertTrue(arvore.inserir(paciente))
            referencia[chave] = paciente
            if indice % 1000 == 0:
                self.conferir_invariantes(arvore, referencia)
        for chave in (1, 2, 5000, 9999, 10_000, 10_001):
            self.assertIs(arvore.buscar(chave), referencia.get(chave))
            self.assertLessEqual(arvore.nos_visitados_ultima_busca, arvore.altura())
        random.Random(2026).shuffle(chaves)
        for indice, chave in enumerate(chaves, start=1):
            self.assertTrue(arvore.remover(chave))
            del referencia[chave]
            if indice % 1000 == 0:
                self.conferir_invariantes(arvore, referencia)


if __name__ == "__main__":
    unittest.main()
