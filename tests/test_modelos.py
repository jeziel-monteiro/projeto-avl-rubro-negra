"""Validação dos quatro campos de Paciente."""

from dataclasses import FrozenInstanceError, fields
import unittest

from modelos import Paciente


class TestPaciente(unittest.TestCase):
    def criar(self, **alteracoes):
        dados = dict(prontuario=1025, nome="Maria Oliveira",
                     data_nascimento="1998-05-12", telefone="01999998888")
        return Paciente(**(dados | alteracoes))

    def test_criacao_valida_e_representacao(self):
        paciente = self.criar()
        self.assertEqual(paciente.telefone, "01999998888")
        self.assertIn("Maria Oliveira", str(paciente))
        self.assertEqual([campo.name for campo in fields(Paciente)],
                         ["prontuario", "nome", "data_nascimento", "telefone"])

    def test_prontuario_invalido(self):
        for valor in (0, -1):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.criar(prontuario=valor)

    def test_nome_vazio(self):
        for nome in ("", "   ", "\t"):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                self.criar(nome=nome)

    def test_telefone_em_branco(self):
        for telefone in ("", " ", "    ", "\t", "\n", " \t\n "):
            with self.subTest(telefone=telefone), self.assertRaisesRegex(
                    ValueError, "O telefone não pode estar vazio"):
                self.criar(telefone=telefone)

    def test_telefone_preservado_exatamente(self):
        for telefone in ("01999998888", "0011999998888", "00012345678",
                         " 01999998888 ", "+55 (92) 1234-5678"):
            with self.subTest(telefone=telefone):
                paciente = self.criar(telefone=telefone)
                self.assertEqual(paciente.telefone, telefone)
                self.assertIsInstance(paciente.telefone, str)
                self.assertEqual(str(paciente),
                                 "Prontuário: 1025 | Nome: Maria Oliveira | "
                                 f"Nascimento: 1998-05-12 | Telefone: {telefone}")

    def test_datas_invalidas(self):
        for data in ("2023-02-29", "2000-13-01", "1998-5-12", "19980512",
                     "0000-01-01", "1998-05-12T00:00:00", "texto"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.criar(data_nascimento=data)
        self.assertEqual(self.criar(data_nascimento="2000-02-29").data_nascimento,
                         "2000-02-29")

    def test_tipos_invalidos(self):
        casos = {"prontuario": (True, "1", 1.0, None),
                 "nome": (1, None, []), "data_nascimento": (20000101, None),
                 "telefone": (11999998888, None, False)}
        for campo, valores in casos.items():
            for valor in valores:
                with self.subTest(campo=campo, valor=valor), self.assertRaises(TypeError):
                    self.criar(**{campo: valor})

    def test_chave_nao_pode_mudar_apos_validacao(self):
        with self.assertRaises(FrozenInstanceError):
            self.criar().prontuario = 0

    def test_duplicidade_nao_e_responsabilidade_do_modelo(self):
        self.assertEqual(self.criar(), self.criar())


if __name__ == "__main__":
    unittest.main()
