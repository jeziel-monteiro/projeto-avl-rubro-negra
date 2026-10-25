"""Inicialização portátil: python -m interface."""

import argparse
import sys
import webbrowser

from interface.servidor import criar_servidor


def main() -> None:
    parser = argparse.ArgumentParser(description="Abra a clínica no navegador, somente neste computador.")
    parser.add_argument("--porta", type=int, default=8000, help="Porta local (padrão: 8000).")
    parser.add_argument("--sem-navegador", action="store_true", help="Não abrir o navegador automaticamente.")
    argumentos = parser.parse_args()
    if not 1 <= argumentos.porta <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")
    try:
        servidor = criar_servidor(porta=argumentos.porta)
    except OSError as erro:
        parser.exit(1, f"Não foi possível abrir a porta {argumentos.porta}. "
                    "Ela pode estar ocupada; tente --porta 8001. "
                    f"Detalhe: {erro}\n")
    except Exception as erro:
        parser.exit(1, f"Não foi possível iniciar a interface: {erro}\n")
    url = f"http://127.0.0.1:{servidor.server_port}"
    print(f"Clínica disponível em {url}")
    print("Os pacientes ficam somente em memória. Use Ctrl+C para encerrar.")
    if not argumentos.sem_navegador:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            print(f"Abra {url} manualmente no navegador.", file=sys.stderr)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nInterface encerrada.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
