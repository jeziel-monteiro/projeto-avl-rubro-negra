"""Dados dos pacientes do minimundo Clínica / Atendimento."""

from dataclasses import dataclass
from datetime import date
import re


@dataclass(frozen=True)
class Paciente:
    """Paciente imutável, identificado nas árvores pelo prontuário positivo."""

    prontuario: int
    nome: str
    data_nascimento: str
    telefone: str

    def __post_init__(self) -> None:
        """Valida tipos e valores sem converter silenciosamente os dados."""
        if type(self.prontuario) is not int:
            raise TypeError("O prontuário deve ser um número inteiro.")
        if self.prontuario <= 0:
            raise ValueError("O prontuário deve ser positivo.")
        for campo in ("nome", "data_nascimento", "telefone"):
            if not isinstance(getattr(self, campo), str):
                raise TypeError(f"O campo {campo} deve ser uma string.")
        if not self.nome.strip():
            raise ValueError("O nome não pode estar vazio.")
        if not self.telefone.strip():
            raise ValueError("O telefone não pode estar vazio.")
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", self.data_nascimento):
            raise ValueError("A data de nascimento deve usar o formato AAAA-MM-DD.")
        try:
            date.fromisoformat(self.data_nascimento)
        except ValueError as erro:
            raise ValueError("A data de nascimento deve ser uma data real.") from erro

    def __str__(self) -> str:
        """Apresenta os quatro campos de forma legível no terminal."""
        return (
            f"Prontuário: {self.prontuario} | Nome: {self.nome} | "
            f"Nascimento: {self.data_nascimento} | Telefone: {self.telefone}"
        )
