"""Adapta a clínica existente para JSON; não implementa operações de árvores."""

from collections import deque
from contextlib import contextmanager, redirect_stdout
import csv
from dataclasses import asdict, fields, replace
from io import StringIO
from threading import RLock

from experimentos import Resultado, executar_experimentos
from gerar_dados import gerar_pacientes
from main import Clinica
from modelos import Paciente


LIMITE_PACIENTES = 500
LIMITE_PERCURSO = 1000
LIMITE_LOGS = 200
MAX_INTEIRO_JSON = 2 ** 53 - 1
ARVORES = ("AVL", "Rubro-Negra")


class ErroRequisicao(ValueError):
    """Erro esperado da API, com o status HTTP que explica a recusa."""

    def __init__(self, mensagem: str, status: int = 400) -> None:
        super().__init__(mensagem)
        self.status = status


class _CapturaLogs:
    """Mantém apenas as últimas linhas, mesmo durante a geração de um lote."""

    def __init__(self) -> None:
        self.linhas: deque[str] = deque(maxlen=LIMITE_LOGS)
        self.pendente = ""

    def write(self, texto: str) -> int:
        partes = (self.pendente + texto).split("\n")
        self.pendente = partes.pop()
        self.linhas.extend(linha for linha in partes if linha)
        return len(texto)

    def flush(self) -> None:
        pass


