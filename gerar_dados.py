"""Geração reproduzível de pacientes sintéticos, sem alterar o random global."""

import argparse
from collections.abc import Iterable
from datetime import date, timedelta
import random

from modelos import Paciente


TAMANHOS_PADRAO = (100, 1_000, 10_000)
NOMES = ("Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Helena", "Igor")
SOBRENOMES = ("Silva", "Oliveira", "Souza", "Lima", "Costa", "Santos", "Pereira")
DATA_INICIAL = date(1940, 1, 1)
DATA_FINAL = date(2020, 12, 31)


def gerar_pacientes(quantidade: int, seed: int | None = 42,
                    prontuario_inicial: int = 1) -> list[Paciente]:
    """Gera prontuários consecutivos únicos e dados fictícios com datas fixas."""
    if type(quantidade) is not int:
        raise TypeError("A quantidade deve ser um número inteiro.")
    if quantidade < 0:
        raise ValueError("A quantidade não pode ser negativa.")
    if type(prontuario_inicial) is not int:
        raise TypeError("O prontuário inicial deve ser um número inteiro.")
    if prontuario_inicial <= 0:
        raise ValueError("O prontuário inicial deve ser positivo.")
    gerador = random.Random(seed)
    dias = (DATA_FINAL - DATA_INICIAL).days
    pacientes = []
    for prontuario in range(prontuario_inicial, prontuario_inicial + quantidade):
        nome = f"{gerador.choice(NOMES)} {gerador.choice(SOBRENOMES)} (Fictício)"
        nascimento = DATA_INICIAL + timedelta(days=gerador.randint(0, dias))
        telefone = f"009{gerador.randrange(100_000_000):08d}"
        pacientes.append(Paciente(prontuario, nome, nascimento.isoformat(), telefone))
    return pacientes


def ordenar_pacientes(pacientes: Iterable[Paciente]) -> list[Paciente]:
    """Retorna uma nova lista em ordem crescente de prontuário."""
    return sorted(pacientes, key=lambda paciente: paciente.prontuario)


def embaralhar_pacientes(pacientes: Iterable[Paciente],
                         seed: int | None = 42) -> list[Paciente]:
    """Embaralha uma cópia da coleção usando uma fonte aleatória local."""
    copia = list(pacientes)
    random.Random(seed).shuffle(copia)
    return copia


def main() -> None:
    """Permite inspecionar registros sintéticos diretamente pelo terminal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quantidade", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--aleatorio", action="store_true")
    argumentos = parser.parse_args()
    try:
        pacientes = gerar_pacientes(argumentos.quantidade, argumentos.seed)
    except (TypeError, ValueError) as erro:
        parser.error(str(erro))
    if argumentos.aleatorio:
        pacientes = embaralhar_pacientes(pacientes, argumentos.seed)
    for paciente in pacientes:
        print(paciente)


if __name__ == "__main__":
    main()
