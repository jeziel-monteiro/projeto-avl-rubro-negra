"""Integração HTTP local com as árvores reais, sem dependências de navegador."""

import csv
from dataclasses import asdict
import hashlib
from http.client import HTTPConnection
from io import StringIO
import json
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch
import unicodedata
from urllib.parse import urlencode

from gerar_dados import gerar_pacientes
from interface.servidor import criar_servidor
from interface.servico import ServicoClinica


MAIOR_PRONTUARIO_SEGURO = 2**53 - 1


def dados_paciente(prontuario):
    return {
        "prontuario": prontuario,
        "nome": f"Paciente fictício {prontuario}",
        "data_nascimento": "2000-02-29",
        "telefone": "00900000000",
    }


class TestInterfaceHTTP(unittest.TestCase):
    def setUp(self):
        self.servico = ServicoClinica()
        self.servidor = criar_servidor(porta=0, servico=self.servico)
        self.porta = self.servidor.server_address[1]
        self.thread = Thread(
            target=self.servidor.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.encerrar_servidor)

    def encerrar_servidor(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def requisicao(self, metodo, caminho, dados=None, bruto=None, cabecalhos=None):
        headers = dict(cabecalhos or {})
        corpo = bruto
        if dados is not None:
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        if corpo is not None:
            headers.setdefault("Content-Type", "application/json")
        conexao = HTTPConnection("127.0.0.1", self.porta, timeout=5)
        try:
            conexao.request(metodo, caminho, body=corpo, headers=headers)
            resposta = conexao.getresponse()
            return (
                resposta.status,
                {nome.lower(): valor for nome, valor in resposta.getheaders()},
                resposta.read(),
            )
        finally:
            conexao.close()

    def json_http(self, metodo, caminho, dados=None, status=200, **opcoes):
        recebido, headers, corpo = self.requisicao(metodo, caminho, dados, **opcoes)
        self.assertEqual(recebido, status, corpo.decode("utf-8", errors="replace"))
        self.assertTrue(headers.get("content-type", "").startswith("application/json"))
        resposta = json.loads(corpo)
        self.assertIs(resposta["ok"], status < 400)
        return resposta

    def estado(self, arvore="AVL"):
        consulta = urlencode({"arvore": arvore})
        return self.json_http("GET", f"/api/estado?{consulta}")["estado"]

    def cadastrar(self, prontuario):
        return self.json_http("POST", "/api/pacientes", dados_paciente(prontuario))

    def conferir_colecao(self, estado, chaves):
        chaves = sorted(chaves)
        self.assertEqual([p["prontuario"] for p in estado["pacientes"]], chaves)
        self.assertEqual(set(estado["arvores"]), {"AVL", "Rubro-Negra"})
        for nome, arvore in estado["arvores"].items():
            with self.subTest(arvore=nome):
                self.assertEqual(arvore["quantidade"], len(chaves))
                self.assertTrue(arvore["valida"])
                self.assertEqual(arvore["percursos"]["em_ordem"], chaves)
                for percurso in arvore["percursos"].values():
                    self.assertEqual(sorted(percurso), chaves)
                if chaves:
                    self.assertEqual(arvore["minimo"]["prontuario"], chaves[0])
                    self.assertEqual(arvore["maximo"]["prontuario"], chaves[-1])
                else:
                    self.assertIsNone(arvore["minimo"])
                    self.assertIsNone(arvore["maximo"])

    def snapshot_clinica(self):
        clinica = self.servico.clinica
        return {
            "pacientes": dict(clinica._pacientes),
            "modos": dict(clinica.detalhado),
            "arvores": {
                nome: (
                    id(arvore), arvore.exibir(), arvore.estatisticas(),
                    arvore.em_ordem(), arvore._modo_detalhado,
                )
                for nome, arvore in clinica.arvores.items()
            },
        }

    def test_estado_inicial_e_consulta_nao_alteram_metricas(self):
        self.assertIs(self.servidor.servico, self.servico)
        antes = self.snapshot_clinica()
        for nome in ("AVL", "Rubro-Negra"):
            estado = self.estado(nome)
            self.conferir_colecao(estado, [])
            for arvore in estado["arvores"].values():
                self.assertIsNone(arvore["raiz"])
                self.assertEqual(arvore["altura"], 0)
        self.assertEqual(self.snapshot_clinica(), antes)

    def test_cadastro_atualiza_as_duas_arvores_e_rejeita_duplicata(self):
        paciente = dados_paciente(30)
        self.cadastrar(30)
        estado = self.estado()
        self.conferir_colecao(estado, [30])
        self.assertEqual(estado["pacientes"], [paciente])
        antes = self.snapshot_clinica()
        alterado = {**paciente, "nome": "Outro nome", "telefone": "outro telefone"}
        self.json_http("POST", "/api/pacientes", alterado, status=409)
        self.assertEqual(self.snapshot_clinica(), antes)
        self.assertEqual(self.estado()["pacientes"], [paciente])

    def test_campos_invalidos_nao_criam_cadastro_parcial(self):
        for alteracoes in (
            {"prontuario": True}, {"prontuario": "30"}, {"nome": " "},
            {"data_nascimento": "2001-02-29"}, {"telefone": ""},
        ):
            with self.subTest(alteracoes=alteracoes):
                self.json_http(
                    "POST", "/api/pacientes", {**dados_paciente(30), **alteracoes}, status=400
                )
                self.conferir_colecao(self.estado(), [])

    def test_maior_prontuario_seguro_permite_cadastro_busca_e_remocao(self):
        chave = MAIOR_PRONTUARIO_SEGURO
        estado = self.cadastrar(chave)["estado"]
        self.conferir_colecao(estado, [chave])
        self.assertEqual(estado["pacientes"][0]["prontuario"], chave)
        self.assertIs(type(estado["pacientes"][0]["prontuario"]), int)
        self.assertIsNone(estado["proximo_prontuario"])
        for nome in ("AVL", "Rubro-Negra"):
            resultado = self.json_http(
                "POST", "/api/buscar", {"prontuario": chave, "arvore": nome}
            )["resultado"]
            self.assertEqual(resultado["paciente"], dados_paciente(chave))
            self.assertEqual(resultado["nos_visitados"], 1)
        removido = self.json_http("POST", "/api/remover", {"prontuario": chave})
        self.conferir_colecao(removido["estado"], [])

    def test_prontuarios_inseguros_float_e_bool_sao_recusados_sem_alteracao(self):
        self.cadastrar(10)
        self.json_http("POST", "/api/buscar", {"prontuario": 10, "arvore": "AVL"})
        antes = self.snapshot_clinica()
        for chave in (MAIOR_PRONTUARIO_SEGURO + 1, True, False, 10.0):
            requisicoes = (
                ("/api/pacientes", dados_paciente(chave)),
                ("/api/buscar", {"prontuario": chave, "arvore": "Rubro-Negra"}),
                ("/api/remover", {"prontuario": chave}),
            )
            for rota, dados in requisicoes:
                with self.subTest(rota=rota, chave=chave, tipo=type(chave)):
                    self.json_http("POST", rota, dados, status=400)
                    self.assertEqual(self.snapshot_clinica(), antes)
        self.conferir_colecao(self.estado(), [10])

    def test_textos_com_html_permanecem_dados_json_dos_pacientes(self):
        paciente = {
            **dados_paciente(10),
            "nome": '<img src=x onerror="alert(1)"> & nome fictício',
            "telefone": "<script>alert('telefone fictício')</script>",
        }
        estado = self.json_http("POST", "/api/pacientes", paciente)["estado"]
        self.assertEqual(estado["pacientes"], [paciente])
        for nome in ("AVL", "Rubro-Negra"):
            resultado = self.json_http(
                "POST", "/api/buscar", {"prontuario": 10, "arvore": nome}
            )["resultado"]
            self.assertEqual(resultado["paciente"], paciente)

    def test_busca_chama_a_arvore_escolhida_e_registra_visitas_reais(self):
        for chave in (30, 10, 20):
            self.cadastrar(chave)
        clinica = self.servico.clinica
        arvore = clinica.arvores["Rubro-Negra"]
        with patch.object(arvore, "buscar", wraps=arvore.buscar) as buscar:
            resposta = self.json_http(
                "POST", "/api/buscar", {"prontuario": 10, "arvore": "Rubro-Negra"}
            )
        buscar.assert_called_once_with(10)
        resultado = resposta["resultado"]
        self.assertEqual(resultado["paciente"], dados_paciente(10))
        self.assertEqual(resultado["arvore"], "Rubro-Negra")
        self.assertEqual(resultado["nos_visitados"], 2)
        self.assertEqual(arvore.nos_visitados_ultima_busca, 2)
        self.assertEqual(clinica.arvores["AVL"].nos_visitados_ultima_busca, 0)
        ausente = self.json_http(
            "POST", "/api/buscar", {"prontuario": 999, "arvore": "Rubro-Negra"}
        )["resultado"]
        self.assertIsNone(ausente["paciente"])
        self.assertEqual(ausente["nos_visitados"], 2)
        self.conferir_colecao(self.estado(), [10, 20, 30])

    def test_remocao_atualiza_ambas_e_ausencia_preserva_estado(self):
        for chave in (10, 5, 15, 12):
            self.cadastrar(chave)
        self.json_http("POST", "/api/remover", {"prontuario": 5})
        self.conferir_colecao(self.estado(), [10, 12, 15])
        antes = self.snapshot_clinica()
        self.json_http("POST", "/api/remover", {"prontuario": 999}, status=400)
        self.assertEqual(self.snapshot_clinica(), antes)

    def test_serializacao_preserva_bst_cores_e_folhas_ausentes(self):
        for chave in (30, 10, 20, 5, 15, 25, 35):
            self.cadastrar(chave)
        estado = self.estado()
        chaves = [5, 10, 15, 20, 25, 30, 35]
        self.conferir_colecao(estado, chaves)
        for nome, arvore in estado["arvores"].items():
            vistos = []

            def percorrer(no, minimo, maximo):
                if no is None:
                    return 1
                self.assertIsInstance(no, dict)
                chave = no["chave"]
                self.assertIs(type(chave), int)
                self.assertLess(minimo, chave)
                self.assertLess(chave, maximo)
                if nome == "Rubro-Negra":
                    self.assertIn(no["cor"], ("preto", "vermelho"))
                    if no["cor"] == "vermelho":
                        for filho in (no["esquerda"], no["direita"]):
                            if filho is not None:
                                self.assertEqual(filho["cor"], "preto")
                esquerda = percorrer(no["esquerda"], minimo, chave)
                vistos.append(chave)
                direita = percorrer(no["direita"], chave, maximo)
                if nome == "Rubro-Negra":
                    self.assertEqual(esquerda, direita)
                    return esquerda + (no["cor"] == "preto")
                return 1 + max(esquerda, direita)

            percorrer(arvore["raiz"], float("-inf"), float("inf"))
            self.assertEqual(vistos, chaves)
            if nome == "Rubro-Negra":
                self.assertEqual(arvore["raiz"]["cor"], "preto")

    def test_logs_contem_rotacoes_e_recoloracoes_reais_sem_mudar_modos(self):
        modos = dict(self.servico.clinica.detalhado)
        for chave in (30, 10, 20):
            self.cadastrar(chave)
        estado = self.estado()
        texto = "\n".join(estado["logs"])
        normalizado = "".join(
            letra for letra in unicodedata.normalize("NFD", texto.lower())
            if unicodedata.category(letra) != "Mn"
        )
        self.assertIn("rotacao a esquerda no prontuario 10", normalizado)
        self.assertIn("rotacao a direita no prontuario 30", normalizado)
        self.assertIn("recoloracao do prontuario 20", normalizado)
        self.assertIn("caso", normalizado)
        self.assertIn("estrutura", normalizado)
        self.assertEqual(self.servico.clinica.detalhado, modos)
        for nome, arvore in self.servico.clinica.arvores.items():
            self.assertEqual(arvore._modo_detalhado, modos[nome])
        self.assertLessEqual(len(estado["logs"]), 200)

    def test_validacao_e_reset_de_metricas_preservam_pacientes_e_forma(self):
        for chave in (30, 10, 20):
            self.cadastrar(chave)
        self.json_http("POST", "/api/buscar", {"prontuario": 10, "arvore": "AVL"})
        antes = self.estado()
        self.json_http("POST", "/api/validar", {})
        depois = self.json_http("POST", "/api/metricas/reset", {})["estado"]
        self.conferir_colecao(depois, [10, 20, 30])
        for nome, arvore in depois["arvores"].items():
            self.assertEqual(arvore["raiz"], antes["arvores"][nome]["raiz"])
            self.assertTrue(all(valor == 0 for valor in arvore["estatisticas"].values()))

    def test_demonstracao_so_preenche_uma_clinica_vazia(self):
        estado = self.json_http("POST", "/api/demonstracao", {})["estado"]
        chaves = [p["prontuario"] for p in estado["pacientes"]]
        self.assertEqual(len(chaves), 12)
        self.assertEqual(len(set(chaves)), 12)
        self.conferir_colecao(estado, chaves)
        antes = self.snapshot_clinica()
        self.json_http("POST", "/api/demonstracao", {}, status=409)
        self.assertEqual(self.snapshot_clinica(), antes)

    def test_geracao_usa_semente_e_chaves_sem_colisao(self):
        self.cadastrar(90)
        estado = self.json_http("POST", "/api/gerar", {"quantidade": 3, "seed": 7})["estado"]
        esperados = [dados_paciente(90), *[asdict(p) for p in gerar_pacientes(3, 7, 91)]]
        self.assertEqual(estado["pacientes"], esperados)
        self.conferir_colecao(estado, [90, 91, 92, 93])

    def test_geracao_na_fronteira_segura_rejeita_lote_inteiro_sem_cadastro_parcial(self):
        penultimo = MAIOR_PRONTUARIO_SEGURO - 1
        self.cadastrar(penultimo)
        antes = self.snapshot_clinica()
        self.json_http("POST", "/api/gerar", {"quantidade": 2, "seed": 7}, status=400)
        self.assertEqual(self.snapshot_clinica(), antes)
        estado = self.json_http("POST", "/api/gerar", {"quantidade": 1, "seed": 7})["estado"]
        self.conferir_colecao(estado, [penultimo, MAIOR_PRONTUARIO_SEGURO])
        esperado = asdict(gerar_pacientes(1, 7, MAIOR_PRONTUARIO_SEGURO)[0])
        self.assertEqual(estado["pacientes"][-1], esperado)
        self.assertIsNone(estado["proximo_prontuario"])
        antes = self.snapshot_clinica()
        self.json_http("POST", "/api/gerar", {"quantidade": 1, "seed": 7}, status=400)
        self.assertEqual(self.snapshot_clinica(), antes)
        self.json_http("POST", "/api/gerar", {"quantidade": 0, "seed": 7})
        self.assertEqual(self.snapshot_clinica(), antes)

    def test_sementes_seguras_e_invalidas_preservam_o_estado_do_cadastro(self):
        self.cadastrar(10)
        antes = self.snapshot_clinica()
        for seed in (-MAIOR_PRONTUARIO_SEGURO, MAIOR_PRONTUARIO_SEGURO):
            self.json_http("POST", "/api/gerar", {"quantidade": 0, "seed": seed})
            self.assertEqual(self.snapshot_clinica(), antes)
        for seed in (-MAIOR_PRONTUARIO_SEGURO - 1, MAIOR_PRONTUARIO_SEGURO + 1, True, 1.0):
            for rota, dados in (
                ("/api/gerar", {"quantidade": 0, "seed": seed}),
                ("/api/experimentos", {"tamanho": 100, "seed": seed}),
            ):
                with self.subTest(rota=rota, seed=seed, tipo=type(seed)):
                    self.json_http("POST", rota, dados, status=400)
                    self.assertEqual(self.snapshot_clinica(), antes)

    def test_experimentos_sao_independentes_e_csv_permanece_em_memoria(self):
        historico = Path(__file__).resolve().parents[1] / "resultados" / "resultados.csv"
        bytes_antes = historico.read_bytes()
        hash_antes = hashlib.sha256(bytes_antes).hexdigest()
        for chave in (90, 70, 80):
            self.cadastrar(chave)
        self.json_http("POST", "/api/buscar", {"prontuario": 70, "arvore": "Rubro-Negra"})
        antes = self.snapshot_clinica()
        # Uma exportação para disco nesta rota violaria o contrato da interface.
        with patch("experimentos.exportar_csv", side_effect=AssertionError("CSV deve ficar em memória")):
            resposta = self.json_http("POST", "/api/experimentos", {"tamanho": 100, "seed": 42})
        resultados = resposta["resultado"]["resultados"]
        linhas = list(csv.DictReader(StringIO(resposta["resultado"]["csv_texto"])))
        self.assertEqual(len(resultados), 14)
        self.assertEqual(len(linhas), 14)
        self.assertEqual({r["arvore"] for r in resultados}, {"AVL", "Rubro-Negra"})
        for resultado in resultados:
            self.assertIs(resultado["valido"], True)
            self.assertEqual(resultado["seed"], 42)
            self.assertEqual(resultado["quantidade_inicial"], 100)
            self.assertGreaterEqual(resultado["tempo_segundos"], 0)
            self.assertIn("altura_inicial", resultado)
        self.assertEqual(self.snapshot_clinica(), antes)
        self.conferir_colecao(resposta["estado"], [70, 80, 90])
        self.assertEqual(historico.read_bytes(), bytes_antes)
        self.assertEqual(hashlib.sha256(historico.read_bytes()).hexdigest(), hash_antes)
        self.json_http("POST", "/api/experimentos", {"tamanho": 20, "seed": 42}, status=400)
        self.assertEqual(self.snapshot_clinica(), antes)

    def test_estaticos_conhecidos_e_rotas_nao_expoem_arquivos_do_projeto(self):
        for caminho, tipo in (
            ("/", "text/html"), ("/styles.css", "text/css"),
            ("/app.js", "javascript"), ("/favicon.svg", "image/svg+xml"),
        ):
            with self.subTest(caminho=caminho):
                status, headers, corpo = self.requisicao("GET", caminho)
                self.assertEqual(status, 200)
                self.assertIn(tipo, headers["content-type"])
                self.assertTrue(corpo)
        for caminho in ("/../main.py", "/%2e%2e/main.py", "/README.md", "/servico.py"):
            with self.subTest(caminho=caminho):
                self.json_http("GET", caminho, status=404)

    def test_origem_externa_e_host_externo_sao_recusados(self):
        self.json_http(
            "POST", "/api/pacientes", dados_paciente(10), status=403,
            cabecalhos={"Origin": "https://exemplo.invalid"},
        )
        self.json_http(
            "GET", "/api/estado", status=403,
            cabecalhos={"Host": "exemplo.invalid"},
        )
        self.conferir_colecao(self.estado(), [])
        origem = f"http://127.0.0.1:{self.porta}"
        self.json_http(
            "POST", "/api/pacientes", dados_paciente(10), cabecalhos={"Origin": origem}
        )
        self.conferir_colecao(self.estado(), [10])

    def test_json_malformado_nao_objeto_e_tipo_incorreto_sao_recusados(self):
        for corpo in (b"{invalido", b"[]", b"null", b'"texto"'):
            with self.subTest(corpo=corpo):
                self.json_http("POST", "/api/pacientes", status=400, bruto=corpo)
                self.conferir_colecao(self.estado(), [])
        self.json_http(
            "POST", "/api/pacientes", dados_paciente(10), status=415,
            cabecalhos={"Content-Type": "text/plain"},
        )
        self.json_http("POST", "/api/pacientes", status=413, bruto=b" " * 65_537)
        self.conferir_colecao(self.estado(), [])

    def test_rotas_e_arvore_desconhecidas_nao_modificam_estado(self):
        antes = self.snapshot_clinica()
        self.json_http("GET", "/api/inexistente", status=404)
        self.json_http("POST", "/api/inexistente", {}, status=404)
        self.json_http("GET", "/api/estado?arvore=desconhecida", status=400)
        self.json_http(
            "POST", "/api/buscar", {"prontuario": 10, "arvore": "desconhecida"}, status=400
        )
        self.assertEqual(self.snapshot_clinica(), antes)


class TestServidorLocal(unittest.TestCase):
    def test_recusa_exposicao_fora_do_loopback(self):
        with self.assertRaises(ValueError):
            criar_servidor(host="0.0.0.0", porta=0)


if __name__ == "__main__":
    unittest.main()