class ServicoClinica:
    """Um cadastro compartilhado por todas as abas, protegido por um único lock."""

    def __init__(self, clinica: Clinica | None = None) -> None:
        self.clinica = clinica if clinica is not None else Clinica()
        self.clinica.exigir_disponibilidade()
        self._lock = RLock()
        self._logs: deque[str] = deque(maxlen=LIMITE_LOGS)

    @staticmethod
    def _inteiro(dados: dict, campo: str, padrao=None, minimo=None, maximo=None) -> int:
        valor = dados.get(campo, padrao)
        if type(valor) is not int:
            raise ErroRequisicao(f"{campo} deve ser um inteiro, sem booleanos.")
        if not -MAX_INTEIRO_JSON <= valor <= MAX_INTEIRO_JSON:
            raise ErroRequisicao(
                f"{campo} deve estar entre {-MAX_INTEIRO_JSON} e {MAX_INTEIRO_JSON} "
                "para ser representado exatamente no navegador."
            )
        if minimo is not None and valor < minimo:
            raise ErroRequisicao(f"{campo} deve ser maior ou igual a {minimo}.")
        if maximo is not None and valor > maximo:
            raise ErroRequisicao(f"{campo} deve ser menor ou igual a {maximo}.")
        return valor

    @staticmethod
    def _arvore(nome: str) -> str:
        if nome not in ARVORES:
            raise ErroRequisicao("Selecione AVL ou Rubro-Negra.")
        return nome

    def _conferir_limite(self, quantidade: int) -> None:
        atual = self.clinica.arvores["AVL"].quantidade()
        if atual + quantidade > LIMITE_PACIENTES:
            raise ErroRequisicao(
                f"A visualização permite até {LIMITE_PACIENTES} pacientes cadastrados.", 409,
            )

    @contextmanager
    def _capturar_alteracao(self, descricao: str):
        captura = _CapturaLogs()
        modos = {nome: bool(getattr(arvore, "_modo_detalhado", self.clinica.detalhado[nome]))
                 for nome, arvore in self.clinica.arvores.items()}
        with redirect_stdout(captura):
            try:
                for arvore in self.clinica.arvores.values():
                    arvore.definir_modo_detalhado(True)
                yield
            finally:
                # A recuperação de falha parcial pode ter substituído as instâncias.
                for nome, arvore in self.clinica.arvores.items():
                    arvore.definir_modo_detalhado(modos[nome])
                self._logs.extend(captura.linhas)
                if captura.pendente:
                    self._logs.append(captura.pendente)
                self._logs.append(f"{descricao} — AVL e Rubro-Negra")

    @staticmethod
    def _serializar_no(no, visitados: set[int]) -> dict | None:
        if no is None or getattr(no, "paciente", None) is None:
            return None
        if id(no) in visitados or len(visitados) >= LIMITE_PERCURSO:
            raise ErroRequisicao("Estrutura inválida ou acima do limite de visualização.", 409)
        visitados.add(id(no))
        chave = ServicoClinica._inteiro({"prontuario": no.prontuario}, "prontuario", minimo=1)
        dados = {"chave": chave,
                 "esquerda": ServicoClinica._serializar_no(no.esquerda, visitados),
                 "direita": ServicoClinica._serializar_no(no.direita, visitados)}
        if hasattr(no, "cor"):
            dados["cor"] = no.cor
        return dados

    def estado(self, arvore: str = "AVL") -> dict:
        """Só consulta a estrutura; não usa buscar() nem altera as estatísticas."""
        self._arvore(arvore)
        with self._lock:
            self.clinica.exigir_disponibilidade()
            arvores = {}
            for nome, instancia in self.clinica.arvores.items():
                minimo, maximo = instancia.minimo(), instancia.maximo()
                arvores[nome] = {
                    "altura": instancia.altura(), "quantidade": instancia.quantidade(),
                    "estatisticas": instancia.estatisticas(), "valida": instancia.validar(),
                    "raiz": self._serializar_no(instancia.raiz, set()),
                    "percursos": {metodo: [p.prontuario for p in getattr(instancia, metodo)()]
                                  [:LIMITE_PERCURSO]
                                  for metodo in ("pre_ordem", "em_ordem", "pos_ordem")},
                    "minimo": asdict(minimo) if minimo is not None else None,
                    "maximo": asdict(maximo) if maximo is not None else None,
                }
            proximo = self.clinica.proximo_prontuario()
            return {
                "pacientes": [asdict(p) for p in self.clinica.arvores["AVL"].em_ordem()],
                "arvores": arvores,
                "proximo_prontuario": proximo if proximo <= MAX_INTEIRO_JSON else None,
                "logs": list(self._logs),
            }

    def executar(self, rota: str, dados: dict) -> dict:
        """Executa uma ação e produz seu snapshot dentro da mesma região crítica."""
        acoes = {
            "/api/pacientes": self._cadastrar, "/api/remover": self._remover,
            "/api/buscar": self._buscar, "/api/demonstracao": self._demonstracao,
            "/api/gerar": self._gerar, "/api/validar": self._validar,
            "/api/metricas/reset": self._reiniciar_metricas,
            "/api/experimentos": self._experimentar,
        }
        if rota not in acoes:
            raise ErroRequisicao("Operação não encontrada.", 404)
        if not isinstance(dados, dict):
            raise ErroRequisicao("Envie um objeto JSON.")
        with self._lock:
            self.clinica.exigir_disponibilidade()
            mensagem, resultado = acoes[rota](dados)
            resposta = {"ok": True, "estado": self.estado(), "mensagem": mensagem}
            if resultado is not None:
                resposta["resultado"] = resultado
            return resposta

    def _cadastrar(self, dados: dict) -> tuple[str, dict]:
        campos = ("prontuario", "nome", "data_nascimento", "telefone")
        if set(dados) != set(campos):
            raise ErroRequisicao("Informe prontuario, nome, data_nascimento e telefone.")
        self._inteiro(dados, "prontuario", minimo=1)
        paciente = Paciente(**dados)
        self._conferir_limite(1)
        try:
            with self._capturar_alteracao(f"Cadastro do prontuário {paciente.prontuario}"):
                self.clinica.cadastrar(paciente)
        except ValueError as erro:
            if "já cadastrado" in str(erro):
                raise ErroRequisicao(str(erro), 409) from erro
            raise
        return "Paciente cadastrado nas duas árvores.", asdict(paciente)

    def _remover(self, dados: dict) -> tuple[str, None]:
        prontuario = self._inteiro(dados, "prontuario", minimo=1)
        with self._capturar_alteracao(f"Remoção do prontuário {prontuario}"):
            self.clinica.remover(prontuario)
        return "Paciente removido das duas árvores.", None

    def _buscar(self, dados: dict) -> tuple[str, dict]:
        nome = self._arvore(dados.get("arvore", "AVL"))
        prontuario = self._inteiro(dados, "prontuario", minimo=1)
        arvore = self.clinica.selecionar(nome)
        paciente = arvore.buscar(prontuario)
        visitas = arvore.nos_visitados_ultima_busca
        self._logs.append(f"Busca de {prontuario} na {nome}: {visitas} nós visitados.")
        return ("Paciente encontrado." if paciente is not None else "Paciente não encontrado."), {
            "paciente": asdict(paciente) if paciente is not None else None,
            "nos_visitados": visitas, "arvore": nome,
        }

    def _demonstracao(self, dados: dict) -> tuple[str, dict]:
        if self.clinica.arvores["AVL"].quantidade() != 0:
            raise ErroRequisicao("A demonstração requer um cadastro vazio.", 409)
        chaves = (30, 10, 20, 50, 40, 60, 5, 15, 55, 70, 65, 1)
        pacientes = [replace(p, prontuario=chave)
                     for p, chave in zip(gerar_pacientes(len(chaves), 42), chaves)]
        with self._capturar_alteracao("Demonstração de rebalanceamento"):
            self.clinica.cadastrar_lote(pacientes)
        return "Demonstração carregada nas duas árvores.", {"chaves": list(chaves)}

    def _gerar(self, dados: dict) -> tuple[str, dict]:
        quantidade = self._inteiro(dados, "quantidade", minimo=0, maximo=LIMITE_PACIENTES)
        seed = self._inteiro(dados, "seed", padrao=42)
        self._conferir_limite(quantidade)
        primeiro = self.clinica.proximo_prontuario()
        if quantidade and primeiro + quantidade - 1 > MAX_INTEIRO_JSON:
            raise ErroRequisicao(
                "O lote excederia o maior prontuário representável no navegador."
            )
        pacientes = gerar_pacientes(quantidade, seed, primeiro)
        with self._capturar_alteracao(f"Geração de {quantidade} pacientes fictícios"):
            self.clinica.cadastrar_lote(pacientes)
        return f"{quantidade} pacientes fictícios cadastrados.", {"gerados": quantidade, "seed": seed}

    def _validar(self, dados: dict) -> tuple[str, dict]:
        validas = {nome: arvore.validar() for nome, arvore in self.clinica.arvores.items()}
        self._logs.append("Validação: " + "; ".join(
            f"{nome}: {'válida' if valida else 'inválida'}" for nome, valida in validas.items()
        ))
        return ("As duas árvores são válidas." if all(validas.values())
                else "A validação encontrou uma estrutura inválida."), validas

    def _reiniciar_metricas(self, dados: dict) -> tuple[str, None]:
        for arvore in self.clinica.arvores.values():
            arvore.reiniciar_estatisticas()
        self._logs.append("Estatísticas das duas árvores reiniciadas; pacientes preservados.")
        return "Estatísticas reiniciadas.", None

    def _experimentar(self, dados: dict) -> tuple[str, dict]:
        tamanho = self._inteiro(dados, "tamanho", padrao=100)
        seed = self._inteiro(dados, "seed", padrao=42)
        if tamanho not in (100, 1000):
            raise ErroRequisicao("Escolha 100 ou 1000 pacientes para a comparação local.")
        resultados = executar_experimentos((tamanho,), seed, self.clinica.fabricas)
        tabela = StringIO(newline="")
        escritor = csv.DictWriter(tabela, fieldnames=[campo.name for campo in fields(Resultado)])
        escritor.writeheader()
        escritor.writerows(asdict(resultado) for resultado in resultados)
        self._logs.append(f"Comparação concluída: {tamanho} pacientes, semente {seed}; cadastro preservado.")
        return "Comparação concluída em árvores independentes.", {
            "resultados": [asdict(resultado) for resultado in resultados],
            "csv_texto": tabela.getvalue(),
        }
