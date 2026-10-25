"""Servidor HTTP local sem dependências e com rotas estáticas explícitas."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from integracao import ErroIntegracao
from interface.servico import ErroRequisicao, ServicoClinica


MAX_CORPO = 65536
PASTA_ESTATICA = Path(__file__).resolve().parent / "static"
ARQUIVOS_ESTATICOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


class ServidorInterface(ThreadingHTTPServer):
    """As requisições compartilham o serviço; seu lock serializa as operações."""

    daemon_threads = True

    def __init__(self, endereco, servico: ServicoClinica) -> None:
        self.servico = servico
        super().__init__(endereco, ManipuladorInterface)


class ManipuladorInterface(BaseHTTPRequestHandler):
    server_version = "ClinicaLocal/1.0"
    sys_version = ""

    def log_message(self, formato, *argumentos) -> None:
        # Não registrar URLs, requisições ou dados dos pacientes no terminal.
        pass

    def _enviar(self, status: int, corpo: bytes, tipo: str, api: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store" if api else "no-cache")
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, status: int, dados: dict) -> None:
        corpo = json.dumps(dados, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._enviar(status, corpo, "application/json; charset=utf-8", api=True)

    def _endereco_local(self, endereco: str, origem: bool = False) -> bool:
        try:
            partes = urlsplit(endereco if origem else "//" + endereco)
            return (partes.hostname in ("127.0.0.1", "localhost")
                    and (partes.port or 80) == self.server.server_port
                    and partes.username is None and partes.password is None
                    and not partes.path and not partes.query and not partes.fragment
                    and (not origem or partes.scheme == "http"))
        except ValueError:
            return False

    def _conferir_host(self) -> None:
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or not self._endereco_local(hosts[0]):
            raise ErroRequisicao("A interface aceita somente endereços locais.", 403)

    @staticmethod
    def _constante_invalida(valor: str):
        raise ValueError("O JSON não pode conter NaN ou infinito.")

    def _ler_json(self) -> dict:
        origem = self.headers.get("Origin")
        if origem is not None and not self._endereco_local(origem, origem=True):
            raise ErroRequisicao("Origem externa recusada pela interface local.", 403)
        if self.headers.get_content_type() != "application/json":
            raise ErroRequisicao("Envie os dados como application/json.", 415)
        comprimentos = self.headers.get_all("Content-Length", [])
        if len(comprimentos) != 1:
            raise ErroRequisicao("Informe um único Content-Length.", 411)
        try:
            comprimento = int(comprimentos[0])
        except ValueError as erro:
            raise ErroRequisicao("Content-Length inválido.") from erro
        if comprimento < 0 or self.headers.get("Transfer-Encoding") is not None:
            raise ErroRequisicao("Corpo da requisição inválido.")
        if comprimento > MAX_CORPO:
            raise ErroRequisicao("A requisição excede o limite de 64 KiB.", 413)
        try:
            texto = self.rfile.read(comprimento).decode("utf-8")
            dados = json.loads(texto, parse_constant=self._constante_invalida)
        except (UnicodeDecodeError, ValueError) as erro:
            raise ErroRequisicao("Envie um objeto JSON válido em UTF-8.") from erro
        if not isinstance(dados, dict):
            raise ErroRequisicao("Envie um objeto JSON.")
        return dados

    def _erro(self, erro: Exception) -> None:
        if isinstance(erro, ErroRequisicao):
            self._json(erro.status, {"ok": False, "erro": str(erro)})
        elif isinstance(erro, (TypeError, ValueError)):
            self._json(400, {"ok": False, "erro": str(erro)})
        elif isinstance(erro, ErroIntegracao):
            self._json(409, {"ok": False, "erro": str(erro)})
        else:
            self._json(500, {"ok": False, "erro": "Não foi possível concluir a operação local."})

    def do_GET(self) -> None:
        try:
            self._conferir_host()
            caminho = urlsplit(self.path)
            if caminho.path == "/api/estado":
                parametros = parse_qs(caminho.query, keep_blank_values=True)
                escolhas = parametros.get("arvore", ["AVL"])
                if len(escolhas) != 1:
                    raise ErroRequisicao("Informe uma única árvore.")
                estado = self.server.servico.estado(escolhas[0])
                self._json(200, {"ok": True, "estado": estado, "mensagem": "Cadastro atualizado."})
                return
            if caminho.path not in ARQUIVOS_ESTATICOS:
                raise ErroRequisicao("Página não encontrada.", 404)
            nome, tipo = ARQUIVOS_ESTATICOS[caminho.path]
            arquivo = PASTA_ESTATICA / nome
            if not arquivo.is_file():
                raise ErroRequisicao("Recurso da interface não encontrado.", 404)
            self._enviar(200, arquivo.read_bytes(), tipo)
        except Exception as erro:
            self._erro(erro)

    def do_POST(self) -> None:
        try:
            self._conferir_host()
            caminho = urlsplit(self.path)
            dados = self._ler_json()
            self._json(200, self.server.servico.executar(caminho.path, dados))
        except Exception as erro:
            self._erro(erro)

    def do_OPTIONS(self) -> None:
        self._json(405, {"ok": False, "erro": "Método não permitido; use GET ou POST."})


def criar_servidor(porta: int = 8000, servico: ServicoClinica | None = None,
                   host: str = "127.0.0.1") -> ServidorInterface:
    """Reserva uma porta local; porta 0 permite testes com porta efêmera."""
    if host != "127.0.0.1":
        raise ValueError("O servidor deve permanecer em 127.0.0.1.")
    if type(porta) is not int or not 0 <= porta <= 65535:
        raise ValueError("A porta deve ser um inteiro entre 0 e 65535.")
    return ServidorInterface((host, porta), servico if servico is not None else ServicoClinica())
